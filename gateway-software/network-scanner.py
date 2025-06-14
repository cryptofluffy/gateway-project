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
import os
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
        # Versuche verschiedene WireGuard config Pfade
        config_paths = ['/etc/wireguard/gateway.conf', '/etc/wireguard/wg0.conf']
        
        for config_path in config_paths:
            try:
                with open(config_path, 'r') as f:
                    content = f.read()
                    # Suche nach Endpoint
                    match = re.search(r'Endpoint\s*=\s*([^:]+)', content)
                    if match:
                        vps_ip = match.group(1)
                        return f"http://{vps_ip}:8080"
            except:
                continue
        
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
        """Ermittle lokale Netzwerk-Bereiche - NUR Server-Netzwerk scannen"""
        networks = []
        
        # Nur das Server-Netzwerk scannen (Port B / eth1)
        # NICHT das Heimnetz (Port A / eth0) - das ist die FritzBox
        server_networks = ['10.0.0.0/24']
        
        try:
            # ip route show für lokale Netzwerke
            result = subprocess.run(['ip', 'route', 'show'], 
                                  capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    # Suche nach Server-Netzwerk (10.0.0.0/24) über eth1
                    if 'dev eth1' in line and 'scope link' in line:
                        parts = line.split()
                        if len(parts) > 0 and '/' in parts[0]:
                            network = parts[0]
                            # Nur Server-Netzwerke (10.x.x.x)
                            if network.startswith('10.'):
                                networks.append(network)
                                logger.info(f"Found server network: {network}")
        except Exception as e:
            logger.error(f"Error getting local networks: {e}")
        
        # Fallback: Nur Server-Netzwerk
        if not networks:
            networks = server_networks
            logger.info(f"Using fallback server networks: {networks}")
        
        # Explizit KEINE Heimnetz-Bereiche (192.168.x.x)
        # Das Gateway scannt NUR das Server-Netzwerk (Port B)
        filtered_networks = []
        for network in networks:
            if network.startswith('10.0.0.'):
                filtered_networks.append(network)
        
        return filtered_networks if filtered_networks else server_networks
    
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
        
        # Prüfe ob Scanner-Service installiert ist
        if not self._check_service_installation():
            logger.warning("Network scanner service is not properly installed")
        
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
    
    def _check_service_installation(self) -> bool:
        """Prüfe ob der Network Scanner Service korrekt installiert ist"""
        try:
            # Prüfe ob Service-Dateien existieren
            service_files = [
                '/etc/systemd/system/network-scanner.service',
                '/etc/systemd/system/network-scanner.timer'
            ]
            
            for file_path in service_files:
                if not os.path.exists(file_path):
                    logger.warning(f"Service file missing: {file_path}")
                    return False
            
            # Prüfe Service-Status
            result = subprocess.run(['systemctl', 'is-enabled', 'network-scanner.timer'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Network scanner timer is not enabled")
                return False
            
            result = subprocess.run(['systemctl', 'is-active', 'network-scanner.timer'], 
                                  capture_output=True, text=True)
            if result.returncode != 0:
                logger.warning("Network scanner timer is not active")
                return False
            
            logger.info("Network scanner service is properly installed and running")
            return True
            
        except Exception as e:
            logger.error(f"Error checking service installation: {e}")
            return False

def main():
    scanner = NetworkScanner()
    
    # Einmaligen Scan ausführen
    scanner.run_scan_cycle()

if __name__ == "__main__":
    main()