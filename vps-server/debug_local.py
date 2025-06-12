#!/usr/bin/env python3
"""
Debug-Version für lokale Entwicklung
Optimiert für Raspberry Pi und ressourcenschonende Tests
"""

import os
import time
import json
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

# Debug: Template-Pfad prüfen
current_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(current_dir, 'templates')

print(f"🔍 Debug-Informationen:")
print(f"Current Dir: {current_dir}")
print(f"Template Dir: {template_dir}")
print(f"Template Dir exists: {os.path.exists(template_dir)}")

if os.path.exists(template_dir):
    print(f"Templates gefunden: {os.listdir(template_dir)}")

# Flask App Setup mit Raspberry Pi Optimierungen
app = Flask(__name__, template_folder=template_dir)
app.config.update({
    'SECRET_KEY': 'debug-key-not-for-production',
    'DEBUG': True,
    'TESTING': True
})

# SocketIO für Real-Time Testing (optimiert)
# Längere Ping-Intervalle für schwache Hardware
socketio = SocketIO(app, cors_allowed_origins="*", 
                   ping_interval=30, ping_timeout=10)

@app.route('/')
def test():
    """Debug-Dashboard mit optimierten Mock-Daten"""
    print("📍 Route '/' wurde aufgerufen")
    try:
        # Mock-Daten für realistisches Testen
        mock_status = {
            'status': 'active', 
            'output': 'Debug WireGuard Interface - Simuliert für Testing',
            'timestamp': datetime.now().isoformat()
        }
        
        mock_clients = [
            {
                'name': 'Debug-Client-1',
                'ip': '10.8.0.2',
                'public_key': 'debug_key_1234...==',
                'last_handshake': '2 minutes ago',
                'status': 'connected'
            },
            {
                'name': 'Debug-Client-2', 
                'ip': '10.8.0.3',
                'public_key': 'debug_key_5678...==',
                'last_handshake': 'never',
                'status': 'disconnected'
            }
        ]
        
        # System-Stats für Dashboard
        system_stats = get_debug_system_stats()
        
        return render_template('dashboard.html', 
                             status=mock_status, 
                             clients=mock_clients,
                             port_forwards={},
                             system_stats=system_stats,
                             debug_mode=True)
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Debug Template Error</h1><p>{e}</p><p>Template-Pfad: {template_dir}</p>"

@app.route('/port-forwards')
def port_forwards():
    """Debug Port-Forwards mit erweiterten Mock-Daten"""
    print("📍 Route '/port-forwards' wurde aufgerufen")
    try:
        # Erweiterte Mock Port-Forwards für besseres Testing
        mock_port_forwards = {
            '8080_tcp': {
                'external_port': 8080,
                'internal_ip': '10.0.0.100',
                'internal_port': 80,
                'protocol': 'tcp',
                'created': '2024-01-15T10:30:00',
                'description': 'Debug Web Server',
                'status': 'active'
            },
            '2222_tcp': {
                'external_port': 2222,
                'internal_ip': '10.0.0.101', 
                'internal_port': 22,
                'protocol': 'tcp',
                'created': '2024-01-15T11:45:00',
                'description': 'Debug SSH Access',
                'status': 'active'
            },
            '3000_tcp': {
                'external_port': 3000,
                'internal_ip': '10.0.0.102',
                'internal_port': 3000,
                'protocol': 'tcp', 
                'created': '2024-01-16T09:15:00',
                'description': 'Debug App Server',
                'status': 'inactive'
            }
        }
        
        return render_template('port_forwards.html', 
                             port_forwards=mock_port_forwards,
                             debug_mode=True)
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Debug Template Error</h1><p>{e}</p>"

@app.route('/topology')
def network_topology():
    """Interaktive Netzwerk-Topologie Ansicht"""
    print("📍 Route '/topology' wurde aufgerufen")
    try:
        return render_template('network_topology.html')
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Template Error</h1><p>{e}</p>"

@app.route('/traffic-flow')
def traffic_flow():
    """Sankey-Style Traffic Flow Diagramm"""
    print("📍 Route '/traffic-flow' wurde aufgerufen")
    try:
        return render_template('traffic_flow.html')
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Template Error</h1><p>{e}</p>"

@app.route('/locations')
def location_manager():
    """Multi-Location VPN Management Dashboard"""
    print("📍 Route '/locations' wurde aufgerufen")
    try:
        return render_template('location_manager.html')
    except Exception as e:
        print(f"❌ Template-Fehler: {e}")
        return f"<h1>Template Error</h1><p>{e}</p>"

@app.route('/test')
def simple_test():
    """Einfacher Funktionstest für Debug-Setup"""
    is_pi, is_low_memory = detect_hardware()
    
    hardware_info = f"""
    <h1>🚀 Debug-Server funktioniert!</h1>
    <h2>📊 Hardware-Informationen:</h2>
    <ul>
        <li>Raspberry Pi erkannt: {'Ja 🍓' if is_pi else 'Nein 💻'}</li>
        <li>Wenig Arbeitsspeicher: {'Ja' if is_low_memory else 'Nein'}</li>
        <li>Optimierungen aktiv: {'Ja' if (is_pi or is_low_memory) else 'Nein'}</li>
    </ul>
    <h2>🔗 Verfügbare Debug-Endpunkte:</h2>
    <ul>
        <li><a href="/">Dashboard</a> - Haupt-Debug-Interface</li>
        <li><a href="/topology" style="color: #00ff88; font-weight: bold;">🌐 Network Topology</a> - Interaktive Netzwerk-Visualisierung</li>
        <li><a href="/traffic-flow" style="color: #f39c12; font-weight: bold;">🔄 Traffic Flow</a> - Sankey-Style Flow Diagramm</li>
        <li><a href="/locations" style="color: #9b59b6; font-weight: bold;">🌍 Location Manager</a> - Multi-Location VPN Management</li>
        <li><a href="/port-forwards">Port-Forwards</a> - Debug Port-Weiterleitungen</li>
        <li><a href="/api/system-stats">System-Stats API</a> - JSON System-Statistiken</li>
        <li><a href="/api/system-health">System-Health API</a> - JSON Gesundheits-Status</li>
    </ul>
    <p><em>Alle Daten sind simuliert für Debug-Zwecke!</em></p>
    """
    
    return hardware_info

