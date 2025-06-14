#!/bin/bash

# Install Network Scanner Service
# This script installs and configures the network scanner service

set -e

echo "Installing Network Scanner Service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create scripts directory if it doesn't exist
mkdir -p /opt/gateway/scripts

# Copy network scanner script
cp /opt/gateway/gateway-software/network-scanner.py /usr/local/bin/
chmod +x /usr/local/bin/network-scanner.py

# Install systemd service files
cp /opt/gateway/gateway-software/systemd/network-scanner.service /etc/systemd/system/
cp /opt/gateway/gateway-software/systemd/network-scanner.timer /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable and start the timer
systemctl enable network-scanner.timer
systemctl start network-scanner.timer

# Check status
if systemctl is-active --quiet network-scanner.timer; then
    echo "✅ Network Scanner Service installed and running"
    systemctl status network-scanner.timer --no-pager
else
    echo "❌ Failed to start Network Scanner Service"
    exit 1
fi

echo "Network Scanner installation completed successfully!"