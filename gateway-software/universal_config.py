#!/usr/bin/env python3
"""
Universelle Konfiguration für VPN Gateway Pro
Automatische Anpassung an verschiedene Netzwerk-Umgebungen
"""

import json
import os
import subprocess
import ipaddress
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from network_detector import NetworkDetector

@dataclass
class GatewayConfig:
    """Universelle Gateway-Konfiguration"""
    wan_interface: str = 'auto'
    lan_interface: str = 'auto' 
    lan_ip: str = 'auto'
    lan_network: str = 'auto'
    dhcp_range_start: str = 'auto'
    dhcp_range_end: str = 'auto'
    dns_servers: List[str] = None
    domain_name: str = 'gateway.local'
    
    def __post_init__(self):
        if self.dns_servers is None:
            self.dns_servers = ['8.8.8.8', '8.8.4.4']

class UniversalConfigurator:
    """Universeller Konfigurator für verschiedene Umgebungen"""
    
    def __init__(self, config_file: str = '/etc/gateway/config.json'):
        self.config_file = config_file
        self.detector = NetworkDetector()
        self.config = GatewayConfig()
        self.load_config()
    
    def auto_detect_configuration(self) -> GatewayConfig:
        """Automatische Konfigurationserkennung"""
        print("🔍 Erkenne Netzwerk-Konfiguration...")
        
        # Interface-Erkennung
        wan_iface, lan_iface = self.detector.auto_configure_interfaces()
        
        # Freien IP-Bereich finden
        lan_network = self._find_free_network_range()
        lan_ip = self._get_gateway_ip(lan_network)
        
        # DHCP-Bereich berechnen
        dhcp_start, dhcp_end = self._calculate_dhcp_range(lan_network)
        
        config = GatewayConfig(
            wan_interface=wan_iface,
            lan_interface=lan_iface,
            lan_ip=lan_ip,
            lan_network=lan_network,
            dhcp_range_start=dhcp_start,
            dhcp_range_end=dhcp_end
        )
        
        return config
    
    def _find_free_network_range(self) -> str:
        """Findet einen freien IP-Bereich für das LAN"""
        # Standard-Bereiche prüfen
        standard_ranges = [
            '192.168.100.0/24',
            '192.168.200.0/24', 
            '10.100.0.0/24',
            '10.200.0.0/24',
            '172.16.100.0/24'
        ]
        
        # Aktuelle Netzwerke ermitteln
        existing_networks = self.detector.scan_network_ranges()
        existing_nets = [ipaddress.IPv4Network(net, strict=False) for net in existing_networks]
        
        # Ersten freien Bereich finden
        for range_str in standard_ranges:
            test_network = ipaddress.IPv4Network(range_str, strict=False)
            
            # Prüfe ob dieser Bereich kollidiert
            collision = False
            for existing in existing_nets:
                if test_network.overlaps(existing):
                    collision = True
                    break
            
            if not collision:
                return range_str
        
        # Fallback: Dynamischen Bereich generieren
        for subnet in range(101, 255):
            test_range = f'192.168.{subnet}.0/24'
            test_network = ipaddress.IPv4Network(test_range, strict=False)
            
            collision = False
            for existing in existing_nets:
                if test_network.overlaps(existing):
                    collision = True
                    break
            
            if not collision:
                return test_range
        
        # Letzter Fallback
        return '192.168.100.0/24'
    
    def _get_gateway_ip(self, network: str) -> str:
        """Gateway-IP für ein Netzwerk bestimmen"""
        net = ipaddress.IPv4Network(network, strict=False)
        return str(list(net.hosts())[0])  # Erste IP im Bereich
    
    def _calculate_dhcp_range(self, network: str) -> Tuple[str, str]:
        """DHCP-Bereich für ein Netzwerk berechnen"""
        net = ipaddress.IPv4Network(network, strict=False)
        hosts = list(net.hosts())
        
        # DHCP-Pool: Zweite Hälfte des Bereichs
        start_idx = len(hosts) // 4  # Ab 25% des Bereichs
        end_idx = int(len(hosts) * 0.9)  # Bis 90% des Bereichs
        
        return str(hosts[start_idx]), str(hosts[end_idx])
    
    def save_config(self, config: GatewayConfig = None):
        """Konfiguration speichern"""
        if config:
            self.config = config
        
        # Verzeichnis erstellen falls nicht vorhanden
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        
        with open(self.config_file, 'w') as f:
            json.dump(asdict(self.config), f, indent=2)
        
        print(f"✅ Konfiguration gespeichert: {self.config_file}")
    
    def load_config(self) -> GatewayConfig:
        """Konfiguration laden"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.config = GatewayConfig(**data)
                print(f"📄 Konfiguration geladen: {self.config_file}")
            except Exception as e:
                print(f"⚠️ Fehler beim Laden der Konfiguration: {e}")
                self.config = GatewayConfig()
        else:
            print("📝 Erstelle neue Konfiguration...")
            self.config = self.auto_detect_configuration()
            self.save_config()
        
        return self.config
    
    def generate_dhcp_config(self) -> str:
        """Universelle DHCP-Konfiguration generieren"""
        config = self.config
        
        dhcp_config = f"""# DHCP-Server Konfiguration - Generiert automatisch
