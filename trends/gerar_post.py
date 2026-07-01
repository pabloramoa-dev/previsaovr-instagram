# trends/gerar_post.py
"""Gera o card visual proprio do post de trend (independente do clima).
Reaproveita os helpers visuais do bot.py para manter a identidade da pagina."""
import os, sys, datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from bot import fonte, gradiente, caixa, centro, W, H
from PIL import Image, ImageDraw

PASTA_IMG = "imagens"


def _quebrar(dr, texto, f, largura_max):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if dr.textlength(teste, font=f) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def card_trend(titulo, gancho, caminho):
    img = Image.new("RGBA", (W, H))
    gradiente(img, (28, 47, 68), (70, 98, 127))
    dr = ImageDraw.Draw(img)
    centro(dr, "EM ALTA HOJE", 200, fonte(44))
    linhas = _quebrar(dr, titulo.upper(), fonte(72), W - 160)
    y = 520 - (len(linhas) * 90) // 2
    for ln in linhas:
        centro(dr, ln, y, fonte(72))
        y += 92
    caixa(img, [80, 1150, W - 80, 1600], 30, 55)
    dr = ImageDraw.Draw(img)
    yg = 1210
    for ln in _quebrar(dr, gancho, fonte(40, False), W - 240):
        centro(dr, ln, yg, fonte(40, False), (230, 238, 246))
        yg += 56
    centro(dr, "@previsaosulflu", 1780, fonte(38), (230, 238, 246))
    img.convert("RGB").save(caminho, "PNG")
    return caminho


def gerar(titulo, gancho):
    hoje = datetime.date.today().isoformat()
    caminho = PASTA_IMG + "/trend-" + hoje + ".png"
    card_trend(titulo, gancho, caminho)
    print("Card de trend gerado: " + caminho)
    return caminho
