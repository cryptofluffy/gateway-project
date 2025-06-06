# WireGuard Gateway System

Eine komplette WireGuard-basierte Gateway-Lösung für sichere Netzwerk-Tunneling zwischen Heimnetzwerk und VPS.

## 🎯 Projektübersicht

Das System besteht aus einem Gateway-Gerät (Raspberry Pi/Mini-PC) mit 2 LAN-Ports, das einen permanenten verschlüsselten Tunnel zu einem VPS aufbaut. Server werden am Gateway angeschlossen und erhalten Internet-Zugang über den VPS-Tunnel.

```
Internet ←→ [Router] ←→ Port A [Gateway-PC] Port B ←→ [Server]
                            ↓ WireGuard Tunnel
                          [VPS] ←→ Internet
```

## 🏗️ Netzwerk-Architektur

- **Port A (eth0)**: Heimnetzwerk-Anschluss (192.168.1.254/24)
- **Port B (eth1)**: Server-Netzwerk (10.0.0.1/24) 
- **WireGuard**: Tunnel-Interface (10.8.0.2 ↔ 10.8.0.1)
- **VPS**: Web-Interface für Port-Weiterleitungen

## 📦 Komponenten

### VPS-Server (`/vps-server/`)
- **Flask Web-Interface** für Management
- **REST-API** für Port-Weiterleitungen
- **WireGuard-Server** mit automatischer Konfiguration
- **Automatisches Setup-Script**

### Gateway-PC (`/gateway-pc/`)
- **Python Command-Line Tool** für Tunnel-Management
- **Tkinter GUI-Anwendung** für einfache Bedienung
- **Automatische Netzwerk-Konfiguration** (2 LAN-Ports)
- **DHCP-Server** für angeschlossene Server
- **Monitoring & Auto-Reconnect**

## 🚀 Quick Start

### 1. VPS installieren

```bash
git clone https://github.com/DEIN_USERNAME/wireguard-gateway.git
cd wireguard-gateway/vps-server
sudo ./install.sh
```

### 2. Gateway-PC installieren

```bash
git clone https://github.com/DEIN_USERNAME/wireguard-gateway.git
cd wireguard-gateway/gateway-pc
sudo ./install.sh
sudo reboot
```

### 3. Gateway konfigurieren

```bash
# VPS Public Key vom Web-Interface kopieren
gateway-manager setup <VPS_IP> <VPS_PUBLIC_KEY>
gateway-manager start
```

### 4. Web-Interface öffnen

`http://VPS_IP:8080` - Port-Weiterleitungen verwalten

## 🖥️ Benutzeroberflächen

### VPS Web-Interface
- Dashboard mit Tunnel-Status
- Port-Weiterleitungen per Klick
- Verbundene Clients anzeigen
- WireGuard-Service steuern

### Gateway-PC GUI
```bash
gateway-gui
```
- Live-Status und Statistiken
- Tunnel-Kontrolle
- Konfiguration per Dialog
- System-Logs

### Command-Line Tools
```bash
gateway-manager setup <VPS_IP> <VPS_KEY>    # Konfigurieren
gateway-manager start                       # Starten
gateway-manager status                      # Status
gateway-manager monitor                     # Monitoring
```

## 🔧 Systemanforderungen

### VPS
- **Ubuntu 22.04+** / Debian 11+
- **512 MB RAM** (minimal)
- **Öffentliche IP-Adresse**
- **Ports**: 51820/UDP (WireGuard), 8080/TCP (Web)

### Gateway-PC
- **Raspberry Pi 4** oder Mini-PC
- **2x Ethernet-Ports**
- **Ubuntu 22.04+**
- **1 GB RAM**

## 🔐 Sicherheitsfeatures

- **WireGuard-Verschlüsselung** für alle Datenübertragung
- **Netzwerk-Isolation** zwischen Heim- und Server-Netz
- **Automatische Firewall-Regeln** (iptables)
- **Keine direkte Exposition** der Server ins Internet

## 📋 Anwendungsfälle

- **Home-Lab Server** sicher von außen erreichen
- **Development-Umgebungen** ohne Port-Forwarding am Router
- **IoT-Geräte** in isoliertem Netz betreiben
- **Backup-Server** mit verschlüsseltem Zugang
- **Media-Server** (Plex, Jellyfin) über VPS

## 🔍 Troubleshooting

### VPS
```bash
systemctl status wg-quick@wg0
systemctl status wireguard-gateway
journalctl -u wireguard-gateway -f
```

### Gateway-PC
```bash
systemctl status wireguard-gateway
gateway-manager status
gateway-gui  # Logs-Tab
```

## 📖 Dokumentation

- [VPS Setup Guide](vps-server/README.md)
- [Gateway-PC Setup Guide](gateway-pc/README.md)

## 🤝 Beitragen

1. Fork das Repository
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Commit deine Änderungen (`git commit -m 'Add amazing feature'`)
4. Push zum Branch (`git push origin feature/amazing-feature`)
5. Pull Request öffnen

## 📄 Lizenz

Dieses Projekt steht unter der MIT-Lizenz. Siehe [LICENSE](LICENSE) für Details.

## 🙏 Acknowledgments

- WireGuard-Team für das großartige VPN-Protokoll
- Flask-Community für das Web-Framework
- Alle Open-Source-Beiträger