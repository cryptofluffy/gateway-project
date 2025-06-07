# 🚀 Deployment Guide

## VPS Deployment via GitHub

### 1. Repository auf VPS klonen

```bash
# SSH zum VPS
ssh root@VPS_IP

# Git installieren (falls nicht vorhanden)
apt update && apt install -y git

# Repository klonen
git clone https://github.com/DEIN_USERNAME/wireguard-gateway.git
cd wireguard-gateway/vps-server

# Installation starten
chmod +x install.sh
./install.sh
```

### 2. Nach der Installation

Das Script gibt dir automatisch aus:
- **Server Public Key** → Für Gateway-PC Konfiguration
- **Web-Interface URL**: `http://VPS_IP:8080`

## Gateway-PC Deployment

### 1. Auf Gateway-PC (Raspberry Pi/Mini-PC)

```bash
# Repository klonen
git clone https://github.com/DEIN_USERNAME/wireguard-gateway.git
cd wireguard-gateway/gateway-pc

# Installation starten
chmod +x install.sh
sudo ./install.sh

# System neu starten (für Netzwerk-Konfiguration)
sudo reboot
```

### 2. Gateway konfigurieren

```bash
# Mit VPS-Daten konfigurieren
gateway-manager setup VPS_IP VPS_PUBLIC_KEY

# Gateway starten
gateway-manager start

# GUI öffnen (optional)
gateway-gui
```

## 🔄 Updates deployen

### VPS aktualisieren
```bash
ssh root@VPS_IP
cd wireguard-gateway
git pull
systemctl restart wireguard-gateway
```

### Gateway-PC aktualisieren
```bash
cd wireguard-gateway
git pull
sudo systemctl restart wireguard-gateway
```

## 📋 Deployment-Checklist

### VPS Setup ✅
- [ ] Ubuntu 22.04+ installiert
- [ ] SSH-Zugang funktioniert
- [ ] Port 51820/UDP + 8080/TCP offen
- [ ] Git installiert
- [ ] Repository geklont
- [ ] `./install.sh` ausgeführt
- [ ] Web-Interface erreichbar
- [ ] Server Public Key notiert

### Gateway-PC Setup ✅
- [ ] Hardware mit 2 Ethernet-Ports
- [ ] Ubuntu 22.04+ installiert
- [ ] Repository geklont
- [ ] `sudo ./install.sh` ausgeführt
- [ ] System neu gestartet
- [ ] Gateway konfiguriert
- [ ] Tunnel gestartet
- [ ] Server-Netz funktioniert (DHCP)

### Test & Verifikation ✅
- [ ] Gateway-PC kann VPS pingen (`ping 10.8.0.1`)
- [ ] Web-Interface zeigt verbundenen Client
- [ ] Server am Port B bekommen IP (10.0.0.x)
- [ ] Port-Weiterleitung funktioniert
- [ ] Internet-Zugang über Tunnel

## 🐛 Häufige Deployment-Probleme

### VPS
**Problem**: Web-Interface nicht erreichbar
```bash
# Firewall prüfen
ufw status
ufw allow 8080

# Service prüfen
systemctl status wireguard-gateway
```

**Problem**: WireGuard startet nicht
```bash
# Logs prüfen
journalctl -u wg-quick@wg0 -f

# Konfiguration prüfen
wg show
```

### Gateway-PC
**Problem**: Netzwerk-Konfiguration fehlerhaft
```bash
# Netplan neu anwenden
sudo netplan apply

# Interface-Status prüfen
ip addr show
```

**Problem**: DHCP-Server startet nicht
```bash
# DHCP-Service prüfen
systemctl status isc-dhcp-server

# Konfiguration prüfen
sudo dhcpd -t
```

## 🔧 Manuelle Konfiguration

Falls das automatische Setup nicht funktioniert, siehe:
- [VPS Manual Setup](vps-server/README.md#manuelle-installation)
- [Gateway Manual Setup](gateway-pc/README.md#manuelle-konfiguration)