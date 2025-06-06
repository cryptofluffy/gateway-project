#!/usr/bin/env python3
"""
WireGuard Gateway VPS Server - Optimierte Version
Hauptanwendung mit Web-Interface und API für das Management
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Lokale Imports
from config import config
from utils import (
    CommandExecutor, InputValidator, NetworkUtils, FileManager,
    ValidationError, rate_limit
)

# Logging Setup
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Flask App Setup
app = Flask(__name__)
app.secret_key = config.SECRET_KEY

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

class ConfigManager:
    """Manager für WireGuard-Konfiguration"""
    
    def __init__(self):
        self.config_path = config.WIREGUARD_CONFIG_PATH
        self.interface = config.WIREGUARD_INTERFACE
        self.server_ip = config.SERVER_IP
        self.server_port = config.SERVER_PORT
        
    def get_interface_status(self) -> Dict:
        """Status des WireGuard Interface abfragen mit Caching"""
        cache_key = 'interface_status'
        cached_result = self._get_cached_result(cache_key, max_age=5)
        
        if cached_result:
            return cached_result
        
        try:
            result = CommandExecutor.run_command(['wg', 'show', self.interface])
            status_data = {
                'status': 'active' if result.returncode == 0 else 'inactive',
                'output': result.stdout if result.returncode == 0 else result.stderr,
                'timestamp': datetime.now().isoformat()
            }
            self._cache_result(cache_key, status_data)
            return status_data
            
        except Exception as e:
            logger.error(f"Error getting interface status: {e}")
            return {
                'status': 'error',
                'output': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def restart_interface(self) -> bool:
        """WireGuard Interface neu starten"""
        try:
            # Interface stoppen
            CommandExecutor.run_command(['wg-quick', 'down', self.interface])
            time.sleep(1)
            # Interface starten
            CommandExecutor.run_command(['wg-quick', 'up', self.interface])
            
            # Cache invalidieren
            self._invalidate_cache('interface_status')
            logger.info(f"WireGuard interface {self.interface} restarted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting WireGuard interface: {e}")
            return False
    
    def get_vps_info(self) -> Dict:
        """VPS-Informationen für Setup abrufen"""
        vps_info = {
            'public_key': None,
            'ip_address': None
        }
        
        try:
            # Public Key aus WireGuard-Konfiguration lesen
            if os.path.exists(config.WIREGUARD_PRIVATE_KEY_PATH):
                with open(config.WIREGUARD_PRIVATE_KEY_PATH, 'r') as f:
                    private_key = f.read().strip()
                    
                result = CommandExecutor.run_command(['wg', 'pubkey'], timeout=5)
                if result.returncode == 0:
                    # Public Key aus Private Key generieren
                    import subprocess
                    process = subprocess.Popen(
                        ['wg', 'pubkey'], 
                        stdin=subprocess.PIPE, 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE, 
                        text=True
                    )
                    stdout, _ = process.communicate(input=private_key)
                    if process.returncode == 0:
                        vps_info['public_key'] = stdout.strip()
            
            # VPS IP-Adresse ermitteln
            try:
                import requests
                response = requests.get('https://ifconfig.me', timeout=5)
                if response.status_code == 200:
                    ip = response.text.strip()
                    if InputValidator.validate_ip_address(ip):
                        vps_info['ip_address'] = ip
            except Exception:
                # Fallback für lokale Entwicklung
                vps_info['ip_address'] = '127.0.0.1'
                
        except Exception as e:
            logger.error(f"Error getting VPS info: {e}")
        
        return vps_info
    
    def update_wireguard_config(self, clients: Dict) -> bool:
        """WireGuard-Konfiguration mit aktuellen Clients aktualisieren"""
        try:
            config_content = f"""[Interface]
PrivateKey = $(cat {config.WIREGUARD_PRIVATE_KEY_PATH})
Address = {self.server_ip}/24
ListenPort = {self.server_port}
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

"""
            
            # Füge jeden Client als Peer hinzu
            client_ip = 2  # Start bei 10.8.0.2
            for public_key, client_info in clients.items():
                if client_ip > 254:  # Max IP-Range erreicht
                    logger.warning("Maximum number of clients reached")
                    break
                    
                config_content += f"""# Client: {client_info.get('name', 'Unbenannt')} ({client_info.get('location', 'Kein Standort')})
