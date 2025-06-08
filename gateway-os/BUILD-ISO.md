# Gateway OS ISO Build Guide

Komplette Anleitung zum Erstellen einer bootbaren ISO-Datei für x86_64 Systeme.

## 🎯 ISO-Features

### Bootmodi
- **Live System** - Läuft komplett aus dem RAM, keine Installation nötig
- **Installation** - Permanente Installation auf Festplatte
- **Rescue Mode** - Rettungssystem für Troubleshooting
- **Safe Mode** - Start ohne automatische Netzwerkkonfiguration

### Unterstützte Systeme
- **x86_64 PCs** - Desktop/Server Hardware
- **BIOS & UEFI** - Dual-Boot-Kompatibilität
- **USB/CD/DVD** - Verschiedene Boot-Medien

## 🛠️ Build-Voraussetzungen

### System-Requirements
```bash
# Ubuntu/Debian
sudo apt-get install -y xorriso isolinux syslinux-utils squashfs-tools \
    cpio gzip build-essential debootstrap

# Fedora/CentOS
sudo dnf install -y xorriso syslinux squashfs-tools cpio gzip \
    build-essential debootstrap
```

### Hardware
- **Linux Host** - Ubuntu 20.04+ empfohlen
- **4GB RAM** - Für Build-Prozess
- **10GB freier Speicher** - Temporäre Build-Dateien
- **Internet** - Für Package-Downloads

## 🚀 ISO erstellen

### Quick Build
```bash
cd gateway-os
sudo ./scripts/build-iso.sh
```

### Custom Build
```bash
# Mit Version und Output-Pfad
sudo ./scripts/build-iso.sh --version 1.1.0 --output /tmp/iso

# Clean Build
sudo ./scripts/build-iso.sh --clean --version 1.0.0
```

### Vollständiger Buildroot Build
```bash
# Für professionelle Builds
sudo ./build/build-image.sh --target x86_64 --version 1.0.0
```

## 📀 ISO verwenden

### USB-Stick erstellen
```bash
# Linux/macOS
sudo dd if=gateway-os-x86_64-1.0.0.iso of=/dev/sdX bs=4M status=progress
sync

# Windows (PowerShell als Administrator)
# Verwende Rufus oder:
dd if=gateway-os-x86_64-1.0.0.iso of=\\.\PhysicalDrive1 bs=4M
```

### Bootvorgang
1. **USB-Stick anschließen**
2. **Von USB booten** (BIOS/UEFI Boot-Reihenfolge anpassen)
3. **Boot-Option wählen:**
   - `Gateway OS Live` - Live-System (Standard)
   - `Install Gateway OS` - Installation auf Festplatte
   - `Rescue Mode` - Rettungsmodus

## 💾 Installation auf Festplatte

### Automatische Installation
1. **Boot-Option "Install Gateway OS" wählen**
2. **Festplatte auswählen** (⚠️ Alle Daten werden gelöscht!)
3. **Installation läuft automatisch**
4. **Nach Neustart:** System ist bereit

### Manuelle Installation
```bash
# Im Live-System
sudo gateway-installer /dev/sda

# Mit Optionen
sudo gateway-installer --target /dev/nvme0n1 --format
```

## 🌐 Netzwerk-Konfiguration

### Standard-Einstellungen
```
LAN-Netzwerk: 192.168.100.0/24
Gateway-IP:   192.168.100.1
DHCP-Bereich: 192.168.100.10-200
Web-Interface: Port 8080
SSH:          Port 22
```

### Erste Anmeldung
```bash
# SSH-Zugang
ssh admin@192.168.100.1
# Passwort: gateway123 (sofort ändern!)

# Web-Interface
http://192.168.100.1:8080
```

## 🔧 ISO-Anpassung

### Build-Konfiguration ändern
```bash
# Buildroot-Konfiguration
vim build/configs/gateway-x86_64_defconfig

# Boot-Menü anpassen
vim bootloader/isolinux.cfg
vim bootloader/grub.cfg

# System-Overlay
# Dateien in rootfs/ werden ins System kopiert
```

