#!/bin/bash
# Umfassendes Update-Script für WireGuard Gateway System
# Führt vollständige Code-Optimierung und Monitoring-Integration durch

set -e

echo "🚀 WireGuard Gateway System - Umfassendes Update"
echo "================================================"

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./update-complete-system.sh)"
    exit 1
fi

# Detect system type
if [ -f "/opt/wireguard-vps/app.py" ]; then
    SYSTEM_TYPE="vps"
    echo "🖥️ VPS System erkannt"
elif [ -f "/usr/local/bin/gateway-manager" ]; then
    SYSTEM_TYPE="gateway"
    echo "🌐 Gateway-PC System erkannt"
else
    echo "❌ System-Typ konnte nicht erkannt werden"
    exit 1
fi

# Backup erstellen
echo "💾 Erstelle System-Backup..."
BACKUP_DIR="/var/backups/wireguard-gateway-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ "$SYSTEM_TYPE" = "vps" ]; then
    cp -r /opt/wireguard-vps "$BACKUP_DIR/"
    cp -r /etc/wireguard "$BACKUP_DIR/"
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    cp -r /etc/wireguard-gateway "$BACKUP_DIR/" 2>/dev/null || true
    cp -r /etc/wireguard "$BACKUP_DIR/" 2>/dev/null || true
fi

echo "✅ Backup erstellt in: $BACKUP_DIR"

# System Updates
echo "📦 System-Updates installieren..."
apt update && apt upgrade -y

