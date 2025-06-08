#!/bin/bash
set -e

# Gateway OS Image Builder
# Builds custom Linux distribution for VPN gateway appliances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build-output"
IMAGES_DIR="$PROJECT_DIR/images"

# Default values
TARGET=""
VERSION="1.0.0"
ARCH=""
KERNEL_VERSION="6.6"
BUILDROOT_VERSION="2024.02"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[SUCCESS] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

usage() {
    cat << EOF
Gateway OS Image Builder

Usage: $0 --target TARGET [OPTIONS]

Targets:
  rpi3         Raspberry Pi 3B/3B+
  rpi4         Raspberry Pi 4B
  rpi5         Raspberry Pi 5
  x86_64       Generic x86_64 system
  aarch64      Generic ARM64 system

Options:
  --version VERSION    OS version (default: $VERSION)
  --kernel VERSION     Kernel version (default: $KERNEL_VERSION)
  --clean             Clean build directory
  --help              Show this help

Examples:
  $0 --target rpi4
  $0 --target x86_64 --version 1.1.0
  $0 --target rpi4 --clean

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --target)
                TARGET="$2"
                shift 2
                ;;
            --version)
                VERSION="$2"
                shift 2
                ;;
            --kernel)
                KERNEL_VERSION="$2"
                shift 2
                ;;
            --clean)
                CLEAN=1
                shift
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

    if [[ -z "$TARGET" ]]; then
        error "Target is required. Use --target to specify."
    fi

    case "$TARGET" in
        rpi3|rpi4|rpi5)
            ARCH="aarch64"
            ;;
        x86_64)
            ARCH="x86_64"
            ;;
        aarch64)
            ARCH="aarch64"
            ;;
        *)
            error "Unknown target: $TARGET"
            ;;
    esac
}

