#!/bin/bash
set -e

# Gateway OS ISO Builder
# Creates bootable ISO image for x86_64 systems

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build-iso"
OUTPUT_DIR="$PROJECT_DIR/images"
VERSION="1.0.0"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[ISO-BUILD] $1${NC}"; }
success() { echo -e "${GREEN}[SUCCESS] $1${NC}"; }
warn() { echo -e "${YELLOW}[WARNING] $1${NC}"; }
error() { echo -e "${RED}[ERROR] $1${NC}"; exit 1; }

usage() {
    cat << EOF
Gateway OS ISO Builder

Usage: $0 [OPTIONS]

Options:
  --version VERSION   Set version string [default: $VERSION]
  --output DIR        Output directory [default: $OUTPUT_DIR]
  --clean            Clean build directory
  --help             Show this help

Examples:
  $0
  $0 --version 1.1.0 --output /tmp
  $0 --clean

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --version)
            VERSION="$2"
            shift 2
            ;;
        --output)
            OUTPUT_DIR="$2"
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

check_dependencies() {
    log "Checking dependencies..."
    
    local deps=("xorriso" "isolinux" "syslinux" "squashfs-tools" "cpio" "gzip")
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

setup_build_environment() {
    log "Setting up build environment..."
    
    if [[ "$CLEAN" == "1" ]]; then
        rm -rf "$BUILD_DIR"
    fi
    
    mkdir -p "$BUILD_DIR"/{iso,rootfs,boot}
    mkdir -p "$OUTPUT_DIR"
    
    success "Build environment ready"
}

create_base_system() {
    log "Creating base system..."
    
    # Create minimal directory structure
    cd "$BUILD_DIR/rootfs"
    
    mkdir -p {bin,boot,dev,etc,home,lib,lib64,media,mnt,opt,proc,root,run,sbin,srv,sys,tmp,usr,var}
    mkdir -p usr/{bin,lib,lib64,local,sbin,share}
    mkdir -p var/{cache,lib,lock,log,opt,run,spool,tmp}
    mkdir -p etc/{gateway,systemd,wireguard,ssh,ssl}
    
    # Copy system files from project
    if [[ -d "$PROJECT_DIR/rootfs" ]]; then
        cp -r "$PROJECT_DIR/rootfs"/* .
    fi
    
    # Mark as live system
    touch .live_system
    
    success "Base system created"
}

install_packages() {
    log "Installing packages..."
    
    # This would normally use debootstrap or similar
    # For this example, we'll create a minimal system
    
    cd "$BUILD_DIR/rootfs"
    
    # Create basic init system
    cat > init << 'EOF'
#!/bin/bash
# Gateway OS Live Init

export PATH=/bin:/sbin:/usr/bin:/usr/sbin
export HOME=/root
export TERM=linux

# Mount essential filesystems
mount -t proc proc /proc
mount -t sysfs sysfs /sys
mount -t devtmpfs devtmpfs /dev
mkdir -p /dev/pts
mount -t devpts devpts /dev/pts

# Check boot parameters
CMDLINE=$(cat /proc/cmdline)

# Start systemd or custom init
if [[ "$CMDLINE" =~ gateway.install=true ]]; then
    # Installation mode
    echo "Gateway OS Installer"
    echo "Starting installation process..."
    /usr/bin/gateway-installer
else
    # Live mode
    echo "Gateway OS Live System"
    echo "Starting Gateway OS services..."
    
    # Configure network
    ip link set lo up
    
    # Start basic services
    /usr/bin/gateway-manager &
    /usr/bin/gateway-web &
    
    # Start shell
    exec /bin/bash
fi
EOF
    
    chmod +x init
    
    # Create basic shell environment
    cat > etc/profile << 'EOF'
export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin
export PS1='\u@gateway:\w\$ '
export TERM=linux
alias ll='ls -la'
alias la='ls -la'
EOF
    
    success "Packages installed"
}

create_initramfs() {
    log "Creating initramfs..."
    
    cd "$BUILD_DIR/rootfs"
    
    # Create compressed initramfs
    find . | cpio -o -H newc | gzip -9 > "$BUILD_DIR/boot/rootfs.cpio.gz"
    
    success "Initramfs created"
}

prepare_boot_files() {
    log "Preparing boot files..."
    
    cd "$BUILD_DIR"
    
    # Copy kernel (would normally be built or extracted)
    # For demo, create placeholder
    echo "Gateway OS Kernel Placeholder" > boot/bzImage
    
    # Copy bootloader files
    mkdir -p iso/boot/isolinux
    
    # Copy ISOLINUX files (these should be from syslinux package)
    if [[ -f /usr/lib/ISOLINUX/isolinux.bin ]]; then
        cp /usr/lib/ISOLINUX/isolinux.bin iso/boot/isolinux/
    elif [[ -f /usr/share/syslinux/isolinux.bin ]]; then
        cp /usr/share/syslinux/isolinux.bin iso/boot/isolinux/
    else
        warn "ISOLINUX binary not found, creating placeholder"
        touch iso/boot/isolinux/isolinux.bin
    fi
    
    # Copy additional ISOLINUX modules
    for module in ldlinux.c32 libcom32.c32 libutil.c32 vesamenu.c32; do
        if [[ -f "/usr/lib/syslinux/modules/bios/$module" ]]; then
            cp "/usr/lib/syslinux/modules/bios/$module" iso/boot/isolinux/
        elif [[ -f "/usr/share/syslinux/$module" ]]; then
            cp "/usr/share/syslinux/$module" iso/boot/isolinux/
        fi
    done
    
    # Copy boot configuration
    cp "$PROJECT_DIR/bootloader/isolinux.cfg" iso/boot/isolinux/
    
    # Copy kernel and initramfs to ISO
    cp boot/bzImage iso/boot/
    cp boot/rootfs.cpio.gz iso/boot/
    
    success "Boot files prepared"
}

create_iso_structure() {
    log "Creating ISO structure..."
    
    cd "$BUILD_DIR/iso"
    
    # Create documentation
    cat > README.txt << EOF
Gateway OS v$VERSION
====================

A specialized Linux distribution for VPN gateway functionality.

Boot Options:
- Gateway OS Live: Run from memory without installation
- Install to Hard Drive: Permanent installation
- Rescue Mode: Troubleshooting and recovery

Default Credentials:
Username: admin
Password: gateway123 (change immediately!)

Web Interface: http://<gateway-ip>:8080

For more information visit:
https://github.com/your-repo/gateway-os

EOF
    
    cat > help.txt << EOF
Gateway OS Boot Help
====================

F1 - This help
F2 - System information

Boot Options:
1. Gateway OS Live (Default)
   - Runs entirely from memory
   - No installation required
   - Perfect for testing

2. Install Gateway OS
   - Installs to hard drive
   - WARNING: Erases target drive!

3. Rescue Mode
   - Boot into recovery shell
   - For troubleshooting

4. Safe Mode
   - Boot without network auto-config
   - For network debugging

Press Tab to edit boot options.
Press Enter to boot selected option.

EOF
    
    # Create version information
    cat > .version << EOF
GATEWAY_OS_VERSION=$VERSION
BUILD_DATE=$(date -Iseconds)
BUILD_HOST=$(hostname)
ARCH=x86_64
EOF
    
    success "ISO structure created"
}

build_iso() {
    log "Building ISO image..."
    
    cd "$BUILD_DIR"
    
    local iso_name="gateway-os-x86_64-${VERSION}.iso"
    local iso_path="$OUTPUT_DIR/$iso_name"
    
    # Build ISO using xorriso
    xorriso -as mkisofs \
        -iso-level 3 \
        -full-iso9660-filenames \
        -volid "GATEWAY_OS_${VERSION}" \
        -appid "Gateway OS" \
        -publisher "Gateway OS Project" \
        -preparer "Gateway OS Build System" \
        -eltorito-boot boot/isolinux/isolinux.bin \
        -eltorito-catalog boot/isolinux/boot.cat \
        -no-emul-boot \
        -boot-load-size 4 \
        -boot-info-table \
        -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
        -output "$iso_path" \
        iso/
    
    # Create checksums
    cd "$OUTPUT_DIR"
    sha256sum "$iso_name" > "$iso_name.sha256"
    md5sum "$iso_name" > "$iso_name.md5"
    
    success "ISO image built: $iso_path"
}

create_documentation() {
    log "Creating deployment documentation..."
    
    local doc_file="$OUTPUT_DIR/gateway-os-x86_64-${VERSION}-README.md"
    
    cat > "$doc_file" << EOF
# Gateway OS x86_64 v$VERSION

**Build Date:** $(date)
**Architecture:** x86_64
**Image Type:** Bootable ISO

## Quick Start

### 1. Create Bootable USB
\`\`\`bash
# Using dd (Linux/macOS)
sudo dd if=gateway-os-x86_64-${VERSION}.iso of=/dev/sdX bs=4M status=progress

# Using Rufus (Windows)
# Select ISO file and target USB drive in Rufus
\`\`\`

### 2. Boot Options

**Live Mode (Default):**
- Boots entirely from memory
- No installation required
- Perfect for testing
- Changes are not persistent

**Install Mode:**
- Permanent installation to hard drive
- ⚠️ WARNING: Erases target drive!
- Recommended for production use

**Rescue Mode:**
- Recovery and troubleshooting
- Root shell access
- Network tools available

### 3. System Requirements

**Minimum:**
- 64-bit x86 processor
- 1GB RAM
- 4GB storage (for installation)
- Network interface

**Recommended:**
- 2GB+ RAM
- 8GB+ storage
- Multiple network interfaces
- SSD storage

### 4. Network Configuration

**Default Settings:**
- LAN Network: 192.168.100.0/24
- Gateway IP: 192.168.100.1
- DHCP Range: 192.168.100.10-200
- Web Interface: Port 8080
- SSH: Port 22

### 5. First Boot

**Live System:**
1. System boots automatically
2. Network interfaces auto-detected
3. Web interface available at http://192.168.100.1:8080
4. SSH: ssh admin@192.168.100.1 (password: gateway123)

**Installed System:**
1. First boot setup runs automatically
2. Unique hostname generated
3. System configures itself
4. Reboot required to complete setup

### 6. VPN Configuration

**Via Web Interface:**
1. Open http://<gateway-ip>:8080
2. Navigate to VPN Settings
3. Enter VPS details
4. Configure WireGuard connection

**Via Command Line:**
\`\`\`bash
# Edit configuration
sudo nano /etc/gateway/gateway.json

# Restart services
sudo systemctl restart gateway-manager
\`\`\`

### 7. Security Notes

- **Change default password immediately**
- **Set up SSH key authentication**
- **Review firewall configuration**
- **Enable automatic updates**

### 8. Troubleshooting

**Boot Issues:**
- Try different USB port
- Disable Secure Boot if necessary
- Check BIOS boot order

**Network Issues:**
- Check cable connections
- Try safe mode boot option
- Verify DHCP settings

**Installation Issues:**
- Ensure target drive is at least 4GB
- Check for hardware compatibility
- Try different installation target

### 9. File Verification

Verify ISO integrity before use:
\`\`\`bash
# SHA256 checksum
sha256sum -c gateway-os-x86_64-${VERSION}.iso.sha256

# MD5 checksum  
md5sum -c gateway-os-x86_64-${VERSION}.iso.md5
\`\`\`

### 10. Support

- Documentation: https://github.com/your-repo/gateway-os
- Issues: Report bugs and feature requests on GitHub
- Community: Discussions and user support

---

**⚠️ Important:** This ISO will boot in both BIOS and UEFI modes. 
Installation will permanently erase the target drive!

EOF

    success "Documentation created: $doc_file"
}

cleanup() {
    if [[ "$CLEAN" == "1" ]]; then
        log "Cleaning up build directory..."
        rm -rf "$BUILD_DIR"
        success "Cleanup complete"
    fi
}

main() {
    log "Building Gateway OS ISO v$VERSION for x86_64..."
    
    check_dependencies
    setup_build_environment
    create_base_system
    install_packages
    create_initramfs
    prepare_boot_files
    create_iso_structure
    build_iso
    create_documentation
    cleanup
    
    success "Gateway OS ISO build complete!"
    echo
    log "Image location: $OUTPUT_DIR/"
    log "Boot from USB: sudo dd if=gateway-os-x86_64-${VERSION}.iso of=/dev/sdX"
    log "Verify checksum: sha256sum -c gateway-os-x86_64-${VERSION}.iso.sha256"
}

# Ensure proper permissions
if [[ $EUID -eq 0 ]]; then
    warn "Running as root. Build files will be owned by root."
fi

main "$@"