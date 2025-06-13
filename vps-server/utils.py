#!/usr/bin/env python3
"""
Utility-Funktionen für WireGuard Gateway VPS
Gemeinsame Hilfsfunktionen und Validierung
"""

import re
import os
import ipaddress
import subprocess
import logging
import time
import json
import shutil
from typing import Dict, List, Optional, Tuple, Union
from functools import wraps

# Logging Setup
logger = logging.getLogger(__name__)

class ValidationError(Exception):
    """Custom Exception für Validierungsfehler"""
    pass

class CommandExecutor:
    """Klasse für sichere Ausführung von System-Kommandos"""
    
    @staticmethod
    def run_command(cmd: List[str], timeout: int = 10, retries: int = 1) -> subprocess.CompletedProcess:
        """
        Führt System-Kommando sicher aus mit Retry-Mechanismus
        
        Args:
            cmd: Kommando als Liste
            timeout: Timeout in Sekunden
            retries: Anzahl Wiederholungen bei Fehlern
            
        Returns:
            CompletedProcess Objekt
            
        Raises:
            subprocess.CalledProcessError: Bei Kommando-Fehlern
            subprocess.TimeoutExpired: Bei Timeout
        """
        last_exception = None
        
        for attempt in range(retries):
            try:
                logger.debug(f"Executing command (attempt {attempt + 1}/{retries}): {' '.join(cmd)}")
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout,
                    check=False
                )
                
                if result.returncode == 0:
                    logger.debug(f"Command successful: {' '.join(cmd)}")
                    return result
                else:
                    logger.warning(f"Command failed with code {result.returncode}: {result.stderr}")
                    if attempt == retries - 1:  # Letzter Versuch
                        raise subprocess.CalledProcessError(result.returncode, cmd, result.stdout, result.stderr)
                        
            except subprocess.TimeoutExpired as e:
                logger.error(f"Command timeout (attempt {attempt + 1}/{retries}): {' '.join(cmd)}")
                last_exception = e
                if attempt == retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Command execution error: {e}")
                last_exception = e
                if attempt == retries - 1:
                    raise
            
            # Warte zwischen Versuchen
            if attempt < retries - 1:
                time.sleep(1)
        
        # Sollte normalerweise nicht erreicht werden
        if last_exception:
            raise last_exception

class InputValidator:
    """Klasse für Input-Validierung"""
    
    # Regex Patterns
    WIREGUARD_PUBLIC_KEY_PATTERN = re.compile(r'^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=?$')
    HOSTNAME_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?$')
    
    @staticmethod
    def validate_ip_address(ip_str: str) -> bool:
        """Validiert IP-Adresse (IPv4 oder IPv6)"""
        try:
            ipaddress.ip_address(ip_str)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_port(port: Union[int, str]) -> bool:
        """Validiert Port-Nummer (1-65535)"""
        try:
            port_int = int(port)
            return 1 <= port_int <= 65535
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_wireguard_key(key: str) -> bool:
        """Validiert WireGuard Public/Private Key Format"""
        if not isinstance(key, str):
            return False
        return bool(InputValidator.WIREGUARD_PUBLIC_KEY_PATTERN.match(key))
    
    @staticmethod
    def validate_client_name(name: str) -> bool:
        """Validiert Client-Namen"""
        if not isinstance(name, str):
            return False
        return 1 <= len(name.strip()) <= 50 and name.strip().isprintable()
    
    @staticmethod
    def validate_protocol(protocol: str) -> bool:
        """Validiert Protokoll (tcp, udp, both)"""
        return protocol.lower() in ['tcp', 'udp', 'both']
    
    @staticmethod
    def sanitize_string(input_str: str, max_length: int = 100) -> str:
        """Bereinigt String-Input"""
        if not isinstance(input_str, str):
            return ""
        
        # Entferne gefährliche Zeichen
        sanitized = re.sub(r'[<>&"\'`$]', '', input_str)
        # Beschränke Länge
        sanitized = sanitized[:max_length]
        # Entferne führende/trailing Whitespace
        return sanitized.strip()

