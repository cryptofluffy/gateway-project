#!/bin/bash
# SiteConnector Update Script
# Einheitliches Update-System für VPS und Gateway-PC

set -e

echo "🚀 SiteConnector - System Update"
echo "================================"

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen: sudo siteconnector-update"
    exit 1
fi

# System-Typ erkennen
if [ -f "/opt/siteconnector-vps/app.py" ] || [ -f "/opt/wireguard-vps/app.py" ]; then
    SYSTEM_TYPE="vps"
    echo "🖥️ SiteConnector VPS erkannt"
elif [ -f "/usr/local/bin/gateway-manager" ] || [ -f "/usr/local/bin/siteconnector-gateway" ]; then
    SYSTEM_TYPE="gateway"
    echo "🌐 SiteConnector Gateway erkannt"
else
    echo "❌ SiteConnector System nicht erkannt"
    echo "💡 Installiere zuerst SiteConnector:"
    echo "   VPS: curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/vps-server/install.sh | sudo bash"
    echo "   Gateway: curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-pc/install.sh | sudo bash"
    exit 1
fi

# Backup erstellen
echo "💾 Erstelle System-Backup..."
BACKUP_DIR="/var/backups/siteconnector-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ "$SYSTEM_TYPE" = "vps" ]; then
    # VPS Backup
    [ -d "/opt/siteconnector-vps" ] && cp -r /opt/siteconnector-vps "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/opt/wireguard-vps" ] && cp -r /opt/wireguard-vps "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/wireguard" ] && cp -r /etc/wireguard "$BACKUP_DIR/" 2>/dev/null || true
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    # Gateway Backup
    [ -d "/etc/siteconnector" ] && cp -r /etc/siteconnector "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/wireguard-gateway" ] && cp -r /etc/wireguard-gateway "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/wireguard" ] && cp -r /etc/wireguard "$BACKUP_DIR/" 2>/dev/null || true
fi

echo "✅ Backup erstellt: $BACKUP_DIR"

# System-Updates
echo "📦 System-Updates installieren..."
apt update && apt upgrade -y

# Repository herunterladen
echo "📥 Lade neueste SiteConnector Version..."
rm -rf /tmp/siteconnector-update
git clone https://github.com/cryptofluffy/gateway-project.git /tmp/siteconnector-update

if [ "$SYSTEM_TYPE" = "vps" ]; then
    echo "🔄 SiteConnector VPS aktualisieren..."
    
    # Zielverzeichnis bestimmen
    if [ -d "/opt/siteconnector-vps" ]; then
        VPS_DIR="/opt/siteconnector-vps"
    else
        VPS_DIR="/opt/wireguard-vps"
    fi
    
    cd "$VPS_DIR"
    
    # Services stoppen
    systemctl stop wireguard-vps 2>/dev/null || true
    systemctl stop siteconnector-vps 2>/dev/null || true
    
    # Virtual Environment erstellen falls nicht vorhanden
    if [ ! -d "venv" ]; then
        echo "📦 Virtual Environment erstellen..."
        python3 -m venv venv
    fi
    
    # Code aktualisieren
    cp /tmp/siteconnector-update/vps-server/*.py .
    cp -r /tmp/siteconnector-update/vps-server/static/* ./static/ 2>/dev/null || true
    cp -r /tmp/siteconnector-update/vps-server/templates/* ./templates/ 2>/dev/null || true
    cp /tmp/siteconnector-update/vps-server/requirements.txt . 2>/dev/null || true
    
    # Python-Abhängigkeiten aktualisieren
    echo "📦 Python-Abhängigkeiten aktualisieren..."
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
    
    # Systemd-Service erstellen/aktualisieren
    echo "📋 SiteConnector VPS Service konfigurieren..."
    cp /tmp/siteconnector-update/vps-server/systemd/wireguard-vps.service /etc/systemd/system/ 2>/dev/null || \
    cat > /etc/systemd/system/siteconnector-vps.service << EOF
[Unit]
Description=SiteConnector VPS Server
After=network.target wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=$VPS_DIR
ExecStart=$VPS_DIR/venv/bin/python $VPS_DIR/app.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
WatchdogSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    # Backwards compatibility
    ln -sf /etc/systemd/system/siteconnector-vps.service /etc/systemd/system/wireguard-vps.service 2>/dev/null || true
    
    # WireGuard Keys prüfen/erstellen
    if [ ! -f "/etc/wireguard/server_private.key" ]; then
        echo "🔑 Generiere WireGuard Keys..."
        WG_PRIVATE_KEY=$(wg genkey)
        WG_PUBLIC_KEY=$(echo "$WG_PRIVATE_KEY" | wg pubkey)
        
        echo "$WG_PRIVATE_KEY" > /etc/wireguard/server_private.key
        echo "$WG_PUBLIC_KEY" > /etc/wireguard/server_public.key
        chmod 600 /etc/wireguard/server_private.key
        chmod 644 /etc/wireguard/server_public.key
        
        echo "✅ WireGuard Keys generiert"
        echo "🔑 VPS Public Key: $WG_PUBLIC_KEY"
    fi
    
    # WireGuard Interface neu starten
    echo "🔄 WireGuard Interface neu starten..."
    wg-quick down wg0 2>/dev/null || true
    sleep 2
    wg-quick up wg0
    systemctl enable wg-quick@wg0
    
    # Services neu starten
    systemctl daemon-reload
    systemctl enable siteconnector-vps
    systemctl start siteconnector-vps
    
    # Status prüfen
    echo "✅ Service-Status:"
    systemctl is-active wg-quick@wg0 && echo "  ✓ WireGuard Interface: Aktiv" || echo "  ✗ WireGuard Interface: Fehler"
    systemctl is-active siteconnector-vps && echo "  ✓ SiteConnector VPS: Aktiv" || echo "  ✗ SiteConnector VPS: Fehler"
    
    # Port prüfen
    if ss -tlnp | grep -q ":8080"; then
        echo "  ✓ Web-Interface verfügbar auf Port 8080"
    else
        echo "  ✗ Port 8080 nicht erreichbar"
    fi
    
    # VPS-Informationen
    VPS_IP=$(curl -s ifconfig.me 2>/dev/null || echo "IP nicht ermittelbar")
    VPS_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "Key nicht gefunden")
    
    echo ""
    echo "🎯 SiteConnector VPS Informationen:"
    echo "===================================="
    echo "VPS IP: $VPS_IP"
    echo "VPS Public Key: $VPS_PUBLIC_KEY"
    echo "Web-Interface: http://$VPS_IP:8080"
    echo ""
    echo "🔧 Gateway Setup-Befehl:"
    echo "sudo siteconnector-gateway setup $VPS_IP $VPS_PUBLIC_KEY"
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    echo "🔄 SiteConnector Gateway aktualisieren..."
    
    # Services stoppen
    systemctl stop gateway-manager 2>/dev/null || true
    systemctl stop gateway-monitoring 2>/dev/null || true
    systemctl stop siteconnector-gateway 2>/dev/null || true
    
    # System-Python-Pakete installieren
    apt install -y python3-psutil python3-requests python3-full python3-pip python3-tk
    
    # Gateway Code aktualisieren
    cp /tmp/siteconnector-update/gateway-software/gateway_manager.py /usr/local/bin/
    cp /tmp/siteconnector-update/gateway-software/system_monitor.py /usr/local/bin/
    cp /tmp/siteconnector-update/gateway-software/gui_app.py /usr/local/bin/ 2>/dev/null || true
    
    # SiteConnector-Befehle erstellen
    cat > /usr/local/bin/siteconnector-gateway << 'EOF'
#!/bin/bash
# SiteConnector Gateway Manager
exec /usr/local/bin/gateway_manager.py "$@"
EOF
    
    # Berechtigungen setzen
    chmod +x /usr/local/bin/gateway_manager.py
    chmod +x /usr/local/bin/system_monitor.py
    chmod +x /usr/local/bin/gui_app.py 2>/dev/null || true
    chmod +x /usr/local/bin/siteconnector-gateway
    
    # Systemd-Services aktualisieren
    echo "📋 SiteConnector Gateway Services konfigurieren..."
    
    cp /tmp/siteconnector-update/gateway-software/systemd/gateway-manager.service /etc/systemd/system/siteconnector-gateway.service 2>/dev/null || \
    cat > /etc/systemd/system/siteconnector-gateway.service << EOF
[Unit]
Description=SiteConnector Gateway Manager
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/gateway_manager.py monitor
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
    
    cp /tmp/siteconnector-update/gateway-software/systemd/gateway-monitoring.service /etc/systemd/system/siteconnector-monitoring.service 2>/dev/null || \
    cat > /etc/systemd/system/siteconnector-monitoring.service << EOF
[Unit]
Description=SiteConnector Gateway Monitoring
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/system_monitor.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    # Backwards compatibility
    ln -sf /etc/systemd/system/siteconnector-gateway.service /etc/systemd/system/gateway-manager.service 2>/dev/null || true
    ln -sf /etc/systemd/system/siteconnector-monitoring.service /etc/systemd/system/gateway-monitoring.service 2>/dev/null || true
    
    # Konfigurationsverzeichnis erstellen
    mkdir -p /etc/siteconnector
    [ -d "/etc/wireguard-gateway" ] && cp -r /etc/wireguard-gateway/* /etc/siteconnector/ 2>/dev/null || true
    
    # Services aktivieren und starten
    systemctl daemon-reload
    systemctl enable siteconnector-gateway
    systemctl enable siteconnector-monitoring
    systemctl start siteconnector-gateway
    systemctl start siteconnector-monitoring
    
    echo "✅ SiteConnector Gateway Update abgeschlossen"
    echo "=============================================="
    echo "Verfügbare Befehle:"
    echo "- siteconnector-gateway status   # System-Status prüfen"
    echo "- siteconnector-gateway setup    # Gateway konfigurieren"
    echo "- siteconnector-gateway start    # Tunnel starten"
    echo "- siteconnector-gateway stop     # Tunnel stoppen"
    echo "- python3 /usr/local/bin/gui_app.py  # GUI öffnen"
fi

# Cleanup
rm -rf /tmp/siteconnector-update

# Update-Information speichern
cat > /var/log/siteconnector-update.log << EOF
# SiteConnector Update Log
# ========================

Update-Datum: $(date)
System-Typ: $SYSTEM_TYPE
Backup-Verzeichnis: $BACKUP_DIR

Update erfolgreich abgeschlossen!
Nächstes Update: sudo siteconnector-update
EOF

echo ""
echo "✅ SiteConnector Update erfolgreich abgeschlossen!"
echo ""
echo "📋 Befehle:"
echo "============"
if [ "$SYSTEM_TYPE" = "vps" ]; then
    echo "Update: sudo siteconnector-update"
    echo "Status: systemctl status siteconnector-vps"
    echo "Logs: journalctl -u siteconnector-vps -f"
else
    echo "Update: sudo siteconnector-update"
    echo "Status: siteconnector-gateway status"
    echo "Setup: siteconnector-gateway setup <VPS_IP> <VPS_KEY>"
    echo "GUI: python3 /usr/local/bin/gui_app.py"
fi
echo ""
echo "🎉 SiteConnector ist bereit!"