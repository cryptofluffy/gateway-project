#!/bin/bash
set -e

# Quick Raspberry Pi Image Builder
# Simple script to build Gateway OS image for Raspberry Pi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Default configuration
TARGET="rpi4"
OUTPUT_DIR="$PROJECT_DIR/images"
TEMP_DIR="/tmp/gateway-os-build"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${BLUE}[BUILD] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }

usage() {
    cat << EOF
Quick Gateway OS Image Builder for Raspberry Pi

Usage: $0 [OPTIONS]

Options:
  --target TARGET     Target platform (rpi3, rpi4, rpi5) [default: rpi4]
  --output DIR        Output directory [default: $OUTPUT_DIR]
  --help              Show this help

Example:
  $0 --target rpi4

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --target)
            TARGET="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            ;;
    esac
done

# Validate target
case "$TARGET" in
    rpi3|rpi4|rpi5) ;;
    *) error "Unsupported target: $TARGET" ;;
esac

log "Building Gateway OS for $TARGET..."

# Create directories
mkdir -p "$OUTPUT_DIR"
mkdir -p "$TEMP_DIR"

# Download Raspberry Pi OS Lite base image
download_base_image() {
    log "Downloading Raspberry Pi OS Lite base image..."
    
    local base_url="https://downloads.raspberrypi.org/raspios_lite_arm64/images"
    local image_date="2024-03-15"  # Latest stable version
    local image_name="2024-03-15-raspios-bookworm-arm64-lite.img.xz"
    local image_url="$base_url/raspios_lite_arm64-$image_date/$image_name"
    
    cd "$TEMP_DIR"
    
    if [[ ! -f "$image_name" ]]; then
        log "Downloading base image..."
        wget -O "$image_name" "$image_url" || error "Failed to download base image"
    fi
    
    if [[ ! -f "base.img" ]]; then
        log "Extracting base image..."
        xz -dk "$image_name"
        mv "${image_name%.xz}" "base.img"
    fi
    
    success "Base image ready"
}