# Netzwerk: {config.lan_network}
# Gateway: {config.lan_ip}

default-lease-time 86400;
max-lease-time 172800;
authoritative;

# DNS-Server
option domain-name-servers {config.lan_ip}, {', '.join(config.dns_servers)};
option domain-name "{config.domain_name}";

# LAN-Subnet
subnet {ipaddress.IPv4Network(config.lan_network).network_address} netmask {ipaddress.IPv4Network(config.lan_network).netmask} {{
    range {config.dhcp_range_start} {config.dhcp_range_end};
    option routers {config.lan_ip};
    option broadcast-address {ipaddress.IPv4Network(config.lan_network).broadcast_address};
}}

# Automatische Host-Registrierung
update-static-leases on;

# Logging
log-facility local7;
"""
        return dhcp_config
    
    def generate_network_config(self) -> Dict[str, str]:
        """Netzwerk-Interface-Konfiguration generieren"""
        config = self.config
        
        # Netplan-Konfiguration (Ubuntu)
        netplan_config = f"""network:
  version: 2
  renderer: networkd
  ethernets:
    {config.lan_interface}:
      addresses:
        - {config.lan_ip}/{ipaddress.IPv4Network(config.lan_network).prefixlen}
      dhcp4: false
"""
        
        # Debian interfaces-Konfiguration
        interfaces_config = f"""# Gateway LAN Interface
auto {config.lan_interface}
iface {config.lan_interface} inet static
    address {config.lan_ip}
    netmask {ipaddress.IPv4Network(config.lan_network).netmask}
"""
        
        return {
            'netplan': netplan_config,
            'interfaces': interfaces_config
        }
    
    def apply_configuration(self):
        """Konfiguration anwenden"""
        config = self.config
        
        print("🔧 Wende Netzwerk-Konfiguration an...")
        
        # 1. Interface konfigurieren
        self._configure_interface()
        
        # 2. DHCP-Server konfigurieren
        self._configure_dhcp()
        
        # 3. NAT/Forwarding aktivieren
        self._configure_routing()
        
        print("✅ Konfiguration erfolgreich angewendet!")
    
    def _configure_interface(self):
        """LAN-Interface konfigurieren"""
        config = self.config
        
        try:
            # Interface IP setzen
            subprocess.run([
                'ip', 'addr', 'flush', 'dev', config.lan_interface
            ], check=True)
            
            subprocess.run([
                'ip', 'addr', 'add', 
                f"{config.lan_ip}/{ipaddress.IPv4Network(config.lan_network).prefixlen}",
                'dev', config.lan_interface
            ], check=True)
            
            subprocess.run([
                'ip', 'link', 'set', config.lan_interface, 'up'
            ], check=True)
            
            print(f"✅ Interface {config.lan_interface} konfiguriert: {config.lan_ip}")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Fehler bei Interface-Konfiguration: {e}")
    
    def _configure_dhcp(self):
        """DHCP-Server konfigurieren"""
        try:
            # DHCP-Konfiguration schreiben
            dhcp_config = self.generate_dhcp_config()
            with open('/etc/dhcp/dhcpd.conf', 'w') as f:
                f.write(dhcp_config)
            
            # Interface für DHCP festlegen
            dhcp_default = f"""INTERFACESv4="{self.config.lan_interface}"
