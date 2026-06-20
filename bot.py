#!/usr/bin/env python3
"""
Bot de previsão do tempo para Instagram (@previsaovr).
API: Instagram Login (graph.instagram.com) — tokens gerados no painel
"Configuração da API com Login do Instagram".

Modos:
  python bot.py diario   -> card de HOJE (poshtar às 8h)
  python bot.py amanha   -> card de AMANHÃ (postar às 20h da véspera)
  python bot.py semanal  -> card da SEMANA (domingo de manhã)

Variáveis de ambiente (Secrets do GitHub):
  IG_USER_ID      -> ID da conta (mostrado junto do token no painel)
  IG_ACCESS_TOKEN -> token de acesso (60 dias)
  REPO_RAW_BASE   -> ex.: https://raw.githubusercontent.com/SEUUSER/SEUREPO/main
"""
import os
import sys
import time
import datetime
import requests
from PIL import Image, ImageDraw, ImageFont

# ----------------- SUAS CIDADES -----------------
CIDADES = [
    {"nome": "Volta Redonda - RJ", "lat": -22.5202, "lon": -44.1043, "hashtag": "voltaredonda"},
]
# ------------------------------------------------

W, H = 1080, 1920
DIAS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
DIAS_LONGO = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
              "sexta-feira", "sábado", "domingo"]
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def fonte(tam, bold=True):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, nome), tam)


def tempo_info(code):
    if code == 0: return ("Céu limpo", (29, 111, 209), (95, 182, 242))
    if code <= 2: return ("Parcialmente nublado", (46, 124, 199), (127, 189, 232))
    if code == 3: return ("Nublado", (78, 100, 120), (142, 163, 181))
    if code <= 48: return ("Névoa", (93, 112, 127), (159, 178, 191))
    if code <= 57: return ("Chuvisco", (58, 99, 144), (123, 162, 196))
    if code <= 67: return ("Chuva", (44, 79, 116), (94, 133, 171))
    if code <= 77: return ("Neve", (106, 138, 165), (184, 205, 218))
    if code <= 82: return ("Pancadas de chuva", (39, 73, 107), (90, 128, 166))
    return ("Tempestade", (28, 47, 68), (70, 98, 127))


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


def buscar_previsao(lat, lon):
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
           "&current=temperature_2m,relative_humidity_2m,weather_code"
           "&timezone=America%2FSao_Paulo&forecast_days=7")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()


def blocos_info(img, dr, itens, y=880):
    total = len(itens) * 250 - 40
    inicio = (W - total) // 2
    for i, (v, r) in enumerate(itens):
        x = inicio + i * 250
        caixa(img, [x, y, x + 210, y + 180], 22, 40)
        dr = ImageDraw.Draw(img)
        wv = dr.textlength(v, font=fonte(52))
        dr.text((x + (210 - wv) / 2, y + 40), v, font=fonte(52), fill=(255, 255, 255))
        wr = dr.textlength(r, font=fonte(28, False))
        dr.text((x + (210 - wr) / 2, y + 115), r, font=fonte(28, False), fill=(225, 235, 244))
    return ImageDraw.Draw(img)


