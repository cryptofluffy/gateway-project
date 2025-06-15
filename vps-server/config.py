#!/usr/bin/env python3
"""
Konfigurationsmanagement für WireGuard Gateway VPS
Sichere, zentralisierte Konfiguration mit umfassender Validierung
"""

import os
import secrets
import ipaddress
import logging
from dataclasses import dataclass, field
from typing import Optional, List, Dict
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class SecurityConfig:
    """Sicherheitsspezifische Konfiguration"""
    SECRET_KEY: str = field(default_factory=lambda: os.getenv('SECRET_KEY', ''))
    CSRF_ENABLED: bool = True
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = 'Lax'
    PERMANENT_SESSION_LIFETIME: int = 3600  # 1 Stunde
    WTF_CSRF_TIME_LIMIT: int = 3600
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL: str = "memory://"
    RATELIMIT_DEFAULT: str = "100 per hour"
    RATELIMIT_HEADERS_ENABLED: bool = True
    
    # Authentication
    AUTH_ENABLED: bool = os.getenv('AUTH_ENABLED', 'False').lower() == 'true'
    ADMIN_USERNAME: str = os.getenv('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD_HASH: str = os.getenv('ADMIN_PASSWORD_HASH', '')
    
    def __post_init__(self):
        """Sicherheitsvalidierung"""
        if not self.SECRET_KEY:
            if os.getenv('FLASK_ENV') == 'production':
                raise ValueError("SECRET_KEY muss in Produktionsumgebung gesetzt sein!")
            else:
                self.SECRET_KEY = secrets.token_hex(32)
                logger.warning("Automatisch generierter SECRET_KEY verwendet - nicht für Produktion geeignet!")
        
        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY muss mindestens 32 Zeichen lang sein!")

@dataclass
class NetworkConfig:
    """Netzwerk-spezifische Konfiguration"""
    SERVER_IP: str = os.getenv('WG_SERVER_IP', '10.8.0.1')
    SERVER_PORT: int = int(os.getenv('WG_SERVER_PORT', '51820'))
    VPN_SUBNET: str = os.getenv('WG_VPN_SUBNET', '10.8.0.0/24')
    GATEWAY_SUBNET: str = os.getenv('WG_GATEWAY_SUBNET', '10.0.0.0/24')
    EXTERNAL_IP_SERVICES: List[str] = field(default_factory=lambda: [
        'https://ifconfig.me',
        'https://ipinfo.io/ip',
        'https://ip.42.pl/raw'
    ])
    DNS_SERVERS: List[str] = field(default_factory=lambda: ['8.8.8.8', '8.8.4.4', '1.1.1.1'])
    
    def __post_init__(self):
        """Netzwerk-Validierung"""
        # Port-Validierung
        if not (1 <= self.SERVER_PORT <= 65535):
            raise ValueError(f"Ungültiger SERVER_PORT: {self.SERVER_PORT}")
        
        if self.SERVER_PORT < 1024 and os.geteuid() != 0:
            logger.warning(f"Privilegierter Port {self.SERVER_PORT} erfordert Root-Rechte")
        
        # IP-Adress-Validierung
        try:
            ipaddress.ip_address(self.SERVER_IP)
        except ValueError:
            raise ValueError(f"Ungültige SERVER_IP: {self.SERVER_IP}")
        
        # Subnet-Validierung
        try:
            vpn_net = ipaddress.ip_network(self.VPN_SUBNET, strict=False)
            gateway_net = ipaddress.ip_network(self.GATEWAY_SUBNET, strict=False)
            
            if vpn_net.overlaps(gateway_net):
                logger.warning("VPN- und Gateway-Subnetze überschneiden sich - kann zu Routing-Problemen führen")
                
            # Server-IP muss im VPN-Subnet liegen
            if not ipaddress.ip_address(self.SERVER_IP) in vpn_net:
                raise ValueError(f"SERVER_IP {self.SERVER_IP} liegt nicht im VPN_SUBNET {self.VPN_SUBNET}")
                
        except ValueError as e:
            raise ValueError(f"Ungültige Subnet-Konfiguration: {e}")

@dataclass
class WireGuardConfig:
    """WireGuard-spezifische Konfiguration"""
    INTERFACE: str = os.getenv('WG_INTERFACE', 'wg0')
    CONFIG_PATH: str = os.getenv('WG_CONFIG_PATH', '/etc/wireguard/wg0.conf')
    PRIVATE_KEY_PATH: str = os.getenv('WG_PRIVATE_KEY_PATH', '/etc/wireguard/server_private.key')
    PUBLIC_KEY_PATH: str = os.getenv('WG_PUBLIC_KEY_PATH', '/etc/wireguard/server_public.key')
    KEEPALIVE_INTERVAL: int = int(os.getenv('WG_KEEPALIVE', '25'))
    
    def __post_init__(self):
        """WireGuard-Validierung"""
        if not self.INTERFACE.isalnum():
            raise ValueError(f"Ungültiger Interface-Name: {self.INTERFACE}")
        
        # Überprüfe ob WireGuard installiert ist
        import shutil
        if not shutil.which('wg'):
            logger.error("WireGuard-Tools nicht gefunden! Installation erforderlich.")
        
        # Verzeichnis-Berechtigungen prüfen
        config_dir = os.path.dirname(self.CONFIG_PATH)
        if os.path.exists(config_dir):
            stat_info = os.stat(config_dir)
            if stat_info.st_mode & 0o077:  # Andere haben Zugriff
                logger.warning(f"WireGuard-Verzeichnis {config_dir} ist nicht sicher (zu offene Berechtigungen)")

@dataclass
class StorageConfig:
    """Datenspeicher-Konfiguration"""
    DATA_DIR: str = os.getenv('DATA_DIR', '/etc/wireguard')
    CLIENTS_FILE: str = os.getenv('CLIENTS_FILE', '/etc/wireguard/clients.json')
    PORT_FORWARDS_FILE: str = os.getenv('PORT_FORWARDS_FILE', '/etc/wireguard/port_forwards.json')
    BACKUP_DIR: str = os.getenv('BACKUP_DIR', '/var/backups/wireguard-gateway')
    BACKUP_RETENTION_DAYS: int = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
    
    def __post_init__(self):
        """Storage-Validierung und Setup"""
        # Verzeichnisse erstellen
        directories = [self.DATA_DIR, self.BACKUP_DIR]
        for directory in directories:
            try:
                os.makedirs(directory, mode=0o750, exist_ok=True)
                
                # Besitzer und Berechtigungen prüfen
                stat_info = os.stat(directory)
                if stat_info.st_mode & 0o027:  # Gruppe/Andere haben zu viel Zugriff
                    logger.warning(f"Verzeichnis {directory} hat unsichere Berechtigungen")
                    
            except PermissionError:
                logger.error(f"Keine Berechtigung zum Erstellen von {directory}")
            except Exception as e:
                logger.error(f"Fehler beim Erstellen von {directory}: {e}")

@dataclass
class MonitoringConfig:
    """Monitoring und Logging-Konfiguration"""
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', '/var/log/wireguard-gateway/app.log')
    LOG_MAX_BYTES: int = int(os.getenv('LOG_MAX_BYTES', '5242880'))  # 5MB (reduziert für Pi)
    LOG_BACKUP_COUNT: int = int(os.getenv('LOG_BACKUP_COUNT', '3'))  # Weniger Backups
    
    # Monitoring
    MONITORING_ENABLED: bool = os.getenv('MONITORING_ENABLED', 'True').lower() == 'true'
    MONITORING_INTERVAL: int = int(os.getenv('MONITORING_INTERVAL', '60'))  # Längere Intervalle für Pi
    ALERT_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        'cpu_percent': float(os.getenv('ALERT_CPU_THRESHOLD', '90.0')),
        'memory_percent': float(os.getenv('ALERT_MEMORY_THRESHOLD', '90.0')),
        'disk_percent': float(os.getenv('ALERT_DISK_THRESHOLD', '95.0')),
        'cpu_temp': float(os.getenv('ALERT_TEMP_THRESHOLD', '80.0'))
    })
    
    def __post_init__(self):
        """Monitoring-Validierung"""
        # Log-Verzeichnis erstellen
        log_dir = os.path.dirname(self.LOG_FILE)
        try:
            os.makedirs(log_dir, mode=0o750, exist_ok=True)
        except Exception as e:
            logger.error(f"Fehler beim Erstellen des Log-Verzeichnisses: {e}")
        
        # Log-Level validieren
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.LOG_LEVEL.upper() not in valid_levels:
            logger.warning(f"Ungültiger LOG_LEVEL: {self.LOG_LEVEL}, verwende INFO")
            self.LOG_LEVEL = 'INFO'

