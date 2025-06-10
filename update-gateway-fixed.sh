#!/bin/bash
# Quick-Fix Update für Gateway-PC mit korrekter Python-Package-Installation
# Umgeht externally-managed-environment Problem

set -e

echo "🚀 WireGuard Gateway-PC - Quick Update Fix"
echo "=========================================="

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./update-gateway-fixed.sh)"
    exit 1
fi

# Prüfe ob Gateway-PC (mehrere mögliche Installationspfade)
GATEWAY_DETECTED=false
if [ -f "/usr/local/bin/gateway_manager.py" ] || [ -f "/usr/local/bin/gateway-manager" ] || [ -d "/etc/wireguard-gateway" ] || [ -f "/home/*/gateway_manager.py" ]; then
    GATEWAY_DETECTED=true
fi

if [ "$GATEWAY_DETECTED" = "false" ]; then
    echo "❌ Kein Gateway-PC erkannt - Script nur für Gateway-PC"
    echo "Prüfe: /usr/local/bin/gateway_manager.py, /etc/wireguard-gateway/"
    echo "Falls Gateway-PC installiert ist, führe das normale Update aus:"
    echo "curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/update-complete-system.sh | sudo bash"
    exit 1
fi

echo "🌐 Gateway-PC System erkannt"

# Backup erstellen
echo "💾 Erstelle System-Backup..."
BACKUP_DIR="/var/backups/wireguard-gateway-$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r /etc/wireguard-gateway "$BACKUP_DIR/" 2>/dev/null || true
cp -r /etc/wireguard "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ Backup erstellt in: $BACKUP_DIR"

# System Updates
echo "📦 System-Updates installieren..."
apt update && apt upgrade -y

# Python-Abhängigkeiten über apt installieren (kein pip!)
echo "📦 System-Python-Pakete installieren..."
apt install -y python3-psutil python3-requests python3-full python3-pip git
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
    echo "✅ Gateway-Code aktualisiert"
fi

# Monitoring-Setup
echo "📊 Monitoring-Setup..."
echo "GATEWAY_MONITORING_ENABLED=true" >> /etc/environment
echo "METRICS_SEND_INTERVAL=60" >> /etc/environment

# Gateway-Services starten und konfigurieren
echo "🔄 Gateway-Services starten..."

# Existierendes Interface herunterfahren
wg-quick down gateway 2>/dev/null || true
sleep 2

# Gateway neu starten
if [ -f "/etc/wireguard/gateway.conf" ]; then
    wg-quick up gateway
    systemctl enable wg-quick@gateway
    echo "  ✓ Gateway Interface gestartet"
else
    echo "  ✗ Gateway-Konfiguration nicht gefunden (/etc/wireguard/gateway.conf)"
    echo "  → Führe Setup aus: sudo gateway-manager setup [VPS_IP] [VPS_PUBLIC_KEY]"
fi

# Service-Status prüfen
echo "🔍 Service-Status nach Update:"
if wg show gateway >/dev/null 2>&1; then
    echo "  ✓ WireGuard Gateway: Aktiv"
    wg show gateway | head -3
else
    echo "  ✗ WireGuard Gateway: Inaktiv"
fi

# Monitoring-Service starten (falls vorhanden)
if [ -f "/usr/local/bin/gateway_manager.py" ]; then
    echo "🔄 Monitoring-Service starten..."
    nohup /usr/local/bin/gateway_manager.py monitor > /var/log/gateway-monitor.log 2>&1 &
    echo "  ✓ Monitoring im Hintergrund gestartet"
fi

# Update-Information speichern
echo "💾 Update-Information speichern..."
cat > /var/log/wireguard-gateway-update.log << EOF
# WireGuard Gateway-PC Update Log
# ===============================

Update-Datum: $(date)
System-Typ: gateway
Backup-Verzeichnis: $BACKUP_DIR

Installierte Features:
- ✅ System-Monitoring (CPU, RAM, Temperatur)
- ✅ Python-Pakete über apt (kein pip-Konflikt)
- ✅ Aktualisierte Gateway-Manager Scripts
- ✅ Monitoring-Konfiguration aktiviert

Python-Pakete installiert:
- python3-psutil (System-Monitoring)
- python3-requests (HTTP-Client für VPS)
- python3-full (Vollständige Python-Installation)

EOF

echo ""
echo "✅ Gateway-PC Update erfolgreich abgeschlossen!"
echo ""
echo "🌐 Gateway-PC Update abgeschlossen"
echo "==================================="
echo "Verfügbare Befehle:"
echo "- gateway-manager status   # System-Status prüfen"
echo "- gateway-manager monitor  # Monitoring starten"
echo "- gateway-gui             # GUI öffnen (falls installiert)"
echo ""
echo "💡 System-Monitoring ist jetzt aktiviert und sendet Metriken an das VPS"

echo ""
echo "📋 Nächste Schritte:"
echo "==================="
echo "1. System-Status prüfen: gateway-manager status"
echo "2. Monitoring testen: gateway-manager monitor"
echo "3. VPS-Verbindung prüfen"
echo ""
echo "🎉 Ihr Gateway-PC ist jetzt vollständig optimiert!"