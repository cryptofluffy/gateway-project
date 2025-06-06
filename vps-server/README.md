# WireGuard Gateway VPS Server

Diese Software läuft auf dem VPS und stellt das Web-Interface sowie die Backend-API für das WireGuard Gateway System bereit.

## 🚀 Installation

### Automatische Installation

```bash
sudo ./install.sh
```

Das Installationsskript:
- Installiert WireGuard und Python-Abhängigkeiten
- Generiert Server-Keys automatisch
- Konfiguriert IP-Forwarding und Firewall
- Startet alle Services

### Manuelle Installation

1. **System vorbereiten:**
```bash
apt update && apt upgrade -y
apt install -y wireguard python3 python3-pip
```

2. **Python-Abhängigkeiten installieren:**
```bash
pip3 install -r requirements.txt
```

3. **WireGuard konfigurieren:**
```bash
# Keys generieren
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key

# Konfiguration erstellen
sudo nano /etc/wireguard/wg0.conf
```

## 📱 Web-Interface

Nach der Installation ist das Web-Interface verfügbar unter:
- **URL:** `http://VPS-IP:8080`
- **Features:**
  - Dashboard mit Tunnel-Status
  - Port-Weiterleitungen verwalten
  - Verbundene Clients anzeigen
  - WireGuard-Service steuern

## 🔌 API-Endpunkte

### Status abfragen
```bash
GET /api/status
```

### Port-Weiterleitungen
```bash
# Alle anzeigen
GET /api/port-forwards

# Neue hinzufügen
POST /api/port-forwards
{
    "external_port": 8080,
    "internal_ip": "10.0.0.100", 
    "internal_port": 80,
    "protocol": "tcp"
}

# Entfernen
DELETE /api/port-forwards?rule_id=8080_tcp
```

### WireGuard Service
```bash
POST /api/restart-wireguard
```

## 🔧 Konfiguration

### WireGuard-Konfiguration (`/etc/wireguard/wg0.conf`)
```ini
[Interface]
PrivateKey = SERVER_PRIVATE_KEY
Address = 10.8.0.1/24
ListenPort = 51820

PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
# Gateway-PC wird hier hinzugefügt
PublicKey = GATEWAY_PUBLIC_KEY
AllowedIPs = 10.8.0.2/32, 10.0.0.0/24
```

### Client hinzufügen

Für jeden Gateway-PC einen `[Peer]`-Block zur `wg0.conf` hinzufügen:

```ini
[Peer]
PublicKey = GATEWAY_PUBLIC_KEY
AllowedIPs = 10.8.0.2/32, 10.0.0.0/24
```

## 🔍 Troubleshooting

### Services prüfen
```bash
# WireGuard Status
systemctl status wg-quick@wg0
wg show

# Web-Interface Status  
systemctl status wireguard-gateway

# Logs anzeigen
journalctl -u wg-quick@wg0 -f
journalctl -u wireguard-gateway -f
```

### Häufige Probleme

**WireGuard startet nicht:**
- IP-Forwarding prüfen: `sysctl net.ipv4.ip_forward`
- Firewall-Regeln prüfen: `iptables -L`

**Web-Interface nicht erreichbar:**
- Port 8080 in Firewall freigeben
- Service-Status prüfen: `systemctl status wireguard-gateway`

**Clients können sich nicht verbinden:**
- Server-Port 51820/UDP freigeben
- Client-Konfiguration prüfen

## 📋 Systemanforderungen

- **OS:** Ubuntu 20.04+ / Debian 10+
- **RAM:** 512 MB (minimal)
- **Storage:** 2 GB
- **Network:** Öffentliche IP-Adresse
- **Ports:** 51820/UDP (WireGuard), 8080/TCP (Web-Interface)

## 🔐 Sicherheit

- Web-Interface läuft standardmäßig ohne Authentifizierung
- Für Produktionseinsatz: Reverse-Proxy mit HTTPS einrichten
- Firewall nur benötigte Ports freigeben
- Regelmäßige Updates durchführen