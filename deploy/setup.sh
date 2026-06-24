#!/usr/bin/env bash
# ============================================================
# setup.sh - prepara a VM Oracle (Ubuntu 22.04+) para rodar
# o bot @previsaovr (alerta.py em polling continuo).
# Rode UMA vez como o usuario ubuntu:
#   bash deploy/setup.sh
# ============================================================
set -euo pipefail

echo ">>> Atualizando o sistema..."
sudo apt-get update -y
sudo apt-get upgrade -y

echo ">>> Instalando Python, pip, venv, git, ffmpeg e fontes..."
sudo apt-get install -y \
  python3 python3-pip python3-venv git ffmpeg \
  fonts-dejavu-core fonts-noto-color-emoji

APP_DIR="${HOME}/previsaovr-instagram"
REPO_URL="https://github.com/pabloramoa-dev/previsaovr-instagram.git"

if [ -d "${APP_DIR}/.git" ]; then
  echo ">>> Repo ja existe, atualizando..."
  git -C "${APP_DIR}" pull --rebase || true
else
  echo ">>> Clonando o repositorio..."
  git clone "${REPO_URL}" "${APP_DIR}"
fi

cd "${APP_DIR}"

echo ">>> Criando ambiente virtual Python..."
python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install requests Pillow

echo ">>> Preparando arquivo .env..."
if [ ! -f "${APP_DIR}/.env" ]; then
  cp "${APP_DIR}/deploy/.env.example" "${APP_DIR}/.env"
  echo "    Criado ${APP_DIR}/.env -- EDITE-O agora com seus tokens:"
  echo "    nano ${APP_DIR}/.env"
else
  echo "    .env ja existe, mantido."
fi

echo ""
echo ">>> Instalacao concluida."
echo ">>> Proximos passos:"
echo "    1) Edite o .env:        nano ${APP_DIR}/.env"
echo "    2) Instale o servico:   bash ${APP_DIR}/deploy/install-service.sh"
