#!/usr/bin/env python3
"""
WireGuard Gateway GUI Application
Grafische Benutzeroberfläche für den Gateway-PC
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
import json
import requests
from datetime import datetime
from gateway_manager import WireGuardGateway, GatewayMonitor

class GatewayGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("WireGuard Gateway Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Gateway-Manager initialisieren
        self.gateway = WireGuardGateway()
        self.monitor = GatewayMonitor(self.gateway)
        
        # GUI-Variablen
        self.status_var = tk.StringVar(value="Unbekannt")
        self.client_count_var = tk.StringVar(value="0")
        self.uptime_var = tk.StringVar(value="--")
        self.data_transferred_var = tk.StringVar(value="-- / --")
        
        self.setup_gui()
        self.start_status_updates()
    
    def setup_gui(self):
        """GUI-Layout erstellen"""
        # Haupt-Container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Grid-Gewichtung
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # Titel
        title_label = ttk.Label(main_frame, text="WireGuard Gateway Manager", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status-Sektion
        self.create_status_section(main_frame, row=1)
        
        # Kontroll-Buttons
        self.create_control_section(main_frame, row=2)
        
        # Informations-Tabs
        self.create_info_tabs(main_frame, row=3)
    
    def create_status_section(self, parent, row):
        """Status-Übersicht erstellen"""
        status_frame = ttk.LabelFrame(parent, text="Gateway Status", padding="10")
        status_frame.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.grid_columnconfigure(1, weight=1)
        status_frame.grid_columnconfigure(3, weight=1)
        
        # Status-Indikatoren
        ttk.Label(status_frame, text="Tunnel-Status:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     font=("Arial", 10, "bold"))
        self.status_label.grid(row=0, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="Verbundene Clients:").grid(row=0, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(status_frame, textvariable=self.client_count_var, 
                 font=("Arial", 10, "bold")).grid(row=0, column=3, sticky=tk.W)
        
        ttk.Label(status_frame, text="Laufzeit:").grid(row=1, column=0, sticky=tk.W, padx=(0, 10))
        ttk.Label(status_frame, textvariable=self.uptime_var).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Label(status_frame, text="Datenverkehr (RX/TX):").grid(row=1, column=2, sticky=tk.W, padx=(20, 10))
        ttk.Label(status_frame, textvariable=self.data_transferred_var).grid(row=1, column=3, sticky=tk.W)
    
    def create_control_section(self, parent, row):
        """Kontroll-Buttons erstellen"""
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=0, columnspan=3, pady=(0, 10))
        
        # Tunnel-Kontrolle
        tunnel_frame = ttk.LabelFrame(control_frame, text="Tunnel-Kontrolle", padding="10")
        tunnel_frame.grid(row=0, column=0, padx=(0, 10), sticky=(tk.N, tk.S))
        
        self.start_button = ttk.Button(tunnel_frame, text="Tunnel starten", 
                                      command=self.start_tunnel, width=15)
        self.start_button.grid(row=0, column=0, pady=2)
        
        self.stop_button = ttk.Button(tunnel_frame, text="Tunnel stoppen", 
                                     command=self.stop_tunnel, width=15)
        self.stop_button.grid(row=1, column=0, pady=2)
        
        self.restart_button = ttk.Button(tunnel_frame, text="Tunnel neustarten", 
                                        command=self.restart_tunnel, width=15)
        self.restart_button.grid(row=2, column=0, pady=2)
        
        # Konfiguration
        config_frame = ttk.LabelFrame(control_frame, text="Konfiguration", padding="10")
        config_frame.grid(row=0, column=1, padx=(0, 10), sticky=(tk.N, tk.S))
        
        ttk.Button(config_frame, text="Gateway konfigurieren", 
                  command=self.configure_gateway, width=15).grid(row=0, column=0, pady=2)
        
        ttk.Button(config_frame, text="Konfiguration anzeigen", 
                  command=self.show_config, width=15).grid(row=1, column=0, pady=2)
        
        ttk.Button(config_frame, text="Logs anzeigen", 
                  command=self.show_logs, width=15).grid(row=2, column=0, pady=2)
        
        # Monitoring
        monitor_frame = ttk.LabelFrame(control_frame, text="Monitoring", padding="10")
        monitor_frame.grid(row=0, column=2, sticky=(tk.N, tk.S))
        
        self.monitor_button = ttk.Button(monitor_frame, text="Monitoring starten", 
                                        command=self.toggle_monitoring, width=15)
        self.monitor_button.grid(row=0, column=0, pady=2)
        
        ttk.Button(monitor_frame, text="Konnektivität testen", 
                  command=self.test_connectivity, width=15).grid(row=1, column=0, pady=2)
        
        ttk.Button(monitor_frame, text="VPS Web-Interface", 
                  command=self.open_vps_interface, width=15).grid(row=2, column=0, pady=2)
    
    def create_info_tabs(self, parent, row):
        """Informations-Tabs erstellen"""
        notebook = ttk.Notebook(parent)
        notebook.grid(row=row, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Interface-Statistiken Tab
        stats_frame = ttk.Frame(notebook, padding="10")
        notebook.add(stats_frame, text="Interface-Statistiken")
        
        self.stats_tree = ttk.Treeview(stats_frame, columns=("Interface", "Status", "RX", "TX"), show="headings")
        self.stats_tree.heading("Interface", text="Interface")
        self.stats_tree.heading("Status", text="Status")
        self.stats_tree.heading("RX", text="Empfangen (MB)")
        self.stats_tree.heading("TX", text="Gesendet (MB)")
        self.stats_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        stats_frame.grid_rowconfigure(0, weight=1)
        stats_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbar für Statistiken
        stats_scrollbar = ttk.Scrollbar(stats_frame, orient=tk.VERTICAL, command=self.stats_tree.yview)
        stats_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.stats_tree.configure(yscrollcommand=stats_scrollbar.set)
        
        # Tunnel-Details Tab
        details_frame = ttk.Frame(notebook, padding="10")
        notebook.add(details_frame, text="Tunnel-Details")
        
        self.details_text = tk.Text(details_frame, wrap=tk.WORD, font=("Courier", 9))
        self.details_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        details_frame.grid_rowconfigure(0, weight=1)
        details_frame.grid_columnconfigure(0, weight=1)
        
        # Scrollbar für Details
        details_scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=self.details_text.yview)
        details_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.details_text.configure(yscrollcommand=details_scrollbar.set)
        
        # Netzwerk-Konfiguration Tab
        network_frame = ttk.Frame(notebook, padding="10")
        notebook.add(network_frame, text="Netzwerk-Konfiguration")
        
        # Netzwerk-Info Labels
        network_info = [
            ("Port A (Heimnetz):", "eth0 - 192.168.1.254/24"),
            ("Port B (Server):", "eth1 - 10.0.0.1/24"),
            ("WireGuard Tunnel:", "wg0 - 10.8.0.2/24"),
            ("VPS Endpoint:", "10.8.0.1:51820"),
        ]
        
        for i, (label, value) in enumerate(network_info):
            ttk.Label(network_frame, text=label, font=("Arial", 10, "bold")).grid(row=i, column=0, sticky=tk.W, pady=2)
            ttk.Label(network_frame, text=value).grid(row=i, column=1, sticky=tk.W, padx=(20, 0), pady=2)
    
    def start_status_updates(self):
        """Automatische Status-Updates starten"""
        def update_loop():
            while True:
                try:
                    self.update_status()
                    time.sleep(5)  # Alle 5 Sekunden aktualisieren
                except Exception as e:
                    print(f"Status-Update Fehler: {e}")
                    time.sleep(10)
        
        update_thread = threading.Thread(target=update_loop, daemon=True)
        update_thread.start()
    
    def update_status(self):
        """Status-Informationen aktualisieren"""
        try:
            # Tunnel-Status
            status = self.gateway.get_tunnel_status()
            status_text = status['status'].upper()
            
            if status['status'] == 'connected':
                self.status_var.set(f"🟢 {status_text}")
                self.status_label.configure(foreground="green")
            else:
                self.status_var.set(f"🔴 {status_text}")
                self.status_label.configure(foreground="red")
            
            # Interface-Statistiken
            stats = self.gateway.get_interface_stats()
            self.update_stats_tree(stats)
            
            # Tunnel-Details
            self.update_details_text(status)
            
        except Exception as e:
            print(f"Fehler beim Status-Update: {e}")
    
    def update_stats_tree(self, stats):
        """Interface-Statistiken-Tabelle aktualisieren"""
        # Tabelle leeren
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        
        # Neue Daten einfügen
        for interface, data in stats.items():
            if 'rx_mb' in data and 'tx_mb' in data:
                self.stats_tree.insert("", "end", values=(
                    interface,
                    "Aktiv",
                    f"{data['rx_mb']} MB",
                    f"{data['tx_mb']} MB"
                ))
            else:
                self.stats_tree.insert("", "end", values=(
                    interface,
                    "Nicht verfügbar",
                    "--",
                    "--"
                ))
    
    def update_details_text(self, status):
        """Tunnel-Details-Text aktualisieren"""
        self.details_text.delete(1.0, tk.END)
        
        details = f"""WireGuard Tunnel Status
