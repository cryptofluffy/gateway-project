#!/usr/bin/env python3
"""
WireGuard Gateway Website - Landing Page & Downloads
Separate Flask application for product website
"""

import logging
import os
import tempfile
import tarfile
import shutil
from datetime import datetime

from flask import Flask, render_template, send_file, abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Flask App Setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')

# Rate Limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["100 per hour"]
)

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Routes
@app.route('/')
def landing():
    """Landing Page"""
    try:
        return render_template('landing.html')
    except Exception as e:
        logger.error(f"Error in landing route: {e}")
        return f"Error: {str(e)}", 500

@app.route('/dashboard')
def dashboard_redirect():
    """Redirect to VPS Dashboard"""
    # Redirect to VPS server dashboard (assuming it runs on port 5000)
    vps_url = "http://localhost:5000/dashboard"
    return f'''
    <script>
        window.location.href = "{vps_url}";
    </script>
    <p>Redirecting to dashboard... <a href="{vps_url}">Click here if not redirected automatically</a></p>
    '''

# Download Routes
@app.route('/download/gateway')
@limiter.limit("5 per minute")
def download_gateway():
    """Download Gateway-PC Package"""
    try:
        # Create temporary archive with Gateway-PC files
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, 'wireguard-gateway.tar.gz')
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Gateway-PC directory
            gateway_dir = os.path.join(os.path.dirname(__file__), '..', 'gateway-pc')
            if os.path.exists(gateway_dir):
                tar.add(gateway_dir, arcname='gateway-pc')
            else:
                # Fallback: Create basic structure
                create_gateway_package(tar)
        
        return send_file(
            archive_path,
            as_attachment=True,
            download_name='wireguard-gateway.tar.gz',
            mimetype='application/gzip'
        )
        
    except Exception as e:
        logger.error(f"Error creating gateway download: {e}")
        abort(500)

@app.route('/download/vps')
@limiter.limit("5 per minute") 
def download_vps():
    """Download VPS-Server Package"""
    try:
        # Create temporary archive with VPS-Server files
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, 'wireguard-vps-server.tar.gz')
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            # VPS-Server directory
            vps_dir = os.path.join(os.path.dirname(__file__), '..', 'vps-server')
            
            if os.path.exists(vps_dir):
                # Important files to include
                files_to_include = [
                    'app.py',
                    'config.py', 
                    'utils.py',
                    'requirements.txt',
                    'install.sh',
                    'templates/',
                    'static/'
                ]
                
                for file_path in files_to_include:
                    full_path = os.path.join(vps_dir, file_path)
                    if os.path.exists(full_path):
                        if os.path.isdir(full_path):
                            tar.add(full_path, arcname=f'vps-server/{file_path}')
                        else:
                            tar.add(full_path, arcname=f'vps-server/{file_path}')
            
            # Installation README
            create_vps_readme(tar)
        
        return send_file(
            archive_path,
            as_attachment=True,
            download_name='wireguard-vps-server.tar.gz',
            mimetype='application/gzip'
        )
        
    except Exception as e:
        logger.error(f"Error creating VPS download: {e}")
        abort(500)

def create_gateway_package(tar):
    """Create Gateway package if directory doesn't exist"""
    temp_dir = tempfile.mkdtemp()
    gateway_dir = os.path.join(temp_dir, 'gateway-pc')
    os.makedirs(gateway_dir)
    
    # Installation Script
    install_script = """#!/bin/bash
# WireGuard Gateway Installation Script
set -e

echo "🚀 Installing WireGuard Gateway..."

# System Update
apt-get update
apt-get install -y wireguard python3 python3-pip

# Install Python requirements
pip3 install flask requests

# Copy files
cp gateway_manager.py /usr/local/bin/
cp gui_app.py /usr/local/bin/
chmod +x /usr/local/bin/gateway_manager.py
chmod +x /usr/local/bin/gui_app.py

# Create systemd service
cat > /etc/systemd/system/wireguard-gateway.service << 'EOF'
[Unit]
Description=WireGuard Gateway Manager
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /usr/local/bin/gateway_manager.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wireguard-gateway.service

echo "✅ WireGuard Gateway installed successfully!"
echo "🔧 Run: python3 /usr/local/bin/gui_app.py to configure"
"""
    
    with open(os.path.join(gateway_dir, 'install.sh'), 'w') as f:
        f.write(install_script)
    
    # README
    readme = """# WireGuard Gateway

## Installation

1. Extract the archive:
   ```bash
   tar -xzf wireguard-gateway.tar.gz
   cd gateway-pc
   ```

2. Run installation:
   ```bash
   sudo bash install.sh
   ```

3. Configure the gateway:
   ```bash
   sudo python3 /usr/local/bin/gui_app.py
   ```

## Requirements

- Linux (Ubuntu 18.04+, Debian 10+, Raspberry Pi OS)
- Root access
- Internet connection

## Features

- Automatic WireGuard setup
- Network interface detection
- Port forwarding support
- Web-based configuration
"""
    
    with open(os.path.join(gateway_dir, 'README.md'), 'w') as f:
        f.write(readme)
    
    tar.add(gateway_dir, arcname='gateway-pc')
    shutil.rmtree(temp_dir)

def create_vps_readme(tar):
    """Create VPS Installation README"""
    temp_dir = tempfile.mkdtemp()
    readme_path = os.path.join(temp_dir, 'README.md')
    
    readme_content = """# WireGuard VPS Server

## Quick Installation

1. Extract the archive:
   ```bash
   tar -xzf wireguard-vps-server.tar.gz
   cd vps-server
   ```

2. Run installation:
   ```bash
   sudo bash install.sh
   ```

3. Access the web interface:
   ```
   http://YOUR_VPS_IP:5000
   ```

## Manual Installation

1. Install requirements:
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3 python3-pip wireguard
   pip3 install -r requirements.txt
   ```

2. Run the server:
   ```bash
   sudo python3 app.py
   ```

## Configuration

- Edit `config.py` for custom settings
- Default port: 5000
- WireGuard port: 51820/UDP

## Features

- Web-based dashboard
- Client management
- Port forwarding
- Real-time monitoring
- Multi-language support (DE/EN)

## Security

- Enable firewall for port 5000 and 51820
- Use HTTPS in production
- Regular security updates

## Support

Check the dashboard for VPS configuration data needed for gateway setup.
"""
    
    with open(readme_path, 'w') as f:
        f.write(readme_content)
    
    tar.add(readme_path, arcname='vps-server/README.md')
    shutil.rmtree(temp_dir)

# Error Handlers
@app.errorhandler(404)
def not_found_error(error):
    return "Page not found", 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {error}")
    return "Internal server error", 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return f"Rate limit exceeded: {str(e.description)}", 429

if __name__ == '__main__':
    logger.info("Starting WireGuard Gateway Website")
    
    # Start the Flask application (website on port 8000)
    app.run(host='0.0.0.0', port=8000, debug=False)