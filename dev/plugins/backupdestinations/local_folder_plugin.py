# /home/philipp/Dokumente/BAckUp_tool_py/plugins/destinations/local_folder_plugin.py

from plugin_interfaces import BackupDestinationPlugin
import os
import shutil
import tkinter as tk
from tkinter import ttk

class LocalFolderPlugin(BackupDestinationPlugin):
    def __init__(self, config_data=None, log_callback=None):
        super().__init__(config_data, log_callback)
        self.log_callback = log_callback
        
        # Standard-Pfad oder aus Konfiguration laden
        self.target_path = self.config_data.get("target_path", os.path.expanduser("~/backups"))

    def get_name(self):
        return "Local Folder"

    def get_description(self):
        return "Stores backup files in a local folder or mounted network share."

    def get_type_id(self):
        return "local_folder"

    def upload_file(self, local_file_path, remote_path):
        """
        Kopiert eine lokale Datei in den Zielordner.
        remote_path wird hier als der gewünschte Dateiname im Zielordner verwendet.
        """
        try:
            # Stelle sicher, dass der Zielordner existiert
            os.makedirs(self.target_path, exist_ok=True)
            
            destination_file_path = os.path.join(self.target_path, remote_path)
            shutil.copy2(local_file_path, destination_file_path)
            self.log(f"Copied '{local_file_path}' to '{destination_file_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error copying file to local folder '{self.target_path}': {e}", level="ERROR")
            return False

    def download_file(self, remote_file_path, local_destination_path):
        """Lädt eine Datei vom Zielordner herunter (kopiert sie lokal)."""
        try:
            source_file_path = os.path.join(self.target_path, remote_file_path)
            if not os.path.exists(source_file_path):
                self.log(f"File '{source_file_path}' not found for download.", level="ERROR")
                return False
            
            shutil.copy2(source_file_path, local_destination_path)
            self.log(f"Copied '{source_file_path}' to '{local_destination_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error downloading file from local folder '{self.target_path}': {e}", level="ERROR")
            return False

    def list_files(self, remote_path=""):
        """Listet Dateien und Ordner im Zielordner auf."""
        try:
            full_path_to_list = os.path.join(self.target_path, remote_path)
            if not os.path.isdir(full_path_to_list):
                self.log(f"Path '{full_path_to_list}' is not a directory.", level="ERROR")
                return []
            
            files_list = []
            for item in os.listdir(full_path_to_list):
                item_path = os.path.join(full_path_to_list, item)
                item_type = "folder" if os.path.isdir(item_path) else "file"
                files_list.append(f"{item} ({item_type})")
            self.log(f"Listed {len(files_list)} items in local folder '{full_path_to_list}'.", level="INFO")
            return files_list
        except Exception as e:
            self.log(f"Error listing files in local folder '{self.target_path}': {e}", level="ERROR")
            return []

    def delete_file(self, remote_file_path):
        """Löscht eine Datei im Zielordner."""
        try:
            file_to_delete_path = os.path.join(self.target_path, remote_file_path)
            if not os.path.exists(file_to_delete_path):
                self.log(f"File '{file_to_delete_path}' not found for deletion.", level="WARNING")
                return False
            
            os.remove(file_to_delete_path)
            self.log(f"Deleted file '{file_to_delete_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error deleting file from local folder '{self.target_path}': {e}", level="ERROR")
            return False

    def get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        """Erstellt die UI-Elemente für die lokale Ordnerkonfiguration."""
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Label(frame, text="Target Folder Path:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        
        target_path_var = tk.StringVar(value=self.target_path)
        ttk.Entry(frame, textvariable=target_path_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["target_path"] = target_path_var

        browse_button = ttk.Button(frame, text="Browse...", 
                                   command=lambda: self._browse_folder(target_path_var))
        browse_button.grid(row=0, column=2, padx=5, pady=2)

        frame.columnconfigure(1, weight=1) # Entry Feld dehnbar machen
        
        return []

    def _browse_folder(self, path_var):
        """Öffnet einen Dateidialog zur Auswahl eines Ordners."""
        folder_selected = filedialog.askdirectory(initialdir=path_var.get())
        if folder_selected:
            path_var.set(folder_selected)
            self.target_path = folder_selected # Aktualisiere internes Attribut

    def validate_config(self):
        """Validiert den Zielordnerpfad."""
        if not self.target_path:
            return False, "Target folder path cannot be empty."
        
        # Versuche, den Pfad zu erstellen, um Schreibrechte zu prüfen
        try:
            os.makedirs(self.target_path, exist_ok=True)
            # Teste Schreibrechte, indem eine temporäre Datei erstellt und gelöscht wird
            temp_file = os.path.join(self.target_path, "temp_write_test.tmp")
            with open(temp_file, "w") as f:
                f.write("test")
            os.remove(temp_file)
            return True, ""
        except OSError as e:
            return False, f"Cannot access or write to target folder '{self.target_path}': {e}"
        except Exception as e:
            return False, f"An unexpected error occurred during path validation: {e}"
