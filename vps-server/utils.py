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
    
    @staticmethod
    def get_available_interfaces() -> Dict:
        """
        Ermittelt verfügbare Netzwerkschnittstellen des Systems
        
        Returns:
            Dictionary mit Interface-Informationen
        """
        interfaces = {
            'ethernet': [],
            'wireless': [],
            'virtual': [],
            'other': []
        }
        
        try:
            # Linux: /sys/class/net verwenden
            if os.path.exists('/sys/class/net'):
                for interface in os.listdir('/sys/class/net'):
                    if interface == 'lo':  # Loopback überspringen
                        continue
                    
                    interface_info = {
                        'name': interface,
                        'type': NetworkUtils._get_interface_type(interface),
                        'status': NetworkUtils._get_interface_status(interface),
                        'ip': NetworkUtils._get_interface_ip(interface)
                    }
                    
                    # Kategorisierung
                    if interface.startswith(('eth', 'enp', 'ens')):
                        interfaces['ethernet'].append(interface_info)
                    elif interface.startswith(('wlan', 'wlp', 'wifi')):
                        interfaces['wireless'].append(interface_info)
                    elif interface.startswith(('veth', 'docker', 'br-', 'virbr')):
                        interfaces['virtual'].append(interface_info)
                    else:
                        interfaces['other'].append(interface_info)
            
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
    """Sichere Datei-Operationen"""
    
    @staticmethod
    def safe_write_json(filepath: str, data: Dict, backup: bool = True) -> bool:
        """
        Schreibt JSON-Daten sicher in Datei mit optionalem Backup
        
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
            # Backup erstellen
            if backup and os.path.exists(filepath):
                shutil.copy2(filepath, f"{filepath}.backup")
            
            # Temporäre Datei schreiben
            temp_filepath = f"{filepath}.tmp"
            with open(temp_filepath, 'w') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomares Verschieben
            shutil.move(temp_filepath, filepath)
            
            logger.debug(f"Successfully wrote JSON to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing JSON to {filepath}: {e}")
            return False
    
    @staticmethod
    def safe_read_json(filepath: str, default: Dict = None) -> Dict:
        """
        Liest JSON-Daten sicher aus Datei
        
        Args:
            filepath: Pfad zur Datei
            default: Default-Wert bei Fehlern
            
        Returns:
            Gelesene Daten oder Default-Wert
        """
        import json
        
        if default is None:
            default = {}
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            logger.debug(f"Successfully read JSON from {filepath}")
            return data
        except FileNotFoundError:
            logger.info(f"File not found: {filepath}, using default")
            return default
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in {filepath}: {e}")
            return default
        except Exception as e:
            logger.error(f"Error reading JSON from {filepath}: {e}")
            return default

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