====================

Status: {status['status']}
Zeitstempel: {status['timestamp']}

WireGuard Output:
{status['output'] if status['output'] else 'Keine Ausgabe verfügbar'}

Gateway-Konfiguration:
- VPS Endpoint: {self.gateway.vps_endpoint or 'Nicht konfiguriert'}
- Interface: {self.gateway.interface}
- Config-Datei: {self.gateway.config_file}
"""
        
        self.details_text.insert(1.0, details)
    
    def start_tunnel(self):
        """Tunnel starten"""
        try:
            if self.gateway.start_tunnel():
                messagebox.showinfo("Erfolg", "Tunnel erfolgreich gestartet")
            else:
                messagebox.showerror("Fehler", "Fehler beim Starten des Tunnels")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Starten: {e}")
    
    def stop_tunnel(self):
        """Tunnel stoppen"""
        try:
            if self.gateway.stop_tunnel():
                messagebox.showinfo("Erfolg", "Tunnel erfolgreich gestoppt")
            else:
                messagebox.showerror("Fehler", "Fehler beim Stoppen des Tunnels")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Stoppen: {e}")
    
    def restart_tunnel(self):
        """Tunnel neustarten"""
        try:
            self.gateway.stop_tunnel()
            time.sleep(2)
            if self.gateway.start_tunnel():
                messagebox.showinfo("Erfolg", "Tunnel erfolgreich neugestartet")
            else:
                messagebox.showerror("Fehler", "Fehler beim Neustarten des Tunnels")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Neustarten: {e}")
    
    def configure_gateway(self):
        """Gateway-Konfiguration Dialog"""
        dialog = ConfigDialog(self.root, self.gateway)
        self.root.wait_window(dialog.dialog)
    
    def show_config(self):
        """Aktuelle Konfiguration anzeigen"""
        try:
            config_info = f"""Gateway-Konfiguration:

