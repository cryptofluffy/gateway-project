#!/usr/bin/env python3
"""
Umfassende System-Diagnose für WireGuard Gateway
Erkennt und behebt häufige Probleme automatisch
"""

import os
import sys
import subprocess
import json
import time
import psutil
import socket
from datetime import datetime
from pathlib import Path

class SystemChecker:
    def __init__(self):
        self.issues = []
        self.fixes_applied = []
        self.system_type = self.detect_system_type()
        
    def detect_system_type(self):
        """Erkenne ob VPS oder Gateway"""
        if os.path.exists('/opt/siteconnector-vps') or os.path.exists('/opt/wireguard-vps'):
            return 'vps'
        elif os.path.exists('/usr/local/bin/gateway_manager.py'):
            return 'gateway'
        else:
            return 'unknown'
    
    def log_issue(self, severity, component, issue, solution=None):
        """Protokolliere ein Problem"""
        self.issues.append({
            'severity': severity,
            'component': component, 
            'issue': issue,
            'solution': solution,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_fix(self, description):
        """Protokolliere angewendete Lösung"""
        self.fixes_applied.append({
            'description': description,
            'timestamp': datetime.now().isoformat()
        })
    
    def check_system_resources(self):
        """Prüfe System-Ressourcen"""
        print("🔍 System-Ressourcen prüfen...")
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            if cpu_percent > 90:
                self.log_issue('warning', 'CPU', f'Hohe CPU-Last: {cpu_percent}%')
            
            # Memory
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                self.log_issue('critical', 'Memory', f'Hohe Speicherlast: {memory.percent}%')
            elif memory.percent > 80:
                self.log_issue('warning', 'Memory', f'Speicherlast: {memory.percent}%')
            
            # Disk
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                self.log_issue('critical', 'Disk', f'Festplatte fast voll: {disk.percent}%')
            elif disk.percent > 85:
                self.log_issue('warning', 'Disk', f'Festplatte wird voll: {disk.percent}%')
            
            # Load Average
            if hasattr(psutil, 'getloadavg'):
                load = psutil.getloadavg()[0]
                cpu_count = psutil.cpu_count()
                if load > cpu_count * 1.5:
                    self.log_issue('warning', 'Load', f'Hohe Systemlast: {load:.2f} (CPUs: {cpu_count})')
            
            print(f"  ✓ CPU: {cpu_percent:.1f}%")
            print(f"  ✓ Memory: {memory.percent:.1f}% ({memory.available // 1024 // 1024}MB verfügbar)")
            print(f"  ✓ Disk: {disk.percent:.1f}% ({disk.free // 1024 // 1024 // 1024}GB frei)")
            
        except Exception as e:
            self.log_issue('error', 'System', f'Ressourcenprüfung fehlgeschlagen: {e}')
    
    def check_processes(self):
        """Prüfe laufende Prozesse"""
        print("🔍 Prozesse prüfen...")
        
        if self.system_type == 'vps':
            self.check_vps_processes()
        elif self.system_type == 'gateway':
            self.check_gateway_processes()
    
    def check_vps_processes(self):
        """Prüfe VPS-spezifische Prozesse"""
        required_processes = {
            'python.*app\.py': 'VPS Server',
            'wg-quick': 'WireGuard Interface'
        }
        
        for process_pattern, description in required_processes.items():
            found = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if process_pattern in cmdline or process_pattern in proc.info['name']:
                        found = True
                        print(f"  ✓ {description}: Läuft (PID: {proc.info['pid']})")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found:
                self.log_issue('critical', 'Process', f'{description} läuft nicht')
                print(f"  ✗ {description}: Nicht gefunden")
    
    def check_gateway_processes(self):
        """Prüfe Gateway-spezifische Prozesse"""
        required_processes = {
            'gateway_manager\.py': 'Gateway Manager',
            'system_monitor\.py': 'System Monitor',
            'dhcpd': 'DHCP Server'
        }
        
        for process_pattern, description in required_processes.items():
            found = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if process_pattern in cmdline or process_pattern in proc.info['name']:
                        found = True
                        print(f"  ✓ {description}: Läuft (PID: {proc.info['pid']})")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if not found:
                self.log_issue('warning', 'Process', f'{description} läuft nicht')
                print(f"  ✗ {description}: Nicht gefunden")
    
    def check_network_connectivity(self):
        """Prüfe Netzwerk-Konnektivität"""
        print("🔍 Netzwerk-Konnektivität prüfen...")
        
        # Internet-Verbindung
        try:
            response = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                    capture_output=True, timeout=5)
            if response.returncode == 0:
                print("  ✓ Internet-Verbindung: OK")
            else:
                self.log_issue('critical', 'Network', 'Keine Internet-Verbindung')
                print("  ✗ Internet-Verbindung: Fehler")
        except Exception as e:
            self.log_issue('error', 'Network', f'Internet-Test fehlgeschlagen: {e}')
        
        # DNS-Auflösung
        try:
            socket.gethostbyname('google.com')
            print("  ✓ DNS-Auflösung: OK")
        except Exception as e:
            self.log_issue('warning', 'Network', f'DNS-Probleme: {e}')
            print("  ✗ DNS-Auflösung: Fehler")
    
    def check_wireguard_status(self):
        """Prüfe WireGuard-Status"""
        print("🔍 WireGuard-Status prüfen...")
        
        try:
            # WireGuard Interface prüfen
            result = subprocess.run(['wg', 'show'], capture_output=True, text=True)
            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    print("  ✓ WireGuard Interface: Aktiv")
                    # Peer-Anzahl zählen
                    peer_count = output.count('peer:')
                    print(f"  ✓ Verbundene Peers: {peer_count}")
                else:
                    self.log_issue('warning', 'WireGuard', 'Kein WireGuard Interface aktiv')
                    print("  ✗ WireGuard Interface: Inaktiv")
            else:
                self.log_issue('error', 'WireGuard', 'WireGuard-Befehle nicht verfügbar')
                print("  ✗ WireGuard: Nicht installiert")
        except Exception as e:
            self.log_issue('error', 'WireGuard', f'WireGuard-Prüfung fehlgeschlagen: {e}')
    
    def check_configuration_files(self):
        """Prüfe Konfigurationsdateien"""
        print("🔍 Konfigurationsdateien prüfen...")
        
        if self.system_type == 'vps':
            config_files = {
                '/etc/wireguard/wg0.conf': 'WireGuard VPS Konfiguration',
                '/etc/wireguard/server_private.key': 'VPS Private Key',
                '/opt/siteconnector-vps/config.py': 'VPS Server Konfiguration'
            }
        elif self.system_type == 'gateway':
            config_files = {
                '/etc/wireguard/gateway.conf': 'Gateway WireGuard Konfiguration',
                '/etc/wireguard-gateway/config.json': 'Gateway Konfiguration',
                '/etc/dhcp/dhcpd.conf': 'DHCP Server Konfiguration'
            }
        else:
            config_files = {}
        
        for config_file, description in config_files.items():
            if os.path.exists(config_file):
                # Prüfe Berechtigungen
                stat = os.stat(config_file)
                if 'private.key' in config_file and (stat.st_mode & 0o077):
                    self.log_issue('security', 'Config', f'{description}: Unsichere Berechtigungen')
                    print(f"  ⚠ {description}: Unsichere Berechtigungen")
                else:
                    print(f"  ✓ {description}: Vorhanden")
            else:
                self.log_issue('warning', 'Config', f'{description}: Nicht gefunden')
                print(f"  ✗ {description}: Fehlt")
    
    def check_systemd_services(self):
        """Prüfe systemd Services"""
        print("🔍 systemd Services prüfen...")
        
        if self.system_type == 'vps':
            services = ['siteconnector-vps', 'wg-quick@wg0']
        elif self.system_type == 'gateway':
            services = ['siteconnector-gateway', 'siteconnector-monitoring', 'isc-dhcp-server']
        else:
            services = []
        
        for service in services:
            try:
                result = subprocess.run(['systemctl', 'is-active', service], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    print(f"  ✓ {service}: Aktiv")
                else:
                    self.log_issue('warning', 'Service', f'{service}: Inaktiv')
                    print(f"  ✗ {service}: Inaktiv")
            except Exception as e:
                self.log_issue('error', 'Service', f'{service}: Prüfung fehlgeschlagen - {e}')
    
    def apply_automatic_fixes(self):
        """Wende automatische Korrekturen an"""
        if not self.issues:
            return
        
        print("\n🔧 Automatische Korrekturen anwenden...")
        
        for issue in self.issues:
            if issue['severity'] == 'critical':
                continue  # Kritische Probleme nicht automatisch beheben
            
            # Beispiel-Korrekturen
            if 'WireGuard Interface: Inaktiv' in issue['issue']:
                try:
                    subprocess.run(['wg-quick', 'up', 'wg0'], check=True)
                    self.log_fix('WireGuard Interface gestartet')
                    print("  ✓ WireGuard Interface gestartet")
                except Exception as e:
                    print(f"  ✗ WireGuard Start fehlgeschlagen: {e}")
            
            elif 'DHCP Server' in issue['issue'] and 'Inaktiv' in issue['issue']:
                try:
                    subprocess.run(['systemctl', 'start', 'isc-dhcp-server'], check=True)
                    self.log_fix('DHCP Server gestartet')
                    print("  ✓ DHCP Server gestartet")
                except Exception as e:
                    print(f"  ✗ DHCP Start fehlgeschlagen: {e}")
    
    def generate_report(self):
        """Erstelle Diagnose-Bericht"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'system_type': self.system_type,
            'issues': self.issues,
            'fixes_applied': self.fixes_applied,
            'system_info': {
                'hostname': socket.gethostname(),
                'platform': sys.platform,
                'python_version': sys.version
            }
        }
        
        # Bericht speichern
        report_file = f'/tmp/system_check_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        return report_file, report
    
    def print_summary(self):
        """Drucke Zusammenfassung"""
        print("\n" + "="*60)
        print("📊 DIAGNOSE-ZUSAMMENFASSUNG")
        print("="*60)
        
        if not self.issues:
            print("✅ Keine Probleme gefunden - System läuft optimal!")
            return
        
        # Probleme nach Schweregrad gruppieren
        critical = [i for i in self.issues if i['severity'] == 'critical']
        warnings = [i for i in self.issues if i['severity'] == 'warning']
        errors = [i for i in self.issues if i['severity'] == 'error']
        
        if critical:
            print(f"🚨 KRITISCHE PROBLEME ({len(critical)}):")
            for issue in critical:
                print(f"   • {issue['component']}: {issue['issue']}")
        
        if errors:
            print(f"❌ FEHLER ({len(errors)}):")
            for issue in errors:
                print(f"   • {issue['component']}: {issue['issue']}")
        
        if warnings:
            print(f"⚠️ WARNUNGEN ({len(warnings)}):")
            for issue in warnings:
                print(f"   • {issue['component']}: {issue['issue']}")
        
        if self.fixes_applied:
            print(f"\n🔧 ANGEWENDETE KORREKTUREN ({len(self.fixes_applied)}):")
            for fix in self.fixes_applied:
                print(f"   • {fix['description']}")
        
        print("\n💡 EMPFOHLENE MASSNAHMEN:")
        if critical:
            print("   1. Kritische Probleme sofort beheben")
            print("   2. System-Update ausführen: sudo siteconnector-update")
            print("   3. Bei anhaltenden Problemen: System neu starten")
        elif errors or warnings:
            print("   1. System-Update ausführen: sudo siteconnector-update")
            print("   2. Services neu starten: sudo systemctl restart siteconnector-*")
        
        print(f"\n📋 Vollständiger Bericht: {self.generate_report()[0]}")

def main():
    print("🔍 WireGuard Gateway System-Diagnose")
    print("="*50)
    
    if os.geteuid() != 0:
        print("⚠️ Für vollständige Diagnose als root ausführen: sudo python3 system_check.py")
        print()
    
    checker = SystemChecker()
    
    # Alle Checks ausführen
    checker.check_system_resources()
    checker.check_processes()
    checker.check_network_connectivity()
    checker.check_wireguard_status()
    checker.check_configuration_files()
    checker.check_systemd_services()
    
    # Automatische Korrekturen (nur bei Berechtigung)
    if os.geteuid() == 0:
        checker.apply_automatic_fixes()
    
    # Zusammenfassung
    checker.print_summary()

if __name__ == '__main__':
    main()