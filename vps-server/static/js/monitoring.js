/**
 * Real-Time System Monitoring für WireGuard Gateway VPS Dashboard
 * Umfassendes Monitoring mit SocketIO, Charts und Alerts
 */

class SystemMonitoring {
    constructor() {
        this.socket = null;
        this.charts = {};
        this.isConnected = false;
        this.lastUpdate = null;
        this.alertCount = 0;
        
        // Chart-Konfigurationen
        this.chartOptions = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    display: false
                },
                x: {
                    display: false
                }
            },
            animation: {
                duration: 500
            }
        };
        
        this.init();
    }
    
    init() {
        this.initSocketIO();
        this.initCharts();
        this.setupEventListeners();
        
        // Fallback: Polling wenn WebSocket nicht verfügbar
        setTimeout(() => {
            if (!this.isConnected) {
                console.log('WebSocket nicht verfügbar, verwende Polling');
                this.startPolling();
            }
        }, 5000);
    }
    
    initSocketIO() {
        try {
            this.socket = io();
            
            this.socket.on('connect', () => {
                console.log('✅ WebSocket verbunden');
                this.isConnected = true;
                this.updateConnectionStatus(true);
                this.socket.emit('subscribe_monitoring');
            });
            
            this.socket.on('disconnect', () => {
                console.log('❌ WebSocket getrennt');
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });
            
            this.socket.on('system_update', (data) => {
                this.handleSystemUpdate(data);
            });
            
            this.socket.on('critical_alert', (data) => {
                this.handleCriticalAlert(data);
            });
            
            this.socket.on('gateway_metrics', (data) => {
                this.handleGatewayMetrics(data);
            });
            
        } catch (error) {
            console.error('Fehler beim Initialisieren von SocketIO:', error);
            this.startPolling();
        }
    }
    
    initCharts() {
        // CPU Chart
        const cpuCtx = document.getElementById('cpu-chart');
        if (cpuCtx) {
            this.charts.cpu = new Chart(cpuCtx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#3B82F6', '#E5E7EB'],
                        borderWidth: 0
                    }]
                },
                options: {
                    ...this.chartOptions,
                    cutout: '70%'
                }
            });
        }
        
        // Memory Chart
        const memoryCtx = document.getElementById('memory-chart');
        if (memoryCtx) {
            this.charts.memory = new Chart(memoryCtx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#8B5CF6', '#E5E7EB'],
                        borderWidth: 0
                    }]
                },
                options: {
                    ...this.chartOptions,
                    cutout: '70%'
                }
            });
        }
        
        // Disk Chart
        const diskCtx = document.getElementById('disk-chart');
        if (diskCtx) {
            this.charts.disk = new Chart(diskCtx, {
                type: 'doughnut',
                data: {
                    datasets: [{
                        data: [0, 100],
                        backgroundColor: ['#F59E0B', '#E5E7EB'],
                        borderWidth: 0
                    }]
                },
                options: {
                    ...this.chartOptions,
                    cutout: '70%'
                }
            });
        }
    }
    
    setupEventListeners() {
        // Refresh Button
        const refreshBtn = document.getElementById('refresh-monitoring');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshData();
            });
        }
        
        // Export Button
        const exportBtn = document.getElementById('export-metrics');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportMetrics();
            });
        }
    }
    
    handleSystemUpdate(data) {
        this.lastUpdate = new Date();
        
        try {
            // System Health
            if (data.health) {
                this.updateSystemHealth(data.health);
            }
            
            // System Stats
            if (data.system_stats) {
                this.updateSystemStats(data.system_stats);
            }
            
            // Alerts
            if (data.alerts) {
                this.updateAlerts(data.alerts);
            }
            
            // Connected Clients
            if (data.connected_clients !== undefined) {
                this.updateClientCount(data.connected_clients, data.total_clients);
            }
            
            // Update timestamp
            this.updateLastUpdate();
            
        } catch (error) {
            console.error('Fehler beim Verarbeiten der System-Updates:', error);
        }
    }
    
    updateSystemHealth(health) {
        const healthScore = document.getElementById('health-score');
        const healthStatus = document.getElementById('health-status');
        
        if (healthScore && health.health_score !== undefined) {
            healthScore.textContent = health.health_score;
            
            // Farbe basierend auf Score
            healthScore.className = 'text-3xl font-bold';
            if (health.health_score >= 90) {
                healthScore.classList.add('text-green-600');
            } else if (health.health_score >= 70) {
                healthScore.classList.add('text-yellow-600');
            } else {
                healthScore.classList.add('text-red-600');
            }
        }
        
        if (healthStatus && health.status) {
            const statusMap = {
                'excellent': 'Excellent',
                'good': 'Good',
                'warning': 'Warning',
                'critical': 'Critical',
                'error': 'Error'
            };
            healthStatus.textContent = statusMap[health.status] || health.status;
        }
    }
    
    updateSystemStats(stats) {
        // CPU
        this.updateCPU(stats.cpu_percent, stats.cpu_temp);
        
        // Memory
        this.updateMemory(stats.memory_percent, stats.memory_used, stats.memory_total);
        
        // Disk
        this.updateDisk(stats.disk_percent, stats.disk_used, stats.disk_total);
        
        // Network (falls verfügbar)
        if (stats.network_bytes_sent !== undefined) {
            this.updateNetwork(stats);
        }
    }
    
    updateCPU(percent, temperature) {
        const cpuUsage = document.getElementById('cpu-usage');
        const cpuTemp = document.getElementById('cpu-temp');
        
        if (cpuUsage && percent !== undefined) {
            cpuUsage.textContent = `${percent.toFixed(1)}%`;
            
            // Chart aktualisieren
            if (this.charts.cpu) {
                this.charts.cpu.data.datasets[0].data = [percent, 100 - percent];
                this.charts.cpu.update('none');
            }
        }
        
        if (cpuTemp && temperature) {
            cpuTemp.textContent = `Temp: ${temperature.toFixed(1)}°C`;
            
            // Warnfarbe bei hoher Temperatur
            if (temperature > 75) {
                cpuTemp.className = 'text-sm text-red-500';
            } else if (temperature > 65) {
                cpuTemp.className = 'text-sm text-yellow-500';
            } else {
                cpuTemp.className = 'text-sm text-gray-500';
            }
        }
    }
    
    updateMemory(percent, used, total) {
        const memoryUsage = document.getElementById('memory-usage');
        const memoryDetails = document.getElementById('memory-details');
        
        if (memoryUsage && percent !== undefined) {
            memoryUsage.textContent = `${percent.toFixed(1)}%`;
            
            // Chart aktualisieren
            if (this.charts.memory) {
                this.charts.memory.data.datasets[0].data = [percent, 100 - percent];
                this.charts.memory.update('none');
            }
        }
        
        if (memoryDetails && used !== undefined && total !== undefined) {
            const usedGB = (used / 1024 / 1024 / 1024).toFixed(1);
            const totalGB = (total / 1024 / 1024 / 1024).toFixed(1);
            memoryDetails.textContent = `${usedGB} / ${totalGB} GB`;
        }
    }
    
    updateDisk(percent, used, total) {
        const diskUsage = document.getElementById('disk-usage');
        const diskDetails = document.getElementById('disk-details');
        
        if (diskUsage && percent !== undefined) {
            diskUsage.textContent = `${percent.toFixed(1)}%`;
            
            // Chart aktualisieren
            if (this.charts.disk) {
                this.charts.disk.data.datasets[0].data = [percent, 100 - percent];
                this.charts.disk.update('none');
            }
        }
        
        if (diskDetails && used !== undefined && total !== undefined) {
            const usedGB = (used / 1024 / 1024 / 1024).toFixed(1);
            const totalGB = (total / 1024 / 1024 / 1024).toFixed(1);
            diskDetails.textContent = `${usedGB} / ${totalGB} GB`;
        }
    }
    
    updateAlerts(alerts) {
        const alertCount = document.getElementById('alert-count');
        if (alertCount) {
            this.alertCount = alerts.length;
            alertCount.textContent = this.alertCount;
            
            // Farbe basierend auf Alert-Anzahl
            alertCount.className = 'text-2xl font-bold';
            if (this.alertCount === 0) {
                alertCount.classList.add('text-gray-600');
            } else if (this.alertCount <= 2) {
                alertCount.classList.add('text-yellow-600');
            } else {
                alertCount.classList.add('text-red-600');
            }
        }
        
        // Alert-Liste aktualisieren (falls vorhanden)
        this.updateAlertsList(alerts);
    }
    
    updateAlertsList(alerts) {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;
        
        if (alerts.length === 0) {
            alertsList.innerHTML = '<div class="text-gray-500 text-center py-4">Keine aktiven Alerts</div>';
            return;
        }
        
        const alertsHTML = alerts.map(alert => {
            const severityColors = {
                'critical': 'bg-red-100 border-red-500 text-red-700',
                'warning': 'bg-yellow-100 border-yellow-500 text-yellow-700',
                'info': 'bg-blue-100 border-blue-500 text-blue-700'
            };
            
            const colorClass = severityColors[alert.severity] || severityColors.info;
            
            return `
                <div class="border-l-4 p-4 ${colorClass} mb-2">
                    <div class="flex">
                        <div class="flex-shrink-0">
                            <span class="font-medium">${alert.type}</span>
                        </div>
                        <div class="ml-3">
                            <p class="text-sm">${alert.message}</p>
                            <p class="text-xs mt-1">${new Date(alert.timestamp).toLocaleString()}</p>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        alertsList.innerHTML = alertsHTML;
    }
    
    updateClientCount(connected, total) {
        const clientCount = document.getElementById('client-count');
        if (clientCount) {
            clientCount.textContent = connected || 0;
        }
        
        const totalClients = document.getElementById('total-clients');
        if (totalClients) {
            totalClients.textContent = total || 0;
        }
    }
    
    updateConnectionStatus(connected) {
        const statusIndicator = document.getElementById('status-indicator');
        const statusText = document.getElementById('status-text');
        
        if (statusIndicator) {
            if (connected) {
                statusIndicator.className = 'w-3 h-3 bg-green-500 rounded-full animate-pulse';
            } else {
                statusIndicator.className = 'w-3 h-3 bg-red-500 rounded-full';
            }
        }
        
        if (statusText) {
            statusText.textContent = connected ? 'Live' : 'Offline';
        }
    }
    
    updateLastUpdate() {
        const lastUpdateElement = document.getElementById('last-update');
        if (lastUpdateElement && this.lastUpdate) {
            lastUpdateElement.textContent = `Letztes Update: ${this.lastUpdate.toLocaleTimeString()}`;
        }
    }
    
    handleCriticalAlert(data) {
        // Kritische Alerts prominent anzeigen
        this.showNotification('Kritischer Alert', data.alerts[0].message, 'error');
        
        // Sound-Benachrichtigung (optional)
        this.playAlertSound();
    }
    
    handleGatewayMetrics(data) {
        console.log('Gateway-Metriken erhalten:', data);
        // Gateway-spezifische Metriken verarbeiten
        // Hier könnten Gateway-spezifische Charts aktualisiert werden
    }
    
    showNotification(title, message, type = 'info') {
        // Einfache Notification-Implementation
        if ('Notification' in window && Notification.permission === 'granted') {
            new Notification(title, {
                body: message,
                icon: '/static/images/icon.png'
            });
        }
        
        // Browser-Notification
        const notification = document.createElement('div');
        notification.className = `fixed top-4 right-4 p-4 rounded-lg shadow-lg z-50 ${
            type === 'error' ? 'bg-red-500 text-white' : 
            type === 'warning' ? 'bg-yellow-500 text-white' : 
            'bg-blue-500 text-white'
        }`;
        notification.innerHTML = `
            <div class="font-medium">${title}</div>
            <div class="text-sm">${message}</div>
        `;
        
        document.body.appendChild(notification);
        
        // Automatisch entfernen nach 5 Sekunden
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
    
    playAlertSound() {
        // Optional: Alert-Sound abspielen
        try {
            const audio = new Audio('/static/sounds/alert.mp3');
            audio.volume = 0.3;
            audio.play().catch(() => {
                // Sound konnte nicht abgespielt werden (User-Interaction erforderlich)
            });
        } catch (error) {
            // Sound nicht verfügbar
        }
    }
    
    startPolling() {
        // Fallback: Polling alle 30 Sekunden
        setInterval(async () => {
            try {
                const response = await fetch('/api/system-stats');
                if (response.ok) {
                    const data = await response.json();
                    if (data.success) {
                        this.handleSystemUpdate({
                            system_stats: data.system_stats,
                            alerts: data.alerts
                        });
                    }
                }
            } catch (error) {
                console.error('Polling-Fehler:', error);
            }
        }, 30000);
    }
    
    refreshData() {
        if (this.isConnected && this.socket) {
            this.socket.emit('subscribe_monitoring');
        } else {
            // Manuelle API-Abfrage
            this.startPolling();
        }
    }
    
    async exportMetrics() {
        try {
            const response = await fetch('/api/system-stats');
            if (response.ok) {
                const data = await response.json();
                
                // JSON-Export
                const blob = new Blob([JSON.stringify(data, null, 2)], {
                    type: 'application/json'
                });
                
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `system-metrics-${new Date().toISOString().split('T')[0]}.json`;
                a.click();
                URL.revokeObjectURL(url);
                
                this.showNotification('Export', 'Metriken erfolgreich exportiert', 'info');
            }
        } catch (error) {
            console.error('Export-Fehler:', error);
            this.showNotification('Fehler', 'Export fehlgeschlagen', 'error');
        }
    }
}

// Notification-Berechtigung anfordern
if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
}

// Monitoring initialisieren wenn DOM geladen ist
document.addEventListener('DOMContentLoaded', () => {
    window.systemMonitoring = new SystemMonitoring();
});

// Service Worker für Offline-Fähigkeiten (optional)
if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/static/js/sw.js').catch(() => {
        // Service Worker nicht verfügbar
    });
}