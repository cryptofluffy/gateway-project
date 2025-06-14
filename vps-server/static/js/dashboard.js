/**
 * Dashboard JavaScript - WireGuard Gateway Management
 * Optimierte Version mit Modularer Struktur
 */

class DashboardManager {
    constructor() {
        this.initializeEventListeners();
        this.loadingOverlay = this.createLoadingOverlay();
        this.loadNetworkInterfaces();
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

        // Netzwerkschnittstellen-Auswahl
        const wanSelect = document.getElementById('wan_interface');
        const lanSelect = document.getElementById('lan_interface');
        
        if (wanSelect) {
            wanSelect.addEventListener('change', () => this.handleInterfaceChange());
        }
        if (lanSelect) {
            lanSelect.addEventListener('change', () => this.handleInterfaceChange());
        }

        // Auto-refresh für Status-Updates
        this.startAutoRefresh();
    }

    /**
     * Netzwerkschnittstellen-Änderung behandeln
     */
    handleInterfaceChange() {
        const wanSelect = document.getElementById('wan_interface');
        const lanSelect = document.getElementById('lan_interface');
        const customDiv = document.getElementById('custom-interfaces');
        
        if (!wanSelect || !lanSelect || !customDiv) return;
        
        const showCustom = wanSelect.value === 'custom' || lanSelect.value === 'custom';
        
        if (showCustom) {
            customDiv.classList.remove('hidden');
        } else {
            customDiv.classList.add('hidden');
        }
        
        // Warnung bei gleicher Interface-Auswahl
        if (wanSelect.value === lanSelect.value && wanSelect.value !== 'auto' && wanSelect.value !== 'custom') {
            this.showWarning('⚠️ WAN und LAN verwenden das gleiche Interface. Das könnte zu Problemen führen.');
        }
    }

