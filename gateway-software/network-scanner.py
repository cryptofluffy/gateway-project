#!/usr/bin/env python3
"""
Gateway-PC Network Scanner
Scannt lokales Netzwerk und meldet Geräte an VPS
"""

import subprocess
import json
import requests
import time
import socket
import logging
import re
from typing import List, Dict, Optional

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NetworkScanner:
    def __init__(self, vps_url: str = None, gateway_id: str = None):
        self.vps_url = vps_url or self._get_vps_url()
        self.gateway_id = gateway_id or self._get_gateway_id()
        
    def _get_vps_url(self) -> str:
        """VPS URL aus Gateway-Konfiguration lesen"""
        try:
            # Versuche VPS URL aus WireGuard config zu lesen
            with open('/etc/wireguard/wg0.conf', 'r') as f:
                content = f.read()
                # Suche nach Endpoint
                match = re.search(r'Endpoint\s*=\s*([^:]+)', content)
                if match:
                    vps_ip = match.group(1)
                    return f"http://{vps_ip}:8080"
        except:
            pass
        
        # Fallback
        return "http://127.0.0.1:8080"  # Für lokalen Test
    
    def _get_gateway_id(self) -> str:
        """Gateway ID ermitteln"""
        try:
            # Verwende Hostname oder MAC als ID
            hostname = socket.gethostname()
            return f"gateway-{hostname}"
        except:
            return "gateway-unknown"
    
    def scan_network(self) -> List[Dict]:
        """Scanne lokales Netzwerk nach Geräten"""
        devices = []
        
        # Ermittle lokale Netzwerk-Bereiche
        networks = self._get_local_networks()
        
        for network in networks:
            logger.info(f"Scanning network: {network}")
            network_devices = self._scan_network_range(network)
            devices.extend(network_devices)
        
        return devices
    
    def _get_local_networks(self) -> List[str]:
        """Ermittle lokale Netzwerk-Bereiche"""
        networks = []
        
        try:
            # ip route show für lokale Netzwerke
            result = subprocess.run(['ip', 'route', 'show'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # Suche nach lokalen Netzwerken
                    if 'dev' in line and 'scope link' in line:
                        parts = line.split()
                        if len(parts) > 0 and '/' in parts[0]:
                            network = parts[0]
                            # Nur typische private Netzwerke
                            if any(network.startswith(prefix) for prefix in 
                                  ['192.168.', '10.', '172.16.', '172.17.', '172.18.', '172.19.', '172.20.']):
                                networks.append(network)
        except Exception as e:
            logger.error(f"Error getting local networks: {e}")
        
        # Fallback zu häufigen Netzwerken
        if not networks:
            networks = ['192.168.1.0/24', '192.168.178.0/24', '10.0.0.0/24']
        
        return networks
    
    def _scan_network_range(self, network: str) -> List[Dict]:
        """Scanne einen Netzwerk-Bereich"""
        devices = []
        
        try:
            # ARP-Tabelle lesen (schneller)
            devices.extend(self._get_arp_devices())
            
            # Zusätzlich: nmap scan für aktive Geräte (falls verfügbar)
            if self._has_nmap():
                nmap_devices = self._nmap_scan(network)
                # Merge mit ARP-Daten
                for nmap_device in nmap_devices:
                    if not any(d['ip'] == nmap_device['ip'] for d in devices):
                        devices.append(nmap_device)
            
        except Exception as e:
            logger.error(f"Error scanning network {network}: {e}")
        
        return devices
    
    def _get_arp_devices(self) -> List[Dict]:
        """Lese ARP-Tabelle für verbundene Geräte"""
        devices = []
        
        try:
            # ip neigh show für ARP-Tabelle
            result = subprocess.run(['ip', 'neigh', 'show'], 
                                  capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        parts = line.split()
                        if len(parts) >= 4:
                            ip = parts[0]
                            mac = None
                            status = 'unknown'
                            
                            # Parse ARP entry
                            for i, part in enumerate(parts):
                                if ':' in part and len(part) == 17:  # MAC address
                                    mac = part
                                elif part in ['REACHABLE', 'STALE', 'DELAY']:
                                    status = 'online'
                            
                            if self._is_valid_local_ip(ip):
                                hostname = self._resolve_hostname(ip)
                                devices.append({
                                    'ip': ip,
                                    'mac': mac,
                                    'hostname': hostname,
                                    'name': hostname or f'Gerät-{ip.split(".")[-1]}',
                                    'status': status,
                                    'method': 'arp'
                                })
        
        except Exception as e:
            logger.error(f"Error reading ARP table: {e}")
        
        return devices
    
    def _has_nmap(self) -> bool:
        """Prüfe ob nmap verfügbar ist"""
        try:
            subprocess.run(['which', 'nmap'], 
                         capture_output=True, timeout=2)
            return True
        except:
            return False
    
    def _nmap_scan(self, network: str) -> List[Dict]:
        """Nmap scan für Netzwerk"""
        devices = []
        
        try:
            # Schneller nmap ping scan
            result = subprocess.run([
                'nmap', '-sn', network
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_ip = None
                
                for line in lines:
                    # Parse nmap output
                    if 'Nmap scan report for' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            ip = parts[-1].strip('()')
                            hostname = parts[4] if len(parts) > 5 else None
                            if self._is_valid_local_ip(ip):
                                devices.append({
                                    'ip': ip,
                                    'hostname': hostname,
                                    'name': hostname or f'Gerät-{ip.split(".")[-1]}',
                                    'status': 'online',
                                    'method': 'nmap'
                                })
        
        except Exception as e:
            logger.error(f"Error in nmap scan: {e}")
        
        return devices
    
    def _is_valid_local_ip(self, ip: str) -> bool:
        """Prüfe ob IP eine gültige lokale IP ist"""
        try:
            parts = ip.split('.')
            if len(parts) != 4:
                return False
            
            # Private IP ranges
            if ip.startswith('192.168.'):
                return True
            elif ip.startswith('10.'):
                return True
            elif ip.startswith('172.'):
                second = int(parts[1])
                return 16 <= second <= 31
            
            return False
        except:
            return False
    
    def _resolve_hostname(self, ip: str) -> Optional[str]:
        """Versuche Hostname für IP zu ermitteln"""
        try:
            socket.setdefaulttimeout(1)
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname if hostname != ip else None
        except:
            return None
    
    def report_to_vps(self, devices: List[Dict]) -> bool:
        """Melde Geräte an VPS"""
        try:
            url = f"{self.vps_url}/api/gateway-network-devices"
            data = {
                'gateway_id': self.gateway_id,
                'devices': devices,
                'timestamp': time.time()
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Successfully reported {len(devices)} devices to VPS")
                return True
            else:
                logger.error(f"VPS returned status {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error reporting to VPS: {e}")
            return False
    
    def run_scan_cycle(self):
        """Führe einen kompletten Scan-Zyklus aus"""
        logger.info(f"Starting network scan for gateway {self.gateway_id}")
        
        # Scanne Netzwerk
        devices = self.scan_network()
        logger.info(f"Found {len(devices)} devices")
        
        # Melde an VPS
        if devices:
            success = self.report_to_vps(devices)
            if success:
                logger.info("Network scan completed successfully")
            else:
                logger.error("Failed to report devices to VPS")
        else:
            logger.warning("No devices found in network scan")

def main():
    scanner = NetworkScanner()
    
    # Einmaligen Scan ausführen
    scanner.run_scan_cycle()

if __name__ == "__main__":
    main()