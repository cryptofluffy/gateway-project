#!/bin/bash
# Interface Debug Script für Raspberry Pi

echo "🔍 Raspberry Pi Interface-Diagnose"
echo "=================================="

echo ""
echo "📡 Alle verfügbaren Interfaces:"
ip link show | grep -E "^[0-9]+:"

echo ""
echo "🌐 Interfaces mit IP-Adressen:"
ip addr show | grep -E "inet |^[0-9]+:"

echo ""
echo "🗺️ Routing-Tabelle:"
ip route show

echo ""
echo "⚙️ Interface-Namen-Schema:"
for iface in $(ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | tr -d ' '); do
    if [[ $iface =~ ^(eth|enp|ens|end|wlan|wlp) ]]; then
        echo "  - $iface"
    fi
done

echo ""
echo "🔧 Empfohlene Interface-Zuordnung:"
# WAN Interface (mit Default Route)
WAN_IFACE=$(ip route show default | awk '{print $5}' | head -1)
echo "  WAN-Interface (Internet): $WAN_IFACE"

# Alle anderen Ethernet-Interfaces als mögliche LAN-Interfaces
echo "  Mögliche LAN-Interfaces:"
for iface in $(ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | tr -d ' '); do
    if [[ $iface =~ ^(eth|enp|ens|end) ]] && [ "$iface" != "$WAN_IFACE" ] && [ "$iface" != "lo" ]; then
        echo "    - $iface"
    fi
done

echo ""
echo "💡 Für Gateway Manager verwenden:"
echo "WAN_INTERFACE='$WAN_IFACE'"
FIRST_LAN=$(ip link show | grep -E "^[0-9]+:" | cut -d: -f2 | tr -d ' ' | grep -E "^(eth|enp|ens|end)" | grep -v "$WAN_IFACE" | head -1)
if [ -n "$FIRST_LAN" ]; then
    echo "LAN_INTERFACE='$FIRST_LAN'"
else
    echo "LAN_INTERFACE='eth0' # Fallback falls nur ein Interface vorhanden"
fi