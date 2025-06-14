/**
 * Device Manager JavaScript - Server Device Discovery and Port Forwarding
 */

class DeviceManager {
    constructor() {
        this.refreshInterval = null;
        this.lastDeviceData = null;
        this.init();
    }

    init() {
        // Load devices on page load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.loadDevices());
        } else {
            this.loadDevices();
        }

        // Start auto-refresh
        this.startAutoRefresh();
    }

    startAutoRefresh() {
        // Refresh devices every 30 seconds
        this.refreshInterval = setInterval(() => {
            this.loadDevices();
        }, 30000);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async loadDevices() {
        try {
            const response = await fetch('/api/devices');
            const data = await response.json();
            
            this.lastDeviceData = data;
            this.updateDevicesDisplay(data);
            this.updateDeviceDropdown(data);
            this.updateDeviceCount(data);
        } catch (error) {
            console.error('Error loading devices:', error);
            this.showError('Fehler beim Laden der Geräte');
        }
    }

    updateDevicesDisplay(data) {
        const container = document.getElementById('devices-container');
        if (!container) return;

        if (!data.success || !data.devices || data.devices.length === 0) {
            container.innerHTML = `
                <div class="text-center py-8">
                    <div class="text-gray-400 mb-2">
                        <svg class="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2"></path>
                        </svg>
                    </div>
                    <p class="text-gray-500 italic">Keine Server-Geräte erkannt</p>
                    <p class="text-sm text-gray-400 mt-1">Stelle sicher, dass der Network Scanner läuft</p>
                    <button onclick="deviceManager.loadDevices()" class="mt-3 bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm">
                        🔄 Erneut versuchen
                    </button>
                </div>
            `;
            return;
        }

        const devicesHtml = data.devices.map(device => `
            <div class="flex justify-between items-center p-4 bg-gray-50 rounded-lg border hover:bg-gray-100 transition-colors">
                <div class="flex items-center space-x-4">
                    <div class="w-3 h-3 ${device.status === 'connected' ? 'bg-green-500' : 'bg-gray-400'} rounded-full"></div>
                    <div>
                        <h4 class="font-medium text-gray-900">${this.escapeHtml(device.name || 'Unbekanntes Gerät')}</h4>
                        <p class="text-sm text-gray-600">IP: ${device.ip}</p>
                        ${device.hostname ? `<p class="text-xs text-gray-500">Hostname: ${this.escapeHtml(device.hostname)}</p>` : ''}
                        ${device.mac ? `<p class="text-xs text-gray-500">MAC: ${device.mac}</p>` : ''}
                    </div>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="px-2 py-1 text-xs rounded-full ${device.status === 'connected' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}">
                        ${device.status}
                    </span>
                    <button onclick="deviceManager.showPortForwardDialog('${device.ip}', '${this.escapeHtml(device.name || device.ip)}')" 
                            class="bg-blue-500 hover:bg-blue-600 text-white px-3 py-1 rounded text-sm transition-colors">
                        🔗 Port freigeben
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = devicesHtml;
    }

    updateDeviceDropdown(data) {
        const dropdown = document.getElementById('quick-device');
        if (!dropdown) return;

        // Clear existing options except first
        dropdown.innerHTML = '<option value="">Gerät wählen...</option>';

        if (data.success && data.devices) {
            data.devices.forEach(device => {
                const option = document.createElement('option');
                option.value = device.ip;
                option.textContent = `${device.name || device.ip} (${device.ip})`;
                dropdown.appendChild(option);
            });
        }
    }

    updateDeviceCount(data) {
        const countElement = document.getElementById('device-count');
        if (countElement) {
            const count = data.success ? (data.devices ? data.devices.length : 0) : 0;
            countElement.textContent = count;
        }
    }

    showPortForwardDialog(deviceIp, deviceName) {
        const modal = document.createElement('div');
        modal.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
        modal.innerHTML = `
            <div class="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Port-Weiterleitung erstellen</h3>
                <p class="text-sm text-gray-600 mb-4">Für Gerät: <strong>${this.escapeHtml(deviceName)} (${deviceIp})</strong></p>
                
                <form class="space-y-4">
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Externer Port</label>
                        <input type="number" id="modal-ext-port" placeholder="z.B. 8080" min="1" max="65535" required
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-500 mt-1">Der Port über den das Gerät von außen erreichbar ist</p>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Interner Port</label>
                        <input type="number" id="modal-int-port" placeholder="z.B. 80" min="1" max="65535" required
                               class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                        <p class="text-xs text-gray-500 mt-1">Der Port auf dem das Gerät den Service anbietet</p>
                    </div>
                    
                    <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Protokoll</label>
                        <select id="modal-protocol" class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500">
                            <option value="tcp">TCP (Web, SSH, etc.)</option>
                            <option value="udp">UDP (DNS, Games, etc.)</option>
                        </select>
                    </div>
                    
                    <!-- Common service presets -->
                    <div class="bg-blue-50 rounded-lg p-3">
                        <p class="text-sm font-medium text-blue-800 mb-2">🚀 Häufige Services:</p>
                        <div class="grid grid-cols-2 gap-2 text-xs">
                            <button type="button" onclick="deviceManager.setPortPreset(80, 80, 'tcp')" class="bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded">
                                HTTP (80)
                            </button>
                            <button type="button" onclick="deviceManager.setPortPreset(443, 443, 'tcp')" class="bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded">
                                HTTPS (443)
                            </button>
                            <button type="button" onclick="deviceManager.setPortPreset(22, 22, 'tcp')" class="bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded">
                                SSH (22)
                            </button>
                            <button type="button" onclick="deviceManager.setPortPreset(3389, 3389, 'tcp')" class="bg-blue-100 hover:bg-blue-200 text-blue-800 px-2 py-1 rounded">
                                RDP (3389)
                            </button>
                        </div>
                    </div>
                    
                    <div class="flex justify-end space-x-3 pt-4">
                        <button type="button" onclick="this.closest('.fixed').remove()" 
                                class="px-4 py-2 bg-gray-300 text-gray-700 rounded hover:bg-gray-400 transition-colors">
                            Abbrechen
                        </button>
                        <button type="submit" 
                                class="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                            Port-Weiterleitung erstellen
                        </button>
                    </div>
                </form>
            </div>
        `;

        modal.querySelector('form').addEventListener('submit', (e) => {
            e.preventDefault();
            const extPort = document.getElementById('modal-ext-port').value;
            const intPort = document.getElementById('modal-int-port').value;
            const protocol = document.getElementById('modal-protocol').value;
            
            if (extPort && intPort) {
                this.createPortForward(parseInt(extPort), deviceIp, parseInt(intPort), protocol);
                modal.remove();
            }
        });

        document.body.appendChild(modal);
        document.getElementById('modal-ext-port').focus();
    }

    setPortPreset(extPort, intPort, protocol) {
        document.getElementById('modal-ext-port').value = extPort;
        document.getElementById('modal-int-port').value = intPort;
        document.getElementById('modal-protocol').value = protocol;
    }

    async createQuickPortForward() {
        const deviceIp = document.getElementById('quick-device')?.value;
        const extPort = document.getElementById('quick-ext-port')?.value;
        const intPort = document.getElementById('quick-int-port')?.value;
        const protocol = document.getElementById('quick-protocol')?.value;

        if (!deviceIp || !extPort || !intPort) {
            this.showError('Bitte alle Felder ausfüllen');
            return;
        }

        await this.createPortForward(parseInt(extPort), deviceIp, parseInt(intPort), protocol);
        
        // Clear form
        document.getElementById('quick-ext-port').value = '';
        document.getElementById('quick-int-port').value = '';
        document.getElementById('quick-device').value = '';
    }

    async createPortForward(externalPort, internalIp, internalPort, protocol) {
        try {
            this.showLoading('Port-Weiterleitung wird erstellt...');
            
            const response = await fetch('/api/port-forwards', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    external_port: externalPort,
                    internal_ip: internalIp,
                    internal_port: internalPort,
                    protocol: protocol
                })
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Port-Weiterleitung erfolgreich erstellt!');
                this.refreshPortForwards();
            } else {
                this.showError('Fehler: ' + (data.message || 'Unbekannter Fehler'));
            }
        } catch (error) {
            this.showError('Netzwerk-Fehler: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async deletePortForward(ruleId) {
        if (!confirm('Port-Weiterleitung wirklich löschen?')) return;

        try {
            this.showLoading('Port-Weiterleitung wird gelöscht...');
            
            const response = await fetch(`/api/port-forwards?rule_id=${encodeURIComponent(ruleId)}`, {
                method: 'DELETE'
            });

            const data = await response.json();

            if (data.success) {
                this.showSuccess('Port-Weiterleitung gelöscht');
                this.refreshPortForwards();
            } else {
                this.showError('Fehler: ' + (data.message || 'Unbekannter Fehler'));
            }
        } catch (error) {
            this.showError('Netzwerk-Fehler: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async refreshPortForwards() {
        try {
            const response = await fetch('/api/port-forwards');
            const data = await response.json();
            this.updatePortForwardsDisplay(data);
        } catch (error) {
            console.error('Error refreshing port forwards:', error);
        }
    }

    updatePortForwardsDisplay(portForwards) {
        const container = document.getElementById('port-forwards-container');
        if (!container) return;

        if (!portForwards || Object.keys(portForwards).length === 0) {
            container.innerHTML = '<p class="text-gray-500 italic">Keine Port-Weiterleitungen konfiguriert</p>';
            return;
        }

        const forwardsHtml = Object.entries(portForwards).map(([ruleId, rule]) => `
            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors">
                <div class="flex items-center space-x-3">
                    <span class="font-medium">Port ${rule.external_port}/${rule.protocol.toUpperCase()}</span>
                    <span class="text-gray-500">→</span>
                    <span class="text-blue-600">${rule.internal_ip}:${rule.internal_port}</span>
                </div>
                <div class="flex items-center space-x-2">
                    <span class="text-xs text-gray-500">${rule.created ? rule.created.substring(0, 19) : ''}</span>
                    <button onclick="deviceManager.deletePortForward('${ruleId}')" 
                            class="text-red-500 hover:text-red-700 text-sm hover:bg-red-50 p-1 rounded transition-colors">
                        🗑️
                    </button>
                </div>
            </div>
        `).join('');

        container.innerHTML = `<div class="space-y-2">${forwardsHtml}</div>`;
    }

    // Utility functions
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showLoading(message = 'Laden...') {
        // Create or update loading overlay
        let overlay = document.getElementById('device-loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'device-loading-overlay';
            overlay.className = 'fixed inset-0 bg-gray-900 bg-opacity-50 flex items-center justify-center z-50';
            overlay.innerHTML = `
                <div class="bg-white rounded-lg p-6 flex items-center space-x-3">
                    <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                    <span class="text-gray-700 font-medium" id="device-loading-text">${message}</span>
                </div>
            `;
            document.body.appendChild(overlay);
        } else {
            document.getElementById('device-loading-text').textContent = message;
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('device-loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showSuccess(message) {
        this.showNotification(message, 'success');
    }

    showError(message) {
        this.showNotification(message, 'error');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        const bgColor = type === 'error' ? 'bg-red-500' : 
                       type === 'success' ? 'bg-green-500' : 
                       type === 'warning' ? 'bg-yellow-500' : 'bg-blue-500';
        
        notification.className = `fixed top-4 right-4 ${bgColor} text-white px-6 py-3 rounded-lg shadow-lg z-50 transform transition-transform duration-300 translate-x-full`;
        notification.innerHTML = `
            <div class="flex items-center space-x-2">
                <span>${this.escapeHtml(message)}</span>
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

        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.classList.add('translate-x-full');
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }
}

// Global functions for template compatibility
window.refreshDevices = () => deviceManager.loadDevices();
window.createQuickPortForward = () => deviceManager.createQuickPortForward();
window.deletePortForward = (ruleId) => deviceManager.deletePortForward(ruleId);

// Initialize device manager
const deviceManager = new DeviceManager();