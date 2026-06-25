#!/usr/bin/env python3
"""
Detector de alertas climaticos para @previsaovr (Sul Fluminense).

Roda em loop curto (ex.: a cada 10-15 min via cron na VM) e:
  1. consulta o Open-Meteo (dados horarios + atuais) das cidades monitoradas;
  2. avalia regras de severidade (chuva, vento, calor, frio);
  3. aplica anti-falso-alarme (dedup por evento + cooldown + so publica se subir de nivel);
  4. gera um card de alerta e publica no feed + story via Instagram Login API.

Estado persistido em alertas_estado.json (na propria pasta).

Variaveis de ambiente (iguais ao bot.py):
    IG_USER_ID       -> ID da conta
    IG_ACCESS_TOKEN  -> token de acesso
    REPO_RAW_BASE    -> base publica das imagens (raw do GitHub) OU servidor proprio
    PUBLICAR_REEL    -> "true" para publicar tambem como Reel (requer ffmpeg)

Uso:
    python alerta.py            -> roda uma verificacao
    python alerta.py --teste    -> forca a geracao de um card de exemplo (sem publicar)
"""
import os
import sys
import json
import time
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont
try:
    from reel import gerar_reel, publicar_reel as _publicar_reel
    _REEL_DISPONIVEL = True
except ImportError:
    _REEL_DISPONIVEL = False
try:
    from telegram_bot import enviar_alerta as _tg_enviar_alerta
    _TELEGRAM_DISPONIVEL = True
except ImportError:
    _TELEGRAM_DISPONIVEL = False

# ------------------------------------------------------------------
# Cidades monitoradas para alertas de emergencia (Angra removida: so previsao sexta 15h)
CIDADES = [
    {"nome": "Volta Redonda - RJ", "lat": -22.5202, "lon": -44.1043, "hashtag": "voltaredonda"},
    {"nome": "Porto Real - RJ", "lat": -22.4178, "lon": -44.2906, "hashtag": "portoreal"},
    {"nome": "Barra Mansa - RJ", "lat": -22.5446, "lon": -44.1717, "hashtag": "barramansa"},
    {"nome": "Resende - RJ", "lat": -22.4683, "lon": -44.4467, "hashtag": "resende"},
]

# ------------------------------------------------------------------
# LIMIARES DE ALERTA  (ajuste fino aqui depois de observar a regiao)
# Cada nivel: (rotulo, cor_de_fundo, emoji)
NIVEIS = {
    1: ("ATENCAO", (214, 158, 18), "\u26a0\ufe0f"),
    2: ("ALERTA", (200, 92, 16), "\U0001F7E0"),
    3: ("ALERTA GRAVE", (168, 28, 28), "\U0001F534"),
}

# Chuva: precipitacao prevista para a proxima hora (mm)
CHUVA_MM = {1: 5.0, 2: 15.0, 3: 30.0}
# Vento: rajada prevista (km/h)
VENTO_KMH = {1: 45.0, 2: 70.0, 3: 90.0}
# Calor: temperatura aparente maxima (graus C)
CALOR_C = {1: 36.0, 2: 39.0, 3: 42.0}
# Frio: temperatura aparente minima (graus C)
FRIO_C = {1: 8.0, 2: 5.0, 3: 2.0}

# Anti-falso-alarme
COOLDOWN_H = 6          # horas minimas entre alertas do mesmo tipo/cidade
ESTADO_ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alertas_estado.json")

W, H = 1080, 1920
FONT_DIR = "/usr/share/fonts/truetype/dejavu"


# ------------------------------------------------------------------
# Helpers visuais (espelham o estilo do bot.py)
def fonte(tam, bold=True):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, nome), tam)


def gradiente(img, c1, c2):
    d = ImageDraw.Draw(img)
    for y in range(H):
        f = y / H
        cor = tuple(int(c1[i] + (c2[i] - c1[i]) * f) for i in range(3))
        d.line([(0, y), (W, y)], fill=cor)


def caixa(img, box, raio, alpha):
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    od.rounded_rectangle(box, raio, fill=(255, 255, 255, alpha))
    img.alpha_composite(ov)


def centro(dr, texto, y, f, cor=(255, 255, 255)):
    w = dr.textlength(texto, font=f)
    dr.text(((W - w) / 2, y), texto, font=f, fill=cor)


def quebrar(dr, texto, f, larg_max):
    """Quebra um texto em varias linhas que cabem em larg_max."""
    palavras = texto.split()
    linhas, atual = [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if dr.textlength(teste, font=f) <= larg_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def buscar_previsao(lat, lon):
    """Busca dados atuais + horarios das proximas horas no Open-Meteo."""
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m"
        "&hourly=precipitation,wind_gusts_10m,apparent_temperature"
        "&forecast_days=1&timezone=America%2FSao_Paulo"
    )
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


