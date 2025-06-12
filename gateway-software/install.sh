#!/bin/bash
# WireGuard Gateway PC Installation Script

set -e

# Automatische Installation ohne interaktive Dialoge
export DEBIAN_FRONTEND=noninteractive

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

# iptables-persistent vorkonfigurieren um interaktive Dialoge zu vermeiden
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections

apt install -y \
    wireguard \
    wireguard-tools \
    python3 \
    python3-pip \
    python3-tk \
    python3-venv \
    python3-requests \
    isc-dhcp-server \
    iptables-persistent \
    bridge-utils \
    net-tools \
    curl \
    wget

# Python virtual environment erstellen
echo "🐍 Python-Umgebung wird vorbereitet..."
mkdir -p /opt/wireguard-gateway
python3 -m venv /opt/wireguard-gateway/venv
/opt/wireguard-gateway/venv/bin/pip install requests

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

# Wrapper-Skripte erstellen
cat > /usr/local/bin/gateway-manager << 'EOF'
#!/bin/bash
/opt/wireguard-gateway/venv/bin/python /opt/wireguard-gateway/gateway_manager.py "$@"
EOF

cat > /usr/local/bin/gateway-gui << 'EOF'
#!/bin/bash
/opt/wireguard-gateway/venv/bin/python /opt/wireguard-gateway/gui_app.py "$@"
EOF

chmod +x /usr/local/bin/gateway-manager
chmod +x /usr/local/bin/gateway-gui

# Netzwerk-Konfiguration
echo "🌐 Netzwerk wird konfiguriert..."

# IP-Forwarding aktivieren
echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
sysctl -p

# Netzwerk-Konfiguration wird über das Dashboard verwaltet
echo "🌐 Netzwerk-Konfiguration wird vorbereitet (über Dashboard konfigurierbar)..."

# Backup der originalen Netplan-Konfiguration falls vorhanden
if [ -f "/etc/netplan/50-cloud-init.yaml" ]; then
    cp /etc/netplan/50-cloud-init.yaml /etc/netplan/50-cloud-init.yaml.backup
fi

# DHCP-Server deaktiviert (wird über Dashboard aktiviert)
echo "🏠 DHCP-Server wird vorbereitet (über Dashboard aktivierbar)..."
systemctl disable isc-dhcp-server 2>/dev/null || true
systemctl stop isc-dhcp-server 2>/dev/null || true

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
systemctl enable wireguard-gateway
systemctl enable gateway-monitor

# Netzwerk-Konfiguration bleibt unverändert (über Dashboard konfigurierbar)
echo "🌐 Bestehende Netzwerk-Konfiguration beibehalten..."

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "🎯 WICHTIGE KONFIGURATIONSDATEN:"
echo "================================"
echo ""

# Gateway Public Key generieren für Copy&Paste
GATEWAY_PRIVATE_KEY=$(wg genkey)
GATEWAY_PUBLIC_KEY=$(echo "$GATEWAY_PRIVATE_KEY" | wg pubkey)

echo "📋 FÜR VPS DASHBOARD EINGEBEN:"
echo "└─ Gateway Public Key: $GATEWAY_PUBLIC_KEY"
echo ""
echo "💾 Diese Daten werden automatisch gespeichert in:"
echo "   /etc/wireguard-gateway/keys.txt"
echo ""

# Keys speichern
mkdir -p /etc/wireguard-gateway
cat > /etc/wireguard-gateway/keys.txt << EOF
# WireGuard Gateway Keys - $(date)
GATEWAY_PRIVATE_KEY=$GATEWAY_PRIVATE_KEY
GATEWAY_PUBLIC_KEY=$GATEWAY_PUBLIC_KEY

# VPS Konfiguration (nach Setup ausfüllen):
VPS_IP=
VPS_PUBLIC_KEY=
EOF

echo "🔧 SETUP-BEFEHLE:"
echo "================"
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
echo "Aktuelle Konfiguration: Unverändert (DHCP/bestehend)"
echo "WireGuard-Tunnel:        Bereit für VPS-Verbindung"
echo "Gateway-Dashboard:       Für Netzwerk-Setup verwenden"
echo ""
echo "📋 NÄCHSTE SCHRITTE:"
echo "==================="
echo "1. Gateway mit VPS verbinden (automatisch)"
echo "2. Dashboard öffnen: gateway-gui"
echo "3. Netzwerkschnittstellen über Dashboard konfigurieren"
echo "4. Port-Weiterleitungen einrichten"
echo ""
echo "⚠️  HINWEIS: Netzwerk-Setup erfolgt über das Dashboard!"