check_dependencies() {
    log "Checking build dependencies..."
    
    local deps=("wget" "git" "make" "gcc" "g++" "unzip" "rsync" "cpio" "bc" "file")
    local missing=()
    
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        fi
    done
    
    if [[ ${#missing[@]} -gt 0 ]]; then
        error "Missing dependencies: ${missing[*]}"
    fi
    
    success "All dependencies satisfied"
}

setup_buildroot() {
    log "Setting up Buildroot..."
    
    local buildroot_dir="$BUILD_DIR/buildroot-$BUILDROOT_VERSION"
    
    if [[ ! -d "$buildroot_dir" ]]; then
        log "Downloading Buildroot $BUILDROOT_VERSION..."
        mkdir -p "$BUILD_DIR"
        cd "$BUILD_DIR"
        
        wget -O "buildroot-$BUILDROOT_VERSION.tar.gz" \
            "https://buildroot.org/downloads/buildroot-$BUILDROOT_VERSION.tar.gz"
        
        tar -xzf "buildroot-$BUILDROOT_VERSION.tar.gz"
        rm "buildroot-$BUILDROOT_VERSION.tar.gz"
    fi
    
    cd "$buildroot_dir"
    
    # Copy our custom configuration
    cp "$SCRIPT_DIR/configs/gateway-${TARGET}_defconfig" configs/
    
    success "Buildroot setup complete"
}

configure_buildroot() {
    log "Configuring Buildroot for $TARGET..."
    
    cd "$BUILD_DIR/buildroot-$BUILDROOT_VERSION"
    
    # Load our configuration
    make "gateway-${TARGET}_defconfig"
    
    # Apply any custom patches
    if [[ -d "$SCRIPT_DIR/patches" ]]; then
        log "Applying custom patches..."
        for patch in "$SCRIPT_DIR/patches"/*.patch; do
            if [[ -f "$patch" ]]; then
                log "Applying $(basename "$patch")"
                patch -p1 < "$patch"
            fi
        done
    fi
    
    success "Configuration complete"
}

build_image() {
    log "Building Gateway OS image for $TARGET..."
    
    cd "$BUILD_DIR/buildroot-$BUILDROOT_VERSION"
    
    # Set build environment
    export BR2_JLEVEL=$(nproc)
    
    # Start build
    log "Starting build (this may take 30-60 minutes)..."
    make
    
    success "Build complete"
}

create_final_image() {
    log "Creating final image..."
    
    local buildroot_dir="$BUILD_DIR/buildroot-$BUILDROOT_VERSION"
    local output_dir="$buildroot_dir/output"
    local image_name="gateway-os-${TARGET}-${VERSION}.img"
    
    mkdir -p "$IMAGES_DIR"
    
    case "$TARGET" in
        rpi3|rpi4|rpi5)
            # For Raspberry Pi, use the generated SD card image
            if [[ -f "$output_dir/images/sdcard.img" ]]; then
                cp "$output_dir/images/sdcard.img" "$IMAGES_DIR/$image_name"
            else
                error "SD card image not found"
            fi
            ;;
        x86_64|aarch64)
            # For generic systems, create ISO image
            if [[ -f "$output_dir/images/rootfs.iso9660" ]]; then
                cp "$output_dir/images/rootfs.iso9660" "$IMAGES_DIR/${image_name%.img}.iso"
                image_name="${image_name%.img}.iso"
            else
                error "ISO image not found"
            fi
            ;;
    esac
    
    # Create checksums
    cd "$IMAGES_DIR"
    sha256sum "$image_name" > "${image_name}.sha256"
    
    success "Final image created: $IMAGES_DIR/$image_name"
}

create_documentation() {
    log "Creating deployment documentation..."
    
    local doc_file="$IMAGES_DIR/gateway-os-${TARGET}-${VERSION}-deployment.md"
    
    cat > "$doc_file" << EOF
# Gateway OS Deployment Guide

**Target:** $TARGET
**Version:** $VERSION
**Build Date:** $(date)
**Architecture:** $ARCH

## Quick Deployment

EOF

    case "$TARGET" in
        rpi3|rpi4|rpi5)
            cat >> "$doc_file" << EOF
### Raspberry Pi Deployment

1. **Flash to SD Card:**
   \`\`\`bash
   sudo dd if=gateway-os-${TARGET}-${VERSION}.img of=/dev/sdX bs=4M status=progress
   sync
   \`\`\`

2. **Insert SD card and power on**

3. **Initial Setup:**
   - Default login: \`admin\` / \`gateway123\` (change immediately)
   - Web interface: \`http://gateway-ip:8080\`
   - SSH: \`ssh admin@gateway-ip\`

### Network Configuration

The gateway will automatically:
- Detect WAN interface (internet connection)
- Configure LAN interface (192.168.100.1/24)
- Start VPN services
- Enable DHCP for connected devices

EOF
            ;;
        x86_64|aarch64)
            cat >> "$doc_file" << EOF
### Generic System Deployment

1. **Boot from ISO:**
   - Burn ISO to USB/CD
   - Boot target system from media

2. **Install to Hard Drive:**
   \`\`\`bash
   sudo gateway-installer /dev/sda
   \`\`\`

3. **Reboot and configure**

EOF
            ;;
    esac
    
    cat >> "$doc_file" << EOF
## Security Notes

- **Change default passwords immediately**
- **Enable SSH key authentication**
- **Configure firewall rules**
- **Enable automatic updates**

## Support

For support and documentation visit:
https://github.com/your-repo/gateway-os

EOF

    success "Documentation created: $doc_file"
}

cleanup() {
    if [[ "$CLEAN" == "1" ]]; then
        log "Cleaning build directory..."
        rm -rf "$BUILD_DIR"
        success "Cleanup complete"
    fi
}

main() {
    parse_args "$@"
    
    log "Building Gateway OS $VERSION for $TARGET ($ARCH)"
    
    check_dependencies
    setup_buildroot
    configure_buildroot
    build_image
    create_final_image
    create_documentation
    cleanup
    
    success "Gateway OS build complete!"
    log "Image location: $IMAGES_DIR/"
    log "Flash with: sudo dd if=gateway-os-${TARGET}-${VERSION}.img of=/dev/sdX bs=4M status=progress"
}

# Ensure we're running as root for some operations
if [[ $EUID -ne 0 ]] && [[ "$1" != "--help" ]]; then
    warn "Some operations require root privileges. Consider running with sudo."
fi

main "$@"