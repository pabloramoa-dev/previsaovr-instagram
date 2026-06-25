#!/usr/bin/env python3
"""
Bot de previsÃ£o do tempo para Instagram (@previsaovr).
API: Instagram Login (graph.instagram.com) â tokens gerados no painel
"ConfiguraÃ§Ã£o da API com Login do Instagram".

Modos:
  python bot.py diario   -> card de HOJE (poshtar Ã s 8h)
  python bot.py amanha   -> card de AMANHÃ (postar Ã s 20h da vÃ©spera)
  python bot.py semanal  -> card da SEMANA (domingo de manhÃ£)

VariÃ¡veis de ambiente (Secrets do GitHub):
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
# Cidade do post temÃ¡tico de sexta Ã  noite (previsÃ£o de sÃ¡bado)
ANGRA = {"nome": "Angra dos Reis - RJ", "lat": -23.0067, "lon": -44.3181, "hashtag": "angradosreis"}

W, H = 1080, 1920
DIAS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÃB", "DOM"]
DIAS_LONGO = ["segunda-feira", "terÃ§a-feira", "quarta-feira", "quinta-feira",
              "sexta-feira", "sÃ¡bado", "domingo"]
MESES = ["janeiro", "fevereiro", "marÃ§o", "abril", "maio", "junho",
         "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def fonte(tam, bold=True):
    nome = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, nome), tam)


def tempo_info(code):
    if code == 0: return ("CÃ©u limpo", (29, 111, 209), (95, 182, 242))
    if code <= 2: return ("Parcialmente nublado", (46, 124, 199), (127, 189, 232))
    if code == 3: return ("Nublado", (78, 100, 120), (142, 163, 181))
    if code <= 48: return ("NÃ©voa", (93, 112, 127), (159, 178, 191))
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
    """Card de HOJE â postado Ã s 8h, com temperatura atual."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["current"]["weather_code"])
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    hoje = datetime.date.today()
    centro(dr, "PREVISÃO DE HOJE", 120, fonte(40))
    centro(dr, cidade["nome"].upper(), 180, fonte(74))
    centro(dr, f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month-1]}", 265, fonte(40, False), (235, 242, 248))
    centro(dr, f"{round(d['current']['temperature_2m'])}Â°", 560, fonte(250))
    centro(dr, cond, 900, fonte(54, False))
    maxi = round(d["daily"]["temperature_2m_max"][0])
    mini = round(d["daily"]["temperature_2m_min"][0])
    chuva = d["daily"]["precipitation_probability_max"][0]
    umid = round(d["current"]["relative_humidity_2m"])
    dr = blocos_info(img, dr, [(f"{maxi}Â°", "MÃ¡xima"), (f"{mini}Â°", "MÃ­nima"),
                               (f"{chuva}%", "Chuva"), (f"{umid}%", "Umidade")])
    centro(dr, "Siga @previsaovr â¢ todos os dias", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_amanha(cidade, d, caminho):
    """Card de AMANHÃ â postado Ã s 20h da vÃ©spera, usa dados do dia seguinte."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][1])
    # tom levemente mais escuro: clima de "noite anterior"
    c1 = tuple(max(0, c - 35) for c in c1)
    c2 = tuple(max(0, c - 25) for c in c2)
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    amanha = datetime.date.today() + datetime.timedelta(days=1)
    centro(dr, "COMO SERÃ AMANHÃ?", 120, fonte(40))
    centro(dr, cidade["nome"].upper(), 180, fonte(74))
    centro(dr, f"{DIAS_LONGO[amanha.weekday()].capitalize()}, {amanha.day} de {MESES[amanha.month-1]}",
              265, fonte(40, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][1])
    mini = round(d["daily"]["temperature_2m_min"][1])
    chuva = d["daily"]["precipitation_probability_max"][1]
    centro(dr, f"{maxi}Â°", 540, fonte(230))
    centro(dr, "mÃ¡xima prevista", 850, fonte(40, False), (220, 230, 240))
    centro(dr, cond, 920, fonte(54, False))
    dr = blocos_info(img, dr, [(f"{maxi}Â°", "MÃ¡xima"), (f"{mini}Â°", "MÃ­nima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, "AmanhÃ£ Ã s 8h tem atualizaÃ§Ã£o â¢ @previsaovr", 1800, fonte(36), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return cond, maxi, mini, chuva


def card_semanal(cidade, d, caminho):
    img = Image.new("RGBA", (W, H))
    gradiente(img, (22, 50, 76), (61, 106, 147))
    dr = ImageDraw.Draw(img)
    centro(dr, "PREVISÃO DA SEMANA", 120, fonte(40))
    centro(dr, cidade["nome"].upper(), 180, fonte(74))
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
        dr.text((800, y + 35), f"{maxi}Â°", font=fonte(44), fill=(255, 255, 255))
        dr.text((910, y + 35), f"{mini}Â°", font=fonte(44), fill=(180, 200, 216))
        linhas.append(f"{rotulo.title()}: {cond}, {mini}Â°â{maxi}Â° (chuva {chuva}%)")
    centro(dr, "Siga @previsaovr â¢ previsÃ£o diÃ¡ria", 1800, fonte(30), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return linhas


def card_carrossel(cidade, d, caminho, posicao, total):
    """Slide de uma cidade dentro do carrossel diario (postado as 6h30)."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][0])
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    hoje = datetime.date.today()
    centro(dr, "PREVIS\u00c3O DE HOJE", 120, fonte(40))
    centro(dr, cidade["nome"].upper(), 188, fonte(70))
    centro(dr, f"{DIAS[hoje.weekday()]}, {hoje.day} de {MESES[hoje.month-1]}", 275, fonte(38, False), (235, 242, 248))
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


def card_angra(d, caminho):
    """Post de sexta Ã  noite: previsÃ£o de SÃBADO para Angra dos Reis."""
    img = Image.new("RGBA", (W, H))
    cond, c1, c2 = tempo_info(d["daily"]["weather_code"][1])
    # tom litorÃ¢neo: azul-mar mais vivo
    c1 = (8, 78, 110)
    c2 = (20, 140, 180)
    gradiente(img, c1, c2)
    dr = ImageDraw.Draw(img)
    amanha = datetime.date.today() + datetime.timedelta(days=1)
    centro(dr, "VAI PRA ANGRA AMANHÃ?", 150, fonte(64))
    centro(dr, "Veja a previsÃ£o ð", 250, fonte(44, False), (255, 209, 102))
    centro(dr, "ANGRA DOS REIS", 420, fonte(70))
    centro(dr, f"{DIAS_LONGO[amanha.weekday()].capitalize()}, {amanha.day} de {MESES[amanha.month-1]}",
              510, fonte(38, False), (235, 242, 248))
    maxi = round(d["daily"]["temperature_2m_max"][1])
    mini = round(d["daily"]["temperature_2m_min"][1])
    chuva = d["daily"]["precipitation_probability_max"][1]
    centro(dr, f"{maxi}Â°", 640, fonte(230))
    centro(dr, cond, 950, fonte(54, False))
    dr = blocos_info(img, dr, [(f"{maxi}Â°", "MÃ¡xima"), (f"{mini}Â°", "MÃ­nima"),
                               (f"{chuva}%", "Chuva")])
    centro(dr, "Bom fim de semana! ðï¸  @previsaovr", 1800, fonte(36), (230, 238, 246))
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
    for cidade in CIDADES:
        d = buscar_previsao(cidade["lat"], cidade["lon"])
        slug = cidade["hashtag"]
        nome_curto = cidade["nome"].split(" -")[0]
        arquivo = f"imagens/{slug}-{modo}-{hoje.isoformat()}.png"
        if modo == "amanha":
            cond, maxi, mini, chuva = card_amanha(cidade, d, arquivo)
            amanha = hoje + datetime.timedelta(days=1)
            dica = "JÃ¡ deixe o guarda-chuva separado! â" if chuva >= 60 else "Pode planejar o dia tranquilo! ð"
            legenda = (f"ð Boa noite, {nome_curto}!\n\n"
                       f"AmanhÃ£ ({DIAS_LONGO[amanha.weekday()]}, {amanha.day}/{amanha.month}):\n"
                       f"{cond} â¢ MÃ¡x {maxi}Â° / MÃ­n {mini}Â° â¢ {chuva}% de chance de chuva\n\n"
                       f"{dica}\n\n"
                       f"AmanhÃ£ Ã s 8h tem atualizaÃ§Ã£o por aqui ð²\n\n"
                       f"#previsaodotempo #{slug} #clima #boanoite")
        elif modo == "angra":
            d_angra = buscar_previsao(ANGRA["lat"], ANGRA["lon"])
            arquivo = f"imagens/{ANGRA['hashtag']}-angra-{hoje.isoformat()}.png"
            cond, maxi, mini, chuva = card_angra(d_angra, arquivo)
            dica = "Leve a capa de chuva! â" if chuva >= 60 else "Bora pra praia! ð"
            legenda = ("VAI PRA ANGRA AMANHÃ? ðï¸\n\n"
                       "Confere a previsÃ£o de sÃ¡bado em Angra dos Reis antes de pegar a estrada!\n\n"
                       f"{cond} â¢ MÃ¡x {maxi}Â° / MÃ­n {mini}Â° â¢ {chuva}% de chance de chuva\n"
                       f"{dica}\n\n"
                       "Marca a galera da viagem ð\n\n"
                       "#angradosreis #litoral #fimdesemana #previsaodotempo #rj")
            print(f"Card Angra gerado: {arquivo}")
            if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
                url_card = f"{raw_base}/{arquivo}"
                publicar_instagram(url_card, legenda)
                publicar_story(url_card)
            else:
                print("Sem credenciais â apenas a imagem foi gerada.")
                print("Legenda:\n", legenda)
            continue
        elif modo == "semanal":
            linhas = card_semanal(cidade, d, arquivo)
            legenda = (f"ðï¸ PrevisÃ£o da semana em {cidade['nome']}!\n\n"
                       + "\n".join(linhas)
                       + "\n\nSalve este post e marque alguÃ©m da cidade! ð"
                       + f"\n\n#previsaodotempo #{slug} #clima #tempo")
        else:
            cond, maxi, mini, chuva = card_diario(cidade, d, arquivo)
            dica = "Leve o guarda-chuva! â" if chuva >= 60 else "Aproveite o dia! ð"
            legenda = (f"âï¸ Bom dia, {nome_curto}!\n\n"
                       f"PrevisÃ£o de hoje ({hoje.day}/{hoje.month}):\n"
                       f"{cond} â¢ MÃ¡x {maxi}Â° / MÃ­n {mini}Â° â¢ {chuva}% de chance de chuva\n\n"
                       f"Vai sair de casa? {dica}\n\n"
                       f"Siga @previsaovr para receber todos os dias ð²\n\n"
                       f"#previsaodotempo #{slug} #clima #bomdia")
        print(f"Card gerado: {arquivo}")
        if raw_base and os.environ.get("IG_ACCESS_TOKEN"):
            url_card = f"{raw_base}/{arquivo}"
            publicar_instagram(url_card, legenda)
            publicar_story(url_card)
        else:
            print("Sem credenciais â apenas a imagem foi gerada.")
            print("Legenda:\n", legenda)


if __name__ == "__main__":
    main()