[Peer]
PublicKey = {public_key}
AllowedIPs = {config.VPN_SUBNET.split('/')[0][:-1]}{client_ip}/32, {config.GATEWAY_SUBNET}

"""
                client_ip += 1
            
            # Backup erstellen und Konfiguration schreiben
            if os.path.exists(self.config_path):
                import shutil
                shutil.copy2(self.config_path, f"{self.config_path}.backup")
            
            with open(self.config_path, 'w') as f:
                f.write(config_content)
            
            logger.info(f"WireGuard configuration updated with {len(clients)} clients")
            return True
            
        except Exception as e:
            logger.error(f"Error updating WireGuard config: {e}")
            return False
    
    # Cache für Performance-Optimierung
    _cache = {}
    
    def _get_cached_result(self, key: str, max_age: int = 60) -> Optional[Dict]:
        """Hole gecachtes Ergebnis wenn noch gültig"""
        if key in self._cache:
            timestamp, data = self._cache[key]
            if time.time() - timestamp < max_age:
                return data
        return None
    
    def _cache_result(self, key: str, data: Dict):
        """Cache Ergebnis mit Timestamp"""
        self._cache[key] = (time.time(), data)
    
    def _invalidate_cache(self, key: str):
        """Invalidiere Cache-Eintrag"""
        if key in self._cache:
            del self._cache[key]

class ClientManager:
    """Manager für Client-Verwaltung"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.clients_file = config.CLIENTS_FILE
        self.clients = self._load_clients()
    
    def _load_clients(self) -> Dict:
        """Lade gespeicherte Client-Informationen"""
        return FileManager.safe_read_json(self.clients_file, {})
    
    def _save_clients(self) -> bool:
        """Speichere Client-Informationen"""
        return FileManager.safe_write_json(self.clients_file, self.clients)
    
    def get_connected_clients(self) -> List[Dict]:
        """Liste der Clients mit erweiterten Informationen"""
        # Hole aktuelle WireGuard Peer-Informationen
        wg_peers = self._get_wireguard_peers()
        
        clients = []
        for public_key, client_info in self.clients.items():
            client_data = {
                'name': client_info.get('name', 'Unbenannt'),
                'location': client_info.get('location', 'Kein Standort'),
                'public_key': public_key,
                'status': 'disconnected',
                'last_handshake': 'Nie',
                'added': client_info.get('added', 'Unbekannt')
            }
            
            # Prüfe ob Client aktuell verbunden ist
            if public_key in wg_peers:
                client_data['status'] = 'connected'
                client_data['last_handshake'] = wg_peers[public_key].get('last_handshake', 'N/A')
            
            clients.append(client_data)
        
        return clients
    
    def _get_wireguard_peers(self) -> Dict:
        """Hole aktuelle WireGuard Peer-Informationen"""
        wg_peers = {}
        try:
            result = CommandExecutor.run_command(['wg', 'show', self.config_manager.interface])
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
            logger.error(f"Error getting WireGuard peers: {e}")
        
        return wg_peers
    
    def add_client(self, name: str, location: str, public_key: str) -> Tuple[bool, str]:
        """Neuen Client hinzufügen mit Validierung"""
        try:
            # Input-Validierung
            if not InputValidator.validate_client_name(name):
                return False, "Ungültiger Client-Name"
            
            if not InputValidator.validate_wireguard_key(public_key):
                return False, "Ungültiger WireGuard Public Key"
            
            # Prüfe ob Key bereits existiert
            if public_key in self.clients:
                return False, "Client mit diesem Public Key existiert bereits"
            
            # Prüfe maximale Anzahl Clients
            if len(self.clients) >= config.MAX_CLIENTS:
                return False, f"Maximale Anzahl Clients ({config.MAX_CLIENTS}) erreicht"
            
            # Client hinzufügen
            self.clients[public_key] = {
                'name': InputValidator.sanitize_string(name),
                'location': InputValidator.sanitize_string(location),
                'added': datetime.now().isoformat()
            }
            
            # Speichern und WireGuard-Config aktualisieren
            if self._save_clients():
                if self.config_manager.update_wireguard_config(self.clients):
                    logger.info(f"Client added successfully: {name}")
                    return True, "Client erfolgreich hinzugefügt"
                else:
                    # Rollback bei Config-Update-Fehler
                    del self.clients[public_key]
                    self._save_clients()
                    return False, "Fehler beim Aktualisieren der WireGuard-Konfiguration"
            else:
                return False, "Fehler beim Speichern der Client-Daten"
                
        except Exception as e:
            logger.error(f"Error adding client: {e}")
            return False, f"Unerwarteter Fehler: {str(e)}"
    
    def remove_client(self, public_key: str) -> Tuple[bool, str]:
        """Client entfernen"""
        try:
            if public_key not in self.clients:
                return False, "Client nicht gefunden"
            
            client_name = self.clients[public_key].get('name', 'Unbekannt')
            del self.clients[public_key]
            
            if self._save_clients():
                if self.config_manager.update_wireguard_config(self.clients):
                    logger.info(f"Client removed successfully: {client_name}")
                    return True, "Client erfolgreich entfernt"
                else:
                    return False, "Fehler beim Aktualisieren der WireGuard-Konfiguration"
            else:
                return False, "Fehler beim Speichern der Client-Daten"
                
        except Exception as e:
            logger.error(f"Error removing client: {e}")
            return False, f"Unerwarteter Fehler: {str(e)}"
    
    def edit_client(self, public_key: str, name: str, location: str) -> Tuple[bool, str]:
        """Client-Informationen bearbeiten"""
        try:
            if public_key not in self.clients:
                return False, "Client nicht gefunden"
            
            if not InputValidator.validate_client_name(name):
                return False, "Ungültiger Client-Name"
            
            # Backup für Rollback
            old_data = self.clients[public_key].copy()
            
            # Daten aktualisieren
            self.clients[public_key]['name'] = InputValidator.sanitize_string(name)
            self.clients[public_key]['location'] = InputValidator.sanitize_string(location)
            self.clients[public_key]['modified'] = datetime.now().isoformat()
            
            if self._save_clients():
                if self.config_manager.update_wireguard_config(self.clients):
                    logger.info(f"Client edited successfully: {name}")
                    return True, "Client erfolgreich bearbeitet"
                else:
                    # Rollback bei Config-Update-Fehler
                    self.clients[public_key] = old_data
                    self._save_clients()
                    return False, "Fehler beim Aktualisieren der WireGuard-Konfiguration"
            else:
                # Rollback bei Save-Fehler
                self.clients[public_key] = old_data
                return False, "Fehler beim Speichern der Client-Daten"
                
        except Exception as e:
            logger.error(f"Error editing client: {e}")
            return False, f"Unerwarteter Fehler: {str(e)}"

