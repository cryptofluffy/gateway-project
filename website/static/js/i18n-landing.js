/**
 * Internationalization for Landing Page
 * Supports German and English translations
 */

class LandingI18nManager {
    constructor() {
        this.currentLanguage = localStorage.getItem('language') || 'de';
        this.translations = {
            de: {
                nav: {
                    dashboard: 'Dashboard'
                },
                hero: {
                    title: 'Sichere VPN-Gateway Lösung',
                    subtitle: 'Verbinden Sie sichere Netzwerke über das Internet mit WireGuard-Technologie. Einfach einzurichten, hochsicher und performant.',
                    download: 'Gateway herunterladen',
                    learn_more: 'Mehr erfahren'
                },
                features: {
                    title: 'Warum WireGuard Gateway?',
                    subtitle: 'Moderne VPN-Technologie trifft auf einfache Bedienung',
                    fast: {
                        title: 'Blitzschnell',
                        description: 'WireGuard ist bis zu 4x schneller als OpenVPN und benötigt weniger Ressourcen'
                    },
                    secure: {
                        title: 'Hochsicher',
                        description: 'Moderne Kryptographie mit ChaCha20, Poly1305 und Curve25519'
                    },
                    easy: {
                        title: 'Einfach',
                        description: 'Ein Befehl für komplette Installation und Konfiguration'
                    },
                    remote: {
                        title: 'Remote Access',
                        description: 'Sicherer Zugriff auf entfernte Netzwerke von überall'
                    },
                    monitoring: {
                        title: 'Monitoring',
                        description: 'Überwachen Sie Verbindungen und Port-Weiterleitungen in Echtzeit'
                    },
                    flexible: {
                        title: 'Flexibel',
                        description: 'Automatische oder manuelle Netzwerk-Interface Konfiguration'
                    }
                },
                howto: {
                    title: 'So funktioniert\'s',
                    step1: {
                        title: 'VPS einrichten',
                        description: 'Installieren Sie den VPS-Server und führen Sie das Setup aus'
                    },
                    step2: {
                        title: 'Gateway-PC installieren',
                        description: 'Laden Sie das Gateway herunter und installieren Sie es auf Ihrem Netzwerk-PC'
                    },
                    step3: {
                        title: 'Fertig!',
                        description: 'Ihr sicherer VPN-Tunnel ist etabliert und Port-Weiterleitungen funktionieren'
                    }
                },
                download: {
                    title: 'Jetzt herunterladen',
                    subtitle: 'Starten Sie in wenigen Minuten mit Ihrer sicheren VPN-Verbindung',
                    success: 'Download gestartet!',
                    vps: {
                        title: '🖥️ VPS Server',
                        description: 'Für Ihren VPS/Cloud Server (Ubuntu, Debian, CentOS)',
                        button: 'VPS Server herunterladen'
                    },
                    gateway: {
                        title: '🏠 Gateway-PC',
                        description: 'Für Ihren lokalen Gateway-PC (Raspberry Pi, Linux PC)',
                        button: 'Gateway-PC herunterladen'
                    },
                    requirements: {
                        title: '📋 Systemanforderungen',
                        linux: '• Linux (Ubuntu 18.04+, Debian 10+, CentOS 7+)',
                        root: '• Root-Zugriff für Installation',
                        network: '• Internetverbindung',
                        ports: '• Offene Ports für WireGuard (Standard: 51820/UDP)'
                    }
                },
                footer: {
                    description: 'Sichere VPN-Lösung für Netzwerk-Verbindungen',
                    copyright: 'Alle Rechte vorbehalten.',
                    links: {
                        title: 'Links',
                        dashboard: 'Dashboard',
                        features: 'Features',
                        download: 'Download'
                    },
                    tech: {
                        title: 'Technologie'
                    }
                }
            },
            en: {
                nav: {
                    dashboard: 'Dashboard'
                },
                hero: {
                    title: 'Secure VPN Gateway Solution',
                    subtitle: 'Connect secure networks over the internet with WireGuard technology. Easy to set up, highly secure, and performant.',
                    download: 'Download Gateway',
                    learn_more: 'Learn More'
                },
                features: {
                    title: 'Why WireGuard Gateway?',
                    subtitle: 'Modern VPN technology meets simple operation',
                    fast: {
                        title: 'Lightning Fast',
                        description: 'WireGuard is up to 4x faster than OpenVPN and requires fewer resources'
                    },
                    secure: {
                        title: 'Highly Secure',
                        description: 'Modern cryptography with ChaCha20, Poly1305, and Curve25519'
                    },
                    easy: {
                        title: 'Easy',
                        description: 'One command for complete installation and configuration'
                    },
                    remote: {
                        title: 'Remote Access',
                        description: 'Secure access to remote networks from anywhere'
                    },
                    monitoring: {
                        title: 'Monitoring',
                        description: 'Monitor connections and port forwards in real-time'
                    },
                    flexible: {
                        title: 'Flexible',
                        description: 'Automatic or manual network interface configuration'
                    }
                },
                howto: {
                    title: 'How it Works',
                    step1: {
                        title: 'Set up VPS',
                        description: 'Install the VPS server and run the setup'
                    },
                    step2: {
                        title: 'Install Gateway PC',
                        description: 'Download the gateway and install it on your network PC'
                    },
                    step3: {
                        title: 'Done!',
                        description: 'Your secure VPN tunnel is established and port forwards work'
                    }
                },
                download: {
                    title: 'Download Now',
                    subtitle: 'Start with your secure VPN connection in minutes',
                    success: 'Download started!',
                    vps: {
                        title: '🖥️ VPS Server',
                        description: 'For your VPS/Cloud Server (Ubuntu, Debian, CentOS)',
                        button: 'Download VPS Server'
                    },
                    gateway: {
                        title: '🏠 Gateway PC',
                        description: 'For your local Gateway PC (Raspberry Pi, Linux PC)',
                        button: 'Download Gateway PC'
                    },
                    requirements: {
                        title: '📋 System Requirements',
                        linux: '• Linux (Ubuntu 18.04+, Debian 10+, CentOS 7+)',
                        root: '• Root access for installation',
                        network: '• Internet connection',
                        ports: '• Open ports for WireGuard (default: 51820/UDP)'
                    }
                },
                footer: {
                    description: 'Secure VPN solution for network connections',
                    copyright: 'All rights reserved.',
                    links: {
                        title: 'Links',
                        dashboard: 'Dashboard',
                        features: 'Features',
                        download: 'Download'
                    },
                    tech: {
                        title: 'Technology'
                    }
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
        const deBtn = document.getElementById('nav-lang-de');
        const enBtn = document.getElementById('nav-lang-en');
        
        if (deBtn && enBtn) {
            if (this.currentLanguage === 'de') {
                deBtn.className = 'px-3 py-1 rounded bg-indigo-500 text-white text-sm';
                enBtn.className = 'px-3 py-1 rounded bg-gray-200 text-gray-700 text-sm';
            } else {
                deBtn.className = 'px-3 py-1 rounded bg-gray-200 text-gray-700 text-sm';
                enBtn.className = 'px-3 py-1 rounded bg-indigo-500 text-white text-sm';
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
const i18n = new LandingI18nManager();

// Global function for language switching
window.setLanguage = (lang) => {
    i18n.setLanguage(lang);
};