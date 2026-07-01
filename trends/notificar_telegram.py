# trends/notificar_telegram.py
"""Envia a lista de trends ao Telegram com botoes inline (aprovar/descartar).
Reaproveita os secrets TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID ja existentes."""
import os, json, requests

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
API = "https://api.telegram.org/bot" + TOKEN
FILA = os.path.join(os.path.dirname(__file__), "fila_pendente.json")


def notificar():
    with open(FILA, encoding="utf-8") as f:
        itens = json.load(f).get("itens", [])
    if not itens:
        print("Nenhum trend para enviar.")
        return
    for i, it in enumerate(itens):
        texto = (
            "*" + it.get("titulo", "(sem titulo)") + "*\n\n"
            + it.get("resumo_curto", "") + "\n\n"
            + "Gancho: " + it.get("gancho_local", "") + "\n"
            + it.get("url", "")
        )
        botoes = {"inline_keyboard": [[
            {"text": "Aprovar", "callback_data": "aprovar|" + str(i)},
            {"text": "Descartar", "callback_data": "descartar|" + str(i)},
        ]]}
        r = requests.post(API + "/sendMessage", json={
            "chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown",
            "reply_markup": botoes,
        }, timeout=30)
        r.raise_for_status()
    print(str(len(itens)) + " itens enviados ao Telegram.")


if __name__ == "__main__":
    notificar()
