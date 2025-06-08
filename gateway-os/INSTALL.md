# Gateway OS Installation Guide

A complete Linux distribution optimized for VPN gateway functionality on Raspberry Pi and similar devices.

## Quick Start

### For Raspberry Pi (Recommended)

1. **Download pre-built image** (when available):
   ```bash
   wget https://releases.gateway-os.com/latest/gateway-os-rpi4.img.xz
   ```

2. **Or build from source:**
   ```bash
   cd gateway-os
   sudo ./scripts/build-rpi-image.sh --target rpi4
   ```

3. **Flash to SD card:**
   ```bash
   sudo dd if=images/gateway-os-rpi4-*.img.xz of=/dev/sdX bs=4M status=progress
   sync
   ```

4. **Boot and configure:**
   - Insert SD card and power on
   - Wait 2-3 minutes for first boot setup
   - Connect via SSH: `ssh admin@<gateway-ip>` (password: `gateway123`)
   - Access web interface: `http://<gateway-ip>:8080`

## Build Requirements

### System Requirements
- Linux host system (Ubuntu 20.04+ recommended)
- 8GB+ free disk space
- Internet connection for downloading packages
- sudo privileges

### Dependencies
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y wget git make gcc g++ unzip rsync cpio bc file \
    qemu-user-static binfmt-support debootstrap xz-utils

# Fedora/RHEL
sudo dnf install -y wget git make gcc gcc-c++ unzip rsync cpio bc file \
    qemu-user-static debootstrap xz
```

## Build Process

### Option 1: Quick Raspberry Pi Build
```bash
# Simple automated build
./scripts/build-rpi-image.sh --target rpi4

# Custom output directory
./scripts/build-rpi-image.sh --target rpi4 --output /tmp/images
```

### Option 2: Full Buildroot Build
```bash
# Full customizable build
./build/build-image.sh --target rpi4 --version 1.1.0

# Clean build
./build/build-image.sh --target rpi4 --clean

# For other platforms
./build/build-image.sh --target x86_64
./build/build-image.sh --target rpi3
./build/build-image.sh --target rpi5
```

## Supported Platforms

| Platform | Architecture | Status | Notes |
|----------|-------------|---------|-------|
| Raspberry Pi 3B+ | ARM64 | ✅ Supported | Minimum requirements |
| Raspberry Pi 4B | ARM64 | ✅ Recommended | Best performance |
| Raspberry Pi 5 | ARM64 | ✅ Supported | Latest hardware |
| Generic x86_64 | x86_64 | 🔄 In Progress | PC/Server deployment |
| Generic ARM64 | ARM64 | 🔄 Planned | Other ARM boards |

## Network Configuration

### Default Network Layout
```
Internet ←→ [WAN] Gateway [LAN] ←→ Local Network
              ↕
             VPN Server
```

### IP Configuration
- **LAN Network:** 192.168.100.0/24
- **Gateway IP:** 192.168.100.1
- **DHCP Range:** 192.168.100.10-200
- **VPN Subnet:** 10.8.0.0/24
- **DNS Servers:** 1.1.1.1, 8.8.8.8

### Interface Detection
The system automatically detects and configures:
- **WAN Interface:** First available Ethernet (internet connection)
- **LAN Interface:** Second Ethernet or USB-Ethernet adapter
- **WiFi:** Can be configured as additional WAN or LAN

## Security Features

### Built-in Security
- Minimal attack surface (only required packages)
- Firewall preconfigured with restrictive rules
- Fail2ban protection against brute force
- SSH key authentication recommended
- Automatic security updates

### Default Access
- **SSH:** Port 22 (admin user)
- **Web Interface:** Port 8080
- **VPN:** Port 51820 (WireGuard)

### Hardening Checklist
- [ ] Change default password
- [ ] Set up SSH key authentication
- [ ] Review firewall rules
- [ ] Configure VPN settings
- [ ] Enable automatic updates
- [ ] Set up monitoring

## VPN Gateway Setup

### 1. VPS Server Setup
First, set up the VPS server component:
```bash
# On your VPS
cd vpn_gateway/vps-server
sudo ./install.sh
```

### 2. Gateway Configuration
Configure the gateway to connect to your VPS:

#### Via Web Interface (Recommended)
1. Open `http://<gateway-ip>:8080`
2. Go to VPN Settings
3. Enter VPS IP address
4. Add VPS public key
5. Copy gateway public key to VPS
6. Enable VPN connection

#### Via Command Line
```bash
# SSH to gateway
ssh admin@<gateway-ip>

# Edit configuration
sudo nano /etc/gateway/gateway.json

# Add VPS settings
{
  "vpn": {
    "enabled": true,
    "vps_ip": "YOUR_VPS_IP",
    "vps_public_key": "VPS_PUBLIC_KEY"
  }
}

# Restart gateway service
sudo systemctl restart gateway-manager
```

## Customization

### Build Customization
Modify these files before building:
- `build/configs/gateway-*_defconfig` - Package selection
- `rootfs/` - Root filesystem overlay
- `bootloader/config.txt` - Boot configuration
- `services/` - System services

### Runtime Customization
- Configuration: `/etc/gateway/gateway.json`
- Custom scripts: `/usr/local/bin/`
- Service overrides: `/etc/systemd/system/`

## Troubleshooting

### Build Issues
```bash
# Check dependencies
./build/build-image.sh --help

# Clean build
rm -rf build-output/
./build/build-image.sh --target rpi4 --clean
```

### Boot Issues
- **No SSH access:** Check network cables and DHCP
- **Web interface unreachable:** Try `http://192.168.100.1:8080`
- **SD card issues:** Use high-quality Class 10+ SD card
- **Power issues:** Use official Raspberry Pi power supply

### Network Issues
```bash
# Check interface status
ip link show
ip addr show

# Check gateway service
systemctl status gateway-manager
journalctl -u gateway-manager -f

# Check firewall rules
sudo iptables -L -n
```

### Reset to Factory
```bash
# Remove first boot completion flag
sudo rm /var/lib/gateway/.firstboot-complete

# Reboot for first boot setup
sudo reboot
```

## Development

### Contributing
1. Fork the repository
2. Create feature branch
3. Test on real hardware
4. Submit pull request

### Testing
```bash
# Build test image
./scripts/build-rpi-image.sh --target rpi4

# Deploy to test hardware
sudo dd if=images/gateway-os-*.img.xz of=/dev/sdX

# Test functionality
- Network connectivity
- VPN connection
- Web interface
- SSH access
```

## Support

### Documentation
- [User Manual](docs/USER_MANUAL.md)
- [API Reference](docs/API.md)
- [Troubleshooting](docs/TROUBLESHOOTING.md)

### Community
- GitHub Issues: Report bugs and feature requests
- Discussions: Community support and questions
- Wiki: Community documentation

### Commercial Support
For commercial deployments and custom requirements, contact the development team.

## License

Gateway OS is released under the MIT License. See LICENSE file for details.

---

**Note:** This is a complete operating system. Flashing the image will erase all data on the target device. Always backup important data before installation.