def card_diario(cidade, d, caminho):
    """Card de HOJE — postado às 8h, com temperatura atual."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["current"]["weather_code"])
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    hoje = datetime.date.today()
    centro(dr, "PREVISÃO DE HOJE", 80, fonte(34))
    centro(dr, cidade["nome"].upper(), 140, fonte(64))
    centro(dr, f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month-1]}", 225, fonte(34, False), (235, 242, 248))
    centro(dr, f"{round(d['current']['temperature_2m'])}°", 400, fonte(220))
    centro(dr, cond, 700, fonte(46, False))
    maxi = round(d["daily"]["temperature_2m_max"][0])
    mini = round(d["daily"]["temperature_2m_min"][0])
    chuva = d["daily"]["precipitation_probability_max"][0]
    umid = round(d["current"]["relative_humidity_2m"])
    dr = blocos_info(img, dr, [(f"{maxi}°", "Máxima"), (f"{mini}°", "Mínima"),
                               (f"{chuva}%", "Chuva"), (f"{umid}%", "Umidade")])
    centro(dr, "Siga @previsaovr • todos os dias", 1230, fonte(30), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_amanha(cidade, d, caminho):
    """Card de AMANHÃ — postado às 20h da véspera, usa dados do dia seguinte."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][1])
    # tom levemente mais escuro: clima de "noite anterior"
    c1 = tuple(max(0, c - 35) for c in c1)
    c2 = tuple(max(0, c - 25) for c in c2)
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    amanha = datetime.date.today() + datetime.timedelta(days=1)
    centro(dr, "COMO SERÁ AMANHÃ?", 80, fonte(34))
    centro(dr, cidade["nome"].upper(), 140, fonte(64))
    centro(dr, f"{DIAS_LONGO[amanha.weekday()].capitalize()}, {amanha.day} de {MESES[amanha.month-1]}",
           225, fonte(34, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][1])
    mini = round(d["daily"]["temperature_2m_min"][1])
    chuva = d["daily"]["precipitation_probability_max"][1]
    centro(dr, f"{maxi}°", 380, fonte(200))
    centro(dr, "máxima prevista", 640, fonte(34, False), (220, 230, 240))
    centro(dr, cond, 710, fonte(46, False))
    dr = blocos_info(img, dr, [(f"{maxi}°", "Máxima"), (f"{mini}°", "Mínima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, "Amanhã às 8h tem atualização • @previsaovr", 1230, fonte(30), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_semanal(cidade, d, caminho):
    img = Image.new("RGBA", (W, H))
    gradiente(img, (22, 50, 76), (61, 106, 147))
    dr = ImageDraw.Draw(img)
    centro(dr, "PREVISÃO DA SEMANA", 80, fonte(34))
    centro(dr, cidade["nome"].upper(), 140, fonte(64))
    linhas = []
    for i in range(7):
        dt = datetime.date.fromisoformat(d["daily"]["time"][i])
        cond, _, _ = tempo_info(d["daily"]["weather_code"][i])
        maxi = round(d["daily"]["temperature_2m_max"][i])
        mini = round(d["daily"]["temperature_2m_min"][i])
        chuva = d["daily"]["precipitation_probability_max"][i]
        y = 270 + i * 135
        caixa(img, [60, y, 1020, y + 115], 20, 55 if i == 0 else 25)
        dr = ImageDraw.Draw(img)
        rotulo = "HOJE" if i == 0 else DIAS[dt.weekday()]
        dr.text((95, y + 35), rotulo, font=fonte(42), fill=(255, 255, 255))
        dr.text((300, y + 40), cond, font=fonte(32, False), fill=(225, 235, 244))
        dr.text((800, y + 35), f"{maxi}°", font=fonte(44), fill=(255, 255, 255))
        dr.text((910, y + 35), f"{mini}°", font=fonte(44), fill=(180, 200, 216))
        linhas.append(f"{rotulo.title()}: {cond}, {mini}°–{maxi}° (chuva {chuva}%)")
    centro(dr, "Siga @previsaovr • previsão diária", 1240, fonte(30), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return linhas


def _aguardar_imagem(url_imagem):
    """Aguarda a imagem ficar publicamente acessivel no raw.githubusercontent.
    Apos o git push, o CDN pode levar alguns segundos para servir o arquivo."""
    for tentativa in range(12):
        try:
            head = requests.head(url_imagem, timeout=15, allow_redirects=True)
            if head.status_code == 200:
                return
        except requests.RequestException as e:
            print(f"Tentativa {tentativa + 1}: erro ao checar imagem -> {e}")
        time.sleep(6)
    raise RuntimeError(f"Imagem nao ficou acessivel a tempo: {url_imagem}")


def _criar_e_publicar(base, token, dados_container, rotulo):
    """Cria um container de midia, aguarda o processamento e publica."""
    r = requests.post(f"{base}/media", data={**dados_container, "access_token": token},
                      timeout=60)
    if not r.ok:
        print(f"Resposta Instagram /media ({rotulo}):", r.status_code, r.text)
    r.raise_for_status()
    container = r.json()["id"]

    for _ in range(12):
        s = requests.get(f"https://graph.instagram.com/v21.0/{container}",
                         params={"fields": "status_code", "access_token": token},
                         timeout=30).json()
        if s.get("status_code") == "FINISHED":
            break
        time.sleep(5)

    r = requests.post(f"{base}/media_publish", data={
        "creation_id": container, "access_token": token
    }, timeout=60)
    if not r.ok:
        print(f"Resposta Instagram /media_publish ({rotulo}):", r.status_code, r.text)
    r.raise_for_status()
    print(f"Publicado ({rotulo})! ID:", r.json().get("id"))


def publicar_instagram(url_imagem, legenda):
    """Publica no feed via Instagram Login API (graph.instagram.com)."""
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.instagram.com/v21.0/{ig_user}"
    _aguardar_imagem(url_imagem)
    _criar_e_publicar(base, token, {
        "image_url": url_imagem, "caption": legenda
    }, "feed")


def publicar_story(url_imagem):
    """Publica a mesma imagem como Story (media_type=STORIES)."""
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.instagram.com/v21.0/{ig_user}"
    _aguardar_imagem(url_imagem)
    _criar_e_publicar(base, token, {
        "image_url": url_imagem, "media_type": "STORIES"
    }, "story")


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "diario"
    raw_base = os.environ.get("REPO_RAW_BASE", "").rstrip("/")
    hoje = datetime.date.today()
    for cidade in CIDADES:
        d = buscar_previsao(cidade["lat"], cidade["lon"])
        slug = cidade["hashtag"]
        nome_curto = cidade["nome"].split(" -")[0]
        arquivo = f"imagens/{slug}-{modo}-{hoje.isoformat()}.png"
        if modo == "amanha":
            cond, maxi, mini, chuva = card_amanha(cidade, d, arquivo)
            amanha = hoje + datetime.timedelta(days=1)
            dica = "Já deixe o guarda-chuva separado! ☔" if chuva >= 60 else "Pode planejar o dia tranquilo! 😎"
            legenda = (f"🌙 Boa noite, {nome_curto}!\n\n"
                       f"Amanhã ({DIAS_LONGO[amanha.weekday()]}, {amanha.day}/{amanha.month}):\n"
                       f"{cond} • Máx {maxi}° / Mín {mini}° • {chuva}% de chance de chuva\n\n"
                       f"{dica}\n\n"
                       f"Amanhã às 8h tem atualização por aqui 📲\n\n"
                       f"#previsaodotempo #{slug} #clima #boanoite")
        elif modo == "semanal":
            linhas = card_semanal(cidade, d, arquivo)
            legenda = (f"🗓️ Previsão da semana em {cidade['nome']}!\n\n"
                       + "\n".join(linhas)
                       + "\n\nSalve este post e marque alguém da cidade! 📍"
                       + f"\n\n#previsaodotempo #{slug} #clima #tempo")
        else:
            cond, maxi, mini, chuva = card_diario(cidade, d, arquivo)
            dica = "Leve o guarda-chuva! ☔" if chuva >= 60 else "Aproveite o dia! 😎"
            legenda = (f"☀️ Bom dia, {nome_curto}!\n\n"
                       f"Previsão de hoje ({hoje.day}/{hoje.month}):\n"
                       f"{cond} • Máx {maxi}° / Mín {mini}° • {chuva}% de chance de chuva\n\n"
                       f"Vai sair de casa? {dica}\n\n"
                       f"Siga @previsaovr para receber todos os dias 📲\n\n"
                       f"#previsaodotempo #{slug} #clima #bomdia")
        print(f"Card gerado: {arquivo}")
        if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
            url_card = f"{raw_base}/{arquivo}"
            publicar_instagram(url_card, legenda)
            publicar_story(url_card)
        else:
            print("Sem credenciais — apenas a imagem foi gerada.")
            print("Legenda:\n", legenda)


if __name__ == "__main__":
    main()
