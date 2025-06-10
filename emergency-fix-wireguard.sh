#!/bin/bash
# Emergency WireGuard Fix - Automatische Reparatur aller Probleme

set -e

echo "🚨 Emergency WireGuard Fix wird ausgeführt..."

# VPS Service stoppen
echo "🔄 Stoppe VPS Service..."
systemctl stop wireguard-vps 2>/dev/null || true
pkill -f "python.*app.py" 2>/dev/null || true

# WireGuard Interface stoppen
echo "🔄 Stoppe WireGuard Interface..."
wg-quick down wg0 2>/dev/null || true

# Private Key sicherstellen
echo "🔑 Überprüfe WireGuard Keys..."
if [ ! -f "/etc/wireguard/server_private.key" ]; then
    echo "🔑 Generiere neuen Private Key..."
    mkdir -p /etc/wireguard
    wg genkey > /etc/wireguard/server_private.key
    chmod 600 /etc/wireguard/server_private.key
fi

if [ ! -f "/etc/wireguard/server_public.key" ]; then
    echo "🔑 Generiere Public Key..."
    wg pubkey < /etc/wireguard/server_private.key > /etc/wireguard/server_public.key
    chmod 644 /etc/wireguard/server_public.key
fi

PRIVATE_KEY=$(cat /etc/wireguard/server_private.key)
PUBLIC_KEY=$(cat /etc/wireguard/server_public.key)

echo "✅ VPS Public Key: $PUBLIC_KEY"

# Clients-Datei überprüfen und reparieren
echo "📋 Überprüfe Client-Daten..."
CLIENTS_FILE="/etc/wireguard/clients.json"

if [ ! -f "$CLIENTS_FILE" ]; then
    echo "📋 Erstelle leere Clients-Datei..."
    mkdir -p /etc/wireguard
    echo "{}" > "$CLIENTS_FILE"
fi

# Basiswerte für WireGuard-Konfiguration
echo "📝 Erstelle WireGuard-Konfiguration..."
cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $PRIVATE_KEY
Address = 10.8.0.1/24
ListenPort = 51820
SaveConfig = false

# Forwarding und NAT aktivieren
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

EOF

# Clients aus JSON-Datei laden und hinzufügen
echo "👥 Füge gespeicherte Clients hinzu..."
python3 -c "
import json
import os

clients_file = '/etc/wireguard/clients.json'
config_file = '/etc/wireguard/wg0.conf'

try:
    if os.path.exists(clients_file):
        with open(clients_file, 'r') as f:
            clients = json.load(f)
        
        if clients:
            with open(config_file, 'a') as f:
                client_ip = 2
                for public_key, client_info in clients.items():
                    name = client_info.get('name', 'Unbekannt')
                    location = client_info.get('location', 'Unbekannt')
                    
                    f.write(f'''# Client: {name} ({location})
[Peer]
PublicKey = {public_key}
AllowedIPs = 10.8.0.{client_ip}/32, 10.0.0.0/24

''')
                    client_ip += 1
                    print(f'✅ Client hinzugefügt: {name} ({location})')
        else:
            print('ℹ️ Keine Clients in der Datenbank gefunden')
    else:
        print('ℹ️ Clients-Datei nicht gefunden')
except Exception as e:
    print(f'⚠️ Fehler beim Laden der Clients: {e}')
"

# Berechtigungen setzen
chmod 600 /etc/wireguard/wg0.conf

# IP-Forwarding aktivieren
echo "🌐 Aktiviere IP-Forwarding..."
sysctl -w net.ipv4.ip_forward=1

# /etc/sysctl.conf aktualisieren
if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf; then
    echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
fi

# WireGuard Interface starten
echo "🚀 Starte WireGuard Interface..."
wg-quick up wg0

# Interface-Status überprüfen
if wg show wg0 >/dev/null 2>&1; then
    echo "✅ WireGuard Interface erfolgreich gestartet"
    echo "📊 WireGuard Status:"
    wg show wg0
else
    echo "❌ Fehler beim Starten des WireGuard Interface"
    echo "📋 Konfiguration prüfen:"
    cat /etc/wireguard/wg0.conf
    exit 1
fi

# VPS-Anwendung starten
echo "🖥️ Starte VPS-Anwendung..."
cd /opt/wireguard-vps

# Virtual Environment aktivieren
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "✅ Virtual Environment aktiviert"
else
    echo "⚠️ Virtual Environment nicht gefunden - verwende System-Python"
fi

# Environment-Variablen für Monitoring setzen
export MONITORING_ENABLED=true
export MONITORING_INTERVAL=15
export LOG_LEVEL=DEBUG

# VPS-Anwendung im Hintergrund starten
nohup python3 app.py > /var/log/wireguard-vps.log 2>&1 &
VPS_PID=$!

echo "🔄 Warte 5 Sekunden auf VPS-Start..."
sleep 5

# Port-Check
if ss -tlnp | grep -q ":8080" || lsof -i :8080 >/dev/null 2>&1; then
    echo "✅ VPS-Anwendung läuft auf Port 8080"
else
    echo "❌ VPS-Anwendung nicht erreichbar auf Port 8080"
    echo "📋 Letzte Log-Einträge:"
    tail -10 /var/log/wireguard-vps.log
    echo ""
    echo "🔄 Versuche systemctl-Start..."
    systemctl start wireguard-vps
    sleep 3
    if ss -tlnp | grep -q ":8080"; then
        echo "✅ VPS über systemctl gestartet"
    fi
fi

# Abschlussbericht
echo ""
echo "🎯 Emergency Fix abgeschlossen!"
echo "==============================="
VPS_IP=$(curl -s ifconfig.me 2>/dev/null || echo "IP nicht ermittelbar")
echo "VPS IP: $VPS_IP"
echo "VPS Public Key: $PUBLIC_KEY"
echo "Web-Interface: http://$VPS_IP:8080"
echo ""
echo "📊 Aktueller WireGuard Status:"
wg show wg0 2>/dev/null || echo "WireGuard Interface nicht aktiv"
echo ""
echo "💡 Nächste Schritte:"
echo "1. Dashboard öffnen: http://$VPS_IP:8080"
echo "2. Falls Gateway fehlt, hinzufügen mit Public Key"
echo "3. Gateway-PC verbinden und testen"
echo ""
echo "🔍 Logs bei Problemen:"
echo "- VPS: tail -f /var/log/wireguard-vps.log"
echo "- WireGuard: journalctl -u wg-quick@wg0 -f"