import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
import os
import datetime
import threading
import queue
import time
import sys

# Füge den Root-Ordner des Projekts zum Python-Pfad hinzu,
# damit PluginLoader und plugin_interfaces gefunden werden können
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from plugin_loader import PluginLoader
from plugin_interfaces import BasePlugin, BackupSourcePlugin, BackupDestinationPlugin, \
                              EncryptionPlugin, PrePostScriptPlugin, RestorePlugin

CONFIG_FILE = "backup_tool_config.json"
PLUGINS_ROOT = os.path.join(current_dir, "plugins") # Angenommener Plugin-Ordner

class BackupToolGUI:
    def __init__(self, master):
        self.master = master
        master.title("Backup Tool")
        master.geometry("1000x800")

        self.plugin_loader = PluginLoader(PLUGINS_ROOT) 
        self.plugin_configs = self._load_config()

        self.selected_source_plugin = None
        self.selected_destination_plugin = None
        self.selected_encryption_plugin = None
        self.selected_pre_post_script_plugin = None
        self.selected_restore_plugin = None

        self.source_plugin_tk_vars = {}
        self.destination_plugin_tk_vars = {}
        self.encryption_plugin_tk_vars = {}
        self.pre_post_script_plugin_tk_vars = {}
        self.restore_plugin_tk_vars = {}

        self._create_widgets()
        self._load_plugins()
        self._update_plugin_comboboxes()
        
        self._create_plugin_configuration_widgets() 
        self._load_current_plugin_selections_and_configs()

        self._log_message("Ready to create a new job.", level="INFO")

    def _log_message(self, message, level="INFO"):
        """Fügt eine Nachricht dem Anwendungslog hinzu."""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level.upper()}] {message}\n"
        
        if hasattr(self, 'log_text') and self.log_text:
            self.log_text.config(state='normal')
            self.log_text.insert(tk.END, log_entry)
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        else:
            print(f"[PRE-GUI-LOG] {log_entry.strip()}") 
        
        print(log_entry.strip())

    def _load_config(self):
        """Lädt die Konfiguration aus der JSON-Datei."""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                try:
                    return json.load(f)
                except json.JSONDecodeError as e:
                    self._log_message(f"Fehler beim Laden der Konfigurationsdatei: {e}. Erstelle leere Konfiguration.", level="ERROR")
                    return {}
        return {}

    def _save_config(self):
        """Speichert die aktuelle Konfiguration in die JSON-Datei."""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.plugin_configs, f, indent=4)
            self._log_message("Konfiguration erfolgreich gespeichert.", level="INFO")
        except Exception as e:
            self._log_message(f"Fehler beim Speichern der Konfiguration: {e}", level="ERROR")

    def _load_plugins(self):
        """Lädt alle Plugins über den PluginLoader und übergibt das Log-Callback."""
        self.source_plugins = self.plugin_loader.load_plugins(BackupSourcePlugin, self._log_message)
        self._log_message(f"Loaded {len(self.source_plugins)} source plugins.", level="INFO")

        self.destination_plugins = self.plugin_loader.load_plugins(BackupDestinationPlugin, self._log_message)
        self._log_message(f"Loaded {len(self.destination_plugins)} destination plugins.", level="INFO")

        self.encryption_plugins = self.plugin_loader.load_plugins(EncryptionPlugin, self._log_message)
        self._log_message(f"Loaded {len(self.encryption_plugins)} encryption plugins.", level="INFO")

        self.pre_post_script_plugins = self.plugin_loader.load_plugins(PrePostScriptPlugin, self._log_message)
        self._log_message(f"Loaded {len(self.pre_post_script_plugins)} pre/post script plugins.", level="INFO")

        self.restore_plugins = self.plugin_loader.load_plugins(RestorePlugin, self._log_message)
        self._log_message(f"Loaded {len(self.restore_plugins)} restore plugins.", level="INFO")

    def _create_widgets(self):
        """Erstellt die Haupt-GUI-Elemente."""
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(pady=10, expand=True, fill="both")

        self.jobs_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.jobs_frame, text="Jobs")
        ttk.Label(self.jobs_frame, text="Hier kommen die Job-Verwaltungselemente hin.").pack(pady=20)

        self.config_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.config_frame, text="Konfiguration")
        self._create_config_tab(self.config_frame)

        self.scheduling_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.scheduling_frame, text="Planung")
        ttk.Label(self.scheduling_frame, text="Hier kommen die Planungselemente hin.").pack(pady=20)

        self.plugins_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.plugins_tab_frame, text="Plugins")
        self._create_plugins_tab(self.plugins_tab_frame)

        self.restore_tab_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.restore_tab_frame, text="Wiederherstellung")
        self._create_restore_tab(self.restore_tab_frame)


        # Anwendungslog
        log_frame = ttk.LabelFrame(self.master, text="Application Log")
        log_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, height=10, font=("Cascadia Code", 10))
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.log_text.config(state='disabled')

        # Start Backup Button
        self.start_backup_button = ttk.Button(self.master, text="Start Backup", command=self._start_backup_process)
        self.start_backup_button.pack(pady=10)

        self.master.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _on_closing(self):
        """Wird aufgerufen, wenn das Fenster geschlossen wird."""
        self._save_current_configs()
        self._save_config()
        self.master.destroy()

    def _create_config_tab(self, parent_frame):
        """Erstellt die Elemente für den Konfigurations-Tab."""
        backup_config_frame = ttk.LabelFrame(parent_frame, text="Backup Konfiguration")
        backup_config_frame.pack(pady=10, padx=10, fill="x")

        source_plugin_frame = ttk.Frame(backup_config_frame)
        source_plugin_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(source_plugin_frame, text="Wähle Quell-Plugin:").pack(side="left", padx=5)
        self.source_plugin_combo = ttk.Combobox(source_plugin_frame, state="readonly", width=40)
        self.source_plugin_combo['values'] = []
        self.source_plugin_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.source_plugin_combo.bind("<<ComboboxSelected>>", self._on_source_plugin_selected)

        self.source_plugin_config_frame = ttk.LabelFrame(backup_config_frame, text="Quell-Plugin Konfiguration")
        self.source_plugin_config_frame.pack(pady=10, padx=10, fill="both", expand=True)

        destination_plugin_frame = ttk.Frame(backup_config_frame)
        destination_plugin_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(destination_plugin_frame, text="Wähle Ziel-Plugin:").pack(side="left", padx=5)
        self.destination_plugin_combo = ttk.Combobox(destination_plugin_frame, state="readonly", width=40)
        self.destination_plugin_combo['values'] = []
        self.destination_plugin_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.destination_plugin_combo.bind("<<ComboboxSelected>>", self._on_destination_plugin_selected)

        self.destination_plugin_config_frame = ttk.LabelFrame(backup_config_frame, text="Ziel-Plugin Konfiguration")
        self.destination_plugin_config_frame.pack(pady=10, padx=10, fill="both", expand=True)

        encryption_plugin_frame = ttk.Frame(backup_config_frame)
        encryption_plugin_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(encryption_plugin_frame, text="Wähle Verschlüsselungs-Plugin:").pack(side="left", padx=5)
        self.encryption_plugin_combo = ttk.Combobox(encryption_plugin_frame, state="readonly", width=40)
        self.encryption_plugin_combo['values'] = ["(Keine)"]
        self.encryption_plugin_combo.set("(Keine)")
        self.encryption_plugin_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.encryption_plugin_combo.bind("<<ComboboxSelected>>", self._on_encryption_plugin_selected)

        self.encryption_plugin_config_frame = ttk.LabelFrame(backup_config_frame, text="Verschlüsselungs-Plugin Konfiguration")
        self.encryption_plugin_config_frame.pack(pady=10, padx=10, fill="both", expand=True)

        pre_post_script_plugin_frame = ttk.Frame(backup_config_frame)
        pre_post_script_plugin_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(pre_post_script_plugin_frame, text="Wähle Pre/Post Script Plugin:").pack(side="left", padx=5)
        self.pre_post_script_plugin_combo = ttk.Combobox(pre_post_script_plugin_frame, state="readonly", width=40)
        self.pre_post_script_plugin_combo['values'] = ["(Keine)"]
        self.pre_post_script_plugin_combo.set("(Keine)")
        self.pre_post_script_plugin_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.pre_post_script_plugin_combo.bind("<<ComboboxSelected>>", self._on_pre_post_script_plugin_selected)

        self.pre_post_script_plugin_config_frame = ttk.LabelFrame(backup_config_frame, text="Pre/Post Script Plugin Konfiguration")
        self.pre_post_script_plugin_config_frame.pack(pady=10, padx=10, fill="both", expand=True)

    def _create_plugins_tab(self, parent_frame):
        """Erstellt die Elemente für den Plugins-Tab."""
        ttk.Label(parent_frame, text="Übersicht und Details zu den geladenen Plugins.").pack(pady=20)

    def _create_restore_tab(self, parent_frame):
        """Erstellt die Elemente für den Wiederherstellungs-Tab."""
        restore_config_frame = ttk.LabelFrame(parent_frame, text="Wiederherstellungs-Konfiguration")
        restore_config_frame.pack(pady=10, padx=10, fill="x")

        restore_plugin_frame = ttk.Frame(restore_config_frame)
        restore_plugin_frame.pack(fill="x", padx=5, pady=5)
        ttk.Label(restore_plugin_frame, text="Wähle Wiederherstellungs-Plugin:").pack(side="left", padx=5)
        self.restore_plugin_combo = ttk.Combobox(restore_plugin_frame, state="readonly", width=40)
        self.restore_plugin_combo['values'] = []
        self.restore_plugin_combo.pack(side="left", fill="x", expand=True, padx=5)
        self.restore_plugin_combo.bind("<<ComboboxSelected>>", self._on_restore_plugin_selected)

        self.restore_plugin_config_frame = ttk.LabelFrame(restore_config_frame, text="Wiederherstellungs-Plugin Konfiguration")
        self.restore_plugin_config_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.start_restore_button = ttk.Button(parent_frame, text="Start Wiederherstellung", command=self._start_restore_process)
        self.start_restore_button.pack(pady=10)

    def _update_plugin_comboboxes(self):
        """Aktualisiert die Werte der Comboboxen nach dem Laden der Plugins."""
        self.source_plugin_combo['values'] = [p.get_name() for p in self.source_plugins]
        self.destination_plugin_combo['values'] = [p.get_name() for p in self.destination_plugins]
        
        self.encryption_plugin_combo['values'] = ["(Keine)"] + [p.get_name() for p in self.encryption_plugins]
        self.pre_post_script_plugin_combo['values'] = ["(Keine)"] + [p.get_name() for p in self.pre_post_script_plugins]
        self.restore_plugin_combo['values'] = [p.get_name() for p in self.restore_plugins]

    def _clear_frame(self, frame):
        """Löscht alle Widgets aus einem Frame."""
        for widget in frame.winfo_children():
            widget.destroy()

    def _create_plugin_configuration_widgets(self):
        pass

    def _load_current_plugin_selections_and_configs(self):
        """Lädt die zuletzt ausgewählten Plugins und ihre Konfigurationen."""
        saved_source_plugin_name = self.plugin_configs.get("selected_source_plugin")
        if saved_source_plugin_name and saved_source_plugin_name in self.source_plugin_combo['values']:
            self.source_plugin_combo.set(saved_source_plugin_name)
            self._on_source_plugin_selected(None)
        elif self.source_plugin_combo['values']:
            self.source_plugin_combo.set(self.source_plugin_combo['values'][0])
            self._on_source_plugin_selected(None)
        else:
            self._log_message("Kein Quell-Plugin geladen oder verfügbar.", level="WARNING")

        saved_destination_plugin_name = self.plugin_configs.get("selected_destination_plugin")
        if saved_destination_plugin_name and saved_destination_plugin_name in self.destination_plugin_combo['values']:
            self.destination_plugin_combo.set(saved_destination_plugin_name)
            self._on_destination_plugin_selected(None)
        elif self.destination_plugin_combo['values']:
            self.destination_plugin_combo.set(self.destination_plugin_combo['values'][0])
            self._on_destination_plugin_selected(None)
        else:
            self._log_message("Kein Ziel-Plugin geladen oder verfügbar.", level="WARNING")

        saved_encryption_plugin_name = self.plugin_configs.get("selected_encryption_plugin")
        if saved_encryption_plugin_name and saved_encryption_plugin_name in self.encryption_plugin_combo['values']:
            self.encryption_plugin_combo.set(saved_encryption_plugin_name)
            self._on_encryption_plugin_selected(None)
        else:
            self.encryption_plugin_combo.set("(Keine)")
            self._on_encryption_plugin_selected(None)

        saved_pre_post_script_plugin_name = self.plugin_configs.get("selected_pre_post_script_plugin")
        if saved_pre_post_script_plugin_name and saved_pre_post_script_plugin_name in self.pre_post_script_plugin_combo['values']:
            self.pre_post_script_plugin_combo.set(saved_pre_post_script_plugin_name)
            self._on_pre_post_script_plugin_selected(None)
        else:
            self.pre_post_script_plugin_combo.set("(Keine)")
            self._on_pre_post_script_plugin_selected(None)

        saved_restore_plugin_name = self.plugin_configs.get("selected_restore_plugin")
        if saved_restore_plugin_name and saved_restore_plugin_name in self.restore_plugin_combo['values']:
            self.restore_plugin_combo.set(saved_restore_plugin_name)
            self._on_restore_plugin_selected(None)
        elif self.restore_plugin_combo['values']:
            self.restore_plugin_combo.set(self.restore_plugin_combo['values'][0])
            self._on_restore_plugin_selected(None)
        else:
            self._log_message("Kein Wiederherstellungs-Plugin geladen oder verfügbar.", level="WARNING")

    def _on_source_plugin_selected(self, event):
        """Wird aufgerufen, wenn ein Quell-Plugin ausgewählt wird."""
        plugin_name = self.source_plugin_combo.get()
        self._clear_frame(self.source_plugin_config_frame)
        self.source_plugin_tk_vars.clear()

        if plugin_name:
            self.selected_source_plugin = next((p for p in self.source_plugins if p.get_name() == plugin_name), None)
            if self.selected_source_plugin:
                self._log_message(f"Quell-Plugin '{plugin_name}' ausgewählt.", level="INFO")
                config_for_plugin = self.plugin_configs.get("plugin_data", {}).get(plugin_name, {})
                self.selected_source_plugin.set_config(config_for_plugin)

                self.selected_source_plugin.get_ui_elements(self.source_plugin_config_frame, self.source_plugin_tk_vars)
            else:
                self._log_message(f"Fehler: Quell-Plugin '{plugin_name}' konnte nicht gefunden werden.", level="ERROR")
                self.selected_source_plugin = None

    def _on_destination_plugin_selected(self, event):
        """Wird aufgerufen, wenn ein Ziel-Plugin ausgewählt wird."""
        plugin_name = self.destination_plugin_combo.get()
        self._clear_frame(self.destination_plugin_config_frame)
        self.destination_plugin_tk_vars.clear()

        if plugin_name:
            self.selected_destination_plugin = next((p for p in self.destination_plugins if p.get_name() == plugin_name), None)
            if self.selected_destination_plugin:
                self._log_message(f"Ziel-Plugin '{plugin_name}' ausgewählt.", level="INFO")
                config_for_plugin = self.plugin_configs.get("plugin_data", {}).get(plugin_name, {})
                self.selected_destination_plugin.set_config(config_for_plugin)
                
                self.selected_destination_plugin.get_ui_elements(self.destination_plugin_config_frame, self.destination_plugin_tk_vars)
            else:
                self._log_message(f"Fehler: Ziel-Plugin '{plugin_name}' konnte nicht gefunden werden.", level="ERROR")
                self.selected_destination_plugin = None

    def _on_encryption_plugin_selected(self, event):
        """Wird aufgerufen, wenn ein Verschlüsselungs-Plugin ausgewählt wird."""
        plugin_name = self.encryption_plugin_combo.get()
        self._clear_frame(self.encryption_plugin_config_frame)
        self.encryption_plugin_tk_vars.clear()

        if plugin_name == "(Keine)":
            self._log_message("Keine Verschlüsselung ausgewählt.", level="INFO")
            self.selected_encryption_plugin = None
            return

        if plugin_name:
            self.selected_encryption_plugin = next((p for p in self.encryption_plugins if p.get_name() == plugin_name), None)
            if self.selected_encryption_plugin:
                self._log_message(f"Verschlüsselungs-Plugin '{plugin_name}' ausgewählt.", level="INFO")
                config_for_plugin = self.plugin_configs.get("plugin_data", {}).get(plugin_name, {})
                self.selected_encryption_plugin.set_config(config_for_plugin)
                
                self.selected_encryption_plugin.get_ui_elements(self.encryption_plugin_config_frame, self.encryption_plugin_tk_vars)
            else:
                self._log_message(f"Fehler: Verschlüsselungs-Plugin '{plugin_name}' konnte nicht gefunden werden.", level="ERROR")
                self.selected_encryption_plugin = None

    def _on_pre_post_script_plugin_selected(self, event):
        """Wird aufgerufen, wenn ein Pre/Post Script Plugin ausgewählt wird."""
        plugin_name = self.pre_post_script_plugin_combo.get()
        self._clear_frame(self.pre_post_script_plugin_config_frame)
        self.pre_post_script_plugin_tk_vars.clear()

        if plugin_name == "(Keine)":
            self._log_message("Kein Pre/Post Script ausgewählt.", level="INFO")
            self.selected_pre_post_script_plugin = None
            return

        if plugin_name:
            self.selected_pre_post_script_plugin = next((p for p in self.pre_post_script_plugins if p.get_name() == plugin_name), None)
            if self.selected_pre_post_script_plugin:
                self._log_message(f"Pre/Post Script Plugin '{plugin_name}' ausgewählt.", level="INFO")
                config_for_plugin = self.plugin_configs.get("plugin_data", {}).get(plugin_name, {})
                self.selected_pre_post_script_plugin.set_config(config_for_plugin)
                
                self.selected_pre_post_script_plugin.get_ui_elements(self.pre_post_script_plugin_config_frame, self.pre_post_script_plugin_tk_vars)
            else:
                self._log_message(f"Fehler: Pre/Post Script Plugin '{plugin_name}' konnte nicht gefunden werden.", level="ERROR")
                self.selected_pre_post_script_plugin = None

    def _on_restore_plugin_selected(self, event):
        """Wird aufgerufen, wenn ein Wiederherstellungs-Plugin ausgewählt wird."""
        plugin_name = self.restore_plugin_combo.get()
        self._clear_frame(self.restore_plugin_config_frame)
        self.restore_plugin_tk_vars.clear()

        if plugin_name:
            self.selected_restore_plugin = next((p for p in self.restore_plugins if p.get_name() == plugin_name), None) 
            if self.selected_restore_plugin:
                self._log_message(f"Wiederherstellungs-Plugin '{plugin_name}' ausgewählt.", level="INFO")
                config_for_plugin = self.plugin_configs.get("plugin_data", {}).get(plugin_name, {})
                self.selected_restore_plugin.set_config(config_for_plugin)

                self.selected_restore_plugin.get_ui_elements(self.restore_plugin_config_frame, self.restore_plugin_tk_vars)
            else:
                self._log_message(f"Fehler: Wiederherstellungs-Plugin '{plugin_name}' konnte nicht gefunden werden.", level="ERROR")
                self.selected_restore_plugin = None

    def _save_current_configs(self):
        """
        Speichert die aktuellen Konfigurationen der ausgewählten Plugins
        von den Tkinter-Variablen in self.plugin_configs.
        """
        self.plugin_configs["plugin_data"] = self.plugin_configs.get("plugin_data", {})

        # Source Plugin
        if self.selected_source_plugin:
            self.plugin_configs["selected_source_plugin"] = self.selected_source_plugin.get_name()
            current_config = {}
            for k, v in self.source_plugin_tk_vars.items():
                if isinstance(v, tk.Text):
                    paths = [line.strip() for line in v.get("1.0", tk.END).splitlines() if line.strip()]
                    current_config[k] = paths
                elif isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar)):
                    current_config[k] = v.get()
                else:
                    self._log_message(f"Unbekannter Variablentyp im Quell-Plugin tk_vars: {type(v)}. Konnte Wert für {k} nicht auslesen.", level="WARNING")
                    current_config[k] = None
            self.selected_source_plugin.set_config(current_config)
            self.plugin_configs["plugin_data"][self.selected_source_plugin.get_name()] = current_config
            self._log_message(f"Quell-Plugin-Konfiguration für '{self.selected_source_plugin.get_name()}' gespeichert.", level="DEBUG")
        else:
            self.plugin_configs["selected_source_plugin"] = None


        # Destination Plugin
        if self.selected_destination_plugin:
            self.plugin_configs["selected_destination_plugin"] = self.selected_destination_plugin.get_name()
            current_config = {k: v.get() for k, v in self.destination_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
            self.selected_destination_plugin.set_config(current_config)
            self.plugin_configs["plugin_data"][self.selected_destination_plugin.get_name()] = current_config
            self._log_message(f"Ziel-Plugin-Konfiguration für '{self.selected_destination_plugin.get_name()}' gespeichert.", level="DEBUG")
        else:
            self.plugin_configs["selected_destination_plugin"] = None

        # Encryption Plugin
        if self.selected_encryption_plugin:
            self.plugin_configs["selected_encryption_plugin"] = self.selected_encryption_plugin.get_name()
            current_config = {k: v.get() for k, v in self.encryption_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
            self.selected_encryption_plugin.set_config(current_config)
            self.plugin_configs["plugin_data"][self.selected_encryption_plugin.get_name()] = current_config
            self._log_message(f"Verschlüsselungs-Plugin-Konfiguration für '{self.selected_encryption_plugin.get_name()}' gespeichert.", level="DEBUG")
        else:
            self.plugin_configs["selected_encryption_plugin"] = "(Keine)"
            for key in list(self.plugin_configs["plugin_data"].keys()):
                if key not in [p.get_name() for p in self.encryption_plugins]:
                    if key != "(Keine)":
                        del self.plugin_configs["plugin_data"][key]
            self._log_message("Kein Verschlüsselungs-Plugin ausgewählt, Konfiguration ggf. entfernt.", level="DEBUG")


        # Pre/Post Script Plugin
        if self.selected_pre_post_script_plugin:
            self.plugin_configs["selected_pre_post_script_plugin"] = self.selected_pre_post_script_plugin.get_name()
            current_config = {k: v.get() for k, v in self.pre_post_script_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
            self.selected_pre_post_script_plugin.set_config(current_config)
            self.plugin_configs["plugin_data"][self.selected_pre_post_script_plugin.get_name()] = current_config
            self._log_message(f"Pre/Post Script Plugin-Konfiguration für '{self.selected_pre_post_script_plugin.get_name()}' gespeichert.", level="DEBUG")
        else:
            self.plugin_configs["selected_pre_post_script_plugin"] = "(Keine)"
            for key in list(self.plugin_configs["plugin_data"].keys()):
                if key not in [p.get_name() for p in self.pre_post_script_plugins]:
                    if key != "(Keine)":
                        del self.plugin_configs["plugin_data"][key]
            self._log_message("Kein Pre/Post Script Plugin ausgewählt, Konfiguration ggf. entfernt.", level="DEBUG")


        # Restore Plugin
        if self.selected_restore_plugin:
            self.plugin_configs["selected_restore_plugin"] = self.selected_restore_plugin.get_name()
            current_config = {k: v.get() for k, v in self.restore_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
            self.selected_restore_plugin.set_config(current_config)
            self.plugin_configs["plugin_data"][self.selected_restore_plugin.get_name()] = current_config
            self._log_message(f"Wiederherstellungs-Plugin-Konfiguration für '{self.selected_restore_plugin.get_name()}' gespeichert.", level="DEBUG")
        else:
            self.plugin_configs["selected_restore_plugin"] = None


    def _start_backup_process(self):
        """Startet den Backup-Prozess in einem separaten Thread."""
        self._save_current_configs()

        if not self.selected_source_plugin:
            messagebox.showerror("Backup Fehler", "Bitte wählen Sie ein Quell-Plugin aus.")
            return
        if not self.selected_destination_plugin:
            messagebox.showerror("Backup Fehler", "Bitte wählen Sie ein Ziel-Plugin aus.")
            return

        # Aktualisiere Plugin-Konfigurationen direkt vor dem Start, falls nicht durch Selection geändert
        # WICHTIG: Dies ist redundant, wenn _save_current_configs() direkt davor aufgerufen wird,
        # kann aber als Fallback dienen, falls die Konfigurationslogik komplexer wird.
        # Für tk.Text muss hier die gleiche Logik wie in _save_current_configs angewendet werden.
        source_plugin_config = {}
        for k, v in self.source_plugin_tk_vars.items():
            if isinstance(v, tk.Text):
                paths = [line.strip() for line in v.get("1.0", tk.END).splitlines() if line.strip()]
                source_plugin_config[k] = paths
            elif isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar)):
                source_plugin_config[k] = v.get()
            else:
                self._log_message(f"Unbekannter Variablentyp im Quell-Plugin tk_vars bei Backup-Start: {type(v)}. Konnte Wert für {k} nicht auslesen.", level="WARNING")
                source_plugin_config[k] = None
        self.selected_source_plugin.set_config(source_plugin_config)

        destination_plugin_config = {k: v.get() for k, v in self.destination_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        self.selected_destination_plugin.set_config(destination_plugin_config)

        encryption_plugin_config = {k: v.get() for k, v in self.encryption_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        if self.selected_encryption_plugin:
            self.selected_encryption_plugin.set_config(encryption_plugin_config)

        pre_post_script_plugin_config = {k: v.get() for k, v in self.pre_post_script_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        if self.selected_pre_post_script_plugin:
            self.selected_pre_post_script_plugin.set_config(pre_post_script_plugin_config)


        is_valid, msg = self.selected_source_plugin.validate_config()
        if not is_valid:
            messagebox.showerror("Backup Fehler: Quell-Plugin", msg)
            return
        is_valid, msg = self.selected_destination_plugin.validate_config()
        if not is_valid:
            messagebox.showerror("Backup Fehler: Ziel-Plugin", msg)
            return
        if self.selected_encryption_plugin:
            is_valid, msg = self.selected_encryption_plugin.validate_config()
            if not is_valid:
                messagebox.showerror("Backup Fehler: Verschlüsselungs-Plugin", msg)
                return
        if self.selected_pre_post_script_plugin:
            is_valid, msg = self.selected_pre_post_script_plugin.validate_config()
            if not is_valid:
                messagebox.showerror("Backup Fehler: Pre/Post Script Plugin", msg)
                return

        self._log_message("Starte Backup-Prozess...", level="INFO")
        self.start_backup_button.config(state=tk.DISABLED)

        self.backup_queue = queue.Queue()

        backup_thread = threading.Thread(target=self._run_backup_in_thread, daemon=True)
        backup_thread.start()

        self.master.after(100, self._check_backup_queue)


    def _run_backup_in_thread(self):
        """Die eigentliche Backup-Logik, die in einem separaten Thread läuft."""
        try:
            self._log_to_queue("Pre-Backup Skripte ausführen...", level="INFO")
            if self.selected_pre_post_script_plugin:
                if not self.selected_pre_post_script_plugin.run_pre_backup_script():
                    self._log_to_queue("Pre-Backup Skript fehlgeschlagen. Backup abgebrochen.", level="ERROR")
                    self.backup_queue.put("finished")
                    return
                self._log_to_queue("Pre-Backup Skript erfolgreich.", level="INFO")

            # Hier wird get_source_paths() des aktuell ausgewählten Source-Plugins aufgerufen
            source_paths = self.selected_source_plugin.get_source_paths()
            if not source_paths:
                self._log_to_queue("Keine Quellpfade zum Sichern konfiguriert.", level="ERROR")
                self.backup_queue.put("finished")
                return

            self._log_to_queue(f"Sichere {len(source_paths)} Pfade...", level="INFO")
            backup_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Dummy-Implementierung: Simuliert das Hochladen einiger Dateien/Ordner
            for i, path in enumerate(source_paths):
                if not os.path.exists(path):
                    self._log_to_queue(f"Warnung: Quellpfad '{path}' existiert nicht und wird übersprungen.", level="WARNING")
                    continue

                # Wenn es ein Ordner ist, verpacken wir ihn (sehr rudimentär für Demo)
                # In einer realen Anwendung würde man hier rekursiv Dateien sammeln oder zip/tar verwenden
                is_directory = os.path.isdir(path)
                
                # Wenn es ein Ordner ist, erstellen wir ein Dummy-Archiv für das Hochladen
                # ECHTE IMPLEMENTIERUNG BENÖTIGT HIER KOMPRIMIERUNG/ARCHIVIERUNG
                if is_directory:
                    temp_archive_name = f"{os.path.basename(path)}_{backup_timestamp}.zip" # Dummy Name
                    temp_archive_path = os.path.join(current_dir, temp_archive_name)
                    self._log_to_queue(f"Simuliere Archivierung von Ordner '{path}' nach '{temp_archive_path}'...", level="INFO")
                    # In einer echten Implementierung: import shutil; shutil.make_archive(...)
                    # Dummy: einfach eine leere Datei erstellen, um den Upload zu simulieren
                    with open(temp_archive_path, 'w') as f:
                        f.write(f"Dummy content for directory {path}")
                    current_file_to_upload = temp_archive_path
                    remote_file_name = temp_archive_name
                else: # Wenn es eine Datei ist
                    current_file_to_upload = path
                    remote_file_name = os.path.basename(path)

                remote_path_prefix = f"backups_{backup_timestamp}/" # Beispiel-Struktur im Ziel
                remote_file_path = os.path.join(remote_path_prefix, remote_file_name)

                self._log_to_queue(f"Verarbeite: {path} ({i+1}/{len(source_paths)})", level="INFO")
                
                temp_encrypted_path = None

                # Verschlüsseln, falls Plugin ausgewählt
                if self.selected_encryption_plugin:
                    encrypted_file_name = f"{remote_file_name}.enc"
                    temp_encrypted_path = os.path.join(current_dir, encrypted_file_name)
                    self._log_to_queue(f"Verschlüssele '{remote_file_name}'...", level="INFO")
                    if not self.selected_encryption_plugin.encrypt(current_file_to_upload, temp_encrypted_path):
                        self._log_to_queue(f"Fehler beim Verschlüsseln von '{remote_file_name}'. Backup abgebrochen.", level="ERROR")
                        if os.path.exists(temp_encrypted_path): os.remove(temp_encrypted_path)
                        if is_directory and os.path.exists(current_file_to_upload): os.remove(current_file_to_upload) # Lösche Dummy-Archiv
                        self.backup_queue.put("finished")
                        return
                    current_file_to_upload = temp_encrypted_path
                    remote_file_path = os.path.join(remote_path_prefix, encrypted_file_name)

                self._log_to_queue(f"Lade '{os.path.basename(current_file_to_upload)}' nach '{self.selected_destination_plugin.get_name()}' hoch...", level="INFO")
                if not self.selected_destination_plugin.upload_file(current_file_to_upload, remote_file_path):
                    self._log_to_queue(f"Fehler beim Hochladen von '{current_file_to_upload}'. Backup abgebrochen.", level="ERROR")
                    if temp_encrypted_path and os.path.exists(temp_encrypted_path): os.remove(temp_encrypted_path)
                    if is_directory and os.path.exists(current_file_to_upload): os.remove(current_file_to_upload) # Lösche Dummy-Archiv
                    self.backup_queue.put("finished")
                    return

                # Temporäre verschlüsselte Datei löschen
                if temp_encrypted_path and os.path.exists(temp_encrypted_path):
                    os.remove(temp_encrypted_path)
                    self._log_to_queue(f"Temporäre verschlüsselte Datei '{temp_encrypted_path}' gelöscht.", level="DEBUG")
                
                # Temporäres Dummy-Archiv löschen, falls es ein Ordner war
                if is_directory and os.path.exists(current_file_to_upload) and current_file_to_upload != path:
                    os.remove(current_file_to_upload)
                    self._log_to_queue(f"Temporäres Archiv '{current_file_to_upload}' gelöscht.", level="DEBUG")

                time.sleep(0.1) # Simulation einer Arbeitsverzögerung

            self._log_to_queue("Post-Backup Skripte ausführen...", level="INFO")
            if self.selected_pre_post_script_plugin:
                if not self.selected_pre_post_script_plugin.run_post_backup_script():
                    self._log_to_queue("Post-Backup Skript fehlgeschlagen.", level="ERROR")
                else:
                    self._log_to_queue("Post-Backup Skript erfolgreich.", level="INFO")

            self._log_to_queue("Backup-Prozess abgeschlossen.", level="INFO")

        except Exception as e:
            self._log_to_queue(f"Ein unerwarteter Fehler im Backup-Thread: {e}", level="ERROR")
            import traceback
            self._log_to_queue(f"Traceback: {traceback.format_exc()}", level="ERROR")
        finally:
            self.backup_queue.put("finished")

    def _log_to_queue(self, message, level="INFO"):
        """Legt eine Log-Nachricht in die Queue, damit sie vom GUI-Thread verarbeitet werden kann."""
        self.backup_queue.put({"message": message, "level": level})

    def _check_backup_queue(self):
        """Überprüft die Queue auf Nachrichten vom Backup-Thread."""
        while not self.backup_queue.empty():
            item = self.backup_queue.get_nowait()
            if item == "finished":
                self.start_backup_button.config(state=tk.NORMAL)
                self._save_config()
                messagebox.showinfo("Backup Status", "Backup-Prozess abgeschlossen!")
                return
            else:
                self._log_message(item["message"], level=item["level"])
        
        if self.start_backup_button['state'] == tk.DISABLED:
            self.master.after(100, self._check_backup_queue)

    def _start_restore_process(self):
        """Startet den Wiederherstellungsprozess (noch eine Dummy-Implementierung)."""
        self._save_current_configs()

        if not self.selected_restore_plugin:
            messagebox.showerror("Wiederherstellungs Fehler", "Bitte wählen Sie ein Wiederherstellungs-Plugin aus.")
            return
        if not self.selected_destination_plugin:
            messagebox.showerror("Wiederherstellungs Fehler", "Bitte wählen Sie ein Ziel-Plugin aus, von dem wiederhergestellt werden soll.")
            return

        restore_plugin_config = {k: v.get() for k, v in self.restore_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        self.selected_restore_plugin.set_config(restore_plugin_config)

        destination_plugin_config = {k: v.get() for k, v in self.destination_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        self.selected_destination_plugin.set_config(destination_plugin_config)

        encryption_plugin_config = {k: v.get() for k, v in self.encryption_plugin_tk_vars.items() if isinstance(v, (tk.StringVar, tk.IntVar, tk.BooleanVar))}
        if self.selected_encryption_plugin:
            self.selected_encryption_plugin.set_config(encryption_plugin_config)

        is_valid, msg = self.selected_restore_plugin.validate_config()
        if not is_valid:
            messagebox.showerror("Wiederherstellungs Fehler: Wiederherstellungs-Plugin", msg)
            return
        is_valid, msg = self.selected_destination_plugin.validate_config()
        if not is_valid:
            messagebox.showerror("Wiederherstellungs Fehler: Ziel-Plugin", msg)
            return
        if self.selected_encryption_plugin:
            is_valid, msg = self.selected_encryption_plugin.validate_config()
            if not is_valid:
                messagebox.showerror("Wiederherstellungs Fehler: Verschlüsselungs-Plugin", msg)
                return

        self._log_message("Starte Wiederherstellungs-Prozess...", level="INFO")
        self.start_restore_button.config(state=tk.DISABLED)

        restore_target_path = self.selected_restore_plugin.get_config().get("restore_location", os.path.join(os.getcwd(), "restored_backup_default"))
        backup_identifier = "latest_backup"

        restore_thread = threading.Thread(target=self._run_restore_in_thread, args=(restore_target_path, backup_identifier), daemon=True)
        restore_thread.start()

        self.restore_queue = queue.Queue()
        self.master.after(100, self._check_restore_queue)


    def _run_restore_in_thread(self, restore_target_path, backup_identifier):
        """Die eigentliche Wiederherstellungs-Logik, die in einem separaten Thread läuft."""
        try:
            self._log_to_queue("Starte Wiederherstellung im Thread...", level="INFO")

            self._log_to_queue(f"Suche Backups im Ziel '{self.selected_destination_plugin.get_name()}'...", level="INFO")
            available_backups = self.selected_destination_plugin.list_backups()
            if not available_backups:
                self._log_to_queue("Keine Backups im Ziel gefunden.", level="ERROR")
                self.restore_queue.put("finished")
                return

            self._log_to_queue(f"Verfügbare Backups: {', '.join(available_backups)}", level="INFO")
            if backup_identifier not in available_backups:
                 if available_backups:
                    self._log_to_queue(f"Backup '{backup_identifier}' nicht gefunden. Wähle ersten verfügbaren Backup: {available_backups[0]}", level="WARNING")
                    backup_identifier = available_backups[0]
                 else:
                    self._log_to_queue(f"Keine Backups verfügbar, um '{backup_identifier}' zu finden.", level="ERROR")
                    self.restore_queue.put("finished")
                    return


            self._log_to_queue(f"Wiederherstellung von '{backup_identifier}' nach '{restore_target_path}'...", level="INFO")

            # Dummy: Nur die erste Datei aus dem simulierten Backup wiederherstellen
            # In einer realen App würde man die Backup-Struktur auslesen und den Benutzer wählen lassen
            remote_file_to_restore = f"backups_{backup_identifier}/testfile.zip.enc" # Oder testfile.txt.enc etc.
            
            # TODO: Ermittle den tatsächlichen Dateinamen und Pfad des Backups im Ziel
            # Hier eine vereinfachte Annahme, dass es eine bekannte Archivdatei gibt

            temp_download_path = os.path.join(current_dir, "temp_downloaded_file.tmp") # Generischer Name für Download
            
            self._log_to_queue(f"Lade '{remote_file_to_restore}' vom Ziel herunter...", level="INFO")
            if not self.selected_destination_plugin.download_file(remote_file_to_restore, temp_download_path):
                self._log_to_queue(f"Fehler beim Herunterladen von '{remote_file_to_restore}'. Wiederherstellung abgebrochen.", level="ERROR")
                self.restore_queue.put("finished")
                return

            current_file_to_decrypt = temp_download_path
            decrypted_output_path = os.path.join(restore_target_path, os.path.basename(remote_file_to_restore).replace(".enc", "")) # Entferne .enc

            if self.selected_encryption_plugin:
                self._log_to_queue(f"Entschlüssele '{temp_download_path}'...", level="INFO")
                if not self.selected_encryption_plugin.decrypt(temp_download_path, decrypted_output_path):
                    self._log_to_queue(f"Fehler beim Entschlüsseln von '{temp_download_path}'. Wiederherstellung fehlgeschlagen.", level="ERROR")
                    if os.path.exists(temp_download_path): os.remove(temp_download_path)
                    self.restore_queue.put("finished")
                    return
            else:
                os.makedirs(restore_target_path, exist_ok=True)
                # Direkt kopieren, wenn keine Entschlüsselung nötig ist, da es keine temporäre Datei war
                shutil.move(temp_download_path, decrypted_output_path) # Verschieben, nicht kopieren
                self._log_to_queue(f"Datei '{temp_download_path}' nach '{decrypted_output_path}' verschoben (keine Entschlüsselung nötig).", level="INFO")

            if os.path.exists(temp_download_path): os.remove(temp_download_path)

            self._log_to_queue("Wiederherstellung im Thread abgeschlossen.", level="INFO")
        except Exception as e:
            self._log_to_queue(f"Ein unerwarteter Fehler im Wiederherstellungs-Thread: {e}", level="ERROR")
            import traceback
            self._log_to_queue(f"Traceback: {traceback.format_exc()}", level="ERROR")
        finally:
            self.restore_queue.put("finished")

    def _check_restore_queue(self):
        """Überprüft die Queue auf Nachrichten vom Wiederherstellungs-Thread."""
        while not self.restore_queue.empty():
            item = self.restore_queue.get_nowait()
            if item == "finished":
                self.start_restore_button.config(state=tk.NORMAL)
                self._save_config()
                messagebox.showinfo("Wiederherstellung Status", "Wiederherstellungs-Prozess abgeschlossen!")
                return
            else:
                self._log_message(item["message"], level=item["level"])
        
        if self.start_restore_button['state'] == tk.DISABLED:
            self.master.after(100, self._check_restore_queue)


if __name__ == "__main__":
    root = tk.Tk()
    app = BackupToolGUI(root)
    root.mainloop()