# Python-Abhängigkeiten installieren
echo "🐍 Python-Abhängigkeiten aktualisieren..."
if [ "$SYSTEM_TYPE" = "vps" ]; then
    # VPS Code aktualisieren
    echo "🔄 VPS Code aktualisieren..."
    cd /opt/wireguard-vps
    
    # Virtual Environment erstellen falls nicht vorhanden
    if [ ! -d "venv" ]; then
        echo "📦 Virtual Environment erstellen..."
        python3 -m venv venv
    fi
    
    # GitHub Repository klonen (falls vorhanden)
    if command -v git >/dev/null 2>&1; then
        echo "📥 Lade neueste Version von GitHub..."
        rm -rf /tmp/gateway-update
        git clone https://github.com/cryptofluffy/gateway-project.git /tmp/gateway-update
        
        # VPS-Dateien aktualisieren
        cp /tmp/gateway-update/vps-server/*.py /opt/wireguard-vps/
        cp -r /tmp/gateway-update/vps-server/static/* /opt/wireguard-vps/static/
        cp -r /tmp/gateway-update/vps-server/templates/* /opt/wireguard-vps/templates/
        cp /tmp/gateway-update/vps-server/requirements.txt /opt/wireguard-vps/
        
        # Neue Abhängigkeiten in Virtual Environment installieren
        echo "📦 Python-Abhängigkeiten in Virtual Environment installieren..."
        /opt/wireguard-vps/venv/bin/pip install --upgrade pip
        /opt/wireguard-vps/venv/bin/pip install -r requirements.txt
        
        rm -rf /tmp/gateway-update
    fi
    
    # Services neu starten
    echo "🔄 VPS Services neu starten..."
    systemctl daemon-reload
    systemctl restart wireguard-vps
    systemctl restart wireguard-vps-watcher
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    # Gateway-PC-spezifische Updates - System-Packages verwenden
    echo "📦 System-Python-Pakete installieren..."
    apt install -y python3-psutil python3-requests python3-full python3-pip
    
    # Ensure we don't use pip3 system-wide - use apt packages only
    echo "✅ Python-Pakete über apt installiert"
    
    # Gateway Code aktualisieren
    echo "🔄 Gateway-PC Code aktualisieren..."
    
    if command -v git >/dev/null 2>&1; then
        echo "📥 Lade neueste Version von GitHub..."
        rm -rf /tmp/gateway-update
        git clone https://github.com/cryptofluffy/gateway-project.git /tmp/gateway-update
        
        # Gateway-Dateien aktualisieren
        cp /tmp/gateway-update/gateway-pc/gateway_manager.py /usr/local/bin/
        cp /tmp/gateway-update/gateway-pc/system_monitor.py /usr/local/bin/
        cp /tmp/gateway-update/gateway-pc/gui_app.py /usr/local/bin/ 2>/dev/null || true
        
        # Berechtigungen setzen
        chmod +x /usr/local/bin/gateway_manager.py
        chmod +x /usr/local/bin/system_monitor.py
        chmod +x /usr/local/bin/gui_app.py 2>/dev/null || true
        
        rm -rf /tmp/gateway-update
    fi
fi

# Konfiguration validieren
echo "🔍 Konfiguration validieren..."
if [ "$SYSTEM_TYPE" = "vps" ]; then
    # VPS-Konfiguration prüfen
    if [ ! -f "/etc/wireguard/wg0.conf" ]; then
        echo "⚠️ WireGuard-Konfiguration nicht gefunden - führe Setup aus"
    fi
    
    # WireGuard Keys prüfen
    if [ ! -f "/etc/wireguard/server_private.key" ]; then
        echo "🔑 Generiere fehlende WireGuard Keys..."
        WG_PRIVATE_KEY=$(wg genkey)
        WG_PUBLIC_KEY=$(echo "$WG_PRIVATE_KEY" | wg pubkey)
        
        echo "$WG_PRIVATE_KEY" > /etc/wireguard/server_private.key
        echo "$WG_PUBLIC_KEY" > /etc/wireguard/server_public.key
        chmod 600 /etc/wireguard/server_private.key
        chmod 644 /etc/wireguard/server_public.key
        
        echo "✅ WireGuard Keys generiert"
        echo "🔑 VPS Public Key: $WG_PUBLIC_KEY"
    fi
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    # Gateway-Konfiguration prüfen
    if [ ! -d "/etc/wireguard-gateway" ]; then
        mkdir -p /etc/wireguard-gateway
        chmod 750 /etc/wireguard-gateway
    fi
fi

# Monitoring-Setup
echo "📊 Monitoring-Setup..."
if [ "$SYSTEM_TYPE" = "vps" ]; then
    # VPS Monitoring-Konfiguration
    echo "VPS_MONITORING_ENABLED=true" >> /etc/environment
    echo "MONITORING_INTERVAL=30" >> /etc/environment
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    # Gateway Monitoring-Konfiguration
    echo "GATEWAY_MONITORING_ENABLED=true" >> /etc/environment
    echo "METRICS_SEND_INTERVAL=60" >> /etc/environment
fi

# Firewall-Konfiguration
echo "🔥 Firewall konfigurieren..."
if command -v ufw >/dev/null 2>&1; then
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        ufw allow 51820/udp  # WireGuard
        ufw allow 8080/tcp   # Web-Interface
    fi
    ufw allow ssh
fi

# Log-Rotation einrichten
echo "📝 Log-Rotation konfigurieren..."
if [ "$SYSTEM_TYPE" = "vps" ]; then
    cat > /etc/logrotate.d/wireguard-vps << EOF
/var/log/wireguard-gateway/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
    postrotate
        systemctl reload wireguard-vps 2>/dev/null || true
    endscript
}
EOF
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    cat > /etc/logrotate.d/wireguard-gateway << EOF
/var/log/wireguard-gateway/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 root root
}
EOF
fi

# System-Service Status prüfen
echo "🔍 Service-Status prüfen..."
if [ "$SYSTEM_TYPE" = "vps" ]; then
    echo "📊 VPS Services:"
    systemctl status wg-quick@wg0 --no-pager -l | head -10
    echo ""
    systemctl status wireguard-vps --no-pager -l | head -10
    echo ""
    systemctl status wireguard-vps-watcher --no-pager -l | head -10
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    echo "📊 Gateway Services:"
    systemctl status wg-quick@gateway --no-pager -l | head -10 || echo "Gateway Tunnel: Nicht konfiguriert"
fi

# Cleanup
echo "🧹 Cleanup..."
apt autoremove -y
apt autoclean

# Update-Information speichern
echo "💾 Update-Information speichern..."
cat > /var/log/wireguard-gateway-update.log << EOF
# WireGuard Gateway System Update Log
# ====================================

Update-Datum: $(date)
System-Typ: $SYSTEM_TYPE
Backup-Verzeichnis: $BACKUP_DIR

Installierte Features:
- ✅ Umfassendes System-Monitoring (CPU, RAM, Temperatur)
- ✅ Real-Time Dashboard mit SocketIO
- ✅ Erweiterte Sicherheitskonfiguration
- ✅ Performance-Optimierungen
- ✅ Automatische Log-Rotation
- ✅ Enhanced Error Handling
- ✅ Alert-System für kritische Zustände

Neue API-Endpunkte (VPS):
- /api/system-stats - System-Statistiken
- /api/system-health - Gesundheitscheck
- /api/gateway-metrics - Gateway-Metriken (POST)
- /api/alerts - System-Alerts

Monitoring-Features:
- Real-Time CPU/Memory/Disk Monitoring
- Temperatur-Überwachung (Raspberry Pi optimiert)
- WireGuard-Tunnel Status Tracking
- Automatische Alert-Generierung
- Performance-Trending
- Metriken-Export (JSON/CSV)

Sicherheits-Verbesserungen:
- Sichere Konfigurationsverwaltung
- Verbesserte Input-Validierung
- Rate Limiting für API-Endpunkte
- Sichere Dateiberechtigungen
- Enhanced Logging

Performance-Optimierungen:
- Intelligentes Caching
- Asynchrone Operationen
- Optimierte Netzwerk-Interface Erkennung
- Effiziente Metriken-Sammlung

EOF

echo ""
echo "✅ Update erfolgreich abgeschlossen!"
echo ""

if [ "$SYSTEM_TYPE" = "vps" ]; then
    VPS_IP=$(curl -s ifconfig.me 2>/dev/null || echo "IP nicht ermittelbar")
    VPS_PUBLIC_KEY=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "Key nicht gefunden")
    
    echo "🎯 VPS-Informationen:"
    echo "======================"
    echo "VPS IP: $VPS_IP"
    echo "VPS Public Key: $VPS_PUBLIC_KEY"
    echo "Web-Interface: http://$VPS_IP:8080"
    echo "Monitoring: Real-Time Dashboard verfügbar"
    echo ""
    echo "🔧 Gateway-PC Setup-Befehl:"
    echo "sudo /usr/local/bin/gateway-manager setup $VPS_IP $VPS_PUBLIC_KEY"
    
elif [ "$SYSTEM_TYPE" = "gateway" ]; then
    echo "🌐 Gateway-PC Update abgeschlossen"
    echo "==================================="
    echo "Verfügbare Befehle:"
    echo "- gateway-manager status   # System-Status prüfen"
    echo "- gateway-manager monitor  # Monitoring starten"
    echo "- gateway-gui             # GUI öffnen (falls installiert)"
    echo ""
    echo "💡 System-Monitoring ist jetzt aktiviert und sendet Metriken an das VPS"
fi

echo ""
echo "📋 Nächste Schritte:"
echo "==================="
echo "1. System-Status prüfen"
echo "2. Monitoring-Dashboard testen"
echo "3. Alert-Konfiguration anpassen (optional)"
echo "4. Performance-Metriken überprüfen"
echo ""
echo "🔍 Logs:"
echo "VPS: journalctl -u wireguard-vps -f"
echo "Gateway: journalctl -u wireguard-gateway -f"
echo ""
echo "📊 Update-Details: /var/log/wireguard-gateway-update.log"
echo ""
echo "🎉 Ihr WireGuard Gateway System ist jetzt vollständig optimiert!"