def validate_input(validation_func):
    """Decorator für Input-Validierung"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Hier könnte spezifische Validierung basierend auf Funktionsname implementiert werden
            return func(*args, **kwargs)
        return wrapper
    return decorator

class NetworkUtils:
    """Netzwerk-bezogene Utility-Funktionen"""
    
    @staticmethod
    def resolve_hostname(ip: str, timeout: int = 2) -> Optional[str]:
        """
        Versucht den Hostnamen für eine IP-Adresse zu ermitteln
        
        Args:
            ip: IP-Adresse
            timeout: Timeout in Sekunden
            
        Returns:
            Hostname oder None falls nicht auflösbar
        """
        try:
            import socket
            socket.setdefaulttimeout(timeout)
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname if hostname != ip else None
        except (socket.herror, socket.gaierror, socket.timeout, OSError):
            return None
    
    @staticmethod
    def get_connected_devices_with_hostnames(subnet: str = "10.0.0.0/24") -> List[Dict[str, str]]:
        """
        Ermittelt alle erreichbaren Geräte im Subnet mit Hostnamen
        
        Args:
            subnet: Subnet zum Scannen
            
        Returns:
            Liste von Geräten mit IP und Hostname
        """
        devices = []
        
        try:
            # ARP-Tabelle lesen für schnelle Geräte-Erkennung
            arp_devices = NetworkUtils._get_arp_table()
            
            # WireGuard verbundene Clients
            wg_clients = NetworkUtils._get_wireguard_clients()
            
            # Kombiniere ARP und WireGuard Daten
            all_ips = set()
            all_ips.update(device['ip'] for device in arp_devices)
            all_ips.update(client['ip'] for client in wg_clients if client.get('ip'))
            
            for ip in all_ips:
                if ip.startswith('10.0.0.') or ip.startswith('10.8.0.'):
                    hostname = NetworkUtils.resolve_hostname(ip, timeout=1)
                    
                    # Suche zusätzliche Infos aus WireGuard
                    wg_info = next((c for c in wg_clients if c.get('ip') == ip), None)
                    name = wg_info.get('name') if wg_info else None
                    
                    devices.append({
                        'ip': ip,
                        'hostname': hostname,
                        'name': name,
                        'status': 'connected' if wg_info else 'reachable'
                    })
            
            # Sortiere nach IP
            devices.sort(key=lambda x: ipaddress.ip_address(x['ip']))
            
        except Exception as e:
            logger.error(f"Error scanning for devices: {e}")
        
        return devices
    
    @staticmethod
    def _get_arp_table() -> List[Dict[str, str]]:
        """Liest die ARP-Tabelle für verbundene Geräte"""
        devices = []
        try:
            result = subprocess.run(['ip', 'neigh'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'REACHABLE' in line or 'STALE' in line:
                        parts = line.split()
                        if len(parts) >= 1:
                            ip = parts[0]
                            if ip.replace('.', '').isdigit():  # Einfache IP-Validierung
                                devices.append({'ip': ip})
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            logger.debug(f"Error reading ARP table: {e}")
        
        return devices
    
    @staticmethod
    def _get_wireguard_clients() -> List[Dict[str, str]]:
        """Ermittelt WireGuard Clients mit IPs"""
        clients = []
        try:
            result = subprocess.run(['wg', 'show', 'wg0', 'allowed-ips'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip() and '/' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            ip = parts[1].split('/')[0]  # Entferne /32 Suffix
                            clients.append({'ip': ip, 'name': 'Gateway'})
        except Exception as e:
            logger.debug(f"Error reading WireGuard clients: {e}")
        
        return clients

    @staticmethod
    def get_next_available_ip(subnet: str, used_ips: List[str]) -> Optional[str]:
        """
        Findet die nächste verfügbare IP in einem Subnet
        
        Args:
            subnet: Subnet im CIDR-Format (z.B. "10.8.0.0/24")
            used_ips: Liste der bereits verwendeten IPs
            
        Returns:
            Nächste verfügbare IP oder None
        """
        try:
            network = ipaddress.ip_network(subnet, strict=False)
            used_addresses = {ipaddress.ip_address(ip) for ip in used_ips}
            
            # Überspringe Netzwerk- und Broadcast-Adresse
            for ip in network.hosts():
                if ip not in used_addresses:
                    return str(ip)
            
            return None
        except (ValueError, ipaddress.AddressValueError) as e:
            logger.error(f"Error in get_next_available_ip: {e}")
            return None
    
    # Cache für Interface-Informationen
    _interface_cache = {}
    _interface_cache_time = 0
    
    @staticmethod
    def get_current_interfaces() -> Dict[str, Optional[str]]:
        """
        Ermittelt die aktuell verwendeten WAN- und LAN-Interfaces
        
        Returns:
            Dictionary mit wan und lan Interface-Namen
        """
        current = {'wan': None, 'lan': None}
        
        try:
            # Versuche WAN-Interface über Default-Route zu ermitteln
            result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'default via' in line and 'dev' in line:
                        parts = line.split()
                        if 'dev' in parts:
                            dev_index = parts.index('dev')
                            if dev_index + 1 < len(parts):
                                current['wan'] = parts[dev_index + 1]
                                break
            
            # LAN-Interface über WireGuard-Konfiguration ermitteln
            if os.path.exists('/etc/wireguard/wg0.conf'):
                with open('/etc/wireguard/wg0.conf', 'r') as f:
                    content = f.read()
                    # Suche nach PostUp/PostDown Regeln mit Interface-Namen
                    for line in content.split('\n'):
                        if 'MASQUERADE' in line and '-o' in line:
                            parts = line.split()
                            if '-o' in parts:
                                o_index = parts.index('-o')
                                if o_index + 1 < len(parts):
                                    current['lan'] = parts[o_index + 1]
                                    break
            
            # Fallback: Versuche über aktive Interfaces zu raten
            if not current['lan']:
                # Suche nach Interface mit 10.0.0.x oder 10.8.0.x IP
                active_interfaces = NetworkUtils._get_interface_with_ip_range(['10.0.0.', '10.8.0.'])
                if active_interfaces:
                    current['lan'] = active_interfaces[0]
                    
        except Exception as e:
            logger.debug(f"Error detecting current interfaces: {e}")
        
        return current
    
    @staticmethod
    def _get_interface_with_ip_range(ip_prefixes: List[str]) -> List[str]:
        """Findet Interfaces mit IPs in bestimmten Bereichen"""
        matching_interfaces = []
        try:
            result = subprocess.run(['ip', 'addr', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                current_interface = None
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    # Interface-Name erkennen
                    if line and not line.startswith(' ') and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            current_interface = parts[1].strip().split('@')[0]
                    # IP-Adressen prüfen
                    elif 'inet ' in line and current_interface:
                        for prefix in ip_prefixes:
                            if f'inet {prefix}' in line:
                                if current_interface not in matching_interfaces:
                                    matching_interfaces.append(current_interface)
                                break
        except Exception as e:
            logger.debug(f"Error finding interfaces with IP range: {e}")
        
        return matching_interfaces

    @staticmethod
    def get_available_interfaces(use_cache: bool = True) -> Dict:
        """
        Ermittelt verfügbare Netzwerkschnittstellen des Systems mit Caching
        
        Args:
            use_cache: Ob Cache verwendet werden soll (Standard: True)
            
        Returns:
            Dictionary mit Interface-Informationen
        """
        current_time = time.time()
        
        # Cache für 60 Sekunden verwenden
        if (use_cache and NetworkUtils._interface_cache and 
            (current_time - NetworkUtils._interface_cache_time) < 60):
            return NetworkUtils._interface_cache
        
        interfaces = {
            'ethernet': [],
            'wireless': [],
            'virtual': [],
            'other': []
        }
        
        try:
            # Linux: /sys/class/net verwenden (effizientester Weg)
            if os.path.exists('/sys/class/net'):
                # Parallele Verarbeitung für bessere Performance
                interface_names = [name for name in os.listdir('/sys/class/net') 
                                 if name != 'lo']
                
                for interface in interface_names:
                    try:
                        interface_info = {
                            'name': interface,
                            'type': NetworkUtils._get_interface_type(interface),
                            'status': NetworkUtils._get_interface_status(interface),
                            'ip': NetworkUtils._get_interface_ip(interface)
                        }
                        
                        # Kategorisierung mit besserer Performance
                        interface_first_chars = interface[:4].lower()
                        if interface_first_chars.startswith(('eth', 'enp', 'ens')):
                            interfaces['ethernet'].append(interface_info)
                        elif interface_first_chars.startswith(('wlan', 'wlp', 'wifi')):
                            interfaces['wireless'].append(interface_info)
                        elif interface_first_chars.startswith(('veth', 'dock', 'br-', 'virb')):
                            interfaces['virtual'].append(interface_info)
                        else:
                            interfaces['other'].append(interface_info)
                            
                    except (OSError, IOError, subprocess.TimeoutExpired) as e:
                        logger.debug(f"Error processing interface {interface}: {e}")
                        # Interface überspringen bei Fehlern
            
            # Fallback: ip command verwenden
            else:
                result = subprocess.run(['ip', 'link', 'show'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if ': ' in line and '@' not in line:
                            parts = line.split(': ')
                            if len(parts) >= 2:
                                interface_name = parts[1].split('@')[0]
                                if interface_name != 'lo':
                                    interface_info = {
                                        'name': interface_name,
                                        'type': 'unknown',
                                        'status': 'unknown',
                                        'ip': None
                                    }
                                    interfaces['other'].append(interface_info)
        
        except Exception as e:
            logger.error(f"Error getting network interfaces: {e}")
            # Fallback zu Standard-Interfaces
            interfaces = {
                'ethernet': [
                    {'name': 'eth0', 'type': 'ethernet', 'status': 'unknown', 'ip': None},
                    {'name': 'eth1', 'type': 'ethernet', 'status': 'unknown', 'ip': None}
                ],
                'wireless': [
                    {'name': 'wlan0', 'type': 'wireless', 'status': 'unknown', 'ip': None}
                ],
                'virtual': [],
                'other': []
            }
        
        # Cache aktualisieren
        NetworkUtils._interface_cache = interfaces
        NetworkUtils._interface_cache_time = current_time
        
        return interfaces
    
    @staticmethod
    def _get_interface_type(interface: str) -> str:
        """Ermittelt den Typ einer Netzwerkschnittstelle"""
        try:
            wireless_path = f'/sys/class/net/{interface}/wireless'
            if os.path.exists(wireless_path):
                return 'wireless'
            
            # Prüfe auf virtuelle Interfaces
            if interface.startswith(('veth', 'docker', 'br-')):
                return 'virtual'
            
            # Standard: Ethernet
            return 'ethernet'
        except:
            return 'unknown'
    
    @staticmethod
    def _get_interface_status(interface: str) -> str:
        """Ermittelt den Status einer Netzwerkschnittstelle"""
        try:
            with open(f'/sys/class/net/{interface}/operstate', 'r') as f:
                return f.read().strip()
        except:
            return 'unknown'
    
    @staticmethod
    def _get_interface_ip(interface: str) -> Optional[str]:
        """Ermittelt die IP-Adresse einer Netzwerkschnittstelle"""
        try:
            result = subprocess.run(['ip', 'addr', 'show', interface], 
                                  capture_output=True, text=True, timeout=3)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and not '127.0.0.1' in line:
                        ip_part = line.strip().split()[1]
                        return ip_part.split('/')[0]
            return None
        except:
            return None
    
    @staticmethod
    def is_ip_in_subnet(ip: str, subnet: str) -> bool:
        """Prüft ob IP-Adresse in Subnet liegt"""
        try:
            ip_addr = ipaddress.ip_address(ip)
            network = ipaddress.ip_network(subnet, strict=False)
            return ip_addr in network
        except (ValueError, ipaddress.AddressValueError):
            return False

class FileManager:
    """Sichere Datei-Operationen mit Performance-Optimierung"""
    
    # Cache für JSON-Daten
    _json_cache = {}
    _file_mtimes = {}
    
    @staticmethod
    def safe_write_json(filepath: str, data: Dict, backup: bool = True) -> bool:
        """
        Schreibt JSON-Daten sicher in Datei mit optimalem I/O
        
        Args:
            filepath: Pfad zur Datei
            data: Zu schreibende Daten
            backup: Ob Backup erstellt werden soll
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        import json
        import shutil
        
        try:
            # Verzeichnis erstellen falls nötig
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # JSON serialisieren mit kompakter Ausgabe für bessere Performance
            json_str = json.dumps(data, separators=(',', ':'), ensure_ascii=False)
            
            # Prüfen ob sich Daten geändert haben
            if os.path.exists(filepath):
                try:
                    with open(filepath, 'r') as f:
                        existing_content = f.read()
                    if existing_content == json_str:
                        logger.debug(f"No changes detected for {filepath}, skipping write")
                        return True
                except (IOError, OSError):
                    pass  # Fehler beim Lesen ignorieren, trotzdem schreiben
                
                # Backup nur bei Änderungen erstellen
                if backup:
                    backup_path = f"{filepath}.backup"
                    shutil.copy2(filepath, backup_path)
                    # Nur neueste 5 Backups behalten
                    FileManager._cleanup_old_backups(filepath, max_backups=5)
            
            # Temporäre Datei schreiben (atomare Operation)
            temp_filepath = f"{filepath}.tmp"
            with open(temp_filepath, 'w') as f:
                f.write(json_str)
                f.flush()  # Sicherstellen dass Daten geschrieben wurden
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomares Verschieben
            shutil.move(temp_filepath, filepath)
            
            # Cache invalidieren
            FileManager._json_cache.pop(filepath, None)
            FileManager._file_mtimes[filepath] = os.path.getmtime(filepath)
            
            logger.debug(f"Successfully wrote JSON to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSON to {filepath}: {e}")
            # Cleanup temp file falls vorhanden
            try:
                temp_filepath = f"{filepath}.tmp"
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
            except:
                pass
            return False
    
    @staticmethod
    def _cleanup_old_backups(filepath: str, max_backups: int = 5):
        """Entfernt alte Backup-Dateien"""
        try:
            backup_dir = os.path.dirname(filepath)
            backup_basename = os.path.basename(filepath) + ".backup"
            
            backup_files = []
            for file in os.listdir(backup_dir):
                if file.startswith(backup_basename):
                    backup_path = os.path.join(backup_dir, file)
                    backup_files.append((backup_path, os.path.getmtime(backup_path)))
            
            # Nach Änderungszeit sortieren (neueste zuerst)
            backup_files.sort(key=lambda x: x[1], reverse=True)
            
            # Alte Backups entfernen
            for backup_path, _ in backup_files[max_backups:]:
                os.remove(backup_path)
                logger.debug(f"Removed old backup: {backup_path}")
                
        except Exception as e:
            logger.debug(f"Error cleaning up backups: {e}")  # Debug only, nicht kritisch
    
    @staticmethod
    def safe_read_json(filepath: str, default: Dict = None, use_cache: bool = True) -> Dict:
        """
        Liest JSON-Daten sicher aus Datei mit Caching
        
        Args:
            filepath: Pfad zur Datei
            default: Default-Wert bei Fehlern
            use_cache: Ob Cache verwendet werden soll
            
        Returns:
            Gelesene Daten oder Default-Wert
        """
        import json
        
        if default is None:
            default = {}
        
        try:
            # Cache-Check
            if use_cache and filepath in FileManager._json_cache:
                cached_mtime = FileManager._file_mtimes.get(filepath, 0)
                current_mtime = os.path.getmtime(filepath) if os.path.exists(filepath) else 0
                
                if cached_mtime == current_mtime:
                    logger.debug(f"Using cached JSON for {filepath}")
                    return FileManager._json_cache[filepath]
            
            # Datei nicht vorhanden
            if not os.path.exists(filepath):
                logger.info(f"File not found: {filepath}, using default")
                return default.copy() if isinstance(default, dict) else default
            
            # JSON laden
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Cache aktualisieren
            if use_cache:
                FileManager._json_cache[filepath] = data
                FileManager._file_mtimes[filepath] = os.path.getmtime(filepath)
                
                # Cache-Größe begrenzen (max 50 Dateien)
                if len(FileManager._json_cache) > 50:
                    # Älteste 10 Einträge entfernen
                    old_files = sorted(FileManager._file_mtimes.items(), 
                                     key=lambda x: x[1])[:10]
                    for old_file, _ in old_files:
                        FileManager._json_cache.pop(old_file, None)
                        FileManager._file_mtimes.pop(old_file, None)
            
            logger.debug(f"Successfully read JSON from {filepath}")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            # Versuche Backup zu laden
            backup_path = f"{filepath}.backup"
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logger.warning(f"Loaded backup file for {filepath}")
                    return data
                except:
                    pass
            return default.copy() if isinstance(default, dict) else default
            
        except Exception as e:
            logger.error(f"Error reading JSON from {filepath}: {e}")
            return default.copy() if isinstance(default, dict) else default
    
    @staticmethod
    def write_file(filepath: str, content: str, encoding: str = 'utf-8') -> bool:
        """
        Schreibt Text-Datei sicher
        
        Args:
            filepath: Pfad zur Datei
            content: Dateiinhalt
            encoding: Dateikodierung
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            with open(filepath, 'w', encoding=encoding) as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())
            
            logger.debug(f"Successfully wrote file {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing file {filepath}: {e}")
            return False

# Rate Limiting Decorator
def rate_limit(max_calls: int = 10, time_window: int = 60):
    """Rate Limiting Decorator"""
    calls = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            now = time.time()
            # Cleanup alte Einträge
            calls[func.__name__] = [call_time for call_time in calls.get(func.__name__, []) 
                                  if now - call_time < time_window]
            
            if len(calls[func.__name__]) >= max_calls:
                raise Exception(f"Rate limit exceeded for {func.__name__}")
            
            calls[func.__name__].append(now)
            return func(*args, **kwargs)
        return wrapper
    return decorator