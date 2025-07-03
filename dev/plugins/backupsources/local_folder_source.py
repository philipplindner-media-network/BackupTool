import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os
from plugin_interfaces import BackupSourcePlugin

class LocalFolderSourcePlugin(BackupSourcePlugin):
    def __init__(self, log_callback):
        super().__init__(log_callback)
        self.log = log_callback
        self.config = {}
        self.source_paths_text = None # Wichtig: Initialisiere dies hier

    def get_name(self):
        return "Local Folder"

    def get_description(self):
        return "Selects files and folders from a local directory for backup."

    def get_ui_elements(self, parent_frame, tk_vars):
        self.log(f"Creating UI for {self.get_name()}", level="DEBUG")
        
        ttk.Label(parent_frame, text="Pfade (eine pro Zeile):").pack(padx=5, pady=2, anchor="w")
        
        # Zuweisung des ScrolledText-Widgets
        self.source_paths_text = scrolledtext.ScrolledText(parent_frame, wrap=tk.WORD, height=8, width=50)
        self.source_paths_text.pack(padx=5, pady=5, fill="both", expand=True)
        
        # Lade gespeicherte Pfade (falls vorhanden) in den Textbereich
        saved_paths = self.config.get('source_paths', [])
        if saved_paths:
            self.source_paths_text.insert(tk.END, "\n".join(saved_paths))
        
        # Speichere das Text-Widget selbst in tk_vars
        tk_vars['source_paths'] = self.source_paths_text 

        add_folder_button = ttk.Button(parent_frame, text="Ordner hinzufügen", command=self._add_folder)
        add_folder_button.pack(padx=5, pady=2, anchor="e")

        add_file_button = ttk.Button(parent_frame, text="Datei hinzufügen", command=self._add_file)
        add_file_button.pack(padx=5, pady=2, anchor="e")

    def _add_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            current_text = self.source_paths_text.get("1.0", tk.END).strip()
            if current_text:
                self.source_paths_text.delete("1.0", tk.END)
                self.source_paths_text.insert(tk.END, current_text + "\n" + folder_selected)
            else:
                self.source_paths_text.insert(tk.END, folder_selected)
            self.log(f"Added folder to source paths: {folder_selected}", level="DEBUG")

    def _add_file(self):
        file_selected = filedialog.askopenfilename()
        if file_selected:
            current_text = self.source_paths_text.get("1.0", tk.END).strip()
            if current_text:
                self.source_paths_text.delete("1.0", tk.END)
                self.source_paths_text.insert(tk.END, current_text + "\n" + file_selected)
            else:
                self.source_paths_text.insert(tk.END, file_selected)
            self.log(f"Added file to source paths: {file_selected}", level="DEBUG")

    def get_source_paths(self):
        """Gibt die Liste der zu sichernden Pfade zurück."""
        if self.source_paths_text:
            content = self.source_paths_text.get("1.0", tk.END)
            paths = [line.strip() for line in content.splitlines() if line.strip()]
            return paths
        return []

    def set_config(self, config):
        """Setzt die Konfiguration für das Plugin."""
        self.config = config
        self.log(f"Config for {self.get_name()} set: {self.config}", level="DEBUG")
        # Aktualisiere das UI, falls es schon erstellt wurde
        if self.source_paths_text and 'source_paths' in config:
            self.source_paths_text.delete("1.0", tk.END)
            self.source_paths_text.insert(tk.END, "\n".join(config['source_paths']))


    def validate_config(self):
        """Validiert die aktuelle Konfiguration des Plugins."""
        paths = self.get_source_paths()
        if not paths:
            return False, "Es müssen Quellpfade angegeben werden."
        
        for path in paths:
            if not os.path.exists(path):
                self.log(f"Warnung: Quellpfad '{path}' existiert nicht und wird möglicherweise übersprungen.", level="WARNING")
                # return False, f"Quellpfad '{path}' existiert nicht." # Dies würde das Backup stoppen
        return True, "Konfiguration ist gültig."
