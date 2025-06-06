#!/usr/bin/env python3
"""
WireGuard Gateway VPS Server
Hauptanwendung mit Web-Interface und API für das Management
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import subprocess
import json
import os
import ipaddress
from datetime import datetime
import configparser

app = Flask(__name__)
app.secret_key = 'wireguard-gateway-secret-key'

class WireGuardManager:
    def __init__(self):
        self.config_path = '/etc/wireguard/wg0.conf'
        self.interface = 'wg0'
        self.server_ip = '10.8.0.1'
        self.server_port = 51820
        self.clients = {}
        self.port_forwards = {}
        self.load_config()
    
    def load_config(self):
        """Lade WireGuard Konfiguration"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    content = f.read()
                    # Parse existing config
                    pass
        except Exception as e:
            print(f"Fehler beim Laden der Konfiguration: {e}")
    
    def get_interface_status(self):
        """Status des WireGuard Interface abfragen"""
        try:
            result = subprocess.run(['wg', 'show', self.interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return {'status': 'active', 'output': result.stdout}
            else:
                return {'status': 'inactive', 'output': result.stderr}
        except Exception as e:
            return {'status': 'error', 'output': str(e)}
    
    def get_connected_clients(self):
        """Liste der verbundenen Clients"""
        try:
            result = subprocess.run(['wg', 'show', self.interface, 'peers'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                peers = result.stdout.strip().split('\n') if result.stdout.strip() else []
                clients = []
                for peer in peers:
                    if peer:
                        clients.append({
                            'public_key': peer[:20] + '...',
                            'status': 'connected',
                            'last_handshake': 'N/A'
                        })
                return clients
            return []
        except Exception as e:
            return []
    
    def add_port_forward(self, external_port, internal_ip, internal_port, protocol='tcp'):
        """Port-Weiterleitung hinzufügen"""
        rule_id = f"{external_port}_{protocol}"
        
        # iptables Regel hinzufügen
        iptables_cmd = [
            'iptables', '-t', 'nat', '-A', 'PREROUTING',
            '-p', protocol, '--dport', str(external_port),
            '-j', 'DNAT', '--to-destination', f"{internal_ip}:{internal_port}"
        ]
        
        try:
            result = subprocess.run(iptables_cmd, capture_output=True, text=True)
            if result.returncode == 0:
                self.port_forwards[rule_id] = {
                    'external_port': external_port,
                    'internal_ip': internal_ip,
                    'internal_port': internal_port,
                    'protocol': protocol,
                    'created': datetime.now().isoformat()
                }
                self.save_port_forwards()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Hinzufügen der Port-Weiterleitung: {e}")
            return False
    
    def remove_port_forward(self, rule_id):
        """Port-Weiterleitung entfernen"""
        if rule_id in self.port_forwards:
            rule = self.port_forwards[rule_id]
            
            # iptables Regel entfernen
            iptables_cmd = [
                'iptables', '-t', 'nat', '-D', 'PREROUTING',
                '-p', rule['protocol'], '--dport', str(rule['external_port']),
                '-j', 'DNAT', '--to-destination', f"{rule['internal_ip']}:{rule['internal_port']}"
            ]
            
            try:
                result = subprocess.run(iptables_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    del self.port_forwards[rule_id]
                    self.save_port_forwards()
                    return True
                return False
            except Exception as e:
                print(f"Fehler beim Entfernen der Port-Weiterleitung: {e}")
                return False
        return False
    
    def save_port_forwards(self):
        """Port-Weiterleitungen speichern"""
        try:
            with open('/etc/wireguard/port_forwards.json', 'w') as f:
                json.dump(self.port_forwards, f, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Port-Weiterleitungen: {e}")

# WireGuard Manager initialisieren
wg_manager = WireGuardManager()

@app.route('/')
def dashboard():
    """Haupt-Dashboard"""
    status = wg_manager.get_interface_status()
    clients = wg_manager.get_connected_clients()
    
    return render_template('dashboard.html', 
                         status=status, 
                         clients=clients,
                         port_forwards=wg_manager.port_forwards)

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
    """API: WireGuard Interface neu starten"""
    try:
        # Interface stoppen
        subprocess.run(['wg-quick', 'down', wg_manager.interface], check=True)
        # Interface starten
        subprocess.run(['wg-quick', 'up', wg_manager.interface], check=True)
        return jsonify({'success': True, 'message': 'WireGuard neu gestartet'})
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'message': f'Fehler: {e}'}), 500

if __name__ == '__main__':
    # Stelle sicher, dass die benötigten Verzeichnisse existieren
    os.makedirs('/etc/wireguard', exist_ok=True)
    
    # Starte die Flask-Anwendung
    app.run(host='0.0.0.0', port=8080, debug=True)