@dataclass
class ApplicationConfig:
    """Haupt-Anwendungskonfiguration"""
    HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT: int = int(os.getenv('FLASK_PORT', '8080'))
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    ENV: str = os.getenv('FLASK_ENV', 'production')
    
    # Feature Flags
    WEBSOCKET_ENABLED: bool = os.getenv('WEBSOCKET_ENABLED', 'True').lower() == 'true'
    API_ENABLED: bool = os.getenv('API_ENABLED', 'True').lower() == 'true'
    
    # Limits
    MAX_CLIENTS: int = int(os.getenv('MAX_CLIENTS', '50'))
    MAX_PORT_FORWARDS: int = int(os.getenv('MAX_PORT_FORWARDS', '100'))
    MAX_CONTENT_LENGTH: int = int(os.getenv('MAX_CONTENT_LENGTH', '1048576'))  # 1MB
    
    # External Services
    GITHUB_REPO: str = os.getenv('GITHUB_REPO', 'cryptofluffy/gateway-project')
    
    def __post_init__(self):
        """Application-Validierung"""
        if not (1 <= self.PORT <= 65535):
            raise ValueError(f"Ungültiger PORT: {self.PORT}")
        
        if self.DEBUG and self.ENV == 'production':
            logger.warning("DEBUG-Modus in Produktionsumgebung aktiviert - Sicherheitsrisiko!")
        
        if not (1 <= self.MAX_CLIENTS <= 254):
            raise ValueError(f"MAX_CLIENTS muss zwischen 1 und 254 liegen: {self.MAX_CLIENTS}")
        
        if self.MAX_PORT_FORWARDS <= 0:
            raise ValueError(f"MAX_PORT_FORWARDS muss positiv sein: {self.MAX_PORT_FORWARDS}")
        
        # Host-Validierung - KRITISCHES SICHERHEITSRISIKO BEHEBEN
        if self.HOST == '0.0.0.0' and self.ENV == 'production':
            logger.error("SICHERHEITSFEHLER: Server kann nicht an 0.0.0.0 in Produktion binden!")
            # Automatische Korrektur: Binde an localhost für Sicherheit
            self.HOST = '127.0.0.1'
            logger.warning("Host automatisch auf 127.0.0.1 korrigiert - für externe Zugriffe VPN verwenden")
        elif self.HOST == '0.0.0.0':
            logger.warning("Server bindet an alle Interfaces (0.0.0.0) - nur für Entwicklung geeignet!")

