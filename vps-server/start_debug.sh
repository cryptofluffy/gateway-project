#!/bin/bash
# Debug Dashboard Starter Script
# Optimiert für Raspberry Pi und lokale Entwicklung

echo "🚀 Starte Debug Dashboard..."

# Wechsle ins VPS-Server Verzeichnis
cd "$(dirname "$0")"

# Prüfe ob Virtual Environment existiert
if [ ! -d "debug_venv" ]; then
    echo "📦 Erstelle Virtual Environment..."
    python3 -m venv debug_venv
    
    echo "📥 Installiere Dependencies..."
    source debug_venv/bin/activate
    pip install flask flask-socketio
else
    echo "📦 Aktiviere Virtual Environment..."
    source debug_venv/bin/activate
fi

echo "🔧 Prüfe Hardware..."
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
    echo "🍓 Raspberry Pi erkannt - optimierte Einstellungen aktiv"
else
    echo "💻 Standard-System erkannt"
fi

echo ""
echo "🌐 Debug Dashboard wird gestartet..."
echo "📍 URLs:"
echo "  ├─ Test: http://localhost:5000/test"
echo "  ├─ Dashboard: http://localhost:5000/"
echo "  ├─ Port-Forwards: http://localhost:5000/port-forwards"
echo "  ├─ System-Stats: http://localhost:5000/api/system-stats"
echo "  └─ System-Health: http://localhost:5000/api/system-health"
echo ""
echo "⚠️  Alle Daten sind simuliert für Debug-Zwecke!"
echo "🛑 Zum Beenden: Ctrl+C"
echo ""

# Starte Debug Dashboard
python3 debug_local.py