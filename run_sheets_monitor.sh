#!/bin/bash
# Cron: envia H2 e I2 da planilha via Telegram (execução diária)
# Exemplo de entrada no crontab (09:00 todo dia):
#   0 9 * * * /Users/lucasaguirre/robo-uma-monitoramento/run_sheets_monitor.sh >> /Users/lucasaguirre/robo-uma-monitoramento/logs/sheets_monitor.log 2>&1

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV="$REPO_DIR/.venv/bin/python3"
SCRIPT="$REPO_DIR/sheets_monitor.py"
ENV_FILE="$REPO_DIR/.env"

if [ -f "$ENV_FILE" ]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

mkdir -p "$REPO_DIR/logs"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando sheets_monitor..."
"$VENV" "$SCRIPT"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Concluído."
