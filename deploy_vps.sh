#!/bin/bash
# VPS Ubuntu/Debian 1-Click Auto Deployment Script for Universal Super Bot

echo "🚀 VPS serverda Universal Super Bot sozlanmoqda..."

# 1. Tizimni yangilash va FFmpeg/Python o'rnatish
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv ffmpeg git curl

# 2. Virtual muhit yaratish
python3 -m venv venv
source venv/bin/activate

# 3. Pip paketlarini o'rnatish
pip install --upgrade pip
pip install -r requirements.txt

# 4. Systemd xizmatini yaratish (24/7 Auto-restart)
SERVICE_FILE="/etc/systemd/system/superbot.service"
CURRENT_DIR=$(pwd)
USER_NAME=$(whoami)

sudo bash -c "cat <<EOF > $SERVICE_FILE
[Unit]
Description=Universal Super Telegram Bot Service
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=$CURRENT_DIR
ExecStart=$CURRENT_DIR/venv/bin/python main.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF"

# 5. Xizmatni yoqish va ishga tushirish
sudo systemctl daemon-reload
sudo systemctl enable superbot
sudo systemctl restart superbot

echo "✅ Bot VPS serverda 24/7 rejimida ishga tushdi!"
echo "📊 Holatni ko'rish uchun: sudo systemctl status superbot"
echo "📜 Loglarni ko'rish uchun: sudo journalctl -u superbot -f"
