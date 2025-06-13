/**
 * Port Forwards JavaScript - WireGuard Gateway Management
 * Optimierte Version für Port-Weiterleitungen
 */

class PortForwardManager {
    constructor() {
        this.initializeEventListeners();
        this.loadingOverlay = this.createLoadingOverlay();
        this.serviceTemplates = this.getServiceTemplates();
        this.loadConnectedClients();
    }

    /**
     * Service-Templates definieren
     */
    getServiceTemplates() {
        return {
            http: { 
                external_port: 80, 
                internal_port: 80, 
                protocol: 'tcp', 
                description: '🌐 HTTP - Standard Web-Server (unverschlüsselt)' 
            },
            https: { 
                external_port: 443, 
                internal_port: 443, 
                protocol: 'tcp', 
                description: '🔒 HTTPS - Sichere Website mit SSL/TLS Verschlüsselung' 
            },
            ssh: { 
                external_port: 2222, 
                internal_port: 22, 
                protocol: 'tcp', 
                description: '🔑 SSH - Sicherer Remote-Zugang über Terminal' 
            },
            ftp: { 
                external_port: 21, 
                internal_port: 21, 
                protocol: 'tcp', 
                description: '📁 FTP - Dateitransfer Protokoll (unverschlüsselt)' 
            },
            mysql: { 
                external_port: 3306, 
                internal_port: 3306, 
                protocol: 'tcp', 
                description: '🗄️ MySQL - Datenbank-Server für Anwendungen' 
            },
            minecraft: { 
                external_port: 25565, 
                internal_port: 25565, 
                protocol: 'both', 
                description: '🎮 Minecraft - Game-Server für Java/Bedrock Edition' 
            },
            rdp: { 
                external_port: 3389, 
                internal_port: 3389, 
                protocol: 'tcp', 
                description: '🖥️ RDP - Windows Remote Desktop Verbindung' 
            },
            plex: { 
                external_port: 32400, 
                internal_port: 32400, 
                protocol: 'tcp', 
                description: '🎬 Plex - Media-Server für Filme und Serien' 
            },
            nextcloud: { 
                external_port: 8443, 
                internal_port: 443, 
                protocol: 'tcp', 
                description: '☁️ Nextcloud - Private Cloud Storage' 
            },
            jellyfin: { 
                external_port: 8096, 
                internal_port: 8096, 
                protocol: 'tcp', 
                description: '📺 Jellyfin - Open-Source Media-Server' 
            },
            docker: { 
                external_port: 2376, 
                internal_port: 2376, 
                protocol: 'tcp', 
                description: '🐳 Docker - Container Management API' 
            }
        };
    }

    /**
     * Event Listeners initialisieren
     */
    initializeEventListeners() {
        // Port Forward Form
        const addForm = document.getElementById('add-port-forward-form');
        if (addForm) {
            addForm.addEventListener('submit', (e) => this.handleAddPortForward(e));
        }

        // Service Type Selection
        const serviceSelect = document.getElementById('service_type');
        if (serviceSelect) {
            serviceSelect.addEventListener('change', () => this.updateServiceInfo());
        }

        // Template Buttons
        document.querySelectorAll('[onclick^="useTemplate"]').forEach(button => {
            const service = button.getAttribute('onclick').match(/useTemplate\('([^']+)'\)/)?.[1];
            if (service) {
                button.onclick = (e) => {
                    e.preventDefault();
                    this.useTemplate(service);
                };
            }
        });
    }

    /**
     * Template anwenden
     */
    useTemplate(service) {
        const template = this.serviceTemplates[service];
        if (template) {
            document.getElementById('service_type').value = service;
            document.getElementById('external_port').value = template.external_port;
            document.getElementById('internal_port').value = template.internal_port;
            document.getElementById('protocol').value = template.protocol;
            this.updateServiceInfo();
            
            // Fokus auf IP-Feld setzen
            const ipField = document.getElementById('internal_ip');
            if (ipField) {
                ipField.focus();
            }
        } else {
            // Custom Template - Felder leeren
            document.getElementById('service_type').value = 'custom';
            document.getElementById('external_port').value = '';
            document.getElementById('internal_port').value = '';
            document.getElementById('protocol').value = 'tcp';
            this.updateServiceInfo();
        }
    }

    /**
     * Service-Info aktualisieren
     */
    updateServiceInfo() {
        const serviceType = document.getElementById('service_type').value;
        const infoDiv = document.getElementById('service-info');
        const descriptionDiv = document.getElementById('service-description');
        
        if (serviceType !== 'custom' && this.serviceTemplates[serviceType]) {
            const template = this.serviceTemplates[serviceType];
            descriptionDiv.innerHTML = template.description;
            infoDiv.classList.remove('hidden');
            
            // Auto-fill wenn Template ausgewählt wird
            const externalPortField = document.getElementById('external_port');
            if (externalPortField && externalPortField.value === '') {
                document.getElementById('external_port').value = template.external_port;
                document.getElementById('internal_port').value = template.internal_port;
                document.getElementById('protocol').value = template.protocol;
            }
        } else {
            infoDiv.classList.add('hidden');
        }
    }

