# trends/processar_aprovacoes.py
"""Le os cliques dos botoes no Telegram (getUpdates) e aplica dupla confirmacao:
aprovar trend -> gera previa e reenvia -> aprovar previa (publicar) -> publica no Instagram.
Reaproveita secrets TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, IG_USER_ID, IG_ACCESS_TOKEN."""
import os, json, datetime, time, requests
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from gerar_post import gerar
import bot
from bot import publicar_instagram


def _aguardar_imagem_robusto(url_imagem):
    """Substitui a versao original: usa GET + cache-busting p/ evitar 404 cacheado pelo CDN."""
    for tentativa in range(20):
        try:
            busting = url_imagem + "?v=" + str(int(time.time()))
            r = requests.get(busting, timeout=20, allow_redirects=True)
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("image"):
                return
            print("Tentativa " + str(tentativa + 1) + ": status " + str(r.status_code))
        except requests.RequestException as e:
            print("Tentativa " + str(tentativa + 1) + ": erro -> " + str(e))
        time.sleep(8)
    raise RuntimeError("Imagem nao ficou acessivel a tempo: " + url_imagem)


# Aplica a correcao sem alterar o bot.py original
bot._aguardar_imagem = _aguardar_imagem_robusto

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
RAW_BASE = os.environ.get("REPO_RAW_BASE", "").rstrip("/")
API = "https://api.telegram.org/bot" + TOKEN
DIR = os.path.dirname(__file__)
FILA = os.path.join(DIR, "fila_pendente.json")
OFFSET = os.path.join(DIR, "_offset.json")


def _get_updates():
    off = 0
    if os.path.exists(OFFSET):
        off = json.load(open(OFFSET)).get("offset", 0)
    r = requests.get(API + "/getUpdates", params={"offset": off, "timeout": 0}, timeout=30).json()
    return r.get("result", [])


def _save_offset(update_id):
    json.dump({"offset": update_id + 1}, open(OFFSET, "w"))


def _answer(cb_id, texto):
    requests.post(API + "/answerCallbackQuery", json={"callback_query_id": cb_id, "text": texto}, timeout=15)


def _send(texto):
    requests.post(API + "/sendMessage", json={"chat_id": CHAT_ID, "text": texto, "parse_mode": "Markdown"}, timeout=30)


def _send_foto(caminho, legenda, botoes):
    with open(caminho, "rb") as fh:
        requests.post(API + "/sendPhoto",
                      data={"chat_id": CHAT_ID, "caption": legenda, "reply_markup": json.dumps(botoes)},
                      files={"photo": fh}, timeout=60)


def _itens():
    if os.path.exists(FILA):
        return json.load(open(FILA, encoding="utf-8")).get("itens", [])
    return []


def processar():
    itens = _itens()
    for upd in _get_updates():
        _save_offset(upd["update_id"])
        cb = upd.get("callback_query")
        if not cb:
            continue
        acao, _, idx = cb.get("data", "").partition("|")
        try:
            it = itens[int(idx)]
        except (ValueError, IndexError):
            _answer(cb["id"], "Item indisponivel (fila renovada).")
            continue

        if acao == "aprovar":
            caminho = gerar(it["titulo"], it.get("gancho_local", ""))
            botoes = {"inline_keyboard": [[
                {"text": "Publicar", "callback_data": "publicar|" + idx},
                {"text": "Cancelar", "callback_data": "cancelar|" + idx},
            ]]}
            _send_foto(caminho, "Previa do post:\n\n" + it.get("gancho_local", ""), botoes)
            _answer(cb["id"], "Previa gerada!")

        elif acao == "publicar":
            hoje = datetime.date.today().isoformat()
            url = RAW_BASE + "/imagens/trend-" + hoje + ".png"
            legenda = it.get("gancho_local", "") + "\n\n@previsaosulflu"
            publicar_instagram(url, legenda)
            _send("Publicado no Instagram!")
            _answer(cb["id"], "Publicado!")

        elif acao in ("descartar", "cancelar"):
            _answer(cb["id"], "Ok, descartado.")


if __name__ == "__main__":
    processar()
