#!/bin/bash
# WireGuard Gateway PC Quick-Install Script
# Usage: curl -s URL | sudo bash -s VPS_IP VPS_PUBLIC_KEY

set -e

# Automatische Installation ohne interaktive Dialoge
export DEBIAN_FRONTEND=noninteractive

echo "🚀 WireGuard Gateway PC Quick-Install"
echo "======================================"

# Parameter prüfen
VPS_IP="$1"

if [ -z "$VPS_IP" ]; then
    echo "❌ Fehler: VPS_IP erforderlich"
    echo ""
    echo "Usage:"
    echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-pc/quick-install.sh | sudo bash -s VPS_IP"
    echo ""
    echo "Beispiel:"
    echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-pc/quick-install.sh | sudo bash -s 217.154.243.158"
    exit 1
fi

echo "📋 Konfiguration:"
echo "VPS IP: $VPS_IP"
echo "VPS Public Key: Wird automatisch abgerufen..."
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
    
    # Versuche git pull, bei Fehlern Repository neu klonen
    if ! git pull origin main 2>/dev/null; then
        echo "⚠️ Git pull fehlgeschlagen, Repository wird neu geklont..."
        cd /tmp
        rm -rf gateway-project
        git clone https://github.com/cryptofluffy/gateway-project.git
    fi
fi

cd /tmp/gateway-project/gateway-pc

# Prüfe ob install.sh die neueste Version mit Python venv fix hat
if ! grep -q "python3-venv" install.sh; then
    echo "⚠️ Veraltete install.sh erkannt, Repository wird aktualisiert..."
    cd /tmp
    rm -rf gateway-project
    git clone https://github.com/cryptofluffy/gateway-project.git
    cd /tmp/gateway-project/gateway-pc
fi

echo "🔧 Gateway-PC wird installiert..."
chmod +x install.sh
./install.sh

echo ""
echo "⚙️ Gateway wird automatisch konfiguriert..."

# Gateway konfigurieren (automatische VPS Public Key Erkennung)
/usr/local/bin/gateway-manager setup "http://$VPS_IP"

if [ $? -eq 0 ]; then
    echo "✅ Gateway erfolgreich konfiguriert!"
    
    echo "🚀 Gateway wird gestartet..."
    /usr/local/bin/gateway-manager start
    
    if [ $? -eq 0 ]; then
        echo "✅ Gateway erfolgreich gestartet!"
        
        # Gateway Public Key aus der Konfiguration lesen
        if [ -f "/etc/wireguard-gateway/keys.txt" ]; then
            GATEWAY_PUBLIC_KEY=$(grep "GATEWAY_PUBLIC_KEY=" /etc/wireguard-gateway/keys.txt | cut -d'=' -f2)
            
            echo ""
            echo "🤖 Gateway wird automatisch beim VPS registriert..."
            
            # Automatische Registrierung beim VPS versuchen
            REGISTER_RESPONSE=$(curl -s -X POST "http://$VPS_IP/api/clients" \
                -H "Content-Type: application/json" \
                -d "{\"name\": \"Gateway-$(hostname)\", \"public_key\": \"$GATEWAY_PUBLIC_KEY\", \"location\": \"Auto-registered\"}" \
                --connect-timeout 10 --max-time 30 2>/dev/null)
            
            if echo "$REGISTER_RESPONSE" | grep -q '"success": *true' 2>/dev/null; then
                echo "✅ Gateway automatisch beim VPS registriert!"
                echo ""
                echo "🎉 INSTALLATION ERFOLGREICH ABGESCHLOSSEN!"
                echo "=========================================="
                echo ""
                echo "✅ Gateway ist konfiguriert und gestartet"
                echo "✅ Automatisch beim VPS registriert"
                echo "✅ Bereit für Port-Weiterleitungen"
                echo ""
                echo "🌐 Öffne das VPS Dashboard und konfiguriere Port-Weiterleitungen"
                echo "🔌 Schließe deine Server an Port B (eth1) an"
            else
                echo "⚠️ Automatische Registrierung fehlgeschlagen"
                echo ""
                echo "🔑 MANUELL IM VPS DASHBOARD EINGEBEN:"
                echo "===================================="
                echo ""
                echo "Gateway Name: Gateway-$(hostname)"
                echo "Gateway Key:  $GATEWAY_PUBLIC_KEY"
                echo ""
                echo "▶️ Gehe zu: http://$VPS_IP"
                echo "▶️ Klicke auf 'Gateway hinzufügen'"
                echo "▶️ Kopiere den Key oben hinein"
                echo "▶️ Klicke auf 'Hinzufügen'"
                echo ""
            fi
            
            echo "📝 Nächste Schritte:"
            echo "==================="
            echo "1. 🌐 VPS Dashboard öffnen: http://$VPS_IP"
            echo "2. 🔧 Port-Weiterleitungen konfigurieren"
            echo "3. 🔌 Server am Port B (eth1) anschließen"
            echo "4. 🖥️ Gateway GUI öffnen: gateway-gui"
            echo ""
        fi
        
        echo "✅ Installation abgeschlossen!"
        echo ""
        echo "📱 Gateway-Dashboard starten:"
        echo "   gateway-gui"
        echo ""
        echo "⚠️  Kein Reboot erforderlich - Netzwerk bleibt unverändert"
        
    else
        echo "❌ Fehler beim Starten des Gateways"
        exit 1
    fi
else
    echo "❌ Fehler bei der Gateway-Konfiguration"
    exit 1
fi