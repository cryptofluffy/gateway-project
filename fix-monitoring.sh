#!/bin/bash
# Fix für VPS Monitoring Dashboard - behebt fehlende Metriken-Anzeige

echo "🔧 VPS Monitoring Fix wird ausgeführt..."

cd /opt/wireguard-vps

# Virtual Environment aktivieren
source venv/bin/activate

# Monitoring-Module testen
echo "📊 Teste Monitoring-Module..."
python3 -c "
try:
    from monitoring import system_monitor, alert_manager, get_system_health
    stats = system_monitor.get_current_stats()
    print('✅ Monitoring-Module funktionieren')
    print(f'CPU: {stats.get(\"cpu_percent\", \"N/A\")}%')
    print(f'Memory: {stats.get(\"memory_percent\", \"N/A\")}%')
    print(f'Temp: {stats.get(\"cpu_temp\", \"N/A\")}°C')
except Exception as e:
    print(f'❌ Monitoring-Fehler: {e}')
    exit(1)
"

# Services stoppen
echo "🔄 Services neu starten..."
systemctl stop wireguard-vps

# Environment-Variablen setzen
export MONITORING_ENABLED=true
export MONITORING_INTERVAL=30

# App im Hintergrund starten mit korrekter Umgebung
echo "🚀 VPS-App mit Monitoring starten..."
nohup python3 app.py > /var/log/wireguard-vps.log 2>&1 &

sleep 5

# Prüfen ob Port 8080 aktiv ist
if ss -tlnp | grep -q ":8080" || lsof -i :8080 >/dev/null 2>&1; then
    echo "✅ VPS läuft auf Port 8080"
    
    # Test API-Endpunkt
    echo "🧪 Teste Monitoring-API..."
    curl -s "http://localhost:8080/api/system-stats" | head -c 200
    echo ""
    
else
    echo "❌ VPS nicht erreichbar auf Port 8080"
    echo "Logfile prüfen:"
    tail -20 /var/log/wireguard-vps.log
fi

echo "🎯 Monitoring-Fix abgeschlossen"
echo "Dashboard sollte jetzt Metriken anzeigen: http://[VPS_IP]:8080"