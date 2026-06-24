# Bloco 3 (alternativa) — Hospedando o bot @previsaovr no Google Cloud (Always Free)

O Oracle Cloud exige CNPJ no Brasil. O **Google Cloud** nao exige: aceita cadastro de
pessoa fisica com cartao (so validacao). Ele oferece uma VM **e2-micro** no tier
**Always Free** (gratis para sempre, dentro dos limites). Este guia poe o `alerta.py`
rodando 24/7 com polling a cada **10 minutos**.

> **Atencao:** Criar a conta, validar o cartao, gerar a chave SSH e colar os tokens
> sao etapas SUAS (marcadas com (VOCE)). O assistente nunca insere credenciais.

> **Limite Always Free da e2-micro:** so e gratuita nas regioes dos EUA
> **us-west1 (Oregon)**, **us-central1 (Iowa)** ou **us-east1 (Carolina do Sul)**.
> Fora delas, a VM e cobrada. Para o nosso bot (so chamadas de saida), a regiao dos
> EUA nao atrapalha em nada.

---

## Passo 9 — Criar a conta (VOCE)

1. Acesse https://cloud.google.com/free e clique em **Comece gratuitamente**.
2. Faca login com uma conta Google e aceite os termos.
3. Informe os dados e **valide um cartao** (o Google faz uma autorizacao temporaria
   de ~R$5 que e estornada; o tier Always Free nao cobra enquanto voce ficar nos limites).
4. Voce ganha tambem um credito inicial de US$300 por 90 dias — mas a e2-micro ja e
   Always Free, entao nao depende desse credito.

---

## Passo 10 — Criar a VM e2-micro (VOCE clica)

1. No console: **Menu (tres tracinhos) > Compute Engine > VM instances**.
   (Na primeira vez, clique para habilitar a Compute Engine API e aguarde 1-2 min.)
2. Clique **Create instance** e configure:
   - **Name:** `previsaovr`
   - **Region:** `us-west1` (Oregon) ou `us-central1` (Iowa) — uma das Always Free.
   - **Machine configuration > Series:** E2; **Machine type:** `e2-micro`.
   - **Boot disk:** clique em Change > **Ubuntu** > **Ubuntu 22.04 LTS**;
     tipo de disco **Standard persistent disk**, tamanho **30 GB** (limite do free tier).
   - **Firewall:** NAO precisa marcar "Allow HTTP/HTTPS" (o bot so faz saida).
3. Clique **Create**. Anote o **IP externo** que aparece na lista de VMs.

> O acesso SSH pelo Google ja vem liberado por padrao. Voce nao precisa abrir portas.

---

## Passo 11 — Conectar e instalar (VOCE roda os comandos)

### 11.1 Conectar via SSH (o jeito mais facil)

Na lista de VMs, na linha da `previsaovr`, clique no botao **SSH**. O Google abre um
terminal no navegador, ja autenticado — nao precisa gerar chave manualmente.

### 11.2 Rodar o instalador

No terminal SSH:

```bash
git clone https://github.com/pabloramoa-dev/previsaovr-instagram.git
cd previsaovr-instagram
bash deploy/setup.sh
```

(Os mesmos scripts do guia Oracle servem aqui — sao genericos para Ubuntu.)

### 11.3 Preencher os tokens (VOCE)

```bash
nano .env
```

Preencha (mesmos valores dos Secrets do GitHub):

| Variavel          | O que e |
|-------------------|---------|
| `IG_USER_ID`      | ID numerico da conta Instagram |
| `IG_ACCESS_TOKEN` | Token de longa duracao da Graph API |
| `GITHUB_REPO`     | `pabloramoa-dev/previsaovr-instagram` (ja preenchido) |
| `GITHUB_TOKEN`    | Fine-grained PAT com **Contents: Read and write** so neste repo |

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`. O `.env` fica so na VM (esta no `.gitignore`).

### 11.4 Instalar o servico (roda a cada 10 min)

```bash
bash deploy/install-service.sh
```

Cria um **systemd timer** que executa `alerta.py` a cada 10 minutos, com
`git pull --rebase` automatico antes de cada execucao e persistencia apos reboot.

---

## Comandos uteis

```bash
systemctl list-timers previsaovr-alerta.timer   # proximas execucoes
journalctl -u previsaovr-alerta.service -f       # logs ao vivo
sudo systemctl start previsaovr-alerta.service   # rodar agora
sudo systemctl stop previsaovr-alerta.timer      # pausar
```

---

## Atencao para nao ser cobrado

- Use **e2-micro** numa das 3 regioes Always Free (us-west1/us-central1/us-east1).
- Disco **<= 30 GB Standard**. Nao adicione IP estatico pago nem trafego de saida alto
  (o bot usa pouquissimo). Configure um **orcamento/alerta de faturamento** em
  Billing > Budgets & alerts para ser avisado se algo passar de US$1.

---

## Resumo: o que e seu vs. o que ja esta pronto

**VOCE faz:** criar a conta Google Cloud, validar o cartao, criar a VM e2-micro,
clicar em SSH, rodar os 2 scripts e colar os tokens no `.env`.

**Ja preparado neste repo:** `deploy/setup.sh`, `deploy/install-service.sh`,
`deploy/.env.example` e este guia. Funciona igual no GCP, na Oracle ou em qualquer VM Ubuntu.
