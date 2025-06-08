#!/bin/bash
# VPS Server Quick-Install/Update Script
# Usage: curl -s URL | sudo bash

set -e

# Automatische Installation ohne interaktive Dialoge
export DEBIAN_FRONTEND=noninteractive

echo "🚀 VPS WireGuard Server Quick-Install/Update"
echo "============================================"

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (mit sudo)"
    exit 1
fi

# Funktionen definieren
cleanup_repo() {
    echo "🧹 Repository wird bereinigt..."
    rm -rf /tmp/gateway-project
}

install_dependencies() {
    echo "📦 System wird aktualisiert..."
    apt update && apt upgrade -y
    
    echo "🔧 Pakete werden installiert..."
    apt install -y \
        wireguard \
        wireguard-tools \
        python3 \
        python3-pip \
        python3-venv \
        python3-flask \
        python3-requests \
        nginx \
        ufw \
        git \
        curl \
        wget \
        certbot \
        python3-certbot-nginx
}

setup_vps() {
    echo "📡 VPS wird konfiguriert..."
    
    # Repository klonen oder aktualisieren
    if [ ! -d "/tmp/gateway-project" ]; then
        echo "📦 Repository wird geklont..."
        cd /tmp
        git clone https://github.com/cryptofluffy/gateway-project.git
    else
        echo "📦 Repository wird aktualisiert..."
        cd /tmp/gateway-project
        
        # Versuche git pull, bei Fehlern Repository neu klonen
        if ! git pull origin main 2>/dev/null; then
            echo "⚠️ Git pull fehlgeschlagen, Repository wird neu geklont..."
            cd /tmp
            rm -rf gateway-project
            git clone https://github.com/cryptofluffy/gateway-project.git
        fi
    fi
    
    cd /tmp/gateway-project/vps-server
    
    # Prüfe ob die neueste Version installiert wird
    if [ -f "/opt/wireguard-vps/app.py" ] && ! diff -q app.py /opt/wireguard-vps/app.py > /dev/null 2>&1; then
        echo "🔄 Neuere Version erkannt, VPS wird aktualisiert..."
    fi
    
    # VPS-Server installieren
    chmod +x install.sh
    ./install.sh
}

# Parameter verarbeiten
case "${1:-install}" in
    "install"|"update")
        install_dependencies
        setup_vps
        ;;
    "clean")
        echo "🧹 VPS-Installation wird bereinigt..."
        systemctl stop wireguard-vps 2>/dev/null || true
        systemctl disable wireguard-vps 2>/dev/null || true
        rm -rf /opt/wireguard-vps
        rm -f /etc/systemd/system/wireguard-vps.service
        rm -f /etc/nginx/sites-enabled/wireguard-vps
        rm -f /etc/nginx/sites-available/wireguard-vps
        systemctl daemon-reload
        nginx -t && systemctl reload nginx || true
        echo "✅ VPS-Installation bereinigt!"
        ;;
    "status")
        echo "📊 VPS-Status:"
        echo "=============="
        
        if systemctl is-active --quiet wireguard-vps; then
            echo "✅ VPS-Service: Läuft"
        else
            echo "❌ VPS-Service: Gestoppt"
        fi
        
        if systemctl is-active --quiet nginx; then
            echo "✅ Nginx: Läuft"
        else
            echo "❌ Nginx: Gestoppt"
        fi
        
        if [ -f "/opt/wireguard-vps/config.py" ]; then
            echo "✅ Konfiguration: Vorhanden"
        else
            echo "❌ Konfiguration: Fehlt"
        fi
        
        echo ""
        echo "🌐 Ports:"
        ss -tlnp | grep -E ":(80|443|51820)" || echo "Keine VPS-Ports geöffnet"
        ;;
    "logs")
        echo "📝 VPS-Logs:"
        echo "============"
        journalctl -u wireguard-vps -n 50 --no-pager
        ;;
    "restart")
        echo "🔄 VPS wird neu gestartet..."
        systemctl restart wireguard-vps
        systemctl restart nginx
        echo "✅ VPS neu gestartet!"
        ;;
    *)
        echo "❌ Unbekannter Befehl: $1"
        echo ""
        echo "📖 Verfügbare Befehle:"
        echo "====================="
        echo "install  - VPS installieren/aktualisieren"
        echo "update   - VPS aktualisieren"
        echo "clean    - VPS-Installation entfernen"
        echo "status   - VPS-Status anzeigen"
        echo "logs     - VPS-Logs anzeigen"
        echo "restart  - VPS-Services neu starten"
        echo ""
        echo "💡 Beispiele:"
        echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/vps-server/quick-install.sh | sudo bash"
        echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/vps-server/quick-install.sh | sudo bash -s update"
        echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/vps-server/quick-install.sh | sudo bash -s clean"
        exit 1
        ;;
esac

# Cleanup bei Erfolg
if [ "${1:-install}" != "clean" ]; then
    cleanup_repo
    
    echo ""
    echo "✅ VPS-Operation abgeschlossen!"
    echo ""
    echo "🔧 Nächste Schritte:"
    echo "==================="
    echo "1. Domain in /opt/wireguard-vps/config.py konfigurieren"
    echo "2. SSL-Zertifikat mit: certbot --nginx -d yourdomain.com"
    echo "3. VPS neu starten: systemctl restart wireguard-vps"
    echo ""
    echo "🌐 Dashboard: https://yourdomain.com"
    echo "📊 Status: curl -s script-url | sudo bash -s status"
    echo "📝 Logs: curl -s script-url | sudo bash -s logs"
fi