    /**
     * Port-Weiterleitung hinzufügen
     */
    async handleAddPortForward(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = {
            external_port: parseInt(formData.get('external_port')),
            internal_ip: formData.get('internal_ip')?.trim(),
            internal_port: parseInt(formData.get('internal_port')),
            protocol: formData.get('protocol')
        };

        // Validierung
        const validation = this.validatePortForwardData(data);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        this.showLoading('Port-Weiterleitung wird hinzugefügt...');

        try {
            const response = await this.apiRequest('/api/port-forwards', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Port-Weiterleitung erfolgreich hinzugefügt');
                setTimeout(() => location.reload(), 1500);
            } else {
                this.showError(result.message || 'Unbekannter Fehler');
            }
        } catch (error) {
            this.showError(`Netzwerk-Fehler: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Port-Weiterleitung entfernen
     */
    async removePortForward(ruleId) {
        const confirmed = await this.showConfirmDialog(
            'Port-Weiterleitung entfernen?',
            'Diese Aktion kann nicht rückgängig gemacht werden.'
        );

        if (!confirmed) return;

        this.showLoading('Port-Weiterleitung wird entfernt...');

        try {
            const response = await this.apiRequest(`/api/port-forwards?rule_id=${encodeURIComponent(ruleId)}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Port-Weiterleitung erfolgreich entfernt');
                setTimeout(() => location.reload(), 1500);
            } else {
                this.showError(result.message || 'Unbekannter Fehler');
            }
        } catch (error) {
            this.showError(`Netzwerk-Fehler: ${error.message}`);
        } finally {
            this.hideLoading();
        }
    }

    /**
     * Validierung für Port-Forward-Daten
     */
    validatePortForwardData(data) {
        // Port-Validierung
        if (!Number.isInteger(data.external_port) || data.external_port < 1 || data.external_port > 65535) {
            return { valid: false, message: 'Externer Port muss zwischen 1 und 65535 liegen' };
        }

        if (!Number.isInteger(data.internal_port) || data.internal_port < 1 || data.internal_port > 65535) {
            return { valid: false, message: 'Interner Port muss zwischen 1 und 65535 liegen' };
        }

        // IP-Validierung
        if (!data.internal_ip) {
            return { valid: false, message: 'Interne IP-Adresse ist erforderlich' };
        }

        // Einfache IP-Validierung (IPv4)
        const ipPattern = /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/;
        if (!ipPattern.test(data.internal_ip)) {
            return { valid: false, message: 'Ungültige IP-Adresse' };
        }

        // Gateway-Subnet prüfen (10.0.0.x)
        if (!data.internal_ip.startsWith('10.0.0.')) {
            return { valid: false, message: 'IP-Adresse muss im Gateway-Subnet (10.0.0.x) liegen' };
        }

        // Protokoll-Validierung
        if (!['tcp', 'udp', 'both'].includes(data.protocol)) {
            return { valid: false, message: 'Ungültiges Protokoll' };
        }

        // Warnung für kritische Ports
        const criticalPorts = [22, 80, 443, 8080];
        if (criticalPorts.includes(data.external_port)) {
            // Hier könnte eine zusätzliche Bestätigung implementiert werden
        }

        return { valid: true };
    }