### Packages hinzufügen
```bash
# In gateway-x86_64_defconfig
BR2_PACKAGE_NEUES_PAKET=y

# Rebuild
sudo ./scripts/build-iso.sh --clean
```

## 📁 ISO-Struktur

```
gateway-os-x86_64-1.0.0.iso
├── boot/
│   ├── isolinux/          # BIOS Boot
│   │   ├── isolinux.bin
│   │   ├── isolinux.cfg
│   │   └── *.c32
│   ├── grub/              # UEFI Boot
│   │   └── grub.cfg
│   ├── bzImage            # Linux Kernel
│   └── rootfs.cpio.gz     # Root Filesystem
├── README.txt
├── help.txt
└── .version
```

## 🔍 Troubleshooting

### Build-Probleme
```bash
# Dependencies prüfen
./scripts/build-iso.sh --help

# Clean Build
sudo rm -rf build-iso/
sudo ./scripts/build-iso.sh --clean

# Verbose Output
sudo bash -x ./scripts/build-iso.sh
```

### Boot-Probleme
- **Secure Boot deaktivieren** (in UEFI-Settings)
- **USB-Port wechseln** (USB 2.0 oft stabiler)
- **BIOS Boot-Reihenfolge** prüfen
- **Legacy/UEFI Modus** testen

### Performance-Optimierung
```bash
# Für schnellere Builds
export MAKEFLAGS="-j$(nproc)"

# RAM-Disk für Build (optional)
sudo mount -t tmpfs -o size=8G tmpfs /tmp/build
```

## 📊 Build-Zeiten

| System | Build-Zeit | RAM | CPU |
|--------|------------|-----|-----|
| Desktop PC | 15-30 min | 8GB | 8 Cores |
| Laptop | 30-60 min | 4GB | 4 Cores |
| Server | 10-20 min | 16GB | 16 Cores |

## 🔐 Sicherheit

### ISO-Verifikation
```bash
# Checksummen prüfen
sha256sum -c gateway-os-x86_64-1.0.0.iso.sha256
md5sum -c gateway-os-x86_64-1.0.0.iso.md5

# GPG-Signatur (falls verfügbar)
gpg --verify gateway-os-x86_64-1.0.0.iso.sig
```

### Sichere Verteilung
- **HTTPS** für Downloads verwenden
- **Checksummen** immer prüfen
- **Offizielle Quellen** verwenden

## 📚 Erweiterte Features

### Multi-Arch Support
```bash
# ARM64 ISO (experimentell)
sudo ./build/build-image.sh --target aarch64

# Verschiedene Architekturen
for arch in x86_64 i686 aarch64; do
    sudo ./build/build-image.sh --target $arch
done
```

### Custom Branding
```bash
# Logo und Splash anpassen
cp custom-logo.png bootloader/splash.png

# Boot-Menü anpassen
vim bootloader/isolinux.cfg
```

## 📋 Checkliste

### Vor dem Build
- [ ] Dependencies installiert
- [ ] Genügend Speicherplatz frei
- [ ] Internet-Verbindung aktiv
- [ ] Root-Rechte verfügbar

### Nach dem Build
- [ ] ISO-Größe prüfen (sollte ~100-500MB sein)
- [ ] Checksummen erstellt
- [ ] Test-Boot von USB
- [ ] Installation getestet

### Vor der Verteilung
- [ ] Funktionstest abgeschlossen
- [ ] Dokumentation aktualisiert
- [ ] Checksummen veröffentlicht
- [ ] Release Notes erstellt

## 🎯 Nächste Schritte

1. **ISO bauen:** `sudo ./scripts/build-iso.sh`
2. **USB erstellen:** `sudo dd if=*.iso of=/dev/sdX`
3. **Testen:** Boot von USB testen
4. **Installieren:** Auf Ziel-Hardware installieren
5. **Konfigurieren:** VPN und Netzwerk einrichten

Perfekt! Du hast jetzt eine vollständige ISO-Datei für x86_64 Systeme! 🎉