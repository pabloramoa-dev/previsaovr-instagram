#!/usr/bin/env python3
"""
Bot de previs\u00e3o do tempo para Instagram (@previsaovr).
API: Instagram Login (graph.instagram.com) \u2014 tokens gerados no painel
"Configura\u00e7\u00e3o da API com Login do Instagram".

Modos:
  python bot.py diario   -> card de HOJE (poshtar \u00e0s 8h)
  python bot.py amanha   -> card de AMANH\u00c3 (postar \u00e0s 20h da v\u00e9spera)
  python bot.py semanal  -> card da SEMANA (domingo de manh\u00e3)

Vari\u00e1veis de ambiente (Secrets do GitHub):
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
    {"nome": "Porto Real - RJ", "lat": -22.4178, "lon": -44.2906, "hashtag": "portoreal"},
    {"nome": "Barra Mansa - RJ", "lat": -22.5446, "lon": -44.1717, "hashtag": "barramansa"},
    {"nome": "Resende - RJ", "lat": -22.4683, "lon": -44.4467, "hashtag": "resende"},
]
# ------------------------------------------------
# Cidade do post tematico de sexta a noite (previsao de sabado)
ANGRA = {"nome": "Angra dos Reis - RJ", "lat": -23.0067, "lon": -44.3181, "hashtag": "angradosreis"}

W, H = 1080, 1920
DIAS = ["SEG", "TER", "QUA", "QUI", "SEX", "S\u00c1B", "DOM"]
DIAS_LONGO = ["segunda-feira", "ter\u00e7a-feira", "quarta-feira", "quinta-feira",
              "sexta-feira", "s\u00e1bado", "domingo"]
MESES = ["janeiro", "fevereiro", "mar\u00e7o", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def fonte(tam, bold=True):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, nome), tam)


def tempo_info(code):
    if code == 0: return ("C\u00e9u limpo", (29, 111, 209), (95, 182, 242))
    if code <= 2: return ("Parcialmente nublado", (46, 124, 199), (127, 189, 232))
    if code == 3: return ("Nublado", (78, 100, 120), (142, 163, 181))
    if code <= 48: return ("N\u00e9voa", (93, 112, 127), (159, 178, 191))
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


def blocos_info(img, dr, itens, y=1180):
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
    """Card de HOJE \u2014 postado \u00e0s 8h, com temperatura atual."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["current"]["weather_code"])
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    hoje = datetime.date.today()
    centro(dr, "PREVIS\u00c3O DE HOJE", 200, fonte(40))
    centro(dr, cidade["nome"].upper(), 280, fonte(74))
    centro(dr, f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month-1]}", 375, fonte(40, False), (235, 242, 248))
    centro(dr, f"{round(d['current']['temperature_2m'])}\u00b0", 560, fonte(250))
    centro(dr, cond, 900, fonte(54, False))
    maxi = round(d["daily"]["temperature_2m_max"][0])
    mini = round(d["daily"]["temperature_2m_min"][0])
    chuva = d["daily"]["precipitation_probability_max"][0]
    umid = round(d["current"]["relative_humidity_2m"])
    dr = blocos_info(img, dr, [(f"{maxi}\u00b0", "M\u00e1xima"), (f"{mini}\u00b0", "M\u00ednima"),
                               (f"{chuva}%", "Chuva"), (f"{umid}%", "Umidade")])
    centro(dr, "Siga @previsaovr \u2022 todos os dias", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_amanha(cidade, d, caminho):
    """Card de AMANH\u00c3 \u2014 postado \u00e0s 20h da v\u00e9spera, usa dados do dia seguinte."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][1])
    # tom levemente mais escuro: clima de "noite anterior"
    c1 = tuple(max(0, c - 35) for c in c1)
    c2 = tuple(max(0, c - 25) for c in c2)
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    amanha = datetime.date.today() + datetime.timedelta(days=1)
    centro(dr, "COMO SER\u00c1 AMANH\u00c3?", 200, fonte(40))
    centro(dr, cidade["nome"].upper(), 280, fonte(74))
    centro(dr, f"{DIAS_LONGO[amanha.weekday()].capitalize()}, {amanha.day} de {MESES[amanha.month-1]}",
              375, fonte(40, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][1])
    mini = round(d["daily"]["temperature_2m_min"][1])
    chuva = d["daily"]["precipitation_probability_max"][1]
    centro(dr, f"{maxi}\u00b0", 540, fonte(230))
    centro(dr, "m\u00e1xima prevista", 850, fonte(40, False), (220, 230, 240))
    centro(dr, cond, 920, fonte(54, False))
    dr = blocos_info(img, dr, [(f"{maxi}\u00b0", "M\u00e1xima"), (f"{mini}\u00b0", "M\u00ednima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, "Amanh\u00e3 \u00e0s 8h tem atualiza\u00e7\u00e3o \u2022 @previsaovr", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_semanal(cidade, d, caminho):
    img = Image.new("RGBA", (W, H))
    gradiente(img, (22, 50, 76), (61, 106, 147))
    dr = ImageDraw.Draw(img)
    centro(dr, "PREVIS\u00c3O DA SEMANA", 200, fonte(40))
    centro(dr, cidade["nome"].upper(), 280, fonte(74))
    linhas = []
    for i in range(7):
        dt = datetime.date.fromisoformat(d["daily"]["time"][i])
        cond, _, _ = tempo_info(d["daily"]["weather_code"][i])
        maxi = round(d["daily"]["temperature_2m_max"][i])
        mini = round(d["daily"]["temperature_2m_min"][i])
        chuva = d["daily"]["precipitation_probability_max"][i]
        y = 340 + i * 135
        caixa(img, [60, y, 1020, y + 115], 20, 55 if i == 0 else 25)
        dr = ImageDraw.Draw(img)
        rotulo = "HOJE" if i == 0 else DIAS[dt.weekday()]
        dr.text((95, y + 35), rotulo, font=fonte(42), fill=(255, 255, 255))
        dr.text((300, y + 40), cond, font=fonte(32, False), fill=(225, 235, 244))
        dr.text((800, y + 35), f"{maxi}\u00b0", font=fonte(44), fill=(255, 255, 255))
        dr.text((910, y + 35), f"{mini}\u00b0", font=fonte(44), fill=(180, 200, 216))
        linhas.append(f"{rotulo.title()}: {cond}, {mini}\u00b0\u2013{maxi}\u00b0 (chuva {chuva}%)")
    centro(dr, "Siga @previsaovr \u2022 previs\u00e3o di\u00e1ria", 1800, fonte(30), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return linhas


def card_carrossel(cidade, d, caminho, posicao, total):
    """Slide de uma cidade dentro do carrossel diario (postado as 6h30)."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][0])
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    hoje = datetime.date.today()
    centro(dr, "PREVIS\u00c3O DE HOJE", 200, fonte(40))
    centro(dr, cidade["nome"].upper(), 280, fonte(70))
    centro(dr, f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month-1]}", 375, fonte(38, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][0])
    mini = round(d["daily"]["temperature_2m_min"][0])
    chuva = d["daily"]["precipitation_probability_max"][0]
    centro(dr, f"{maxi}\u00b0", 540, fonte(250))
    centro(dr, cond, 880, fonte(54, False))
    dr = blocos_info(img, dr, [(f"{maxi}\u00b0", "M\u00e1xima"), (f"{mini}\u00b0", "M\u00ednima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, f"{posicao}/{total}  \u2022  arrasta para o lado \u2192", 1700, fonte(34), (230, 238, 246))
    centro(dr, "Siga @previsaovr \u2022 todos os dias", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_provocacao(caminho):
    """Ultimo slide do carrossel: chamada para engajamento."""
    img = Image.new("RGBA", (W, H))
    gradiente(img, (24, 47, 79), (52, 92, 140))
    dr = ImageDraw.Draw(img)
    centro(dr, "MOSTRE A SUA CIDADE!", 320, fonte(64))
    centro(dr, "Tem foto ou v\u00eddeo do tempo", 470, fonte(40, False), (225, 235, 244))
    centro(dr, "a\u00ed na sua cidade?", 525, fonte(40, False), (225, 235, 244))
    centro(dr, "A GENTE PUBLICA AQUI! \U0001F4F8", 600, fonte(42), (255, 209, 102))
    caixa(img, [140, 760, W - 140, 1120], 36, 45)
    centro(dr, "Manda no Direct \U0001F4E9", 830, fonte(50))
    centro(dr, "sua foto ou v\u00eddeo da", 910, fonte(50))
    centro(dr, "chuva, sol, c\u00e9u ou rua", 990, fonte(50))
    centro(dr, "e a gente compartilha! \U0001F64C", 1070, fonte(46), (255, 209, 102))
    centro(dr, "Salve este post \U0001F4CC", 1300, fonte(46, False), (235, 242, 248))
    centro(dr, "Marque algu\u00e9m da regi\u00e3o", 1380, fonte(46, False), (235, 242, 248))
    centro(dr, "Siga @previsaovr \u2022 todos os dias", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")

def montar_panorama(d):
    """Analisa os proximos 5 dias e devolve (frase_informativa, resumo)."""
    daily = d["daily"]
    codes = daily["weather_code"]
    maxs = daily["temperature_2m_max"]
    mins = daily["temperature_2m_min"]
    chuvas = daily.get("precipitation_probability_max") or [0] * len(codes)
    fim = min(6, len(codes))
    idxs = list(range(1, fim))
    n_janela = len(idxs)
    def conta(cond):
        return sum(1 for i in idxs if cond(i))
    dias_frio = conta(lambda i: maxs[i] < 23 or mins[i] < 14)
    dias_chuva = conta(lambda i: chuvas[i] >= 60)
    dias_chuva_leve = conta(lambda i: 40 <= chuvas[i] < 60)
    dias_calor = conta(lambda i: maxs[i] >= 32)
    dias_sol = conta(lambda i: codes[i] <= 2 and chuvas[i] < 40)
    # Escolhe UMA unica frase informativa, por prioridade
    def plural(n):
        return "dia" if n == 1 else "dias"
    if dias_chuva >= 1:
        frase = f"Prepare o guarda-chuva: {dias_chuva} {plural(dias_chuva)} de chuva pela frente"
    elif dias_frio >= 1:
        frase = f"Ainda teremos mais {dias_frio} {plural(dias_frio)} de frio pela frente"
    elif dias_calor >= 1:
        frase = f"Calor forte chegando: {dias_calor} {plural(dias_calor)} acima de 32 graus"
    elif dias_chuva_leve >= 2:
        frase = f"Pode pintar chuva em {dias_chuva_leve} dias da semana"
    elif dias_sol >= 1:
        frase = f"Sol firme em {dias_sol} {plural(dias_sol)} para aproveitar"
    else:
        frase = "Tempo estavel e sem grandes mudancas nos proximos dias"
    return frase, {
        "frio": dias_frio, "chuva": dias_chuva, "calor": dias_calor,
        "sol": dias_sol, "janela": n_janela,
    }


def quebrar(texto, limite):
    """Quebra um texto em varias linhas com no maximo `limite` caracteres."""
    palavras = texto.split(" ")
    linhas, atual = [], ""
    for pal in palavras:
        teste = (atual + " " + pal).strip()
        if len(teste) <= limite:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = pal
    if atual:
        linhas.append(atual)
    return linhas


def card_panorama(d, frase, caminho):
    """Card do meio-dia: uma frase informativa + chamada para comentario."""
    img = Image.new("RGBA", (W, H))
    gradiente(img, (20, 33, 61), (58, 90, 134))
    dr = ImageDraw.Draw(img)
    centro(dr, "PANORAMA DA SEMANA", 280, fonte(58))
    centro(dr, "Sul Fluminense \u2022 pr\u00f3ximos 5 dias", 370, fonte(38, False), (200, 214, 230))
    # frase informativa em destaque (caixa central)
    caixa(img, [110, 620, W - 110, 1080], 36, 40)
    linhas = quebrar(frase, 24)
    total_alt = len(linhas) * 90
    y = 850 - total_alt // 2
    for ln in linhas:
        centro(dr, ln, y, fonte(64))
        y += 90
    # chamada para comentario
    centro(dr, "E a\u00ed na SUA cidade?", 1320, fonte(50), (255, 209, 102))
    cta = quebrar("Comenta aqui como esta o tempo hoje na sua cidade!", 26)
    yc = 1440
    for ln in cta:
        centro(dr, ln, yc, fonte(46, False), (235, 242, 248))
        yc += 64
    centro(dr, "Siga @previsaovr \u2022 todos os dias", 1820, fonte(34), (210, 222, 238))
    img.convert("RGB").save(caminho, "PNG")


def card_angra(d, caminho):
    """Post de sexta \u00e0 noite: previs\u00e3o de S\u00c1BADO para Angra dos Reis."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][1])
    # tom litoraneo: azul-mar mais vivo
    c1 = (8, 78, 110)
    c2 = (20, 140, 180)
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    amanha = datetime.date.today() + datetime.timedelta(days=1)
    centro(dr, "VAI PRA ANGRA AMANH\u00c3?", 150, fonte(64))
    centro(dr, "Veja a previs\u00e3o \U0001f440", 250, fonte(44, False), (255, 209, 102))
    centro(dr, "ANGRA DOS REIS", 420, fonte(70))
    centro(dr, f"{DIAS_LONGO[amanha.weekday()].capitalize()}, {amanha.day} de {MESES[amanha.month-1]}",
              510, fonte(38, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][1])
    mini = round(d["daily"]["temperature_2m_min"][1])
    chuva = d["daily"]["precipitation_probability_max"][1]
    centro(dr, f"{maxi}\u00b0", 640, fonte(230))
    centro(dr, cond, 950, fonte(54, False))
    dr = blocos_info(img, dr, [(f"{maxi}\u00b0", "M\u00e1xima"), (f"{mini}\u00b0", "M\u00ednima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, "Bom fim de semana! \U0001f3dd\ufe0f  @previsaovr", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva

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


def publicar_carrossel(urls_imagens, legenda):
    """Publica um carrossel (varias imagens num unico post) via Graph API."""
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.instagram.com/v21.0/{ig_user}"
    filhos = []
    for url in urls_imagens:
        _aguardar_imagem(url)
        r = requests.post(f"{base}/media", data={
            "image_url": url, "is_carousel_item": "true", "access_token": token
        }, timeout=60)
        if not r.ok:
            print("Resposta Instagram /media (item):", r.status_code, r.text)
        r.raise_for_status()
        filhos.append(r.json()["id"])
    r = requests.post(f"{base}/media", data={
        "media_type": "CAROUSEL",
        "children": ",".join(filhos),
        "caption": legenda,
        "access_token": token
    }, timeout=60)
    if not r.ok:
        print("Resposta Instagram /media (carrossel):", r.status_code, r.text)
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
        print("Resposta Instagram /media_publish (carrossel):", r.status_code, r.text)
    r.raise_for_status()
    print("Carrossel publicado! ID:", r.json().get("id"))


def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "diario"
    raw_base = os.environ.get("REPO_RAW_BASE", "").rstrip("/")
    hoje = datetime.date.today()
    if modo == "carrossel":
        urls = []
        n = len(CIDADES)
        for i, cidade in enumerate(CIDADES, start=1):
            d = buscar_previsao(cidade["lat"], cidade["lon"])
            arquivo = f"imagens/{cidade['hashtag']}-carrossel-{hoje.isoformat()}.png"
            card_carrossel(cidade, d, arquivo, i, n + 1)
            print(f"Slide gerado: {arquivo}")
            if raw_base:
                urls.append(f"{raw_base}/{arquivo}")
        arquivo_prov = f"imagens/provocacao-carrossel-{hoje.isoformat()}.png"
        card_provocacao(arquivo_prov)
        print(f"Slide gerado: {arquivo_prov}")
        if raw_base:
            urls.append(f"{raw_base}/{arquivo_prov}")
        legenda = ("\u2600\ufe0f Bom dia, Sul Fluminense!\n\n"
                   f"A previs\u00e3o de hoje ({hoje.day}/{hoje.month}) para as principais cidades da regi\u00e3o:\n\n"
                   "\U0001F4CD Volta Redonda \u2022 Porto Real \u2022 Barra Mansa \u2022 Resende\n\n"
                   "Arrasta para o lado para ver a sua cidade \u2192\n"
                   "Faltou a sua cidade? Comenta aqui que a gente inclui! \U0001F447\n\n"
                   "\U0001F4F8 Manda no Direct sua foto ou v\u00eddeo do tempo a\u00ed na sua cidade que a gente publica no perfil! \U0001F64C\n\n"
                   "Siga @previsaovr para receber todos os dias \U0001F4F2\n\n"
                   "#previsaodotempo #sulfluminense #voltaredonda #portoreal #barramansa #resende #clima #rj #bomdia")
        if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
            publicar_carrossel(urls, legenda)
        else:
            print("Sem credenciais \u2014 apenas os slides foram gerados.")
            print("Legenda:\n", legenda)
        return
    if modo == "panorama":
        ref = CIDADES[0]  # Volta Redonda como referencia regional
        d = buscar_previsao(ref["lat"], ref["lon"])
        frase, resumo = montar_panorama(d)
        arquivo = f"imagens/panorama-{hoje.isoformat()}.png"
        card_panorama(d, frase, arquivo)
        print(f"Card panorama gerado: {arquivo}")
        legenda = ("\U0001F4C5 Panorama da semana no Sul Fluminense!\n\n"
                   f"{frase}.\n\n"
                   "E a\u00ed na SUA cidade, como est\u00e1 o tempo hoje? Comenta aqui! \U0001F447\n\n"
                   "Siga @previsaovr para o resumo todos os dias \U0001F4F2\n\n"
                   "#previsaodotempo #sulfluminense #clima #rj #voltaredonda #tempo")
        if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
            url_card = f"{raw_base}/{arquivo}"
            publicar_instagram(url_card, legenda)
        else:
            print("Sem credenciais \u2014 apenas a imagem foi gerada.")
            print("Legenda:\n", legenda)
        return
    for cidade in CIDADES:
        d = buscar_previsao(cidade["lat"], cidade["lon"])
        slug = cidade["hashtag"]
        nome_curto = cidade["nome"].split(" -")[0]
        arquivo = f"imagens/{slug}-{modo}-{hoje.isoformat()}.png"
        if modo == "amanha":
            cond, maxi, mini, chuva = card_amanha(cidade, d, arquivo)
            amanha = hoje + datetime.timedelta(days=1)
            dica = "J\u00e1 deixe o guarda-chuva separado! \u2614" if chuva >= 60 else "Pode planejar o dia tranquilo! \U0001f60e"
            legenda = (f"\U0001f319 Boa noite, {nome_curto}!\n\n"
                       f"Amanh\u00e3 ({DIAS_LONGO[amanha.weekday()]}, {amanha.day}/{amanha.month}):\n"
                       f"{cond} \u2022 M\u00e1x {maxi}\u00b0 / M\u00edn {mini}\u00b0 \u2022 {chuva}% de chance de chuva\n\n"
                       f"{dica}\n\n"
                       f"Amanh\u00e3 \u00e0s 8h tem atualiza\u00e7\u00e3o por aqui \U0001f4f2\n\n"
                       f"#previsaodotempo #{slug} #clima #boanoite")
        elif modo == "angra":
            d_angra = buscar_previsao(ANGRA["lat"], ANGRA["lon"])
            arquivo = f"imagens/{ANGRA['hashtag']}-angra-{hoje.isoformat()}.png"
            cond, maxi, mini, chuva = card_angra(d_angra, arquivo)
            dica = "Leve a capa de chuva! \u2614" if chuva >= 60 else "Bora pra praia! \U0001f30a"
            legenda = ("VAI PRA ANGRA AMANH\u00c3? \U0001f3dd\ufe0f\n\n"
                       "Confere a previs\u00e3o de s\u00e1bado em Angra dos Reis antes de pegar a estrada!\n\n"
                       f"{cond} \u2022 M\u00e1x {maxi}\u00b0 / M\u00edn {mini}\u00b0 \u2022 {chuva}% de chance de chuva\n"
                       f"{dica}\n\n"
                       "Marca a galera da viagem \U0001f447\n\n"
                       "#angradosreis #litoral #fimdesemana #previsaodotempo #rj")
            print(f"Card Angra gerado: {arquivo}")
            if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
                url_card = f"{raw_base}/{arquivo}"
                publicar_instagram(url_card, legenda)
                publicar_story(url_card)
            else:
                print("Sem credenciais \u2014 apenas a imagem foi gerada.")
                print("Legenda:\n", legenda)
            continue
        elif modo == "semanal":
            linhas = card_semanal(cidade, d, arquivo)
            legenda = (f"\U0001f5d3\ufe0f Previs\u00e3o da semana em {cidade['nome']}!\n\n"
                       + "\n".join(linhas)
                       + "\n\nSalve este post e marque algu\u00e9m da cidade! \U0001f4cd"
                       + f"\n\n#previsaodotempo #{slug} #clima #tempo")
        else:
            cond, maxi, mini, chuva = card_diario(cidade, d, arquivo)
            dica = "Leve o guarda-chuva! \u2614" if chuva >= 60 else "Aproveite o dia! \U0001f60e"
            legenda = (f"\u2600\ufe0f Bom dia, {nome_curto}!\n\n"
                       f"Previs\u00e3o de hoje ({hoje.day}/{hoje.month}):\n"
                       f"{cond} \u2022 M\u00e1x {maxi}\u00b0 / M\u00edn {mini}\u00b0 \u2022 {chuva}% de chance de chuva\n\n"
                       f"Vai sair de casa? {dica}\n\n"
                       f"Siga @previsaovr para receber todos os dias \U0001f4f2\n\n"
                       f"#previsaodotempo #{slug} #clima #bomdia")
        print(f"Card gerado: {arquivo}")
        if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
            url_card = f"{raw_base}/{arquivo}"
            publicar_instagram(url_card, legenda)
            publicar_story(url_card)
        else:
            print("Sem credenciais \u2014 apenas a imagem foi gerada.")
            print("Legenda:\n", legenda)


if __name__ == "__main__":
    main()
