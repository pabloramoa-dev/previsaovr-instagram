# trends/buscar_trends.py
"""Busca trending topics relevantes p/ Sul Fluminense (RJ) e Brasil via Anthropic API + web_search.
Salva em trends/fila_pendente.json. NAO faz scraping de Instagram/TikTok; usa web como inspiracao de pauta."""
import os, json, datetime, anthropic

MODEL = "claude-haiku-4-5-20251001"
WEB_SEARCH_TOOL = {"type": "web_search_20250305", "name": "web_search", "max_uses": 5}
ARQUIVO_SAIDA = os.path.join(os.path.dirname(__file__), "fila_pendente.json")

PROMPT = """Voce e assistente de pauta da pagina @previsaosulflu (Sul Fluminense - RJ:
Volta Redonda, Barra Mansa, Resende, Porto Real, Angra dos Reis).
Busque na web ate 8 assuntos EM ALTA hoje que possam virar pauta, priorizando noticias
do Sul Fluminense/RJ e assuntos nacionais com gancho local. Evite politica partidaria,
tragedias sensiveis sem utilidade publica e nada que exija repostar material de terceiros.
Crie um gancho ORIGINAL (nao copie manchetes). Responda APENAS com JSON:
{"itens":[{"titulo":"","resumo_curto":"","gancho_local":"","fonte":"","url":""}]}"""


def buscar_trends():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    resp = client.messages.create(
        model=MODEL, max_tokens=2000, tools=[WEB_SEARCH_TOOL],
        messages=[{"role": "user", "content": PROMPT}],
    )
    texto = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    ini, fim = texto.find("{"), texto.rfind("}")
    if ini == -1 or fim == -1:
        raise RuntimeError("Sem JSON na resposta:\n" + texto)
    itens = json.loads(texto[ini:fim + 1]).get("itens", [])
    saida = {"gerado_em": datetime.datetime.now().isoformat(timespec="seconds"), "itens": itens}
    with open(ARQUIVO_SAIDA, "w", encoding="utf-8") as f:
        json.dump(saida, f, ensure_ascii=False, indent=2)
    print(str(len(itens)) + " trends salvos.")
    return saida


if __name__ == "__main__":
    buscar_trends()
