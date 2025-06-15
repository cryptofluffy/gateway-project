#!/bin/bash
# Tiefgreifende System-Reparatur für WireGuard Gateway
# Behebt kritische Probleme und optimiert Performance

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
log_critical() { echo -e "${RED}🚨 KRITISCH: $1${NC}"; }
log_repair() { echo -e "${GREEN}🔧 REPARIERT: $1${NC}"; }
log_check() { echo -e "${CYAN}🔍 PRÜFE: $1${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }

# Globale Variablen
CRITICAL_ISSUES=()
REPAIRS_MADE=()
SYSTEM_TYPE=""

# Root-Check
if [ "$EUID" -ne 0 ]; then
    log_critical "Als root ausführen: sudo $0"
    exit 1
fi

# Hardware-Erkennung
detect_hardware() {
    log_check "Hardware-Typ erkennen..."
    
    # Raspberry Pi Erkennung
    if grep -qi "raspberry\|bcm" /proc/cpuinfo 2>/dev/null; then
        echo "raspberry_pi"
        return
    fi
    
    # VPS Erkennung (wenig RAM, virtuelle CPU)
    local memory_gb=$(free -g | awk 'NR==2{print $2}')
    if [ "$memory_gb" -le 2 ] && grep -qi "virtual\|kvm\|xen" /proc/cpuinfo 2>/dev/null; then
        echo "vps"
        return
    fi
    
    echo "unknown"
}

# Hängende Prozesse reparieren
fix_hanging_processes() {
    log_check "Hängende Prozesse suchen und beenden..."
    
    # Prozesse in D-State (uninterruptible sleep) finden
    local hung_pids=$(ps axo pid,stat,comm | awk '$2 ~ /D/ {print $1}')
    
    if [ ! -z "$hung_pids" ]; then
        log_critical "Hängende Prozesse gefunden!"
        
        echo "$hung_pids" | while read pid; do
            if [ ! -z "$pid" ]; then
                local comm=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                log_info "Beende hängenden Prozess: $comm (PID: $pid)"
                
                # Sanft beenden
                kill -TERM "$pid" 2>/dev/null || true
                sleep 2
                
                # Noch aktiv? Dann härter
                if kill -0 "$pid" 2>/dev/null; then
                    kill -KILL "$pid" 2>/dev/null || true
                    sleep 1
                fi
                
                # Überprüfung
                if ! kill -0 "$pid" 2>/dev/null; then
                    log_repair "Prozess beendet: $comm"
                    REPAIRS_MADE+=("Hängender Prozess beendet: $comm")
                fi
            fi
        done
    fi
    
    # Prozesse mit extrem hoher CPU-Last (mögliche infinite loops)
    local high_cpu_pids=$(ps axo pid,pcpu,comm --sort=-pcpu | head -5 | awk '$2 > 95 {print $1}')
    
    if [ ! -z "$high_cpu_pids" ]; then
        echo "$high_cpu_pids" | while read pid; do
            if [ ! -z "$pid" ] && [ "$pid" != "PID" ]; then
                local comm=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
                local cpu=$(ps -p "$pid" -o pcpu= 2>/dev/null || echo "0")
                
                # Nur Gateway/WireGuard/Python Prozesse mit >95% CPU beenden
                if echo "$comm" | grep -qE "(python|gateway|wireguard|monitor)"; then
                    log_critical "Infinite Loop erkannt: $comm (PID: $pid, CPU: $cpu%)"
                    
                    kill -TERM "$pid" 2>/dev/null || true
                    sleep 3
                    
                    if kill -0 "$pid" 2>/dev/null; then
                        kill -KILL "$pid" 2>/dev/null || true
                    fi
                    
                    if ! kill -0 "$pid" 2>/dev/null; then
                        log_repair "Infinite Loop beendet: $comm"
                        REPAIRS_MADE+=("Infinite Loop beendet: $comm")
                    fi
                fi
            fi
        done
    fi
}

# Speicher-Probleme beheben
fix_memory_issues() {
    log_check "Speicher-Probleme beheben..."
    
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$memory_usage" -gt 90 ]; then
        log_critical "Kritische Speicherauslastung: $memory_usage%"
        
        # Cache leeren
        sync
        echo 3 > /proc/sys/vm/drop_caches
        log_repair "System-Cache geleert"
        
        # Swap aktivieren falls verfügbar
        if [ -f "/swapfile" ] && ! swapon --show | grep -q "/swapfile"; then
            swapon /swapfile 2>/dev/null && log_repair "Swap aktiviert"
        fi
        
        # Memory-intensive Prozesse finden und warnen
        local memory_hogs=$(ps axo pid,pmem,comm --sort=-pmem | head -5 | awk '$2 > 20 {print $3 " (" $2 "%)"}')
        if [ ! -z "$memory_hogs" ]; then
            log_info "Speicher-intensive Prozesse:"
            echo "$memory_hogs"
        fi
        
        REPAIRS_MADE+=("Speicher-Optimierung durchgeführt")
    fi
}

# Festplatte bereinigen
fix_disk_issues() {
    log_check "Festplatten-Probleme beheben..."
    
    local disk_usage=$(df / | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [ "$disk_usage" -gt 85 ]; then
        log_critical "Hohe Festplattenauslastung: $disk_usage%"
        
        # Log-Dateien bereinigen
        find /var/log -name "*.log" -type f -size +100M -exec truncate -s 50M {} \; 2>/dev/null || true
        find /var/log -name "*.log.*" -type f -mtime +7 -delete 2>/dev/null || true
        
        # Journal bereinigen
        journalctl --vacuum-time=7d 2>/dev/null || true
        journalctl --vacuum-size=100M 2>/dev/null || true
        
        # Temp-Dateien löschen
        find /tmp -type f -atime +3 -delete 2>/dev/null || true
        find /var/tmp -type f -atime +7 -delete 2>/dev/null || true
        
        # Package-Cache bereinigen
        apt autoclean 2>/dev/null || true
        apt autoremove -y 2>/dev/null || true
        
        log_repair "Festplatten-Bereinigung durchgeführt"
        REPAIRS_MADE+=("Festplatte bereinigt - $(df / | awk 'NR==2{printf "%.0f", $3*100/$2}')% Auslastung")
    fi
}

# Netzwerk-Probleme reparieren
fix_network_issues() {
    log_check "Netzwerk-Probleme reparieren..."
    
    # DNS-Test
    if ! nslookup google.com >/dev/null 2>&1; then
        log_critical "DNS-Probleme erkannt"
        
        # DNS-Server reparieren
        cat > /etc/resolv.conf << EOF
nameserver 8.8.8.8
nameserver 8.8.4.4
nameserver 1.1.1.1
EOF
        log_repair "DNS-Server korrigiert"
        REPAIRS_MADE+=("DNS-Konfiguration repariert")
    fi
    
    # Interface-Probleme beheben
    local down_interfaces=$(ip link show | grep "state DOWN" | awk -F: '{print $2}' | tr -d ' ')
    
    if [ ! -z "$down_interfaces" ]; then
        echo "$down_interfaces" | while read iface; do
            if [ ! -z "$iface" ] && [[ ! "$iface" =~ ^(lo|docker|br-|veth) ]]; then
                log_info "Versuche Interface zu aktivieren: $iface"
                ip link set "$iface" up 2>/dev/null && log_repair "Interface aktiviert: $iface"
            fi
        done
    fi
    
    # IP-Forwarding sicherstellen
    if [ "$(cat /proc/sys/net/ipv4/ip_forward)" != "1" ]; then
        echo 1 > /proc/sys/net/ipv4/ip_forward
        log_repair "IP-Forwarding aktiviert"
        REPAIRS_MADE+=("IP-Forwarding repariert")
    fi
}

# WireGuard-Probleme beheben
fix_wireguard_issues() {
    log_check "WireGuard-Probleme beheben..."
    
    # WireGuard Installation prüfen
    if ! which wg >/dev/null 2>&1; then
        log_critical "WireGuard nicht installiert"
        apt update >/dev/null 2>&1
        apt install -y wireguard >/dev/null 2>&1
        log_repair "WireGuard installiert"
        REPAIRS_MADE+=("WireGuard installiert")
    fi
    
    # Defekte WireGuard-Konfiguration reparieren
    local wg_configs=$(find /etc/wireguard -name "*.conf" 2>/dev/null)
    
    for config in $wg_configs; do
        if [ -f "$config" ]; then
            # Prüfe auf Shell-Substitution-Fehler
            if grep -q '$(cat' "$config" 2>/dev/null; then
                log_critical "Defekte WireGuard-Konfiguration: $config"
                
                # Backup erstellen
                cp "$config" "$config.broken.$(date +%s)"
                
                # Keys extrahieren und Config reparieren
                local private_key_file=$(grep '$(cat' "$config" | sed 's/.*$(cat \([^)]*\)).*/\1/')
                if [ -f "$private_key_file" ]; then
                    local private_key=$(cat "$private_key_file")
                    sed -i "s|\$(cat $private_key_file)|$private_key|g" "$config"
                    log_repair "WireGuard-Konfiguration repariert: $config"
                    REPAIRS_MADE+=("WireGuard-Config repariert: $(basename $config)")
                fi
            fi
        fi
    done
    
    # WireGuard Interface-Status prüfen
    if ! wg show 2>/dev/null | grep -q "interface:"; then
        # Versuche WireGuard Interface zu starten
        local interface=$(basename $(find /etc/wireguard -name "*.conf" | head -1) .conf)
        if [ ! -z "$interface" ]; then
            wg-quick up "$interface" 2>/dev/null && log_repair "WireGuard Interface gestartet: $interface"
        fi
    fi
}

# Service-Probleme beheben
fix_service_issues() {
    log_check "Service-Probleme beheben..."
    
    # Systemd-Services prüfen und reparieren
    local critical_services=()
    
    if [ -f "/opt/siteconnector-vps/app.py" ] || [ -f "/opt/wireguard-vps/app.py" ]; then
        SYSTEM_TYPE="vps"
        critical_services=("siteconnector-vps" "wg-quick@wg0")
    elif [ -f "/usr/local/bin/gateway_manager.py" ]; then
        SYSTEM_TYPE="gateway"
        critical_services=("siteconnector-gateway" "isc-dhcp-server")
    fi
    
    for service in "${critical_services[@]}"; do
        if ! systemctl is-active --quiet "$service" 2>/dev/null; then
            log_critical "Service nicht aktiv: $service"
            
            # Service starten
            systemctl start "$service" 2>/dev/null || true
            sleep 2
            
            if systemctl is-active --quiet "$service"; then
                log_repair "Service gestartet: $service"
                REPAIRS_MADE+=("Service repariert: $service")
            else
                # Journal-Logs prüfen
                local error_logs=$(journalctl -u "$service" --since "1 hour ago" --no-pager -q | tail -5)
                if [ ! -z "$error_logs" ]; then
                    log_info "Service-Fehler für $service:"
                    echo "$error_logs"
                fi
            fi
        fi
    done
    
    # Failed Units reparieren
    local failed_units=$(systemctl list-units --failed --no-legend | awk '{print $1}')
    
    if [ ! -z "$failed_units" ]; then
        echo "$failed_units" | while read unit; do
            if [[ "$unit" =~ (siteconnector|gateway|wireguard) ]]; then
                log_critical "Failed Unit: $unit"
                systemctl reset-failed "$unit" 2>/dev/null || true
                systemctl start "$unit" 2>/dev/null || true
                log_repair "Unit zurückgesetzt: $unit"
            fi
        done
    fi
}

# Hardware-spezifische Optimierungen
apply_hardware_optimizations() {
    local hardware_type=$(detect_hardware)
    log_check "Hardware-Optimierungen anwenden: $hardware_type"
    
    case "$hardware_type" in
        "raspberry_pi")
            # Raspberry Pi Optimierungen
            
            # GPU Memory reduzieren
            if grep -q "gpu_mem=16" /boot/config.txt; then
                echo "gpu_mem=16" >> /boot/config.txt
                log_repair "GPU Memory reduziert (Raspberry Pi)"
            fi
            
            # Swap-Optimierung
            if [ -f "/etc/dphys-swapfile" ]; then
                sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=512/' /etc/dphys-swapfile 2>/dev/null || true
                systemctl restart dphys-swapfile 2>/dev/null || true
                log_repair "Swap-Größe optimiert (Raspberry Pi)"
            fi
            
            # CPU-Governor auf performance
            echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || true
            
            REPAIRS_MADE+=("Raspberry Pi Optimierungen angewendet")
            ;;
            
        "vps")
            # VPS Optimierungen
            
            # Network-Buffer optimieren
            sysctl -w net.core.rmem_max=16777216 2>/dev/null || true
            sysctl -w net.core.wmem_max=16777216 2>/dev/null || true
            
            # VM-Einstellungen optimieren
            sysctl -w vm.swappiness=10 2>/dev/null || true
            
            REPAIRS_MADE+=("VPS Optimierungen angewendet")
            ;;
    esac
}

