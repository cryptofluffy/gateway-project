#!/bin/bash
# WireGuard Gateway Website Installation Script
set -e

echo "🌐 Installing WireGuard Gateway Website..."

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo "❌ This script should NOT be run as root for security reasons."
   echo "Please run as regular user with sudo access."
   exit 1
fi

# System Update
echo "📦 Updating system packages..."
sudo apt-get update

# Install Python and pip if not present
echo "🐍 Installing Python dependencies..."
sudo apt-get install -y python3 python3-pip python3-venv

# Create virtual environment
echo "🏗️  Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python requirements
echo "📋 Installing Python packages..."
pip install -r requirements.txt

# Create systemd service for website
echo "⚙️  Creating systemd service..."
sudo tee /etc/systemd/system/wireguard-website.service > /dev/null <<EOF
[Unit]
Description=WireGuard Gateway Website
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/venv/bin
ExecStart=$(pwd)/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Enabling and starting website service..."
sudo systemctl daemon-reload
sudo systemctl enable wireguard-website.service
sudo systemctl start wireguard-website.service

# Show status
echo "📊 Service status:"
sudo systemctl status wireguard-website.service --no-pager

echo ""
echo "✅ WireGuard Gateway Website installed successfully!"
echo ""
echo "🌐 Website is running on: http://localhost:8000"
echo "🔧 To manage the service:"
echo "   sudo systemctl start|stop|restart wireguard-website"
echo "   sudo systemctl status wireguard-website"
echo ""
echo "📋 Logs: sudo journalctl -u wireguard-website -f"
echo ""
echo "🔥 Firewall: Remember to open port 8000 if needed:"
echo "   sudo ufw allow 8000"
echo ""