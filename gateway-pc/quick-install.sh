#!/bin/bash
# WireGuard Gateway PC Quick-Install Script
# Usage: curl -s URL | sudo bash -s VPS_IP VPS_PUBLIC_KEY

set -e

echo "🚀 WireGuard Gateway PC Quick-Install"
echo "======================================"

# Parameter prüfen
VPS_IP="$1"
VPS_PUBLIC_KEY="$2"

if [ -z "$VPS_IP" ] || [ -z "$VPS_PUBLIC_KEY" ]; then
    echo "❌ Fehler: VPS_IP und VPS_PUBLIC_KEY erforderlich"
    echo ""
    echo "Usage:"
    echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-pc/quick-install.sh | sudo bash -s VPS_IP VPS_PUBLIC_KEY"
    echo ""
    echo "Beispiel:"
    echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-pc/quick-install.sh | sudo bash -s 217.154.243.158 abcd1234..."
    exit 1
fi

echo "📋 Konfiguration:"
echo "VPS IP: $VPS_IP"
echo "VPS Public Key: ${VPS_PUBLIC_KEY:0:20}..."
echo ""

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (mit sudo)"
    exit 1
fi

# Repository klonen oder aktualisieren
if [ ! -d "/tmp/gateway-project" ]; then
    echo "📦 Repository wird geklont..."
    cd /tmp
    git clone https://github.com/cryptofluffy/gateway-project.git
else
    echo "📦 Repository wird aktualisiert..."
    cd /tmp/gateway-project
    git pull origin main
fi

cd /tmp/gateway-project/gateway-pc

echo "🔧 Gateway-PC wird installiert..."
chmod +x install.sh
./install.sh

echo ""
echo "⚙️ Gateway wird automatisch konfiguriert..."

# Gateway konfigurieren
./gateway_manager.py setup "$VPS_IP" "$VPS_PUBLIC_KEY"

if [ $? -eq 0 ]; then
    echo "✅ Gateway erfolgreich konfiguriert!"
    
    echo "🚀 Gateway wird gestartet..."
    ./gateway_manager.py start
    
    if [ $? -eq 0 ]; then
        echo "✅ Gateway erfolgreich gestartet!"
        
        # Gateway Public Key aus der Konfiguration lesen
        if [ -f "/etc/wireguard-gateway/keys.txt" ]; then
            GATEWAY_PUBLIC_KEY=$(grep "GATEWAY_PUBLIC_KEY=" /etc/wireguard-gateway/keys.txt | cut -d'=' -f2)
            echo ""
            echo "🔑 WICHTIG - Gateway Public Key für VPS Dashboard:"
            echo "=================================================="
            echo "$GATEWAY_PUBLIC_KEY"
            echo "=================================================="
            echo ""
            echo "📝 Nächste Schritte:"
            echo "1. Diesen Public Key im VPS Dashboard eingeben"
            echo "2. Port-Weiterleitungen nach Bedarf konfigurieren"
            echo "3. Server am Port B (eth1) anschließen"
            echo ""
        fi
        
        echo "🔄 System wird neu gestartet für finale Netzwerk-Konfiguration..."
        echo "Nach dem Reboot ist das Gateway betriebsbereit!"
        sleep 5
        reboot
        
    else
        echo "❌ Fehler beim Starten des Gateways"
        exit 1
    fi
else
    echo "❌ Fehler bei der Gateway-Konfiguration"
    exit 1
fi