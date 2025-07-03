# your_backup_tool/plugin_loader.py

import os
import importlib.util
import sys

# Wichtig: Stelle sicher, dass du plugin_interfaces hier importierst,
# da es für die Typüberprüfung (issubclass) benötigt wird.
# Je nach Projektstruktur muss der Pfad hier korrekt sein.
# Wenn plugin_loader.py und plugin_interfaces.py im selben Hauptverzeichnis sind, reicht dieser Import.
# Wenn plugin_interfaces.py in einem Unterordner ist, muss der Import entsprechend angepasst werden.
# Da main.py den Root-Ordner zu sys.path hinzufügt, sollte dies funktionieren,
# solange plugin_interfaces.py auf dieser Ebene ist.
from plugin_interfaces import BasePlugin # Brauchen wir für issubclass-Prüfung


class PluginLoader:
    def __init__(self, plugin_dir: str):
        """
        Initialisiert den PluginLoader.
        Args:
            plugin_dir (str): Der Hauptpfad, unter dem die Plugin-Unterordner liegen (z.B. 'plugins/').
        """
        self.plugin_dir = plugin_dir

    def _log_internal(self, message: str, level: str = "INFO"):
        """
        Interne Logging-Funktion für den PluginLoader selbst.
        Diese wird verwendet, wenn der Loader selbst etwas melden muss,
        bevor die GUI-Log-Funktion an die Plugins übergeben werden kann.
        """
        print(f"[PluginLoader-Internal] [{level.upper()}] {message}")

    def load_plugins(self, plugin_type: type[BasePlugin], log_callback: callable) -> list[BasePlugin]:
        """
        Lädt Plugins eines bestimmten Typs aus dem entsprechenden Unterverzeichnis.
        
        Args:
            plugin_type (type): Der Typ des Plugins, der geladen werden soll (z.B. BackupSourcePlugin).
            log_callback (callable): Eine Funktion (z.B. self._log_message aus der GUI),
                                     die an die Plugin-Instanzen zur Verwendung übergeben wird.
        
        Returns:
            list[BasePlugin]: Eine Liste von instanziierten Plugin-Objekten des angegebenen Typs.
        """
        plugins = []
        
        # Bestimme den Unterordner basierend auf dem Plugin-Typ-Namen (z.B. "BackupSourcePlugin" -> "sources")
        # Ausnahme für BasePlugin, falls es direkt geladen werden sollte (normalerweise nicht der Fall)
        if plugin_type == BasePlugin:
            folder_name = "" # Oder ein spezifischer Ordner für "Basis-Plugins"
            self._log_internal("Attempting to load BasePlugin directly, this is unusual.", level="WARNING")
        else:
            folder_name = plugin_type.__name__.replace('Plugin', '').lower() + 's'

        target_dir = os.path.join(self.plugin_dir, folder_name)
        
        if not os.path.exists(target_dir):
            self._log_internal(f"Plugin-Verzeichnis '{target_dir}' nicht gefunden. Keine {plugin_type.__name__}s geladen.", level="WARNING")
            return []

        for filename in os.listdir(target_dir):
            if filename.endswith(".py") and filename != "__init__.py":
                module_name = filename[:-3] # Entferne .py Endung
                file_path = os.path.join(target_dir, filename)

                try:
                    # Lade das Modul dynamisch
                    spec = importlib.util.spec_from_file_location(module_name, file_path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[module_name] = module # Füge das Modul zu sys.modules hinzu
                    spec.loader.exec_module(module) # Führe den Code des Moduls aus

                    # Durchlaufe die Attribute des Moduls, um die Plugin-Klasse zu finden
                    for name, obj in module.__dict__.items():
                        # Überprüfe, ob 'obj' eine Klasse ist, die vom gewünschten 'plugin_type' erbt,
                        # aber nicht der 'plugin_type' selbst ist (um die abstrakte Basisklasse nicht zu instanziieren)
                        if isinstance(obj, type) and issubclass(obj, plugin_type) and obj is not plugin_type:
                            self._log_internal(f"Gefundene Plugin-Klasse: {name} in Datei '{filename}'.", level="DEBUG")
                            try:
                                # Instanziiere das Plugin und übergebe die leere Konfiguration
                                # und das globale log_callback.
                                # Die eigentliche Konfiguration wird später über set_config gesetzt.
                                instance = obj(config_data={}, log_callback=log_callback)
                                plugins.append(instance)
                                self._log_internal(f"Plugin erfolgreich instanziiert: {name}.", level="INFO")
                            except Exception as e:
                                # Fang spezifische Fehler beim Instanziieren ab
                                self._log_internal(f"Fehler beim Instanziieren von Plugin '{name}' aus '{filename}': {e}. "
                                                   f"Bitte überprüfen Sie den Konstruktor (__init__) des Plugins.", level="ERROR")
                                # Optional: Stacktrace für detailliertere Fehleranalyse
                                # import traceback
                                # self._log_internal(traceback.format_exc(), level="ERROR")

                except Exception as e:
                    # Fang Fehler beim Laden des Moduls ab (z.B. Syntaxfehler in der Plugin-Datei)
                    self._log_internal(f"Fehler beim Laden der Plugin-Datei '{filename}': {e}. "
                                       f"Stellen Sie sicher, dass die Datei gültigen Python-Code enthält.", level="ERROR")
                    # import traceback
                    # self._log_internal(traceback.format_exc(), level="ERROR")
        return plugins