class PortForwardManager:
    """Manager für Port-Weiterleitungen"""
    
    def __init__(self):
        self.port_forwards_file = config.PORT_FORWARDS_FILE
        self.port_forwards = self._load_port_forwards()
    
    def _load_port_forwards(self) -> Dict:
        """Lade gespeicherte Port-Weiterleitungen"""
        return FileManager.safe_read_json(self.port_forwards_file, {})
    
    def _save_port_forwards(self) -> bool:
        """Speichere Port-Weiterleitungen"""
        return FileManager.safe_write_json(self.port_forwards_file, self.port_forwards)
    
    def add_port_forward(self, external_port: int, internal_ip: str, 
                        internal_port: int, protocol: str = 'tcp') -> Tuple[bool, str]:
        """Port-Weiterleitung hinzufügen mit Validierung"""
        try:
            # Input-Validierung
            if not InputValidator.validate_port(external_port):
                return False, "Ungültiger externer Port"
            
            if not InputValidator.validate_ip_address(internal_ip):
                return False, "Ungültige interne IP-Adresse"
            
            if not InputValidator.validate_port(internal_port):
                return False, "Ungültiger interner Port"
            
            if not InputValidator.validate_protocol(protocol):
                return False, "Ungültiges Protokoll"
            
            # Prüfe Gateway-Subnet
            if not NetworkUtils.is_ip_in_subnet(internal_ip, config.GATEWAY_SUBNET):
                return False, f"IP-Adresse muss im Gateway-Subnet ({config.GATEWAY_SUBNET}) liegen"
            
            rule_id = f"{external_port}_{protocol}"
            
            # Prüfe ob Port bereits verwendet wird
            if rule_id in self.port_forwards:
                return False, f"Port {external_port}/{protocol} bereits in Verwendung"
            
            # Prüfe maximale Anzahl
            if len(self.port_forwards) >= config.MAX_PORT_FORWARDS:
                return False, f"Maximale Anzahl Port-Weiterleitungen ({config.MAX_PORT_FORWARDS}) erreicht"
            
            # iptables Regel hinzufügen
            success = self._add_iptables_rule(external_port, internal_ip, internal_port, protocol)
            if not success:
                return False, "Fehler beim Hinzufügen der iptables-Regel"
            
            # Regel speichern
            self.port_forwards[rule_id] = {
                'external_port': external_port,
                'internal_ip': internal_ip,
                'internal_port': internal_port,
                'protocol': protocol,
                'created': datetime.now().isoformat()
            }
            
            if self._save_port_forwards():
                logger.info(f"Port forward added: {external_port}/{protocol} -> {internal_ip}:{internal_port}")
                return True, "Port-Weiterleitung erfolgreich hinzugefügt"
            else:
                # Rollback iptables bei Save-Fehler
                self._remove_iptables_rule(external_port, internal_ip, internal_port, protocol)
                return False, "Fehler beim Speichern der Port-Weiterleitung"
                
        except Exception as e:
            logger.error(f"Error adding port forward: {e}")
            return False, f"Unerwarteter Fehler: {str(e)}"
    
    def remove_port_forward(self, rule_id: str) -> Tuple[bool, str]:
        """Port-Weiterleitung entfernen"""
        try:
            if rule_id not in self.port_forwards:
                return False, "Port-Weiterleitung nicht gefunden"
            
            rule = self.port_forwards[rule_id]
            
            # iptables Regel entfernen
            success = self._remove_iptables_rule(
                rule['external_port'], 
                rule['internal_ip'], 
                rule['internal_port'], 
                rule['protocol']
            )
            
            if success:
                del self.port_forwards[rule_id]
                if self._save_port_forwards():
                    logger.info(f"Port forward removed: {rule_id}")
                    return True, "Port-Weiterleitung erfolgreich entfernt"
                else:
                    return False, "Fehler beim Speichern"
            else:
                return False, "Fehler beim Entfernen der iptables-Regel"
                
        except Exception as e:
            logger.error(f"Error removing port forward: {e}")
            return False, f"Unerwarteter Fehler: {str(e)}"
    
    def _add_iptables_rule(self, external_port: int, internal_ip: str, 
                          internal_port: int, protocol: str) -> bool:
        """Füge iptables-Regel hinzu"""
        try:
            cmd = [
                'iptables', '-t', 'nat', '-A', 'PREROUTING',
                '-p', protocol, '--dport', str(external_port),
                '-j', 'DNAT', '--to-destination', f"{internal_ip}:{internal_port}"
            ]
            
            result = CommandExecutor.run_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error adding iptables rule: {e}")
            return False
    
    def _remove_iptables_rule(self, external_port: int, internal_ip: str, 
                             internal_port: int, protocol: str) -> bool:
        """Entferne iptables-Regel"""
        try:
            cmd = [
                'iptables', '-t', 'nat', '-D', 'PREROUTING',
                '-p', protocol, '--dport', str(external_port),
                '-j', 'DNAT', '--to-destination', f"{internal_ip}:{internal_port}"
            ]
            
            result = CommandExecutor.run_command(cmd)
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Error removing iptables rule: {e}")
            return False

