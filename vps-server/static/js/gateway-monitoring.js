/**
 * Gateway-PC Monitoring Integration für VPS Dashboard
 * Zeigt CPU, RAM, Temperatur und andere Metriken der Gateway-PCs an
 */

class GatewayMonitoringManager {
    constructor() {
        this.gatewayMetrics = new Map();
        this.updateInterval = 30000; // 30 Sekunden
        this.charts = new Map();
        this.init();
    }

    init() {
        console.log('🔄 Gateway Monitoring Manager initialisiert');
        
        // Event-Listener für Gateway-Metriken über WebSocket
        if (window.socket) {
            window.socket.on('gateway_metrics', (data) => {
                this.handleGatewayMetrics(data);
            });
        }

        // Container für Gateway-Monitoring erstellen falls nicht vorhanden
        this.ensureGatewayMonitoringContainer();
        
        // Initial laden
        this.loadGatewayMetrics();
        
        // Regelmäßige Updates
        setInterval(() => {
            this.loadGatewayMetrics();
        }, this.updateInterval);
    }

    ensureGatewayMonitoringContainer() {
        // Prüfen ob Gateway-Monitoring-Container existiert
        let container = document.getElementById('gateway-monitoring-section');
        if (!container) {
            // Container dynamisch erstellen
            const mainContent = document.querySelector('.grid.grid-cols-1.gap-6') || document.querySelector('main');
            if (mainContent) {
                const section = this.createGatewayMonitoringSection();
                mainContent.appendChild(section);
            }
        }
    }

    createGatewayMonitoringSection() {
        const section = document.createElement('div');
        section.id = 'gateway-monitoring-section';
        section.className = 'bg-white shadow rounded-lg mb-6';
        
        section.innerHTML = `
            <div class="px-6 py-4 border-b border-gray-200">
                <h3 class="text-lg font-medium text-gray-900">
                    🌐 Gateway-PC Monitoring
                </h3>
                <p class="text-sm text-gray-500">
                    Real-Time System-Metriken der verbundenen Gateway-PCs
                </p>
            </div>
            <div id="gateway-monitoring-content" class="p-6">
                <div id="no-gateway-metrics" class="text-center py-8 text-gray-500">
                    <div class="text-4xl mb-4">📊</div>
                    <p>Keine Gateway-Metriken verfügbar</p>
                    <p class="text-sm">Gateway-PCs müssen das Monitoring aktiviert haben</p>
                </div>
                
                <div id="gateway-metrics-container" class="hidden">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6" id="gateway-cards-grid">
                        <!-- Gateway-Karten werden hier dynamisch eingefügt -->
                    </div>
                </div>
            </div>
        `;
        
        return section;
    }

    handleGatewayMetrics(data) {
        console.log('📊 Gateway-Metriken empfangen:', data);
        
        const gatewayId = data.gateway_id;
        const metrics = data.metrics;
        
        // Metriken aktualisieren
        this.gatewayMetrics.set(gatewayId, {
            ...metrics,
            lastUpdate: new Date(),
            gateway_id: gatewayId
        });
        
        // UI aktualisieren
        this.updateGatewayDisplay();
    }

    async loadGatewayMetrics() {
        // Placeholder für direkte API-Abfrage falls WebSocket nicht verfügbar
        try {
            const response = await fetch('/api/gateway-metrics');
            if (response.ok) {
                const data = await response.json();
                // Verarbeite gespeicherte Gateway-Metriken falls vorhanden
                console.log('📊 Gateway-Metriken von API geladen');
            }
        } catch (error) {
            console.debug('Keine direkte Gateway-Metriken-API verfügbar');
        }
    }

    updateGatewayDisplay() {
        const container = document.getElementById('gateway-metrics-container');
        const noDataElement = document.getElementById('no-gateway-metrics');
        const gridElement = document.getElementById('gateway-cards-grid');
        
        if (!container || !noDataElement || !gridElement) {
            console.warn('Gateway-Monitoring-Container nicht gefunden');
            return;
        }

        if (this.gatewayMetrics.size === 0) {
            // Keine Gateways vorhanden
            container.classList.add('hidden');
            noDataElement.classList.remove('hidden');
            return;
        }

        // Gateways vorhanden
        noDataElement.classList.add('hidden');
        container.classList.remove('hidden');
        
        // Gateway-Karten erstellen/aktualisieren
        gridElement.innerHTML = '';
        
        this.gatewayMetrics.forEach((metrics, gatewayId) => {
            const card = this.createGatewayCard(gatewayId, metrics);
            gridElement.appendChild(card);
        });
    }

