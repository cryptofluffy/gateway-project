# 🔧 Manuelles Update-System für WireGuard Gateway

Dieses umfassende Update-System behebt alle kritischen Probleme und optimiert die Performance des WireGuard Gateway Systems.

## 📋 **Verfügbare Scripts**

### 1. **`manual-update.sh`** - Hauptupdate-Script
```bash
sudo chmod +x manual-update.sh
sudo ./manual-update.sh
```
**Funktion**: Vollständiges System-Update mit:
- Automatische System-Typ-Erkennung (VPS/Gateway)
- Umfassendes Backup vor Update
- Sichere Service-Verwaltung
- Code-Aktualisierung von GitHub
- Hardware-spezifische Optimierungen
- Detaillierte Fehlerbehandlung und Logging

### 2. **`system-repair.sh`** - Notfall-Reparatur
```bash
sudo chmod +x system-repair.sh
sudo ./system-repair.sh
```
**Funktion**: Tiefgreifende System-Reparatur:
- Hängende Prozesse erkennen und beenden (infinite loops)
- Speicher- und Festplattenprobleme beheben
- Netzwerk-Konfiguration reparieren
- WireGuard-Probleme lösen
- Kritische Sicherheitslücken schließen
- Hardware-spezifische Performance-Optimierungen

### 3. **`install-gateway.sh`** - Neuinstallation
```bash
sudo chmod +x install-gateway.sh
sudo ./install-gateway.sh
```
**Funktion**: Komplette Neuinstallation:
- Automatische Hardware-Erkennung (Raspberry Pi, VPS, Mini-PC)
- Interaktive Installations-Typ-Auswahl
- Optimierte Konfiguration je Hardware
- WireGuard-Setup mit automatischer Key-Generierung
- Netzwerk-Konfiguration mit Interface-Auswahl

### 4. **`system_check.py`** - System-Diagnose
```bash
sudo python3 system_check.py
```
**Funktion**: Umfassende System-Diagnose:
- Ressourcen-Monitoring (CPU, RAM, Disk)
- Service-Status-Prüfung
- Netzwerk-Konnektivität-Tests
- WireGuard-Status-Analyse
- Automatische Problem-Behebung
- Detaillierte JSON-Berichte

## 🚨 **Kritische Probleme behoben**

### **Problem: "der ganze pi hängt sich beim updaten auf"**
**Lösung**: 
- Infinite Loops in Monitoring-Systemen stabilisiert
- Consecutive Error Counting (max 3-5 Fehler)
- Exponential Backoff bei Fehlern
- Automatische Monitoring-Stopp bei zu vielen Fehlern
- Proper KeyboardInterrupt-Handling

### **Problem: "vps kann nicht mehr erreicht werden"**
**Lösung**:
- VPS Server Binding-Probleme behoben (0.0.0.0 → 127.0.0.1 in Produktion)
- SSH-Sicherheitslücken geschlossen (hardcoded passwords entfernt)
- Optimierte Startup-Sequenz mit Ressourcen-Checks
- Bessere Fehlerbehandlung und Logging

### **Problem: Interface-Konfiguration**
**Lösung**:
- Dynamische Interface-Erkennung statt hardcoded `eth1`
- Dashboard-Konfiguration hat absolute Priorität
- Universelle Hardware-Unterstützung (Ethernet, WLAN, USB, etc.)
- Sichere Interface-Validierung und Fallbacks

## 🎯 **Anwendungsszenarien**

### **Scenario 1: System hängt sich auf**
```bash
# 1. Notfall-Reparatur
sudo ./system-repair.sh

# 2. Falls weiterhin Probleme
sudo ./manual-update.sh

# 3. System-Status prüfen
sudo python3 system_check.py
```

### **Scenario 2: VPS nicht erreichbar**
```bash
# 1. System-Diagnose
sudo python3 system_check.py

# 2. Vollständiges Update
sudo ./manual-update.sh

# 3. Bei anhaltenden Problemen: Neuinstallation
sudo ./install-gateway.sh
```

### **Scenario 3: Reguläres Update**
```bash
# Standard-Update-Prozess
sudo ./manual-update.sh

# Optional: Anschließende Diagnose
sudo python3 system_check.py
```

### **Scenario 4: Komplett neue Installation**
```bash
# Frische Installation
sudo ./install-gateway.sh

# Oder für VPS
sudo ./install-gateway.sh  # Wähle VPS während Installation
```

