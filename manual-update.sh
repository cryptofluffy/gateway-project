#!/bin/bash
# Manuelles Update-Script für WireGuard Gateway System
# Umfassende Reparatur und Diagnose mit detaillierter Fehlerbehandlung

set -e

# Farben für bessere Lesbarkeit
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging-Funktionen
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_step() {
    echo -e "${PURPLE}🔧 $1${NC}"
}

log_check() {
    echo -e "${CYAN}🔍 $1${NC}"
}

# Globale Variablen
BACKUP_DIR=""
SYSTEM_TYPE=""
ERRORS=()
WARNINGS=()
FIXES_APPLIED=()
START_TIME=$(date +%s)

# Fehler-Handling
handle_error() {
    local error_msg="$1"
    local exit_code=${2:-1}
    
    log_error "FEHLER: $error_msg"
    ERRORS+=("$error_msg")
    
    if [ "$exit_code" -ne 0 ]; then
        echo ""
        log_error "Update abgebrochen aufgrund kritischen Fehlers"
        show_summary
        exit $exit_code
    fi
}

# Warnung protokollieren
handle_warning() {
    local warning_msg="$1"
    log_warning "$warning_msg"
    WARNINGS+=("$warning_msg")
}

# Angewendete Korrekturen protokollieren
log_fix() {
    local fix_msg="$1"
    log_success "KORREKTUR: $fix_msg"
    FIXES_APPLIED+=("$fix_msg")
}

# System-Typ erkennen
detect_system_type() {
    log_check "System-Typ erkennen..."
    
    if [ -f "/opt/siteconnector-vps/app.py" ] || [ -f "/opt/wireguard-vps/app.py" ]; then
        SYSTEM_TYPE="vps"
        log_info "SiteConnector VPS erkannt"
    elif [ -f "/usr/local/bin/gateway_manager.py" ] || [ -f "/usr/local/bin/gateway-manager" ]; then
        SYSTEM_TYPE="gateway"
        log_info "SiteConnector Gateway erkannt"
    elif systemctl is-enabled wireguard-vps &>/dev/null; then
        SYSTEM_TYPE="vps"
        log_info "Legacy VPS Installation erkannt"
    elif systemctl is-enabled gateway-manager &>/dev/null; then
        SYSTEM_TYPE="gateway"
        log_info "Legacy Gateway Installation erkannt"
    elif [ -f "/etc/wireguard/gateway.conf" ]; then
        SYSTEM_TYPE="gateway"
        log_info "Gateway anhand WireGuard-Config erkannt"
    else
        if which wg &>/dev/null && ! [ -d "/opt/wireguard-vps" ]; then
            SYSTEM_TYPE="gateway"
            log_warning "Gateway anhand WireGuard-Installation erkannt (Fallback)"
        else
            handle_error "SiteConnector System nicht erkannt" 1
        fi
    fi
}

# Root-Berechtigung prüfen
check_root() {
    if [ "$EUID" -ne 0 ]; then
        handle_error "Bitte als root ausführen: sudo $0" 1
    fi
}

