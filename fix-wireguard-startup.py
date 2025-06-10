#!/usr/bin/env python3
"""
Automatischer WireGuard-Konfiguration Fix beim VPS-Start
Repariert fehlerhafte Shell-Substitutionen in WireGuard-Konfigurationen
"""

import os
import sys
import logging
import subprocess

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_wireguard_config():
    """Repariere WireGuard-Konfiguration automatisch"""
    config_path = '/etc/wireguard/wg0.conf'
    private_key_paths = [
        '/etc/wireguard/server_private.key',
        '/etc/wireguard/privatekey'
    ]
    
    try:
        # Private Key laden
        private_key = None
        for key_path in private_key_paths:
            if os.path.exists(key_path):
                with open(key_path, 'r') as f:
                    private_key = f.read().strip()
                    logger.info(f"Private key found at {key_path}")
                    break
        
        if not private_key:
            logger.error("No private key found - generating new one")
            # Generiere neuen Private Key
            result = subprocess.run(['wg', 'genkey'], capture_output=True, text=True)
            if result.returncode == 0:
                private_key = result.stdout.strip()
                
                # Speichere Private Key
                os.makedirs('/etc/wireguard', exist_ok=True)
                with open('/etc/wireguard/server_private.key', 'w') as f:
                    f.write(private_key)
                os.chmod('/etc/wireguard/server_private.key', 0o600)
                
                # Generiere und speichere Public Key
                proc = subprocess.Popen(['wg', 'pubkey'], stdin=subprocess.PIPE, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = proc.communicate(input=private_key)
                if proc.returncode == 0:
                    public_key = stdout.strip()
                    with open('/etc/wireguard/server_public.key', 'w') as f:
                        f.write(public_key)
                    logger.info(f"Generated new keys - Public key: {public_key}")
                else:
                    logger.error(f"Failed to generate public key: {stderr}")
                    return False
            else:
                logger.error("Failed to generate private key")
                return False
        
        # Prüfe und repariere Konfiguration
        needs_fix = False
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                content = f.read()
                
            # Prüfe auf fehlerhafte Shell-Substitution
            if '$(cat' in content or 'PrivateKey = ' not in content:
                logger.warning("Found shell substitution in WireGuard config - fixing...")
                needs_fix = True
        else:
            logger.info("WireGuard config not found - creating new one")
            needs_fix = True
        
        if needs_fix:
            # Erstelle korrekte Konfiguration
            config_content = f"""[Interface]
PrivateKey = {private_key}
Address = 10.8.0.1/24
ListenPort = 51820
SaveConfig = false

# IP-Forwarding und NAT
PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -A FORWARD -o %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -D FORWARD -o %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

"""
            
            # Backup erstellen
            if os.path.exists(config_path):
                subprocess.run(['cp', config_path, f'{config_path}.backup'], check=False)
            
            # Neue Konfiguration schreiben
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            os.chmod(config_path, 0o600)
            logger.info(f"WireGuard config fixed at {config_path}")
            
            # IP-Forwarding aktivieren
            try:
                subprocess.run(['sysctl', '-w', 'net.ipv4.ip_forward=1'], check=True)
                logger.info("IP forwarding enabled")
            except subprocess.CalledProcessError:
                logger.warning("Could not enable IP forwarding")
            
            return True
        else:
            logger.info("WireGuard config is already correct")
            return True
            
    except Exception as e:
        logger.error(f"Error fixing WireGuard config: {e}")
        return False

def restart_wireguard():
    """WireGuard Interface neu starten"""
    try:
        # Interface stoppen (falls es läuft)
        subprocess.run(['wg-quick', 'down', 'wg0'], capture_output=True)
        
        # Interface starten
        result = subprocess.run(['wg-quick', 'up', 'wg0'], capture_output=True, text=True)
        if result.returncode == 0:
            logger.info("WireGuard interface started successfully")
            return True
        else:
            logger.error(f"Failed to start WireGuard interface: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error restarting WireGuard: {e}")
        return False

if __name__ == "__main__":
    logger.info("Starting WireGuard configuration fix...")
    
    # Konfiguration reparieren
    if fix_wireguard_config():
        logger.info("WireGuard configuration fix completed")
        
        # WireGuard neu starten
        if restart_wireguard():
            logger.info("WireGuard restarted successfully")
            sys.exit(0)
        else:
            logger.error("Failed to restart WireGuard")
            sys.exit(1)
    else:
        logger.error("Failed to fix WireGuard configuration")
        sys.exit(1)