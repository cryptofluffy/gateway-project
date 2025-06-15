#!/usr/bin/env python3
"""
Optimierter VPS Server Startup - Verhindert Hangs und Memory-Leaks
"""

import os
import sys
import logging
import signal
import psutil
from config import config

# Logging konfigurieren BEVOR andere Module geladen werden
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def setup_signal_handlers():
    """Setup für sauberen Shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Signal {signum} erhalten - sauberer Shutdown")
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def check_system_resources():
    """Prüfe System-Ressourcen vor Start"""
    try:
        # Memory check
        memory = psutil.virtual_memory()
        if memory.available < 100 * 1024 * 1024:  # 100MB
            logger.warning(f"Wenig verfügbarer Speicher: {memory.available // 1024 // 1024}MB")
        
        # Disk check  
        disk = psutil.disk_usage('/')
        if disk.free < 500 * 1024 * 1024:  # 500MB
            logger.warning(f"Wenig Festplattenspeicher: {disk.free // 1024 // 1024}MB")
            
        # Load check
        if hasattr(psutil, 'getloadavg'):
            load = psutil.getloadavg()[0]
            cpu_count = psutil.cpu_count()
            if load > cpu_count * 2:
                logger.warning(f"Hohe Systemlast: {load} (CPUs: {cpu_count})")
                
    except Exception as e:
        logger.warning(f"Ressourcenprüfung fehlgeschlagen: {e}")

def optimize_for_hardware():
    """Hardware-spezifische Optimierungen"""
    if config.is_raspberry_pi:
        logger.info("Raspberry Pi Optimierungen aktiviert")
        # Reduziere SocketIO Ping-Intervall
        os.environ['SOCKETIO_PING_INTERVAL'] = '60'
        os.environ['SOCKETIO_PING_TIMEOUT'] = '30'
    
    if config.is_low_memory:
        logger.info("Low-Memory Optimierungen aktiviert")
        # Reduziere Cache-Größen
        os.environ['WERKZEUG_CACHE_THRESHOLD'] = '50'

def main():
    """Hauptfunktion mit verbesserter Fehlerbehandlung"""
    logger.info("VPS Server wird gestartet...")
    
    # Signal-Handler setzen
    setup_signal_handlers()
    
    # System-Ressourcen prüfen
    check_system_resources()
    
    # Hardware-Optimierungen
    optimize_for_hardware()
    
    # Verzeichnisse erstellen
    try:
        os.makedirs(config.DATA_DIR, mode=0o750, exist_ok=True)
        os.makedirs(os.path.dirname(config.LOG_FILE), mode=0o750, exist_ok=True)
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Verzeichnisse: {e}")
        sys.exit(1)
    
    # App importieren und starten
    try:
        from app import app, socketio, realtime_monitor
        
        logger.info(f"Server startet auf {config.HOST}:{config.PORT}")
        logger.info(f"Debug-Modus: {config.DEBUG}")
        logger.info(f"Monitoring: {config.monitoring.MONITORING_ENABLED}")
        
        # Monitoring starten
        if config.monitoring.MONITORING_ENABLED:
            realtime_monitor.start()
        
        # Server starten
        socketio.run(
            app, 
            host=config.HOST, 
            port=config.PORT, 
            debug=config.DEBUG,
            allow_unsafe_werkzeug=True,
            use_reloader=False  # Verhindert doppelte Prozesse
        )
        
    except ImportError as e:
        logger.error(f"Import-Fehler: {e}")
        logger.error("Möglicherweise fehlen Python-Abhängigkeiten")
        sys.exit(1)
    except PermissionError as e:
        logger.error(f"Berechtigung verweigert: {e}")
        logger.error("Server benötigt möglicherweise Root-Rechte")
        sys.exit(1)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"Port {config.PORT} bereits in Verwendung")
            logger.info("Andere Server-Instanz läuft möglicherweise bereits")
        else:
            logger.error(f"OS-Fehler: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Server durch Benutzer gestoppt")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # Cleanup
        try:
            if 'realtime_monitor' in locals():
                realtime_monitor.stop()
        except:
            pass
        logger.info("Server beendet")

if __name__ == '__main__':
    main()