@dataclass
class Config:
    """Zentrale Konfigurationsklasse mit allen Teilkonfigurationen"""
    
    def __init__(self):
        """Initialisiert alle Teilkonfigurationen"""
        try:
            self.security = SecurityConfig()
            self.network = NetworkConfig()
            self.wireguard = WireGuardConfig()
            self.storage = StorageConfig()
            self.monitoring = MonitoringConfig()
            self.app = ApplicationConfig()
            
            # Hardware-Erkennung für adaptive Konfiguration
            # Muss vor Setup erfolgen um Einstellungen anzupassen
            self._detect_hardware()
            
            # Kompatibilitäts-Aliases für bestehenden Code
            # Ermöglicht schrittweise Migration zu neuer Struktur
            self._setup_aliases()
            
            # Konfiguration validieren
            # Prüft alle Einstellungen auf Konsistenz
            self._validate_configuration()
            
            logger.info("Konfiguration erfolgreich geladen und validiert")
            
        except Exception as e:
            logger.error(f"Fehler bei der Konfiguration: {e}")
            raise
    
    def _setup_aliases(self):
        """Erstellt Aliases für Rückwärtskompatibilität"""
        # Flask-App Aliases
        self.HOST = self.app.HOST
        self.PORT = self.app.PORT
        self.DEBUG = self.app.DEBUG
        self.SECRET_KEY = self.security.SECRET_KEY
        
        # WireGuard Aliases
        self.WIREGUARD_INTERFACE = self.wireguard.INTERFACE
        self.WIREGUARD_CONFIG_PATH = self.wireguard.CONFIG_PATH
        self.WIREGUARD_PRIVATE_KEY_PATH = self.wireguard.PRIVATE_KEY_PATH
        
        # Network Aliases
        self.SERVER_IP = self.network.SERVER_IP
        self.SERVER_PORT = self.network.SERVER_PORT
        self.VPN_SUBNET = self.network.VPN_SUBNET
        self.GATEWAY_SUBNET = self.network.GATEWAY_SUBNET
        
        # Storage Aliases
        self.DATA_DIR = self.storage.DATA_DIR
        self.CLIENTS_FILE = self.storage.CLIENTS_FILE
        self.PORT_FORWARDS_FILE = self.storage.PORT_FORWARDS_FILE
        
        # Monitoring Aliases
        self.LOG_LEVEL = self.monitoring.LOG_LEVEL
        self.LOG_FILE = self.monitoring.LOG_FILE
        
        # Application Aliases
        self.MAX_CLIENTS = self.app.MAX_CLIENTS
        self.MAX_PORT_FORWARDS = self.app.MAX_PORT_FORWARDS
        self.GITHUB_REPO = self.app.GITHUB_REPO
        
        # Generierte URLs
        self.INSTALL_SCRIPT_URL = f"https://raw.githubusercontent.com/{self.GITHUB_REPO}/main/gateway-pc/quick-install.sh"
    
    def _detect_hardware(self):
        """Erkennt Hardware und passt Konfiguration an"""
        # Initialisiere Hardware-Flags
        self.is_raspberry_pi = False
        self.is_low_memory = False
        
        try:
            # Raspberry Pi Erkennung über CPU-Informationen
            # /proc/cpuinfo enthält Hardware-spezifische Informationen
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read().lower()
                # Pi hat charakteristische Bezeichnungen in cpuinfo
                if 'raspberry pi' in content or 'bcm' in content:
                    self.is_raspberry_pi = True
                    logger.info("Raspberry Pi erkannt - verwende ressourcenschonende Einstellungen")
            
            # Memory Erkennung für adaptive Konfiguration
            # /proc/meminfo enthält detaillierte Speicher-Informationen
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        # Parse Speichergröße (in kB)
                        mem_kb = int(line.split()[1])
                        mem_mb = mem_kb // 1024
                        
                        # Systeme mit <1GB RAM brauchen aggressive Optimierung
                        if mem_mb < 1024:  # Weniger als 1GB RAM
                            self.is_low_memory = True
                            logger.info(f"Wenig Arbeitsspeicher erkannt ({mem_mb}MB) - optimiere Konfiguration")
                        break
            
            # Hardware-spezifische Anpassungen
            # Reduziere Ressourcenverbrauch auf schwächeren Systemen
            if self.is_raspberry_pi or self.is_low_memory:
                # Längere Monitoring-Intervalle = weniger CPU-Last
                self.monitoring.MONITORING_INTERVAL = max(self.monitoring.MONITORING_INTERVAL, 120)
                
                # Kleinere Log-Dateien = weniger Disk-I/O
                self.monitoring.LOG_MAX_BYTES = min(self.monitoring.LOG_MAX_BYTES, 2097152)  # Max 2MB
                
                # Weniger Log-Backups = weniger Speicherplatz
                self.monitoring.LOG_BACKUP_COUNT = 2
                
        except Exception as e:
            logger.debug(f"Hardware-Erkennung fehlgeschlagen: {e}")
    
    def _validate_configuration(self):
        """Übergreifende Konfigurationsvalidierung"""
        # Prüfe kritische Verzeichnisse auf Zugriff
        # Verhindert spätere Laufzeit-Fehler
        test_dirs = [self.storage.DATA_DIR, os.path.dirname(self.monitoring.LOG_FILE)]
        
        for test_dir in test_dirs:
            if os.path.exists(test_dir):
                if not os.access(test_dir, os.W_OK):
                    logger.warning(f"Verzeichnis {test_dir} ist nicht beschreibbar")
        
        # Validiere WireGuard-Konfiguration
        if os.path.exists(self.wireguard.CONFIG_PATH):
            try:
                with open(self.wireguard.CONFIG_PATH, 'r') as f:
                    config_content = f.read()
                    if 'PrivateKey' not in config_content:
                        logger.warning("WireGuard-Konfiguration scheint unvollständig zu sein")
            except Exception as e:
                logger.warning(f"Konnte WireGuard-Konfiguration nicht lesen: {e}")
    
    def get_flask_config(self) -> Dict:
        """Erstellt Flask-kompatible Konfiguration"""
        return {
            'SECRET_KEY': self.security.SECRET_KEY,
            'WTF_CSRF_ENABLED': self.security.CSRF_ENABLED,
            'SESSION_COOKIE_SECURE': self.security.SESSION_COOKIE_SECURE,
            'SESSION_COOKIE_HTTPONLY': self.security.SESSION_COOKIE_HTTPONLY,
            'SESSION_COOKIE_SAMESITE': self.security.SESSION_COOKIE_SAMESITE,
            'PERMANENT_SESSION_LIFETIME': self.security.PERMANENT_SESSION_LIFETIME,
            'WTF_CSRF_TIME_LIMIT': self.security.WTF_CSRF_TIME_LIMIT,
            'MAX_CONTENT_LENGTH': self.app.MAX_CONTENT_LENGTH,
            'DEBUG': self.app.DEBUG
        }
    
    def to_dict(self) -> Dict:
        """Konvertiert Konfiguration zu Dictionary (ohne sensible Daten)"""
        return {
            'app': {
                'host': self.app.HOST,
                'port': self.app.PORT,
                'debug': self.app.DEBUG,
                'env': self.app.ENV
            },
            'network': {
                'server_ip': self.network.SERVER_IP,
                'server_port': self.network.SERVER_PORT,
                'vpn_subnet': self.network.VPN_SUBNET,
                'gateway_subnet': self.network.GATEWAY_SUBNET
            },
            'wireguard': {
                'interface': self.wireguard.INTERFACE,
                'keepalive': self.wireguard.KEEPALIVE_INTERVAL
            },
            'limits': {
                'max_clients': self.app.MAX_CLIENTS,
                'max_port_forwards': self.app.MAX_PORT_FORWARDS
            },
            'monitoring': {
                'enabled': self.monitoring.MONITORING_ENABLED,
                'interval': self.monitoring.MONITORING_INTERVAL,
                'log_level': self.monitoring.LOG_LEVEL
            }
        }

# Globale Konfigurationsinstanz
config = Config()