# Kritische Sicherheitsprobleme beheben
fix_security_issues() {
    log_check "Sicherheitsprobleme beheben..."
    
    # Unsichere Dateiberechtigungen
    find /etc/wireguard -name "*private*" -type f -exec chmod 600 {} \; 2>/dev/null || true
    find /etc/wireguard -name "*key" -type f -exec chmod 600 {} \; 2>/dev/null || true
    
    # SSH-Konfiguration sichern
    if grep -q "PermitRootLogin yes" /etc/ssh/sshd_config 2>/dev/null; then
        sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        systemctl reload sshd 2>/dev/null || true
        log_repair "SSH Root-Login deaktiviert"
        REPAIRS_MADE+=("SSH-Sicherheit verbessert")
    fi
    
    # Schwache Passwörter entfernen (falls vorhanden)
    if grep -r "password.*123\|password.*admin" /opt /etc /usr/local/bin 2>/dev/null | grep -v ".backup"; then
        log_critical "Schwache Passwörter in Konfiguration gefunden!"
        CRITICAL_ISSUES+=("Schwache Passwörter entdeckt - manuelle Überprüfung erforderlich")
    fi
}

# System-Performance optimieren
optimize_performance() {
    log_check "System-Performance optimieren..."
    
    # I/O-Scheduler optimieren
    for disk in /sys/block/*/queue/scheduler; do
        if [ -f "$disk" ] && grep -q "mq-deadline" "$disk"; then
            echo mq-deadline > "$disk" 2>/dev/null || true
        fi
    done
    
    # Kernel-Parameter optimieren
    cat >> /etc/sysctl.conf << EOF

# Performance-Optimierungen (System-Repair)
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_congestion_control = bbr
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF
    
    sysctl -p >/dev/null 2>&1 || true
    
    log_repair "Performance-Optimierungen angewendet"
    REPAIRS_MADE+=("System-Performance optimiert")
}

# Vollständige Diagnose
run_comprehensive_diagnosis() {
    log_check "Umfassende System-Diagnose..."
    
    # System-Load prüfen
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_count=$(nproc)
    
    if (( $(echo "$load_avg > $cpu_count * 2" | bc -l) )); then
        CRITICAL_ISSUES+=("Sehr hohe Systemlast: $load_avg (CPUs: $cpu_count)")
    fi
    
    # Memory-Fragmentierung prüfen
    local memory_fragmentation=$(cat /proc/buddyinfo | awk '{sum+=$NF} END {print sum}')
    if [ "$memory_fragmentation" -lt 100 ]; then
        CRITICAL_ISSUES+=("Hohe Memory-Fragmentierung erkannt")
    fi
    
    # Netzwerk-Errors prüfen
    local network_errors=$(cat /proc/net/dev | awk 'NR>2 {sum+=$4+$5+$13+$14} END {print sum}')
    if [ "$network_errors" -gt 1000 ]; then
        CRITICAL_ISSUES+=("Hohe Anzahl Netzwerk-Fehler: $network_errors")
    fi
    
    # Dateisystem-Errors prüfen
    local filesystem_errors=$(dmesg | grep -i "error\|critical\|fail" | grep -c "ext4\|filesystem" || echo "0")
    if [ "$filesystem_errors" -gt 10 ]; then
        CRITICAL_ISSUES+=("Dateisystem-Fehler erkannt: $filesystem_errors")
    fi
}

# Notfall-Reparatur für schwere Probleme
emergency_repair() {
    log_critical "NOTFALL-REPARATUR AKTIVIERT"
    
    # Alle nicht-essentiellen Services stoppen
    local non_essential_services=("apache2" "nginx" "mysql" "postgresql" "docker")
    for service in "${non_essential_services[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            systemctl stop "$service" 2>/dev/null || true
            log_repair "Non-essential Service gestoppt: $service"
        fi
    done
    
    # Kernel-Module neu laden
    if lsmod | grep -q wireguard; then
        modprobe -r wireguard 2>/dev/null || true
        sleep 2
        modprobe wireguard 2>/dev/null || true
        log_repair "WireGuard-Modul neu geladen"
    fi
    
    # Systemd-Manager neu laden
    systemctl daemon-reexec
    log_repair "Systemd neu geladen"
    
    REPAIRS_MADE+=("Notfall-Reparatur durchgeführt")
}

# Zusammenfassung erstellen
show_repair_summary() {
    echo ""
    echo "=================================================="
    log_info "SYSTEM-REPARATUR ABGESCHLOSSEN"
    echo "=================================================="
    echo ""
    
    if [ ${#CRITICAL_ISSUES[@]} -gt 0 ]; then
        log_critical "KRITISCHE PROBLEME GEFUNDEN (${#CRITICAL_ISSUES[@]}):"
        for issue in "${CRITICAL_ISSUES[@]}"; do
            echo "  🚨 $issue"
        done
        echo ""
        
        log_critical "EMPFOHLENE MASSNAHMEN:"
        echo "  1. System sofort neu starten: sudo reboot"
        echo "  2. Vollständiges Update durchführen: sudo ./manual-update.sh"
        echo "  3. Bei anhaltenden Problemen: Hardware prüfen"
        echo ""
    fi
    
    if [ ${#REPAIRS_MADE[@]} -gt 0 ]; then
        log_repair "DURCHGEFÜHRTE REPARATUREN (${#REPAIRS_MADE[@]}):"
        for repair in "${REPAIRS_MADE[@]}"; do
            echo "  🔧 $repair"
        done
        echo ""
    fi
    
    # System-Status nach Reparatur
    log_info "SYSTEM-STATUS NACH REPARATUR:"
    local memory_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    local disk_usage=$(df / | awk 'NR==2{printf "%.0f", $3*100/$2}')
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    
    echo "  📊 Speicher: $memory_usage%"
    echo "  💽 Festplatte: $disk_usage%"
    echo "  ⚡ Load: $load_avg"
    
    if [ "$SYSTEM_TYPE" = "vps" ]; then
        echo "  🌐 VPS Dashboard: http://$(curl -s ifconfig.me 2>/dev/null || echo 'VPS-IP'):8080"
    else
        echo "  🔧 Gateway Status: systemctl status siteconnector-gateway"
    fi
    
    echo ""
    log_info "Nächste Schritte:"
    echo "  1. System-Update: sudo ./manual-update.sh"
    echo "  2. Diagnose: python3 system_check.py"
    echo "  3. Monitoring: journalctl -f"
    echo ""
}

# Hauptfunktion
main() {
    echo "🚨 SYSTEM-REPARATUR - WIREGUARD GATEWAY"
    echo "======================================="
    echo ""
    
    log_info "Starte tiefgreifende System-Reparatur..."
    echo ""
    
    # Kritische Reparaturen
    fix_hanging_processes
    fix_memory_issues
    fix_disk_issues
    fix_network_issues
    fix_wireguard_issues
    fix_service_issues
    fix_security_issues
    
    # Optimierungen
    apply_hardware_optimizations
    optimize_performance
    
    # Diagnose
    run_comprehensive_diagnosis
    
    # Notfall-Reparatur bei kritischen Problemen
    if [ ${#CRITICAL_ISSUES[@]} -gt 2 ]; then
        emergency_repair
    fi
    
    show_repair_summary
}

# Script ausführen
main "$@"