# Manager-Instanzen initialisieren
config_manager = ConfigManager()
client_manager = ClientManager(config_manager)
port_forward_manager = PortForwardManager()

# Flask Routes
@app.route('/')
def dashboard():
    """Haupt-Dashboard"""
    try:
        status = config_manager.get_interface_status()
        clients = client_manager.get_connected_clients()
        vps_info = config_manager.get_vps_info()
        
        return render_template('dashboard.html',
                             status=status,
                             clients=clients,
                             port_forwards=port_forward_manager.port_forwards,
                             vps_public_key=vps_info.get('public_key'),
                             vps_ip=vps_info.get('ip_address'))
    except Exception as e:
        logger.error(f"Error in dashboard route: {e}")
        return render_template('error.html', error=str(e)), 500

@app.route('/port-forwards')
def port_forwards():
    """Port-Weiterleitungen verwalten"""
    try:
        return render_template('port_forwards.html',
                             port_forwards=port_forward_manager.port_forwards)
    except Exception as e:
        logger.error(f"Error in port-forwards route: {e}")
        return render_template('error.html', error=str(e)), 500

# API Routes mit Rate Limiting
@app.route('/api/status')
@limiter.limit("30 per minute")
def api_status():
    """API: System-Status"""
    try:
        status = config_manager.get_interface_status()
        clients = client_manager.get_connected_clients()
        
        return jsonify({
            'interface': status,
            'clients': clients,
            'port_forwards': len(port_forward_manager.port_forwards),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in api_status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/clients', methods=['GET', 'POST', 'PUT', 'DELETE'])
@limiter.limit("10 per minute")
def api_clients():
    """API: Client-Management"""
    try:
        if request.method == 'GET':
            clients = client_manager.get_connected_clients()
            return jsonify(clients)
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
            
            name = data.get('name', '').strip()
            location = data.get('location', '').strip()
            public_key = data.get('public_key', '').strip()
            
            success, message = client_manager.add_client(name, location, public_key)
            status_code = 200 if success else 400
            return jsonify({'success': success, 'message': message}), status_code
        
        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
            
            public_key = data.get('public_key', '').strip()
            name = data.get('name', '').strip()
            location = data.get('location', '').strip()
            
            success, message = client_manager.edit_client(public_key, name, location)
            status_code = 200 if success else 400
            return jsonify({'success': success, 'message': message}), status_code
        
        elif request.method == 'DELETE':
            public_key = request.args.get('public_key', '').strip()
            if not public_key:
                return jsonify({'success': False, 'message': 'Public Key erforderlich'}), 400
            
            success, message = client_manager.remove_client(public_key)
            status_code = 200 if success else 400
            return jsonify({'success': success, 'message': message}), status_code
            
    except Exception as e:
        logger.error(f"Error in api_clients: {e}")
        return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500

@app.route('/api/port-forwards', methods=['GET', 'POST', 'DELETE'])
@limiter.limit("15 per minute")
def api_port_forwards():
    """API: Port-Weiterleitungen verwalten"""
    try:
        if request.method == 'GET':
            return jsonify(port_forward_manager.port_forwards)
        
        elif request.method == 'POST':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
            
            external_port = data.get('external_port')
            internal_ip = data.get('internal_ip', '').strip()
            internal_port = data.get('internal_port')
            protocol = data.get('protocol', 'tcp').lower()
            
            success, message = port_forward_manager.add_port_forward(
                external_port, internal_ip, internal_port, protocol
            )
            status_code = 200 if success else 400
            return jsonify({'success': success, 'message': message}), status_code
        
        elif request.method == 'DELETE':
            rule_id = request.args.get('rule_id', '').strip()
            if not rule_id:
                return jsonify({'success': False, 'message': 'Rule ID erforderlich'}), 400
            
            success, message = port_forward_manager.remove_port_forward(rule_id)
            status_code = 200 if success else 400
            return jsonify({'success': success, 'message': message}), status_code
            
    except Exception as e:
        logger.error(f"Error in api_port_forwards: {e}")
        return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500

@app.route('/api/restart-wireguard', methods=['POST'])
@limiter.limit("3 per minute")
def api_restart_wireguard():
    """API: WireGuard Interface neu starten"""
    try:
        success = config_manager.restart_interface()
        if success:
            return jsonify({'success': True, 'message': 'WireGuard erfolgreich neu gestartet'})
        else:
            return jsonify({'success': False, 'message': 'Fehler beim Neustart'}), 500
    except Exception as e:
        logger.error(f"Error in api_restart_wireguard: {e}")
        return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('error.html', error='Seite nicht gefunden'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return render_template('error.html', error='Interner Server-Fehler'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': 'Rate limit exceeded', 'message': str(e.description)}), 429

if __name__ == '__main__':
    logger.info("Starting WireGuard Gateway VPS Server")
    logger.info(f"Configuration: Interface={config.WIREGUARD_INTERFACE}, Server={config.SERVER_IP}:{config.SERVER_PORT}")
    
    # Stelle sicher, dass die benötigten Verzeichnisse existieren
    os.makedirs(config.DATA_DIR, exist_ok=True)
    
    # Starte die Flask-Anwendung
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)