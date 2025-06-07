#!/bin/bash
# VPS Deployment Script - Einfache Installation

echo "🚀 WireGuard Gateway VPS Deployment"
echo "===================================="

VPS_IP="$1"
if [ -z "$VPS_IP" ]; then
    echo "Usage: ./deploy-vps.sh <VPS_IP>"
    echo "Beispiel: ./deploy-vps.sh 192.168.100.50"
    exit 1
fi

echo "📦 Erstelle Deployment-Paket..."

# Deployment-Paket erstellen
tar -czf vps-deployment.tar.gz -C vps-server/ .

echo "📤 Übertrage Dateien zum VPS..."

# Dateien zum VPS übertragen
scp vps-deployment.tar.gz root@$VPS_IP:/tmp/

echo "🔧 Installation auf VPS starten..."

# Remote-Installation durchführen
ssh root@$VPS_IP << 'EOF'
cd /tmp
tar -xzf vps-deployment.tar.gz
chmod +x install.sh
./install.sh
EOF

echo ""
echo "✅ Installation abgeschlossen!"
echo ""
echo "🌐 Web-Interface: http://$VPS_IP:8080"
echo "🔑 Server Public Key wurde ausgegeben - bitte notieren!"
echo ""
echo "📋 Nächste Schritte:"
echo "1. Public Key für Gateway-PC notieren"
echo "2. Gateway-PC installieren und konfigurieren"
echo "3. Web-Interface testen"