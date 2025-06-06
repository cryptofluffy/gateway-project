#!/usr/bin/env python3
"""
Konfigurationsmanagement für WireGuard Gateway VPS
Zentralisierte Konfiguration mit Environment Variables
"""

import os
import secrets
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Zentrale Konfigurationsklasse"""
    
    # Server Configuration
    HOST: str = os.getenv('FLASK_HOST', '0.0.0.0')
    PORT: int = int(os.getenv('FLASK_PORT', '8080'))
    DEBUG: bool = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Security
    SECRET_KEY: str = os.getenv('SECRET_KEY', secrets.token_hex(32))
    
    # WireGuard Configuration
    WIREGUARD_INTERFACE: str = os.getenv('WG_INTERFACE', 'wg0')
    WIREGUARD_CONFIG_PATH: str = os.getenv('WG_CONFIG_PATH', '/etc/wireguard/wg0.conf')
    WIREGUARD_PRIVATE_KEY_PATH: str = os.getenv('WG_PRIVATE_KEY_PATH', '/etc/wireguard/private.key')
    
    # Network Configuration
    SERVER_IP: str = os.getenv('WG_SERVER_IP', '10.8.0.1')
    SERVER_PORT: int = int(os.getenv('WG_SERVER_PORT', '51820'))
    VPN_SUBNET: str = os.getenv('WG_VPN_SUBNET', '10.8.0.0/24')
    GATEWAY_SUBNET: str = os.getenv('WG_GATEWAY_SUBNET', '10.0.0.0/24')
    
    # Data Storage
    DATA_DIR: str = os.getenv('DATA_DIR', '/etc/wireguard')
    CLIENTS_FILE: str = os.getenv('CLIENTS_FILE', '/etc/wireguard/clients.json')
    PORT_FORWARDS_FILE: str = os.getenv('PORT_FORWARDS_FILE', '/etc/wireguard/port_forwards.json')
    
    # Logging
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', '/var/log/wireguard-gateway/app.log')
    
    # GitHub Configuration  
    GITHUB_REPO: str = os.getenv('GITHUB_REPO', 'cryptofluffy/gateway-project')
    INSTALL_SCRIPT_URL: str = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/gateway-pc/quick-install.sh"
    
    # Validation
    MAX_CLIENTS: int = int(os.getenv('MAX_CLIENTS', '50'))
    MAX_PORT_FORWARDS: int = int(os.getenv('MAX_PORT_FORWARDS', '100'))
    
    def __post_init__(self):
        """Validierung nach Initialisierung"""
        # Erstelle Verzeichnisse falls nicht vorhanden
        os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)
        os.makedirs(self.DATA_DIR, exist_ok=True)
        
        # Validiere Konfiguration
        if not (1 <= self.SERVER_PORT <= 65535):
            raise ValueError(f"Invalid SERVER_PORT: {self.SERVER_PORT}")
        
        if self.MAX_CLIENTS <= 0 or self.MAX_CLIENTS > 254:
            raise ValueError(f"Invalid MAX_CLIENTS: {self.MAX_CLIENTS}")

# Globale Konfigurationsinstanz
config = Config()