#!/usr/bin/env python3
"""
Universeller Netzwerk-Detektor für VPN Gateway Pro
Automatische Erkennung von Netzwerk-Interfaces und Geräten
"""

import subprocess
import json
import ipaddress
import socket
import threading
import time
from typing import Dict, List, Optional, Tuple

class NetworkDetector:
    def __init__(self):
        self.detected_interfaces = {}
        self.detected_devices = []
        self.network_ranges = []
    
    def detect_interfaces(self) -> Dict[str, Dict]:
        """Automatische Interface-Erkennung für alle Linux-Systeme"""
        interfaces = {}
        
        try:
            # Alle Netzwerk-Interfaces auflisten
            result = subprocess.run(['ip', 'link', 'show'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                if ':' in line and ('eth' in line or 'enp' in line or 'ens' in line or 'wlan' in line):
                    # Interface-Name extrahieren
                    parts = line.split(':')
                    if len(parts) >= 2:
                        iface_name = parts[1].strip().split('@')[0]
                        
                        # Interface-Details ermitteln
                        iface_info = self._get_interface_details(iface_name)
                        if iface_info:
                            interfaces[iface_name] = iface_info
            
        except subprocess.CalledProcessError:
            print("Fehler beim Abrufen der Interface-Liste")
        
        self.detected_interfaces = interfaces
        return interfaces
    
    def _get_interface_details(self, interface: str) -> Optional[Dict]:
        """Detaillierte Interface-Informationen"""
        try:
            # IP-Adresse ermitteln
            result = subprocess.run(['ip', 'addr', 'show', interface], 
                                  capture_output=True, text=True, check=True)
            
            info = {
                'name': interface,
                'status': 'down',
                'ip_address': None,
                'netmask': None,
                'mac_address': None,
                'type': 'unknown',
                'is_default_route': False
            }
            
            # Status ermitteln
            if 'state UP' in result.stdout:
                info['status'] = 'up'
            
            # IP-Adresse und Netzwerk ermitteln
            for line in result.stdout.split('\n'):
                if 'inet ' in line and 'scope global' in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip_with_prefix = parts[1]
                        ip, prefix = ip_with_prefix.split('/')
                        info['ip_address'] = ip
                        info['prefix_length'] = int(prefix)
                        info['network'] = str(ipaddress.IPv4Network(ip_with_prefix, strict=False))
                
                elif 'link/ether' in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        info['mac_address'] = parts[1]
            
            # Interface-Typ bestimmen
            if 'eth' in interface or 'enp' in interface or 'ens' in interface:
                info['type'] = 'ethernet'
            elif 'wlan' in interface or 'wlp' in interface:
                info['type'] = 'wireless'
            elif 'docker' in interface or 'br-' in interface:
                info['type'] = 'bridge'
            elif 'wg' in interface:
                info['type'] = 'wireguard'
            
            # Standard-Route prüfen
            try:
                route_result = subprocess.run(['ip', 'route', 'show', 'default'], 
                                            capture_output=True, text=True, check=True)
                if interface in route_result.stdout:
                    info['is_default_route'] = True
            except:
                pass
            
            return info
            
        except subprocess.CalledProcessError:
            return None
    
    def auto_configure_interfaces(self) -> Tuple[str, str]:
        """Automatische WAN/LAN Interface-Zuordnung"""
        interfaces = self.detect_interfaces()
        
        wan_interface = None
        lan_interface = None
        
        # WAN = Interface mit Default-Route
        for name, info in interfaces.items():
            if info.get('is_default_route') and info.get('status') == 'up':
                wan_interface = name
                break
        
        # LAN = Erstes verfügbares Ethernet-Interface das nicht WAN ist
        for name, info in interfaces.items():
            if (info.get('type') == 'ethernet' and 
                name != wan_interface and 
                'docker' not in name and 
                'br-' not in name):
                lan_interface = name
                break
        
        return wan_interface or 'auto', lan_interface or 'auto'
    
    def scan_network_ranges(self) -> List[str]:
        """Erkennt alle aktiven Netzwerk-Bereiche"""
        ranges = []
        
        try:
            result = subprocess.run(['ip', 'route', 'show'], 
                                  capture_output=True, text=True, check=True)
            
            for line in result.stdout.split('\n'):
                if '/' in line and ('192.168.' in line or '10.' in line or '172.' in line):
                    parts = line.split()
                    if len(parts) > 0 and '/' in parts[0]:
                        network = parts[0]
                        try:
                            # Validiere Netzwerk-Format
                            ipaddress.IPv4Network(network, strict=False)
                            ranges.append(network)
                        except:
                            pass
        
        except subprocess.CalledProcessError:
            pass
        
        self.network_ranges = list(set(ranges))  # Duplikate entfernen
        return self.network_ranges
    
    def ping_scan_range(self, network: str, timeout: int = 1) -> List[str]:
        """Ping-Scan eines Netzwerk-Bereichs"""
        active_hosts = []
        
        try:
            net = ipaddress.IPv4Network(network, strict=False)
            threads = []
            lock = threading.Lock()
            
            def ping_host(ip):
                try:
                    result = subprocess.run(['ping', '-c', '1', '-W', str(timeout), str(ip)], 
                                          capture_output=True, check=True)
                    with lock:
                        active_hosts.append(str(ip))
                except:
                    pass
            
            # Parallel ping für bessere Performance
            for ip in list(net.hosts())[:50]:  # Limitiere auf erste 50 IPs
                thread = threading.Thread(target=ping_host, args=(ip,))
                threads.append(thread)
                thread.start()
            
            # Warte auf alle Threads (max 10 Sekunden)
            for thread in threads:
                thread.join(timeout=10)
                
        except Exception as e:
            print(f"Fehler beim Netzwerk-Scan: {e}")
        
        return sorted(active_hosts, key=lambda x: ipaddress.IPv4Address(x))
    
    def port_scan(self, ip: str, ports: List[int]) -> Dict[int, bool]:
        """Port-Scan für einen Host"""
        open_ports = {}
        
        for port in ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((ip, port))
                open_ports[port] = (result == 0)
                sock.close()
            except:
                open_ports[port] = False
        
        return open_ports
    
    def detect_device_type(self, ip: str) -> Dict[str, any]:
        """Versucht Geräte-Typ zu erkennen"""
        info = {
            'ip': ip,
            'hostname': None,
            'mac_address': None,
            'device_type': 'unknown',
            'services': [],
            'confidence': 0
        }
        
        # Hostname ermitteln
        try:
            info['hostname'] = socket.gethostbyaddr(ip)[0]
        except:
            pass
        
        # MAC-Adresse aus ARP-Tabelle
        try:
            result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
            for line in result.stdout.split('\n'):
                if ip in line and ':' in line:
                    parts = line.split()
                    for part in parts:
                        if ':' in part and len(part) == 17:  # MAC-Format
                            info['mac_address'] = part
                            break
        except:
            pass
        
        # Port-Scan für Service-Erkennung
        common_ports = [22, 23, 25, 53, 80, 110, 443, 445, 993, 995, 3389, 5900, 8080, 10000]
        open_ports = self.port_scan(ip, common_ports)
        
        # Service-Klassifizierung
        for port, is_open in open_ports.items():
            if is_open:
                service = self._classify_port(port)
                if service:
                    info['services'].append(service)
        
        # Geräte-Typ basierend auf Services erraten
        info['device_type'] = self._guess_device_type(info)
        
        return info
    
    def _classify_port(self, port: int) -> Optional[str]:
        """Klassifiziert einen offenen Port"""
        port_services = {
            22: 'SSH',
            23: 'Telnet', 
            25: 'SMTP',
            53: 'DNS',
            80: 'HTTP',
            110: 'POP3',
            443: 'HTTPS',
            445: 'SMB/CIFS',
            993: 'IMAPS',
            995: 'POP3S',
            3389: 'RDP',
            5900: 'VNC',
            8080: 'HTTP-Alt',
            10000: 'Webmin'
        }
        return port_services.get(port)
    
    def _guess_device_type(self, info: Dict) -> str:
        """Versucht Geräte-Typ zu erraten"""
        services = info.get('services', [])
        hostname = info.get('hostname', '').lower()
        
        # NAS-Erkennung
        if ('SMB/CIFS' in services or 
            any(nas in hostname for nas in ['truenas', 'freenas', 'nas', 'storage'])):
            return 'nas'
        
        # Router/Gateway
        if ('HTTP' in services and 'SSH' in services and 
            any(router in hostname for router in ['router', 'gateway', 'gw'])):
            return 'router'
        
        # Server
        if len(services) >= 3:
            return 'server'
        
        # Desktop/Laptop
        if 'RDP' in services or 'VNC' in services:
            return 'desktop'
        
        # Printer
        if any(printer in hostname for printer in ['printer', 'print', 'hp', 'canon', 'epson']):
            return 'printer'
        
        return 'unknown'
    
    def find_nas_devices(self) -> List[Dict]:
        """Spezialisierte NAS-Suche"""
        nas_devices = []
        
        # Alle Netzwerk-Bereiche scannen
        for network in self.scan_network_ranges():
            print(f"Scanne {network} nach NAS-Geräten...")
            active_hosts = self.ping_scan_range(network)
            
            for ip in active_hosts:
                device_info = self.detect_device_type(ip)
                
                # NAS-spezifische Checks
                if (device_info['device_type'] == 'nas' or
                    'SMB/CIFS' in device_info['services'] or
                    any(nas in str(device_info['hostname']).lower() 
                        for nas in ['truenas', 'freenas', 'nas', 'storage'])):
                    nas_devices.append(device_info)
        
        return nas_devices
    
    def generate_dhcp_config(self, lan_interface: str, lan_ip: str = "192.168.100.1") -> str:
        """Generiert universelle DHCP-Konfiguration"""
        network_base = '.'.join(lan_ip.split('.')[:-1])
        
        config = f"""# DHCP-Server Konfiguration - Generiert am {time.strftime('%Y-%m-%d %H:%M:%S')}
# Interface: {lan_interface}
# Gateway: {lan_ip}

default-lease-time 86400;
max-lease-time 172800;
authoritative;

# DNS-Server
option domain-name-servers {lan_ip}, 8.8.8.8, 8.8.4.4;
option domain-name "gateway.local";

# LAN-Subnet
subnet {network_base}.0 netmask 255.255.255.0 {{
    range {network_base}.50 {network_base}.200;
    option routers {lan_ip};
    option broadcast-address {network_base}.255;
}}

# Logging
log-facility local7;
"""
        return config
    
    def export_config(self) -> Dict:
        """Exportiert die erkannte Konfiguration"""
        wan_iface, lan_iface = self.auto_configure_interfaces()
        
        config = {
            'detection_time': time.time(),
            'interfaces': self.detected_interfaces,
            'recommended_config': {
                'wan_interface': wan_iface,
                'lan_interface': lan_iface
            },
            'network_ranges': self.network_ranges,
            'detected_devices': self.detected_devices
        }
        
        return config


def main():
    """Hauptfunktion für CLI-Nutzung"""
    print("🔍 Universeller Netzwerk-Detektor")
    print("=================================")
    
    detector = NetworkDetector()
    
    print("\n📡 Erkenne Netzwerk-Interfaces...")
    interfaces = detector.detect_interfaces()
    
    print("\n🌐 Gefundene Interfaces:")
    for name, info in interfaces.items():
        status_icon = "✅" if info['status'] == 'up' else "❌"
        route_icon = "🌍" if info['is_default_route'] else "🏠"
        print(f"  {status_icon} {route_icon} {name} ({info['type']}) - {info.get('ip_address', 'Keine IP')}")
    
    print("\n⚙️ Empfohlene Konfiguration:")
    wan_iface, lan_iface = detector.auto_configure_interfaces()
    print(f"  WAN-Interface: {wan_iface}")
    print(f"  LAN-Interface: {lan_iface}")
    
    print("\n🔍 Suche nach NAS-Geräten...")
    nas_devices = detector.find_nas_devices()
    
    if nas_devices:
        print("\n🗄️ Gefundene NAS-Geräte:")
        for device in nas_devices:
            print(f"  ✅ {device['ip']} - {device.get('hostname', 'Unbekannt')}")
            print(f"     Services: {', '.join(device['services'])}")
    else:
        print("\n❌ Keine NAS-Geräte gefunden")
    
    # Konfiguration exportieren
    config = detector.export_config()
    with open('/tmp/network_detection.json', 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Konfiguration gespeichert: /tmp/network_detection.json")


if __name__ == "__main__":
    main()