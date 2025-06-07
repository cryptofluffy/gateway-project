/**
 * Internationalization (i18n) Manager
 * Supports German and English translations
 */

class I18nManager {
    constructor() {
        this.currentLanguage = localStorage.getItem('language') || 'de';
        this.translations = {
            de: {
                nav: {
                    home: 'Home',
                    dashboard: 'Dashboard',
                    port_forwards: 'Port-Weiterleitungen'
                },
                dashboard: {
                    title: 'Dashboard - WireGuard Gateway',
                    tunnel_status: 'Tunnel Status',
                    active: 'Aktiv',
                    inactive: 'Inaktiv',
                    connected_clients: 'Verbundene Clients',
                    port_forwards: 'Port-Weiterleitungen',
                    interface_details: 'WireGuard Interface Details',
                    restart_interface: 'Interface neu starten',
                    add_gateway: 'Gateway-Client hinzufügen',
                    gateway_name: 'Gateway Name',
                    location: 'Standort/Beschreibung',
                    public_key: 'Gateway Public Key',
                    network_interfaces: 'Netzwerkschnittstellen-Zuordnung',
                    wan_interface: 'WAN-Interface (Internet)',
                    lan_interface: 'LAN-Interface (Server)',
                    auto_detect: 'Automatisch erkennen',
                    custom: 'Benutzerdefiniert',
                    add_button: 'Gateway hinzufügen',
                    edit: 'Bearbeiten',
                    remove: 'Entfernen',
                    copy: 'Kopieren',
                    copied: 'Kopiert!',
                    copy_error: 'Fehler beim Kopieren',
                    vps_config: 'VPS Konfigurationsdaten',
                    vps_public_key: 'VPS Public Key:',
                    vps_ip: 'VPS IP-Adresse:',
                    gateway_oneliner: 'Gateway-PC One-Liner (Komplette Installation):',
                    copy_oneliner: 'One-Liner kopieren',
                    manage: 'Verwalten'
                },
                notifications: {
                    loading: 'Laden...',
                    gateway_adding: 'Gateway wird hinzugefügt...',
                    gateway_added: 'Gateway-Client erfolgreich hinzugefügt!',
                    client_editing: 'Client wird bearbeitet...',
                    client_edited: 'Client erfolgreich bearbeitet',
                    client_removing: 'Client wird entfernt...',
                    client_removed: 'Client erfolgreich entfernt',
                    wireguard_restarting: 'Interface wird neu gestartet...',
                    wireguard_restarted: 'WireGuard erfolgreich neu gestartet',
                    error_unknown: 'Unbekannter Fehler',
                    error_network: 'Netzwerk-Fehler',
                    confirm_remove: 'Client entfernen?',
                    confirm_remove_message: 'Diese Aktion kann nicht rückgängig gemacht werden.',
                    confirm_restart: 'WireGuard Interface neu starten?',
                    confirm_restart_message: 'Dies kann zu kurzen Verbindungsunterbrechungen führen.',
                    cancel: 'Abbrechen',
                    confirm: 'Bestätigen',
                    save: 'Speichern'
                }
            },
            en: {
                nav: {
                    home: 'Home',
                    dashboard: 'Dashboard',
                    port_forwards: 'Port Forwards'
                },
                dashboard: {
                    title: 'Dashboard - WireGuard Gateway',
                    tunnel_status: 'Tunnel Status',
                    active: 'Active',
                    inactive: 'Inactive',
                    connected_clients: 'Connected Clients',
                    port_forwards: 'Port Forwards',
                    interface_details: 'WireGuard Interface Details',
                    restart_interface: 'Restart Interface',
                    add_gateway: 'Add Gateway Client',
                    gateway_name: 'Gateway Name',
                    location: 'Location/Description',
                    public_key: 'Gateway Public Key',
                    network_interfaces: 'Network Interface Mapping',
                    wan_interface: 'WAN Interface (Internet)',
                    lan_interface: 'LAN Interface (Server)',
                    auto_detect: 'Auto Detect',
                    custom: 'Custom',
                    add_button: 'Add Gateway',
                    edit: 'Edit',
                    remove: 'Remove',
                    copy: 'Copy',
                    copied: 'Copied!',
                    copy_error: 'Copy error',
                    vps_config: 'VPS Configuration Data',
                    vps_public_key: 'VPS Public Key:',
                    vps_ip: 'VPS IP Address:',
                    gateway_oneliner: 'Gateway PC One-Liner (Complete Installation):',
                    copy_oneliner: 'Copy One-Liner',
                    manage: 'Manage'
                },
                notifications: {
                    loading: 'Loading...',
                    gateway_adding: 'Adding gateway...',
                    gateway_added: 'Gateway client successfully added!',
                    client_editing: 'Editing client...',
                    client_edited: 'Client successfully edited',
                    client_removing: 'Removing client...',
                    client_removed: 'Client successfully removed',
                    wireguard_restarting: 'Restarting interface...',
                    wireguard_restarted: 'WireGuard successfully restarted',
                    error_unknown: 'Unknown error',
                    error_network: 'Network error',
                    confirm_remove: 'Remove client?',
                    confirm_remove_message: 'This action cannot be undone.',
                    confirm_restart: 'Restart WireGuard interface?',
                    confirm_restart_message: 'This may cause brief connection interruptions.',
                    cancel: 'Cancel',
                    confirm: 'Confirm',
                    save: 'Save'
                }
            }
        };
        
        this.init();
    }

    init() {
        this.updateLanguageButtons();
        this.translatePage();
    }

    setLanguage(lang) {
        if (this.translations[lang]) {
            this.currentLanguage = lang;
            localStorage.setItem('language', lang);
            this.updateLanguageButtons();
            this.translatePage();
        }
    }

    updateLanguageButtons() {
        const deBtn = document.getElementById('lang-de');
        const enBtn = document.getElementById('lang-en');
        
        if (deBtn && enBtn) {
            if (this.currentLanguage === 'de') {
                deBtn.className = 'px-3 py-1 rounded bg-blue-500 text-white text-sm';
                enBtn.className = 'px-3 py-1 rounded bg-gray-200 text-gray-700 text-sm ml-1';
            } else {
                deBtn.className = 'px-3 py-1 rounded bg-gray-200 text-gray-700 text-sm';
                enBtn.className = 'px-3 py-1 rounded bg-blue-500 text-white text-sm ml-1';
            }
        }
    }

    translatePage() {
        const elements = document.querySelectorAll('[data-i18n]');
        elements.forEach(element => {
            const key = element.getAttribute('data-i18n');
            const translation = this.getTranslation(key);
            if (translation) {
                element.textContent = translation;
            }
        });
    }

    getTranslation(key) {
        const keys = key.split('.');
        let translation = this.translations[this.currentLanguage];
        
        for (const k of keys) {
            if (translation && translation[k]) {
                translation = translation[k];
            } else {
                return null;
            }
        }
        
        return translation;
    }

    translate(key) {
        return this.getTranslation(key) || key;
    }
}

// Global instance
const i18n = new I18nManager();

// Global function for language switching
window.setLanguage = (lang) => {
    i18n.setLanguage(lang);
};