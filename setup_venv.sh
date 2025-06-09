#!/bin/bash

# === Settings ===
PYTHON_VERSION="3.10"
PROJECT_DIR="$(pwd)"
VENV_DIR="$PROJECT_DIR/venv"
ENV_FILE="$PROJECT_DIR/.env"

echo "[*] Updating system and installing required packages..."
sudo apt update
sudo apt install -y \
  python${PYTHON_VERSION} \
  python${PYTHON_VERSION}-venv \
  python${PYTHON_VERSION}-distutils \
  python${PYTHON_VERSION}-dev \
  build-essential \
  libffi-dev \
  libssl-dev \
  curl

echo "[*] Checking for pip..."
if ! command -v pip${PYTHON_VERSION} &>/dev/null; then
    echo "[*] pip not found, installing via get-pip.py..."
    curl -sS https://bootstrap.pypa.io/get-pip.py | sudo python${PYTHON_VERSION}
fi

echo "[*] Creating virtual environment..."
python${PYTHON_VERSION} -m venv "$VENV_DIR"

echo "[*] Activating virtual environment..."
source "$VENV_DIR/bin/activate"

echo "[*] Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Generate .env template if not exists
if [ ! -f "$ENV_FILE" ]; then
    echo "[*] Creating .env template..."
    cat <<EOF > "$ENV_FILE"
TG_BOT_TOKEN=
ADMIN_CHAT_ID=
ROOT_ADMIN_ID=
FORWARD_CHAT_IDS=
DB_PATH=database/db.sqlite3
MT5_SECRET_KEY=
BALANCE_API_KEY=
LOG_LEVEL=INFO
EOF
else
    echo "[i] .env file already exists. Skipping creation."
fi

echo "[+] Setup complete. Virtual environment is ready."
echo "[i] To activate it manually later, run:"
echo "    source $VENV_DIR/bin/activate"