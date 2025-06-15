#!/usr/bin/env python3
"""
System Monitoring Module für WireGuard Gateway-PC
Umfassendes Monitoring von CPU, RAM, Temperatur, Netzwerk und WireGuard
Optimiert für Raspberry Pi und andere ARM-basierte Gateway-Systeme
"""

import os
import time
import json
import logging
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import requests

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil nicht verfügbar - System-Monitoring eingeschränkt")

logger = logging.getLogger(__name__)

@dataclass
class SystemMetrics:
    """System-Metriken Datenstruktur"""
    timestamp: str
    cpu_percent: float
    cpu_temp: Optional[float]
    cpu_frequency: Optional[float]
    memory_total: int
    memory_used: int
    memory_percent: float
    disk_total: int
    disk_used: int
    disk_percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    network_interfaces: Dict[str, Dict]
    uptime_seconds: int
    load_average: List[float]
    wireguard_status: str
    tunnel_connected: bool

@dataclass
class NetworkInterface:
    """Netzwerk-Interface Informationen"""
    name: str
    ip_address: Optional[str]
    mac_address: Optional[str]
    is_up: bool
    speed: Optional[int]
    rx_bytes: int
    tx_bytes: int
    rx_packets: int
    tx_packets: int

class GatewaySystemMonitor:
    """Umfassendes System-Monitoring für Gateway-PC"""
    
    def __init__(self, vps_api_url: str = None):
        self.vps_api_url = vps_api_url
        self.monitoring_active = False
        self.monitor_thread = None
        self.metrics_history = []
        self.max_history = 100  # Letzte 100 Metriken speichern
        
        # Gateway-spezifische Konfiguration
        self.gateway_config_file = '/etc/wireguard-gateway/config.json'
        self.gateway_interface = 'gateway'
        
        # Monitoring-Intervall (Sekunden)
        self.update_interval = int(os.getenv('METRICS_SEND_INTERVAL', '60'))
        
        # Gateway-Identifikation
        self.gateway_id = self._get_gateway_id()
        
        logger.info(f"Gateway System Monitor initialisiert - ID: {self.gateway_id}")
    
    def _get_gateway_id(self) -> str:
        """Eindeutige Gateway-ID generieren"""
        try:
            # Versuche aus Gateway-Konfiguration zu lesen
            if os.path.exists(self.gateway_config_file):
                with open(self.gateway_config_file, 'r') as f:
                    config = json.load(f)
                    gateway_id = config.get('gateway_id')
                    if gateway_id:
                        return gateway_id
            
            # Fallback: MAC-Adresse der primären Schnittstelle
            if PSUTIL_AVAILABLE:
                interfaces = psutil.net_if_addrs()
                for interface_name, addresses in interfaces.items():
                    if interface_name.startswith(('eth', 'enp', 'ens')):
                        for addr in addresses:
                            if addr.family.name == 'AF_PACKET':  # MAC-Adresse
                                return f"gateway-{addr.address.replace(':', '')}"
            
            # Letzter Fallback: Hostname
            import socket
            return f"gateway-{socket.gethostname()}"
            
        except Exception as e:
            logger.warning(f"Fehler beim Ermitteln der Gateway-ID: {e}")
            return "gateway-unknown"
    
    def get_current_metrics(self) -> SystemMetrics:
        """Sammle aktuelle System-Metriken"""
        try:
            # CPU-Metriken
            cpu_percent = self._get_cpu_percent()
            cpu_temp = self._get_cpu_temperature()
            cpu_freq = self._get_cpu_frequency()
            
            # Memory-Metriken
            memory_info = self._get_memory_info()
            
            # Disk-Metriken
            disk_info = self._get_disk_info()
            
            # Swap-Metriken
            swap_info = self._get_swap_info()
            
            # Netzwerk-Interfaces
            network_interfaces = self._get_network_interfaces()
            
            # System-Informationen
            uptime = self._get_uptime()
            load_avg = self._get_load_average()
            
            # WireGuard-Status
            wg_status, tunnel_connected = self._get_wireguard_status()
            
            metrics = SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=cpu_percent,
                cpu_temp=cpu_temp,
                cpu_frequency=cpu_freq,
                memory_total=memory_info['total'],
                memory_used=memory_info['used'],
                memory_percent=memory_info['percent'],
                disk_total=disk_info['total'],
                disk_used=disk_info['used'],
                disk_percent=disk_info['percent'],
                swap_total=swap_info['total'],
                swap_used=swap_info['used'],
                swap_percent=swap_info['percent'],
                network_interfaces=network_interfaces,
                uptime_seconds=uptime,
                load_average=load_avg,
                wireguard_status=wg_status,
                tunnel_connected=tunnel_connected
            )
            
            # Zur Historie hinzufügen
            self.metrics_history.append(asdict(metrics))
            if len(self.metrics_history) > self.max_history:
                self.metrics_history.pop(0)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Metriken: {e}")
            # Fallback mit minimalen Daten
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,
                cpu_temp=None,
                cpu_frequency=None,
                memory_total=0,
                memory_used=0,
                memory_percent=0.0,
                disk_total=0,
                disk_used=0,
                disk_percent=0.0,
                swap_total=0,
                swap_used=0,
                swap_percent=0.0,
                network_interfaces={},
                uptime_seconds=0,
                load_average=[0.0, 0.0, 0.0],
                wireguard_status="error",
                tunnel_connected=False
            )
    
    def send_metrics_to_vps(self, metrics: SystemMetrics) -> bool:
        """Sende Metriken an VPS Dashboard"""
        if not self.vps_api_url:
            logger.debug("Keine VPS API URL konfiguriert - Metriken werden nicht gesendet")
            return False
        
        try:
            # Normalisiere VPS URL
            if not self.vps_api_url.startswith(('http://', 'https://')):
                vps_url = f"http://{self.vps_api_url}"
            else:
                vps_url = self.vps_api_url
            
            api_endpoint = f"{vps_url}/api/gateway-metrics"
            
            # Konvertiere Metriken zu Dictionary
            metrics_data = asdict(metrics)
            metrics_data['gateway_id'] = self.gateway_id
            
            # API-Anfrage senden
            response = requests.post(
                api_endpoint,
                json=metrics_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.debug("Metriken erfolgreich an VPS gesendet")
                return True
            else:
                logger.warning(f"VPS API Fehler: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning("Timeout beim Senden der Metriken an VPS")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Verbindungsfehler beim Senden der Metriken an VPS")
            return False
        except Exception as e:
            logger.error(f"Fehler beim Senden der Metriken: {e}")
            return False
    
    def start_monitoring(self) -> bool:
        """Starte kontinuierliches Monitoring"""
        if self.monitoring_active:
            logger.warning("Monitoring bereits aktiv")
            return False
        
        # VPS API URL aus Gateway-Konfiguration laden
        self._load_vps_config()
        
        self.monitoring_active = True
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"Gateway Monitoring gestartet - Intervall: {self.update_interval}s")
        return True
    
    def stop_monitoring(self):
        """Stoppe Monitoring"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logger.info("Gateway Monitoring gestoppt")
    
    def _load_vps_config(self):
        """Lade VPS-Konfiguration aus Gateway-Config"""
        try:
            if os.path.exists(self.gateway_config_file):
                with open(self.gateway_config_file, 'r') as f:
                    config = json.load(f)
                    if not self.vps_api_url:
                        self.vps_api_url = config.get('vps_api_url')
                        logger.info(f"VPS API URL aus Konfiguration geladen: {self.vps_api_url}")
        except Exception as e:
            logger.warning(f"Fehler beim Laden der VPS-Konfiguration: {e}")
    
    def _monitoring_loop(self):
        """Haupt-Monitoring-Schleife"""
        logger.info("Gateway Monitoring-Schleife gestartet")
        
        consecutive_errors = 0
        max_consecutive_errors = 5
        
        while self.monitoring_active:
            try:
                # Sammle aktuelle Metriken
                metrics = self.get_current_metrics()
                
                # Lokales Logging
                logger.debug(f"Metriken gesammelt: CPU={metrics.cpu_percent}%, RAM={metrics.memory_percent}%, Temp={metrics.cpu_temp}°C")
                
                # An VPS senden
                if self.vps_api_url:
                    self.send_metrics_to_vps(metrics)
                
                # Reset error counter bei erfolgreichem Durchlauf
                consecutive_errors = 0
                
                # Warte bis zum nächsten Update
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                logger.info("Monitoring gestoppt durch Benutzer")
                self.monitoring_active = False
                break
            except Exception as e:
                consecutive_errors += 1
                logger.error(f"Monitoring-Fehler ({consecutive_errors}/{max_consecutive_errors}): {e}")
                
                # Stoppe bei zu vielen aufeinanderfolgenden Fehlern
                if consecutive_errors >= max_consecutive_errors:
                    logger.error("Zu viele Monitoring-Fehler - Stoppe Überwachung")
                    self.monitoring_active = False
                    break
                
                # Exponential backoff bei Fehlern
                time.sleep(min(120, 30 * consecutive_errors))
    
    def _get_cpu_percent(self) -> float:
        """CPU-Auslastung ermitteln"""
        if PSUTIL_AVAILABLE:
            return psutil.cpu_percent(interval=1)
        else:
            # Fallback: /proc/loadavg
            try:
                with open('/proc/loadavg', 'r') as f:
                    load = float(f.read().split()[0])
                    return min(load * 100, 100.0)  # Grobe Schätzung
            except Exception:
                return 0.0
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """CPU-Temperatur ermitteln (Raspberry Pi optimiert)"""
        temp_sources = [
            '/sys/class/thermal/thermal_zone0/temp',  # Raspberry Pi
            '/opt/vc/bin/vcgencmd'  # Pi-spezifisches Tool
        ]
        
        # Thermal Zone (Standard Linux)
        try:
            if os.path.exists(temp_sources[0]):
                with open(temp_sources[0], 'r') as f:
                    temp_raw = int(f.read().strip())
                    return temp_raw / 1000.0  # milli-Celsius zu Celsius
        except Exception:
            pass
        
        # vcgencmd (Raspberry Pi spezifisch)
        try:
            result = subprocess.run(['vcgencmd', 'measure_temp'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                temp_str = result.stdout.strip()
                if 'temp=' in temp_str:
                    temp_value = temp_str.split('temp=')[1].replace("'C", "")
                    return float(temp_value)
        except Exception:
            pass
        
        # psutil sensors (falls verfügbar)
        if PSUTIL_AVAILABLE:
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        if entries:
                            return entries[0].current
            except Exception:
                pass
        
        return None
    
    def _get_cpu_frequency(self) -> Optional[float]:
        """CPU-Frequenz ermitteln"""
        if PSUTIL_AVAILABLE:
            try:
                freq = psutil.cpu_freq()
                if freq:
                    return freq.current
            except Exception:
                pass
        
        # Fallback: /proc/cpuinfo
        try:
            with open('/proc/cpuinfo', 'r') as f:
                for line in f:
                    if 'cpu MHz' in line:
                        return float(line.split(':')[1].strip())
        except Exception:
            pass
        
        return None
    
    def _get_memory_info(self) -> Dict:
        """Memory-Informationen ermitteln"""
        if PSUTIL_AVAILABLE:
            mem = psutil.virtual_memory()
            return {
                'total': mem.total,
                'used': mem.used,
                'percent': mem.percent
            }
        else:
            # Fallback: /proc/meminfo
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = {}
                    for line in f:
                        key, value = line.split(':')
                        meminfo[key.strip()] = int(value.strip().split()[0]) * 1024  # KB zu Bytes
                
                total = meminfo.get('MemTotal', 0)
                available = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
                used = total - available
                percent = (used / total * 100) if total > 0 else 0
                
                return {
                    'total': total,
                    'used': used,
                    'percent': percent
                }
            except Exception:
                return {'total': 0, 'used': 0, 'percent': 0}
    
    def _get_disk_info(self) -> Dict:
        """Disk-Informationen ermitteln"""
        if PSUTIL_AVAILABLE:
            try:
                disk = psutil.disk_usage('/')
                return {
                    'total': disk.total,
                    'used': disk.used,
                    'percent': (disk.used / disk.total * 100) if disk.total > 0 else 0
                }
            except Exception:
                pass
        
        # Fallback: df command
        try:
            result = subprocess.run(['df', '/'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    fields = lines[1].split()
                    total = int(fields[1]) * 1024  # KB zu Bytes
                    used = int(fields[2]) * 1024
                    percent = float(fields[4].rstrip('%'))
                    return {
                        'total': total,
                        'used': used,
                        'percent': percent
                    }
        except Exception:
            pass
        
        return {'total': 0, 'used': 0, 'percent': 0}
    
    def _get_swap_info(self) -> Dict:
        """Swap-Informationen ermitteln"""
        if PSUTIL_AVAILABLE:
            try:
                swap = psutil.swap_memory()
                return {
                    'total': swap.total,
                    'used': swap.used,
                    'percent': swap.percent
                }
            except Exception:
                pass
        
        # Fallback: /proc/meminfo
        try:
            with open('/proc/meminfo', 'r') as f:
                swap_total = 0
                swap_free = 0
                for line in f:
                    if line.startswith('SwapTotal:'):
                        swap_total = int(line.split()[1]) * 1024  # KB zu Bytes
                    elif line.startswith('SwapFree:'):
                        swap_free = int(line.split()[1]) * 1024
                
                swap_used = swap_total - swap_free
                swap_percent = (swap_used / swap_total * 100) if swap_total > 0 else 0
                
                return {
                    'total': swap_total,
                    'used': swap_used,
                    'percent': swap_percent
                }
        except Exception:
            pass
        
        return {'total': 0, 'used': 0, 'percent': 0}
    
    def _get_network_interfaces(self) -> Dict[str, Dict]:
        """Netzwerk-Interface-Informationen sammeln (nur aktive Interfaces)"""
        interfaces = {}
        
        if PSUTIL_AVAILABLE:
            try:
                # Interface-Statistiken
                net_io = psutil.net_io_counters(pernic=True)
                net_addrs = psutil.net_if_addrs()
                net_stats = psutil.net_if_stats()
                
                for interface_name, io_stats in net_io.items():
                    # Überspringe Loopback-Interface
                    if interface_name == 'lo':
                        continue
                    
                    interface_info = {
                        'name': interface_name,
                        'bytes_sent': io_stats.bytes_sent,
                        'bytes_recv': io_stats.bytes_recv,
                        'packets_sent': io_stats.packets_sent,
                        'packets_recv': io_stats.packets_recv,
                        'errors_in': io_stats.errin,
                        'errors_out': io_stats.errout,
                        'ip_address': None,
                        'mac_address': None,
                        'is_up': False,
                        'speed': None
                    }
                    
                    # Interface-Status prüfen
                    if interface_name in net_stats:
                        interface_info['is_up'] = net_stats[interface_name].isup
                        interface_info['speed'] = net_stats[interface_name].speed
                    
                    # Nur aktive Interfaces hinzufügen
                    if not interface_info['is_up']:
                        continue
                    
                    # IP und MAC-Adressen
                    if interface_name in net_addrs:
                        for addr in net_addrs[interface_name]:
                            if addr.family.name == 'AF_INET':  # IPv4
                                interface_info['ip_address'] = addr.address
                            elif addr.family.name == 'AF_PACKET':  # MAC
                                interface_info['mac_address'] = addr.address
                    
                    # Nur Interfaces mit IP-Adresse anzeigen
                    if interface_info['ip_address']:
                        interfaces[interface_name] = interface_info
                    
            except Exception as e:
                logger.warning(f"Fehler beim Sammeln der Interface-Daten: {e}")
        
        return interfaces
    
    def _get_uptime(self) -> int:
        """System-Uptime in Sekunden"""
        if PSUTIL_AVAILABLE:
            try:
                return int(time.time() - psutil.boot_time())
            except Exception:
                pass
        
        # Fallback: /proc/uptime
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                return int(uptime_seconds)
        except Exception:
            return 0
    
    def _get_load_average(self) -> List[float]:
        """Load Average ermitteln"""
        if PSUTIL_AVAILABLE:
            try:
                return list(psutil.getloadavg())
            except Exception:
                pass
        
        # Fallback: /proc/loadavg
        try:
            with open('/proc/loadavg', 'r') as f:
                load_values = f.read().split()[:3]
                return [float(x) for x in load_values]
        except Exception:
            return [0.0, 0.0, 0.0]
    
    def _get_wireguard_status(self) -> Tuple[str, bool]:
        """WireGuard-Status ermitteln"""
        try:
            result = subprocess.run(['wg', 'show', self.gateway_interface], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                output = result.stdout.strip()
                if 'latest handshake:' in output:
                    return "connected", True
                elif 'peer:' in output:
                    return "configured", False
                else:
                    return "interface_up", False
            else:
                return "disconnected", False
        except Exception as e:
            logger.debug(f"WireGuard Status-Fehler: {e}")
            return "error", False

# Globale Monitor-Instanz für CLI-Zugriff
gateway_monitor = None

def start_gateway_monitoring(vps_api_url: str = None) -> bool:
    """Starte Gateway-Monitoring global"""
    global gateway_monitor
    
    if gateway_monitor and gateway_monitor.monitoring_active:
        logger.warning("Gateway Monitoring bereits aktiv")
        return False
    
    gateway_monitor = GatewaySystemMonitor(vps_api_url)
    return gateway_monitor.start_monitoring()

def stop_gateway_monitoring():
    """Stoppe Gateway-Monitoring global"""
    global gateway_monitor
    
    if gateway_monitor:
        gateway_monitor.stop_monitoring()
        gateway_monitor = None

def get_current_gateway_metrics() -> Optional[SystemMetrics]:
    """Hole aktuelle Gateway-Metriken"""
    global gateway_monitor
    
    if not gateway_monitor:
        gateway_monitor = GatewaySystemMonitor()
    
    return gateway_monitor.get_current_metrics()

if __name__ == "__main__":
    # Service-Modus - kontinuierliches Monitoring
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/var/log/gateway-monitoring.log'),
            logging.StreamHandler()
        ]
    )
    
    print("🚀 Gateway System Monitor Service gestartet")
    
    # Monitoring permanent starten
    if start_gateway_monitoring():
        print("✅ Gateway-Monitoring läuft - sendet Daten an VPS")
        
        try:
            # Service läuft mit Stabilisierung
            consecutive_errors = 0
            max_consecutive_errors = 3
            
            while True:
                try:
                    time.sleep(60)
                    
                    # Health-Check
                    if gateway_monitor and not gateway_monitor.monitoring_active:
                        print("⚠️ Monitoring gestoppt - starte neu...")
                        start_gateway_monitoring()
                    
                    # Reset error counter bei erfolgreichem Health-Check
                    consecutive_errors = 0
                    
                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Service-Fehler ({consecutive_errors}/{max_consecutive_errors}): {e}")
                    
                    if consecutive_errors >= max_consecutive_errors:
                        logger.error("Zu viele Service-Fehler - beende Service")
                        break
                    
                    time.sleep(min(300, 60 * consecutive_errors))
                    
        except KeyboardInterrupt:
            print("\n🛑 Service-Stopp angefordert")
            stop_gateway_monitoring()
            print("✅ Gateway-Monitoring gestoppt")
    else:
        print("❌ Fehler beim Starten des Gateway-Monitoring")
        sys.exit(1)

@dataclass
class NetworkInterface:
    """Netzwerk-Interface Statistiken"""
    name: str
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errors_in: int
    errors_out: int
    drops_in: int
    drops_out: int
    speed_mbps: Optional[int]
    is_up: bool
    ip_address: Optional[str]

class SystemMonitor:
    """Umfassendes System-Monitoring für Gateway-PC"""
    
    def __init__(self, history_size: int = 100):
        self.history_size = history_size
        self.metrics_history: List[SystemMetrics] = []
        self.cache_timeout = 5  # Sekunden
        self.last_update = 0
        self.cached_metrics: Optional[SystemMetrics] = None
        self._lock = threading.Lock()
        
        # Alert-Schwellenwerte
        self.alert_thresholds = {
            'cpu_percent': 85.0,
            'memory_percent': 90.0,
            'disk_percent': 95.0,
            'cpu_temp': 75.0,  # Raspberry Pi kritische Temperatur
            'swap_percent': 50.0
        }
        
        # Netzwerk-Interface Mapping
        self.network_interfaces = ['eth0', 'eth1', 'wlan0', 'wg0', 'gateway']
        
    def get_current_metrics(self, force_refresh: bool = False) -> Dict:
        """
        Aktuelle System-Metriken mit intelligentem Caching
        
        Args:
            force_refresh: Cache umgehen und neue Daten sammeln
            
        Returns:
            Dictionary mit aktuellen System-Metriken
        """
        current_time = time.time()
        
        # Cache prüfen
        if (not force_refresh and 
            self.cached_metrics and 
            current_time - self.last_update < self.cache_timeout):
            return asdict(self.cached_metrics)
        
        with self._lock:
            try:
                # Neue Metriken sammeln
                metrics = self._collect_system_metrics()
                
                # Cache aktualisieren
                self.cached_metrics = metrics
                self.last_update = current_time
                
                # Historie aktualisieren
                self.metrics_history.append(metrics)
                if len(self.metrics_history) > self.history_size:
                    self.metrics_history.pop(0)
                
                return asdict(metrics)
                
            except Exception as e:
                logger.error(f"Fehler beim Sammeln der System-Metriken: {e}")
                return self._get_fallback_metrics()
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """Sammelt alle verfügbaren System-Metriken"""
        
        if not PSUTIL_AVAILABLE:
            return self._get_minimal_metrics()
        
        try:
            # CPU-Metriken
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_temp = self._get_cpu_temperature()
            cpu_freq = psutil.cpu_freq()
            load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
            
            # Memory-Metriken
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Disk-Metriken (Root-Partition)
            disk = psutil.disk_usage('/')
            
            # Netzwerk-Metriken
            network_interfaces = self._get_network_interfaces()
            
            # System-Uptime
            uptime = time.time() - psutil.boot_time()
            
            # WireGuard-Status
            wg_status, tunnel_connected = self._get_wireguard_status()
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=round(cpu_percent, 1),
                cpu_temp=cpu_temp,
                cpu_frequency=round(cpu_freq.current, 1) if cpu_freq and cpu_freq.current else None,
                memory_total=memory.total,
                memory_used=memory.used,
                memory_percent=round(memory.percent, 1),
                disk_total=disk.total,
                disk_used=disk.used,
                disk_percent=round((disk.used / disk.total) * 100, 1),
                swap_total=swap.total,
                swap_used=swap.used,
                swap_percent=round(swap.percent, 1),
                network_interfaces=network_interfaces,
                uptime_seconds=int(uptime),
                load_average=[round(x, 2) for x in load_avg],
                wireguard_status=wg_status,
                tunnel_connected=tunnel_connected
            )
            
        except Exception as e:
            logger.error(f"Fehler bei der Metriken-Sammlung: {e}")
            return self._get_minimal_metrics()
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """CPU-Temperatur ermitteln (optimiert für Raspberry Pi)"""
        temp_sources = [
            # Raspberry Pi
            '/sys/class/thermal/thermal_zone0/temp',
            '/sys/class/thermal/thermal_zone1/temp',
            # Generic thermal zones
            '/sys/class/hwmon/hwmon0/temp1_input',
            '/sys/class/hwmon/hwmon1/temp1_input',
            '/sys/class/hwmon/hwmon2/temp1_input',
            # Alternative Raspberry Pi locations
            '/opt/vc/bin/vcgencmd'  # Special handling below
        ]
        
        # Standard thermal zone files
        for source in temp_sources[:-1]:
            try:
                if os.path.exists(source):
                    with open(source, 'r') as f:
                        temp_raw = int(f.read().strip())
                        temp = temp_raw / 1000.0 if temp_raw > 1000 else temp_raw
                        if 0 <= temp <= 120:  # Plausibilitätsprüfung
                            return round(temp, 1)
            except (OSError, ValueError) as e:
                logger.debug(f"Fehler beim Lesen von {source}: {e}")
                continue
        
        # Raspberry Pi vcgencmd (falls verfügbar)
        try:
            if os.path.exists('/opt/vc/bin/vcgencmd'):
                result = subprocess.run(['/opt/vc/bin/vcgencmd', 'measure_temp'], 
                                      capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    temp_str = result.stdout.strip()
                    if 'temp=' in temp_str:
                        temp = float(temp_str.split('=')[1].replace("'C", ""))
                        if 0 <= temp <= 120:
                            return round(temp, 1)
        except Exception as e:
            logger.debug(f"vcgencmd Fehler: {e}")
        
        # Fallback: psutil thermal sensors
        try:
            if PSUTIL_AVAILABLE and hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        if 0 <= temp <= 120:
                            return round(temp, 1)
        except Exception as e:
            logger.debug(f"psutil Temperatur-Sensor Fehler: {e}")
        
        return None
    
    def _get_network_interfaces(self) -> Dict[str, Dict]:
        """Detaillierte Netzwerk-Interface Informationen"""
        interfaces = {}
        
        if not PSUTIL_AVAILABLE:
            return interfaces
        
        try:
            # Interface-Statistiken von psutil
            net_io = psutil.net_io_counters(pernic=True)
            
            for interface_name in self.network_interfaces:
                if interface_name in net_io:
                    stats = net_io[interface_name]
                    
                    # Interface-Status ermitteln
                    is_up = self._is_interface_up(interface_name)
                    ip_address = self._get_interface_ip(interface_name)
                    speed = self._get_interface_speed(interface_name)
                    
                    interfaces[interface_name] = {
                        'bytes_sent': stats.bytes_sent,
                        'bytes_recv': stats.bytes_recv,
                        'packets_sent': stats.packets_sent,
                        'packets_recv': stats.packets_recv,
                        'errors_in': stats.errin,
                        'errors_out': stats.errout,
                        'drops_in': stats.dropin,
                        'drops_out': stats.dropout,
                        'speed_mbps': speed,
                        'is_up': is_up,
                        'ip_address': ip_address,
                        'last_update': datetime.now().isoformat()
                    }
        
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Netzwerk-Interface Daten: {e}")
        
        return interfaces
    
    def _is_interface_up(self, interface: str) -> bool:
        """Prüft ob ein Netzwerk-Interface aktiv ist"""
        try:
            with open(f'/sys/class/net/{interface}/operstate', 'r') as f:
                state = f.read().strip()
                return state == 'up'
        except:
            return False
    
    def _get_interface_ip(self, interface: str) -> Optional[str]:
        """IP-Adresse eines Interfaces ermitteln"""
        try:
            result = subprocess.run(['ip', 'addr', 'show', interface], 
                                  capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'inet ' in line and not '127.0.0.1' in line:
                        ip_part = line.strip().split()[1]
                        return ip_part.split('/')[0]
        except:
            pass
        return None
    
    def _get_interface_speed(self, interface: str) -> Optional[int]:
        """Interface-Geschwindigkeit ermitteln (in Mbps)"""
        try:
            with open(f'/sys/class/net/{interface}/speed', 'r') as f:
                speed = int(f.read().strip())
                return speed if speed > 0 else None
        except:
            return None
    
    def _get_wireguard_status(self) -> Tuple[str, bool]:
        """WireGuard-Status und Tunnel-Verbindung ermitteln"""
        try:
            # Prüfe Gateway-Interface
            result = subprocess.run(['wg', 'show', 'gateway'], 
                                  capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0:
                output = result.stdout
                if 'peer:' in output:
                    # Prüfe Handshake-Status
                    if 'latest handshake:' in output:
                        # Extrahiere Handshake-Zeit
                        for line in output.split('\n'):
                            if 'latest handshake:' in line and 'seconds ago' in line:
                                try:
                                    seconds_text = line.split('seconds ago')[0].split()[-1]
                                    seconds = int(seconds_text)
                                    # Tunnel als verbunden wenn Handshake < 5 Minuten
                                    connected = seconds < 300
                                    return 'active', connected
                                except (ValueError, IndexError):
                                    pass
                        return 'active', False
                    else:
                        return 'active', False
                else:
                    return 'no_peers', False
            else:
                return 'inactive', False
                
        except Exception as e:
            logger.debug(f"WireGuard-Status Fehler: {e}")
            return 'error', False
    
    def _get_minimal_metrics(self) -> SystemMetrics:
        """Minimale Metriken ohne psutil (Fallback)"""
        try:
            # Load average
            with open('/proc/loadavg', 'r') as f:
                load_avg = [float(x) for x in f.read().split()[:3]]
            
            # Memory-Info
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(':', 1)
                    meminfo[key.strip()] = int(value.split()[0]) * 1024  # kB zu Bytes
            
            memory_total = meminfo.get('MemTotal', 0)
            memory_free = meminfo.get('MemFree', 0) + meminfo.get('Buffers', 0) + meminfo.get('Cached', 0)
            memory_used = memory_total - memory_free
            memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
            
            # Disk-Info
            disk = os.statvfs('/')
            disk_total = disk.f_frsize * disk.f_blocks
            disk_free = disk.f_frsize * disk.f_bavail
            disk_used = disk_total - disk_free
            disk_percent = (disk_used / disk_total) * 100 if disk_total > 0 else 0
            
            # Uptime
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.read().split()[0])
            
            # WireGuard-Status
            wg_status, tunnel_connected = self._get_wireguard_status()
            
            return SystemMetrics(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,  # Nicht verfügbar
                cpu_temp=self._get_cpu_temperature(),
                cpu_frequency=None,
                memory_total=memory_total,
                memory_used=memory_used,
                memory_percent=round(memory_percent, 1),
                disk_total=disk_total,
                disk_used=disk_used,
                disk_percent=round(disk_percent, 1),
                swap_total=meminfo.get('SwapTotal', 0),
                swap_used=meminfo.get('SwapTotal', 0) - meminfo.get('SwapFree', 0),
                swap_percent=0.0,  # Berechnung vereinfacht
                network_interfaces={},
                uptime_seconds=int(uptime),
                load_average=load_avg,
                wireguard_status=wg_status,
                tunnel_connected=tunnel_connected
            )
            
        except Exception as e:
            logger.error(f"Fehler bei minimalen Metriken: {e}")
            return self._get_fallback_metrics()
    
    def _get_fallback_metrics(self) -> Dict:
        """Absolute Fallback-Metriken bei allen Fehlern"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': 0.0,
            'cpu_temp': None,
            'cpu_frequency': None,
            'memory_total': 0,
            'memory_used': 0,
            'memory_percent': 0.0,
            'disk_total': 0,
            'disk_used': 0,
            'disk_percent': 0.0,
            'swap_total': 0,
            'swap_used': 0,
            'swap_percent': 0.0,
            'network_interfaces': {},
            'uptime_seconds': 0,
            'load_average': [0.0, 0.0, 0.0],
            'wireguard_status': 'error',
            'tunnel_connected': False,
            'error': 'Monitoring nicht verfügbar'
        }
    
    def check_alerts(self, metrics: Dict) -> List[Dict]:
        """
        Prüft System-Metriken auf kritische Werte
        
        Args:
            metrics: System-Metriken Dictionary
            
        Returns:
            Liste von Alert-Dictionaries
        """
        alerts = []
        current_time = datetime.now()
        
        # CPU-Überlastung
        if metrics.get('cpu_percent', 0) > self.alert_thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"CPU-Auslastung bei {metrics['cpu_percent']}%",
                'value': metrics['cpu_percent'],
                'threshold': self.alert_thresholds['cpu_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Memory-Überlastung
        if metrics.get('memory_percent', 0) > self.alert_thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"Speicher-Auslastung bei {metrics['memory_percent']}%",
                'value': metrics['memory_percent'],
                'threshold': self.alert_thresholds['memory_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Disk-Überlastung
        if metrics.get('disk_percent', 0) > self.alert_thresholds['disk_percent']:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f"Festplatten-Auslastung bei {metrics['disk_percent']}%",
                'value': metrics['disk_percent'],
                'threshold': self.alert_thresholds['disk_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Temperatur-Überwachung
        if metrics.get('cpu_temp') and metrics['cpu_temp'] > self.alert_thresholds['cpu_temp']:
            alerts.append({
                'type': 'temperature_high',
                'severity': 'critical',
                'message': f"CPU-Temperatur bei {metrics['cpu_temp']}°C",
                'value': metrics['cpu_temp'],
                'threshold': self.alert_thresholds['cpu_temp'],
                'timestamp': current_time.isoformat()
            })
        
        # Swap-Verwendung
        if metrics.get('swap_percent', 0) > self.alert_thresholds['swap_percent']:
            alerts.append({
                'type': 'swap_high',
                'severity': 'warning',
                'message': f"Swap-Verwendung bei {metrics['swap_percent']}%",
                'value': metrics['swap_percent'],
                'threshold': self.alert_thresholds['swap_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # WireGuard-Status
        if metrics.get('wireguard_status') == 'error':
            alerts.append({
                'type': 'wireguard_error',
                'severity': 'critical',
                'message': "WireGuard Interface nicht verfügbar",
                'timestamp': current_time.isoformat()
            })
        elif not metrics.get('tunnel_connected', False):
            alerts.append({
                'type': 'tunnel_disconnected',
                'severity': 'warning',
                'message': "WireGuard Tunnel nicht verbunden",
                'timestamp': current_time.isoformat()
            })
        
        # Netzwerk-Interface Fehler
        for iface_name, iface_data in metrics.get('network_interfaces', {}).items():
            if iface_data.get('errors_in', 0) > 100 or iface_data.get('errors_out', 0) > 100:
                alerts.append({
                    'type': 'network_errors',
                    'severity': 'warning',
                    'message': f"Netzwerk-Fehler auf {iface_name}",
                    'interface': iface_name,
                    'errors_in': iface_data.get('errors_in', 0),
                    'errors_out': iface_data.get('errors_out', 0),
                    'timestamp': current_time.isoformat()
                })
        
        return alerts
    
    def get_metrics_history(self, minutes: int = 60) -> List[Dict]:
        """
        Historische Metriken der letzten N Minuten
        
        Args:
            minutes: Anzahl Minuten für Historie
            
        Returns:
            Liste von Metriken-Dictionaries
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            filtered_metrics = []
            for metrics in self.metrics_history:
                metrics_time = datetime.fromisoformat(metrics.timestamp)
                if metrics_time >= cutoff_time:
                    filtered_metrics.append(asdict(metrics))
            
            return filtered_metrics
    
    def get_performance_summary(self) -> Dict:
        """
        Performance-Zusammenfassung über die letzten Metriken
        
        Returns:
            Dictionary mit Durchschnitts- und Peak-Werten
        """
        if not self.metrics_history:
            return {}
        
        with self._lock:
            recent_metrics = self.metrics_history[-20:]  # Letzte 20 Messungen
            
            cpu_values = [m.cpu_percent for m in recent_metrics]
            memory_values = [m.memory_percent for m in recent_metrics]
            temp_values = [m.cpu_temp for m in recent_metrics if m.cpu_temp is not None]
            load_values = [m.load_average[0] for m in recent_metrics if m.load_average]
            
            return {
                'cpu_avg': round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0,
                'cpu_peak': round(max(cpu_values), 1) if cpu_values else 0,
                'memory_avg': round(sum(memory_values) / len(memory_values), 1) if memory_values else 0,
                'memory_peak': round(max(memory_values), 1) if memory_values else 0,
                'temp_avg': round(sum(temp_values) / len(temp_values), 1) if temp_values else None,
                'temp_peak': round(max(temp_values), 1) if temp_values else None,
                'load_avg': round(sum(load_values) / len(load_values), 2) if load_values else 0,
                'load_peak': round(max(load_values), 2) if load_values else 0,
                'sample_count': len(recent_metrics),
                'time_span_minutes': len(recent_metrics) * (self.cache_timeout / 60),
                'tunnel_uptime_percent': sum(1 for m in recent_metrics if m.tunnel_connected) / len(recent_metrics) * 100
            }
    
    def export_metrics(self, filepath: str, format: str = 'json') -> bool:
        """
        Exportiert Metriken in verschiedene Formate
        
        Args:
            filepath: Pfad für Export-Datei
            format: Format (json, csv)
            
        Returns:
            True bei Erfolg, False bei Fehler
        """
        try:
            with self._lock:
                if format.lower() == 'json':
                    with open(filepath, 'w') as f:
                        json.dump([asdict(m) for m in self.metrics_history], f, indent=2)
                elif format.lower() == 'csv':
                    import csv
                    with open(filepath, 'w', newline='') as f:
                        if self.metrics_history:
                            writer = csv.DictWriter(f, fieldnames=asdict(self.metrics_history[0]).keys())
                            writer.writeheader()
                            for metrics in self.metrics_history:
                                writer.writerow(asdict(metrics))
                else:
                    logger.error(f"Unbekanntes Export-Format: {format}")
                    return False
                
                logger.info(f"Metriken erfolgreich nach {filepath} exportiert ({format})")
                return True
                
        except Exception as e:
            logger.error(f"Fehler beim Export der Metriken: {e}")
            return False

# Globale Monitor-Instanz
system_monitor = SystemMonitor()