VPS Endpoint: {self.gateway.vps_endpoint or 'Nicht konfiguriert'}
VPS Public Key: {self.gateway.vps_public_key or 'Nicht konfiguriert'}
Gateway Public Key: {self.gateway.gateway_public_key or 'Nicht generiert'}

Konfigurationsdatei: {self.gateway.config_file}
Interface: {self.gateway.interface}
"""
            messagebox.showinfo("Gateway-Konfiguration", config_info)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Laden der Konfiguration: {e}")
    
    def show_logs(self):
        """Logs anzeigen"""
        LogDialog(self.root)
    
    def toggle_monitoring(self):
        """Monitoring ein-/ausschalten"""
        if not self.monitor.running:
            self.monitor.start_monitoring()
            self.monitor_button.configure(text="Monitoring stoppen")
            messagebox.showinfo("Monitoring", "Monitoring gestartet")
        else:
            self.monitor.stop_monitoring()
            self.monitor_button.configure(text="Monitoring starten")
            messagebox.showinfo("Monitoring", "Monitoring gestoppt")
    
    def test_connectivity(self):
        """Konnektivität zum VPS testen"""
        try:
            result = self.gateway.test_connectivity()
            if result['success']:
                latency = f" (Latenz: {result['latency']}ms)" if result['latency'] else ""
                messagebox.showinfo("Konnektivitätstest", f"✅ Verbindung zum VPS erfolgreich{latency}")
            else:
                messagebox.showerror("Konnektivitätstest", f"❌ Verbindung fehlgeschlagen:\n{result['output']}")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Konnektivitätstest: {e}")
    
    def open_vps_interface(self):
        """VPS Web-Interface im Browser öffnen"""
        try:
            if self.gateway.vps_endpoint:
                vps_ip = self.gateway.vps_endpoint.split(':')[0]
                url = f"http://{vps_ip}:8080"
                import webbrowser
                webbrowser.open(url)
            else:
                messagebox.showwarning("Warnung", "VPS-Endpoint nicht konfiguriert")
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Öffnen des Web-Interface: {e}")

class ConfigDialog:
    def __init__(self, parent, gateway):
        self.gateway = gateway
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Gateway konfigurieren")
        self.dialog.geometry("500x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_dialog()
    
    def setup_dialog(self):
        """Konfigurations-Dialog erstellen"""
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # VPS IP
        ttk.Label(main_frame, text="VPS IP-Adresse:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.vps_ip_entry = ttk.Entry(main_frame, width=40)
        self.vps_ip_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # VPS Public Key
        ttk.Label(main_frame, text="VPS Public Key:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.vps_key_entry = ttk.Entry(main_frame, width=40)
        self.vps_key_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Konfigurieren", 
                  command=self.configure).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Abbrechen", 
                  command=self.dialog.destroy).grid(row=0, column=1, padx=5)
        
        # Grid-Gewichtung
        main_frame.grid_columnconfigure(1, weight=1)
    
    def configure(self):
        """Gateway konfigurieren"""
        vps_ip = self.vps_ip_entry.get().strip()
        vps_key = self.vps_key_entry.get().strip()
        
        if not vps_ip or not vps_key:
            messagebox.showerror("Fehler", "Bitte alle Felder ausfüllen")
            return
        
        try:
            if self.gateway.setup_initial_config(vps_ip, vps_key):
                messagebox.showinfo("Erfolg", 
                    f"Gateway erfolgreich konfiguriert!\n\n"
                    f"Gateway Public Key:\n{self.gateway.gateway_public_key}\n\n"
                    f"Bitte diesen Key auf dem VPS in die wg0.conf eintragen.")
                self.dialog.destroy()
            else:
                messagebox.showerror("Fehler", "Fehler bei der Konfiguration")
        except Exception as e:
            messagebox.showerror("Fehler", f"Konfigurationsfehler: {e}")

class LogDialog:
    def __init__(self, parent):
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("System-Logs")
        self.dialog.geometry("800x600")
        self.dialog.transient(parent)
        
        self.setup_dialog()
        self.load_logs()
    
    def setup_dialog(self):
        """Log-Dialog erstellen"""
        main_frame = ttk.Frame(self.dialog, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Text-Widget für Logs
        self.log_text = tk.Text(main_frame, wrap=tk.WORD, font=("Courier", 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Aktualisieren", command=self.load_logs).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="Schließen", command=self.dialog.destroy).grid(row=0, column=1, padx=5)
        
        # Grid-Gewichtung
        self.dialog.grid_rowconfigure(0, weight=1)
        self.dialog.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
    
    def load_logs(self):
        """System-Logs laden"""
        self.log_text.delete(1.0, tk.END)
        
        log_sources = [
            ("WireGuard Service", "journalctl -u wg-quick@gateway --no-pager -n 50"),
            ("Gateway Monitor", "tail -50 /var/log/wireguard-gateway/monitor.log"),
            ("System Logs", "journalctl --no-pager -n 30")
        ]
        
        for title, command in log_sources:
            self.log_text.insert(tk.END, f"\n=== {title} ===\n")
            try:
                import subprocess
                result = subprocess.run(command.split(), capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    self.log_text.insert(tk.END, result.stdout)
                else:
                    self.log_text.insert(tk.END, f"Fehler: {result.stderr}")
            except Exception as e:
                self.log_text.insert(tk.END, f"Fehler beim Laden: {e}")
            self.log_text.insert(tk.END, "\n" + "="*50 + "\n")

def main():
    root = tk.Tk()
    app = GatewayGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()