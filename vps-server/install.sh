#!/bin/bash
# WireGuard Gateway VPS Installation Script

set -e

echo "🚀 WireGuard Gateway VPS Installation"
echo "======================================"

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./install.sh)"
    exit 1
fi

# System aktualisieren
echo "📦 System wird aktualisiert..."
apt update && apt upgrade -y

# WireGuard installieren
echo "🔧 WireGuard wird installiert..."
apt install -y wireguard wireguard-tools

# Python und Flask installieren
echo "🐍 Python-Abhängigkeiten werden installiert..."
apt install -y python3 python3-pip python3-venv
pip3 install -r requirements.txt

# Verzeichnisse erstellen
echo "📁 Verzeichnisse werden erstellt..."
mkdir -p /etc/wireguard
mkdir -p /var/log/wireguard-gateway
mkdir -p /opt/wireguard-gateway

# WireGuard Konfiguration generieren
echo "🔑 WireGuard-Keys werden generiert..."
WG_DIR="/etc/wireguard"
SERVER_PRIVATE_KEY=$(wg genkey)
SERVER_PUBLIC_KEY=$(echo "$SERVER_PRIVATE_KEY" | wg pubkey)

# Server-Konfiguration erstellen
cat > "$WG_DIR/wg0.conf" << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE_KEY
Address = 10.8.0.1/24
ListenPort = 51820
SaveConfig = false

# Forwarding und NAT aktivieren
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Gateway-Client (wird beim ersten Verbinden hinzugefügt)
EOF

# IP-Forwarding aktivieren
echo "🌐 IP-Forwarding wird aktiviert..."
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# WireGuard-Service aktivieren
echo "🔄 WireGuard-Service wird aktiviert..."
systemctl enable wg-quick@wg0

# Gateway-App installieren
echo "📱 Gateway-App wird installiert..."
cp -r . /opt/wireguard-gateway/
chmod +x /opt/wireguard-gateway/app.py

# Systemd-Service für die Web-App erstellen
cat > /etc/systemd/system/wireguard-gateway.service << EOF
[Unit]
Description=WireGuard Gateway Web Interface
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wireguard-gateway
ExecStart=/usr/bin/python3 /opt/wireguard-gateway/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Service aktivieren und starten
systemctl daemon-reload
systemctl enable wireguard-gateway
systemctl start wireguard-gateway

# UFW Firewall konfigurieren (falls installiert)
if command -v ufw >/dev/null 2>&1; then
    echo "🔥 Firewall wird konfiguriert..."
    ufw allow 51820/udp  # WireGuard
    ufw allow 8080/tcp   # Web-Interface
    ufw allow ssh
fi

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "📋 Wichtige Informationen:"
echo "========================="
echo "Server Public Key: $SERVER_PUBLIC_KEY"
echo "Server IP: 10.8.0.1"
echo "Listen Port: 51820"
echo "Web-Interface: http://$(curl -s ifconfig.me):8080"
echo ""
echo "📝 Nächste Schritte:"
echo "1. Gateway-PC konfigurieren mit diesem Public Key"
echo "2. Web-Interface unter Port 8080 aufrufen"
echo "3. Port-Weiterleitungen nach Bedarf einrichten"
echo ""
echo "🔍 Service-Status prüfen:"
echo "systemctl status wg-quick@wg0"
echo "systemctl status wireguard-gateway"