#!/bin/bash
# Universeller Gateway-Installer mit automatischer Hardware-Erkennung
# Funktioniert auf Raspberry Pi, Mini-PCs, VPS und Standard-Linux-Systemen

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

# Logging
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_step() { echo -e "${PURPLE}🔧 $1${NC}"; }

# Globale Variablen
HARDWARE_TYPE=""
SYSTEM_MEMORY=""
CPU_CORES=""
INSTALL_TYPE=""
GATEWAY_ID=""

# Hardware-Erkennung
detect_hardware() {
    log_step "Hardware-Typ erkennen..."
    
    # Raspberry Pi
    if grep -qi "raspberry\|bcm" /proc/cpuinfo 2>/dev/null; then
        HARDWARE_TYPE="raspberry_pi"
        log_info "Raspberry Pi erkannt"
        return
    fi
    
    # VPS (virtualisierte Umgebung mit wenig RAM)
    SYSTEM_MEMORY=$(free -m | awk 'NR==2{print $2}')
    CPU_CORES=$(nproc)
    
    if [ "$SYSTEM_MEMORY" -le 2048 ] && grep -qi "virtual\|kvm\|xen\|vmware" /proc/cpuinfo 2>/dev/null; then
        HARDWARE_TYPE="vps"
        log_info "VPS-System erkannt (${SYSTEM_MEMORY}MB RAM, ${CPU_CORES} CPUs)"
        return
    fi
    
    # Mini-PC / Standard-Hardware
    if [ "$SYSTEM_MEMORY" -ge 1024 ] && [ "$CPU_CORES" -ge 2 ]; then
        HARDWARE_TYPE="mini_pc"
        log_info "Mini-PC/Standard-Hardware erkannt (${SYSTEM_MEMORY}MB RAM, ${CPU_CORES} CPUs)"
        return
    fi
    
    # Fallback
    HARDWARE_TYPE="unknown"
    log_warning "Hardware-Typ unbekannt - verwende Standard-Konfiguration"
}

# Installations-Typ bestimmen
determine_install_type() {
    log_step "Installations-Typ bestimmen..."
    
    echo ""
    echo "Welcher System-Typ soll installiert werden?"
    echo "1) VPS Server (zentrale Verwaltung, öffentliche IP)"
    echo "2) Gateway (lokaler Router/Gateway für Server-Netzwerk)"
    echo "3) Automatische Erkennung"
    echo ""
    
    read -p "Auswahl [1-3]: " choice
    
    case "$choice" in
        1)
            INSTALL_TYPE="vps"
            log_info "VPS Server Installation gewählt"
            ;;
        2)
            INSTALL_TYPE="gateway"
            log_info "Gateway Installation gewählt"
            ;;
        3)
            # Automatische Erkennung basierend auf Hardware und Netzwerk
            if [ "$HARDWARE_TYPE" = "vps" ] || curl -s --connect-timeout 5 ifconfig.me >/dev/null 2>&1; then
                INSTALL_TYPE="vps"
                log_info "VPS Server automatisch erkannt (öffentliche IP verfügbar)"
            else
                INSTALL_TYPE="gateway"
                log_info "Gateway automatisch erkannt (lokales Netzwerk)"
            fi
            ;;
        *)
            log_error "Ungültige Auswahl"
            determine_install_type
            ;;
    esac
}

# System-Vorbereitung
prepare_system() {
    log_step "System vorbereiten..."
    
    # Root-Check
    if [ "$EUID" -ne 0 ]; then
        log_error "Bitte als root ausführen: sudo $0"
        exit 1
    fi
    
    # System aktualisieren
    log_info "System-Updates installieren..."
    apt update >/dev/null 2>&1
    apt upgrade -y >/dev/null 2>&1
    
    # Basis-Pakete installieren
    log_info "Basis-Pakete installieren..."
    apt install -y curl wget git python3 python3-pip python3-venv \
                   wireguard-tools iptables-persistent \
                   htop nano vim sudo systemd >/dev/null 2>&1
    
    # Hardware-spezifische Pakete
    case "$HARDWARE_TYPE" in
        "raspberry_pi")
            apt install -y python3-psutil python3-requests python3-tk \
                           raspi-config rpi-update >/dev/null 2>&1 || true
            log_success "Raspberry Pi Pakete installiert"
            ;;
        "vps")
            apt install -y python3-psutil python3-requests \
                           ufw fail2ban >/dev/null 2>&1 || true
            log_success "VPS Pakete installiert"
            ;;
        *)
            apt install -y python3-psutil python3-requests python3-tk >/dev/null 2>&1 || true
            ;;
    esac
    
    log_success "System vorbereitet"
}

