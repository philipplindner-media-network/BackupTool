# your_backup_tool/plugin_interfaces.py

import abc
import tkinter as tk # Tkinter für UI-Elemente
from tkinter import ttk

class BasePlugin(abc.ABC):
    """Abstrakte Basisklasse für alle Plugins."""
    def __init__(self, config_data=None, log_callback=None):
        self.config_data = config_data if config_data is not None else {}
        self.log = log_callback if log_callback else self._default_log

    def _default_log(self, message, level="INFO"):
        """Standard-Logging-Funktion, falls keine Rückruffunktion bereitgestellt wird."""
        print(f"[{level.upper()}] BasePlugin: {message}")

    @abc.abstractmethod
    def get_name(self) -> str:
        """Gibt den Anzeigenamen des Plugins zurück (z.B. 'Lokaler Ordner', 'SFTP-Server')."""
        pass

    @abc.abstractmethod
    def get_description(self) -> str:
        """Gibt eine kurze Beschreibung des Plugins zurück."""
        pass

    @abc.abstractmethod
    def get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        """
        Erstellt und packt Tkinter-UI-Elemente in den übergebenen parent_frame
        und speichert die zugehörigen Tkinter-Variablen (StringVar, IntVar etc.)
        im tk_vars_dict unter einem sprechenden Schlüssel.

        Args:
            parent_frame (ttk.Frame): Der Tkinter-Frame, in den die UI-Elemente gepackt werden sollen.
            tk_vars_dict (dict): Ein Dictionary, in dem Tkinter-Variablen
                                   (z.B. tk.StringVar, tk.IntVar) gespeichert werden,
                                   damit ihre Werte später von der GUI ausgelesen werden können.
                                   Schlüssel sollten die Namen der Konfigurationsparameter sein.

        Returns:
            list[tk.Widget]: Eine Liste der erstellten Tkinter-Widgets (optional, primär für Layout-Kontrolle).
        """
        pass

    def set_config(self, config_data: dict):
        """Setzt die Konfiguration für das Plugin."""
        self.config_data = config_data if config_data is not None else {}
        self.log(f"{self.get_name()}: Konfiguration aktualisiert.", level="DEBUG")

    def get_config(self) -> dict:
        """Gibt die aktuelle Konfiguration des Plugins zurück."""
        return self.config_data

    @abc.abstractmethod
    def validate_config(self) -> tuple[bool, str]:
        """
        Validiert die aktuelle Konfiguration des Plugins.

        Returns:
            tuple[bool, str]: (True, "") wenn gültig, (False, "Fehlermeldung") wenn ungültig.
        """
        pass

class BackupSourcePlugin(BasePlugin):
    """Abstrakte Basisklasse für Backup-Quell-Plugins."""
    @abc.abstractmethod
    def get_source_paths(self) -> list[str]: # config_data wird intern genutzt
        """
        Gibt eine Liste von Pfaden (Dateien oder Verzeichnisse) zurück,
        die gesichert werden sollen, basierend auf der aktuellen Konfiguration.
        """
        pass

class BackupDestinationPlugin(BasePlugin):
    """Abstrakte Basisklasse für Backup-Ziel-Plugins."""
    @abc.abstractmethod
    def get_type_id(self) -> str:
        """
        Gibt eine eindeutige ID für den Plugin-Typ zurück (z.B. 'local_folder', 'sftp').
        Wird für die Speicherung der Konfiguration verwendet.
        """
        pass

    @abc.abstractmethod
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Lädt eine Datei vom lokalen System zum Ziel hoch."""
        pass

    @abc.abstractmethod
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Lädt eine Datei vom Ziel zum lokalen System herunter."""
        pass

    @abc.abstractmethod
    def list_files(self, remote_path: str = "") -> list[str]:
        """Listet Dateien und Verzeichnisse am Ziel auf."""
        pass

    @abc.abstractmethod
    def delete_file(self, remote_file_path: str) -> bool:
        """Löscht eine Datei vom Ziel."""
        pass

class EncryptionPlugin(BasePlugin):
    """Abstrakte Basisklasse für Verschlüsselungs-Plugins."""
    @abc.abstractmethod
    def encrypt(self, input_file_path: str, output_file_path: str) -> bool:
        """Verschlüsselt eine Datei."""
        pass

    @abc.abstractmethod
    def decrypt(self, input_file_path: str, output_file_path: str) -> bool:
        """Entschlüsselt eine Datei."""
        pass

class PrePostScriptPlugin(BasePlugin):
    """Abstrakte Basisklasse für Pre- und Post-Backup-Skript-Plugins."""
    @abc.abstractmethod
    def run_pre_backup_script(self) -> bool:
        """Führt ein Skript vor dem Backup aus."""
        pass

    @abc.abstractmethod
    def run_post_backup_script(self) -> bool:
        """Führt ein Skript nach dem Backup aus."""
        pass

class RestorePlugin(BasePlugin):
    """Abstrakte Basisklasse für Wiederherstellungs-Plugins."""
    @abc.abstractmethod
    def restore_backup(
        self,
        destination_plugin: BackupDestinationPlugin,
        encryption_plugin: EncryptionPlugin,
        local_restore_path: str,
        backup_identifier: str
    ) -> bool:
        """Stellt ein Backup wieder her."""
        pass
