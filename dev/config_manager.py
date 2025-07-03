import os
import json
import base64
from cryptography.fernet import Fernet, InvalidToken
#from backup_logic import generate_and_save_config_key, load_config_key
from backup_logic import generate_and_save_config_key

class ConfigManager:
    """
    Verwaltet das Laden und Speichern von Anwendungskonfigurationen und Backup-Jobs.
    Beinhaltet die Verschlüsselung sensibler Daten.
    """
    def __init__(self):
        # Basisverzeichnis für Anwendungsdaten im Benutzerprofil
        self.app_data_dir = os.path.join(os.path.expanduser("~"), ".local", "share", "AdvancedBackupTool")
        
        # Sicherstellen, dass das Anwendungsverzeichnis existiert
        os.makedirs(self.app_data_dir, exist_ok=True)

        self.config_file_path = os.path.join(self.app_data_dir, "config.json")
        self.config_key_file_path = os.path.join(self.app_data_dir, "config_key.key") # Korrigierter Pfad

        # Lade oder generiere den Verschlüsselungsschlüssel für die Konfigurationsdatei
        self.config_encryption_key = generate_and_save_config_key(self.config_key_file_path)
        self.fernet = Fernet(self.config_encryption_key)
        
        self.config = self._load_config()

    def _load_config(self):
        """
        Lädt die verschlüsselte Konfiguration aus der Datei und entschlüsselt sie.
        """
        if not os.path.exists(self.config_file_path):
            return {"jobs": [], "plugin_settings": {}}

        try:
            with open(self.config_file_path, "rb") as f:
                encrypted_data = f.read()
            
            decrypted_data = self.fernet.decrypt(encrypted_data).decode('utf-8')
            return json.loads(decrypted_data)
        except InvalidToken:
            print("Warnung: Konfigurationsdatei konnte nicht entschlüsselt werden. Schlüssel möglicherweise geändert oder Datei korrupt. Erstelle leere Konfiguration.")
            # Bei Fehlern eine leere Konfiguration zurückgeben
            return {"jobs": [], "plugin_settings": {}}
        except Exception as e:
            print(f"Fehler beim Laden der Konfiguration: {e}. Erstelle leere Konfiguration.")
            return {"jobs": [], "plugin_settings": {}}

    def save_config(self):
        """
        Verschlüsselt die aktuelle Konfiguration und speichert sie in der Datei.
        """
        try:
            json_data = json.dumps(self.config, indent=4)
            encrypted_data = self.fernet.encrypt(json_data.encode('utf-8'))
            
            with open(self.config_file_path, "wb") as f:
                f.write(encrypted_data)
            print("Konfiguration erfolgreich gespeichert.")
        except Exception as e:
            print(f"Fehler beim Speichern der Konfiguration: {e}")

    def get_all_jobs(self):
        """
        Gibt alle gespeicherten Backup-Jobs zurück.
        """
        return self.config.get("jobs", [])

    def get_job_by_name(self, job_name):
        """
        Sucht und gibt einen spezifischen Job anhand seines Namens zurück.
        """
        for job in self.config.get("jobs", []):
            if job.get("name") == job_name:
                return job
        return None

    def add_job(self, job_data):
        """
        Fügt einen neuen Backup-Job hinzu.
        """
        # Überprüfen, ob ein Job mit diesem Namen bereits existiert
        if self.get_job_by_name(job_data.get("name")):
            print(f"Job mit dem Namen '{job_data.get('name')}' existiert bereits. Bitte wählen Sie einen anderen Namen.")
            return False
        self.config["jobs"].append(job_data)
        self.save_config()
        return True

    def update_job(self, job_name, new_job_data):
        """
        Aktualisiert einen bestehenden Backup-Job anhand seines Namens.
        """
        found = False
        for i, job in enumerate(self.config["jobs"]):
            if job.get("name") == job_name:
                self.config["jobs"][i] = new_job_data
                found = True
                break
        if found:
            self.save_config()
            print(f"Job '{job_name}' erfolgreich aktualisiert.")
        else:
            print(f"Job '{job_name}' nicht gefunden.")
        return found

    def delete_job(self, job_name):
        """
        Löscht einen Backup-Job anhand seines Namens.
        """
        initial_len = len(self.config["jobs"])
        self.config["jobs"] = [job for job in self.config["jobs"] if job.get("name") != job_name]
        if len(self.config["jobs"]) < initial_len:
            self.save_config()
            print(f"Job '{job_name}' erfolgreich gelöscht.")
            return True
        else:
            print(f"Job '{job_name}' nicht gefunden.")
            return False

    def get_plugin_settings(self, plugin_type_id, plugin_instance_id=None):
        """
        Gibt die Einstellungen für ein spezifisches Plugin oder alle Einstellungen eines Typs zurück.
        plugin_instance_id wird verwendet, wenn ein Plugin mehrere Instanzen haben kann (z.B. verschiedene Destinationen).
        """
        settings = self.config.get("plugin_settings", {}).get(plugin_type_id, {})
        if plugin_instance_id:
            return settings.get(plugin_instance_id, {})
        return settings # Gibt alle Instanzeinstellungen für diesen Typ zurück

    def set_plugin_settings(self, plugin_type_id, settings_data, plugin_instance_id=None):
        """
        Speichert die Einstellungen für ein spezifisches Plugin.
        """
        if "plugin_settings" not in self.config:
            self.config["plugin_settings"] = {}
        if plugin_type_id not in self.config["plugin_settings"]:
            self.config["plugin_settings"][plugin_type_id] = {}
        
        if plugin_instance_id:
            self.config["plugin_settings"][plugin_type_id][plugin_instance_id] = settings_data
        else:
            # Wenn keine Instanz-ID angegeben, überschreibe direkt die Einstellungen für diesen Typ
            # Dies ist typischerweise für Plugins, die nur eine globale Einstellung haben.
            self.config["plugin_settings"][plugin_type_id] = settings_data
        self.save_config()


# Hilfsfunktionen (aus backup_logic.py, hier nur zur Referenz, sollten von dort importiert werden)
# from backup_logic import generate_and_save_config_key, load_config_key

# Hinweis: Die Funktionen generate_and_save_config_key und load_config_key 
# müssen in der backup_logic.py definiert sein und von hier importiert werden.
# Ich füge sie hier nicht ein, um Redundanz zu vermeiden, da sie schon in backup_logic.py stehen.
