#!/bin/bash

# VPN Gateway Project Location Finder
# This script provides commands to help locate your gateway project on a VPS server

echo "=== VPN Gateway Project Location Finder ==="
echo "Copy and run these commands on your VPS server to locate the project:"
echo ""

echo "1. Search common installation directories:"
echo "# Check /opt directory (common for custom applications)"
echo "find /opt -name '*gateway*' -type d 2>/dev/null"
echo "find /opt -name '*.py' -path '*gateway*' 2>/dev/null | head -10"
echo ""

echo "# Check /home directories (user installations)"
echo "find /home -name '*gateway*' -type d 2>/dev/null"
echo "find /home -name 'requirements.txt' -o -name 'setup.py' -o -name 'main.py' 2>/dev/null | grep -i gateway"
echo ""

echo "# Check /root directory (root user installations)"
echo "find /root -name '*gateway*' -type d 2>/dev/null"
echo "find /root -name '*.py' 2>/dev/null | head -20"
echo ""

echo "# Check /var/www (web applications)"
echo "find /var/www -name '*gateway*' -type d 2>/dev/null"
echo ""

echo "# Check /srv (service data)"
echo "find /srv -name '*gateway*' -type d 2>/dev/null"
echo ""

echo "# Check /usr/local (locally installed software)"
echo "find /usr/local -name '*gateway*' -type d 2>/dev/null"
echo ""

echo "2. Use locate command (if updatedb is available):"
echo "# Update locate database first"
echo "updatedb"
echo "# Search for gateway-related files"
echo "locate gateway | grep -v /proc | head -20"
echo "locate vpn | grep -v /proc | head -20"
echo ""

echo "3. Search for Python files that might be the gateway:"
echo "# Find Python files with common gateway patterns"
echo "find / -name '*.py' -exec grep -l 'gateway\\|vpn\\|server\\|tunnel' {} \\; 2>/dev/null | head -20"
echo ""

echo "# Look for main entry points"
echo "find / -name 'main.py' -o -name 'app.py' -o -name 'server.py' -o -name 'gateway.py' 2>/dev/null"
echo ""

echo "4. Check for running processes:"
echo "# Find Python processes that might be your gateway"
echo "ps aux | grep python | grep -v grep"
echo ""

echo "# Get detailed process information with working directory"
echo "ps -eo pid,ppid,cmd,cwd | grep python | grep -v grep"
echo ""

echo "# For each Python PID found above, check its working directory:"
echo "# Replace PID with actual process ID"
echo "pwdx PID"
echo "ls -la /proc/PID/cwd"
echo ""

echo "5. Check systemd services:"
echo "# List all systemd services"
echo "systemctl list-unit-files | grep -i gateway"
echo "systemctl list-unit-files | grep -i vpn"
echo ""

echo "# Check service status and get more info"
echo "systemctl status gateway* 2>/dev/null"
echo "systemctl status vpn* 2>/dev/null"
echo ""

echo "# Show service file locations"
echo "find /etc/systemd -name '*gateway*' -o -name '*vpn*' 2>/dev/null"
echo "find /lib/systemd -name '*gateway*' -o -name '*vpn*' 2>/dev/null"
echo ""

echo "6. Check for configuration files:"
echo "# Look for config files that might indicate installation location"
echo "find /etc -name '*gateway*' -o -name '*vpn*' 2>/dev/null"
echo ""

echo "# Check for Python virtual environments"
echo "find / -name 'pyvenv.cfg' 2>/dev/null | head -10"
echo "find / -type d -name 'venv' -o -name '.venv' -o -name 'env' 2>/dev/null | head -10"
echo ""

echo "7. Search by file content:"
echo "# Search for files containing specific gateway-related terms"
echo "grep -r 'import.*gateway' / 2>/dev/null | head -10"
echo "grep -r 'class.*Gateway' / 2>/dev/null | head -10"
echo ""

echo "8. Check common Python package locations:"
echo "# Check site-packages for installed gateway packages"
echo "find /usr/local/lib/python*/site-packages -name '*gateway*' 2>/dev/null"
echo "find /usr/lib/python*/site-packages -name '*gateway*' 2>/dev/null"
echo ""

echo "9. Check for Docker containers (if using Docker):"
echo "# List running containers"
echo "docker ps"
echo ""

echo "# Check for gateway-related images"
echo "docker images | grep -i gateway"
echo "docker images | grep -i vpn"
echo ""

echo "10. Advanced process inspection:"
echo "# If you find a Python process, get its command line and environment"
echo "# Replace PID with actual process ID"
echo "cat /proc/PID/cmdline | tr '\\0' ' '"
echo "cat /proc/PID/environ | tr '\\0' '\\n' | grep -E 'PATH|PWD|HOME'"
echo ""

echo "11. Check for recent Python files:"
echo "# Find recently modified Python files (last 7 days)"
echo "find / -name '*.py' -mtime -7 2>/dev/null | head -20"
echo ""

echo "12. Network-based detection:"
echo "# Check what's listening on common VPN/gateway ports"
echo "netstat -tlnp | grep ':1194\\|:443\\|:80\\|:8080\\|:8000'"
echo "ss -tlnp | grep ':1194\\|:443\\|:80\\|:8080\\|:8000'"
echo ""

echo "# Use lsof to find which process is using specific ports"
echo "lsof -i :PORT_NUMBER"
echo ""

echo "=== Quick One-Liner Commands ==="
echo ""
echo "# Comprehensive search in one command:"
echo "for dir in /opt /home /root /var/www /srv /usr/local; do echo \"=== Searching \$dir ===\"; find \$dir -name '*gateway*' -o -name '*vpn*' 2>/dev/null; done"
echo ""

echo "# Find all Python files and search for gateway-related content:"
echo "find / -name '*.py' 2>/dev/null | xargs grep -l 'gateway\\|Gateway' 2>/dev/null | head -10"
echo ""

echo "# Check all running Python processes and their directories:"
echo "ps aux | grep python | grep -v grep | awk '{print \$2}' | xargs -I {} sh -c 'echo \"PID: {}\"; ls -la /proc/{}/cwd 2>/dev/null; echo'"