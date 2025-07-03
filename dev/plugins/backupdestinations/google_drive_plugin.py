# /home/philipp/Dokumente/BAckUp_tool_py/plugins/destinations/google_drive_plugin.py

from plugin_interfaces import BackupDestinationPlugin
import tkinter as tk
from tkinter import ttk
import os
import io

# Importiere Google Drive spezifische Bibliotheken
# Stelle sicher, dass du diese installiert hast: pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError


class GoogleDrivePlugin(BackupDestinationPlugin):
    def __init__(self, config_data=None, log_callback=None):
        # Wichtig: config_data direkt an die Superklasse übergeben.
        # Die Superklasse (BackupDestinationPlugin) sorgt dafür, dass self.config_data 
        # immer ein Dictionary ist (auch wenn hier None übergeben wurde).
        super().__init__(config_data, log_callback) 
        
        self.log_callback = log_callback # Speichere den Callback für das Logging
        
        # Initialisiere Google Drive spezifische Konfigurationsvariablen
        # Greife jetzt auf self.config_data zu, das von der Superklasse gesetzt wurde
        self.client_id = self.config_data.get("client_id", "")
        self.client_secret = self.config_data.get("client_secret", "")
        self.access_token_info = self.config_data.get("access_token_info", None) # Das gesamte Token-Info-Dict
        self.folder_id = self.config_data.get("folder_id", "root") # 'root' für das Hauptverzeichnis

        self.SCOPES = ['https://www.googleapis.com/auth/drive.file'] # Erlaubt Zugriff auf Dateien, die von der App erstellt/geöffnet wurden
        self.CREDS_TOKEN_FILE = os.path.join(os.path.expanduser("~"), ".local", "share", "AdvancedBackupTool", "gd_token.json")

        self.gd_service = None 
        if self.access_token_info: # Versuche den Service mit gespeicherten Tokens zu initialisieren
            self._initialize_google_drive_service_from_token()

    def get_name(self):
        return "Google Drive Backup"

    def get_description(self):
        return "Uploads backup files to Google Drive."

    def get_type_id(self):
        return "google_drive"

    def _initialize_google_drive_service_from_token(self):
        """Initialisiert den Google Drive Service mit einem vorhandenen Token."""
        try:
            creds = Credentials.from_authorized_user_info(self.access_token_info, self.SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.log("Google Drive access token refreshed.", level="INFO")
                # Aktualisiertes Token speichern
                self.config_data["access_token_info"] = creds.to_json()
                # Wichtig: GUI müsste diese config_data dann persistieren!
                # Dies geschieht normalerweise, wenn der Job gespeichert wird.
            self.gd_service = build('drive', 'v3', credentials=creds)
            self.log("Google Drive service initialized successfully from token.", level="INFO")
        except Exception as e:
            self.log(f"Error initializing Google Drive service from token: {e}", level="ERROR")
            self.gd_service = None # Sicherstellen, dass der Service None ist bei Fehlern

    def _authenticate_google_drive(self, parent_frame):
        """Führt den OAuth2-Authentifizierungsprozess durch."""
        try:
            # Stelle sicher, dass das Client-Secret-JSON existiert
            client_config = {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": ["http://localhost"] # Oder andere zulässige Redirect-URIs
                }
            }
            # Speichere die Client-Konfiguration temporär in einer Datei
            temp_client_secret_path = os.path.join(os.path.dirname(self.CREDS_TOKEN_FILE), "client_secret_temp.json")
            with open(temp_client_secret_path, 'w') as f:
                json.dump(client_config, f)

            flow = InstalledAppFlow.from_client_secrets_file(
                temp_client_secret_path, self.SCOPES
            )
            # Entferne die temporäre Datei sofort wieder
            os.remove(temp_client_secret_path)

            creds = None
            # Standardmäßig wird der Browser geöffnet. Bei lokalen Apps ist dies oft am einfachsten.
            creds = flow.run_local_server(port=0) 
            
            # Speichern der Anmeldeinformationen für die nächste Ausführung
            self.access_token_info = creds.to_json()
            # Wichtig: Speichere access_token_info zurück in self.config_data, damit es in main.py gespeichert wird
            self.config_data["access_token_info"] = self.access_token_info 
            
            self.gd_service = build('drive', 'v3', credentials=creds)
            self.log("Google Drive authentication successful.", level="INFO")
            messagebox.showinfo("Google Drive", "Authentication successful!")
            return True
        except HttpError as error:
            self.log(f"An HTTP error occurred during Google Drive authentication: {error}", level="ERROR")
            messagebox.showerror("Google Drive Authentication Error", f"Failed to authenticate Google Drive. Error: {error}")
        except Exception as e:
            self.log(f"An unexpected error occurred during Google Drive authentication: {e}", level="ERROR")
            messagebox.showerror("Google Drive Authentication Error", f"An unexpected error occurred: {e}")
        self.gd_service = None
        self.access_token_info = None
        return False

    def validate_config(self):
        """Überprüft, ob Client ID/Secret vorhanden sind und ob der Service authentifiziert ist."""
        if not self.client_id or not self.client_secret:
            return False, "Client ID and Client Secret must be provided."
        
        # Versuche, den Service zu initialisieren/zu erneuern, wenn er noch nicht da ist oder abgelaufen ist
        if not self.gd_service:
            # Versuche, mit dem gespeicherten Token zu initialisieren
            if self.access_token_info:
                self._initialize_google_drive_service_from_token()
            
            if not self.gd_service: # Wenn immer noch kein Service, dann Authentifizierung erforderlich
                 return False, "Google Drive service not authenticated. Please authenticate."
        
        return True, ""

   def  get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        """
        Erstellt die UI-Elemente für die Google Drive Konfiguration.
        """
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        # Client ID
        ttk.Label(frame, text="Client ID:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        client_id_var = tk.StringVar(value=self.client_id)
        ttk.Entry(frame, textvariable=client_id_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["client_id"] = client_id_var

        # Client Secret
        ttk.Label(frame, text="Client Secret:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        client_secret_var = tk.StringVar(value=self.client_secret)
        ttk.Entry(frame, textvariable=client_secret_var, show="*").grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["client_secret"] = client_secret_var

        # Folder ID (optional, für spezifischen Zielordner)
        ttk.Label(frame, text="Target Folder ID (optional, 'root' for My Drive):").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        folder_id_var = tk.StringVar(value=self.folder_id)
        ttk.Entry(frame, textvariable=folder_id_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["folder_id"] = folder_id_var

        # Authentifizierungs-Button
        authenticate_button = ttk.Button(frame, text="Authenticate Google Drive", 
                                         command=lambda: self._authenticate_google_drive(parent_frame))
        authenticate_button.grid(row=3, column=0, columnspan=2, padx=5, pady=10)

        # Frame anpassbar machen
        frame.columnconfigure(1, weight=1)
        
        return []

    def upload_file(self, local_file_path, remote_path):
        """Lädt eine lokale Datei in Google Drive hoch."""
        if not self.gd_service:
            self.log("Google Drive service not authenticated. Cannot upload.", level="ERROR")
            return False

        try:
            # Überprüfe, ob der Zielordner existiert, oder erstelle ihn
            target_folder_id = self.folder_id
            if target_folder_id and target_folder_id != "root":
                # Versuche, den Ordner zu finden
                results = self.gd_service.files().list(
                    q=f"mimeType='application/vnd.google-apps.folder' and name='{target_folder_id}' and trashed=false",
                    spaces='drive',
                    fields='nextPageToken, files(id, name)'
                ).execute()
                items = results.get('files', [])
                if not items:
                    # Ordner nicht gefunden, erstelle ihn
                    file_metadata = {
                        'name': target_folder_id,
                        'mimeType': 'application/vnd.google-apps.folder'
                    }
                    folder = self.gd_service.files().create(body=file_metadata, fields='id').execute()
                    target_folder_id = folder.get('id')
                    self.log(f"Created Google Drive folder: {target_folder_id}", level="INFO")
                else:
                    target_folder_id = items[0]['id']
                    self.log(f"Using existing Google Drive folder: {target_folder_id}", level="INFO")
            
            file_name = os.path.basename(local_file_path)
            file_metadata = {'name': file_name}
            if target_folder_id and target_folder_id != "root":
                 file_metadata['parents'] = [target_folder_id]

            media = MediaFileUpload(local_file_path, resumable=True)
            
            # Suche nach bestehender Datei, um sie ggf. zu aktualisieren anstatt neu zu erstellen
            # (Dies ist eine einfache Implementierung, fortgeschrittener wäre Versionsverwaltung)
            existing_files = self.gd_service.files().list(
                q=f"name='{file_name}' and '{target_folder_id}' in parents and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute().get('files', [])

            if existing_files:
                # Update bestehende Datei
                file_id = existing_files[0]['id']
                uploaded_file = self.gd_service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id'
                ).execute()
                self.log(f"Updated file '{file_name}' to Google Drive with ID: {uploaded_file.get('id')}", level="INFO")
            else:
                # Neue Datei hochladen
                uploaded_file = self.gd_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id'
                ).execute()
                self.log(f"Uploaded file '{file_name}' to Google Drive with ID: {uploaded_file.get('id')}", level="INFO")
            
            return True
        except HttpError as error:
            self.log(f"An HTTP error occurred during Google Drive upload for {local_file_path}: {error}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during Google Drive upload for {local_file_path}: {e}", level="ERROR")
            return False

    def download_file(self, remote_file_path, local_destination_path):
        """Lädt eine Datei von Google Drive herunter."""
        if not self.gd_service:
            self.log("Google Drive service not authenticated. Cannot download.", level="ERROR")
            return False

        try:
            # Suche nach der Datei anhand des Namens (remote_file_path ist hier der Dateiname)
            # Dies ist eine vereinfachte Suche. In der Realität müsste man den Pfad korrekt parsen.
            # Für Backup-Zwecke ist remote_file_path oft der Dateiname des Backups.
            query = f"name='{remote_file_path}' and '{self.folder_id}' in parents and trashed=false"
            results = self.gd_service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
            items = results.get('files', [])

            if not items:
                self.log(f"File '{remote_file_path}' not found in Google Drive folder '{self.folder_id}'.", level="ERROR")
                return False

            file_id = items[0]['id']
            
            request = self.gd_service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_destination_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                # self.log(f"Download {int(status.progress() * 100)}%.", level="DEBUG") # Optional: Fortschritts-Logging
            self.log(f"Downloaded '{remote_file_path}' from Google Drive to '{local_destination_path}'.", level="INFO")
            return True
        except HttpError as error:
            self.log(f"An HTTP error occurred during Google Drive download for {remote_file_path}: {error}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during Google Drive download for {remote_file_path}: {e}", level="ERROR")
            return False

    def list_files(self, remote_path=""):
        """Listet Dateien und Ordner im angegebenen Google Drive Remote-Pfad auf."""
        if not self.gd_service:
            self.log("Google Drive service not authenticated. Cannot list files.", level="ERROR")
            return []

        files_list = []
        try:
            # Wenn remote_path leer ist, listen wir den konfigurierten Ordner auf.
            # Andernfalls, müssten wir remote_path zu einer Ordner-ID auflösen.
            # Für Einfachheit nehmen wir an, dass remote_path hier ignoriert wird
            # und wir immer den konfigurierten self.folder_id listen.
            
            query = f"'{self.folder_id}' in parents and trashed=false"
            results = self.gd_service.files().list(
                q=query,
                spaces='drive',
                fields='nextPageToken, files(id, name, mimeType)'
            ).execute()
            items = results.get('files', [])
            
            for item in items:
                file_type = "folder" if item['mimeType'] == 'application/vnd.google-apps.folder' else "file"
                files_list.append(f"{item['name']} ({file_type})")

            self.log(f"Listed {len(files_list)} files/folders in Google Drive folder '{self.folder_id}'.", level="INFO")
        except HttpError as error:
            self.log(f"An HTTP error occurred during Google Drive file listing: {error}", level="ERROR")
        except Exception as e:
            self.log(f"An unexpected error occurred during Google Drive file listing: {e}", level="ERROR")
        return files_list

    def delete_file(self, remote_file_path):
        """Löscht eine Datei in Google Drive."""
        if not self.gd_service:
            self.log("Google Drive service not authenticated. Cannot delete.", level="ERROR")
            return False

        try:
            # Suche nach der Datei, die gelöscht werden soll
            query = f"name='{remote_file_path}' and '{self.folder_id}' in parents and trashed=false"
            results = self.gd_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
            items = results.get('files', [])

            if not items:
                self.log(f"File '{remote_file_path}' not found for deletion in Google Drive folder '{self.folder_id}'.", level="WARNING")
                return False

            file_id = items[0]['id']
            self.gd_service.files().delete(fileId=file_id).execute()
            self.log(f"Deleted file '{remote_file_path}' (ID: {file_id}) from Google Drive.", level="INFO")
            return True
        except HttpError as error:
            self.log(f"An HTTP error occurred during Google Drive deletion for {remote_file_path}: {error}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during Google Drive deletion for {remote_file_path}: {e}", level="ERROR")
            return False