# Mount and customize the image
customize_image() {
    log "Customizing image for Gateway OS..."
    
    cd "$TEMP_DIR"
    
    # Create loop device
    local loop_device=$(sudo losetup -fP --show base.img)
    log "Using loop device: $loop_device"
    
    # Mount partitions
    mkdir -p rootfs boot
    sudo mount "${loop_device}p2" rootfs
    sudo mount "${loop_device}p1" boot
    
    # Copy our customizations
    log "Installing Gateway OS components..."
    
    # Copy root filesystem overlay
    if [[ -d "$PROJECT_DIR/rootfs" ]]; then
        sudo cp -r "$PROJECT_DIR/rootfs"/* rootfs/
    fi
    
    # Copy services
    sudo mkdir -p rootfs/usr/share/gateway/services
    sudo cp "$PROJECT_DIR/services"/*.service rootfs/usr/share/gateway/services/
    sudo cp "$PROJECT_DIR/services"/*.timer rootfs/usr/share/gateway/services/
    
    # Copy boot configuration
    sudo cp "$PROJECT_DIR/bootloader/config.txt" boot/
    
    # Enable SSH by default
    sudo touch boot/ssh
    
    # Create initial user setup
    echo 'admin:$6$rounds=656000$YourSaltHere$hashedpassword' | sudo tee rootfs/etc/userconf > /dev/null
    
    # Install additional packages via chroot
    log "Installing additional packages..."
    
    # Copy package installation script
    cat > install_packages.sh << 'EOF'
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y \
    wireguard-tools \
    iptables-persistent \
    dnsmasq \
    hostapd \
    fail2ban \
    python3-pip \
    python3-flask \
    nginx \
    systemd-resolved
    
# Clean up
apt-get autoremove -y
apt-get clean
rm -rf /var/lib/apt/lists/*
EOF
    
    chmod +x install_packages.sh
    sudo cp install_packages.sh rootfs/tmp/
    
    # Run package installation in chroot
    sudo chroot rootfs /tmp/install_packages.sh
    sudo rm rootfs/tmp/install_packages.sh
    
    # Enable services
    sudo chroot rootfs systemctl enable gateway-firstboot.service
    sudo chroot rootfs systemctl enable ssh
    sudo chroot rootfs systemctl enable systemd-networkd
    sudo chroot rootfs systemctl enable systemd-resolved
    
    # Cleanup and unmount
    sudo umount boot rootfs
    sudo losetup -d "$loop_device"
    
    success "Image customization complete"
}

# Create final image
create_final_image() {
    log "Creating final Gateway OS image..."
    
    local final_image="$OUTPUT_DIR/gateway-os-$TARGET-$(date +%Y%m%d).img"
    
    cp "$TEMP_DIR/base.img" "$final_image"
    
    # Compress image
    log "Compressing image..."
    xz -z -9 "$final_image"
    
    # Create checksums
    cd "$OUTPUT_DIR"
    sha256sum "$(basename "$final_image.xz")" > "$(basename "$final_image.xz").sha256"
    
    success "Final image created: $final_image.xz"
}

# Create deployment documentation
create_documentation() {
    local doc_file="$OUTPUT_DIR/gateway-os-$TARGET-deployment.md"
    
    cat > "$doc_file" << EOF
# Gateway OS Deployment Guide - $TARGET

**Build Date:** $(date)
**Target:** $TARGET

## Quick Start

1. **Flash to SD Card (4GB minimum):**
   \`\`\`bash
   sudo dd if=gateway-os-$TARGET-$(date +%Y%m%d).img.xz of=/dev/sdX bs=4M status=progress
   sync
   \`\`\`

2. **Insert SD card and power on Raspberry Pi**

3. **Wait for first boot setup (2-3 minutes)**

4. **Connect via SSH:**
   \`\`\`bash
   ssh admin@<gateway-ip>
   # Default password: gateway123 (change immediately!)
   \`\`\`

5. **Access web interface:**
   \`http://<gateway-ip>:8080\`

## Network Configuration

- **LAN Network:** 192.168.100.0/24
- **Gateway IP:** 192.168.100.1
- **DHCP Range:** 192.168.100.10-200
- **Web Interface:** Port 8080
- **SSH:** Port 22

## First Boot Process

The system automatically:
1. Generates unique hostname and SSH keys
2. Creates admin user with default password
3. Configures network interfaces
4. Sets up firewall rules
5. Enables gateway services
6. Reboots to apply changes

## Security Notes

- **Change default password immediately**
- **Set up SSH key authentication**
- **Review firewall configuration**
- **Enable automatic updates**

## VPN Configuration

Configure VPN via web interface:
1. Enter VPS IP address
2. Add VPS public key
3. Copy gateway public key to VPS
4. Enable VPN connection

## Hardware Requirements

- Raspberry Pi 3B+ or newer
- 4GB+ SD card (Class 10 recommended)
- Ethernet connection for WAN
- Optional: USB-Ethernet adapter for additional LAN ports

## Troubleshooting

- **No network:** Check Ethernet connections
- **Can't access web:** Try http://192.168.100.1:8080
- **SSH fails:** Ensure SSH is enabled and firewall allows port 22
- **Reset to defaults:** Hold boot button during power-on (if available)

For support: https://github.com/your-repo/gateway-os
EOF

    success "Documentation created: $doc_file"
}

# Cleanup
cleanup() {
    log "Cleaning up..."
    sudo rm -rf "$TEMP_DIR"
}

# Main execution
main() {
    log "Starting Gateway OS build for $TARGET"
    
    # Check dependencies
    command -v wget >/dev/null || error "wget not found"
    command -v xz >/dev/null || error "xz not found"
    
    # Build process
    download_base_image
    customize_image
    create_final_image
    create_documentation
    cleanup
    
    success "Gateway OS build complete!"
    log "Image location: $OUTPUT_DIR/"
    log "Flash with: sudo dd if=gateway-os-$TARGET-*.img.xz of=/dev/sdX bs=4M status=progress"
}

# Ensure running with proper permissions
if [[ $EUID -eq 0 ]]; then
    error "Don't run as root. Script will use sudo when needed."
fi

# Trap cleanup on exit
trap cleanup EXIT

main "$@"