INTERFACESv6=""
"""
            with open('/etc/default/isc-dhcp-server', 'w') as f:
                f.write(dhcp_default)
            
            # DHCP-Server starten
            subprocess.run(['systemctl', 'restart', 'isc-dhcp-server'], check=True)
            subprocess.run(['systemctl', 'enable', 'isc-dhcp-server'], check=True)
            
            print("✅ DHCP-Server konfiguriert")
            
        except Exception as e:
            print(f"❌ Fehler bei DHCP-Konfiguration: {e}")
    
    def _configure_routing(self):
        """NAT und IP-Forwarding konfigurieren"""
        config = self.config
        
        try:
            # IP-Forwarding aktivieren
            with open('/etc/sysctl.d/99-gateway.conf', 'w') as f:
                f.write('net.ipv4.ip_forward=1\n')
            
            subprocess.run(['sysctl', '-p', '/etc/sysctl.d/99-gateway.conf'], check=True)
            
            # NAT-Regeln setzen
            subprocess.run([
                'iptables', '-t', 'nat', '-A', 'POSTROUTING',
                '-o', config.wan_interface, '-j', 'MASQUERADE'
            ], check=True)
            
            subprocess.run([
                'iptables', '-A', 'FORWARD',
                '-i', config.lan_interface, '-o', config.wan_interface, '-j', 'ACCEPT'
            ], check=True)
            
            subprocess.run([
                'iptables', '-A', 'FORWARD',
                '-i', config.wan_interface, '-o', config.lan_interface,
                '-m', 'state', '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'
            ], check=True)
            
            # Regeln permanent machen
            subprocess.run(['iptables-save'], 
                         stdout=open('/etc/iptables/rules.v4', 'w'), check=True)
            
            print("✅ NAT und Routing konfiguriert")
            
        except Exception as e:
            print(f"❌ Fehler bei Routing-Konfiguration: {e}")
    
    def print_summary(self):
        """Konfiguration zusammenfassen"""
        config = self.config
        
        print("\n📊 Gateway-Konfiguration")
        print("========================")
        print(f"WAN-Interface: {config.wan_interface}")
        print(f"LAN-Interface: {config.lan_interface}")
        print(f"Gateway-IP: {config.lan_ip}")
        print(f"LAN-Netzwerk: {config.lan_network}")
        print(f"DHCP-Bereich: {config.dhcp_range_start} - {config.dhcp_range_end}")
        print(f"DNS-Server: {', '.join(config.dns_servers)}")
        print(f"Domain: {config.domain_name}")
        
        print(f"\n📁 Konfigurationsdatei: {self.config_file}")


def main():
    """CLI-Interface für universelle Konfiguration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Universelle Gateway-Konfiguration')
    parser.add_argument('--detect', action='store_true', help='Automatische Erkennung')
    parser.add_argument('--apply', action='store_true', help='Konfiguration anwenden')
    parser.add_argument('--summary', action='store_true', help='Konfiguration anzeigen')
    parser.add_argument('--config-file', default='/etc/gateway/config.json', 
                       help='Konfigurationsdatei')
    
    args = parser.parse_args()
    
    configurator = UniversalConfigurator(args.config_file)
    
    if args.detect:
        print("🔍 Führe automatische Erkennung durch...")
        config = configurator.auto_detect_configuration()
        configurator.save_config(config)
    
    if args.apply:
        print("🔧 Wende Konfiguration an...")
        configurator.apply_configuration()
    
    if args.summary or not any([args.detect, args.apply]):
        configurator.print_summary()


if __name__ == "__main__":
    main()