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
        self.load_clients()
        self.load_port_forwards()
    
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
    
    def load_clients(self):
        """Lade gespeicherte Client-Informationen"""
        try:
            if os.path.exists('/etc/wireguard/clients.json'):
                with open('/etc/wireguard/clients.json', 'r') as f:
                    self.clients = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Clients: {e}")
            self.clients = {}
    
    def save_clients(self):
        """Speichere Client-Informationen"""
        try:
            os.makedirs('/etc/wireguard', exist_ok=True)
            with open('/etc/wireguard/clients.json', 'w') as f:
                json.dump(self.clients, f, indent=2)
        except Exception as e:
            print(f"Fehler beim Speichern der Clients: {e}")
    
    def load_port_forwards(self):
        """Lade gespeicherte Port-Weiterleitungen"""
        try:
            if os.path.exists('/etc/wireguard/port_forwards.json'):
                with open('/etc/wireguard/port_forwards.json', 'r') as f:
                    self.port_forwards = json.load(f)
        except Exception as e:
            print(f"Fehler beim Laden der Port-Weiterleitungen: {e}")
            self.port_forwards = {}
    
    def get_connected_clients(self):
        """Liste der verbundenen Clients mit erweiterten Informationen"""
        # Hole aktuelle WireGuard Peer-Informationen
        wg_peers = {}
        try:
            result = subprocess.run(['wg', 'show', self.interface], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                current_peer = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if line.startswith('peer:'):
                        current_peer = line.split('peer:')[1].strip()
                        wg_peers[current_peer] = {'status': 'connected'}
                    elif current_peer and 'latest handshake:' in line:
                        handshake = line.split('latest handshake:')[1].strip()
                        wg_peers[current_peer]['last_handshake'] = handshake
        except Exception as e:
            print(f"Fehler beim Abrufen der WireGuard-Peers: {e}")
        
        # Kombiniere gespeicherte Client-Daten mit aktuellen WireGuard-Daten
        clients = []
        for public_key, client_info in self.clients.items():
            client_data = {
                'name': client_info.get('name', 'Unbenannt'),
                'location': client_info.get('location', 'Kein Standort'),
                'public_key': public_key,
                'status': 'disconnected',
                'last_handshake': 'Nie'
            }
            
            # Prüfe ob Client aktuell verbunden ist
            if public_key in wg_peers:
                client_data['status'] = 'connected'
                client_data['last_handshake'] = wg_peers[public_key].get('last_handshake', 'N/A')
            
            clients.append(client_data)
        
        return clients
    
    def add_client(self, name, location, public_key):
        """Neuen Client hinzufügen"""
        try:
            # Client-Informationen speichern
            self.clients[public_key] = {
                'name': name,
                'location': location,
                'added': datetime.now().isoformat()
            }
            self.save_clients()
            
            # WireGuard-Konfiguration aktualisieren
            self.update_wireguard_config()
            return True
        except Exception as e:
            print(f"Fehler beim Hinzufügen des Clients: {e}")
            return False
    
    def remove_client(self, public_key):
        """Client entfernen"""
        try:
            if public_key in self.clients:
                del self.clients[public_key]
                self.save_clients()
                
                # WireGuard-Konfiguration aktualisieren
                self.update_wireguard_config()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Entfernen des Clients: {e}")
            return False
    
    def edit_client(self, public_key, name, location):
        """Client-Informationen bearbeiten"""
        try:
            if public_key in self.clients:
                self.clients[public_key]['name'] = name
                self.clients[public_key]['location'] = location
                self.clients[public_key]['modified'] = datetime.now().isoformat()
                self.save_clients()
                return True
            return False
        except Exception as e:
            print(f"Fehler beim Bearbeiten des Clients: {e}")
            return False
    
    def update_wireguard_config(self):
        """WireGuard-Konfiguration mit aktuellen Clients aktualisieren"""
        try:
            config_content = f"""[Interface]
PrivateKey = $(cat /etc/wireguard/private.key)
Address = {self.server_ip}/24
ListenPort = {self.server_port}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

"""
            
            # Füge jeden Client als Peer hinzu
            client_ip = 2  # Start bei 10.8.0.2
            for public_key, client_info in self.clients.items():
                config_content += f"""# Client: {client_info.get('name', 'Unbenannt')} ({client_info.get('location', 'Kein Standort')})
[Peer]
PublicKey = {public_key}
AllowedIPs = 10.8.0.{client_ip}/32, 10.0.0.0/24

"""
                client_ip += 1
            
            # Konfiguration schreiben
            with open(self.config_path, 'w') as f:
                f.write(config_content)
            
            return True
        except Exception as e:
            print(f"Fehler beim Aktualisieren der WireGuard-Konfiguration: {e}")
            return False
    
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
    
    def get_vps_info(self):
        """VPS-Informationen für Setup abrufen"""
        vps_info = {
            'public_key': None,
            'ip_address': None
        }
        
        try:
            # Public Key aus WireGuard-Konfiguration lesen
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    content = f.read()
                    # Private Key finden und Public Key ableiten
                    for line in content.split('\n'):
                        if line.strip().startswith('PrivateKey'):
                            private_key = line.split('=')[1].strip()
                            # Public Key aus Private Key generieren
                            result = subprocess.run(['wg', 'pubkey'], 
                                                  input=private_key, 
                                                  capture_output=True, 
                                                  text=True)
                            if result.returncode == 0:
                                vps_info['public_key'] = result.stdout.strip()
                            break
            
            # VPS IP-Adresse ermitteln
            try:
                import requests
                response = requests.get('https://ifconfig.me', timeout=5)
                if response.status_code == 200:
                    vps_info['ip_address'] = response.text.strip()
            except:
                # Fallback: localhost für lokale Entwicklung
                vps_info['ip_address'] = '127.0.0.1'
                
        except Exception as e:
            print(f"Fehler beim Abrufen der VPS-Informationen: {e}")
        
        return vps_info

# WireGuard Manager initialisieren
wg_manager = WireGuardManager()

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

@app.route('/api/clients', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_clients():
    """API: Client-Management"""
    if request.method == 'GET':
        clients = wg_manager.get_connected_clients()
        return jsonify(clients)
    
    elif request.method == 'POST':
        data = request.get_json()
        name = data.get('name', '')
        location = data.get('location', '')
        public_key = data.get('public_key', '')
        
        if not name or not public_key:
            return jsonify({'success': False, 'message': 'Name und Public Key sind erforderlich'}), 400
        
        if wg_manager.add_client(name, location, public_key):
            return jsonify({'success': True, 'message': 'Client erfolgreich hinzugefügt'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Hinzufügen des Clients'}), 400
    
    elif request.method == 'PUT':
        data = request.get_json()
        public_key = data.get('public_key', '')
        name = data.get('name', '')
        location = data.get('location', '')
        
        if not public_key:
            return jsonify({'success': False, 'message': 'Public Key ist erforderlich'}), 400
        
        if wg_manager.edit_client(public_key, name, location):
            return jsonify({'success': True, 'message': 'Client erfolgreich bearbeitet'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Bearbeiten des Clients'}), 400
    
    elif request.method == 'DELETE':
        public_key = request.args.get('public_key')
        if not public_key:
            return jsonify({'success': False, 'message': 'Public Key ist erforderlich'}), 400
        
        if wg_manager.remove_client(public_key):
            return jsonify({'success': True, 'message': 'Client erfolgreich entfernt'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Entfernen des Clients'}), 400

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