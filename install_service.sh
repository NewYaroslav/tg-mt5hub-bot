#!/bin/bash

SERVICE_NAME="mt5hub-bot"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}.service"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_PATH="$PROJECT_DIR/venv/bin/python"
WORKING_DIR="$PROJECT_DIR"
USER_NAME="$(whoami)"

if [ ! -f "$PYTHON_PATH" ]; then
  echo "❌ Python not found at $PYTHON_PATH"
  echo "Did you run setup_venv.sh first?"
  exit 1
fi

echo "[*] Creating $SERVICE_NAME service at $SERVICE_PATH..."

sudo tee "$SERVICE_PATH" > /dev/null <<EOF
[Unit]
Description=MT5Hub Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$WORKING_DIR
ExecStart=$PYTHON_PATH mt5hub_bot.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

echo "[*] Reloading and enabling systemd service..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo "[+] Service $SERVICE_NAME is now installed and started."
echo "[i] Check status with:"
echo "    sudo systemctl status $SERVICE_NAME"