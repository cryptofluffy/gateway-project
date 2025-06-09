#!/bin/bash
# Update Script für automatisches Service-Reload
set -e

echo "🔄 Updating VPS services for automatic reload..."

# Überprüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then 
    echo "❌ Bitte als root ausführen (sudo ./update-services.sh)"
    exit 1
fi

# inotify-tools installieren
echo "📦 Installing inotify-tools..."
apt update && apt install -y inotify-tools

# Aktualisierter VPS Service
echo "🔧 Updating wireguard-vps service..."
cat > /etc/systemd/system/wireguard-vps.service << EOF
[Unit]
Description=WireGuard VPS Web Interface
After=network.target wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/wireguard-vps
ExecStart=/opt/wireguard-vps/venv/bin/python /opt/wireguard-vps/app.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=always
RestartSec=5
WatchdogSec=30

[Install]
WantedBy=multi-user.target
EOF

# File-Watcher Service erstellen
echo "👀 Creating file-watcher service..."
cat > /etc/systemd/system/wireguard-vps-watcher.service << EOF
[Unit]
Description=WireGuard VPS File Watcher
After=wireguard-vps.service

[Service]
Type=simple
User=root
ExecStart=/bin/bash -c 'inotifywait -m -e modify,create,delete /opt/wireguard-vps/templates/ --format "%%w%%f" | while read file; do echo "File changed: \$file"; systemctl reload wireguard-vps; sleep 2; done'
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Services aktualisieren
echo "🚀 Reloading and starting services..."
systemctl daemon-reload
systemctl enable wireguard-vps-watcher
systemctl restart wireguard-vps
systemctl start wireguard-vps-watcher

echo "✅ Services updated successfully!"
echo "📊 Status:"
systemctl status wireguard-vps --no-pager -l
echo ""
systemctl status wireguard-vps-watcher --no-pager -l

echo ""
echo "🎯 Das Dashboard lädt jetzt automatisch neu bei Template-Änderungen!"