    /**
     * Gateway-Client hinzufügen
     */
    async handleAddGateway(event) {
        event.preventDefault();
        
        const formData = new FormData(event.target);
        
        // Robuste Datensammlung - Fallback zu getElementById falls FormData fehlschlägt
        const getName = () => formData.get('gateway_name')?.trim() || document.getElementById('gateway_name')?.value?.trim() || '';
        const getLocation = () => formData.get('gateway_location')?.trim() || document.getElementById('gateway_location')?.value?.trim() || '';
        const getPublicKey = () => formData.get('gateway_public_key')?.trim() || document.getElementById('gateway_public_key')?.value?.trim() || '';
        
        // Netzwerkschnittstellen-Konfiguration sammeln
        const wanInterface = formData.get('wan_interface') || 'auto';
        const lanInterface = formData.get('lan_interface') || 'auto';
        const customWan = formData.get('custom_wan')?.trim();
        const customLan = formData.get('custom_lan')?.trim();
        
        const data = {
            name: getName(),
            location: getLocation(),
            public_key: getPublicKey(),
            network_config: {
                wan_interface: wanInterface === 'custom' ? customWan : wanInterface,
                lan_interface: lanInterface === 'custom' ? customLan : lanInterface,
                auto_detect: wanInterface === 'auto' || lanInterface === 'auto'
            }
        };

        // Debug-Ausgabe
        console.log('Form data being sent:', data);

        // Client-seitige Validierung
        const validation = this.validateGatewayData(data);
        if (!validation.valid) {
            this.showError(validation.message);
            return;
        }

        this.showLoading(i18n ? i18n.translate('notifications.gateway_adding') : 'Gateway wird hinzugefügt...');

        try {
            console.log('Sending request to /api/clients with data:', JSON.stringify(data, null, 2));
            
            const response = await this.apiRequest('/api/clients', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            });

            console.log('Response status:', response.status);
            console.log('Response headers:', response.headers);

            const result = await response.json();
            console.log('Response body:', result);

            if (result.success) {
                this.showSuccess(i18n ? i18n.translate('notifications.gateway_added') : 'Gateway-Client erfolgreich hinzugefügt!');
                // Form zurücksetzen
                event.target.reset();
                setTimeout(() => location.reload(), 1500);
            } else {
                this.showError(result.message || 'Unbekannter Fehler');
            }
        } catch (error) {
            console.error('Error details:', error);
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
            
            // Netzwerkschnittstellen-Konfiguration sammeln
            const wanInterface = formData.get('edit_wan_interface') || 'auto';
            const lanInterface = formData.get('edit_lan_interface') || 'auto';
            const customWan = formData.get('edit_custom_wan')?.trim();
            const customLan = formData.get('edit_custom_lan')?.trim();
            
            const data = {
                public_key: publicKey,
                name: formData.get('edit_name')?.trim(),
                location: formData.get('edit_location')?.trim(),
                network_config: {
                    wan_interface: wanInterface === 'custom' ? customWan : wanInterface,
                    lan_interface: lanInterface === 'custom' ? customLan : lanInterface,
                    auto_detect: wanInterface === 'auto' || lanInterface === 'auto'
                }
            };

            const validation = this.validateGatewayData(data);
            if (!validation.valid) {
                this.showError(validation.message);
                return;
            }

            // Kritische Änderungen erfordern Rollback-Bestätigung
            const isCriticalChange = this.isCriticalNetworkChange(data.network_config);
            if (isCriticalChange) {
                const confirmed = await this.showRollbackWarning();
                if (!confirmed) return;
            }

            this.showLoading(i18n ? i18n.translate('notifications.client_editing') : 'Client wird bearbeitet...');

            try {
                // Backup der aktuellen Konfiguration vor Änderung
                const backupConfig = isCriticalChange ? await this.backupCurrentConfig(publicKey) : null;

                const response = await this.apiRequest('/api/clients', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(data)
                });

                const result = await response.json();

                if (result.success) {
                    modal.remove();
                    
                    if (isCriticalChange && backupConfig) {
                        // Starte 2-Minuten-Rollback-Timer
                        this.startRollbackTimer(publicKey, backupConfig);
                    } else {
                        this.showSuccess(i18n ? i18n.translate('notifications.client_edited') : 'Client erfolgreich bearbeitet');
                        setTimeout(() => location.reload(), 1500);
                    }
                } else {
                    this.showError(result.message || 'Unbekannter Fehler');
                }
            } catch (error) {
                this.showError(`Netzwerk-Fehler: ${error.message}`);
            } finally {
                this.hideLoading();
            }
        });
    }

    /**
     * Client entfernen
     */
    async removeClient(publicKey) {
        const confirmed = await this.showConfirmDialog(
            i18n ? i18n.translate('notifications.confirm_remove') : 'Client entfernen?',
            i18n ? i18n.translate('notifications.confirm_remove_message') : 'Diese Aktion kann nicht rückgängig gemacht werden.'
        );

        if (!confirmed) return;

        this.showLoading(i18n ? i18n.translate('notifications.client_removing') : 'Client wird entfernt...');

        try {
            const response = await this.apiRequest(`/api/clients?public_key=${encodeURIComponent(publicKey)}`, {
                method: 'DELETE'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(i18n ? i18n.translate('notifications.client_removed') : 'Client erfolgreich entfernt');
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
            i18n ? i18n.translate('notifications.confirm_restart') : 'WireGuard Interface neu starten?',
            i18n ? i18n.translate('notifications.confirm_restart_message') : 'Dies kann zu kurzen Verbindungsunterbrechungen führen.'
        );

        if (!confirmed) return;

        this.showLoading(i18n ? i18n.translate('notifications.wireguard_restarting') : 'Interface wird neu gestartet...');

        try {
            const response = await this.apiRequest('/api/restart-wireguard', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess(i18n ? i18n.translate('notifications.wireguard_restarted') : 'WireGuard erfolgreich neu gestartet');
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
     * API-Request mit verbesserter Fehlerbehandlung
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

        console.log(`Making ${mergedOptions.method || 'GET'} request to:`, url);
        console.log('Request options:', mergedOptions);

        const response = await fetch(url, mergedOptions);
        
        console.log('Response received:', {
            status: response.status,
            statusText: response.statusText,
            ok: response.ok,
            headers: Object.fromEntries(response.headers.entries())
        });
        
        if (!response.ok) {
            let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
            
            // Versuche detailliertere Fehlermeldung aus Response zu extrahieren
            try {
                const errorBody = await response.text();
                console.log('Error response body:', errorBody);
                
                // Versuche JSON zu parsen
                try {
                    const errorJson = JSON.parse(errorBody);
                    if (errorJson.message) {
                        errorMessage = errorJson.message;
                    }
                } catch (e) {
                    // Fallback zu Text-Response
                    if (errorBody) {
                        errorMessage = errorBody;
                    }
                }
            } catch (e) {
                console.warn('Could not read error response body:', e);
            }
            
            if (response.status === 429) {
                throw new Error('Zu viele Anfragen. Bitte warten Sie einen Moment.');
            } else if (response.status === 400) {
                throw new Error(`Ungültige Anfrage: ${errorMessage}`);
            } else if (response.status === 500) {
                throw new Error(`Server-Fehler: ${errorMessage}`);
            }
            
            throw new Error(errorMessage);
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

        if (!data.public_key || data.public_key.trim().length < 20) {
            return { valid: false, message: 'Gültiger WireGuard Public Key erforderlich' };
        }

        // WireGuard Key Format prüfen (lockerer Base64 Check)
        const keyPattern = /^[A-Za-z0-9+/]+=*$/;
        if (!keyPattern.test(data.public_key.trim())) {
            return { valid: false, message: 'Ungültiges WireGuard Key Format (Base64 erwartet)' };
        }

        if (data.location && data.location.length > 100) {
            return { valid: false, message: 'Standort-Beschreibung ist zu lang (max. 100 Zeichen)' };
        }

        // Netzwerkschnittstellen-Validierung
        if (data.network_config) {
            const { wan_interface, lan_interface } = data.network_config;
            
            // Custom Interface-Validierung
            if (wan_interface === '' && document.getElementById('wan_interface')?.value === 'custom') {
                return { valid: false, message: 'Custom WAN Interface ist erforderlich' };
            }
            
            if (lan_interface === '' && document.getElementById('lan_interface')?.value === 'custom') {
                return { valid: false, message: 'Custom LAN Interface ist erforderlich' };
            }
            
            // Interface-Name-Validierung
            const interfacePattern = /^[a-zA-Z0-9]+$/;
            if (wan_interface && wan_interface !== 'auto' && !interfacePattern.test(wan_interface)) {
                return { valid: false, message: 'Ungültiger WAN Interface Name (nur Buchstaben und Zahlen)' };
            }
            
            if (lan_interface && lan_interface !== 'auto' && !interfacePattern.test(lan_interface)) {
                return { valid: false, message: 'Ungültiger LAN Interface Name (nur Buchstaben und Zahlen)' };
            }
        }

        return { valid: true };
    }

    /**
     * Netzwerkschnittstellen laden und Dropdown befüllen mit Caching
     */
    async loadNetworkInterfaces() {
        // Bereits geladen? Verwende Cache
        if (this.lastLoadedInterfaces && this.lastInterfaceLoadTime) {
            const cacheAge = Date.now() - this.lastInterfaceLoadTime;
            if (cacheAge < 60000) { // 60 Sekunden Cache
                this.populateInterfaceDropdowns(this.lastLoadedInterfaces);
                return;
            }
        }
        
        try {
            const response = await this.apiRequest('/api/network-interfaces');
            const result = await response.json();
            
            if (result.success && result.interfaces) {
                this.lastLoadedInterfaces = result.interfaces;
                this.lastCurrentInterfaces = result.current || {};
                this.lastInterfaceLoadTime = Date.now();
                this.populateInterfaceDropdowns(result);
            }
        } catch (error) {
            console.log('Network interfaces loading failed:', error.message);
            // Fallback zu gecachten Daten
            if (this.lastLoadedInterfaces) {
                const fallbackData = {
                    interfaces: this.lastLoadedInterfaces,
                    current: this.lastCurrentInterfaces || {}
                };
                this.populateInterfaceDropdowns(fallbackData);
            }
        }
    }

    /**
     * Interface-Dropdowns mit erkannten Schnittstellen befüllen
     */
    populateInterfaceDropdowns(data) {
        const wanSelect = document.getElementById('wan_interface');
        const lanSelect = document.getElementById('lan_interface');
        
        if (!wanSelect || !lanSelect) return;
        
        const interfaces = data.interfaces || {};
        const current = data.current || {};
        
        // Dropdowns komplett neu aufbauen
        this.rebuildInterfaceDropdown(wanSelect, interfaces, current.wan, 'wan');
        this.rebuildInterfaceDropdown(lanSelect, interfaces, current.lan, 'lan');
        
        // Auch Edit-Modal-Dropdowns aktualisieren falls vorhanden
        const editWanSelect = document.getElementById('edit_wan_interface');
        const editLanSelect = document.getElementById('edit_lan_interface');
        if (editWanSelect) {
            this.rebuildInterfaceDropdown(editWanSelect, interfaces, current.wan, 'wan');
        }
        if (editLanSelect) {
            this.rebuildInterfaceDropdown(editLanSelect, interfaces, current.lan, 'lan');
        }
    }

    /**
     * Interface-Dropdown komplett neu aufbauen
     */
    rebuildInterfaceDropdown(select, interfaces, currentInterface, type) {
        if (!select) return;
        
        // Aktuelle Auswahl speichern
        const savedValue = select.value;
        
        // Dropdown leeren
        select.innerHTML = '';
        
        // Automatisch erkennen Option (immer zuerst)
        const autoOption = document.createElement('option');
        autoOption.value = 'auto';
        if (currentInterface) {
            autoOption.textContent = `🔄 Automatisch erkennen (aktuell: ${currentInterface})`;
        } else {
            autoOption.textContent = '🔄 Automatisch erkennen';
        }
        select.appendChild(autoOption);
        
        // Gruppierte Interface-Optionen hinzufügen
        const categories = [
            { key: 'ethernet', name: 'Ethernet', icon: '🌐' },
            { key: 'wireless', name: 'WLAN', icon: '📡' },
            { key: 'virtual', name: 'Virtuell', icon: '🔗' },
            { key: 'other', name: 'Andere', icon: '🔌' }
        ];
        
        categories.forEach(category => {
            const interfaceList = interfaces[category.key] || [];
            if (interfaceList.length > 0) {
                // Kategorie-Header hinzufügen
                const optgroup = document.createElement('optgroup');
                optgroup.label = `${category.icon} ${category.name}`;
                
                interfaceList.forEach(iface => {
                    const option = document.createElement('option');
                    option.value = iface.name;
                    
                    let status = iface.status === 'up' ? '✅' : '⚠️';
                    let ip = iface.ip ? ` (${iface.ip})` : '';
                    let isCurrentMarker = '';
                    
                    // Markiere aktuell verwendetes Interface
                    if (iface.name === currentInterface) {
                        isCurrentMarker = ' - AKTUELL';
                        status = '✅';
                    }
                    
                    option.textContent = `${iface.name}${ip} ${status}${isCurrentMarker}`;
                    optgroup.appendChild(option);
                });
                
                select.appendChild(optgroup);
            }
        });
        
        // Benutzerdefiniert Option hinzufügen
        const customOption = document.createElement('option');
        customOption.value = 'custom';
        customOption.textContent = '🔧 Benutzerdefiniert';
        select.appendChild(customOption);
        
        // Auswahl wiederherstellen oder auf aktuelles Interface setzen
        if (savedValue && Array.from(select.options).some(opt => opt.value === savedValue)) {
            select.value = savedValue;
        } else if (currentInterface && Array.from(select.options).some(opt => opt.value === currentInterface)) {
            select.value = currentInterface;
        } else {
            select.value = 'auto';
        }
    }

    /**
     * Auto-Refresh für Status-Updates mit intelligentem Timing
     */
    startAutoRefresh() {
        // Adaptives Refresh-Intervall
        let refreshInterval = 30000; // Start: 30 Sekunden
        let lastActivity = Date.now();
        
        // Aktivitäts-Tracking
        document.addEventListener('click', () => {
            lastActivity = Date.now();
            refreshInterval = 15000; // Bei Aktivität: 15 Sekunden
        });
        
        const refreshFunction = () => {
            const timeSinceActivity = Date.now() - lastActivity;
            
            // Längere Intervalle bei Inaktivität
            if (timeSinceActivity > 300000) { // 5 Minuten inaktiv
                refreshInterval = 120000; // 2 Minuten
            } else if (timeSinceActivity > 60000) { // 1 Minute inaktiv
                refreshInterval = 60000; // 1 Minute
            } else {
                refreshInterval = 30000; // Aktiv: 30 Sekunden
            }
            
            this.updateStatus();
            setTimeout(refreshFunction, refreshInterval);
        };
        
        // Initialer Start
        setTimeout(refreshFunction, refreshInterval);
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
                const isActive = data.iface ? data.iface.status === 'active' : data.interface && data.interface.status === 'active';
                tunnelStatus.className = `inline-block w-4 h-4 ${isActive ? 'bg-green-500' : 'bg-red-500'} rounded-full`;
            }


        } catch (error) {
            console.warn('Status update failed:', error);
        }
    }

    /**
     * Copy to Clipboard mit verbesserter UX und Mehrsprachen-Support
     */
    async copyToClipboard(elementId) {
        const element = document.getElementById(elementId);
        if (!element) {
            console.error(`Element mit ID '${elementId}' nicht gefunden`);
            return;
        }

        const text = element.textContent || element.innerText;
        
        // Finde den zugehörigen Button - verbesserte Selektion
        const button = document.querySelector(`button[onclick="copyToClipboard('${elementId}')"]`) ||
                     document.querySelector(`button[onclick*="${elementId}"]`);

        try {
            // Prüfe ob Clipboard API verfügbar ist (benötigt HTTPS)
            if (!navigator.clipboard) {
                throw new Error('Clipboard API nicht verfügbar');
            }
            await navigator.clipboard.writeText(text);
            
            // Verbessertes visuelles Feedback
            const originalBg = element.style.backgroundColor;
            const originalColor = element.style.color;
            const originalText = element.innerHTML;
            const originalButtonText = button ? button.innerHTML : '';
            const originalButtonClass = button ? button.className : '';

            // Element-Feedback mit Transition
            element.style.transition = 'all 0.3s ease';
            element.style.backgroundColor = '#10B981';
            element.style.color = 'white';
            element.style.padding = '4px';
            element.innerHTML = `✅ ${i18n ? i18n.translate('dashboard.copied') : 'Kopiert!'}`;

            // Button-Feedback
            if (button) {
                button.style.transition = 'all 0.3s ease';
                button.innerHTML = `✅ ${i18n ? i18n.translate('dashboard.copied') : 'Kopiert!'}`;
                button.className = button.className.replace(/bg-\w+-\d+/, 'bg-green-500').replace(/hover:bg-\w+-\d+/, 'hover:bg-green-600');
                button.disabled = true;
            }

            // Erfolgs-Animation
            element.style.transform = 'scale(1.05)';
            setTimeout(() => {
                element.style.transform = 'scale(1)';
            }, 200);

            // Zusätzliche Toast-Notification
            this.showNotification(
                i18n ? i18n.translate('dashboard.copied') : 'In Zwischenablage kopiert!', 
                'success'
            );

            // Reset nach 2.5 Sekunden
            setTimeout(() => {
                element.style.backgroundColor = originalBg;
                element.style.color = originalColor;
                element.style.padding = '';
                element.style.transition = '';
                element.innerHTML = originalText;
                
                if (button) {
                    button.innerHTML = originalButtonText;
                    button.className = originalButtonClass;
                    button.style.transition = '';
                    button.disabled = false;
                }
            }, 2500);

        } catch (error) {
            console.warn('Moderne Clipboard API fehlgeschlagen, verwende Fallback:', error);
            
            // Fallback für HTTP oder ältere Browser
            try {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                
                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);
                
                if (successful) {
                    // Gleiches visuelles Feedback wie bei moderner API
                    const originalBg = element.style.backgroundColor;
                    const originalColor = element.style.color;
                    const originalText = element.innerHTML;
                    const originalButtonText = button ? button.innerHTML : '';
                    const originalButtonClass = button ? button.className : '';

                    // Element-Feedback
                    element.style.transition = 'all 0.3s ease';
                    element.style.backgroundColor = '#10B981';
                    element.style.color = 'white';
                    element.style.padding = '4px';
                    element.innerHTML = `✅ ${i18n ? i18n.translate('dashboard.copied') : 'Kopiert!'}`;

                    // Button-Feedback
                    if (button) {
                        button.style.transition = 'all 0.3s ease';
                        button.innerHTML = `✅ ${i18n ? i18n.translate('dashboard.copied') : 'Kopiert!'}`;
                        button.className = button.className.replace(/bg-\w+-\d+/, 'bg-green-500').replace(/hover:bg-\w+-\d+/, 'hover:bg-green-600');
                        button.disabled = true;
                    }

                    // Erfolgs-Animation
                    element.style.transform = 'scale(1.05)';
                    setTimeout(() => {
                        element.style.transform = 'scale(1)';
                    }, 200);

                    this.showNotification(
                        i18n ? i18n.translate('dashboard.copied') : 'In Zwischenablage kopiert!', 
                        'success'
                    );

                    // Reset nach 2.5 Sekunden
                    setTimeout(() => {
                        element.style.backgroundColor = originalBg;
                        element.style.color = originalColor;
                        element.style.padding = '';
                        element.style.transition = '';
                        element.innerHTML = originalText;
                        
                        if (button) {
                            button.innerHTML = originalButtonText;
                            button.className = originalButtonClass;
                            button.style.transition = '';
                            button.disabled = false;
                        }
                    }, 2500);
                } else {
                    throw new Error('execCommand copy fehlgeschlagen');
                }
            } catch (fallbackError) {
                console.error('Alle Copy-Methoden fehlgeschlagen:', fallbackError);
                
                // Zeige Text zum manuellen Kopieren
                const userText = prompt(
                    i18n ? i18n.translate('dashboard.manual_copy') : 'Kopieren fehlgeschlagen. Bitte manuell markieren und kopieren (Ctrl+C):',
                    text
                );
                
                if (userText !== null) {
                    this.showNotification(
                        i18n ? i18n.translate('dashboard.manual_copy_success') : 'Text zum Kopieren bereitgestellt', 
                        'info'
                    );
                }
            }
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
     * Warnung anzeigen
     */
    showWarning(message) {
        this.showNotification(message, 'warning');
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
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
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
                            ${i18n ? i18n.translate('notifications.cancel') : 'Abbrechen'}
                        </button>
                        <button class="confirm-btn px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                            ${i18n ? i18n.translate('notifications.confirm') : 'Bestätigen'}
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
            <div class="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Client bearbeiten</h3>
                <form class="edit-form space-y-4">
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Gateway Name</label>
                            <input type="text" name="edit_name" required maxlength="50"
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                        <div>
                            <label class="block text-sm font-medium text-gray-700 mb-2">Standort/Beschreibung</label>
                            <input type="text" name="edit_location" maxlength="100"
                                   class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        </div>
                    </div>
                    
                    <!-- Netzwerkschnittstellen-Konfiguration -->
                    <div class="bg-gray-50 rounded-lg p-4">
                        <h4 class="font-medium text-gray-700 mb-3">🌐 Netzwerkschnittstellen-Konfiguration</h4>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">WAN-Interface (Internet)</label>
                                <select name="edit_wan_interface" id="edit_wan_interface" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value="auto">🔄 Automatisch erkennen</option>
                                    <option value="custom">🔧 Benutzerdefiniert</option>
                                </select>
                            </div>
                            
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">LAN-Interface (Server)</label>
                                <select name="edit_lan_interface" id="edit_lan_interface" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                                    <option value="auto">🔄 Automatisch erkennen</option>
                                    <option value="custom">🔧 Benutzerdefiniert</option>
                                </select>
                            </div>
                        </div>
                        
                        <!-- Custom Interface Inputs -->
                        <div class="edit-custom-interfaces grid grid-cols-1 md:grid-cols-2 gap-4 mt-3 hidden">
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Custom WAN Interface</label>
                                <input type="text" name="edit_custom_wan" placeholder="z.B. wlp2s0"
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700 mb-2">Custom LAN Interface</label>
                                <input type="text" name="edit_custom_lan" placeholder="z.B. enp3s0"
                                       class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                            </div>
                        </div>
                        
                        <div class="mt-3 p-3 bg-blue-50 rounded border-l-4 border-blue-400">
                            <div class="text-sm text-blue-800">
                                💡 <strong>Interface-Zuordnung:</strong> WAN für VPS-Verbindung, LAN für Server-Netzwerk<br>
                                🔄 <strong>Automatisch:</strong> Gateway wählt beste verfügbare Interfaces
                            </div>
                        </div>
                    </div>
                    
                    <div class="flex justify-end space-x-3">
                        <button type="button" class="cancel-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            ${i18n ? i18n.translate('notifications.cancel') : 'Abbrechen'}
                        </button>
                        <button type="submit" class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">
                            ${i18n ? i18n.translate('notifications.save') : 'Speichern'}
                        </button>
                    </div>
                </form>
            </div>
        `;

        // Event Listeners für Custom Interface Handling
        const wanSelect = modal.querySelector('select[name="edit_wan_interface"]');
        const lanSelect = modal.querySelector('select[name="edit_lan_interface"]');
        const customDiv = modal.querySelector('.edit-custom-interfaces');
        
        const updateCustomInputs = () => {
            const showCustom = wanSelect.value === 'custom' || lanSelect.value === 'custom';
            if (showCustom) {
                customDiv.classList.remove('hidden');
            } else {
                customDiv.classList.add('hidden');
            }
        };
        
        wanSelect.addEventListener('change', updateCustomInputs);
        lanSelect.addEventListener('change', updateCustomInputs);

        modal.querySelector('.cancel-btn').addEventListener('click', () => {
            modal.remove();
        });

        // Client-Daten laden und in Form einsetzen
        this.loadClientDataIntoEditForm(modal, publicKey);

        return modal;
    }

    /**
     * Client-Daten in Edit-Form laden
     */
    async loadClientDataIntoEditForm(modal, publicKey) {
        try {
            // Client-Daten vom Server abrufen
            const response = await this.apiRequest('/api/clients');
            const clients = await response.json();
            
            // Client mit matchendem Public Key finden (clients ist ein Array)
            const client = Array.isArray(clients) 
                ? clients.find(c => c.public_key === publicKey)
                : null;
                
            if (!client) {
                this.showError(i18n ? i18n.translate('notifications.error_unknown') : 'Client nicht gefunden');
                modal.remove();
                return;
            }
            
            // Form-Felder befüllen
            modal.querySelector('input[name="edit_name"]').value = client.name || '';
            modal.querySelector('input[name="edit_location"]').value = client.location || '';
            
            // Netzwerkschnittstellen-Konfiguration laden
            if (client.network_config) {
                const wanSelect = modal.querySelector('select[name="edit_wan_interface"]');
                const lanSelect = modal.querySelector('select[name="edit_lan_interface"]');
                const customWanInput = modal.querySelector('input[name="edit_custom_wan"]');
                const customLanInput = modal.querySelector('input[name="edit_custom_lan"]');
                
                const wanInterface = client.network_config.wan_interface || 'auto';
                const lanInterface = client.network_config.lan_interface || 'auto';
                
                // Standard-Interfaces setzen oder custom wählen
                const setInterfaceValue = (select, customInput, value) => {
                    const option = Array.from(select.options).find(opt => opt.value === value);
                    if (option) {
                        select.value = value;
                    } else if (value && value !== 'auto') {
                        select.value = 'custom';
                        customInput.value = value;
                    } else {
                        select.value = 'auto';
                    }
                };
                
                setInterfaceValue(wanSelect, customWanInput, wanInterface);
                setInterfaceValue(lanSelect, customLanInput, lanInterface);
                
                // Custom Inputs anzeigen falls nötig
                const showCustom = wanSelect.value === 'custom' || lanSelect.value === 'custom';
                if (showCustom) {
                    modal.querySelector('.edit-custom-interfaces').classList.remove('hidden');
                }
            }
            
            // Verfügbare Interfaces zu Dropdowns hinzufügen
            this.populateEditInterfaceDropdowns(modal);
            
        } catch (error) {
            console.error('Error loading client data:', error);
            this.showError('Fehler beim Laden der Client-Daten');
        }
    }

    /**
     * Interface-Dropdowns im Edit-Modal befüllen
     */
    async populateEditInterfaceDropdowns(modal) {
        // Lade aktuelle Interface-Daten falls nicht vorhanden
        if (!this.lastLoadedInterfaces) {
            await this.loadNetworkInterfaces();
        }
        
        // Verwende die neue rebuild-Funktion für konsistente Darstellung
        if (this.lastLoadedInterfaces) {
            const wanSelect = modal.querySelector('select[name="edit_wan_interface"]');
            const lanSelect = modal.querySelector('select[name="edit_lan_interface"]');
            
            const data = {
                interfaces: this.lastLoadedInterfaces,
                current: this.lastCurrentInterfaces || {}
            };
            
            if (wanSelect) {
                this.rebuildInterfaceDropdown(wanSelect, data.interfaces, data.current.wan, 'wan');
            }
            if (lanSelect) {
                this.rebuildInterfaceDropdown(lanSelect, data.interfaces, data.current.lan, 'lan');
            }
        }
    }

    /**
     * Interface-Option zu Select hinzufügen
     */
    addInterfaceOptionToSelect(select, iface, category) {
        const option = document.createElement('option');
        option.value = iface.name;
        
        let icon = '🔌';
        if (category === 'ethernet') icon = '🌐';
        if (category === 'wireless') icon = '📡';
        if (category === 'virtual') icon = '🔗';
        
        let status = iface.status === 'up' ? '✅' : '⚠️';
        let ip = iface.ip ? ` (${iface.ip})` : '';
        
        option.textContent = `${icon} ${iface.name}${ip} ${status}`;
        
        // Nur hinzufügen wenn noch nicht vorhanden
        const exists = Array.from(select.options).some(opt => opt.value === iface.name);
        if (!exists) {
            select.appendChild(option);
        }
    }

    /**
     * Prüft ob eine Netzwerk-Änderung kritisch ist (Rollback erforderlich)
     */
    isCriticalNetworkChange(newConfig) {
        // Änderungen an Netzwerkschnittstellen sind immer kritisch
        return newConfig.wan_interface !== 'auto' || newConfig.lan_interface !== 'auto';
    }

    /**
     * Zeigt Warnung vor kritischen Änderungen mit Rollback-Hinweis
     */
    async showRollbackWarning() {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
            modal.innerHTML = `
                <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                    <div class="flex items-center mb-4">
                        <div class="flex-shrink-0">
                            <svg class="h-8 w-8 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L4.35 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                            </svg>
                        </div>
                        <div class="ml-3">
                            <h3 class="text-lg font-semibold text-gray-900">Kritische Netzwerk-Änderung</h3>
                        </div>
                    </div>
                    <div class="mb-6">
                        <p class="text-gray-600 mb-3">
                            Sie sind dabei, kritische Netzwerkeinstellungen zu ändern. Dies kann zu Verbindungsabbrüchen führen.
                        </p>
                        <div class="bg-orange-50 border border-orange-200 rounded-lg p-3">
                            <div class="flex">
                                <div class="flex-shrink-0">
                                    <svg class="h-5 w-5 text-orange-400" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd"></path>
                                    </svg>
                                </div>
                                <div class="ml-3">
                                    <h4 class="text-sm font-medium text-orange-800">Automatisches Rollback</h4>
                                    <p class="text-sm text-orange-700 mt-1">
                                        Die Änderungen werden in <strong>2 Minuten automatisch rückgängig gemacht</strong>, falls Sie sie nicht bestätigen.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="flex justify-end space-x-3">
                        <button class="cancel-btn px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            Abbrechen
                        </button>
                        <button class="confirm-btn px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition-colors">
                            Trotzdem ändern
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
     * Aktuelle Konfiguration als Backup speichern
     */
    async backupCurrentConfig(publicKey) {
        try {
            const response = await this.apiRequest(`/api/clients`);
            const clients = await response.json();
            
            if (Array.isArray(clients)) {
                const client = clients.find(c => c.public_key === publicKey);
                return client ? {
                    public_key: publicKey,
                    name: client.name,
                    location: client.location,
                    network_config: client.network_config
                } : null;
            }
        } catch (error) {
            console.error('Error backing up config:', error);
        }
        return null;
    }

    /**
     * Startet 2-Minuten Rollback-Timer mit Bestätigungsdialog
     */
    startRollbackTimer(publicKey, backupConfig) {
        let timeLeft = 120; // 2 Minuten
        let rollbackTimer;
        let countdownInterval;

        // Erstelle Rollback-Bestätigungsdialog
        const rollbackModal = document.createElement('div');
        rollbackModal.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
        rollbackModal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <div class="flex items-center mb-4">
                    <div class="flex-shrink-0">
                        <svg class="h-8 w-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                    </div>
                    <div class="ml-3">
                        <h3 class="text-lg font-semibold text-gray-900">Änderungen erfolgreich</h3>
                    </div>
                </div>
                <div class="mb-6">
                    <p class="text-gray-600 mb-3">
                        Die Netzwerkeinstellungen wurden geändert. Bestätigen Sie die Änderungen innerhalb von <span class="countdown font-bold text-red-600">2:00</span> Minuten, oder sie werden automatisch rückgängig gemacht.
                    </p>
                    <div class="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <p class="text-sm text-blue-700">
                            💡 Testen Sie jetzt die Verbindung und bestätigen Sie die Änderungen nur, wenn alles funktioniert.
                        </p>
                    </div>
                </div>
                <div class="flex justify-end space-x-3">
                    <button class="rollback-btn px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition-colors">
                        Jetzt rückgängig machen
                    </button>
                    <button class="confirm-btn px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                        Änderungen bestätigen
                    </button>
                </div>
            </div>
        `;

        const countdownElement = rollbackModal.querySelector('.countdown');

        // Countdown-Update-Funktion
        const updateCountdown = () => {
            const minutes = Math.floor(timeLeft / 60);
            const seconds = timeLeft % 60;
            countdownElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            
            if (timeLeft <= 30) {
                countdownElement.className = 'countdown font-bold text-red-600 animate-pulse';
            }
        };

        // Rollback-Timer starten
        rollbackTimer = setTimeout(async () => {
            await this.performRollback(publicKey, backupConfig);
            rollbackModal.remove();
        }, timeLeft * 1000);

        // Countdown-Interval starten
        countdownInterval = setInterval(() => {
            timeLeft--;
            updateCountdown();
            
            if (timeLeft <= 0) {
                clearInterval(countdownInterval);
            }
        }, 1000);

        // Event Listeners
        rollbackModal.querySelector('.confirm-btn').addEventListener('click', () => {
            clearTimeout(rollbackTimer);
            clearInterval(countdownInterval);
            rollbackModal.remove();
            this.showSuccess('Änderungen erfolgreich bestätigt');
            setTimeout(() => location.reload(), 1500);
        });

        rollbackModal.querySelector('.rollback-btn').addEventListener('click', async () => {
            clearTimeout(rollbackTimer);
            clearInterval(countdownInterval);
            await this.performRollback(publicKey, backupConfig);
            rollbackModal.remove();
        });

        document.body.appendChild(rollbackModal);
        updateCountdown();
    }

    /**
     * Führt Rollback zur vorherigen Konfiguration durch
     */
    async performRollback(publicKey, backupConfig) {
        this.showLoading('Konfiguration wird wiederhergestellt...');
        
        try {
            const response = await this.apiRequest('/api/clients', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(backupConfig)
            });

            const result = await response.json();

            if (result.success) {
                this.showSuccess('Konfiguration erfolgreich wiederhergestellt');
            } else {
                this.showError('Fehler beim Wiederherstellen der Konfiguration');
            }
        } catch (error) {
            this.showError(`Rollback-Fehler: ${error.message}`);
        } finally {
            this.hideLoading();
            setTimeout(() => location.reload(), 2000);
        }
    }
}

// Dashboard Manager initialisieren
const dashboardManager = new DashboardManager();

// Globale Funktionen für Template-Kompatibilität
window.copyToClipboard = (elementId) => dashboardManager.copyToClipboard(elementId);
window.editClient = (publicKey) => dashboardManager.editClient(publicKey);
window.removeClient = (publicKey) => dashboardManager.removeClient(publicKey);
window.restartWireGuard = () => dashboardManager.restartWireGuard();