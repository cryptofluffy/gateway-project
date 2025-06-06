#!/usr/bin/env python3
"""
Lokale Entwicklungsversion der VPS-Software
Simuliert WireGuard-Funktionen für lokale Entwicklung
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from flask import Flask, render_template, request, jsonify

# Mock-Version des WireGuard Managers für lokale Entwicklung
class MockWireGuardManager:
    def __init__(self):
        self.interface = 'wg0'
        self.server_ip = '10.8.0.1'
        self.server_port = 51820
        self.clients = [
            {
                'public_key': 'abc123...def456',
                'status': 'connected',
                'last_handshake': '2 minutes ago'
            },
            {
                'public_key': 'xyz789...uvw012',
                'status': 'connected', 
                'last_handshake': '5 minutes ago'
            }
        ]
        self.port_forwards = {
            '8080_tcp': {
                'external_port': 8080,
                'internal_ip': '10.0.0.100',
                'internal_port': 80,
                'protocol': 'tcp',
                'created': '2024-01-15T10:30:00'
            },
            '2222_tcp': {
                'external_port': 2222,
                'internal_ip': '10.0.0.101',
                'internal_port': 22,
                'protocol': 'tcp',
                'created': '2024-01-15T11:45:00'
            },
            '25565_tcp': {
                'external_port': 25565,
                'internal_ip': '10.0.0.102',
                'internal_port': 25565,
                'protocol': 'tcp',
                'created': '2024-01-15T12:15:00'
            }
        }
    
    def get_interface_status(self):
        """Mock: WireGuard Interface Status"""
        return {
            'status': 'active',
            'output': '''interface: wg0
  public key: abcd1234567890
  private key: (hidden)
  listening port: 51820

peer: xyz9876543210
  endpoint: 192.168.1.100:51820
  allowed ips: 10.8.0.2/32, 10.0.0.0/24
  latest handshake: 2 minutes, 15 seconds ago
  transfer: 15.25 MiB received, 8.91 MiB sent

peer: def5555444333
  endpoint: 192.168.2.50:51820
  allowed ips: 10.8.0.3/32, 10.1.0.0/24
  latest handshake: 5 minutes, 33 seconds ago
  transfer: 42.18 MiB received, 23.77 MiB sent'''
        }
    
    def get_connected_clients(self):
        """Mock: Verbundene Clients"""
        return self.clients
    
    def add_port_forward(self, external_port, internal_ip, internal_port, protocol='tcp'):
        """Mock: Port-Weiterleitung hinzufügen"""
        rule_id = f"{external_port}_{protocol}"
        
        self.port_forwards[rule_id] = {
            'external_port': external_port,
            'internal_ip': internal_ip,
            'internal_port': internal_port,
            'protocol': protocol,
            'created': datetime.now().isoformat()
        }
        return True
    
    def remove_port_forward(self, rule_id):
        """Mock: Port-Weiterleitung entfernen"""
        if rule_id in self.port_forwards:
            del self.port_forwards[rule_id]
            return True
        return False
    
    def get_vps_info(self):
        """Mock: VPS-Informationen für Setup"""
        return {
            'public_key': 'abcd1234567890EXAMPLE_VPS_PUBLIC_KEY',
            'ip_address': '127.0.0.1'  # Localhost für lokale Entwicklung
        }

# Flask App Setup (mit korrektem Template-Pfad)
import os
template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=template_dir)
app.secret_key = 'local-dev-secret-key'

# Mock Manager initialisieren
wg_manager = MockWireGuardManager()

# Routes (gleich wie in der Original-App)
@app.route('/')
def dashboard():
    """Haupt-Dashboard"""
    status = wg_manager.get_interface_status()
    clients = wg_manager.get_connected_clients()
    
    # VPS-Informationen für Setup
    vps_info = wg_manager.get_vps_info()
    
    return render_template('dashboard.html', 
                         status=status, 
                         clients=clients,
                         port_forwards=wg_manager.port_forwards,
                         vps_public_key=vps_info.get('public_key'),
                         vps_ip=vps_info.get('ip_address'))

@app.route('/port-forwards')
def port_forwards():
    """Port-Weiterleitungen verwalten"""
    return render_template('port_forwards.html', 
                         port_forwards=wg_manager.port_forwards)

@app.route('/api/status')
def api_status():
    """API: System-Status"""
    status = wg_manager.get_interface_status()
    clients = wg_manager.get_connected_clients()
    
    return jsonify({
        'interface': status,
        'clients': clients,
        'port_forwards': len(wg_manager.port_forwards),
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/port-forwards', methods=['GET', 'POST', 'DELETE'])
def api_port_forwards():
    """API: Port-Weiterleitungen verwalten"""
    if request.method == 'GET':
        return jsonify(wg_manager.port_forwards)
    
    elif request.method == 'POST':
        data = request.get_json()
        external_port = data.get('external_port')
        internal_ip = data.get('internal_ip')
        internal_port = data.get('internal_port')
        protocol = data.get('protocol', 'tcp')
        
        if wg_manager.add_port_forward(external_port, internal_ip, internal_port, protocol):
            return jsonify({'success': True, 'message': 'Port-Weiterleitung hinzugefügt'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Hinzufügen'}), 400
    
    elif request.method == 'DELETE':
        rule_id = request.args.get('rule_id')
        if wg_manager.remove_port_forward(rule_id):
            return jsonify({'success': True, 'message': 'Port-Weiterleitung entfernt'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Entfernen'}), 400

@app.route('/api/restart-wireguard', methods=['POST'])
def api_restart_wireguard():
    """API: WireGuard Interface neu starten (Mock)"""
    return jsonify({'success': True, 'message': 'WireGuard neu gestartet (Mock)'})

if __name__ == '__main__':
    print("🚀 Lokale Entwicklungsumgebung")
    print("==============================")
    print("Dashboard: http://localhost:5000")
    print("API: http://localhost:5000/api/status")
    print("")
    print("💡 Alle WireGuard-Funktionen werden simuliert")
    print("📝 Änderungen werden live übernommen")
    print("")
    
    # Entwicklungsserver starten
    app.run(host='localhost', port=5000, debug=True)