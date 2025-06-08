# Gateway OS - Custom Linux Distribution

A specialized Linux distribution optimized for VPN gateway functionality, designed to run on Raspberry Pi and similar ARM/x86 devices.

## Features

- **Zero-touch deployment**: Automatic VPN gateway setup on first boot
- **Minimal footprint**: Optimized for embedded systems
- **Secure by default**: Hardened security configuration
- **Auto-update**: Automatic security and feature updates
- **Hardware support**: Raspberry Pi 3/4/5, x86_64 systems
- **Web management**: Built-in web interface for configuration

## Architecture

```
gateway-os/
├── build/              # Build system and scripts
├── rootfs/            # Root filesystem overlay
├── kernel/            # Custom kernel configuration
├── bootloader/        # Boot configuration
├── services/          # System services
├── configs/           # System configurations
├── scripts/           # Utility scripts
└── images/            # Built OS images
```

## Quick Start

1. Build the OS image:
   ```bash
   sudo ./build/build-image.sh --target rpi4
   ```

2. Flash to SD card:
   ```bash
   sudo dd if=images/gateway-os-rpi4.img of=/dev/sdX bs=4M status=progress
   ```

3. Insert SD card and boot device

## Supported Hardware

- Raspberry Pi 3B/3B+
- Raspberry Pi 4B (1GB/2GB/4GB/8GB)
- Raspberry Pi 5 (4GB/8GB)
- Generic x86_64 systems
- ARM64 development boards

## Security Features

- Read-only root filesystem
- Automatic security updates
- Firewall preconfigured
- SSH key-only authentication
- Fail2ban protection
- SELinux/AppArmor support

## Development

Built on Buildroot with custom packages and configurations for optimal VPN gateway performance.