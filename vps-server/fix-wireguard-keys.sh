#!/bin/bash
# Fix WireGuard Keys Script für VPS
set -e

echo "🔧 Repariere WireGuard-Keys..."

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./fix-wireguard-keys.sh)"
    exit 1
fi

WG_DIR="/etc/wireguard"

# Prüfe existierende Keys
echo "📋 Prüfe existierende Keys..."
if [ -f "$WG_DIR/server_private.key" ] && [ -f "$WG_DIR/server_public.key" ]; then
    echo "✅ Keys bereits vorhanden"
    SERVER_PRIVATE_KEY=$(cat "$WG_DIR/server_private.key")
    SERVER_PUBLIC_KEY=$(cat "$WG_DIR/server_public.key")
else
    echo "🔑 Generiere neue WireGuard-Keys..."
    SERVER_PRIVATE_KEY=$(wg genkey)
    SERVER_PUBLIC_KEY=$(echo "$SERVER_PRIVATE_KEY" | wg pubkey)
    
    # Keys speichern
    echo "$SERVER_PRIVATE_KEY" > "$WG_DIR/server_private.key"
    echo "$SERVER_PUBLIC_KEY" > "$WG_DIR/server_public.key"
    chmod 600 "$WG_DIR/server_private.key"
    chmod 644 "$WG_DIR/server_public.key"
fi

# Für Kompatibilität auch private.key erstellen
echo "$SERVER_PRIVATE_KEY" > "$WG_DIR/private.key"
chmod 600 "$WG_DIR/private.key"

# Backup der aktuellen Konfiguration
if [ -f "$WG_DIR/wg0.conf" ]; then
    cp "$WG_DIR/wg0.conf" "$WG_DIR/wg0.conf.backup.$(date +%Y%m%d_%H%M%S)"
    echo "💾 Backup erstellt: $WG_DIR/wg0.conf.backup.$(date +%Y%m%d_%H%M%S)"
fi

# WireGuard Interface stoppen
echo "🛑 Stoppe WireGuard Interface..."
systemctl stop wg-quick@wg0 2>/dev/null || true
ip link delete wg0 2>/dev/null || true

# Neue Konfiguration erstellen
echo "📝 Erstelle neue WireGuard-Konfiguration..."
cat > "$WG_DIR/wg0.conf" << EOF
[Interface]
PrivateKey = $SERVER_PRIVATE_KEY
Address = 10.8.0.1/24
ListenPort = 51820
SaveConfig = false

# IP-Forwarding und NAT
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Gateway-Clients werden automatisch hinzugefügt
EOF

# IP-Forwarding aktivieren
echo "🌐 Aktiviere IP-Forwarding..."
sysctl -w net.ipv4.ip_forward=1

# WireGuard starten
echo "🚀 Starte WireGuard..."
systemctl start wg-quick@wg0
systemctl enable wg-quick@wg0

# Status prüfen
echo "📊 Status:"
systemctl status wg-quick@wg0 --no-pager -l
echo ""
wg show wg0

echo ""
echo "✅ WireGuard-Keys erfolgreich repariert!"
echo ""
echo "🔑 VPS Public Key: $SERVER_PUBLIC_KEY"
echo "📱 Web-Interface: http://$(curl -s ifconfig.me):8080"
echo ""
echo "💡 Verwende diesen Public Key für Gateway-PC Setup:"
echo "    sudo /usr/local/bin/gateway-manager setup $(curl -s ifconfig.me) $SERVER_PUBLIC_KEY"