#!/usr/bin/env bash
# ============================================================
# install-service.sh - instala um systemd timer que roda o
# alerta.py a cada 10 minutos na VM Oracle.
# Rode UMA vez (apos editar o .env):
#   bash deploy/install-service.sh
# ============================================================
set -euo pipefail

APP_DIR="${HOME}/previsaovr-instagram"
PYTHON="${APP_DIR}/.venv/bin/python"
USER_NAME="$(whoami)"

if [ ! -f "${APP_DIR}/.env" ]; then
  echo "ERRO: ${APP_DIR}/.env nao existe. Rode deploy/setup.sh e edite o .env primeiro."
  exit 1
fi

echo ">>> Criando o service unit /etc/systemd/system/previsaovr-alerta.service ..."
sudo tee /etc/systemd/system/previsaovr-alerta.service > /dev/null <<EOF
[Unit]
Description=Detector de alertas climaticos @previsaovr
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=${USER_NAME}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStartPre=/usr/bin/git -C ${APP_DIR} pull --rebase
ExecStart=${PYTHON} ${APP_DIR}/alerta.py
EOF

echo ">>> Criando o timer unit /etc/systemd/system/previsaovr-alerta.timer ..."
sudo tee /etc/systemd/system/previsaovr-alerta.timer > /dev/null <<EOF
[Unit]
Description=Roda o detector de alertas @previsaovr a cada 10 minutos

[Timer]
OnBootSec=2min
OnUnitActiveSec=10min
AccuracySec=30s
Persistent=true

[Install]
WantedBy=timers.target
EOF

echo ">>> Recarregando systemd e habilitando o timer..."
sudo systemctl daemon-reload
sudo systemctl enable --now previsaovr-alerta.timer

echo ""
echo ">>> Pronto! O timer esta ativo. Comandos uteis:"
echo "    Status do timer:   systemctl status previsaovr-alerta.timer"
echo "    Proximas execucoes:systemctl list-timers previsaovr-alerta.timer"
echo "    Ver logs:          journalctl -u previsaovr-alerta.service -f"
echo "    Rodar agora:       sudo systemctl start previsaovr-alerta.service"
