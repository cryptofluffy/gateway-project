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
apt install -y python3 python3-pip python3-venv python3-flask python3-requests

# Verzeichnisse erstellen
echo "📁 Verzeichnisse werden erstellt..."
mkdir -p /etc/wireguard
mkdir -p /var/log/wireguard-vps
mkdir -p /opt/wireguard-vps

# Virtual environment für VPS erstellen
echo "🐍 Python Virtual Environment wird erstellt..."
python3 -m venv /opt/wireguard-vps/venv
/opt/wireguard-vps/venv/bin/pip install -r requirements.txt

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

# VPS-App installieren
echo "📱 VPS-App wird installiert..."
cp -r . /opt/wireguard-vps/
chmod +x /opt/wireguard-vps/app.py

# Systemd-Service für die VPS-App erstellen
cat > /etc/systemd/system/wireguard-vps.service << EOF
[Unit]
Description=WireGuard VPS Web Interface
After=network.target wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wireguard-vps
ExecStart=/opt/wireguard-vps/venv/bin/python /opt/wireguard-vps/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Service aktivieren und starten
systemctl daemon-reload
systemctl enable wireguard-vps
systemctl start wireguard-vps

# UFW Firewall konfigurieren (falls installiert)
if command -v ufw >/dev/null 2>&1; then
    echo "🔥 Firewall wird konfiguriert..."
    ufw allow 51820/udp  # WireGuard
    ufw allow 8080/tcp   # Web-Interface
    ufw allow ssh
fi

echo ""
echo "✅ VPS Installation abgeschlossen!"
echo ""

# VPS IP automatisch ermitteln
VPS_IP=$(curl -s ifconfig.me)

echo "🎯 GATEWAY-PC SETUP-BEFEHL:"
echo "============================"
echo ""
echo "Führe diesen Befehl auf dem Gateway-PC aus:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "git clone https://github.com/cryptofluffy/gateway-project.git && \\"
echo "cd gateway-project/gateway-pc && \\"
echo "sudo ./install.sh && \\"
echo "sudo reboot"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Nach dem Reboot des Gateway-PCs:"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "gateway-manager setup $VPS_IP $SERVER_PUBLIC_KEY && \\"
echo "gateway-manager start"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📱 VPS-Informationen:"
echo "===================="
echo "VPS IP: $VPS_IP"
echo "Server Public Key: $SERVER_PUBLIC_KEY"
echo "Web-Interface: http://$VPS_IP:8080"
echo "WireGuard Port: 51820/UDP"
echo ""
echo "📋 Nach Gateway-Installation:"
echo "============================"
echo "1. Gateway Public Key im Web-Interface eingeben"
echo "2. Port-Weiterleitungen konfigurieren"
echo "3. Server am Gateway-PC anschließen"
echo ""
echo "🔍 Service-Status prüfen:"
echo "systemctl status wg-quick@wg0"
echo "systemctl status wireguard-gateway"
echo ""
echo "💾 Konfiguration gespeichert in: /etc/wireguard/setup-info.txt"

# Setup-Info für später speichern
cat > /etc/wireguard/setup-info.txt << EOF
# WireGuard Gateway VPS Setup Info - $(date)
# ==========================================

VPS_IP=$VPS_IP
SERVER_PUBLIC_KEY=$SERVER_PUBLIC_KEY
WEB_INTERFACE=http://$VPS_IP:8080

# Gateway-PC Installation:
git clone https://github.com/cryptofluffy/gateway-project.git && cd gateway-project/gateway-pc && sudo ./install.sh && sudo reboot

# Gateway-PC Konfiguration (nach Reboot):
gateway-manager setup $VPS_IP $SERVER_PUBLIC_KEY && gateway-manager start
EOF