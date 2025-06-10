#!/bin/bash
# Debug-Script für Monitoring und Handshake-Anzeige

echo "🔍 Debugging Monitoring und Handshake-Anzeige..."

# WireGuard-Status direkt testen
echo "📊 WireGuard Interface Status:"
wg show wg0

echo ""
echo "📡 API-Test für System-Stats:"
curl -s "http://localhost:8080/api/system-stats" | head -c 500
echo ""

echo ""
echo "👥 API-Test für Clients:"
curl -s "http://localhost:8080/api/clients" | python3 -m json.tool

echo ""
echo "🔧 VPS Logs (letzte 20 Zeilen):"
tail -20 /var/log/wireguard-vps.log

echo ""
echo "🖥️ System-Informationen:"
echo "CPU-Auslastung: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)%"
echo "RAM-Auslastung: $(free | grep Mem | awk '{printf("%.1f%%", $3/$2 * 100.0)}')"

# Temperatur testen (verschiedene Quellen)
echo "🌡️ Temperatur-Tests:"
if [ -f "/sys/class/thermal/thermal_zone0/temp" ]; then
    TEMP=$(cat /sys/class/thermal/thermal_zone0/temp)
    echo "Thermal Zone 0: $((TEMP/1000))°C"
fi

if command -v vcgencmd >/dev/null 2>&1; then
    TEMP=$(vcgencmd measure_temp 2>/dev/null | cut -d'=' -f2 | cut -d"'" -f1)
    echo "vcgencmd: ${TEMP}°C"
fi

if command -v sensors >/dev/null 2>&1; then
    echo "Sensors-Ausgabe:"
    sensors 2>/dev/null | grep -E "(Core|temp)" | head -5
fi

echo ""
echo "🔄 VPS Service neu starten mit Debug-Modus..."
cd /opt/wireguard-vps
pkill -f "python.*app.py" 2>/dev/null

# Monitoring-Environment setzen
export MONITORING_ENABLED=true
export MONITORING_INTERVAL=10
export LOG_LEVEL=DEBUG

source venv/bin/activate 2>/dev/null || true
nohup python3 app.py > /var/log/wireguard-vps-debug.log 2>&1 &

echo "⏱️ Warte 5 Sekunden..."
sleep 5

echo ""
echo "✅ Debug-Test abgeschlossen"
echo "🌐 Dashboard: http://$(curl -s ifconfig.me):8080"
echo "📋 Debug-Logs: tail -f /var/log/wireguard-vps-debug.log"