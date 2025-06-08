#!/usr/bin/env python3
"""
WireGuard Gateway PC Manager
Hauptanwendung für den Gateway-PC (Mini-PC/Raspberry Pi)
"""

import os
import sys
import subprocess
import json
import time
import threading
import requests
from datetime import datetime
import configparser

class WireGuardGateway:
    def __init__(self):
        self.config_file = '/etc/wireguard/gateway.conf'
        self.interface = 'wg0'
        self.vps_endpoint = None
        self.vps_public_key = None
        self.gateway_private_key = None
        self.gateway_public_key = None
        self.is_connected = False
        self.load_config()
    
    def load_config(self):
        """Lade Gateway-Konfiguration"""
        try:
            if os.path.exists('/etc/wireguard-gateway/config.json'):
                with open('/etc/wireguard-gateway/config.json', 'r') as f:
                    config = json.load(f)
                    self.vps_endpoint = config.get('vps_endpoint')
                    self.vps_public_key = config.get('vps_public_key')
        except Exception as e:
            print(f"Fehler beim Laden der Konfiguration: {e}")
    
    def generate_keys(self):
        """Generiere WireGuard-Keys für das Gateway"""
        try:
            # Private Key generieren
            result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True)
            if result.returncode == 0:
                self.gateway_private_key = result.stdout.strip()
                
                # Public Key aus Private Key ableiten
                process = subprocess.Popen(['wg', 'pubkey'], stdin=subprocess.PIPE, 
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate(input=self.gateway_private_key)
                
                if process.returncode == 0:
                    self.gateway_public_key = stdout.strip()
                    return True
            return False
        except Exception as e:
            print(f"Fehler beim Generieren der Keys: {e}")
            return False
    
    def setup_initial_config(self, vps_ip, vps_public_key):
        """Initiale Konfiguration des Gateways"""
        self.vps_endpoint = f"{vps_ip}:51820"
        self.vps_public_key = vps_public_key
        
        if not self.generate_keys():
            return False
        
        # Konfiguration speichern
        config = {
            'vps_endpoint': self.vps_endpoint,
            'vps_public_key': self.vps_public_key,
            'gateway_private_key': self.gateway_private_key,
            'gateway_public_key': self.gateway_public_key
        }
        
        os.makedirs('/etc/wireguard-gateway', exist_ok=True)
        with open('/etc/wireguard-gateway/config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        return self.create_wireguard_config()
    
    def create_wireguard_config(self):
        """Erstelle WireGuard-Konfigurationsdatei"""
        config_content = f"""[Interface]
PrivateKey = {self.gateway_private_key}
Address = 10.8.0.2/24
Table = off

# Routing-Regeln für Gateway-Funktion
PostUp = ip rule add from 10.0.0.0/24 table 200
PostUp = ip route add default dev %i table 200
PostUp = iptables -t nat -A POSTROUTING -o %i -j MASQUERADE
PostUp = iptables -A FORWARD -i eth1 -o %i -j ACCEPT
PostUp = iptables -A FORWARD -i %i -o eth1 -j ACCEPT

PostDown = ip rule del from 10.0.0.0/24 table 200
PostDown = ip route del default dev %i table 200
PostDown = iptables -t nat -D POSTROUTING -o %i -j MASQUERADE
PostDown = iptables -D FORWARD -i eth1 -o %i -j ACCEPT
PostDown = iptables -D FORWARD -i %i -o eth1 -j ACCEPT

[Peer]
PublicKey = {self.vps_public_key}
Endpoint = {self.vps_endpoint}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
        
        try:
            os.makedirs('/etc/wireguard', exist_ok=True)
            with open(self.config_file, 'w') as f:
                f.write(config_content)
            return True
        except Exception as e:
            print(f"Fehler beim Erstellen der WireGuard-Konfiguration: {e}")
            return False
    
    def setup_network_interfaces(self):
        """Konfiguriere Netzwerk-Interfaces für Gateway-Funktion"""
        print("🌐 Netzwerk-Interfaces werden konfiguriert...")
        
        # Interface-Konfigurationen
        interfaces = [
            {'dev': 'eth0', 'ip': '192.168.1.254/24', 'desc': 'Heimnetzwerk (Port A)'},
            {'dev': 'eth1', 'ip': '10.0.0.1/24', 'desc': 'Server-Netzwerk (Port B)'}
        ]
        
        for iface in interfaces:
            try:
                # Entferne bestehende IP-Adressen auf dem Interface
                subprocess.run(['ip', 'addr', 'flush', 'dev', iface['dev']], 
                              capture_output=True, text=True)
                
                # Füge neue IP-Adresse hinzu
                result = subprocess.run(['ip', 'addr', 'add', iface['ip'], 'dev', iface['dev']], 
                                      capture_output=True, text=True)
                
                if result.returncode != 0:
                    # Prüfe ob die Adresse bereits existiert (ist OK)
                    if "File exists" in result.stderr or "cannot assign requested address" in result.stderr.lower():
                        print(f"ℹ️ IP {iface['ip']} bereits auf {iface['dev']} vorhanden")
                    else:
                        print(f"⚠️ Warnung bei {iface['desc']}: {result.stderr}")
                
                # Interface aktivieren
                subprocess.run(['ip', 'link', 'set', iface['dev'], 'up'], 
                              capture_output=True, text=True)
                
            except Exception as e:
                print(f"Fehler bei Netzwerk-Setup: {iface['desc']} - {e}")
                print("⚠️ Netzwerk-Konfiguration teilweise fehlgeschlagen (normal bei erstem Setup)")
        
        # IP-Forwarding aktivieren
        try:
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], 
                          capture_output=True, text=True)
        except Exception as e:
            print(f"IP-Forwarding Fehler: {e}")
                
        return True
    
    def cleanup_existing_interfaces(self):
        """Bereinige bestehende WireGuard-Interfaces"""
        try:
            print("🧹 Bereinige bestehende WireGuard-Interfaces...")
            
            # Explizit das Gateway-Interface bereinigen
            subprocess.run(['wg-quick', 'down', 'gateway'], 
                          capture_output=True, text=True)
            
            # Zusätzlich manuell Interface entfernen falls noch vorhanden
            subprocess.run(['ip', 'link', 'delete', 'gateway'], 
                          capture_output=True, text=True)
            
            return True
        except Exception as e:
            # Fehler hier sind normal (Interface existiert möglicherweise nicht)
            return True

    def start_tunnel(self):
        """Starte WireGuard-Tunnel"""
        try:
            # Bereinige bestehende Interfaces
            self.cleanup_existing_interfaces()
            
            print("🚀 Starte Gateway...")
            result = subprocess.run(['wg-quick', 'up', 'gateway'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.is_connected = True
                print("✅ Gateway erfolgreich gestartet!")
                return True
            else:
                print(f"Fehler beim Starten des Tunnels: {result.stderr}")
                return False
        except Exception as e:
            print(f"Fehler beim Starten des Tunnels: {e}")
            return False
    
    def stop_tunnel(self):
        """Stoppe WireGuard-Tunnel"""
        try:
            result = subprocess.run(['wg-quick', 'down', 'gateway'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                self.is_connected = False
                return True
            else:
                print(f"Fehler beim Stoppen des Tunnels: {result.stderr}")
                return False
        except Exception as e:
            print(f"Fehler beim Stoppen des Tunnels: {e}")
            return False
    
    def get_tunnel_status(self):
        """Status des WireGuard-Tunnels abfragen"""
        try:
            result = subprocess.run(['wg', 'show', 'gateway'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                return {
                    'status': 'connected',
                    'output': result.stdout,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                return {
                    'status': 'disconnected',
                    'output': result.stderr,
                    'timestamp': datetime.now().isoformat()
                }
        except Exception as e:
            return {
                'status': 'error',
                'output': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_interface_stats(self):
        """Netzwerk-Interface-Statistiken"""
        stats = {}
        interfaces = ['eth0', 'eth1', 'wg0']
        
        for iface in interfaces:
            try:
                with open(f'/sys/class/net/{iface}/statistics/rx_bytes', 'r') as f:
                    rx_bytes = int(f.read().strip())
                with open(f'/sys/class/net/{iface}/statistics/tx_bytes', 'r') as f:
                    tx_bytes = int(f.read().strip())
                
                stats[iface] = {
                    'rx_bytes': rx_bytes,
                    'tx_bytes': tx_bytes,
                    'rx_mb': round(rx_bytes / 1024 / 1024, 2),
                    'tx_mb': round(tx_bytes / 1024 / 1024, 2)
                }
            except Exception:
                stats[iface] = {'status': 'unavailable'}
        
        return stats
    
    def test_connectivity(self):
        """Teste Verbindung zum VPS"""
        try:
            result = subprocess.run(['ping', '-c', '3', '10.8.0.1'], 
                                  capture_output=True, text=True, timeout=10)
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'latency': self.extract_ping_time(result.stdout) if result.returncode == 0 else None
            }
        except Exception as e:
            return {
                'success': False,
                'output': str(e),
                'latency': None
            }
    
    def extract_ping_time(self, ping_output):
        """Extrahiere Ping-Zeit aus ping-Ausgabe"""
        try:
            lines = ping_output.split('\n')
            for line in lines:
                if 'time=' in line:
                    time_part = line.split('time=')[1].split()[0]
                    return float(time_part)
        except Exception:
            pass
        return None
    
    def setup_dhcp_server(self):
        """DHCP-Server für Server-Netzwerk (eth1) einrichten"""
        dhcp_config = """
# DHCP-Konfiguration für Gateway eth1
subnet 10.0.0.0 netmask 255.255.255.0 {
    range 10.0.0.100 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    default-lease-time 600;
    max-lease-time 7200;
}
"""
        
        try:
            with open('/etc/dhcp/dhcpd.conf', 'w') as f:
                f.write(dhcp_config)
            
            # DHCP-Server starten
            subprocess.run(['systemctl', 'enable', 'isc-dhcp-server'], check=True)
            subprocess.run(['systemctl', 'start', 'isc-dhcp-server'], check=True)
            return True
        except Exception as e:
            print(f"Fehler beim DHCP-Setup: {e}")
            return False

class GatewayMonitor:
    def __init__(self, gateway):
        self.gateway = gateway
        self.running = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Starte kontinuierliches Monitoring"""
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """Stoppe Monitoring"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join()
    
    def _monitor_loop(self):
        """Monitoring-Schleife"""
        while self.running:
            try:
                # Tunnel-Status prüfen
                status = self.gateway.get_tunnel_status()
                
                # Bei Verbindungsabbruch automatisch reconnecten
                if status['status'] == 'disconnected' and self.gateway.is_connected:
                    print("Tunnel-Verbindung verloren - versuche Reconnect...")
                    self.gateway.stop_tunnel()
                    time.sleep(5)
                    self.gateway.start_tunnel()
                
                # Logs schreiben
                with open('/var/log/wireguard-gateway/monitor.log', 'a') as f:
                    f.write(f"{datetime.now().isoformat()} - Status: {status['status']}\n")
                
                time.sleep(30)  # Alle 30 Sekunden prüfen
                
            except Exception as e:
                print(f"Monitoring-Fehler: {e}")
                time.sleep(60)

if __name__ == "__main__":
    gateway = WireGuardGateway()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            if len(sys.argv) != 4:
                print("Usage: python3 gateway_manager.py setup <VPS_IP> <VPS_PUBLIC_KEY>")
                sys.exit(1)
            
            vps_ip = sys.argv[2]
            vps_public_key = sys.argv[3]
            
            print("🔧 Gateway wird konfiguriert...")
            if gateway.setup_initial_config(vps_ip, vps_public_key):
                print("✅ Gateway-Konfiguration erstellt")
                
                # Gateway Public Key prominent ausgeben für Copy&Paste
                print("")
                print("🔑 GATEWAY PUBLIC KEY FÜR VPS DASHBOARD:")
                print("=" * 50)
                print(gateway.gateway_public_key)
                print("=" * 50)
                print("")
                print("💡 Diesen Key im VPS Dashboard unter 'Gateway-Client hinzufügen' eingeben!")
                
                # Netzwerk-Setup durchführen
                print("🌐 Netzwerk-Interfaces werden konfiguriert...")
                if gateway.setup_network_interfaces():
                    print("✅ Netzwerk-Konfiguration erfolgreich")
                else:
                    print("⚠️ Netzwerk-Konfiguration teilweise fehlgeschlagen (normal bei erstem Setup)")
                
            else:
                print("❌ Fehler bei der Konfiguration")
                sys.exit(1)
        
        elif command == "start":
            print("🚀 Starte Gateway...")
            if gateway.start_tunnel():
                print("✅ Gateway erfolgreich gestartet")
            else:
                print("❌ Fehler beim Starten")
                sys.exit(1)
        
        elif command == "stop":
            print("🛑 Stoppe Gateway...")
            if gateway.stop_tunnel():
                print("✅ Gateway erfolgreich gestoppt")
            else:
                print("❌ Fehler beim Stoppen")
                sys.exit(1)
        
        elif command == "status":
            status = gateway.get_tunnel_status()
            print(f"Status: {status['status']}")
            if status['output']:
                print(f"Details:\n{status['output']}")
        
        elif command == "monitor":
            print("🔍 Starte Gateway-Monitoring...")
            monitor = GatewayMonitor(gateway)
            monitor.start_monitoring()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Monitoring gestoppt")
                monitor.stop_monitoring()
        
        else:
            print("Unbekannter Befehl:", command)
            sys.exit(1)
    
    else:
        print("WireGuard Gateway Manager")
        print("Verfügbare Befehle:")
        print("  setup <VPS_IP> <VPS_PUBLIC_KEY> - Gateway konfigurieren")
        print("  start                           - Gateway starten")
        print("  stop                            - Gateway stoppen") 
        print("  status                          - Status anzeigen")
        print("  monitor                         - Monitoring starten")