# Hardware-Erkennung für adaptive Debug-Konfiguration
def detect_hardware():
    """Erkennt Hardware für optimierte Debug-Einstellungen"""
    is_pi = False
    is_low_memory = False
    
    try:
        # Raspberry Pi Erkennung
        with open('/proc/cpuinfo', 'r') as f:
            content = f.read().lower()
            if 'raspberry pi' in content or 'bcm' in content:
                is_pi = True
                print("🍓 Raspberry Pi erkannt - Debug-Modus optimiert")
        
        # Memory Check
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    mem_kb = int(line.split()[1])
                    mem_mb = mem_kb // 1024
                    if mem_mb < 1024:
                        is_low_memory = True
                        print(f"📊 Wenig RAM erkannt ({mem_mb}MB) - Debug reduziert")
                    break
    except:
        print("⚠️ Hardware-Erkennung fehlgeschlagen - Standard-Einstellungen")
    
    return is_pi, is_low_memory

# Mock System Monitoring für Debug
def get_debug_system_stats():
    """Simuliert System-Statistiken für Debug-Dashboard"""
    import random
    
    # Simuliere realistische aber harmlose Werte
    return {
        'timestamp': datetime.now().isoformat(),
        'cpu_percent': round(random.uniform(5, 25), 1),  # Niedrige CPU-Last
        'cpu_temp': round(random.uniform(35, 55), 1),    # Normale Temperaturen
        'memory_total': 1073741824,  # 1GB
        'memory_used': random.randint(200000000, 600000000),
        'memory_percent': round(random.uniform(20, 60), 1),
        'disk_total': 16106127360,  # 15GB
        'disk_used': random.randint(2000000000, 8000000000),
        'disk_percent': round(random.uniform(15, 50), 1),
        'network_bytes_sent': random.randint(1000000, 10000000),
        'network_bytes_recv': random.randint(5000000, 50000000),
        'wireguard_connected_peers': random.randint(0, 3),
        'wireguard_status': random.choice(['active', 'inactive', 'no_peers']),
        'uptime_seconds': random.randint(3600, 86400),
        'load_average': [round(random.uniform(0.1, 0.8), 2) for _ in range(3)]
    }

@app.route('/api/system-stats')
def api_system_stats():
    """API-Endpunkt für Debug-System-Statistiken"""
    return jsonify({
        'success': True,
        'data': get_debug_system_stats()
    })

@app.route('/api/system-health')
def api_system_health():
    """API-Endpunkt für Debug-System-Gesundheit"""
    stats = get_debug_system_stats()
    return jsonify({
        'success': True,
        'data': {
            'status': 'good',
            'health_score': random.randint(75, 95),
            'current_stats': stats,
            'alerts': [],  # Keine Alerts im Debug-Modus
            'timestamp': datetime.now().isoformat()
        }
    })

# SocketIO Events für Real-Time Debug
@socketio.on('connect')
def handle_connect():
    """Client-Verbindung für Debug-Monitoring"""
    print(f"🔗 Debug-Client verbunden: {request.sid if 'request' in globals() else 'unknown'}")
    emit('status', {'message': 'Debug-Monitoring verbunden'})

@socketio.on('request_stats')
def handle_stats_request():
    """Sende Debug-Statistiken an Client"""
    stats = get_debug_system_stats()
    emit('system_stats', stats)

if __name__ == '__main__':
    print("\n🚀 Debug-Server startet (Raspberry Pi optimiert)...")
    
    # Hardware-Erkennung
    is_pi, is_low_memory = detect_hardware()
    
    print("\n🔗 Verfügbare Endpunkte:")
    print("  Test-URL: http://localhost:5001/test")
    print("  Dashboard: http://localhost:5001/")
    print("  🌐 Network Topology: http://localhost:5001/topology")
    print("  🔄 Traffic Flow: http://localhost:5001/traffic-flow")
    print("  🌍 Location Manager: http://localhost:5001/locations")
    print("  Port-Forwards: http://localhost:5001/port-forwards")
    print("  System-Stats API: http://localhost:5001/api/system-stats")
    print("  System-Health API: http://localhost:5001/api/system-health")
    
    # Adaptive Konfiguration basierend auf Hardware
    if is_pi or is_low_memory:
        print("\n🍓 Hardware-optimierte Einstellungen aktiv")
        # Reduzierte Threads für schwache Hardware
        socketio.run(app, host='localhost', port=5001, debug=True, use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        print("\n💻 Standard Debug-Einstellungen")
        socketio.run(app, host='localhost', port=5001, debug=True, allow_unsafe_werkzeug=True)