# Gateway-ID generieren
generate_gateway_id() {
    # Eindeutige Gateway-ID basierend auf MAC-Adresse
    local primary_mac=$(ip link show | grep -A1 "state UP" | grep "link/ether" | head -1 | awk '{print $2}' | tr -d ':')
    local hostname=$(hostname)
    
    GATEWAY_ID="gateway-${hostname}-${primary_mac:8}"
    log_info "Gateway-ID: $GATEWAY_ID"
}

# VPS Installation
install_vps() {
    log_step "VPS Server installieren..."
    
    # Arbeitsverzeichnis erstellen
    local install_dir="/opt/siteconnector-vps"
    mkdir -p "$install_dir"
    cd "$install_dir"
    
    # Code herunterladen
    log_info "Code herunterladen..."
    if ! git clone https://github.com/cryptofluffy/gateway-project.git /tmp/gateway-install; then
        log_error "Code-Download fehlgeschlagen"
        exit 1
    fi
    
    # VPS-Code installieren
    cp /tmp/gateway-install/vps-server/*.py .
    cp -r /tmp/gateway-install/vps-server/static .
    cp -r /tmp/gateway-install/vps-server/templates .
    cp /tmp/gateway-install/vps-server/requirements.txt .
    
    # Virtual Environment erstellen
    log_info "Python Virtual Environment erstellen..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip >/dev/null 2>&1
    ./venv/bin/pip install -r requirements.txt >/dev/null 2>&1
    
    # WireGuard Keys generieren
    log_info "WireGuard Keys generieren..."
    mkdir -p /etc/wireguard
    
    local private_key=$(wg genkey)
    local public_key=$(echo "$private_key" | wg pubkey)
    
    echo "$private_key" > /etc/wireguard/server_private.key
    echo "$public_key" > /etc/wireguard/server_public.key
    chmod 600 /etc/wireguard/server_private.key
    chmod 644 /etc/wireguard/server_public.key
    
    # WireGuard Konfiguration erstellen
    cat > /etc/wireguard/wg0.conf << EOF
[Interface]
PrivateKey = $private_key
Address = 10.8.0.1/24
ListenPort = 51820
SaveConfig = false

# IP-Forwarding aktivieren
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

# Gateways werden automatisch hinzugefügt
EOF
    
    # Systemd-Service erstellen
    create_vps_service "$install_dir"
    
    # Firewall konfigurieren
    configure_vps_firewall
    
    # Services starten
    systemctl enable wg-quick@wg0
    systemctl start wg-quick@wg0
    systemctl enable siteconnector-vps
    systemctl start siteconnector-vps
    
    # VPS-Informationen anzeigen
    show_vps_info "$public_key"
    
    log_success "VPS Server Installation abgeschlossen"
}

# Gateway Installation
install_gateway() {
    log_step "Gateway installieren..."
    
    # Code herunterladen
    log_info "Code herunterladen..."
    if ! git clone https://github.com/cryptofluffy/gateway-project.git /tmp/gateway-install; then
        log_error "Code-Download fehlgeschlagen"
        exit 1
    fi
    
    # Gateway-Software installieren
    log_info "Gateway-Software installieren..."
    cp /tmp/gateway-install/gateway-software/*.py /usr/local/bin/
    cp /tmp/gateway-install/system_check.py /usr/local/bin/
    chmod +x /usr/local/bin/*.py
    
    # Befehle erstellen
    cat > /usr/local/bin/siteconnector-gateway << 'EOF'
#!/bin/bash
exec /usr/local/bin/gateway_manager.py "$@"
EOF
    chmod +x /usr/local/bin/siteconnector-gateway
    
    # DHCP-Server installieren
    log_info "DHCP-Server installieren..."
    apt install -y isc-dhcp-server >/dev/null 2>&1
    
    # Network Scanner installieren
    install_gateway_network_scanner
    
    # Systemd-Services erstellen
    create_gateway_services
    
    # Interface-Konfiguration
    configure_gateway_network
    
    # Services starten
    systemctl daemon-reload
    systemctl enable siteconnector-gateway
    systemctl enable siteconnector-monitoring
    systemctl enable network-scanner.timer
    systemctl start siteconnector-gateway
    systemctl start siteconnector-monitoring
    systemctl start network-scanner.timer
    
    # Gateway-Informationen anzeigen
    show_gateway_info
    
    log_success "Gateway Installation abgeschlossen"
}

# VPS Systemd Service
create_vps_service() {
    local install_dir="$1"
    
    cat > /etc/systemd/system/siteconnector-vps.service << EOF
[Unit]
Description=SiteConnector VPS Server
After=network.target wg-quick@wg0.service
Wants=wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=$install_dir
ExecStart=$install_dir/venv/bin/python $install_dir/run.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
StartLimitInterval=300
StartLimitBurst=3

# Hardware-spezifische Limits
$(case "$HARDWARE_TYPE" in
    "vps"|"raspberry_pi")
        echo "MemoryMax=512M"
        echo "CPUQuota=80%"
        ;;
    *)
        echo "MemoryMax=1G"
        echo "CPUQuota=100%"
        ;;
esac)

[Install]
WantedBy=multi-user.target
EOF
}

# VPS Firewall
configure_vps_firewall() {
    log_info "VPS Firewall konfigurieren..."
    
    # UFW konfigurieren (falls installiert)
    if which ufw >/dev/null 2>&1; then
        ufw --force reset >/dev/null 2>&1
        ufw default deny incoming >/dev/null 2>&1
        ufw default allow outgoing >/dev/null 2>&1
        ufw allow ssh >/dev/null 2>&1
        ufw allow 8080/tcp >/dev/null 2>&1
        ufw allow 51820/udp >/dev/null 2>&1
        ufw --force enable >/dev/null 2>&1
        log_success "UFW Firewall konfiguriert"
    fi
    
    # IP-Forwarding aktivieren
    echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
    sysctl -p >/dev/null 2>&1
}

# Gateway Services
create_gateway_services() {
    # Hauptservice
    cat > /etc/systemd/system/siteconnector-gateway.service << EOF
[Unit]
Description=SiteConnector Gateway Manager
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/gateway_manager.py monitor
Restart=on-failure
RestartSec=15
StartLimitInterval=300
StartLimitBurst=3

# Hardware-spezifische Limits
$(case "$HARDWARE_TYPE" in
    "raspberry_pi")
        echo "MemoryMax=256M"
        echo "CPUQuota=60%"
        ;;
    "vps")
        echo "MemoryMax=384M"
        echo "CPUQuota=70%"
        ;;
    *)
        echo "MemoryMax=512M"
        echo "CPUQuota=80%"
        ;;
esac)

[Install]
WantedBy=multi-user.target
EOF

    # Monitoring Service
    cat > /etc/systemd/system/siteconnector-monitoring.service << EOF
[Unit]
Description=SiteConnector Gateway Monitoring
After=network.target siteconnector-gateway.service
Wants=siteconnector-gateway.service

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/system_monitor.py
Restart=on-failure
RestartSec=30
StartLimitInterval=600
StartLimitBurst=3

# Ressourcen-Limits
MemoryMax=128M
CPUQuota=30%

[Install]
WantedBy=multi-user.target
EOF
}

# Gateway Network Scanner
install_gateway_network_scanner() {
    # Network Scanner Service
    cat > /etc/systemd/system/network-scanner.service << 'EOF'
[Unit]
Description=Network Scanner for Gateway Devices
After=network.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/local/bin/network-scanner.py
StandardOutput=journal
StandardError=journal
TimeoutStartSec=60

[Install]
WantedBy=multi-user.target
EOF

    # Network Scanner Timer
    cat > /etc/systemd/system/network-scanner.timer << 'EOF'
[Unit]
Description=Run Network Scanner every 5 minutes
Requires=network-scanner.service

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Unit=network-scanner.service

[Install]
WantedBy=timers.target
EOF
}

# Gateway Netzwerk-Konfiguration
configure_gateway_network() {
    log_info "Gateway-Netzwerk konfigurieren..."
    
    # Verfügbare Interfaces ermitteln
    local interfaces=($(ip link show | grep "state UP\|state DOWN" | grep -v "LOOPBACK" | awk -F: '{print $2}' | tr -d ' '))
    
    log_info "Verfügbare Netzwerk-Interfaces:"
    for i in "${!interfaces[@]}"; do
        local iface="${interfaces[$i]}"
        local status=$(ip link show "$iface" | grep -o "state [A-Z]*" | cut -d' ' -f2)
        local ip=$(ip addr show "$iface" | grep "inet " | awk '{print $2}' | head -1)
        echo "  $((i+1))) $iface ($status) ${ip:-"Keine IP"}"
    done
    
    # Standard-Konfiguration basierend auf Hardware
    local default_wan="eth0"
    local default_lan="eth1"
    
    if [ "$HARDWARE_TYPE" = "raspberry_pi" ]; then
        # Raspberry Pi: WLAN für Internet, Ethernet für Server
        if [[ " ${interfaces[@]} " =~ " wlan0 " ]]; then
            default_wan="wlan0"
        fi
        if [[ " ${interfaces[@]} " =~ " eth0 " ]]; then
            default_lan="eth0"
        fi
    fi
    
    # Benutzer-Eingabe
    echo ""
    read -p "WAN-Interface (Internet-Verbindung) [$default_wan]: " wan_interface
    wan_interface=${wan_interface:-$default_wan}
    
    read -p "LAN-Interface (Server-Netzwerk) [$default_lan]: " lan_interface
    lan_interface=${lan_interface:-$default_lan}
    
    # DHCP-Konfiguration
    cat > /etc/default/isc-dhcp-server << EOF
INTERFACESv4="$lan_interface"
INTERFACESv6=""
EOF

    cat > /etc/dhcp/dhcpd.conf << EOF
# DHCP für Gateway LAN ($lan_interface)
default-lease-time 86400;
max-lease-time 172800;
authoritative;

option domain-name-servers 192.168.100.1, 8.8.8.8, 8.8.4.4;
option domain-name "gateway.local";

subnet 192.168.100.0 netmask 255.255.255.0 {
    range 192.168.100.50 192.168.100.200;
    option routers 192.168.100.1;
    option broadcast-address 192.168.100.255;
}
EOF

    # Interface konfigurieren
    ip addr flush dev "$lan_interface" 2>/dev/null || true
    ip addr add 192.168.100.1/24 dev "$lan_interface" 2>/dev/null || true
    ip link set "$lan_interface" up 2>/dev/null || true
    
    # Persistente Konfiguration
    cat > /etc/systemd/network/gateway-lan.network << EOF
[Match]
Name=$lan_interface

[Network]
Address=192.168.100.1/24
IPForward=yes
EOF
    
    systemctl enable systemd-networkd 2>/dev/null || true
    systemctl enable isc-dhcp-server 2>/dev/null || true
    systemctl start isc-dhcp-server 2>/dev/null || true
    
    log_success "Gateway-Netzwerk konfiguriert: WAN=$wan_interface, LAN=$lan_interface"
}

# VPS-Informationen anzeigen
show_vps_info() {
    local public_key="$1"
    local vps_ip=$(curl -s ifconfig.me 2>/dev/null || echo "UNBEKANNT")
    
    echo ""
    echo "=================================================="
    log_success "VPS SERVER INSTALLATION ABGESCHLOSSEN"
    echo "=================================================="
    echo ""
    log_info "VPS-Informationen:"
    echo "  🌐 Öffentliche IP: $vps_ip"
    echo "  🔑 Public Key: $public_key"
    echo "  📊 Dashboard: http://$vps_ip:8080"
    echo "  🔧 SSH Port: 22"
    echo ""
    log_info "Gateway Setup-Befehl:"
    echo "  sudo curl -s https://raw.githubusercontent.com/cryptofluffy/gateway-project/main/install-gateway.sh | bash"
    echo "  sudo siteconnector-gateway setup $vps_ip $public_key"
    echo ""
    log_info "Nützliche Befehle:"
    echo "  Status: systemctl status siteconnector-vps"
    echo "  Logs: journalctl -u siteconnector-vps -f"
    echo "  Update: sudo siteconnector-update"
    echo ""
}

# Gateway-Informationen anzeigen
show_gateway_info() {
    echo ""
    echo "=================================================="
    log_success "GATEWAY INSTALLATION ABGESCHLOSSEN"
    echo "=================================================="
    echo ""
    log_info "Gateway-Informationen:"
    echo "  🆔 Gateway-ID: $GATEWAY_ID"
    echo "  🌐 LAN-Netzwerk: 192.168.100.1/24"
    echo "  📡 DHCP-Bereich: 192.168.100.50-200"
    echo "  🔧 Hardware: $HARDWARE_TYPE"
    echo ""
    log_info "Nächste Schritte:"
    echo "  1. VPS-Verbindung konfigurieren:"
    echo "     sudo siteconnector-gateway setup <VPS_IP> <VPS_PUBLIC_KEY>"
    echo ""
    echo "  2. Server am LAN-Port anschließen"
    echo "  3. Gateway-Dashboard im VPS überprüfen"
    echo ""
    log_info "Nützliche Befehle:"
    echo "  Status: siteconnector-gateway status"
    echo "  GUI: python3 /usr/local/bin/gui_app.py"
    echo "  Diagnose: python3 /usr/local/bin/system_check.py"
    echo "  Update: sudo siteconnector-update"
    echo ""
}

# Hardware-spezifische Optimierungen
apply_hardware_optimizations() {
    log_step "Hardware-Optimierungen anwenden..."
    
    case "$HARDWARE_TYPE" in
        "raspberry_pi")
            # Raspberry Pi Optimierungen
            if [ -f "/boot/config.txt" ]; then
                # GPU Memory reduzieren
                if ! grep -q "gpu_mem=16" /boot/config.txt; then
                    echo "gpu_mem=16" >> /boot/config.txt
                fi
                
                # Overclock (konservativ)
                if ! grep -q "arm_freq=1000" /boot/config.txt; then
                    echo "arm_freq=1000" >> /boot/config.txt
                fi
                
                log_success "Raspberry Pi Optimierungen angewendet"
            fi
            ;;
            
        "vps")
            # VPS Optimierungen
            cat >> /etc/sysctl.conf << EOF

# VPS Optimierungen
net.core.rmem_max=16777216
net.core.wmem_max=16777216
vm.swappiness=10
EOF
            sysctl -p >/dev/null 2>&1
            log_success "VPS Optimierungen angewendet"
            ;;
    esac
}

# Cleanup
cleanup() {
    rm -rf /tmp/gateway-install
    log_success "Temporäre Dateien bereinigt"
}

# Hauptfunktion
main() {
    echo "🚀 SITECONNECTOR GATEWAY INSTALLER"
    echo "=================================="
    echo ""
    
    detect_hardware
    determine_install_type
    prepare_system
    
    if [ "$INSTALL_TYPE" = "gateway" ]; then
        generate_gateway_id
    fi
    
    apply_hardware_optimizations
    
    if [ "$INSTALL_TYPE" = "vps" ]; then
        install_vps
    else
        install_gateway
    fi
    
    cleanup
    
    echo ""
    log_success "Installation erfolgreich abgeschlossen!"
    echo ""
    
    # Neustart empfehlen bei Hardware-Optimierungen
    if [ "$HARDWARE_TYPE" = "raspberry_pi" ]; then
        log_warning "Neustart empfohlen für Raspberry Pi Optimierungen: sudo reboot"
    fi
}

# Script ausführen
main "$@"