# ------------------------------------------------------------------
# Deteccao de eventos
def _nivel_por_limiar(valor, limiares, maior_e_pior=True):
    """Retorna o maior nivel (1..3) atingido por valor, ou 0 se nenhum."""
    nivel = 0
    for n in (1, 2, 3):
        lim = limiares[n]
        if (maior_e_pior and valor >= lim) or (not maior_e_pior and valor <= lim):
            nivel = n
    return nivel


def avaliar(cidade, dados):
    """Avalia as regras e devolve o evento mais grave da cidade (ou None).
    Evento: dict com tipo, nivel, valor, titulo, descricao."""
    horas = dados.get("hourly", {})
    prox_chuva = max((horas.get("precipitation") or [0])[:3] or [0])
    prox_rajada = max((horas.get("wind_gusts_10m") or [0])[:3] or [0])
    temps_ap = (horas.get("apparent_temperature") or [])[:6]
    calor = max(temps_ap) if temps_ap else dados["current"].get("apparent_temperature", 0)
    frio = min(temps_ap) if temps_ap else dados["current"].get("apparent_temperature", 99)

    candidatos = []
    n = _nivel_por_limiar(prox_chuva, CHUVA_MM, True)
    if n:
        candidatos.append({
            "tipo": "chuva", "nivel": n, "valor": round(prox_chuva, 1),
            "titulo": "CHUVA FORTE A CAMINHO",
            "descricao": f"Ate {round(prox_chuva)} mm de chuva nas proximas horas em {cidade['nome'].split(' -')[0]}.",
        })
    n = _nivel_por_limiar(prox_rajada, VENTO_KMH, True)
    if n:
        candidatos.append({
            "tipo": "vento", "nivel": n, "valor": round(prox_rajada),
            "titulo": "VENTO FORTE",
            "descricao": f"Rajadas de ate {round(prox_rajada)} km/h previstas para {cidade['nome'].split(' -')[0]}.",
        })
    n = _nivel_por_limiar(calor, CALOR_C, True)
    if n:
        candidatos.append({
            "tipo": "calor", "nivel": n, "valor": round(calor),
            "titulo": "CALOR EXTREMO",
            "descricao": f"Sensacao termica pode chegar a {round(calor)} graus em {cidade['nome'].split(' -')[0]}. Hidrate-se!",
        })
    n = _nivel_por_limiar(frio, FRIO_C, False)
    if n:
        candidatos.append({
            "tipo": "frio", "nivel": n, "valor": round(frio),
            "titulo": "FRIO INTENSO",
            "descricao": f"Sensacao termica pode cair a {round(frio)} graus em {cidade['nome'].split(' -')[0]}.",
        })
    if not candidatos:
        return None
    return max(candidatos, key=lambda e: e["nivel"])


