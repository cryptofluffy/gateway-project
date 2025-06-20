# Gateway Pro Dashboard

Professional Gateway Management Dashboard mit FastSpring Integration für kommerzielle VPN/Gateway Services.

## Features

🔐 **FastSpring Integration** - Serverlose License-Validierung  
🖥️ **VPS Management** - Vollständige Server-Kontrolle  
🌐 **Gateway Control** - Hardware-Gateway Management  
📊 **Real-time Monitoring** - Live Status und Metriken  
🔧 **One-liner Installation** - Automatische Gateway-Setup  
💳 **Subscription Management** - Flexible Gateway-Limits  

## Quick Start

### 1. Repository klonen
```bash
git clone https://github.com/yourusername/gateway-dashboard.git
cd gateway-dashboard
```

### 2. Environment Setup
```bash
# .env Datei erstellen
cp .env.example .env

# FastSpring Credentials eintragen
nano .env
```

### 3. Development starten
```bash
npm install
npm run dev
```

### 4. Production Deployment
```bash
# Mit Docker Compose
docker-compose up -d

# Oder manuell
npm run build
```

## FastSpring Integration

### 1. FastSpring API Credentials

Hole deine Credentials aus dem FastSpring Dashboard:

1. **Login** → FastSpring Dashboard
2. **Developer Tools** → API Credentials  
3. **Create API User** mit Permissions:
   - `subscription:read`
   - `account:read`
   - `account:write`

### 2. Environment Variablen

In `.env` Datei eintragen:

```bash
# FastSpring API Configuration
VITE_FASTSPRING_USERNAME=your_api_username
VITE_FASTSPRING_PASSWORD=your_api_password  
VITE_FASTSPRING_STOREFRONT=yourstore.onfastspring.com

# Production Mode (false = Mock API)
VITE_USE_FASTSPRING_MOCK=false

# VPS Configuration
VITE_VPS_DOMAIN=your-vps-domain.com
VITE_VPS_IP=your.vps.ip.address
```

### 3. FastSpring Produkte

Erstelle diese Produkte in FastSpring:

**Starter Plan:**
- Product ID: `gateway-starter`
- Preis: €10/Monat  
- Quantity: 1 Gateway

**Professional Plan:**
- Product ID: `gateway-professional`
- Preis: €50/Monat
- Quantity: 5 Gateways

**Enterprise Plan:**
- Product ID: `gateway-enterprise`
- Preis: €200/Monat
- Quantity: 50 Gateways

## VPS Deployment

### Docker Compose (Empfohlen)

```bash
# 1. Repository klonen
git clone https://github.com/yourusername/gateway-dashboard.git
cd gateway-dashboard

# 2. Environment konfigurieren
cp .env.example .env
nano .env

# 3. SSL Zertifikate (Let's Encrypt)
mkdir ssl
sudo certbot certonly --standalone -d your-domain.com
cp /etc/letsencrypt/live/your-domain.com/* ./ssl/

# 4. Domain in nginx.conf anpassen
sed -i 's/your-domain.com/YOUR_ACTUAL_DOMAIN/g' nginx.conf

# 5. Starten
docker-compose up -d
```

## Gateway Installation

Das Dashboard generiert automatisch One-liner Commands für Gateway-Hardware:

### 1. Gateway hinzufügen
1. **Dashboard** → Gateway Tab
2. **Add Gateway** klicken
3. **Gateway Details** eingeben
4. **Installation Command** kopieren

### 2. Auf Gateway Hardware ausführen
```bash
# Beispiel Command (vom Dashboard generiert)
curl -fsSL https://raw.githubusercontent.com/yourusername/gateway-installer/main/install.sh | bash -s -- \
  --vps-ip="45.67.89.123" \
  --gateway-id="office-berlin" \
  --tunnel-network="10.0.50.1/24"
```

### 3. Gateway Status prüfen
- **Dashboard** zeigt automatisch Online/Offline Status
- **WireGuard Tunnel** Status
- **Letzte Verbindung** Timestamp

## Tech Stack

- React 19.1.0
- Vite 6.3.5
- FastSpring API Integration
- WireGuard VPN
- Docker & nginx
- Let's Encrypt SSL

## Development

### Scripts
```bash
npm run dev          # Development server (Port 5174)
npm run build        # Production build
npm run preview      # Preview production build
```

### Project Structure
```
src/
├── components/          # React Components
│   ├── Dashboard.jsx
│   ├── VPSManager.jsx
│   ├── GatewayManager.jsx
│   ├── EmailLogin.jsx
│   └── ...
├── services/           # API Services
│   ├── fastspringApi.js
│   ├── mockApi.js
│   └── api.js
├── styles/            # Component Styles
└── App.jsx           # Main Application
```
