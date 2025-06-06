/**
 * Dashboard JavaScript - WireGuard Gateway Management
 * Optimierte Version mit Modularer Struktur
 */

class DashboardManager {
    constructor() {
        this.initializeEventListeners();
        this.loadingOverlay = this.createLoadingOverlay();
    }

    /**
     * Initialisiert alle Event Listener
     */
    initializeEventListeners() {
        // Gateway-Client Management
        const addGatewayForm = document.getElementById('add-gateway-form');
        if (addGatewayForm) {
            addGatewayForm.addEventListener('submit', (e) => this.handleAddGateway(e));
        }

        // Auto-refresh für Status-Updates
        this.startAutoRefresh();
    }

    /**
     * Gateway-Client hinzufügen
     */
    async handleAddGateway(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        const data = {
            name: formData.get('gateway_name')?.trim(),
            location: formData.get('gateway_location')?.trim(),
            public_key: formData.get('gateway_public_key')?.trim()
        };

        // Client-seitige Validierung
        const validation = this.validateGatewayData(data);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        this.showLoading('Gateway wird hinzugefügt...');

        try {
            const response = await this.apiRequest('/api/clients', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Gateway-Client erfolgreich hinzugefügt!');
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
     * Client bearbeiten
     */
    async editClient(publicKey) {
        // Verwende Modal statt Prompt für bessere UX
        const modal = this.createEditModal(publicKey);
        document.body.appendChild(modal);
        
        modal.querySelector('.edit-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(e.target);
            const data = {
                public_key: publicKey,
                name: formData.get('edit_name')?.trim(),
                location: formData.get('edit_location')?.trim()
            };

            const validation = this.validateGatewayData(data);
            if (!validation.valid) {
                this.showError(validation.message);
                return;
            }

            this.showLoading('Client wird bearbeitet...');

            try {
                const response = await this.apiRequest('/api/clients', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    this.showSuccess('Client erfolgreich bearbeitet');
                    setTimeout(() => location.reload(), 1500);
                } else {
                    this.showError(result.message || 'Unbekannter Fehler');
                }
            } catch (error) {
                this.showError(`Netzwerk-Fehler: ${error.message}`);
            } finally {
                this.hideLoading();
                modal.remove();
            }
        });
    }

    /**
     * Client entfernen
     */
    async removeClient(publicKey) {
        const confirmed = await this.showConfirmDialog(
            'Client entfernen?',
            'Diese Aktion kann nicht rückgängig gemacht werden.'
        );

        if (!confirmed) return;

        this.showLoading('Client wird entfernt...');

        try {
            const response = await this.apiRequest(`/api/clients?public_key=${encodeURIComponent(publicKey)}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Client erfolgreich entfernt');
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
     * WireGuard Interface neu starten
     */
    async restartWireGuard() {
        const confirmed = await this.showConfirmDialog(
            'WireGuard Interface neu starten?',
            'Dies kann zu kurzen Verbindungsunterbrechungen führen.'
        );

        if (!confirmed) return;

        this.showLoading('Interface wird neu gestartet...');

        try {
            const response = await this.apiRequest('/api/restart-wireguard', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('WireGuard erfolgreich neu gestartet');
                setTimeout(() => location.reload(), 3000);
            } else {
                this.showError(result.message || 'Fehler beim Neustart');
            }
        } catch (error) {
            this.showError(`Netzwerk-Fehler: ${error.message}`);
        } finally {
            this.hideLoading();
        }
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
     * Validierung für Gateway-Daten
     */
    validateGatewayData(data) {
        if (!data.name || data.name.length < 1) {
            return { valid: false, message: 'Gateway-Name ist erforderlich' };
        }

        if (data.name.length > 50) {
            return { valid: false, message: 'Gateway-Name ist zu lang (max. 50 Zeichen)' };
        }

        if (!data.public_key || data.public_key.length < 40) {
            return { valid: false, message: 'Gültiger WireGuard Public Key erforderlich' };
        }

        // WireGuard Key Format prüfen (Base64)
        const keyPattern = /^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw048]=?$/;
        if (!keyPattern.test(data.public_key)) {
            return { valid: false, message: 'Ungültiges WireGuard Key Format' };
        }

        if (data.location && data.location.length > 100) {
            return { valid: false, message: 'Standort-Beschreibung ist zu lang (max. 100 Zeichen)' };
        }

        return { valid: true };
    }

    /**
     * Auto-Refresh für Status-Updates
     */
    startAutoRefresh() {
        // Refresh alle 30 Sekunden
        setInterval(() => {
            this.updateStatus();
        }, 30000);
    }

    /**
     * Status-Update ohne komplettes Reload
     */
    async updateStatus() {
        try {
            const response = await this.apiRequest('/api/status');
            const data = await response.json();

            // Update Client-Count
            const clientCount = document.getElementById('client-count');
            if (clientCount) {
                clientCount.textContent = data.clients.length;
            }

            // Update Tunnel-Status
            const tunnelStatus = document.getElementById('tunnel-status');
            if (tunnelStatus) {
                const isActive = data.interface.status === 'active';
                tunnelStatus.className = `inline-block w-4 h-4 ${isActive ? 'bg-green-500' : 'bg-red-500'} rounded-full`;
            }

        } catch (error) {
            console.warn('Status update failed:', error);
        }
    }

    /**
     * Copy to Clipboard mit besserer UX
     */
    async copyToClipboard(elementId) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const text = element.textContent || element.innerText;

        try {
            await navigator.clipboard.writeText(text);
            
            // Visuelles Feedback
            const originalBg = element.style.backgroundColor;
            const originalColor = element.style.color;
            const originalText = element.innerHTML;

            element.style.backgroundColor = '#10B981';
            element.style.color = 'white';
            element.innerHTML = '✅ Kopiert!';

            setTimeout(() => {
                element.style.backgroundColor = originalBg;
                element.style.color = originalColor;
                element.innerHTML = originalText;
            }, 2000);

        } catch (error) {
            this.showError('Fehler beim Kopieren in die Zwischenablage');
        }
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

    /**
     * Edit-Modal erstellen
     */
    createEditModal(publicKey) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Client bearbeiten</h3>
                <form class="edit-form">
                    <div class="mb-4">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Gateway Name</label>
                        <input type="text" name="edit_name" required maxlength="50"
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                    </div>
                    <div class="mb-6">
                        <label class="block text-sm font-medium text-gray-700 mb-2">Standort/Beschreibung</label>
                        <input type="text" name="edit_location" maxlength="100"
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                    </div>
                    <div class="flex justify-end space-x-3">
                        <button type="button" class="cancel-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            Abbrechen
                        </button>
                        <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                            Speichern
                        </button>
                    </div>
                </form>
            </div>
        `;

        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });

        return modal;
    }
}

// Dashboard Manager initialisieren
const dashboardManager = new DashboardManager();

// Globale Funktionen für Template-Kompatibilität
window.copyToClipboard = (elementId) => dashboardManager.copyToClipboard(elementId);
window.editClient = (publicKey) => dashboardManager.editClient(publicKey);
window.removeClient = (publicKey) => dashboardManager.removeClient(publicKey);
window.restartWireGuard = () => dashboardManager.restartWireGuard();