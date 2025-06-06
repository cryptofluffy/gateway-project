#!/bin/bash
# WireGuard Gateway PC Installation Script

set -e

echo "🚀 WireGuard Gateway PC Installation"
echo "===================================="

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./install.sh)"
    exit 1
fi

# System aktualisieren
echo "📦 System wird aktualisiert..."
apt update && apt upgrade -y

# Benötigte Pakete installieren
echo "🔧 Pakete werden installiert..."
apt install -y \
    wireguard \
    wireguard-tools \
    python3 \
    python3-pip \
    python3-tk \
    isc-dhcp-server \
    iptables-persistent \
    bridge-utils \
    net-tools \
    curl \
    wget

# Python-Abhängigkeiten installieren
echo "🐍 Python-Abhängigkeiten werden installiert..."
pip3 install requests

# Verzeichnisse erstellen
echo "📁 Verzeichnisse werden erstellt..."
mkdir -p /etc/wireguard-gateway
mkdir -p /var/log/wireguard-gateway
mkdir -p /opt/wireguard-gateway

# Gateway-Software installieren
echo "📱 Gateway-Software wird installiert..."
cp gateway_manager.py /opt/wireguard-gateway/
cp gui_app.py /opt/wireguard-gateway/
chmod +x /opt/wireguard-gateway/gateway_manager.py
chmod +x /opt/wireguard-gateway/gui_app.py

# Symbolische Links erstellen
ln -sf /opt/wireguard-gateway/gateway_manager.py /usr/local/bin/gateway-manager
ln -sf /opt/wireguard-gateway/gui_app.py /usr/local/bin/gateway-gui

# Netzwerk-Konfiguration
echo "🌐 Netzwerk wird konfiguriert..."

# IP-Forwarding aktivieren
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Netzwerk-Interfaces konfigurieren
cat > /etc/netplan/01-gateway-config.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - 192.168.1.254/24
      routes:
        - to: 192.168.1.0/24
          via: 192.168.1.1
    eth1:
      dhcp4: false
      addresses:
        - 10.0.0.1/24
EOF

# DHCP-Server für eth1 konfigurieren
echo "🏠 DHCP-Server wird konfiguriert..."
cat > /etc/dhcp/dhcpd.conf << 'EOF'
# DHCP-Konfiguration für Gateway eth1 (Server-Netz)
default-lease-time 600;
max-lease-time 7200;
authoritative;

subnet 10.0.0.0 netmask 255.255.255.0 {
    range 10.0.0.100 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    option domain-name "gateway.local";
}
EOF

# DHCP-Server Interface konfigurieren
echo 'INTERFACESv4="eth1"' > /etc/default/isc-dhcp-server

# WireGuard Systemd-Template erstellen
echo "🔄 WireGuard-Service wird konfiguriert..."
cat > /etc/systemd/system/wireguard-gateway.service << 'EOF'
[Unit]
Description=WireGuard Gateway Service
After=network.target
Wants=network.target

[Service]
Type=forking
RemainAfterExit=yes
ExecStart=/usr/bin/wg-quick up gateway
ExecStop=/usr/bin/wg-quick down gateway
ExecReload=/bin/bash -c 'wg-quick down gateway; wg-quick up gateway'

[Install]
WantedBy=multi-user.target
EOF

# Gateway-Monitor Service erstellen
cat > /etc/systemd/system/gateway-monitor.service << 'EOF'
[Unit]
Description=WireGuard Gateway Monitor
After=wireguard-gateway.service
Requires=wireguard-gateway.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/gateway-manager monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Desktop-Entry für GUI erstellen
echo "🖥️ Desktop-Anwendung wird registriert..."
cat > /usr/share/applications/wireguard-gateway.desktop << 'EOF'
[Desktop Entry]
Name=WireGuard Gateway Manager
Comment=Manage WireGuard Gateway connections
Exec=/usr/local/bin/gateway-gui
Icon=network-wired
Terminal=false
Type=Application
Categories=Network;System;
EOF

# Autostart-Script für GUI (optional)
cat > /etc/xdg/autostart/wireguard-gateway.desktop << 'EOF'
[Desktop Entry]
Name=WireGuard Gateway Manager
Comment=WireGuard Gateway startup
Exec=/usr/local/bin/gateway-gui
Icon=network-wired
Terminal=false
Type=Application
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
EOF

# iptables Basis-Regeln
echo "🔥 Firewall-Regeln werden gesetzt..."
# NAT für WireGuard-Traffic
iptables -t nat -A POSTROUTING -s 10.8.0.0/24 -o eth0 -j MASQUERADE

# Forwarding zwischen Interfaces erlauben
iptables -A FORWARD -i wg0 -o eth1 -j ACCEPT
iptables -A FORWARD -i eth1 -o wg0 -j ACCEPT
iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT
iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT

# iptables-Regeln persistent machen
iptables-save > /etc/iptables/rules.v4

# Services aktivieren
echo "🔄 Services werden aktiviert..."
systemctl daemon-reload
systemctl enable isc-dhcp-server
systemctl enable wireguard-gateway
systemctl enable gateway-monitor

# Netzwerk-Konfiguration anwenden
echo "🌐 Netzwerk-Konfiguration wird angewendet..."
netplan apply

# DHCP-Server starten
systemctl start isc-dhcp-server

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo "==================="
echo ""
echo "1. Gateway konfigurieren:"
echo "   gateway-manager setup <VPS_IP> <VPS_PUBLIC_KEY>"
echo ""
echo "2. Gateway starten:"
echo "   gateway-manager start"
echo ""
echo "3. GUI öffnen:"
echo "   gateway-gui"
echo ""
echo "🔍 Verfügbare Befehle:"
echo "====================="
echo "gateway-manager setup <VPS_IP> <VPS_KEY>  - Gateway konfigurieren"
echo "gateway-manager start                     - Gateway starten"
echo "gateway-manager stop                      - Gateway stoppen"
echo "gateway-manager status                    - Status anzeigen"
echo "gateway-manager monitor                   - Monitoring starten"
echo "gateway-gui                               - GUI öffnen"
echo ""
echo "📁 Wichtige Dateien:"
echo "==================="
echo "Konfiguration: /etc/wireguard-gateway/config.json"
echo "WireGuard:     /etc/wireguard/gateway.conf"
echo "Logs:          /var/log/wireguard-gateway/"
echo ""
echo "🖥️ Netzwerk-Konfiguration:"
echo "=========================="
echo "Port A (eth0): 192.168.1.254/24 (Heimnetzwerk)"
echo "Port B (eth1): 10.0.0.1/24      (Server-Netzwerk)"
echo "WireGuard:     10.8.0.2/24      (Tunnel zum VPS)"
echo ""
echo "⚠️  WICHTIG: Reboot erforderlich für vollständige Netzwerk-Konfiguration!"