    createGatewayCard(gatewayId, metrics) {
        const card = document.createElement('div');
        card.className = 'bg-white border border-gray-200 rounded-lg p-6 shadow-sm';
        card.id = `gateway-card-${gatewayId}`;
        
        // Gateway-Name aus Metrics oder ID ableiten
        const gatewayName = this.getGatewayName(gatewayId, metrics);
        
        // Status-Farbe basierend auf Verbindung
        const statusClass = metrics.tunnel_connected ? 'text-green-600' : 'text-red-600';
        const statusIcon = metrics.tunnel_connected ? '🟢' : '🔴';
        const statusText = metrics.tunnel_connected ? 'Verbunden' : 'Getrennt';
        
        // Temperatur-Anzeige
        const tempDisplay = metrics.cpu_temp ? `${metrics.cpu_temp.toFixed(1)}°C` : 'N/A';
        const tempClass = this.getTempColorClass(metrics.cpu_temp);
        
        // Uptime formatieren
        const uptimeFormatted = this.formatUptime(metrics.uptime_seconds);
        
        // RAM in GB umrechnen
        const ramTotalGB = (metrics.memory_total / (1024 * 1024 * 1024)).toFixed(1);
        const ramUsedGB = (metrics.memory_used / (1024 * 1024 * 1024)).toFixed(1);
        
        card.innerHTML = `
            <div class="flex items-center justify-between mb-4">
                <h4 class="text-lg font-medium text-gray-900">${gatewayName}</h4>
                <span class="${statusClass} text-sm font-medium">
                    ${statusIcon} ${statusText}
                </span>
            </div>
            
            <!-- System-Metriken Grid -->
            <div class="grid grid-cols-2 gap-4 mb-4">
                <!-- CPU -->
                <div class="text-center p-3 bg-blue-50 rounded-lg">
                    <div class="text-2xl font-bold text-blue-600">${metrics.cpu_percent.toFixed(1)}%</div>
                    <div class="text-xs text-blue-500 uppercase">CPU</div>
                </div>
                
                <!-- RAM -->
                <div class="text-center p-3 bg-green-50 rounded-lg">
                    <div class="text-2xl font-bold text-green-600">${metrics.memory_percent.toFixed(1)}%</div>
                    <div class="text-xs text-green-500 uppercase">${ramUsedGB}/${ramTotalGB} GB</div>
                </div>
                
                <!-- Temperatur -->
                <div class="text-center p-3 bg-orange-50 rounded-lg">
                    <div class="text-2xl font-bold ${tempClass}">${tempDisplay}</div>
                    <div class="text-xs text-orange-500 uppercase">Temp</div>
                </div>
                
                <!-- Disk -->
                <div class="text-center p-3 bg-purple-50 rounded-lg">
                    <div class="text-2xl font-bold text-purple-600">${metrics.disk_percent.toFixed(1)}%</div>
                    <div class="text-xs text-purple-500 uppercase">Disk</div>
                </div>
            </div>
            
            <!-- Zusätzliche Informationen -->
            <div class="border-t border-gray-200 pt-4">
                <div class="grid grid-cols-2 gap-2 text-sm">
                    <div>
                        <span class="text-gray-500">WireGuard:</span>
                        <span class="font-medium">${metrics.wireguard_status}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Uptime:</span>
                        <span class="font-medium">${uptimeFormatted}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Load:</span>
                        <span class="font-medium">${metrics.load_average[0].toFixed(2)}</span>
                    </div>
                    <div>
                        <span class="text-gray-500">Interfaces:</span>
                        <span class="font-medium">${Object.keys(metrics.network_interfaces || {}).length}</span>
                    </div>
                </div>
            </div>
            
            <!-- Letzte Aktualisierung -->
            <div class="text-xs text-gray-400 mt-2 text-center">
                Letzte Aktualisierung: ${new Date(metrics.timestamp).toLocaleTimeString()}
            </div>
        `;
        
        return card;
    }

    getGatewayName(gatewayId, metrics) {
        // Versuche Name aus verschiedenen Quellen zu extrahieren
        if (metrics.gateway_name) {
            return metrics.gateway_name;
        }
        
        // Suche in Client-Liste nach matching Public Key
        const clients = window.clientsData || [];
        const matchingClient = clients.find(client => 
            client.status === 'connected' && gatewayId.includes(client.name.toLowerCase())
        );
        
        if (matchingClient) {
            return matchingClient.name;
        }
        
        // Fallback: Gateway-ID formatieren
        return gatewayId.replace('gateway-', 'Gateway ').toUpperCase();
    }

    getTempColorClass(temp) {
        if (!temp) return 'text-gray-600';
        
        if (temp < 40) return 'text-blue-600';
        if (temp < 60) return 'text-green-600';
        if (temp < 75) return 'text-yellow-600';
        if (temp < 85) return 'text-orange-600';
        return 'text-red-600';
    }

    formatUptime(seconds) {
        if (!seconds) return 'N/A';
        
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (days > 0) {
            return `${days}d ${hours}h`;
        } else if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }

    // Cleanup veraltete Gateway-Metriken (älter als 5 Minuten)
    cleanupStaleMetrics() {
        const now = new Date();
        const staleThreshold = 5 * 60 * 1000; // 5 Minuten
        
        for (const [gatewayId, metrics] of this.gatewayMetrics.entries()) {
            if (now - metrics.lastUpdate > staleThreshold) {
                console.log(`🗑️ Entferne veraltete Metriken für Gateway ${gatewayId}`);
                this.gatewayMetrics.delete(gatewayId);
            }
        }
        
        this.updateGatewayDisplay();
    }
}

// Gateway-Monitoring-Manager global initialisieren
let gatewayMonitoringManager;

document.addEventListener('DOMContentLoaded', function() {
    // Warte auf Socket-Initialisierung
    setTimeout(() => {
        gatewayMonitoringManager = new GatewayMonitoringManager();
        
        // Cleanup-Timer für veraltete Metriken
        setInterval(() => {
            if (gatewayMonitoringManager) {
                gatewayMonitoringManager.cleanupStaleMetrics();
            }
        }, 60000); // Jede Minute
        
    }, 1000);
});

// Export für andere Module
window.GatewayMonitoringManager = GatewayMonitoringManager;