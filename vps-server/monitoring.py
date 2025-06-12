#!/usr/bin/env python3
"""
System Monitoring Module für WireGuard Gateway VPS
Umfassendes Monitoring von CPU, RAM, Temperatur, Netzwerk und WireGuard
"""

import os
import time
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logging.warning("psutil not available - system monitoring limited")

logger = logging.getLogger(__name__)

@dataclass
class SystemStats:
    """System statistics data structure"""
    timestamp: str
    cpu_percent: float
    cpu_temp: Optional[float]
    memory_total: int
    memory_used: int
    memory_percent: float
    disk_total: int
    disk_used: int
    disk_percent: float
    network_bytes_sent: int
    network_bytes_recv: int
    wireguard_connected_peers: int
    wireguard_status: str
    uptime_seconds: int
    load_average: List[float]

@dataclass
class ProcessStats:
    """Process-specific statistics"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_rss: int
    status: str

class SystemMonitor:
    """Umfassendes System-Monitoring mit Caching und Historie"""
    
    def __init__(self, history_size: int = 50):
        # Begrenzte Historie für bessere Performance auf schwächerer Hardware
        self.history_size = min(history_size, 50)  # Begrenzt für Raspberry Pi
        self.stats_history: List[SystemStats] = []
        
        # Längeres Caching reduziert CPU-Last erheblich
        self.cache_timeout = 10  # Längeres Caching für weniger CPU-Last
        self.last_update = 0
        self.cached_stats: Optional[SystemStats] = None
        
        # Thread-Sicherheit für gleichzeitige Zugriffe
        self._lock = threading.Lock()
        
        # Hardware-spezifische Optimierungen
        self._is_rpi = self._detect_raspberry_pi()
        
    def get_current_stats(self, force_refresh: bool = False) -> Dict:
        """
        Aktuelle System-Statistiken abrufen mit intelligentem Caching
        
        Args:
            force_refresh: Cache umgehen und neue Daten sammeln
            
        Returns:
            Dictionary mit aktuellen System-Statistiken
        """
        current_time = time.time()
        
        # Cache prüfen - verhindert unnötige System-Calls
        # Besonders wichtig auf Pi wo System-Calls teuer sind
        if (not force_refresh and 
            self.cached_stats and 
            current_time - self.last_update < self.cache_timeout):
            return asdict(self.cached_stats)
        
        with self._lock:
            try:
                # Neue Statistiken sammeln
                stats = self._collect_system_stats()
                
                # Cache aktualisieren
                self.cached_stats = stats
                self.last_update = current_time
                
                # Historie aktualisieren
                self.stats_history.append(stats)
                if len(self.stats_history) > self.history_size:
                    self.stats_history.pop(0)
                
                return asdict(stats)
                
            except Exception as e:
                logger.error(f"Fehler beim Sammeln der System-Statistiken: {e}")
                return self._get_fallback_stats()
    
    def _collect_system_stats(self) -> SystemStats:
        """Sammelt alle verfügbaren System-Statistiken"""
        
        if not PSUTIL_AVAILABLE:
            return self._get_minimal_stats()
        
        try:
            # CPU-Statistiken (optimiert für Raspberry Pi)
            # Längere Intervalle reduzieren CPU-Last auf schwächeren Systemen
            interval = 0.5 if self._is_rpi else 0.1  # Längere Messintervalle auf Pi
            cpu_percent = psutil.cpu_percent(interval=interval)
            
            # Temperatur-Monitoring besonders wichtig für Pi (Throttling-Schutz)
            cpu_temp = self._get_cpu_temperature()
            
            # Load Average für bessere Performance-Einschätzung
            load_avg = list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else [0.0, 0.0, 0.0]
            
            # Memory-Statistiken
            memory = psutil.virtual_memory()
            
            # Disk-Statistiken
            disk = psutil.disk_usage('/')
            
            # Netzwerk-Statistiken
            network = psutil.net_io_counters()
            
            # System-Uptime
            uptime = time.time() - psutil.boot_time()
            
            # WireGuard-Statistiken
            wg_stats = self._get_wireguard_stats()
            
            return SystemStats(
                timestamp=datetime.now().isoformat(),
                cpu_percent=round(cpu_percent, 1),
                cpu_temp=cpu_temp,
                memory_total=memory.total,
                memory_used=memory.used,
                memory_percent=round(memory.percent, 1),
                disk_total=disk.total,
                disk_used=disk.used,
                disk_percent=round((disk.used / disk.total) * 100, 1),
                network_bytes_sent=network.bytes_sent,
                network_bytes_recv=network.bytes_recv,
                wireguard_connected_peers=wg_stats['connected_peers'],
                wireguard_status=wg_stats['status'],
                uptime_seconds=int(uptime),
                load_average=load_avg
            )
            
        except Exception as e:
            logger.debug(f"Fehler bei der Statistik-Sammlung: {e}")  # Debug statt Error
            return self._get_minimal_stats()
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """CPU-Temperatur aus verschiedenen Quellen ermitteln"""
        temp_sources = [
            '/sys/class/thermal/thermal_zone0/temp',
            '/sys/class/thermal/thermal_zone1/temp',
            '/sys/class/hwmon/hwmon0/temp1_input',
            '/sys/class/hwmon/hwmon1/temp1_input',
            '/sys/class/hwmon/hwmon2/temp1_input'
        ]
        
        for source in temp_sources:
            try:
                if os.path.exists(source):
                    with open(source, 'r') as f:
                        temp_raw = int(f.read().strip())
                        # Konvertierung: Milligrad zu Grad
                        temp = temp_raw / 1000.0 if temp_raw > 1000 else temp_raw
                        # Plausibilitätsprüfung (0-100°C)
                        if 0 <= temp <= 100:
                            return round(temp, 1)
            except (OSError, ValueError) as e:
                logger.debug(f"Fehler beim Lesen von {source}: {e}")
                continue
        
        # Fallback: psutil thermal sensors (falls verfügbar)
        try:
            if hasattr(psutil, 'sensors_temperatures'):
                temps = psutil.sensors_temperatures()
                for name, entries in temps.items():
                    if entries:
                        temp = entries[0].current
                        if 0 <= temp <= 100:
                            return round(temp, 1)
        except Exception as e:
            logger.debug(f"psutil Temperatur-Sensor Fehler: {e}")
        
        return None
    
    def _get_wireguard_stats(self) -> Dict:
        """WireGuard-Statistiken ermitteln"""
        try:
            import subprocess
            result = subprocess.run(
                ['wg', 'show', 'wg0'], 
                capture_output=True, 
                text=True, 
                timeout=5
            )
            
            if result.returncode == 0:
                # Anzahl verbundener Peers zählen
                peers = result.stdout.count('peer:')
                
                # Handshake-Zeiten analysieren für aktive Verbindungen
                lines = result.stdout.split('\n')
                active_peers = 0
                for line in lines:
                    if 'latest handshake:' in line and 'seconds ago' in line:
                        # Peer ist aktiv wenn Handshake < 5 Minuten
                        try:
                            seconds_text = line.split('seconds ago')[0].split()[-1]
                            seconds = int(seconds_text)
                            if seconds < 300:  # 5 Minuten
                                active_peers += 1
                        except (ValueError, IndexError):
                            pass
                
                return {
                    'connected_peers': active_peers,
                    'total_peers': peers,
                    'status': 'active' if peers > 0 else 'no_peers'
                }
            else:
                return {
                    'connected_peers': 0,
                    'total_peers': 0,
                    'status': 'inactive'
                }
                
        except Exception as e:
            logger.debug(f"WireGuard-Statistik Fehler: {e}")
            return {
                'connected_peers': 0,
                'total_peers': 0,
                'status': 'error'
            }
    
    def _get_minimal_stats(self) -> SystemStats:
        """Minimale Statistiken ohne psutil (Fallback)"""
        try:
            # Basis-Informationen aus /proc filesystem
            with open('/proc/loadavg', 'r') as f:
                load_avg = [float(x) for x in f.read().split()[:3]]
            
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    key, value = line.split(':', 1)
                    meminfo[key.strip()] = int(value.split()[0]) * 1024  # kB zu Bytes
            
            memory_total = meminfo.get('MemTotal', 0)
            memory_free = meminfo.get('MemFree', 0) + meminfo.get('Buffers', 0) + meminfo.get('Cached', 0)
            memory_used = memory_total - memory_free
            memory_percent = (memory_used / memory_total) * 100 if memory_total > 0 else 0
            
            # Disk-Info (root partition)
            disk = os.statvfs('/')
            disk_total = disk.f_frsize * disk.f_blocks
            disk_free = disk.f_frsize * disk.f_bavail
            disk_used = disk_total - disk_free
            disk_percent = (disk_used / disk_total) * 100 if disk_total > 0 else 0
            
            # Uptime
            with open('/proc/uptime', 'r') as f:
                uptime = float(f.read().split()[0])
            
            return SystemStats(
                timestamp=datetime.now().isoformat(),
                cpu_percent=0.0,  # Nicht verfügbar ohne psutil
                cpu_temp=self._get_cpu_temperature(),
                memory_total=memory_total,
                memory_used=memory_used,
                memory_percent=round(memory_percent, 1),
                disk_total=disk_total,
                disk_used=disk_used,
                disk_percent=round(disk_percent, 1),
                network_bytes_sent=0,  # Nicht verfügbar
                network_bytes_recv=0,  # Nicht verfügbar
                wireguard_connected_peers=0,
                wireguard_status='unknown',
                uptime_seconds=int(uptime),
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error(f"Fehler bei minimalen Statistiken: {e}")
            return self._get_fallback_stats()
    
    def _get_fallback_stats(self) -> Dict:
        """Absolute Fallback-Statistiken bei allen Fehlern"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': 0.0,
            'cpu_temp': None,
            'memory_total': 0,
            'memory_used': 0,
            'memory_percent': 0.0,
            'disk_total': 0,
            'disk_used': 0,
            'disk_percent': 0.0,
            'network_bytes_sent': 0,
            'network_bytes_recv': 0,
            'wireguard_connected_peers': 0,
            'wireguard_status': 'error',
            'uptime_seconds': 0,
            'load_average': [0.0, 0.0, 0.0],
            'error': 'Monitoring nicht verfügbar'
        }
    
    def _detect_raspberry_pi(self) -> bool:
        """Erkennt ob auf Raspberry Pi ausgeführt wird"""
        try:
            # /proc/cpuinfo enthält Hardware-Informationen
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read().lower()
                # Raspberry Pi hat charakteristische Bezeichnungen
                return 'raspberry pi' in content or 'bcm' in content
        except:
            # Bei Fehlern konservativ annehmen: kein Pi
            return False
    
    def get_process_stats(self, process_names: List[str] = None) -> List[ProcessStats]:
        """
        Statistiken für spezifische Prozesse
        
        Args:
            process_names: Liste der zu überwachenden Prozess-Namen
            
        Returns:
            Liste von ProcessStats für gefundene Prozesse
        """
        if not PSUTIL_AVAILABLE:
            return []
        
        if process_names is None:
            process_names = ['python', 'wireguard', 'wg-quick']
        
        processes = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'memory_info', 'status']):
                try:
                    if any(name in proc.info['name'].lower() for name in process_names):
                        processes.append(ProcessStats(
                            pid=proc.info['pid'],
                            name=proc.info['name'],
                            cpu_percent=round(proc.info['cpu_percent'] or 0.0, 1),
                            memory_percent=round(proc.info['memory_percent'] or 0.0, 1),
                            memory_rss=proc.info['memory_info'].rss if proc.info['memory_info'] else 0,
                            status=proc.info['status']
                        ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            logger.error(f"Fehler beim Sammeln der Prozess-Statistiken: {e}")
        
        return processes
    
    def get_stats_history(self, minutes: int = 60) -> List[Dict]:
        """
        Historische Statistiken der letzten N Minuten
        
        Args:
            minutes: Anzahl Minuten für Historie
            
        Returns:
            Liste von Statistik-Dictionaries
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            filtered_stats = []
            for stats in self.stats_history:
                stats_time = datetime.fromisoformat(stats.timestamp)
                if stats_time >= cutoff_time:
                    filtered_stats.append(asdict(stats))
            
            return filtered_stats
    
    def get_performance_summary(self) -> Dict:
        """
        Performance-Zusammenfassung über die letzten Statistiken
        
        Returns:
            Dictionary mit Durchschnitts- und Peak-Werten
        """
        if not self.stats_history:
            return {}
        
        with self._lock:
            # Weniger Samples auf Pi reduziert Speicher- und CPU-Verbrauch
            sample_size = 10 if self._is_rpi else 20  # Weniger Samples auf Pi
            
            # Extrahiere Werte für Performance-Analyse
            cpu_values = [s.cpu_percent for s in self.stats_history[-sample_size:]]
            memory_values = [s.memory_percent for s in self.stats_history[-sample_size:]]
            temp_values = [s.cpu_temp for s in self.stats_history[-sample_size:] if s.cpu_temp is not None]
            
            return {
                'cpu_avg': round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0,
                'cpu_peak': round(max(cpu_values), 1) if cpu_values else 0,
                'memory_avg': round(sum(memory_values) / len(memory_values), 1) if memory_values else 0,
                'memory_peak': round(max(memory_values), 1) if memory_values else 0,
                'temp_avg': round(sum(temp_values) / len(temp_values), 1) if temp_values else None,
                'temp_peak': round(max(temp_values), 1) if temp_values else None,
                'sample_count': len(cpu_values),
                'time_span_minutes': len(cpu_values) * (self.cache_timeout / 60)
            }

class AlertManager:
    """Alert-System für kritische System-Zustände"""
    
    def __init__(self):
        self.thresholds = {
            'cpu_percent': 90.0,
            'memory_percent': 90.0,
            'disk_percent': 95.0,
            'cpu_temp': 80.0
        }
        self.alert_history: List[Dict] = []
        self.max_history = 100
    
    def check_alerts(self, stats: Dict) -> List[Dict]:
        """
        Überprüft System-Statistiken auf kritische Werte
        
        Args:
            stats: System-Statistiken Dictionary
            
        Returns:
            Liste von Alert-Dictionaries
        """
        alerts = []
        current_time = datetime.now()
        
        # CPU-Überlastung
        if stats.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'severity': 'warning',
                'message': f"CPU-Auslastung bei {stats['cpu_percent']}%",
                'value': stats['cpu_percent'],
                'threshold': self.thresholds['cpu_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Memory-Überlastung
        if stats.get('memory_percent', 0) > self.thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'severity': 'warning',
                'message': f"Speicher-Auslastung bei {stats['memory_percent']}%",
                'value': stats['memory_percent'],
                'threshold': self.thresholds['memory_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Disk-Überlastung
        if stats.get('disk_percent', 0) > self.thresholds['disk_percent']:
            alerts.append({
                'type': 'disk_high',
                'severity': 'critical',
                'message': f"Festplatten-Auslastung bei {stats['disk_percent']}%",
                'value': stats['disk_percent'],
                'threshold': self.thresholds['disk_percent'],
                'timestamp': current_time.isoformat()
            })
        
        # Temperatur-Überwachung
        if stats.get('cpu_temp') and stats['cpu_temp'] > self.thresholds['cpu_temp']:
            alerts.append({
                'type': 'temperature_high',
                'severity': 'critical',
                'message': f"CPU-Temperatur bei {stats['cpu_temp']}°C",
                'value': stats['cpu_temp'],
                'threshold': self.thresholds['cpu_temp'],
                'timestamp': current_time.isoformat()
            })
        
        # WireGuard-Status
        if stats.get('wireguard_status') == 'error':
            alerts.append({
                'type': 'wireguard_error',
                'severity': 'critical',
                'message': "WireGuard Interface nicht verfügbar",
                'timestamp': current_time.isoformat()
            })
        
        # Alerts zur Historie hinzufügen
        for alert in alerts:
            self.alert_history.append(alert)
        
        # Historie begrenzen
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        return alerts
    
    def get_recent_alerts(self, hours: int = 24) -> List[Dict]:
        """
        Kürzlich aufgetretene Alerts abrufen
        
        Args:
            hours: Zeitraum in Stunden
            
        Returns:
            Liste der Alerts im Zeitraum
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        recent_alerts = []
        for alert in self.alert_history:
            alert_time = datetime.fromisoformat(alert['timestamp'])
            if alert_time >= cutoff_time:
                recent_alerts.append(alert)
        
        return recent_alerts

# Globale Instanzen
system_monitor = SystemMonitor()
alert_manager = AlertManager()

def get_system_health() -> Dict:
    """
    Umfassender System-Gesundheitscheck
    
    Returns:
        Dictionary mit Gesundheits-Status und Details
    """
    try:
        stats = system_monitor.get_current_stats()
        alerts = alert_manager.check_alerts(stats)
        performance = system_monitor.get_performance_summary()
        
        # Gesundheits-Score berechnen (0-100)
        health_score = 100
        if stats.get('cpu_percent', 0) > 80:
            health_score -= 20
        if stats.get('memory_percent', 0) > 80:
            health_score -= 20
        if stats.get('disk_percent', 0) > 90:
            health_score -= 30
        if stats.get('cpu_temp') and stats['cpu_temp'] > 70:
            health_score -= 15
        if stats.get('wireguard_status') != 'active':
            health_score -= 15
        
        # Status bestimmen
        if health_score >= 90:
            status = 'excellent'
        elif health_score >= 70:
            status = 'good'
        elif health_score >= 50:
            status = 'warning'
        else:
            status = 'critical'
        
        return {
            'status': status,
            'health_score': max(0, health_score),
            'current_stats': stats,
            'alerts': alerts,
            'performance_summary': performance,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Fehler beim System-Gesundheitscheck: {e}")
        return {
            'status': 'error',
            'health_score': 0,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }