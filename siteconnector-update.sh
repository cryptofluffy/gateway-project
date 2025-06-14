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

# Selbst-Installation prüfen und ausführen
if [ ! -f "/usr/local/bin/siteconnector-update" ]; then
    echo "📦 Installiere siteconnector-update Kommando..."
    cp "$0" /usr/local/bin/siteconnector-update
    chmod +x /usr/local/bin/siteconnector-update
    echo "✅ siteconnector-update Kommando installiert"
    echo "💡 Nächstes Mal verwende: sudo siteconnector-update"
fi

# System-Typ erkennen (erweiterte Erkennung)
if [ -f "/opt/siteconnector-vps/app.py" ] || [ -f "/opt/wireguard-vps/app.py" ]; then
    SYSTEM_TYPE="vps"
    echo "🖥️ SiteConnector VPS erkannt"
elif [ -f "/usr/local/bin/gateway-manager" ] || [ -f "/usr/local/bin/siteconnector-gateway" ] || [ -f "/usr/local/bin/gateway_manager.py" ]; then
    SYSTEM_TYPE="gateway"
    echo "🌐 SiteConnector Gateway erkannt"
elif systemctl is-enabled wireguard-vps &>/dev/null || systemctl is-active wireguard-vps &>/dev/null; then
    SYSTEM_TYPE="vps"
    echo "🖥️ Legacy VPS Installation erkannt"
elif systemctl is-enabled gateway-manager &>/dev/null || systemctl is-active gateway-manager &>/dev/null; then
    SYSTEM_TYPE="gateway" 
    echo "🌐 Legacy Gateway Installation erkannt"
elif systemctl is-enabled siteconnector-gateway &>/dev/null || systemctl is-active siteconnector-gateway &>/dev/null; then
    SYSTEM_TYPE="gateway" 
    echo "🌐 SiteConnector Gateway Service erkannt"
elif [ -f "/etc/wireguard/gateway.conf" ] || [ -f "/etc/wireguard-gateway/config.json" ]; then
    SYSTEM_TYPE="gateway"
    echo "🌐 Gateway anhand WireGuard-Config erkannt"
else
    # Fallback: Prüfe ob WireGuard installiert ist (wahrscheinlich Gateway)
    if which wg &>/dev/null && ! [ -d "/opt/wireguard-vps" ] && ! [ -d "/opt/siteconnector-vps" ]; then
        SYSTEM_TYPE="gateway"
        echo "🌐 Gateway anhand WireGuard-Installation erkannt (Fallback)"
    else
        echo "❌ SiteConnector System nicht erkannt"
        echo "💡 Installiere zuerst SiteConnector:"
        echo "   VPS: curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/vps-server/install.sh | sudo bash"
        echo "   Gateway: curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-software/install.sh | sudo bash"
        exit 1
    fi
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
    if [ -f "/tmp/siteconnector-update/vps-server/systemd/wireguard-vps.service" ]; then
        cp /tmp/siteconnector-update/vps-server/systemd/wireguard-vps.service /etc/systemd/system/siteconnector-vps.service
    else
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
    fi
    
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
    echo "📦 Python-Abhängigkeiten installieren..."
    apt install -y python3-psutil python3-requests python3-full python3-pip python3-tk
    
    # Gateway Code aktualisieren
    echo "📁 Gateway-Software aktualisieren..."
    
    # Network Scanner zuerst - KRITISCH für Geräteerkennung
    echo "📡 Network Scanner installieren..."
    if [ -f "/tmp/siteconnector-update/gateway-software/network-scanner.py" ]; then
        cp /tmp/siteconnector-update/gateway-software/network-scanner.py /usr/local/bin/
        chmod +x /usr/local/bin/network-scanner.py
        echo "✅ network-scanner.py installiert"
    else
        echo "⚠️ Datei nicht gefunden, lade von GitHub..."
        wget -q https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/gateway-software/network-scanner.py -O /usr/local/bin/network-scanner.py
        chmod +x /usr/local/bin/network-scanner.py
        echo "✅ network-scanner.py von GitHub installiert"
    fi
    
    # Andere Gateway-Dateien
    cp /tmp/siteconnector-update/gateway-software/gateway_manager.py /usr/local/bin/ 2>/dev/null || true
    cp /tmp/siteconnector-update/gateway-software/system_monitor.py /usr/local/bin/ 2>/dev/null || true
    cp /tmp/siteconnector-update/gateway-software/gui_app.py /usr/local/bin/ 2>/dev/null || true
    
    # SiteConnector-Befehle erstellen
    cat > /usr/local/bin/siteconnector-gateway << 'EOF'
#!/bin/bash
# SiteConnector Gateway Manager
exec /usr/local/bin/gateway_manager.py "$@"
EOF
    
    # Berechtigungen setzen
    chmod +x /usr/local/bin/gateway_manager.py 2>/dev/null || true
    chmod +x /usr/local/bin/system_monitor.py 2>/dev/null || true
    chmod +x /usr/local/bin/network-scanner.py 2>/dev/null || true
    chmod +x /usr/local/bin/gui_app.py 2>/dev/null || true
    chmod +x /usr/local/bin/siteconnector-gateway 2>/dev/null || true
    
    # Prüfe ob Network Scanner installiert wurde
    if [ -f "/usr/local/bin/network-scanner.py" ]; then
        echo "✅ network-scanner.py erfolgreich installiert"
    else
        echo "❌ network-scanner.py FEHLT - Geräteerkennung wird nicht funktionieren!"
    fi
    
    # Systemd-Services aktualisieren
    echo "📋 SiteConnector Gateway Services konfigurieren..."
    
    # Hauptservice
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
    
    # Monitoring service
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
    
    # Network scanner service and timer - KRITISCH für Geräteerkennung
    echo "📡 Network Scanner Services installieren..."
    if [ -f "/tmp/siteconnector-update/gateway-software/systemd/network-scanner.service" ]; then
        cp /tmp/siteconnector-update/gateway-software/systemd/network-scanner.service /etc/systemd/system/
        echo "✅ network-scanner.service installiert"
    else
        echo "⚠️ Service-Datei nicht gefunden, erstelle manuell..."
        cat > /etc/systemd/system/network-scanner.service << 'EOF'
[Unit]
Description=Network Scanner for Gateway Devices
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/network-scanner.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
        echo "✅ network-scanner.service manuell erstellt"
    fi
    
    if [ -f "/tmp/siteconnector-update/gateway-software/systemd/network-scanner.timer" ]; then
        cp /tmp/siteconnector-update/gateway-software/systemd/network-scanner.timer /etc/systemd/system/
        echo "✅ network-scanner.timer installiert"
    else
        echo "⚠️ Timer-Datei nicht gefunden, erstelle manuell..."
        cat > /etc/systemd/system/network-scanner.timer << 'EOF'
[Unit]
Description=Run Network Scanner every 5 minutes
Requires=network-scanner.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Unit=network-scanner.service

[Install]
WantedBy=timers.target
EOF
        echo "✅ network-scanner.timer manuell erstellt"
    fi
    
    # Network scanner installer script
    if [ -f "/tmp/siteconnector-update/scripts/install-network-scanner.sh" ]; then
        cp /tmp/siteconnector-update/scripts/install-network-scanner.sh /usr/local/bin/
        chmod +x /usr/local/bin/install-network-scanner.sh
        echo "✅ install-network-scanner.sh installiert"
    else
        echo "⚠️ install-network-scanner.sh nicht gefunden"
    fi
    
    # Backwards compatibility
    ln -sf /etc/systemd/system/siteconnector-gateway.service /etc/systemd/system/gateway-manager.service 2>/dev/null || true
    ln -sf /etc/systemd/system/siteconnector-monitoring.service /etc/systemd/system/gateway-monitoring.service 2>/dev/null || true
    
    # Konfigurationsverzeichnis erstellen
    mkdir -p /etc/siteconnector
    [ -d "/etc/wireguard-gateway" ] && cp -r /etc/wireguard-gateway/* /etc/siteconnector/ 2>/dev/null || true
    
    # Services aktivieren und starten
    systemctl daemon-reload
    systemctl enable siteconnector-gateway 2>/dev/null || true
    systemctl enable siteconnector-monitoring 2>/dev/null || true
    systemctl start siteconnector-gateway 2>/dev/null || true
    systemctl start siteconnector-monitoring 2>/dev/null || true
    
    # Network Scanner Service - KRITISCH
    if [ -f "/etc/systemd/system/network-scanner.timer" ]; then
        systemctl enable network-scanner.timer
        systemctl start network-scanner.timer
        echo "✅ Network Scanner Timer gestartet"
        
        # Status prüfen
        if systemctl is-active --quiet network-scanner.timer; then
            echo "✅ Network Scanner läuft korrekt"
        else
            echo "❌ Network Scanner konnte nicht gestartet werden"
            systemctl status network-scanner.timer --no-pager
        fi
    else
        echo "❌ Network Scanner Timer nicht installiert - kann nicht gestartet werden"
    fi
    
    # DHCP-Server für Server-Netzwerk (Port B) einrichten
    echo "🌐 DHCP-Server für Server-Netzwerk konfigurieren..."
    
    # DHCP-Server installieren
    apt install -y isc-dhcp-server
    
    # Interface für DHCP konfigurieren
    cat > /etc/default/isc-dhcp-server << 'EOF'
# Interface für DHCP-Server (Port B / Server-Netz)
INTERFACESv4="eth1"
INTERFACESv6=""
EOF
    
    # DHCP-Konfiguration für Server-Netzwerk
    cat > /etc/dhcp/dhcpd.conf << 'EOF'
# DHCP-Konfiguration für Server-Netzwerk (Port B)
default-lease-time 3600;
max-lease-time 7200;
authoritative;

# Server-Netzwerk (Port B / eth1) - Internet über VPN
subnet 10.0.0.0 netmask 255.255.255.0 {
    range 10.0.0.100 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    option domain-name "server.local";
    default-lease-time 3600;
    max-lease-time 7200;
}
EOF
    
    # eth1 Interface als Gateway konfigurieren
    ip addr add 10.0.0.1/24 dev eth1 2>/dev/null || true
    ip link set eth1 up
    echo "✅ eth1 als Gateway (10.0.0.1/24) konfiguriert"
    
    # DHCP-Server starten
    systemctl enable isc-dhcp-server
    systemctl start isc-dhcp-server
    
    if systemctl is-active --quiet isc-dhcp-server; then
        echo "✅ DHCP-Server läuft - Server bekommen automatisch IPs (10.0.0.100-200)"
    else
        echo "⚠️ DHCP-Server Probleme:"
        systemctl status isc-dhcp-server --no-pager
    fi
    
    # Test network scanner functionality
    echo "🧪 Testing Network Scanner..."
    if [ -f "/usr/local/bin/network-scanner.py" ]; then
        python3 /usr/local/bin/network-scanner.py || echo "⚠️ Network scanner test completed (normal if no devices found yet)"
    else
        echo "❌ Network Scanner Script fehlt - kann nicht getestet werden"
        echo "📁 Verfügbare Dateien in /tmp/siteconnector-update/gateway-software/:"
        ls -la /tmp/siteconnector-update/gateway-software/ 2>/dev/null || echo "Verzeichnis nicht gefunden"
    fi
    
    echo "✅ SiteConnector Gateway Update abgeschlossen"
    echo "=============================================="
    echo "🖥️ Gateway-PC Konfiguration:"
    echo "   Port A (eth0): Heimnetz-Client (DHCP von FritzBox)"
    echo "   Port B (eth1): Server-Gateway (10.0.0.1/24)"
    echo ""
    echo "🌐 Server-Netzwerk:"
    echo "   DHCP-Bereich: 10.0.0.100 - 10.0.0.200"
    echo "   Gateway: 10.0.0.1"
    echo "   DNS: 8.8.8.8, 8.8.4.4"
    echo "   Internet: Über VPN-Tunnel"
    echo ""
    echo "📋 Verfügbare Befehle:"
    echo "- siteconnector-gateway status   # System-Status prüfen"
    echo "- siteconnector-gateway setup    # Gateway konfigurieren"
    echo "- siteconnector-gateway start    # Tunnel starten"
    echo "- siteconnector-gateway stop     # Tunnel stoppen"
    echo "- python3 /usr/local/bin/gui_app.py  # GUI öffnen"
    echo ""
    echo "🔍 Server-Erkennung:"
    echo "   Network Scanner läuft alle 5 Minuten"
    echo "   Server erscheinen automatisch im Dashboard"
    echo "   Dashboard: http://$(curl -s ifconfig.me 2>/dev/null || echo 'VPS-IP'):8080/dashboard"
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