# System-Ressourcen prüfen
check_system_resources() {
    log_check "System-Ressourcen prüfen..."
    
    # Speicher prüfen
    local memory_mb=$(free -m | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$memory_mb" -gt 90 ]; then
        handle_warning "Hohe Speicherauslastung: ${memory_mb}%"
    fi
    
    # Festplatte prüfen
    local disk_usage=$(df / | awk 'NR==2{printf "%.0f", $3*100/$2}')
    if [ "$disk_usage" -gt 90 ]; then
        handle_warning "Hohe Festplattenauslastung: ${disk_usage}%"
    fi
    
    # Load Average prüfen
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_count=$(nproc)
    
    if (( $(echo "$load_avg > $cpu_count" | bc -l) )); then
        handle_warning "Hohe Systemlast: $load_avg (CPUs: $cpu_count)"
    fi
    
    log_success "System-Ressourcen: Speicher ${memory_mb}%, Disk ${disk_usage}%, Load ${load_avg}"
}

# Laufende Prozesse prüfen
check_running_processes() {
    log_check "Problematische Prozesse prüfen..."
    
    # Hung Prozesse finden
    local hung_processes=$(ps aux | awk '$8 ~ /D/ { print $2, $11 }' | grep -E "(gateway|wireguard|dhcp)" || true)
    if [ ! -z "$hung_processes" ]; then
        handle_warning "Hängende Prozesse gefunden:"
        echo "$hung_processes"
        
        # Versuche Prozesse zu beenden
        echo "$hung_processes" | while read pid cmd; do
            if [ ! -z "$pid" ]; then
                log_step "Beende hängenden Prozess: $cmd (PID: $pid)"
                kill -TERM "$pid" 2>/dev/null || true
                sleep 2
                kill -KILL "$pid" 2>/dev/null || true
                log_fix "Hängender Prozess beendet: $cmd"
            fi
        done
    fi
    
    # Infinite Loop Prozesse finden (hohe CPU-Last)
    local high_cpu_processes=$(ps aux --sort=-%cpu | head -10 | awk '$3 > 80 { print $2, $3, $11 }' | grep -E "(python|gateway|monitor)" || true)
    if [ ! -z "$high_cpu_processes" ]; then
        handle_warning "Prozesse mit hoher CPU-Last:"
        echo "$high_cpu_processes"
    fi
}

# Umfassendes Backup erstellen
create_comprehensive_backup() {
    log_step "Umfassendes System-Backup erstellen..."
    
    BACKUP_DIR="/var/backups/manual-update-$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # System-Konfiguration sichern
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        [ -d "/opt/siteconnector-vps" ] && cp -r /opt/siteconnector-vps "$BACKUP_DIR/" 2>/dev/null || true
        [ -d "/opt/wireguard-vps" ] && cp -r /opt/wireguard-vps "$BACKUP_DIR/" 2>/dev/null || true
    else
        [ -d "/etc/siteconnector" ] && cp -r /etc/siteconnector "$BACKUP_DIR/" 2>/dev/null || true
        [ -d "/etc/wireguard-gateway" ] && cp -r /etc/wireguard-gateway "$BACKUP_DIR/" 2>/dev/null || true
    fi
    
    # Allgemeine Konfigurationen
    [ -d "/etc/wireguard" ] && cp -r /etc/wireguard "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/dhcp" ] && cp -r /etc/dhcp "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/systemd/system" ] && cp /etc/systemd/system/*siteconnector* "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/systemd/system" ] && cp /etc/systemd/system/*gateway* "$BACKUP_DIR/" 2>/dev/null || true
    [ -d "/etc/systemd/system" ] && cp /etc/systemd/system/*wireguard* "$BACKUP_DIR/" 2>/dev/null || true
    
    # System-Status speichern
    ps aux > "$BACKUP_DIR/processes.txt"
    systemctl list-units --type=service > "$BACKUP_DIR/services.txt"
    ip addr show > "$BACKUP_DIR/interfaces.txt"
    ip route show > "$BACKUP_DIR/routes.txt"
    iptables -L -n > "$BACKUP_DIR/iptables.txt" 2>/dev/null || true
    
    log_success "Backup erstellt: $BACKUP_DIR"
}

# Services sicher stoppen
stop_services_safely() {
    log_step "Services sicher stoppen..."
    
    local services_to_stop=()
    
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        services_to_stop=("siteconnector-vps" "wireguard-vps")
    else
        services_to_stop=("siteconnector-gateway" "siteconnector-monitoring" "gateway-manager" "gateway-monitoring")
    fi
    
    for service in "${services_to_stop[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            log_info "Stoppe Service: $service"
            systemctl stop "$service" 2>/dev/null || handle_warning "Service $service konnte nicht gestoppt werden"
            
            # Warte bis Service wirklich gestoppt ist
            local timeout=10
            while systemctl is-active --quiet "$service" 2>/dev/null && [ $timeout -gt 0 ]; do
                sleep 1
                ((timeout--))
            done
            
            if systemctl is-active --quiet "$service" 2>/dev/null; then
                handle_warning "Service $service läuft noch - force kill"
                systemctl kill "$service" 2>/dev/null || true
            fi
            
            log_fix "Service gestoppt: $service"
        fi
    done
}

# Neuesten Code herunterladen
download_latest_code() {
    log_step "Neuesten Code herunterladen..."
    
    local temp_dir="/tmp/manual-update-$$"
    rm -rf "$temp_dir"
    
    if git clone https://github.com/cryptofluffy/gateway-project.git "$temp_dir" 2>/dev/null; then
        log_success "Code von GitHub heruntergeladen"
    else
        # Fallback: wget
        handle_warning "Git nicht verfügbar - verwende wget"
        mkdir -p "$temp_dir"
        if wget -q "https://github.com/cryptofluffy/gateway-project/archive/main.zip" -O "$temp_dir/main.zip"; then
            cd "$temp_dir"
            unzip -q main.zip
            mv gateway-project-main/* .
            rmdir gateway-project-main
            rm main.zip
            log_fix "Code per wget heruntergeladen"
        else
            handle_error "Code-Download fehlgeschlagen" 1
        fi
    fi
    
    echo "$temp_dir"
}

# VPS-spezifische Updates
update_vps_system() {
    local code_dir="$1"
    log_step "VPS-System aktualisieren..."
    
    # Zielverzeichnis bestimmen
    local vps_dir
    if [ -d "/opt/siteconnector-vps" ]; then
        vps_dir="/opt/siteconnector-vps"
    elif [ -d "/opt/wireguard-vps" ]; then
        vps_dir="/opt/wireguard-vps"
    else
        vps_dir="/opt/siteconnector-vps"
        mkdir -p "$vps_dir"
        log_fix "VPS-Verzeichnis erstellt: $vps_dir"
    fi
    
    cd "$vps_dir"
    
    # Virtual Environment erstellen/aktualisieren
    if [ ! -d "venv" ]; then
        log_info "Python Virtual Environment erstellen..."
        python3 -m venv venv
        log_fix "Virtual Environment erstellt"
    fi
    
    # Code aktualisieren
    log_info "VPS-Code aktualisieren..."
    cp "$code_dir/vps-server"/*.py . 2>/dev/null || true
    cp -r "$code_dir/vps-server/static"/* ./static/ 2>/dev/null || mkdir -p static
    cp -r "$code_dir/vps-server/templates"/* ./templates/ 2>/dev/null || mkdir -p templates
    cp "$code_dir/vps-server/requirements.txt" . 2>/dev/null || true
    
    # Neue Dateien installieren
    cp "$code_dir/vps-server/run.py" . 2>/dev/null || true
    
    # Python-Abhängigkeiten aktualisieren
    log_info "Python-Abhängigkeiten aktualisieren..."
    ./venv/bin/pip install --upgrade pip >/dev/null 2>&1
    if [ -f "requirements.txt" ]; then
        ./venv/bin/pip install -r requirements.txt >/dev/null 2>&1
        log_fix "Python-Abhängigkeiten aktualisiert"
    fi
    
    # Systemd-Service erstellen/aktualisieren
    create_vps_systemd_service "$vps_dir"
    
    # WireGuard Keys prüfen/erstellen
    ensure_wireguard_keys
    
    log_success "VPS-System aktualisiert"
}

# Gateway-spezifische Updates
update_gateway_system() {
    local code_dir="$1"
    log_step "Gateway-System aktualisieren..."
    
    # Python-Abhängigkeiten installieren
    log_info "Python-Abhängigkeiten installieren..."
    apt update >/dev/null 2>&1 || handle_warning "apt update fehlgeschlagen"
    apt install -y python3-psutil python3-requests python3-full python3-pip python3-tk >/dev/null 2>&1 || handle_warning "Python-Paket-Installation unvollständig"
    
    # Gateway-Software installieren
    log_info "Gateway-Software installieren..."
    
    # Kritische Dateien zuerst
    if [ -f "$code_dir/gateway-software/gateway_manager.py" ]; then
        cp "$code_dir/gateway-software/gateway_manager.py" /usr/local/bin/
        chmod +x /usr/local/bin/gateway_manager.py
        log_fix "gateway_manager.py installiert"
    else
        handle_error "gateway_manager.py nicht gefunden in $code_dir/gateway-software/"
    fi
    
    # Weitere Dateien
    local files=("system_monitor.py" "network-scanner.py" "gui_app.py")
    for file in "${files[@]}"; do
        if [ -f "$code_dir/gateway-software/$file" ]; then
            cp "$code_dir/gateway-software/$file" /usr/local/bin/
            chmod +x "/usr/local/bin/$file"
            log_fix "$file installiert"
        else
            handle_warning "$file nicht gefunden"
        fi
    done
    
    # System-Check Script installieren
    if [ -f "$code_dir/system_check.py" ]; then
        cp "$code_dir/system_check.py" /usr/local/bin/
        chmod +x /usr/local/bin/system_check.py
        log_fix "system_check.py installiert"
    fi
    
    # SiteConnector-Befehle erstellen
    create_gateway_commands
    
    # Systemd-Services erstellen
    create_gateway_systemd_services
    
    # DHCP-Server installieren und konfigurieren
    setup_dhcp_server
    
    # Network Scanner installieren
    install_network_scanner "$code_dir"
    
    log_success "Gateway-System aktualisiert"
}

# VPS Systemd Service erstellen
create_vps_systemd_service() {
    local vps_dir="$1"
    log_info "VPS Systemd-Service konfigurieren..."
    
    cat > /etc/systemd/system/siteconnector-vps.service << EOF
[Unit]
Description=SiteConnector VPS Server (Stabilisiert)
After=network.target wg-quick@wg0.service
Wants=wg-quick@wg0.service

[Service]
Type=simple
User=root
WorkingDirectory=$vps_dir
ExecStart=$vps_dir/venv/bin/python $vps_dir/run.py
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure
RestartSec=10
StartLimitInterval=300
StartLimitBurst=3
WatchdogSec=30

# Ressourcen-Limits für Stabilität
MemoryMax=512M
CPUQuota=80%

# Sicherheit
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$vps_dir /etc/wireguard /var/log

[Install]
WantedBy=multi-user.target
EOF
    
    # Backwards compatibility
    ln -sf /etc/systemd/system/siteconnector-vps.service /etc/systemd/system/wireguard-vps.service 2>/dev/null || true
    
    log_fix "VPS Systemd-Service erstellt"
}

# Gateway Befehle erstellen
create_gateway_commands() {
    log_info "Gateway-Befehle erstellen..."
    
    cat > /usr/local/bin/siteconnector-gateway << 'EOF'
#!/bin/bash
# SiteConnector Gateway Manager
exec /usr/local/bin/gateway_manager.py "$@"
EOF
    
    cat > /usr/local/bin/gateway-manager << 'EOF'
#!/bin/bash
# Legacy Gateway Manager (Compatibility)
exec /usr/local/bin/gateway_manager.py "$@"
EOF
    
    chmod +x /usr/local/bin/siteconnector-gateway
    chmod +x /usr/local/bin/gateway-manager
    
    log_fix "Gateway-Befehle erstellt"
}

# Gateway Systemd Services erstellen
create_gateway_systemd_services() {
    log_info "Gateway Systemd-Services konfigurieren..."
    
    # Hauptservice
    cat > /etc/systemd/system/siteconnector-gateway.service << EOF
[Unit]
Description=SiteConnector Gateway Manager (Stabilisiert)
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

# Ressourcen-Limits für Raspberry Pi
MemoryMax=256M
CPUQuota=60%

# Sicherheit
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/etc/wireguard-gateway /etc/wireguard /var/log /tmp

[Install]
WantedBy=multi-user.target
EOF
    
    # Monitoring Service
    cat > /etc/systemd/system/siteconnector-monitoring.service << EOF
[Unit]
Description=SiteConnector Gateway Monitoring (Stabilisiert)
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
    
    # Backwards compatibility
    ln -sf /etc/systemd/system/siteconnector-gateway.service /etc/systemd/system/gateway-manager.service 2>/dev/null || true
    ln -sf /etc/systemd/system/siteconnector-monitoring.service /etc/systemd/system/gateway-monitoring.service 2>/dev/null || true
    
    log_fix "Gateway Systemd-Services erstellt"
}

# DHCP-Server einrichten
setup_dhcp_server() {
    log_info "DHCP-Server konfigurieren..."
    
    # DHCP-Server installieren
    if ! dpkg -l | grep -q isc-dhcp-server; then
        apt install -y isc-dhcp-server >/dev/null 2>&1 || handle_warning "DHCP-Server Installation fehlgeschlagen"
    fi
    
    # Interface-Konfiguration über Gateway Manager
    if [ -f "/usr/local/bin/gateway_manager.py" ]; then
        log_info "Ermittle LAN-Interface über Gateway Manager..."
        
        python3 << 'EOF'
import sys
sys.path.append('/usr/local/bin')

try:
    from gateway_manager import WireGuardGateway
    gw = WireGuardGateway()
    
    # Hole tatsächlich konfigurierte Interfaces
    if hasattr(gw, 'get_actual_interfaces'):
        wan_iface, lan_iface = gw.get_actual_interfaces()
    else:
        wan_iface = getattr(gw, 'wan_interface', 'eth0')
        lan_iface = getattr(gw, 'lan_interface', 'eth1')
    
    print(f"WAN_INTERFACE={wan_iface}")
    print(f"LAN_INTERFACE={lan_iface}")
    
    # DHCP-Konfiguration schreiben
    with open('/etc/default/isc-dhcp-server', 'w') as f:
        f.write(f'INTERFACESv4="{lan_iface}"\n')
        f.write('INTERFACESv6=""\n')
    
    with open('/etc/dhcp/dhcpd.conf', 'w') as f:
        f.write(f'''# DHCP für Gateway LAN ({lan_iface}) - Dashboard-konfiguriert
default-lease-time 86400;
max-lease-time 172800;
authoritative;

option domain-name-servers 192.168.100.1, 8.8.8.8, 8.8.4.4;
option domain-name "gateway.local";

subnet 192.168.100.0 netmask 255.255.255.0 {{
    range 192.168.100.50 192.168.100.200;
    option routers 192.168.100.1;
    option broadcast-address 192.168.100.255;
}}
''')
    
    print("DHCP_CONFIG_SUCCESS=true")
    
except Exception as e:
    print(f"DHCP_CONFIG_ERROR={e}")
EOF
    else
        handle_warning "Gateway Manager nicht verfügbar - verwende Standard-DHCP-Konfiguration"
        
        # Fallback-Konfiguration
        cat > /etc/dhcp/dhcpd.conf << EOF
# Standard DHCP-Konfiguration
default-lease-time 86400;
max-lease-time 172800;
authoritative;

subnet 192.168.100.0 netmask 255.255.255.0 {
    range 192.168.100.50 192.168.100.200;
    option routers 192.168.100.1;
    option domain-name-servers 192.168.100.1, 8.8.8.8;
}
EOF
        
        cat > /etc/default/isc-dhcp-server << EOF
INTERFACESv4="eth1"
INTERFACESv6=""
EOF
    fi
    
    log_fix "DHCP-Server konfiguriert"
}

# Network Scanner installieren
install_network_scanner() {
    local code_dir="$1"
    log_info "Network Scanner installieren..."
    
    # Service-Dateien
    if [ -f "$code_dir/gateway-software/systemd/network-scanner.service" ]; then
        cp "$code_dir/gateway-software/systemd/network-scanner.service" /etc/systemd/system/
    else
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
    fi
    
    if [ -f "$code_dir/gateway-software/systemd/network-scanner.timer" ]; then
        cp "$code_dir/gateway-software/systemd/network-scanner.timer" /etc/systemd/system/
    else
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
    fi
    
    log_fix "Network Scanner Services installiert"
}

# WireGuard Keys sicherstellen
ensure_wireguard_keys() {
    log_info "WireGuard Keys prüfen..."
    
    if [ ! -f "/etc/wireguard/server_private.key" ]; then
        log_info "Generiere WireGuard Keys..."
        
        mkdir -p /etc/wireguard
        WG_PRIVATE_KEY=$(wg genkey)
        WG_PUBLIC_KEY=$(echo "$WG_PRIVATE_KEY" | wg pubkey)
        
        echo "$WG_PRIVATE_KEY" > /etc/wireguard/server_private.key
        echo "$WG_PUBLIC_KEY" > /etc/wireguard/server_public.key
        chmod 600 /etc/wireguard/server_private.key
        chmod 644 /etc/wireguard/server_public.key
        
        log_fix "WireGuard Keys generiert"
        log_info "VPS Public Key: $WG_PUBLIC_KEY"
    else
        log_success "WireGuard Keys bereits vorhanden"
    fi
}

# Services starten
start_services() {
    log_step "Services starten..."
    
    systemctl daemon-reload
    
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        # WireGuard Interface
        if ! wg show wg0 &>/dev/null; then
            wg-quick up wg0 || handle_warning "WireGuard Interface konnte nicht gestartet werden"
        fi
        systemctl enable wg-quick@wg0 2>/dev/null || true
        
        # VPS Service
        systemctl enable siteconnector-vps
        systemctl start siteconnector-vps
        
        sleep 3
        
        if systemctl is-active --quiet siteconnector-vps; then
            log_success "VPS Service gestartet"
        else
            handle_warning "VPS Service konnte nicht gestartet werden"
        fi
        
    else
        # Gateway Services
        systemctl enable siteconnector-gateway 2>/dev/null || true
        systemctl enable siteconnector-monitoring 2>/dev/null || true
        systemctl enable isc-dhcp-server 2>/dev/null || true
        systemctl enable network-scanner.timer 2>/dev/null || true
        
        systemctl start siteconnector-gateway 2>/dev/null || handle_warning "Gateway Service Start-Problem"
        systemctl start siteconnector-monitoring 2>/dev/null || handle_warning "Monitoring Service Start-Problem"
        systemctl start isc-dhcp-server 2>/dev/null || handle_warning "DHCP Service Start-Problem"
        systemctl start network-scanner.timer 2>/dev/null || handle_warning "Network Scanner Start-Problem"
        
        sleep 3
        
        # Status prüfen
        local services=("siteconnector-gateway" "siteconnector-monitoring" "isc-dhcp-server" "network-scanner.timer")
        for service in "${services[@]}"; do
            if systemctl is-active --quiet "$service"; then
                log_success "$service: Aktiv"
            else
                handle_warning "$service: Inaktiv"
            fi
        done
    fi
}

# Netzwerk-Fixes anwenden
apply_network_fixes() {
    log_step "Netzwerk-Optimierungen anwenden..."
    
    # IP-Forwarding aktivieren
    if ! grep -q "net.ipv4.ip_forward=1" /etc/sysctl.conf 2>/dev/null; then
        echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf
        sysctl -p >/dev/null 2>&1
        log_fix "IP-Forwarding aktiviert"
    fi
    
    # Gateway-spezifische Netzwerk-Konfiguration
    if [ "$SYSTEM_TYPE" = "gateway" ] && [ -f "/usr/local/bin/gateway_manager.py" ]; then
        log_info "Gateway-Netzwerk konfigurieren..."
        
        python3 << 'EOF'
import sys, subprocess
sys.path.append('/usr/local/bin')

try:
    from gateway_manager import WireGuardGateway
    gw = WireGuardGateway()
    
    if hasattr(gw, 'get_actual_interfaces'):
        wan_iface, lan_iface = gw.get_actual_interfaces()
    else:
        wan_iface = getattr(gw, 'wan_interface', 'eth0')
        lan_iface = getattr(gw, 'lan_interface', 'eth1')
    
    # LAN-Interface konfigurieren
    subprocess.run(['ip', 'addr', 'flush', 'dev', lan_iface], capture_output=True)
    subprocess.run(['ip', 'addr', 'add', '192.168.100.1/24', 'dev', lan_iface], capture_output=True)
    subprocess.run(['ip', 'link', 'set', lan_iface, 'up'], capture_output=True)
    
    print(f"Interface {lan_iface} konfiguriert: 192.168.100.1/24")
    
except Exception as e:
    print(f"Netzwerk-Konfiguration Fehler: {e}")
EOF
        
        log_fix "Gateway-Netzwerk konfiguriert"
    fi
}

# System-Diagnose durchführen
run_system_diagnosis() {
    log_step "System-Diagnose durchführen..."
    
    if [ -f "/usr/local/bin/system_check.py" ]; then
        python3 /usr/local/bin/system_check.py || handle_warning "System-Diagnose mit Warnungen abgeschlossen"
        log_fix "System-Diagnose durchgeführt"
    else
        handle_warning "System-Diagnose Script nicht verfügbar"
    fi
}

# Zusammenfassung anzeigen
show_summary() {
    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    
    echo ""
    echo "========================================"
    log_info "MANUELLES UPDATE ABGESCHLOSSEN"
    echo "========================================"
    echo ""
    
    log_info "System-Typ: $SYSTEM_TYPE"
    log_info "Dauer: ${duration}s"
    
    if [ ! -z "$BACKUP_DIR" ]; then
        log_info "Backup: $BACKUP_DIR"
    fi
    
    echo ""
    
    if [ ${#FIXES_APPLIED[@]} -gt 0 ]; then
        log_success "ANGEWENDETE KORREKTUREN (${#FIXES_APPLIED[@]}):"
        for fix in "${FIXES_APPLIED[@]}"; do
            echo "  ✅ $fix"
        done
        echo ""
    fi
    
    if [ ${#WARNINGS[@]} -gt 0 ]; then
        log_warning "WARNUNGEN (${#WARNINGS[@]}):"
        for warning in "${WARNINGS[@]}"; do
            echo "  ⚠️  $warning"
        done
        echo ""
    fi
    
    if [ ${#ERRORS[@]} -gt 0 ]; then
        log_error "FEHLER (${#ERRORS[@]}):"
        for error in "${ERRORS[@]}"; do
            echo "  ❌ $error"
        done
        echo ""
    fi
    
    # Empfehlungen
    if [ ${#ERRORS[@]} -gt 0 ]; then
        log_error "EMPFOHLENE MASSNAHMEN:"
        echo "  1. System neu starten: sudo reboot"
        echo "  2. Logs prüfen: journalctl -f"
        echo "  3. Support kontaktieren falls Probleme bestehen"
    elif [ ${#WARNINGS[@]} -gt 0 ]; then
        log_warning "EMPFOHLENE MASSNAHMEN:"
        echo "  1. Services überwachen: systemctl status siteconnector-*"
        echo "  2. Regelmäßige Updates: sudo siteconnector-update"
    else
        log_success "SYSTEM OPTIMAL KONFIGURIERT!"
        echo "  ✅ Alle Services laufen stabil"
        echo "  ✅ Keine kritischen Probleme gefunden"
        echo "  ✅ System bereit für den Produktivbetrieb"
    fi
    
    echo ""
    log_info "Nächste Schritte:"
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        local vps_ip=$(curl -s ifconfig.me 2>/dev/null || echo "VPS-IP")
        local vps_key=$(cat /etc/wireguard/server_public.key 2>/dev/null || echo "VPS-KEY")
        echo "  🌐 Dashboard: http://$vps_ip:8080"
        echo "  🔑 VPS Public Key: $vps_key"
        echo "  📋 Status: systemctl status siteconnector-vps"
    else
        echo "  🔧 Status: siteconnector-gateway status"
        echo "  🖥️  GUI: python3 /usr/local/bin/gui_app.py"
        echo "  🔍 Diagnose: python3 /usr/local/bin/system_check.py"
    fi
    
    echo "  📊 Update: sudo siteconnector-update"
    echo ""
}

# Hauptfunktion
main() {
    echo "🔧 MANUELLES UPDATE - WIREGUARD GATEWAY SYSTEM"
    echo "=============================================="
    
    check_root
    detect_system_type
    check_system_resources
    check_running_processes
    create_comprehensive_backup
    stop_services_safely
    
    local code_dir
    code_dir=$(download_latest_code)
    
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        update_vps_system "$code_dir"
    else
        update_gateway_system "$code_dir"
    fi
    
    apply_network_fixes
    start_services
    run_system_diagnosis
    
    # Cleanup
    rm -rf "$code_dir"
    
    show_summary
}

# Script-Ausführung
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main "$@"
fi