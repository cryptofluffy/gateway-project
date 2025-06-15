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
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime
import configparser
from urllib.parse import urlparse

# Gateway Monitoring importieren
try:
    from system_monitor import GatewaySystemMonitor, start_gateway_monitoring
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False
    print("⚠️ System-Monitoring nicht verfügbar - system_monitor.py nicht gefunden")

class WireGuardGateway:
    def __init__(self):
        self.config_file = '/etc/wireguard/gateway.conf'
        self.interface = 'wg0'
        self.vps_endpoint = None
        self.vps_public_key = None
        self.gateway_private_key = None
        self.gateway_public_key = None
        self.is_connected = False
        self._setup_requests_session()
        self.load_config()
    
    def _setup_requests_session(self):
        """Konfiguriert requests für bessere Performance auf Pi"""
        # Session wiederverwenden reduziert Connection-Overhead
        self.session = requests.Session()
        
        # Retry-Strategie für instabile Netzwerkverbindungen
        # Besonders wichtig bei schwachen Internet-Verbindungen
        retry_strategy = Retry(
            total=3,  # Max 3 Wiederholungsversuche
            backoff_factor=1,  # Exponentielles Backoff
            status_forcelist=[429, 500, 502, 503, 504],  # Server-Fehler wiederholen
        )
        
        # HTTP-Adapter mit Retry-Logik
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def normalize_url(self, url):
        """Normalisiert URL durch Hinzufügen von http:// wenn kein Schema vorhanden ist"""
        if not url:
            return url
        
        # Bereinige URL von Leerzeichen
        url = url.strip()
        
        # Parse URL um Schema zu prüfen
        parsed = urlparse(url)
        if not parsed.scheme:
            # Kein Schema vorhanden, füge http:// als Standard hinzu
            # HTTP als Default da VPS oft keine SSL-Zertifikate haben
            url = f"http://{url}"
        
        return url
    
    def load_config(self):
        """Lade Gateway-Konfiguration"""
        try:
            # Standard-Pfad für Gateway-Konfiguration
            if os.path.exists('/etc/wireguard-gateway/config.json'):
                with open('/etc/wireguard-gateway/config.json', 'r') as f:
                    config = json.load(f)
                    
                    # Lade VPS-Verbindungsparameter
                    self.vps_endpoint = config.get('vps_endpoint')
                    self.vps_public_key = config.get('vps_public_key')
                    
                    # VPS API-Endpunkt für automatische Key-Updates
                    # Normalisiere URL für konsistente Verwendung
                    self.vps_api_url = self.normalize_url(config.get('vps_api_url'))
                    
                    # Lade Netzwerk-Interface-Konfiguration
                    self.network_config = config.get('network_config', {})
                    self.wan_interface = self.network_config.get('wan_interface', 'auto')
                    self.lan_interface = self.network_config.get('lan_interface', 'auto')
        except Exception as e:
            # Konfigurationsfehler sind nicht kritisch beim Start
            print(f"Fehler beim Laden der Konfiguration: {e}")
            # Fallback-Werte setzen
            self.network_config = {}
            self.wan_interface = 'auto'
            self.lan_interface = 'auto'
    
    def fetch_vps_public_key(self, vps_api_url):
        """Hole aktuellen VPS Public Key vom VPS Dashboard API"""
        try:
            # URL normalisieren BEVOR wir sie verwenden
            vps_api_url = self.normalize_url(vps_api_url)
            print("🔄 Hole aktuellen VPS Public Key vom Dashboard...")
            print(f"📡 Verbinde zu: {vps_api_url}")
            
            # API-Endpunkt aufrufen (längerer Timeout für Pi)
            # 30s Timeout für langsame Internet-Verbindungen
            response = self.session.get(f"{vps_api_url}/api/vps-info", timeout=30)
            
            if response.status_code == 200:
                vps_info = response.json()
                if vps_info.get('success') and vps_info.get('public_key'):
                    print("✅ VPS Public Key erfolgreich abgerufen")
                    return {
                        'public_key': vps_info['public_key'],
                        'endpoint': vps_info.get('endpoint')
                    }
                else:
                    print(f"❌ Ungültige API-Antwort: {vps_info}")
                    return None
            elif response.status_code == 404:
                print("❌ API-Route /api/vps-info nicht verfügbar")
                print("💡 Manuelles Setup verwenden:")
                print(f"   python3 gateway_manager.py setup {vps_api_url} <VPS_PUBLIC_KEY>")
                print("   (VPS Public Key aus dem VPS Dashboard kopieren)")
                return None
            else:
                print(f"❌ API-Fehler: HTTP {response.status_code}")
                return None
                
        except requests.exceptions.ConnectTimeout:
            # Timeout häufig bei schlechter Internet-Verbindung oder überlasteten Pi
            print("❌ Timeout beim Verbinden zum VPS Dashboard (Netzwerk langsam?)")
        except requests.exceptions.ConnectionError:
            # Connection-Fehler: VPS offline, falsche URL, Firewall, etc.
            print("❌ Verbindungsfehler zum VPS Dashboard (VPS erreichbar?)")
        except Exception as e:
            print(f"❌ Fehler beim Abrufen des VPS Public Key: {e}")
        
        return None
    
    def detect_interfaces(self):
        """Automatische Interface-Erkennung"""
        try:
            # Alle verfügbaren Netzwerk-Interfaces ermitteln
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
            interfaces = []
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if ': ' in line and not line.startswith(' '):
                        # Extrahiere Interface-Name
                        interface_name = line.split(':')[1].strip().split('@')[0]
                        # Überspringe Loopback und virtuelle Interfaces
                        if interface_name not in ['lo'] and not interface_name.startswith('wg'):
                            interfaces.append(interface_name)
            
            # Sortiere Interfaces: Ethernet vor WLAN
            eth_interfaces = [iface for iface in interfaces if iface.startswith(('eth', 'en'))]
            wlan_interfaces = [iface for iface in interfaces if iface.startswith(('wlan', 'wl'))]
            other_interfaces = [iface for iface in interfaces if not iface.startswith(('eth', 'en', 'wlan', 'wl'))]
            
            sorted_interfaces = eth_interfaces + wlan_interfaces + other_interfaces
            
            print(f"🔍 Erkannte Interfaces: {sorted_interfaces}")
            return sorted_interfaces
            
        except Exception as e:
            print(f"Fehler bei Interface-Erkennung: {e}")
            return ['eth0']  # Fallback - nur ein Interface falls Detection fehlschlägt
    
    def get_actual_interfaces(self):
        """Ermittle die tatsächlich zu verwendenden Interfaces - Dashboard hat Priorität"""
        
        # Dashboard-Konfiguration hat IMMER Priorität
        wan_iface = self.wan_interface
        lan_iface = self.lan_interface
        
        # Nur Auto-Detection wenn Dashboard nicht konfiguriert
        if wan_iface == 'auto' or lan_iface == 'auto':
            detected = self.detect_interfaces()
            
            if wan_iface == 'auto':
                wan_iface = detected[0] if detected else 'eth0'
                
            if lan_iface == 'auto':
                lan_iface = detected[1] if len(detected) > 1 else 'eth1'
        
        print(f"📡 WAN Interface (Internet): {wan_iface}")
        print(f"🖧 LAN Interface (Server): {lan_iface}")
        
        return wan_iface, lan_iface
    
    def update_network_config(self, network_config):
        """Aktualisiert die Netzwerk-Interface-Konfiguration vom Dashboard"""
        if not network_config:
            print("⚠️ Keine Netzwerk-Konfiguration erhalten")
            return False
            
        try:
            print(f"🔄 Aktualisiere Interface-Konfiguration...")
            print(f"   WAN: {network_config.get('wan_interface', 'auto')}")
            print(f"   LAN: {network_config.get('lan_interface', 'auto')}")
            
            # Neue Konfiguration setzen
            self.network_config = network_config
            self.wan_interface = network_config.get('wan_interface', 'auto')
            self.lan_interface = network_config.get('lan_interface', 'auto')
            
            # Konfigurationsdatei aktualisieren
            if os.path.exists('/etc/wireguard-gateway/config.json'):
                with open('/etc/wireguard-gateway/config.json', 'r') as f:
                    config = json.load(f)
                
                config['network_config'] = self.network_config
                
                with open('/etc/wireguard-gateway/config.json', 'w') as f:
                    json.dump(config, f, indent=2)
                
                print("✅ Netzwerk-Konfiguration aktualisiert und gespeichert")
                return True
            else:
                print("❌ Gateway-Konfigurationsdatei nicht gefunden")
                return False
                
        except Exception as e:
            print(f"❌ Fehler beim Aktualisieren der Netzwerk-Konfiguration: {e}")
            return False
    
    def update_vps_public_key(self):
        """Aktualisiere VPS Public Key automatisch"""
        # Prüfe ob API-URL konfiguriert ist
        if not self.vps_api_url:
            print("⚠️ Keine VPS API URL konfiguriert")
            return False
        
        vps_info = self.fetch_vps_public_key(self.vps_api_url)
        if vps_info:
            old_key = self.vps_public_key
            self.vps_public_key = vps_info['public_key']
            
            if vps_info.get('endpoint'):
                self.vps_endpoint = vps_info['endpoint']
            
            # Prüfe ob sich der Key geändert hat
            if old_key != self.vps_public_key:
                print("🔄 VPS Public Key hat sich geändert - aktualisiere Konfiguration...")
                
                # Konfiguration persistent speichern
                try:
                    with open('/etc/wireguard-gateway/config.json', 'r') as f:
                        config = json.load(f)
                    
                    config['vps_public_key'] = self.vps_public_key
                    config['vps_endpoint'] = self.vps_endpoint
                    
                    with open('/etc/wireguard-gateway/config.json', 'w') as f:
                        json.dump(config, f, indent=2)
                    
                    # WireGuard-Konfiguration neu erstellen
                    if self.create_wireguard_config():
                        print("✅ Konfiguration mit neuem VPS Public Key aktualisiert")
                        return True
                    else:
                        print("❌ Fehler beim Aktualisieren der WireGuard-Konfiguration")
                        return False
                        
                except Exception as e:
                    print(f"❌ Fehler beim Speichern der Konfiguration: {e}")
                    return False
            else:
                print("ℹ️ VPS Public Key ist bereits aktuell")
                return True
        
        return False
    
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
    
    def setup_initial_config(self, vps_ip, vps_public_key, network_config=None):
        """Initiale Konfiguration des Gateways mit manuellen Parametern"""
        # VPS-Parameter setzen
        self.vps_public_key = vps_public_key
        self.vps_endpoint = f"{vps_ip}:51820"
        
        # Optional: API URL für Dashboard-Integration
        self.vps_api_url = f"http://{vps_ip}:8080"
        
        # Netzwerk-Konfiguration setzen (Standard: automatisch)
        if network_config:
            self.network_config = network_config
            self.wan_interface = network_config.get('wan_interface', 'auto')
            self.lan_interface = network_config.get('lan_interface', 'auto')
        else:
            # Standardkonfiguration: automatische Interface-Erkennung
            self.network_config = {
                'wan_interface': 'auto',
                'lan_interface': 'auto',
                'auto_detect': True
            }
            self.wan_interface = 'auto'
            self.lan_interface = 'auto'
        
        print(f"✅ VPS Public Key gesetzt: {self.vps_public_key[:20]}...")
        print(f"✅ VPS Endpoint: {self.vps_endpoint}")
        print(f"✅ VPS Dashboard URL: {self.vps_api_url}")
        print(f"✅ Netzwerk-Konfiguration: WAN={self.wan_interface}, LAN={self.lan_interface}")
        
        if not self.generate_keys():
            return False
        
        # Konfiguration speichern
        config = {
            'vps_api_url': self.vps_api_url,
            'vps_endpoint': self.vps_endpoint,
            'vps_public_key': self.vps_public_key,
            'gateway_private_key': self.gateway_private_key,
            'gateway_public_key': self.gateway_public_key,
            'network_config': self.network_config
        }
        
        os.makedirs('/etc/wireguard-gateway', exist_ok=True)
        with open('/etc/wireguard-gateway/config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        if not self.create_wireguard_config():
            return False
        
        # Gateway Public Key anzeigen für manuelles Hinzufügen
        print(f"")
        print(f"🔑 Gateway-Setup abgeschlossen!")
        print(f"📋 Nächster Schritt: Gateway im VPS-Dashboard hinzufügen")
        print(f"")
        print(f"   Gateway Public Key: {self.gateway_public_key}")
        print(f"")
        print(f"💡 Kopiere den Public Key und füge das Gateway im VPS-Dashboard hinzu")
        
        return True
    
    def create_wireguard_config(self):
        """Erstelle WireGuard-Konfigurationsdatei mit dynamischen Interfaces"""
        # Ermittle die tatsächlich zu verwendenden Interfaces
        wan_iface, lan_iface = self.get_actual_interfaces()
        
        config_content = f"""[Interface]
PrivateKey = {self.gateway_private_key}
Address = 10.8.0.2/24
Table = off

# Nur Server-Netzwerk ({lan_iface}) über VPN routen - {wan_iface} bleibt lokal
PostUp = ip rule add from 10.0.0.0/24 table 200 priority 100
PostUp = ip route add default dev %i table 200
PostUp = ip route add 10.0.0.0/24 dev {lan_iface} table 200
PostUp = iptables -t nat -A POSTROUTING -s 10.0.0.0/24 -o %i -j MASQUERADE
PostUp = iptables -A FORWARD -i {lan_iface} -o %i -j ACCEPT
PostUp = iptables -A FORWARD -i %i -o {lan_iface} -j ACCEPT
PostUp = iptables -A FORWARD -s 10.0.0.0/24 -j ACCEPT

PostDown = ip rule del from 10.0.0.0/24 table 200 2>/dev/null || true
PostDown = ip route del default dev %i table 200 2>/dev/null || true
PostDown = ip route del 10.0.0.0/24 dev {lan_iface} table 200 2>/dev/null || true
PostDown = iptables -t nat -D POSTROUTING -s 10.0.0.0/24 -o %i -j MASQUERADE 2>/dev/null || true
PostDown = iptables -D FORWARD -i {lan_iface} -o %i -j ACCEPT 2>/dev/null || true
PostDown = iptables -D FORWARD -i %i -o {lan_iface} -j ACCEPT 2>/dev/null || true
PostDown = iptables -D FORWARD -s 10.0.0.0/24 -j ACCEPT 2>/dev/null || true

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
    
    def register_with_vps(self, gateway_name="Gateway-PC", location="Auto-Setup"):
        """Registriere Gateway automatisch beim VPS über API"""
        try:
            # VPS-API URL aufbauen
            api_url = f"{self.vps_api_url}/api/clients"
            
            # Registrierungs-Daten
            data = {
                "name": gateway_name,
                "location": location,
                "public_key": self.gateway_public_key
            }
            
            print(f"📡 Sende Registrierung an: {api_url}")
            
            # API-Anfrage senden
            response = requests.post(
                api_url,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ {result.get('message', 'Gateway registriert')}")
                    return True
                else:
                    print(f"❌ VPS-Fehler: {result.get('message', 'Unbekannter Fehler')}")
                    return False
            else:
                print(f"❌ HTTP-Fehler: {response.status_code}")
                return False
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout bei VPS-Verbindung")
            return False
        except requests.exceptions.ConnectionError:
            print(f"❌ Kann VPS nicht erreichen")
            return False
        except Exception as e:
            print(f"❌ Registrierungsfehler: {e}")
            return False
    
    def setup_network_interfaces(self):
        """Konfiguriere Netzwerk-Interfaces für Gateway-Funktion mit dynamischen Interfaces"""
        print("🌐 Netzwerk-Interfaces werden konfiguriert...")
        
        # Ermittle die tatsächlich zu verwendenden Interfaces
        wan_iface, lan_iface = self.get_actual_interfaces()
        
        # Interface-Konfigurationen
        # WAN Interface: Heimnetz-Client (DHCP von FritzBox)
        # LAN Interface: Server-Gateway (eigener DHCP für abgeschirmtes Netz)
        interfaces = [
            {'dev': lan_iface, 'ip': '10.0.0.1/24', 'desc': f'Server-Netzwerk ({lan_iface} - Gateway-Funktion)'}
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
                
                print(f"✅ Interface {iface['dev']} als Server-Gateway (10.0.0.1/24) konfiguriert")
                
            except Exception as e:
                print(f"Fehler bei Netzwerk-Setup: {iface['desc']} - {e}")
                print("⚠️ Netzwerk-Konfiguration teilweise fehlgeschlagen (normal bei erstem Setup)")
        
        # IP-Forwarding aktivieren
        try:
            subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], 
                          capture_output=True, text=True)
            print("✅ IP-Forwarding aktiviert")
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
        """Starte WireGuard-Tunnel mit automatischem VPS Key Update"""
        try:
            # VPS Public Key vor dem Start aktualisieren
            if self.vps_api_url:
                print("🔄 Prüfe VPS Public Key vor Start...")
                self.update_vps_public_key()
            
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
        """Netzwerk-Interface-Statistiken (nur aktive Interfaces)"""
        stats = {}
        
        # Dynamische Interface-Erkennung
        try:
            # Alle verfügbaren Interfaces scannen
            net_dir = '/sys/class/net'
            if os.path.exists(net_dir):
                for iface in os.listdir(net_dir):
                    # Überspringe Loopback-Interface
                    if iface == 'lo':
                        continue
                    
                    # Prüfe ob Interface aktiv ist
                    try:
                        with open(f'{net_dir}/{iface}/operstate', 'r') as f:
                            state = f.read().strip()
                        
                        # Nur aktive Interfaces (up) berücksichtigen
                        if state not in ['up', 'unknown']:
                            continue
                        
                        # Statistiken lesen
                        with open(f'{net_dir}/{iface}/statistics/rx_bytes', 'r') as f:
                            rx_bytes = int(f.read().strip())
                        with open(f'{net_dir}/{iface}/statistics/tx_bytes', 'r') as f:
                            tx_bytes = int(f.read().strip())
                        
                        # Prüfe ob Interface IP-Adresse hat
                        has_ip = False
                        try:
                            result = subprocess.run(['ip', 'addr', 'show', iface], 
                                                  capture_output=True, text=True)
                            if 'inet ' in result.stdout:
                                has_ip = True
                        except Exception:
                            pass
                        
                        # Nur Interfaces mit IP-Adresse oder wichtige virtuelle Interfaces
                        if has_ip or iface.startswith(('wg', 'gateway')):
                            stats[iface] = {
                                'rx_bytes': rx_bytes,
                                'tx_bytes': tx_bytes,
                                'rx_mb': round(rx_bytes / 1024 / 1024, 2),
                                'tx_mb': round(tx_bytes / 1024 / 1024, 2),
                                'state': state
                            }
                            
                    except Exception:
                        # Interface nicht lesbar - überspringe
                        continue
        except Exception:
            # Fallback: feste Liste für ältere Systeme
            fallback_interfaces = ['eth0', 'wg0', 'gateway']
            for iface in fallback_interfaces:
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
                    continue
        
        return stats
    
    def test_connectivity(self):
        """Teste Verbindung zum VPS und Internet"""
        results = {}
        
        # Test 1: VPS Verbindung
        try:
            result = subprocess.run(['ping', '-c', '3', '10.8.0.1'], 
                                  capture_output=True, text=True, timeout=10)
            results['vps'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'latency': self.extract_ping_time(result.stdout) if result.returncode == 0 else None
            }
        except Exception as e:
            results['vps'] = {
                'success': False,
                'output': str(e),
                'latency': None
            }
        
        # Test 2: Internet Verbindung (DNS)
        try:
            result = subprocess.run(['ping', '-c', '3', '8.8.8.8'], 
                                  capture_output=True, text=True, timeout=10)
            results['internet'] = {
                'success': result.returncode == 0,
                'output': result.stdout,
                'latency': self.extract_ping_time(result.stdout) if result.returncode == 0 else None
            }
        except Exception as e:
            results['internet'] = {
                'success': False,
                'output': str(e),
                'latency': None
            }
        
        # Test 3: DNS Auflösung
        try:
            result = subprocess.run(['nslookup', 'google.com'], 
                                  capture_output=True, text=True, timeout=5)
            results['dns'] = {
                'success': result.returncode == 0,
                'output': result.stdout
            }
        except Exception as e:
            results['dns'] = {
                'success': False,
                'output': str(e)
            }
        
        # Gesamtstatus
        results['overall'] = {
            'success': results['vps']['success'] and results['internet']['success'],
            'vps_reachable': results['vps']['success'],
            'internet_reachable': results['internet']['success'],
            'dns_working': results['dns']['success']
        }
        
        return results
    
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
    
    def get_lan_interface_for_dhcp(self):
        """Ermittle das LAN-Interface für DHCP-Konfiguration"""
        _, lan_iface = self.get_actual_interfaces()
        return lan_iface
    
    def setup_dhcp_server(self):
        """DHCP-Server nur für Server-Netzwerk mit dynamischem Interface"""
        # Ermittle das korrekte LAN-Interface
        lan_iface = self.get_lan_interface_for_dhcp()
        
        dhcp_config = f"""
# DHCP nur für Server-Netzwerk ({lan_iface}) - Internet über VPN
# WAN-Interface hat bereits DHCP von FritzBox/Router
subnet 10.0.0.0 netmask 255.255.255.0 {{
    range 10.0.0.100 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
    option domain-name "server.local";
    default-lease-time 3600;
    max-lease-time 7200;
}}
"""
        
        dhcp_default_config = f"""# Interface für DHCP-Server (Server-Netzwerk)
INTERFACESv4="{lan_iface}"
INTERFACESv6=""
"""
        
        try:
            # DHCP-Konfiguration schreiben
            with open('/etc/dhcp/dhcpd.conf', 'w') as f:
                f.write(dhcp_config)
            
            # Interface-Konfiguration schreiben
            with open('/etc/default/isc-dhcp-server', 'w') as f:
                f.write(dhcp_default_config)
            
            print(f"✅ DHCP-Server konfiguriert für Interface: {lan_iface}")
            
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
        """Monitoring-Schleife mit VPS Key Updates - STABILISIERT"""
        vps_key_check_counter = 0
        consecutive_errors = 0
        max_consecutive_errors = 3
        
        while self.running:
            try:
                # Timeout für alle Operationen setzen
                start_time = time.time()
                
                # Tunnel-Status prüfen mit Timeout
                try:
                    status = self.gateway.get_tunnel_status()
                except Exception as e:
                    print(f"⚠️ Tunnel-Status Fehler: {e}")
                    status = {'status': 'unknown'}
                
                # Bei Verbindungsabbruch automatisch reconnecten (mit Limit)
                if status['status'] == 'disconnected' and self.gateway.is_connected:
                    print("🔄 Tunnel-Verbindung verloren - versuche Reconnect...")
                    try:
                        self.gateway.stop_tunnel()
                        time.sleep(5)
                        self.gateway.start_tunnel()
                    except Exception as e:
                        print(f"⚠️ Reconnect fehlgeschlagen: {e}")
                
                # VPS Public Key alle 10 Minuten prüfen (10 * 60 Sekunden)
                vps_key_check_counter += 1
                if vps_key_check_counter >= 10 and self.gateway.vps_api_url:
                    print("🔄 Regelmäßige VPS Public Key Prüfung...")
                    try:
                        # Timeout für VPS-Verbindung
                        if self.gateway.update_vps_public_key():
                            # Tunnel neu starten wenn sich Key geändert hat
                            if self.gateway.is_connected:
                                print("🔄 VPS Key geändert - Tunnel wird neu gestartet...")
                                self.gateway.stop_tunnel()
                                time.sleep(2)
                                self.gateway.start_tunnel()
                    except Exception as e:
                        print(f"⚠️ VPS Key Update fehlgeschlagen: {e}")
                    vps_key_check_counter = 0
                
                # Logs schreiben (mit Exception-Handling)
                try:
                    os.makedirs('/var/log/wireguard-gateway', exist_ok=True)
                    with open('/var/log/wireguard-gateway/monitor.log', 'a') as f:
                        f.write(f"{datetime.now().isoformat()} - Status: {status['status']}\n")
                except Exception as e:
                    print(f"⚠️ Log-Schreibfehler: {e}")
                
                # Reset error counter on success
                consecutive_errors = 0
                
                # 60 Sekunden warten (reduziert CPU-Last auf Pi)
                time.sleep(60)
                
            except KeyboardInterrupt:
                print("\n⚠️ Monitoring wird beendet...")
                self.running = False
                break
            except Exception as e:
                consecutive_errors += 1
                print(f"❌ Monitoring-Fehler ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                # Stoppe bei zu vielen aufeinanderfolgenden Fehlern
                if consecutive_errors >= max_consecutive_errors:
                    print("❌ Zu viele Monitoring-Fehler - Stoppe Überwachung")
                    self.running = False
                    break
                
                # Exponential backoff bei Fehlern
                time.sleep(min(120, 30 * consecutive_errors))

if __name__ == "__main__":
    gateway = WireGuardGateway()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "setup":
            if len(sys.argv) < 4:
                print("Usage:")
                print("  python3 gateway_manager.py setup <VPS_IP> <VPS_PUBLIC_KEY>")
                print("")
                print("Beispiel:")
                print("  python3 gateway_manager.py setup 192.168.1.100 abcd1234...")
                print("  python3 gateway_manager.py setup myvps.example.com xyz5678...")
                print("")
                print("💡 VPS IP und Public Key aus dem VPS Dashboard kopieren")
                sys.exit(1)
            
            vps_ip = sys.argv[2]
            vps_public_key = sys.argv[3]
            
            print("🔧 Gateway wird konfiguriert...")
            print(f"📡 VPS IP: {vps_ip}")
            print(f"🔑 VPS Public Key: {vps_public_key[:20]}...")
            
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
        
        elif command == "update-key":
            print("🔄 Aktualisiere VPS Public Key...")
            if gateway.update_vps_public_key():
                print("✅ VPS Public Key erfolgreich aktualisiert")
                
                # Tunnel neu starten wenn er läuft
                status = gateway.get_tunnel_status()
                if status['status'] == 'connected':
                    print("🔄 Tunnel wird mit neuem Key neu gestartet...")
                    if gateway.stop_tunnel():
                        time.sleep(2)
                        if gateway.start_tunnel():
                            print("✅ Tunnel erfolgreich mit neuem Key neu gestartet")
                        else:
                            print("❌ Fehler beim Neustart des Tunnels")
                    else:
                        print("❌ Fehler beim Stoppen des Tunnels")
            else:
                print("❌ Fehler beim Aktualisieren des VPS Public Key")
                sys.exit(1)
        
        elif command == "monitor":
            print("🔍 Starte Gateway-Monitoring...")
            
            # Integriertes System-Monitoring starten
            if MONITORING_AVAILABLE:
                if start_gateway_monitoring(gateway.vps_api_url):
                    print("✅ System-Monitoring gestartet - sendet Metriken an VPS")
                else:
                    print("⚠️ System-Monitoring konnte nicht gestartet werden")
            
            # WireGuard-Monitoring
            monitor = GatewayMonitor(gateway)
            monitor.start_monitoring()
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Monitoring gestoppt")
                monitor.stop_monitoring()
                
                # System-Monitoring stoppen
                if MONITORING_AVAILABLE:
                    from system_monitor import stop_gateway_monitoring
                    stop_gateway_monitoring()
                    print("✅ System-Monitoring gestoppt")
        
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
        print("  update-key                      - VPS Public Key aktualisieren")
        print("  monitor                         - Monitoring starten")
        print("")
        print("Beispiel:")
        print("  python3 gateway_manager.py setup 192.168.1.100 abc123...")