    /**
     * API-Request mit Fehlerbehandlung
     */
    async apiRequest(url, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        const response = await fetch(url, mergedOptions);
        
        if (!response.ok) {
            if (response.status === 429) {
                throw new Error('Zu viele Anfragen. Bitte warten Sie einen Moment.');
            }
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return response;
    }

    /**
     * Loading Overlay erstellen
     */
    createLoadingOverlay() {
        const overlay = document.createElement('div');
        overlay.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50 hidden';
        overlay.innerHTML = `
            <div class="bg-white rounded-lg p-6 flex items-center space-x-3">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                <span class="text-gray-700 font-medium" id="loading-text">Laden...</span>
            </div>
        `;
        document.body.appendChild(overlay);
        return overlay;
    }

    /**
     * Loading anzeigen
     */
    showLoading(message = 'Laden...') {
        const loadingText = document.getElementById('loading-text');
        if (loadingText) {
            loadingText.textContent = message;
        }
        this.loadingOverlay.classList.remove('hidden');
    }

    /**
     * Loading verstecken
     */
    hideLoading() {
        this.loadingOverlay.classList.add('hidden');
    }

    /**
     * Erfolgs-Nachricht anzeigen
     */
    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    /**
     * Fehler-Nachricht anzeigen
     */
    showError(message) {
        this.showNotification(message, 'error');
    }

    /**
     * Notification anzeigen
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : type === 'success' ? 'bg-green-500' : 'bg-blue-500';
        
        notification.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-transform duration-300 translate-x-full`;
        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" class="text-white hover:text-gray-200 ml-2">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                    </svg>
                </button>
            </div>
        `;

        document.body.appendChild(notification);

        // Animation
        setTimeout(() => {
            notification.classList.remove('translate-x-full');
        }, 100);

        // Auto-remove nach 5 Sekunden
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    /**
     * Verbundene Clients laden und IP-Dropdown aktualisieren
     */
    async loadConnectedClients() {
        try {
            const response = await this.apiRequest('/api/clients');
            const clients = await response.json();
            
            this.updateIPDropdown(clients);
        } catch (error) {
            console.error('Fehler beim Laden der verbundenen Clients:', error);
        }
    }

    /**
     * IP-Dropdown mit verbundenen Gateway-IPs aktualisieren
     */
    updateIPDropdown(clients) {
        const ipField = document.getElementById('internal_ip');
        if (!ipField) return;

        // Aktuellen Wert speichern
        const currentValue = ipField.value;

        // Datalist für Autocomplete erstellen/aktualisieren
        let datalist = document.getElementById('gateway-ips');
        if (!datalist) {
            datalist = document.createElement('datalist');
            datalist.id = 'gateway-ips';
            ipField.parentNode.insertBefore(datalist, ipField.nextSibling);
            ipField.setAttribute('list', 'gateway-ips');
        }

        // Datalist leeren
        datalist.innerHTML = '';

        // Connected Clients hinzufügen
        if (clients && clients.length > 0) {
            clients.forEach(client => {
                if (client.ip && client.status === 'connected') {
                    const option = document.createElement('option');
                    option.value = client.ip;
                    option.label = `${client.ip} - ${client.name || 'Gateway'} (${client.location || 'Unbekannt'})`;
                    datalist.appendChild(option);
                }
            });
        }

        // Default-IPs hinzufügen falls keine Clients verbunden sind
        if (datalist.children.length === 0) {
            const defaultIPs = ['10.0.0.100', '10.0.0.101', '10.0.0.102'];
            defaultIPs.forEach(ip => {
                const option = document.createElement('option');
                option.value = ip;
                option.label = `${ip} - Gateway (Beispiel)`;
                datalist.appendChild(option);
            });
        }

        // Aktuellen Wert wiederherstellen
        ipField.value = currentValue;

        // IP-Feld als verbessert markieren
        if (!ipField.classList.contains('enhanced')) {
            ipField.classList.add('enhanced');
            ipField.placeholder = 'IP-Adresse oder wählen Sie aus verfügbaren Gateways';
            
            // Refresh-Button hinzufügen
            this.addRefreshButton(ipField);
        }
    }

    /**
     * Refresh-Button für IP-Dropdown hinzufügen
     */
    addRefreshButton(ipField) {
        const container = ipField.parentNode;
        if (container.querySelector('.refresh-clients-btn')) return;

        const refreshBtn = document.createElement('button');
        refreshBtn.type = 'button';
        refreshBtn.className = 'refresh-clients-btn absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none';
        refreshBtn.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
            </svg>
        `;
        refreshBtn.title = 'Verbundene Gateways neu laden';
        refreshBtn.addEventListener('click', () => this.loadConnectedClients());

        // Container als relative positionieren
        container.style.position = 'relative';
        container.appendChild(refreshBtn);
    }

    /**
     * Bestätigungs-Dialog anzeigen
     */
    showConfirmDialog(title, message) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <h3 class="text-lg font-semibold text-gray-900 mb-2">${title}</h3>
                    <p class="text-gray-600 mb-6">${message}</p>
                    <div class="flex justify-end space-x-3">
                        <button class="cancel-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            Abbrechen
                        </button>
                        <button class="confirm-btn px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                            Bestätigen
                        </button>
                    </div>
                </div>
            `;

            modal.querySelector('.cancel-btn').addEventListener('click', () => {
                modal.remove();
                resolve(false);
            });

            modal.querySelector('.confirm-btn').addEventListener('click', () => {
                modal.remove();
                resolve(true);
            });

            document.body.appendChild(modal);
        });
    }
}

// Port Forward Manager initialisieren
const portForwardManager = new PortForwardManager();

// Globale Funktionen für Template-Kompatibilität
window.useTemplate = (service) => portForwardManager.useTemplate(service);
window.updateServiceInfo = () => portForwardManager.updateServiceInfo();
window.removePortForward = (ruleId) => portForwardManager.removePortForward(ruleId);