#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reel.py - converte o card de alerta (PNG) em um Reel vertical (MP4 9:16)
e publica no Instagram via Graph API (media_type=REELS).

Uso como modulo:
    from reel import gerar_reel, publicar_reel
    gerar_reel("imagens/alerta.png", "imagens/alerta.mp4")
    publicar_reel("https://raw.githubusercontent.com/.../alerta.mp4", legenda)

Uso direto (teste local, so gera o video a partir de um PNG):
    python reel.py --teste imagens/exemplo-alerta.png

Requisitos: ffmpeg no PATH (ja vem nos runners do GitHub Actions e na VM
via deploy/setup.sh). O MP4 precisa estar publico (commitado no repo) antes
de publicar, pois o Instagram baixa o video pela URL.
"""
import os
import sys
import time
import shutil
import subprocess

import requests

# ------------------------------------------------------------------
# Geracao do video com ffmpeg
# ------------------------------------------------------------------
LARGURA, ALTURA = 1080, 1920   # 9:16
DURACAO_S = 6                  # duracao do Reel em segundos
FPS = 30


def ffmpeg_ok():
    """Retorna True se o ffmpeg estiver disponivel no PATH."""
    return shutil.which("ffmpeg") is not None


def gerar_reel(png_path, mp4_path, duracao=DURACAO_S):
    """
    Gera um MP4 vertical a partir de um PNG (o card de alerta).
    Efeito: leve zoom-in (Ken Burns) + fade in/out. Inclui uma faixa
    de audio silenciosa, pois o Instagram exige stream de audio nos Reels.
    """
    if not ffmpeg_ok():
        raise RuntimeError("ffmpeg nao encontrado no PATH.")

    total_frames = int(duracao * FPS)
    # zoompan faz o zoom lento; escala/pad garantem exatamente 1080x1920.
    vf = (
        f"scale={LARGURA}:-2,"
        f"zoompan=z='min(zoom+0.0008,1.12)':d={total_frames}:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={LARGURA}x{ALTURA}:fps={FPS},"
        f"fade=t=in:st=0:d=0.6,fade=t=out:st={duracao-0.6}:d=0.6,"
        f"format=yuv420p"
    )
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", png_path,
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-t", str(duracao),
        "-vf", vf,
        "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-shortest",
        "-movflags", "+faststart",
        mp4_path,
    ]
    print(">>> ffmpeg:", " ".join(cmd))
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-2000:])
        raise RuntimeError("ffmpeg falhou ao gerar o Reel.")
    print(f">>> Reel gerado: {mp4_path}")
    return mp4_path


# ------------------------------------------------------------------
# Publicacao do Reel via Instagram Graph API
# ------------------------------------------------------------------
def publicar_reel(video_url, legenda, compartilhar_feed=True):
    """
    Publica um Reel a partir de uma URL publica de video.
    O fluxo e: cria container (media_type=REELS) -> aguarda processar
    -> media_publish.
    """
    ig_user = os.environ["IG_USER_ID"]
    token = os.environ["IG_ACCESS_TOKEN"]
    base = f"https://graph.instagram.com/v21.0/{ig_user}"

    dados = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": legenda,
        "share_to_feed": "true" if compartilhar_feed else "false",
        "access_token": token,
    }
    r = requests.post(f"{base}/media", data=dados, timeout=120)
    if not r.ok:
        print("Resposta /media (reel):", r.status_code, r.text)
    r.raise_for_status()
    container = r.json()["id"]

    # Reels demoram mais para processar; checa o status_code ate FINISHED.
    for tentativa in range(30):
        s = requests.get(
            f"https://graph.instagram.com/v21.0/{container}",
            params={"fields": "status_code,status", "access_token": token},
            timeout=30,
        ).json()
        code = s.get("status_code")
        print(f"   status do reel ({tentativa+1}):", code)
        if code == "FINISHED":
            break
        if code == "ERROR":
            raise RuntimeError(f"Processamento do Reel falhou: {s}")
        time.sleep(10)
    else:
        raise RuntimeError("Tempo esgotado aguardando o Reel processar.")

    r = requests.post(
        f"{base}/media_publish",
        data={"creation_id": container, "access_token": token},
        timeout=120,
    )
    if not r.ok:
        print("Resposta /media_publish (reel):", r.status_code, r.text)
    r.raise_for_status()
    rid = r.json().get("id")
    print("Reel publicado! ID:", rid)
    return rid


# ------------------------------------------------------------------
# Teste local: so gera o MP4 a partir de um PNG, sem publicar.
# ------------------------------------------------------------------
def _teste(png_path):
    saida = os.path.splitext(png_path)[0] + ".mp4"
    gerar_reel(png_path, saida)
    tam = os.path.getsize(saida) if os.path.exists(saida) else 0
    print(f">>> OK. {saida} ({tam} bytes)")


if __name__ == "__main__":
    if "--teste" in sys.argv:
        idx = sys.argv.index("--teste")
        png = sys.argv[idx + 1] if len(sys.argv) > idx + 1 else "imagens/exemplo-alerta.png"
        _teste(png)
    else:
        print("Use: python reel.py --teste CAMINHO_DO_PNG")
