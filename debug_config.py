#!/usr/bin/env python3
"""
Debug Script - Interface Konfiguration prüfen
"""

import sys
import os
import json

sys.path.append('/usr/local/bin')

print("🔍 Debug: Interface-Konfiguration")
print("=" * 40)

# Prüfe verschiedene Konfigurationspfade
config_paths = [
    '/etc/wireguard-gateway/config.json',
    '/etc/siteconnector/config.json',
    '/etc/gateway/config.json'
]

for path in config_paths:
    print(f"\n📁 Prüfe: {path}")
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                config = json.load(f)
                print(f"✅ Gefunden!")
                print(f"   network_config: {config.get('network_config', 'NICHT GEFUNDEN')}")
                if 'network_config' in config:
                    nc = config['network_config']
                    print(f"   wan_interface: {nc.get('wan_interface', 'NICHT GESETZT')}")
                    print(f"   lan_interface: {nc.get('lan_interface', 'NICHT GESETZT')}")
        except Exception as e:
            print(f"❌ Fehler beim Lesen: {e}")
    else:
        print("❌ Datei nicht gefunden")

# Teste Gateway Manager direkt
print(f"\n🔧 Teste Gateway Manager direkt:")
try:
    from gateway_manager import WireGuardGateway
    gw = WireGuardGateway()
    print(f"   wan_interface: {gw.wan_interface}")
    print(f"   lan_interface: {gw.lan_interface}")
    
    wan, lan = gw.get_actual_interfaces()
    print(f"   get_actual_interfaces(): WAN={wan}, LAN={lan}")
    
except Exception as e:
    print(f"❌ Gateway Manager Fehler: {e}")

print("\n🔍 Das Dashboard zeigt:")
print("   WAN: wlan0 (192.168.178.45)")
print("   LAN: eth0")
print("\nVergleiche mit den geladenen Werten oben!")