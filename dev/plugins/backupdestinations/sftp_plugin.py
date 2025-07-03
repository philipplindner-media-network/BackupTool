# /home/philipp/Dokumente/BAckUp_tool_py/plugins/destinations/sftp_plugin.py

from plugin_interfaces import BackupDestinationPlugin
import paramiko # pip install paramiko
import os
import tkinter as tk
from tkinter import ttk

class SFTPPlugin(BackupDestinationPlugin):
    def __init__(self, config_data=None, log_callback=None):
        super().__init__(config_data, log_callback)
        self.log_callback = log_callback
        
        self.hostname = self.config_data.get("sftp_host", "")
        self.port = int(self.config_data.get("sftp_port", 22))
        self.username = self.config_data.get("sftp_user", "")
        self.password = self.config_data.get("sftp_password", "") # Oder Key-Pfad
        self.remote_base_path = self.config_data.get("sftp_remote_base_path", "/")

        self.ssh_client = None
        self.sftp_client = None

    def get_name(self):
        return "SFTP (Hetzner Storage Box)"

    def get_description(self):
        return "Uploads backup files via SFTP (e.g., to Hetzner Storage Box)."

    def get_type_id(self):
        return "sftp"

    def _connect(self):
        """Stellt eine SFTP-Verbindung her."""
        if self.sftp_client and self.sftp_client.get_channel().is_active():
            return True # Bereits verbunden

        try:
            self.log(f"Connecting to SFTP server: {self.hostname}:{self.port} as {self.username}", level="INFO")
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.load_system_host_keys()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy()) # Vorsicht: AutoAddPolicy für einfache Tests, besser KnownHosts
            
            self.ssh_client.connect(
                hostname=self.hostname,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=10 # Verbindungs-Timeout
            )
            self.sftp_client = self.ssh_client.open_sftp()
            self.log("SFTP connection established.", level="INFO")
            return True
        except paramiko.AuthenticationException:
            self.log("SFTP authentication failed. Check username and password.", level="ERROR")
            messagebox.showerror("SFTP Error", "Authentication failed. Check username and password.")
            return False
        except paramiko.SSHException as e:
            self.log(f"Could not establish SFTP connection: {e}", level="ERROR")
            messagebox.showerror("SFTP Error", f"Could not establish SFTP connection: {e}")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during SFTP connection: {e}", level="ERROR")
            messagebox.showerror("SFTP Error", f"An unexpected error occurred: {e}")
            return False

    def _disconnect(self):
        """Trennt die SFTP-Verbindung."""
        if self.sftp_client:
            self.sftp_client.close()
            self.sftp_client = None
        if self.ssh_client:
            self.ssh_client.close()
            self.ssh_client = None
        self.log("SFTP connection closed.", level="INFO")

    def upload_file(self, local_file_path, remote_file_name):
        if not self._connect():
            return False
        
        full_remote_path = os.path.join(self.remote_base_path, remote_file_name).replace("\\", "/") # Für Unix-Pfade
        self.log(f"Uploading '{local_file_path}' to '{full_remote_path}' via SFTP...", level="INFO")
        try:
            # Erstelle Remote-Verzeichnisse, falls sie nicht existieren
            remote_dir = os.path.dirname(full_remote_path)
            if remote_dir and remote_dir != "/":
                try:
                    self.sftp_client.stat(remote_dir) # Prüfen, ob Ordner existiert
                except FileNotFoundError:
                    # Ordner existiert nicht, erstelle ihn rekursiv
                    self._mkdirs_sftp(remote_dir)

            self.sftp_client.put(local_file_path, full_remote_path)
            self.log(f"Successfully uploaded '{local_file_path}' to '{full_remote_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error uploading file to SFTP: {e}", level="ERROR")
            return False
        finally:
            self._disconnect() # Trenne nach jedem Vorgang oder halte persistent für mehrere
            
    def _mkdirs_sftp(self, path):
        """Erstellt rekursiv Verzeichnisse auf dem SFTP-Server."""
        current_path = ''
        for segment in path.split('/'):
            if not segment:
                continue
            current_path = os.path.join(current_path, segment).replace("\\", "/")
            try:
                self.sftp_client.stat(current_path)
            except FileNotFoundError:
                self.log(f"Creating remote directory: {current_path}", level="DEBUG")
                self.sftp_client.mkdir(current_path)


    def download_file(self, remote_file_path, local_destination_path):
        if not self._connect():
            return False
        
        full_remote_path = os.path.join(self.remote_base_path, remote_file_path).replace("\\", "/")
        self.log(f"Downloading '{full_remote_path}' to '{local_destination_path}' via SFTP...", level="INFO")
        try:
            self.sftp_client.get(full_remote_path, local_destination_path)
            self.log(f"Successfully downloaded '{full_remote_path}' to '{local_destination_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error downloading file from SFTP: {e}", level="ERROR")
            return False
        finally:
            self._disconnect()

    def list_files(self, remote_path=""):
        if not self._connect():
            return []
        
        full_remote_path = os.path.join(self.remote_base_path, remote_path).replace("\\", "/")
        self.log(f"Listing files in '{full_remote_path}' via SFTP...", level="INFO")
        files_list = []
        try:
            for entry in self.sftp_client.listdir_attr(full_remote_path):
                # entry.st_mode gibt Dateityp-Informationen
                if paramiko.sftp_client.SFTP_S_ISDIR(entry.st_mode):
                    files_list.append(f"{entry.filename} (folder)")
                else:
                    files_list.append(f"{entry.filename} (file)")
            self.log(f"Listed {len(files_list)} items in '{full_remote_path}'.", level="INFO")
            return files_list
        except Exception as e:
            self.log(f"Error listing files on SFTP: {e}", level="ERROR")
            return []
        finally:
            self._disconnect()

    def delete_file(self, remote_file_path):
        if not self._connect():
            return False
        
        full_remote_path = os.path.join(self.remote_base_path, remote_file_path).replace("\\", "/")
        self.log(f"Deleting '{full_remote_path}' via SFTP...", level="INFO")
        try:
            self.sftp_client.remove(full_remote_path)
            self.log(f"Successfully deleted '{full_remote_path}'.", level="INFO")
            return True
        except Exception as e:
            self.log(f"Error deleting file from SFTP: {e}", level="ERROR")
            return False
        finally:
            self._disconnect()

    def get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        # Hostname
        ttk.Label(frame, text="SFTP Hostname:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        hostname_var = tk.StringVar(value=self.hostname)
        ttk.Entry(frame, textvariable=hostname_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["sftp_host"] = hostname_var

        # Port
        ttk.Label(frame, text="Port:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        port_var = tk.StringVar(value=str(self.port))
        ttk.Entry(frame, textvariable=port_var).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["sftp_port"] = port_var

        # Username
        ttk.Label(frame, text="Username:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        username_var = tk.StringVar(value=self.username)
        ttk.Entry(frame, textvariable=username_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["sftp_user"] = username_var

        # Password
        ttk.Label(frame, text="Password:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        password_var = tk.StringVar(value=self.password)
        ttk.Entry(frame, textvariable=password_var, show="*").grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["sftp_password"] = password_var

        # Remote Base Path
        ttk.Label(frame, text="Remote Base Path:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        remote_base_path_var = tk.StringVar(value=self.remote_base_path)
        ttk.Entry(frame, textvariable=remote_base_path_var).grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["sftp_remote_base_path"] = remote_base_path_var

        frame.columnconfigure(1, weight=1)
        
        return []

    def validate_config(self):
        if not self.hostname or not self.username or not self.password:
            return False, "SFTP Hostname, Username, and Password cannot be empty."
        try:
            port_val = int(self.port)
            if not (1 <= port_val <= 65535):
                return False, "SFTP Port must be a valid number between 1 and 65535."
        except ValueError:
            return False, "SFTP Port must be a valid number."
        
        # Testverbindung
        self.log("Attempting SFTP test connection...", level="INFO")
        if self._connect():
            self.log("SFTP test connection successful.", level="INFO")
            self._disconnect() # Verbindung sofort wieder schließen
            return True, ""
        else:
            return False, "Failed to establish SFTP test connection. Check credentials and server availability."
