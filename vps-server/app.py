#!/usr/bin/env python3
"""
WireGuard Gateway VPS Server - Optimierte Version mit Monitoring
Hauptanwendung mit Web-Interface, API und Real-Time Monitoring
"""

import logging
import os
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flask import Flask, render_template, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_socketio import SocketIO, emit

# Lokale Imports
from config import config
from monitoring import system_monitor, alert_manager, get_system_health
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
app.config.update(config.get_flask_config())

# SocketIO für Real-Time Monitoring
socketio = SocketIO(app, cors_allowed_origins="*")

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
            error_msg = str(e)
            logger.error(f"Error getting interface status: {e}")
            
            # Benutzerfreundliche Fehlermeldungen
            if "returned non-zero exit status" in error_msg and "wg show" in error_msg:
                friendly_msg = "❌ WireGuard Interface noch nicht konfiguriert. Bitte führen Sie die WireGuard-Installation durch."
            elif "No such file or directory" in error_msg:
                friendly_msg = "❌ WireGuard ist nicht installiert. Bitte installieren Sie WireGuard zuerst."
            elif "Permission denied" in error_msg:
                friendly_msg = "❌ Keine Berechtigung für WireGuard-Befehle. Service als root ausführen."
            else:
                friendly_msg = f"❌ WireGuard-Fehler: {error_msg}"
            
            return {
                'status': 'error',
                'output': friendly_msg,
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
        """VPS-Informationen für Setup abrufen - generiert Keys falls nötig"""
        vps_info = {
            'public_key': None,
            'ip_address': None
        }
        
        try:
            # Automatische Key-Generierung und Setup
            public_key = self._ensure_wireguard_keys()
            if public_key:
                vps_info['public_key'] = public_key
            
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
    
    def _ensure_wireguard_keys(self) -> Optional[str]:
        """WireGuard Keys generieren falls sie nicht existieren"""
        try:
            # Mögliche Pfade für Private Key prüfen
            key_paths = [
                config.WIREGUARD_PRIVATE_KEY_PATH,
                '/etc/wireguard/server_private.key',
                '/etc/wireguard/privatekey'
            ]
            
            private_key_path = None
            private_key = None
            
            # Existierenden Private Key finden
            for path in key_paths:
                if os.path.exists(path):
                    private_key_path = path
                    with open(path, 'r') as f:
                        private_key = f.read().strip()
                    break
            
            # Falls kein Private Key existiert, generieren
            if not private_key:
                logger.info("Generating new WireGuard private key...")
                
                # Verzeichnis erstellen
                os.makedirs('/etc/wireguard', exist_ok=True)
                
                # Private Key generieren
                result = CommandExecutor.run_command(['wg', 'genkey'])
                if result.returncode == 0:
                    private_key = result.stdout.strip()
                    private_key_path = '/etc/wireguard/server_private.key'
                    
                    # Private Key speichern
                    FileManager.write_file(private_key_path, private_key)
                    os.chmod(private_key_path, 0o600)
                    
                    logger.info(f"Private key saved to {private_key_path}")
                else:
                    logger.error("Failed to generate WireGuard private key")
                    return None
            
            # Public Key aus Private Key generieren
            if private_key:
                import subprocess
                process = subprocess.Popen(
                    ['wg', 'pubkey'], 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                stdout, stderr = process.communicate(input=private_key)
                if process.returncode == 0:
                    public_key = stdout.strip()
                    
                    # Public Key auch speichern
                    public_key_path = '/etc/wireguard/server_public.key'
                    FileManager.write_file(public_key_path, public_key)
                    
                    # WireGuard Konfiguration erstellen falls sie nicht existiert
                    self._ensure_wireguard_config(private_key)
                    
                    logger.info(f"Public key: {public_key}")
                    return public_key
                else:
                    logger.error(f"Failed to generate public key: {stderr}")
                    return None
            
        except Exception as e:
            logger.error(f"Error ensuring WireGuard keys: {e}")
            return None
    
    def _ensure_wireguard_config(self, private_key: str):
        """WireGuard Konfiguration erstellen falls sie nicht existiert oder reparieren falls fehlerhaft"""
        try:
            needs_fix = False
            
            # Prüfe ob Konfiguration existiert und korrekt ist
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    existing_content = f.read()
                    
                # Prüfe auf fehlerhafte Shell-Substitution
                if '$(cat' in existing_content or 'PrivateKey = ' not in existing_content:
                    logger.warning("WireGuard config contains shell substitution or missing private key - fixing...")
                    needs_fix = True
            else:
                logger.info("Creating WireGuard configuration...")
                needs_fix = True
            
            if needs_fix:
                config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {self.server_ip}/24
ListenPort = {config.SERVER_PORT}
SaveConfig = false

# IP-Forwarding und NAT
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Gateway-Clients werden automatisch hinzugefügt
"""
                
                FileManager.write_file(self.config_path, config_content)
                logger.info(f"WireGuard config {'fixed' if os.path.exists(self.config_path) else 'created'} at {self.config_path}")
                
                # IP-Forwarding aktivieren
                try:
                    CommandExecutor.run_command(['sysctl', '-w', 'net.ipv4.ip_forward=1'])
                    
                    # Permanent machen
                    sysctl_conf = '/etc/sysctl.conf'
                    if os.path.exists(sysctl_conf):
                        with open(sysctl_conf, 'r') as f:
                            content = f.read()
                        if 'net.ipv4.ip_forward=1' not in content:
                            with open(sysctl_conf, 'a') as f:
                                f.write('\nnet.ipv4.ip_forward=1\n')
                except Exception as e:
                    logger.warning(f"Could not enable IP forwarding: {e}")
                
        except Exception as e:
            logger.error(f"Error creating WireGuard config: {e}")
    
    def update_wireguard_config(self, clients: Dict) -> bool:
        """WireGuard-Konfiguration mit aktuellen Clients aktualisieren"""
        try:
            # Private Key laden
            private_key_paths = [
                '/etc/wireguard/server_private.key',
                '/etc/wireguard/privatekey'
            ]
            
            private_key = None
            for key_path in private_key_paths:
                try:
                    with open(key_path, 'r') as f:
                        private_key = f.read().strip()
                        break
                except FileNotFoundError:
                    continue
            
            if not private_key:
                logger.error(f"Private key not found in any of: {private_key_paths}")
                return False
            
            config_content = f"""[Interface]
PrivateKey = {private_key}
Address = {self.server_ip}/24
ListenPort = {self.server_port}
SaveConfig = false

# Forwarding und NAT aktivieren
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
        try:
            if key in self._cache:
                timestamp, data = self._cache[key]
                if time.time() - timestamp < max_age:
                    return data
                else:
                    # Abgelaufene Einträge automatisch entfernen
                    del self._cache[key]
        except (KeyError, TypeError, ValueError):
            # Korrupte Cache-Einträge entfernen
            self._cache.pop(key, None)
        return None
    
    def _cache_result(self, key: str, data: Dict):
        """Cache Ergebnis mit Timestamp und automatischer Bereinigung"""
        current_time = time.time()
        
        # Cache-Größe begrenzen (max 100 Einträge)
        if len(self._cache) >= 100:
            # Älteste 20% entfernen
            old_keys = sorted(self._cache.keys(), 
                            key=lambda k: self._cache[k][0])[:20]
            for old_key in old_keys:
                self._cache.pop(old_key, None)
        
        self._cache[key] = (current_time, data)
    
    def _invalidate_cache(self, key: str = None):
        """Invalidiere Cache-Eintrag oder gesamten Cache"""
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    def _cleanup_expired_cache(self, max_age: int = 300):
        """Entferne abgelaufene Cache-Einträge"""
        current_time = time.time()
        expired_keys = [
            key for key, (timestamp, _) in self._cache.items()
            if current_time - timestamp > max_age
        ]
        for key in expired_keys:
            del self._cache[key]

class ClientManager:
    """Manager für Client-Verwaltung mit Performance-Optimierung"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.clients_file = config.CLIENTS_FILE
        self._file_mtime = 0
        self._client_cache = {}
        self._peers_cache = None
        self._peers_cache_time = 0
        self.clients = self._load_clients()
    
    def _load_clients(self) -> Dict:
        """Lade gespeicherte Client-Informationen mit Caching"""
        try:
            current_mtime = os.path.getmtime(self.clients_file) if os.path.exists(self.clients_file) else 0
            
            # Nur neu laden wenn Datei geändert wurde
            if current_mtime > self._file_mtime:
                self._file_mtime = current_mtime
                clients = FileManager.safe_read_json(self.clients_file, {})
                self._client_cache.clear()  # Cache invalidieren
                return clients
            
            # Wenn bereits geladen, return cached version
            return getattr(self, 'clients', {})
        except (OSError, IOError) as e:
            logger.warning(f"Could not check file modification time: {e}")
            return FileManager.safe_read_json(self.clients_file, {})
    
    def _save_clients(self) -> bool:
        """Speichere Client-Informationen mit optimierter I/O"""
        try:
            success = FileManager.safe_write_json(self.clients_file, self.clients)
            if success:
                self._file_mtime = os.path.getmtime(self.clients_file)
                self._client_cache.clear()  # Cache invalidieren
            return success
        except (OSError, IOError) as e:
            logger.error(f"Error updating file modification time: {e}")
            return False
    
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
    
    def _get_wireguard_peers(self, use_cache: bool = True) -> Dict:
        """Hole aktuelle WireGuard Peer-Informationen mit Caching"""
        current_time = time.time()
        
        # Cache für 30 Sekunden verwenden
        if use_cache and self._peers_cache and (current_time - self._peers_cache_time) < 30:
            return self._peers_cache
        
        wg_peers = {}
        try:
            result = CommandExecutor.run_command(['wg', 'show', self.config_manager.interface], timeout=5)
            if result.returncode == 0:
                # Optimized parsing mit regulären Ausdrücken
                import re
                peer_pattern = re.compile(r'peer:\s*(\S+)')
                handshake_pattern = re.compile(r'latest handshake:\s*(.+)')
                
                lines = result.stdout.split('\n')
                current_peer = None
                
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    
                    peer_match = peer_pattern.match(line)
                    if peer_match:
                        current_peer = peer_match.group(1)
                        wg_peers[current_peer] = {'status': 'connected'}
                        continue
                    
                    if current_peer:
                        handshake_match = handshake_pattern.search(line)
                        if handshake_match:
                            wg_peers[current_peer]['last_handshake'] = handshake_match.group(1)
                            
        except Exception as e:
            logger.error(f"Error getting WireGuard peers: {e}")
            # Fallback zu gecachten Daten
            if self._peers_cache:
                return self._peers_cache
        
        # Cache aktualisieren
        self._peers_cache = wg_peers
        self._peers_cache_time = current_time
        
        return wg_peers
    
    def add_client(self, name: str, location: str, public_key: str, network_config: Dict = None) -> Tuple[bool, str]:
        """Neuen Client hinzufügen mit Validierung und Netzwerkschnittstellen-Konfiguration"""
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
            client_data = {
                'name': InputValidator.sanitize_string(name),
                'location': InputValidator.sanitize_string(location),
                'added': datetime.now().isoformat()
            }
            
            # Netzwerkschnittstellen-Konfiguration hinzufügen
            if network_config:
                client_data['network_config'] = {
                    'wan_interface': network_config.get('wan_interface', 'auto'),
                    'lan_interface': network_config.get('lan_interface', 'auto'),
                    'auto_detect': network_config.get('auto_detect', True)
                }
            
            self.clients[public_key] = client_data
            
            # Speichern und WireGuard-Config aktualisieren
            if self._save_clients():
                if self.config_manager.update_wireguard_config(self.clients):
                    # WireGuard Interface neu laden um neue Config zu aktivieren
                    try:
                        CommandExecutor.run_command(['wg-quick', 'down', self.config_manager.interface])
                        time.sleep(1)
                        CommandExecutor.run_command(['wg-quick', 'up', self.config_manager.interface])
                        logger.info(f"Client added and WireGuard reloaded: {name}")
                    except Exception as e:
                        logger.warning(f"Could not reload WireGuard interface: {e}")
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
    
    def edit_client(self, public_key: str, name: str, location: str, network_config: Dict = None) -> Tuple[bool, str]:
        """Client-Informationen bearbeiten mit Netzwerkschnittstellen-Konfiguration"""
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
            
            # Netzwerkschnittstellen-Konfiguration aktualisieren
            if network_config:
                self.clients[public_key]['network_config'] = {
                    'wan_interface': network_config.get('wan_interface', 'auto'),
                    'lan_interface': network_config.get('lan_interface', 'auto'),
                    'auto_detect': network_config.get('auto_detect', True)
                }
            
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
@app.route('/dashboard')
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
@limiter.limit("20 per minute")
def api_clients():
    """API: Client-Management"""
    try:
        if request.method == 'GET':
            clients = client_manager.get_connected_clients()
            return jsonify(clients)
        
        elif request.method == 'POST':
            try:
                data = request.get_json()
                logger.info(f"Received POST request with data: {data}")
                
                if not data:
                    logger.warning("No JSON data received in POST request")
                    return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
                
                name = data.get('name', '').strip()
                location = data.get('location', '').strip()
                public_key = data.get('public_key', '').strip()
                network_config = data.get('network_config', {})
                
                logger.info(f"Processing client addition: name='{name}', location='{location}', public_key_length={len(public_key)}")
                
                # Zusätzliche Validierung
                if not name:
                    return jsonify({'success': False, 'message': 'Gateway-Name ist erforderlich'}), 400
                
                if not public_key:
                    return jsonify({'success': False, 'message': 'WireGuard Public Key ist erforderlich'}), 400
                
                success, message = client_manager.add_client(name, location, public_key, network_config)
                status_code = 200 if success else 400
                
                logger.info(f"Client addition result: success={success}, message='{message}'")
                return jsonify({'success': success, 'message': message}), status_code
                
            except Exception as e:
                logger.error(f"Exception in POST /api/clients: {e}", exc_info=True)
                return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500
        
        elif request.method == 'PUT':
            data = request.get_json()
            if not data:
                return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
            
            public_key = data.get('public_key', '').strip()
            name = data.get('name', '').strip()
            location = data.get('location', '').strip()
            network_config = data.get('network_config', {})
            
            success, message = client_manager.edit_client(public_key, name, location, network_config)
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

@app.route('/api/network-interfaces', methods=['GET'])
@limiter.limit("5 per minute")
def api_network_interfaces():
    """API: Verfügbare Netzwerkschnittstellen abrufen"""
    try:
        interfaces = NetworkUtils.get_available_interfaces()
        return jsonify({
            'success': True,
            'interfaces': interfaces
        })
    except Exception as e:
        logger.error(f"Error getting network interfaces: {e}")
        return jsonify({
            'success': False, 
            'message': f'Fehler beim Abrufen der Netzwerkschnittstellen: {str(e)}'
        }), 500

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

@app.route('/api/fix-wireguard-config', methods=['POST'])
@limiter.limit("3 per minute")
def api_fix_wireguard_config():
    """API: WireGuard-Konfiguration automatisch reparieren"""
    try:
        # Keys sicherstellen und Konfiguration reparieren
        public_key = config_manager._ensure_wireguard_keys()
        if public_key:
            # Aktuelle Clients laden und Konfiguration komplett neu schreiben
            config_manager.update_wireguard_config(client_manager.clients)
            
            # WireGuard Interface neu starten
            success = config_manager.restart_interface()
            
            if success:
                return jsonify({
                    'success': True, 
                    'message': 'WireGuard-Konfiguration erfolgreich repariert',
                    'public_key': public_key
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': 'Konfiguration repariert, aber Interface-Neustart fehlgeschlagen'
                }), 500
        else:
            return jsonify({
                'success': False, 
                'message': 'Fehler beim Generieren der WireGuard-Keys'
            }), 500
            
    except Exception as e:
        logger.error(f"Error in api_fix_wireguard_config: {e}")
        return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500

@app.route('/api/vps-info', methods=['GET'])
@limiter.limit("10 per minute")
def api_vps_info():
    """API: VPS-Informationen für Gateway-Setup"""
    try:
        vps_info = config_manager.get_vps_info()
        return jsonify({
            'success': True,
            'public_key': vps_info.get('public_key'),
            'ip_address': vps_info.get('ip_address'),
            'server_port': config.SERVER_PORT,
            'endpoint': f"{vps_info.get('ip_address')}:{config.SERVER_PORT}" if vps_info.get('ip_address') else None
        })
    except Exception as e:
        logger.error(f"Error in api_vps_info: {e}")
        return jsonify({'success': False, 'message': f'Server-Fehler: {str(e)}'}), 500

@app.route('/api/system-stats', methods=['GET'])
@limiter.limit("30 per minute")
def api_system_stats():
    """API: VPS System-Statistiken"""
    try:
        stats = system_monitor.get_current_stats()
        alerts = alert_manager.check_alerts(stats)
        performance = system_monitor.get_performance_summary()
        
        return jsonify({
            'success': True,
            'system_stats': stats,
            'alerts': alerts,
            'performance_summary': performance,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in api_system_stats: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/system-health', methods=['GET'])
@limiter.limit("20 per minute")
def api_system_health():
    """API: VPS System-Gesundheitscheck"""
    try:
        health = get_system_health()
        return jsonify(health)
    except Exception as e:
        logger.error(f"Error in api_system_health: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/gateway-metrics', methods=['POST'])
@limiter.limit("60 per minute")
def api_gateway_metrics():
    """API: Gateway-PC Metriken empfangen"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'Keine Daten erhalten'}), 400
        
        # Gateway-Metriken speichern/verarbeiten
        gateway_id = data.get('gateway_id', 'unknown')
        
        # Hier könnten die Gateway-Metriken in einer Datenbank gespeichert werden
        # Für jetzt loggen wir sie nur
        logger.info(f"Gateway-Metriken erhalten von {gateway_id}: CPU={data.get('cpu_percent', 'N/A')}%, Memory={data.get('memory_percent', 'N/A')}%")
        
        # An WebSocket-Clients weiterleiten
        socketio.emit('gateway_metrics', {
            'gateway_id': gateway_id,
            'metrics': data,
            'timestamp': datetime.now().isoformat()
        })
        
        return jsonify({'success': True, 'message': 'Metriken empfangen'})
        
    except Exception as e:
        logger.error(f"Error in api_gateway_metrics: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/alerts', methods=['GET'])
@limiter.limit("20 per minute") 
def api_alerts():
    """API: Aktuelle System-Alerts"""
    try:
        hours = int(request.args.get('hours', 24))
        alerts = alert_manager.get_recent_alerts(hours)
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts),
            'hours': hours
        })
    except Exception as e:
        logger.error(f"Error in api_alerts: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


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

# WebSocket Events für Real-Time Monitoring
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    emit('status', {'msg': 'Connected to real-time monitoring'})
    logger.info(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('subscribe_monitoring')
def handle_subscribe_monitoring():
    """Client subscription to monitoring data"""
    emit('monitoring_subscribed', {'msg': 'Subscribed to monitoring updates'})
    # Sofort aktuelle Daten senden
    try:
        stats = system_monitor.get_current_stats()
        alerts = alert_manager.check_alerts(stats)
        health = get_system_health()
        
        emit('system_update', {
            'system_stats': stats,
            'alerts': alerts,
            'health': health,
            'clients': client_manager.get_connected_clients(),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error sending initial monitoring data: {e}")

# Real-Time Monitoring Thread
class RealtimeMonitor:
    def __init__(self):
        self.running = False
        self.thread = None
        self.update_interval = config.monitoring.MONITORING_INTERVAL
    
    def start(self):
        """Start real-time monitoring thread"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop)
            self.thread.daemon = True
            self.thread.start()
            logger.info("Real-time monitoring started")
    
    def stop(self):
        """Stop real-time monitoring thread"""
        self.running = False
        if self.thread:
            self.thread.join()
        logger.info("Real-time monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                # Sammle System-Statistiken
                stats = system_monitor.get_current_stats()
                alerts = alert_manager.check_alerts(stats)
                health = get_system_health()
                clients = client_manager.get_connected_clients()
                
                # Sende Updates an alle verbundenen Clients
                socketio.emit('system_update', {
                    'system_stats': stats,
                    'alerts': alerts,
                    'health': health,
                    'connected_clients': len([c for c in clients if c['status'] == 'connected']),
                    'total_clients': len(clients),
                    'timestamp': datetime.now().isoformat()
                })
                
                # Bei kritischen Alerts sofort senden
                critical_alerts = [a for a in alerts if a.get('severity') == 'critical']
                if critical_alerts:
                    socketio.emit('critical_alert', {
                        'alerts': critical_alerts,
                        'timestamp': datetime.now().isoformat()
                    })
                
                time.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(30)  # Längere Pause bei Fehlern

# Globale Monitor-Instanz
realtime_monitor = RealtimeMonitor()

if __name__ == '__main__':
    logger.info("Starting WireGuard Gateway VPS Server with Real-Time Monitoring")
    logger.info(f"Configuration: Interface={config.WIREGUARD_INTERFACE}, Server={config.SERVER_IP}:{config.SERVER_PORT}")
    
    # Stelle sicher, dass die benötigten Verzeichnisse existieren
    os.makedirs(config.DATA_DIR, exist_ok=True)
    
    # Starte Real-Time Monitoring
    if config.monitoring.MONITORING_ENABLED:
        realtime_monitor.start()
    
    # Starte die Flask-SocketIO-Anwendung
    try:
        socketio.run(app, host=config.HOST, port=config.PORT, debug=config.DEBUG, allow_unsafe_werkzeug=True)
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        realtime_monitor.stop()
    except Exception as e:
        logger.error(f"Server error: {e}")
        realtime_monitor.stop()
        raise