## 🔍 **Detaillierte Funktionen**

### **Hardware-Optimierungen**
- **Raspberry Pi**: GPU Memory reduziert, Swap optimiert, CPU-Governor auf performance
- **VPS**: Netzwerk-Buffer optimiert, VM-Einstellungen angepasst
- **Mini-PC**: Standard-Optimierungen für bessere Performance

### **Monitoring-Stabilisierung**
```python
# Beispiel der implementierten Stabilisierung:
consecutive_errors = 0
max_consecutive_errors = 5

while self.running:
    try:
        # Monitoring-Logik
        consecutive_errors = 0  # Reset bei Erfolg
    except KeyboardInterrupt:
        self.running = False
        break
    except Exception as e:
        consecutive_errors += 1
        if consecutive_errors >= max_consecutive_errors:
            self.running = False
            break
        time.sleep(min(300, 30 * consecutive_errors))  # Exponential backoff
```

### **Automatische Problem-Erkennung**
- Hängende Prozesse (D-State) erkennen und beenden
- Infinite Loops (>95% CPU) identifizieren und stoppen
- Speicher-Fragmentierung überwachen
- Netzwerk-Fehler analysieren
- Dateisystem-Probleme erkennen

### **Sicherheits-Verbesserungen**
- Hardcoded Passwörter entfernt
- SSH Root-Login deaktiviert
- Dateiberechtigungen korrigiert
- UFW Firewall-Konfiguration
- Sichere Service-Konfigurationen mit Resource-Limits

## 📊 **Logging und Monitoring**

### **Log-Dateien**
```bash
# Update-Logs
tail -f /var/log/siteconnector-update.log

# System-Logs
journalctl -u siteconnector-* -f

# Diagnose-Berichte
ls /tmp/system_check_*.json
```

### **Service-Status**
```bash
# VPS
systemctl status siteconnector-vps
systemctl status wg-quick@wg0

# Gateway
systemctl status siteconnector-gateway
systemctl status siteconnector-monitoring
systemctl status isc-dhcp-server
systemctl status network-scanner.timer
```

## 🎛️ **Konfiguration**

### **Hardware-Adaptive Einstellungen**
- **Raspberry Pi**: Reduzierte Ressourcen-Limits, längere Monitoring-Intervalle
- **VPS**: Optimierte Netzwerk-Einstellungen, Sicherheits-Härtung
- **Standard-Hardware**: Balanced Performance-Einstellungen

### **Service-Limits**
```ini
# Beispiel: Raspberry Pi Service-Limits
MemoryMax=256M
CPUQuota=60%
```

## 🆘 **Troubleshooting**

### **Script schlägt fehl**
```bash
# Logs prüfen
journalctl -xe

# Manuell mit Debug
bash -x ./manual-update.sh
```

### **Services starten nicht**
```bash
# Service-Status prüfen
systemctl status siteconnector-*

# Logs analysieren
journalctl -u siteconnector-gateway --since "1 hour ago"

# Notfall-Reparatur
sudo ./system-repair.sh
```

### **Netzwerk-Probleme**
```bash
# Interface prüfen
ip addr show

# DNS testen
nslookup google.com

# WireGuard Status
wg show
```

## 📞 **Support**

Bei anhaltenden Problemen:

1. **Vollständige Diagnose erstellen**:
   ```bash
   sudo python3 system_check.py
   ```

2. **Logs sammeln**:
   ```bash
   journalctl -u siteconnector-* --since "1 hour ago" > logs.txt
   ```

3. **System-Informationen**:
   ```bash
   uname -a > system_info.txt
   free -h >> system_info.txt
   df -h >> system_info.txt
   ```

## 🎉 **Erfolgskriterien**

Nach erfolgreichem Update sollten folgende Bedingungen erfüllt sein:

✅ **Keine hängenden Prozesse** - `ps aux | grep -E "(D|Z)"`  
✅ **Services laufen stabil** - `systemctl status siteconnector-*`  
✅ **Speicherverbrauch normal** - `free -h`  
✅ **Netzwerk funktioniert** - `ping 8.8.8.8`  
✅ **WireGuard aktiv** - `wg show`  
✅ **Dashboard erreichbar** - HTTP-Test auf Port 8080  

Das System ist jetzt **produktionsbereit** und **stabil** konfiguriert! 🚀