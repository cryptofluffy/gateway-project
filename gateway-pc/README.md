# WireGuard Gateway PC Software

Diese Software läuft auf dem Gateway-PC (Raspberry Pi/Mini-PC) und stellt die Gateway-Funktionalität zwischen Heimnetzwerk und VPS bereit.

## 🏗️ Hardware-Setup

```
Internet ←→ [Router] ←→ Port A [Gateway-PC] Port B ←→ [Server]
                            ↓ WireGuard Tunnel
                          [VPS] ←→ Internet
```

### Netzwerk-Interfaces:
- **Port A (eth0)**: Heimnetzwerk-Anschluss (192.168.1.254/24)
- **Port B (eth1)**: Server-Netzwerk (10.0.0.1/24) 
- **WireGuard (wg0)**: Tunnel-Interface (10.8.0.2/24)

## 🚀 Installation

### Automatische Installation

```bash
sudo ./install.sh
```

Das Installationsskript:
- Installiert WireGuard und alle Abhängigkeiten
- Konfiguriert Netzwerk-Interfaces automatisch
- Richtet DHCP-Server für Server-Netzwerk ein
- Erstellt Systemd-Services für automatischen Start
- Installiert GUI-Anwendung

### Nach der Installation

1. **System neu starten** (für Netzwerk-Konfiguration):
```bash
sudo reboot
```

2. **Gateway konfigurieren**:
```bash
gateway-manager setup <VPS_IP> <VPS_PUBLIC_KEY>
```

3. **Gateway starten**:
```bash
gateway-manager start
```

## 🖥️ Benutzeroberflächen

### Kommandozeilen-Tool

```bash
# Gateway konfigurieren
gateway-manager setup 192.168.100.50 "SERVER_PUBLIC_KEY_HIER"

# Gateway starten/stoppen
gateway-manager start
gateway-manager stop

# Status prüfen
gateway-manager status

# Monitoring starten
gateway-manager monitor
```

### Grafische Oberfläche

```bash
# GUI starten
gateway-gui
```

**GUI-Features:**
- 📊 Dashboard mit Live-Status
- 🔄 Tunnel-Kontrolle (Start/Stop/Restart)
- ⚙️ Konfiguration per Dialog
- 📈 Interface-Statistiken
- 📝 System-Logs anzeigen
- 🔍 Konnektivitätstest
- 🌐 VPS Web-Interface öffnen

## 🔧 Konfiguration

### Manuelle Konfiguration

Falls die automatische Konfiguration nicht funktioniert:

1. **VPS-Konfiguration** (`/etc/wireguard-gateway/config.json`):
```json
{
    "vps_endpoint": "VPS_IP:51820",
    "vps_public_key": "VPS_PUBLIC_KEY",
    "gateway_private_key": "GATEWAY_PRIVATE_KEY", 
    "gateway_public_key": "GATEWAY_PUBLIC_KEY"
}
```

2. **WireGuard-Konfiguration** (`/etc/wireguard/gateway.conf`):
```ini
[Interface]
PrivateKey = GATEWAY_PRIVATE_KEY
Address = 10.8.0.2/24
Table = off

PostUp = ip rule add from 10.0.0.0/24 table 200
PostUp = ip route add default dev %i table 200
PostUp = iptables -t nat -A POSTROUTING -o %i -j MASQUERADE

[Peer]
PublicKey = VPS_PUBLIC_KEY
Endpoint = VPS_IP:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
```

### Netzwerk-Konfiguration

**Netplan-Konfiguration** (`/etc/netplan/01-gateway-config.yaml`):
```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: false
      addresses:
        - 192.168.1.254/24
    eth1:
      dhcp4: false
      addresses:
        - 10.0.0.1/24
```

**DHCP-Server** (`/etc/dhcp/dhcpd.conf`):
```
subnet 10.0.0.0 netmask 255.255.255.0 {
    range 10.0.0.100 10.0.0.200;
    option routers 10.0.0.1;
    option domain-name-servers 8.8.8.8, 8.8.4.4;
}
```

## 🔍 Troubleshooting

### Services prüfen
```bash
# WireGuard Status
systemctl status wireguard-gateway
wg show

# Gateway Monitor
systemctl status gateway-monitor

# DHCP-Server
systemctl status isc-dhcp-server

# Logs anzeigen
journalctl -u wireguard-gateway -f
tail -f /var/log/wireguard-gateway/monitor.log
```

### Netzwerk-Diagnose
```bash
# Interface-Status
ip addr show
ip route show

# Konnektivität testen
ping 10.8.0.1          # VPS erreichen
ping 8.8.8.8           # Internet über Tunnel
```

### Häufige Probleme

**Gateway startet nicht:**
- Netplan-Konfiguration prüfen: `netplan apply`
- Interface-Status prüfen: `ip link show`

**Tunnel verbindet nicht:**
- VPS-Konfiguration prüfen
- Firewall-Regeln überprüfen
- Public Key auf VPS korrekt eingetragen?

**Server bekommen keine IP:**
- DHCP-Server Status: `systemctl status isc-dhcp-server`
- Interface eth1 aktiv: `ip link show eth1`

**Kein Internet-Zugang:**
- IP-Forwarding aktiviert: `sysctl net.ipv4.ip_forward`
- iptables-Regeln prüfen: `iptables -L -n`

## 📋 Systemanforderungen

### Hardware
- **Raspberry Pi 4** (empfohlen) oder vergleichbarer Mini-PC
- **2x Ethernet-Ports** (USB-Ethernet-Adapter falls nötig)
- **16 GB SD-Karte** (minimal)
- **Gehäuse mit Lüftung** (empfohlen)

### Software
- **Ubuntu 22.04 LTS** (empfohlen)
- **Debian 11+** (alternativ)
- **Minimum 1 GB RAM**

### Netzwerk
- **Statische IP** im Heimnetzwerk (192.168.1.254)
- **Internet-Zugang** für VPS-Verbindung
- **Freier Port 51820/UDP** für WireGuard

## 🔐 Sicherheit

### Empfohlene Maßnahmen
- **SSH-Zugang absichern** (Key-Auth, non-standard Port)
- **Firewall konfigurieren** (ufw/iptables)
- **Regelmäßige Updates** durchführen
- **Backup der Konfiguration** erstellen

### Backup erstellen
```bash
# Konfiguration sichern
sudo tar -czf gateway-backup.tar.gz \
    /etc/wireguard/ \
    /etc/wireguard-gateway/ \
    /etc/netplan/01-gateway-config.yaml \
    /etc/dhcp/dhcpd.conf
```

## 🔗 Integration

### Server-Anschluss
Server am Port B (eth1) erhalten automatisch:
- **IP-Adresse**: 10.0.0.100 - 10.0.0.200 (DHCP)
- **Gateway**: 10.0.0.1 (Gateway-PC)
- **DNS**: 8.8.8.8, 8.8.4.4
- **Internet-Zugang**: Über VPS-Tunnel

### Port-Weiterleitungen
Werden zentral auf dem VPS über das Web-Interface verwaltet:
- **VPS Port** → **Server-IP:Port**
- Automatische iptables-Regeln
- Sofortige Aktivierung

## 📞 Support

Bei Problemen:
1. **Logs prüfen**: `gateway-gui` → Logs-Tab
2. **Status überprüfen**: `gateway-manager status`
3. **Services neu starten**: `sudo systemctl restart wireguard-gateway`
4. **System neu starten**: `sudo reboot`