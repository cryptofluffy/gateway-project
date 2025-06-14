#!/usr/bin/env python3
"""
Gateway Netzwerk-Problem Löser
Behebt das Problem mit falscher Geräte-Erkennung
"""

import subprocess
import json
import time
import os

def diagnose_problem():
    """Analysiert das Netzwerk-Problem"""
    print("🔍 Gateway Netzwerk-Diagnose")
    print("=" * 40)
    
    # 1. Aktuelle Interface-Konfiguration
    print("\n📡 Aktuelle Interface-Konfiguration:")
    try:
        result = subprocess.run(['ip', 'addr', 'show'], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if ('inet ' in line and ('192.168.' in line or '10.' in line)) or 'wg0' in line:
                print(f"  {line.strip()}")
    except:
        print("  Fehler beim Abrufen der Interface-Info")
    
    # 2. Routing-Tabelle
    print("\n🗺️ Routing-Tabelle:")
    try:
        result = subprocess.run(['ip', 'route', 'show'], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if line.strip():
                print(f"  {line}")
    except:
        print("  Fehler beim Abrufen der Routing-Info")
    
    # 3. DHCP-Server Status
    print("\n📡 DHCP-Server Status:")
    try:
        result = subprocess.run(['systemctl', 'status', 'isc-dhcp-server'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("  ✅ DHCP-Server läuft")
        else:
            print("  ❌ DHCP-Server läuft NICHT")
            print(f"  Fehler: {result.stderr}")
    except:
        print("  ❌ DHCP-Server nicht installiert")
    
    # 4. WireGuard Status
    print("\n🔒 WireGuard Status:")
    try:
        result = subprocess.run(['wg', 'show'], capture_output=True, text=True, check=True)
        print(f"  {result.stdout}")
    except:
        print("  ❌ WireGuard nicht aktiv oder nicht installiert")
    
    # 5. Problem-Analyse
    print("\n🚨 Problem-Analyse:")
    print("Das Gateway zeigt 192.168.178.x Geräte (Fritz.Box-Netzwerk)")
    print("Aber es sollte ein eigenes 192.168.100.x Netzwerk haben")
    print("")
    print("Mögliche Ursachen:")
    print("1. ❌ LAN-Interface nicht konfiguriert")
    print("2. ❌ DHCP-Server läuft nicht")
    print("3. ❌ Gateway Manager zeigt falsches Netzwerk")
    print("4. ❌ Keine physische LAN-Verbindung")

def fix_gateway_network():
    """Behebt das Gateway-Netzwerk"""
    print("\n🔧 Repariere Gateway-Netzwerk")
    print("=" * 40)
    
    # 1. Interfaces ermitteln
    print("\n1. Ermittle verfügbare Interfaces...")
    interfaces = get_available_interfaces()
    
    if len(interfaces) < 2:
        print("❌ Zu wenige Interfaces gefunden!")
        print("   Das Gateway braucht mindestens 2 Interfaces (WAN + LAN)")
        print("   Gefunden:", interfaces)
        return False
    
    # WAN/LAN automatisch zuordnen
    wan_interface = get_wan_interface()
    lan_interface = get_best_lan_interface(interfaces, wan_interface)
    
    print(f"  WAN-Interface: {wan_interface}")
    print(f"  LAN-Interface: {lan_interface}")
    
    # 2. LAN-Interface konfigurieren
    print("\n2. Konfiguriere LAN-Interface...")
    success = configure_lan_interface(lan_interface)
    if not success:
        print("❌ LAN-Interface-Konfiguration fehlgeschlagen")
        return False
    
    # 3. DHCP-Server installieren/konfigurieren
    print("\n3. Konfiguriere DHCP-Server...")
    success = configure_dhcp_server(lan_interface)
    if not success:
        print("❌ DHCP-Server-Konfiguration fehlgeschlagen")
        return False
    
    # 4. NAT/Forwarding konfigurieren
    print("\n4. Konfiguriere NAT und Forwarding...")
    success = configure_nat_forwarding(wan_interface, lan_interface)
    if not success:
        print("❌ NAT-Konfiguration fehlgeschlagen")
        return False
    
    # 5. Gateway Manager Config anpassen
    print("\n5. Aktualisiere Gateway Manager...")
    update_gateway_manager_config(wan_interface, lan_interface)
    
    print("\n✅ Gateway-Netzwerk erfolgreich konfiguriert!")
    print("\nNächste Schritte:")
    print("1. Geräte mit dem LAN-Port des Gateways verbinden")
    print("2. Gateway Manager neu starten: sudo systemctl restart gateway-manager")
    print("3. Nach 1-2 Minuten sollten Geräte im 192.168.100.x Bereich sichtbar sein")
    
    return True

def get_available_interfaces():
    """Ermittelt verfügbare Ethernet-Interfaces"""
    interfaces = []
    try:
        result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if ':' in line and ('eth' in line or 'enp' in line or 'ens' in line):
                parts = line.split(':')
                if len(parts) >= 2:
                    iface_name = parts[1].strip().split('@')[0]
                    if 'docker' not in iface_name and 'br-' not in iface_name:
                        interfaces.append(iface_name)
    except:
        # Fallback
        interfaces = ['eth0', 'eth1']
    
    return interfaces

def get_wan_interface():
    """Ermittelt WAN-Interface (mit Default-Route)"""
    try:
        result = subprocess.run(['ip', 'route', 'show', 'default'], 
                              capture_output=True, text=True, check=True)
        for line in result.stdout.split('\n'):
            if 'dev' in line:
                parts = line.split()
                dev_index = parts.index('dev')
                if dev_index + 1 < len(parts):
                    return parts[dev_index + 1]
    except:
        pass
    
    return 'eth0'  # Fallback

def get_best_lan_interface(interfaces, wan_interface):
    """Wählt bestes LAN-Interface"""
    for iface in interfaces:
        if iface != wan_interface:
            return iface
    
    return 'eth1'  # Fallback

def configure_lan_interface(lan_interface):
    """Konfiguriert LAN-Interface mit statischer IP"""
    lan_ip = "192.168.100.1"
    
    try:
        print(f"  Konfiguriere {lan_interface} mit {lan_ip}...")
        
        # Interface zurücksetzen
        subprocess.run(['ip', 'addr', 'flush', 'dev', lan_interface], 
                      capture_output=True, check=True)
        
        # Statische IP setzen
        subprocess.run(['ip', 'addr', 'add', f'{lan_ip}/24', 'dev', lan_interface], 
                      capture_output=True, check=True)
        
        # Interface aktivieren
        subprocess.run(['ip', 'link', 'set', lan_interface, 'up'], 
                      capture_output=True, check=True)
        
        print(f"  ✅ {lan_interface} konfiguriert: {lan_ip}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Fehler: {e}")
        return False

def configure_dhcp_server(lan_interface):
    """Installiert und konfiguriert DHCP-Server"""
    try:
        # DHCP-Server installieren falls nicht vorhanden
        print("  Installiere DHCP-Server...")
        subprocess.run(['apt', 'update'], capture_output=True)
        subprocess.run(['apt', 'install', '-y', 'isc-dhcp-server'], 
                      capture_output=True, check=True)
        
        # DHCP-Konfiguration erstellen
        dhcp_config = f"""# DHCP-Server Konfiguration für Gateway LAN
default-lease-time 86400;
max-lease-time 172800;
authoritative;

# DNS-Server (Gateway + Google)
option domain-name-servers 192.168.100.1, 8.8.8.8, 8.8.4.4;
option domain-name "gateway.local";

# LAN-Subnet
subnet 192.168.100.0 netmask 255.255.255.0 {{
    range 192.168.100.50 192.168.100.200;
    option routers 192.168.100.1;
    option broadcast-address 192.168.100.255;
}}

# Logging
log-facility local7;
"""
        
        with open('/etc/dhcp/dhcpd.conf', 'w') as f:
            f.write(dhcp_config)
        
        # Interface für DHCP festlegen
        dhcp_default = f"""# DHCP-Server Interface Konfiguration
DHCPDv4_CONF=/etc/dhcp/dhcpd.conf
DHCPDv4_PID=/var/run/dhcpd.pid
OPTIONS=""
INTERFACESv4="{lan_interface}"
INTERFACESv6=""
"""
        
        with open('/etc/default/isc-dhcp-server', 'w') as f:
            f.write(dhcp_default)
        
        # DHCP-Server starten
        subprocess.run(['systemctl', 'stop', 'isc-dhcp-server'], capture_output=True)
        time.sleep(2)
        subprocess.run(['systemctl', 'start', 'isc-dhcp-server'], capture_output=True, check=True)
        subprocess.run(['systemctl', 'enable', 'isc-dhcp-server'], capture_output=True)
        
        print("  ✅ DHCP-Server konfiguriert und gestartet")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ DHCP-Fehler: {e}")
        return False

def configure_nat_forwarding(wan_interface, lan_interface):
    """Konfiguriert NAT und IP-Forwarding"""
    try:
        print("  Aktiviere IP-Forwarding...")
        
        # IP-Forwarding aktivieren
        with open('/etc/sysctl.d/99-gateway-forwarding.conf', 'w') as f:
            f.write('net.ipv4.ip_forward=1\n')
        
        subprocess.run(['sysctl', '-p', '/etc/sysctl.d/99-gateway-forwarding.conf'], 
                      capture_output=True, check=True)
        
        print("  Konfiguriere NAT-Regeln...")
        
        # Alte Regeln löschen
        subprocess.run(['iptables', '-t', 'nat', '-F'], capture_output=True)
        subprocess.run(['iptables', '-F', 'FORWARD'], capture_output=True)
        
        # NAT für Internet-Zugang
        subprocess.run(['iptables', '-t', 'nat', '-A', 'POSTROUTING', 
                       '-o', wan_interface, '-j', 'MASQUERADE'], 
                      capture_output=True, check=True)
        
        # Forwarding-Regeln
        subprocess.run(['iptables', '-A', 'FORWARD', '-i', lan_interface, 
                       '-o', wan_interface, '-j', 'ACCEPT'], 
                      capture_output=True, check=True)
        
        subprocess.run(['iptables', '-A', 'FORWARD', '-i', wan_interface, 
                       '-o', lan_interface, '-m', 'state', 
                       '--state', 'RELATED,ESTABLISHED', '-j', 'ACCEPT'], 
                      capture_output=True, check=True)
        
        # Regeln permanent machen
        if os.path.exists('/usr/sbin/iptables-save'):
            subprocess.run(['apt', 'install', '-y', 'iptables-persistent'], 
                          capture_output=True)
            with open('/etc/iptables/rules.v4', 'w') as f:
                result = subprocess.run(['iptables-save'], capture_output=True, text=True)
                f.write(result.stdout)
        
        print("  ✅ NAT und Forwarding konfiguriert")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"  ❌ NAT-Fehler: {e}")
        return False

def update_gateway_manager_config(wan_interface, lan_interface):
    """Aktualisiert Gateway Manager Konfiguration"""
    try:
        config_file = '/etc/gateway/config.json'
        
        # Verzeichnis erstellen
        os.makedirs('/etc/gateway', exist_ok=True)
        
        # Konfiguration erstellen/aktualisieren
        config = {
            "wan_interface": wan_interface,
            "lan_interface": lan_interface,
            "lan_ip": "192.168.100.1",
            "lan_network": "192.168.100.0/24",
            "dhcp_range_start": "192.168.100.50",
            "dhcp_range_end": "192.168.100.200",
            "dns_servers": ["8.8.8.8", "8.8.4.4"],
            "domain_name": "gateway.local"
        }
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"  ✅ Gateway-Konfiguration gespeichert: {config_file}")
        
    except Exception as e:
        print(f"  ⚠️ Warnung - Gateway-Config-Fehler: {e}")

def main():
    """Hauptfunktion"""
    print("🔧 Gateway Netzwerk-Reparatur")
    print("Behebt das Problem mit falscher Geräte-Anzeige")
    print("")
    
    # Prüfe Root-Rechte
    if os.geteuid() != 0:
        print("❌ Dieses Script muss als root ausgeführt werden!")
        print("Ausführen mit: sudo python3 fix_gateway_network.py")
        return
    
    # Diagnose durchführen
    diagnose_problem()
    
    print("\n" + "=" * 50)
    choice = input("\nSoll das Gateway-Netzwerk repariert werden? (y/N): ")
    
    if choice.lower() in ['y', 'yes', 'j', 'ja']:
        success = fix_gateway_network()
        
        if success:
            print("\n🎉 Reparatur abgeschlossen!")
            print("\nTeste jetzt:")
            print("1. Verbinde TrueNAS mit LAN-Port des Gateways")
            print("2. Warte 2-3 Minuten")
            print("3. TrueNAS sollte IP 192.168.100.x erhalten")
            print("4. Gateway Dashboard sollte TrueNAS anzeigen")
        else:
            print("\n❌ Reparatur fehlgeschlagen!")
            print("Bitte Logs prüfen und manuell konfigurieren")
    else:
        print("\nAbgebrochen - keine Änderungen vorgenommen")

if __name__ == "__main__":
    main()