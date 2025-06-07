# WireGuard Gateway - Projekt Übersicht

Ein sicheres VPN-Gateway-System mit WireGuard-Technologie, bestehend aus drei Hauptkomponenten:

## 📁 Projektstruktur

### 🖥️ **vps-server/**
VPS/Cloud-Server Anwendung mit Web-Dashboard
- **Port:** 5000 (Management Interface)
- **Features:** Client-Management, Port-Weiterleitungen, Monitoring
- **Technologie:** Python Flask, WireGuard

### 🏠 **gateway-pc/**
Gateway-Client für lokale Netzwerke
- **Hardware:** Raspberry Pi, Linux PC, Router
- **Features:** Automatische VPN-Verbindung, Netzwerk-Bridging
- **Technologie:** Python, WireGuard, Network Interface Management

### 🌐 **website/**
Produkt-Website mit Downloads
- **Port:** 8000 (Public Website)
- **Features:** Landing Page, Download-Center, Mehrsprachen-Support
- **Technologie:** Flask, TailwindCSS, i18n

## 🚀 Quick Start

### 1. VPS Server Setup
```bash
cd vps-server
sudo bash install.sh
# Läuft auf http://YOUR_VPS_IP:5000
```

### 2. Gateway PC Setup
```bash
cd gateway-pc
sudo bash install.sh
# Konfiguration über GUI oder Kommandozeile
```

### 3. Website (Optional)
```bash
cd website
pip3 install -r requirements.txt
python3 app.py
# Läuft auf http://localhost:8000
```

## 🔧 Systemanforderungen

- **OS:** Ubuntu 18.04+, Debian 10+, CentOS 7+, Raspberry Pi OS
- **Netzwerk:** Internet-Verbindung, offene Ports (51820/UDP für WireGuard)
- **Berechtigung:** Root-Zugriff für Installation
- **Hardware:** Mindestens 512MB RAM, 1GB Speicher

## 🌟 Features

### VPS Server
- 📊 **Real-time Dashboard** - Live-Monitoring aller Verbindungen
- 👥 **Client Management** - Einfache Verwaltung von Gateway-PCs
- 🔀 **Port Forwarding** - Sichere Weiterleitung von Ports
- 🌍 **Multi-Language** - Deutsch & Englisch Support
- 🔒 **Security** - Rate Limiting, Input Validation

### Gateway PC
- 🔄 **Auto-Connect** - Automatische VPN-Verbindung zum VPS
- 🌐 **Network Bridge** - Transparente Netzwerk-Integration
- ⚡ **Interface Detection** - Automatische Netzwerk-Interface Erkennung
- 🎛️ **Manual Config** - Manuelle Konfiguration für spezielle Setups
- 📱 **GUI Management** - Benutzerfreundliche Oberfläche

### Website
- 🎨 **Modern Design** - Responsive Landing Page
- 📥 **Download Center** - Direkte Downloads für beide Komponenten
- 🌍 **Internationalization** - DE/EN Sprach-Support
- 📋 **Documentation** - Vollständige Setup-Anleitungen

## 🔗 Verbindungsablauf

1. **VPS Setup** → WireGuard Server läuft auf Port 51820
2. **Gateway Installation** → Verbindet sich automatisch zum VPS
3. **Netzwerk-Bridge** → Gateway leitet lokalen Traffic über VPN
4. **Port-Weiterleitungen** → Externe Ports → VPS → Gateway → Lokale Services

## 📋 Port-Übersicht

| Service | Port | Beschreibung |
|---------|------|--------------|
| WireGuard VPN | 51820/UDP | VPN-Tunnel |
| VPS Dashboard | 5000/TCP | Management Interface |
| Website | 8000/TCP | Public Landing Page |

## 🛡️ Sicherheit

- **WireGuard Encryption** - ChaCha20, Poly1305, Curve25519
- **Rate Limiting** - Schutz vor Brute-Force-Angriffen
- **Input Validation** - Sichere Behandlung aller Eingaben
- **Firewall Ready** - Konfiguration für iptables/ufw

## 📚 Weitere Dokumentation

- **VPS Server:** `vps-server/README.md`
- **Gateway PC:** `gateway-pc/README.md`
- **Deployment:** `vps-server/deploy.md`

## 🆘 Support

Bei Problemen:
1. Prüfen Sie die Logs: `journalctl -u wireguard-gateway`
2. Firewall-Einstellungen für Port 51820/UDP
3. Netzwerk-Konnektivität zwischen VPS und Gateway
4. Root-Berechtigung für WireGuard-Befehle

---

🔒 **WireGuard Gateway** - Sichere Netzwerk-Verbindungen leicht gemacht!