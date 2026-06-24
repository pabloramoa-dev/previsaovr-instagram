#!/usr/bin/env python3
"""
Modulo Telegram para @previsaovr.
Envia notificacoes de alertas climaticos para um canal/grupo do Telegram.
Variaveis de ambiente necessarias:
  TELEGRAM_BOT_TOKEN  -> token do bot (gerado pelo BotFather)
  TELEGRAM_CHAT_ID    -> ID do canal/grupo destino (ex.: @previsaovr ou -100xxxxxxx)
Uso standalone:
  python telegram_bot.py --teste   # envia uma mensagem de teste
"""
import os
import sys
import time
import requests

# -------------------------------------------------------------------
# Config
API_BASE = "https://api.telegram.org/bot{token}/{method}"

EMOJI_NIVEL = {1: "\u26a0\ufe0f", 2: "\U0001F7E0", 3: "\U0001F534"}
EMOJI_TIPO  = {"chuva": "\U0001F327\ufe0f", "vento": "\U0001F4A8", "calor": "\U0001F525", "frio": "\u2744\ufe0f"}
ROTULO_NIVEL = {1: "ATENCAO", 2: "ALERTA", 3: "ALERTA GRAVE"}

# -------------------------------------------------------------------
def _get_creds():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat  = os.environ.get("TELEGRAM_CHAT_ID",   "").strip()
    return token, chat


def _post(token, method, **kwargs):
    """Envia requisicao para a Bot API do Telegram com retry simples."""
    url = API_BASE.format(token=token, method=method)
    for tentativa in range(3):
        try:
            r = requests.post(url, timeout=30, **kwargs)
            if r.ok:
                return r.json()
            print(f"[Telegram] {method} falhou ({r.status_code}): {r.text[:200]}")
        except requests.RequestException as e:
            print(f"[Telegram] {method} erro de rede (tentativa {tentativa+1}): {e}")
        time.sleep(3)
    return None


# -------------------------------------------------------------------
def formatar_mensagem(cidade_nome, evento):
    """Formata a mensagem HTML para o Telegram."""
    nivel   = evento["nivel"]
    tipo    = evento["tipo"]
    emoji_n = EMOJI_NIVEL.get(nivel, "\u26a0\ufe0f")
    emoji_t = EMOJI_TIPO.get(tipo, "\U0001F321\ufe0f")
    rotulo  = ROTULO_NIVEL.get(nivel, "ALERTA")
    nome    = cidade_nome.split(" -")[0]

    linhas = [
        f"{emoji_n} <b>{rotulo} CLIMATICO</b> {emoji_n}",
        f"{emoji_t} <b>{evento['titulo']}</b>",
        f"\U0001F4CD {nome}",
        "",
        evento["descricao"],
        "",
        "\U0001F4F2 <a href=\"https://www.instagram.com/previsaovr/\">Veja o post completo no Instagram</a>",
        "",
        "\U0001F514 <i>Ative as notificacoes para nao perder nenhum alerta!</i>",
    ]
    return "\n".join(linhas)


def enviar_alerta(cidade_nome, evento, foto_path=None):
    """Envia um alerta climatico para o canal Telegram.
    Se foto_path for fornecido e existir, envia o card como imagem + legenda.
    Caso contrario, envia so o texto.
    Retorna True em caso de sucesso."""
    token, chat = _get_creds()
    if not token or not chat:
        print("[Telegram] Credenciais nao configuradas - notificacao ignorada.")
        return False

    mensagem = formatar_mensagem(cidade_nome, evento)

    # Tenta enviar com foto
    if foto_path and os.path.exists(foto_path):
        with open(foto_path, "rb") as f:
            resultado = _post(token, "sendPhoto",
                files={"photo": f},
                data={"chat_id": chat, "caption": mensagem,
                      "parse_mode": "HTML", "disable_notification": False})
        if resultado and resultado.get("ok"):
            print(f"[Telegram] Foto enviada para {chat}.")
            return True
        print("[Telegram] Falha ao enviar foto; tentando texto puro...")

    # Fallback: texto puro
    resultado = _post(token, "sendMessage",
        json={"chat_id": chat, "text": mensagem,
              "parse_mode": "HTML", "disable_web_page_preview": True})
    if resultado and resultado.get("ok"):
        print(f"[Telegram] Mensagem enviada para {chat}.")
        return True
    print("[Telegram] Falha ao enviar mensagem de texto.")
    return False


def enviar_resumo_diario(linhas_resumo):
    """Envia um resumo diario (lista de strings) para o canal.
    Usado opcionalmente no final do dia para informar quantos alertas foram emitidos."""
    token, chat = _get_creds()
    if not token or not chat:
        return False
    texto = "\U0001F4CA <b>Resumo de Alertas do Dia</b>\n\n" + "\n".join(linhas_resumo)
    resultado = _post(token, "sendMessage",
        json={"chat_id": chat, "text": texto,
              "parse_mode": "HTML", "disable_web_page_preview": True})
    return bool(resultado and resultado.get("ok"))


def enviar_mensagem_simples(texto):
    """Envia uma mensagem de texto simples para o canal (util para debug/admin)."""
    token, chat = _get_creds()
    if not token or not chat:
        return False
    resultado = _post(token, "sendMessage",
        json={"chat_id": chat, "text": texto, "parse_mode": "HTML"})
    return bool(resultado and resultado.get("ok"))


# -------------------------------------------------------------------
if __name__ == "__main__":
    if "--teste" in sys.argv:
        cidade_fake = "Volta Redonda - RJ"
        evento_fake = {
            "tipo": "chuva", "nivel": 2, "valor": 18,
            "titulo": "CHUVA FORTE A CAMINHO",
            "descricao": "Ate 18 mm de chuva nas proximas horas em Volta Redonda. Fique atento.",
        }
        print("[Telegram] Enviando mensagem de teste...")
        ok = enviar_alerta(cidade_fake, evento_fake)
        print("[Telegram] Resultado:", "OK" if ok else "FALHOU")
        sys.exit(0 if ok else 1)
    print("Use: python telegram_bot.py --teste")