# ------------------------------------------------------------------
# Estado / anti-falso-alarme
def carregar_estado():
    try:
        with open(ESTADO_ARQ, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def salvar_estado(estado):
    with open(ESTADO_ARQ, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def deve_publicar(estado, chave, evento):
    """Decide se vale a pena publicar este evento agora.
    Regras anti-falso-alarme:
      - se nunca publicou esta chave: publica;
      - se o nivel SUBIU em relacao ao ultimo: publica (mesmo dentro do cooldown);
      - se o nivel e igual/menor e ainda esta no cooldown: nao publica."""
    agora = datetime.datetime.now()
    anterior = estado.get(chave)
    if not anterior:
        return True
    if evento["nivel"] > anterior.get("nivel", 0):
        return True
    try:
        ult = datetime.datetime.fromisoformat(anterior.get("quando"))
    except (TypeError, ValueError):
        return True
    return (agora - ult) >= datetime.timedelta(hours=COOLDOWN_H)


def registrar(estado, chave, evento):
    estado[chave] = {
        "nivel": evento["nivel"],
        "tipo": evento["tipo"],
        "valor": evento["valor"],
        "quando": datetime.datetime.now().isoformat(timespec="seconds"),
    }


# ------------------------------------------------------------------
# Card visual do alerta
EMOJI_TIPO = {
    "chuva": "\U0001F327\ufe0f",
    "vento": "\U0001F4A8",
    "calor": "\U0001F525",
    "frio": "\u2744\ufe0f",
}


def card_alerta(cidade, evento, caminho):
    """Gera o card do alerta com a cor do nivel de severidade."""
    rotulo, cor, emoji = NIVEIS[evento["nivel"]]
    c1 = tuple(max(0, c - 30) for c in cor)
    c2 = tuple(min(255, c + 25) for c in cor)
    img = Image.new("RGBA", (W, H))
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    agora = datetime.datetime.now()
    # faixa superior
    centro(dr, rotulo, 150, fonte(58))
    centro(dr, cidade["nome"].upper(), 250, fonte(64))
    # faixa central com o tipo do evento (sem emoji: DejaVu nao tem glifo colorido)
    rotulo_tipo = {"chuva": "CHUVA", "vento": "VENTO", "calor": "CALOR", "frio": "FRIO"}.get(evento["tipo"], "ALERTA")
    caixa(img, [120, 430, W - 120, 700], 40, 35)
    dr = ImageDraw.Draw(img)
    centro(dr, rotulo_tipo, 500, fonte(150))
    # titulo do evento
    centro(dr, evento["titulo"], 760, fonte(70))
    # descricao quebrada em linhas dentro de uma caixa
    caixa(img, [90, 900, W - 90, 1320], 36, 40)
    dr = ImageDraw.Draw(img)
    linhas = quebrar(dr, evento["descricao"], fonte(46, False), W - 220)
    y = 960
    for ln in linhas[:5]:
        centro(dr, ln, y, fonte(46, False), (255, 255, 255))
        y += 64
    # rodape
    centro(dr, f"Atualizado as {agora.strftime('%H:%M')} \u2022 fonte: Open-Meteo", 1640, fonte(34), (250, 245, 240))
    centro(dr, "Siga @previsaovr e ative as notificacoes!", 1780, fonte(38), (255, 255, 255))
    img.convert("RGB").save(caminho, "PNG")


# ------------------------------------------------------------------
# Publicacao (Instagram Login API)
def _aguardar_imagem(url_imagem):
    for tentativa in range(12):
        try:
            head = requests.head(url_imagem, timeout=15, allow_redirects=True)
            if head.status_code == 200:
                return
        except requests.RequestException as e:
            print(f"Tentativa {tentativa + 1}: erro ao checar imagem -> {e}")
        time.sleep(6)
    raise RuntimeError(f"Imagem nao ficou acessivel a tempo: {url_imagem}")


def _criar_e_publicar(base, token, dados, rotulo):
    r = requests.post(f"{base}/media", data={**dados, "access_token": token}, timeout=60)
    if not r.ok:
        print(f"Resposta /media ({rotulo}):", r.status_code, r.text)
    r.raise_for_status()
    container = r.json()["id"]
    for _ in range(12):
        s = requests.get(f"https://graph.instagram.com/v21.0/{container}",
                         params={"fields": "status_code", "access_token": token},
                         timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(5)
    r = requests.post(f"{base}/media_publish", data={"creation_id": container, "access_token": token}, timeout=60)
    if not r.ok:
        print(f"Resposta /media_publish ({rotulo}):", r.status_code, r.text)
    r.raise_for_status()
    print(f"Publicado ({rotulo})! ID:", r.json().get("id"))


def publicar(url_imagem, legenda):
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.instagram.com/v21.0/{ig_user}"
    _aguardar_imagem(url_imagem)
    _criar_e_publicar(base, token, {"image_url": url_imagem, "caption": legenda}, "feed")
    _criar_e_publicar(base, token, {"image_url": url_imagem, "media_type": "STORIES"}, "story")


# ------------------------------------------------------------------
def montar_legenda(cidade, evento):
    rotulo, _, emoji = NIVEIS[evento["nivel"]]
    nome = cidade["nome"].split(" -")[0]
    return (
        f"{emoji} {rotulo}: {evento['titulo'].title()} em {nome}!\n\n"
        f"{evento['descricao']}\n\n"
        "Compartilhe com quem mora ou vai sair por ai agora \U0001F501\n"
        "Marca alguem que PRECISA saber disso \U0001F447\n\n"
        "Siga @previsaovr e ative as notificacoes para nao perder nenhum alerta \U0001F514\n\n"
        f"#alerta #{cidade['hashtag']} #sulfluminense #tempovr #previsaodotempo #{evento['tipo']} #rj"
    )


def _exemplo():
    """Gera um card de exemplo (nivel 3, chuva) sem publicar. Para ajuste visual."""
    cidade = CIDADES[0]
    evento = {
        "tipo": "chuva", "nivel": 3, "valor": 42,
        "titulo": "CHUVA FORTE A CAMINHO",
        "descricao": "Ate 42 mm de chuva nas proximas horas em Volta Redonda. Evite areas de alagamento.",
    }
    os.makedirs("imagens", exist_ok=True)
    caminho = "imagens/exemplo-alerta.png"
    card_alerta(cidade, evento, caminho)
    print("Card de exemplo gerado em", caminho)
    print("Legenda:\n", montar_legenda(cidade, evento))


FILA_ARQ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alertas_fila.json")


def detectar_e_gerar():
    """Fase 1: detecta eventos, aplica anti-falso-alarme, gera os cards e grava
    uma fila (alertas_fila.json) com o que deve ser publicado. NAO publica."""
    estado = carregar_estado()
    hoje = datetime.date.today().isoformat()
    os.makedirs("imagens", exist_ok=True)
    fila = []
    for cidade in CIDADES:
        try:
            dados = buscar_previsao(cidade["lat"], cidade["lon"])
        except Exception as e:
            print(f"Erro ao buscar {cidade['nome']}: {e}")
            continue
        evento = avaliar(cidade, dados)
        if not evento:
            continue
        chave = f"{cidade['hashtag']}:{evento['tipo']}"
        if not deve_publicar(estado, chave, evento):
            print(f"[skip] {chave} nivel {evento['nivel']} ainda em cooldown.")
            continue
        arquivo = f"imagens/alerta-{cidade['hashtag']}-{evento['tipo']}-{hoje}.png"
        card_alerta(cidade, evento, arquivo)
        legenda = montar_legenda(cidade, evento)
        print(f"ALERTA detectado: {chave} nivel {evento['nivel']} -> {arquivo}")
        evento["cidade_nome"] = cidade["nome"]
        fila.append({"chave": chave, "arquivo": arquivo, "legenda": legenda, "evento": evento})
    with open(FILA_ARQ, "w", encoding="utf-8") as f:
        json.dump(fila, f, ensure_ascii=False, indent=2)
    print(f"{len(fila)} alerta(s) na fila.")
    return fila


def publicar_fila():
    """Fase 2: le a fila, publica cada card e atualiza o estado (cooldown)."""
    try:
        with open(FILA_ARQ, "r", encoding="utf-8") as f:
            fila = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        fila = []
    if not fila:
        print("Fila vazia - nada a publicar.")
        return
    raw_base = os.environ.get("REPO_RAW_BASE", "").rstrip("/")
    if not (raw_base and os.environ.get("IG_ACCESS_TOKEN")):
        print("Sem credenciais/REPO_RAW_BASE - publicacao ignorada.")
        return
    estado = carregar_estado()
    for item in fila:
        try:
            publicar(f"{raw_base}/{item['arquivo']}", item["legenda"])
            registrar(estado, item["chave"], item["evento"])
            # --- Telegram opcional ---
            if _TELEGRAM_DISPONIVEL:
                try:
                    _tg_enviar_alerta(
                        item["evento"].get("cidade_nome", item["chave"].split(":")[0]),
                        item["evento"],
                        foto_path=item.get("arquivo"),
                    )
                except Exception as te:
                    print(f"Telegram ignorado (erro nao critico): {te}")
            # --- Reel opcional ---
            if _REEL_DISPONIVEL and os.environ.get("PUBLICAR_REEL", "").lower() == "true":
                try:
                    png_path = item["arquivo"]
                    mp4_path = os.path.splitext(png_path)[0] + ".mp4"
                    gerar_reel(png_path, mp4_path)
                    import subprocess as _sp
                    _sp.run(["git", "add", mp4_path], check=False)
                    _sp.run(["git", "commit", "-m", f"reel: {os.path.basename(mp4_path)}"], check=False)
                    _sp.run(["git", "push"], check=False)
                    import time as _t; _t.sleep(5)
                    url_mp4 = f"{raw_base}/{mp4_path}"
                    _publicar_reel(url_mp4, item["legenda"])
                except Exception as re:
                    print(f"Reel ignorado (erro nao critico): {re}")
        except Exception as e:
            print(f"Erro ao publicar {item['chave']}: {e}")
    salvar_estado(estado)
    with open(FILA_ARQ, "w", encoding="utf-8") as f:
        json.dump([], f)
    print("Publicacao concluida.")


def main():
    if "--teste" in sys.argv:
        _exemplo()
        return
    if "--apenas-gerar" in sys.argv:
        detectar_e_gerar()
        return
    if "--apenas-publicar" in sys.argv:
        publicar_fila()
        return
    fila = detectar_e_gerar()
    if fila:
        publicar_fila()
    else:
        print("Nenhum alerta novo para publicar.")


if __name__ == "__main__":
    main()
