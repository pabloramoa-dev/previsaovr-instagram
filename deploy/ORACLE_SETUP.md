# Bloco 3 — Hospedando o bot @previsaovr na Oracle Cloud (Always Free)

Este guia coloca o detector de alertas (`alerta.py`) rodando 24/7 numa VM gratuita
da Oracle Cloud, com polling a cada **10 minutos** (mais rapido que o GitHub Actions,
que tem fila e atrasos). O GitHub Actions continua valendo como backup/redundancia.

> **Atencao:** As etapas de criar conta, gerar chave SSH e colar tokens sao SUAS.
> O assistente nunca insere credenciais. Siga voce mesmo os passos marcados com (VOCE).

---

## Passo 9 — Criar a conta e a VM (VOCE)

1. Acesse https://www.oracle.com/cloud/free/ e crie a conta **Always Free**.
   - Precisa de um cartao para verificacao (nao ha cobranca no tier gratuito).
   - Escolha a regiao mais proxima (ex.: Brazil East (Sao Paulo) ou Brazil Southeast (Vinhedo)).
2. No console: **Compute > Instances > Create Instance**.
3. Configuracao recomendada (sempre gratuita):
   - **Image:** Canonical Ubuntu 22.04 (ou 24.04).
   - **Shape:** `VM.Standard.A1.Flex` (Ampere ARM) com 1 OCPU e 6 GB RAM
     — ou `VM.Standard.E2.1.Micro` (x86) se ARM estiver indisponivel.
4. Em **Add SSH keys**, escolha **Generate a key pair for me** e BAIXE a chave privada,
   ou cole sua propria chave publica. Guarde a chave privada com seguranca.
5. Em **Networking**, deixe criar uma VCN nova e marque **Assign a public IPv4 address**.
6. Clique **Create** e anote o **IP publico** da instancia.

> O alerta.py so faz chamadas de saida (Open-Meteo, Instagram, GitHub). Voce NAO precisa
> abrir portas de entrada alem do SSH (porta 22, que ja vem liberada).

---

## Passo 10 — Conectar e instalar (VOCE roda os comandos)

### 10.1 Conectar via SSH

No seu computador (substitua o caminho da chave e o IP):

```bash
chmod 600 ~/Downloads/ssh-key-previsaovr.key
ssh -i ~/Downloads/ssh-key-previsaovr.key ubuntu@SEU_IP_PUBLICO
```

### 10.2 Rodar o instalador

Ja dentro da VM:

```bash
git clone https://github.com/pabloramoa-dev/previsaovr-instagram.git
cd previsaovr-instagram
bash deploy/setup.sh
```

O `setup.sh` instala Python, Pillow, ffmpeg e fontes, cria o ambiente virtual e
gera um arquivo `.env` a partir do modelo.

### 10.3 Preencher os tokens (VOCE)

```bash
nano .env
```

Preencha (mesmos valores dos Secrets do GitHub):

| Variavel        | O que e |
|-----------------|---------|
| `IG_USER_ID`    | ID numerico da conta Instagram |
| `IG_ACCESS_TOKEN` | Token de longa duracao da Graph API |
| `GITHUB_REPO`   | `pabloramoa-dev/previsaovr-instagram` (ja preenchido) |
| `GITHUB_TOKEN`  | Fine-grained PAT com **Contents: Read and write** so neste repo |

Salve com `Ctrl+O`, `Enter`, `Ctrl+X`.

> **Seguranca:** o `.env` fica so na VM e esta no `.gitignore` — nunca vai pro GitHub.

### 10.4 Instalar o servico que roda a cada 10 min

```bash
bash deploy/install-service.sh
```

Isso cria um **systemd timer** que executa `alerta.py` a cada 10 minutos,
mesmo apos reinicios da VM.

---

## Comandos uteis (apos instalado)

```bash
# Ver quando o timer roda de novo
systemctl list-timers previsaovr-alerta.timer

# Acompanhar os logs em tempo real
journalctl -u previsaovr-alerta.service -f

# Forcar uma execucao agora (teste)
sudo systemctl start previsaovr-alerta.service

# Pausar / retomar
sudo systemctl stop previsaovr-alerta.timer
sudo systemctl start previsaovr-alerta.timer
```

---

## Manutencao

- **Atualizar o codigo:** o timer ja roda `git pull --rebase` antes de cada execucao,
  entao novos commits no `main` chegam sozinhos na VM.
- **Renovar o token do Instagram:** a cada ~60 dias, edite o `.env` (`nano .env`) e
  cole o novo `IG_ACCESS_TOKEN`. Nao precisa reiniciar nada.
- **Trocar GitHub Actions x Oracle:** se quiser, desabilite o cron do `alerta.yml`
  no GitHub para evitar posts duplicados — ou deixe ambos: o estado
  (`alertas_estado.json`) com cooldown evita alertas repetidos.

---

## Resumo: o que e seu vs. o que ja esta pronto

**VOCE faz:** criar a conta Oracle, criar a VM, gerar/baixar a chave SSH, conectar,
rodar os 2 scripts e colar os tokens no `.env`.

**Ja preparado neste repo:** `deploy/setup.sh`, `deploy/install-service.sh`,
`deploy/.env.example` e este guia. O `alerta.py` ja roda em duas fases (gerar + publicar)
e funciona igual na VM e no GitHub Actions.
