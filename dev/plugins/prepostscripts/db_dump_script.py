# /home/philipp/Dokumente/BAckUp_tool_py/plugins/scripts/db_dump_script.py

from plugin_interfaces import PrePostScriptPlugin
import subprocess
import os
import tkinter as tk
from tkinter import ttk

class DBDumpScriptPlugin(PrePostScriptPlugin):
    def __init__(self, config_data=None, log_callback=None):
        super().__init__(config_data, log_callback)
        self.log_callback = log_callback

        # Beispielkonfiguration für die Datenbankverbindung
        self.db_type = self.config_data.get("db_type", "postgresql") # oder "mysql", "sqlite"
        self.db_host = self.config_data.get("db_host", "localhost")
        self.db_port = self.config_data.get("db_port", "") # Kann leer sein
        self.db_name = self.config_data.get("db_name", "")
        self.db_user = self.config_data.get("db_user", "")
        self.db_password = self.config_data.get("db_password", "")
        self.dump_file_path = self.config_data.get("dump_file_path", "/tmp/db_dump.sql")

    def get_name(self):
        return "Database Dump Script"

    def get_description(self): # <-- DIESE METHODE HINZUFÜGEN
        return "Creates a database dump before backup and cleans it up afterwards."

    def run_pre_backup_script(self):
        self.log(f"Starting pre-backup script: Dumping {self.db_type} database '{self.db_name}'...", level="INFO")
        try:
            dump_command = []
            env = os.environ.copy() # Kopiere Umgebungsvariablen

            if self.db_type == "postgresql":
                dump_command = ["pg_dump"]
                if self.db_host:
                    dump_command.extend(["-h", self.db_host])
                if self.db_port:
                    dump_command.extend(["-p", self.db_port])
                if self.db_user:
                    dump_command.extend(["-U", self.db_user])
                dump_command.append(self.db_name)
                dump_command.extend([">", self.dump_file_path]) # Umleitung in Shell

                if self.db_password:
                    env["PGPASSWORD"] = self.db_password # Passwort über Umgebungsvariable

                # pg_dump kann keine direkte Ausgabeumleitung im subprocess.run
                # Daher muss die Shell verwendet werden
                result = subprocess.run(" ".join(dump_command), shell=True, env=env, capture_output=True, text=True, check=True)

            elif self.db_type == "mysql":
                dump_command = ["mysqldump"]
                if self.db_host:
                    dump_command.extend(["-h", self.db_host])
                if self.db_port:
                    dump_command.extend(["-P", self.db_port]) # -P für Port bei MySQL
                if self.db_user:
                    dump_command.extend(["-u", self.db_user])
                if self.db_password:
                    dump_command.extend([f"-p{self.db_password}"]) # Kein Leerzeichen nach -p
                dump_command.append(self.db_name)
                dump_command.extend([">", self.dump_file_path])

                result = subprocess.run(" ".join(dump_command), shell=True, env=env, capture_output=True, text=True, check=True)

            elif self.db_type == "sqlite":
                # SQLite ist einfach eine Datei, hier könnte man sie direkt kopieren
                # Aber wenn es um einen "Dump" geht, ist es oft eine SQL-Export-Datei
                # Hierfür bräuchte man ein SQL-Client-Tool, das SQL exportiert.
                # Dies ist ein Platzhalter, da SQLite-Dumps komplexer sind.
                self.log("SQLite dump not directly supported by this script, please implement custom logic.", level="WARNING")
                return False
            else:
                self.log(f"Unsupported database type: {self.db_type}", level="ERROR")
                return False

            if result.stderr:
                self.log(f"DB Dump Stderr: {result.stderr}", level="WARNING")

            self.log(f"Database dump saved to {self.dump_file_path}", level="INFO")
            # Füge den Dump-Pfad zu den Source-Pfaden des Backup-Jobs hinzu,
            # damit er vom Backup-Tool gesichert wird.
            # ACHTUNG: Das müsste das Job-Objekt selbst tun, dieses Plugin hat keinen direkten Zugriff auf job_data.
            # In der perform_backup-Funktion müsste der dump_file_path in job_data['source_paths']
            # vorübergehend hinzugefügt werden, wenn dieses Plugin verwendet wird.
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"Database dump failed: {e.stderr}", level="ERROR")
            return False
        except FileNotFoundError:
            self.log(f"Database client command for {self.db_type} not found. Please ensure it is installed and in your PATH.", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during database dump: {e}", level="ERROR")
            return False

    def run_post_backup_script(self):
        self.log("Starting post-backup script: Cleaning up database dump file...", level="INFO")
        try:
            if os.path.exists(self.dump_file_path):
                os.remove(self.dump_file_path)
                self.log(f"Removed database dump file: {self.dump_file_path}", level="INFO")
                return True
            else:
                self.log(f"Database dump file not found for cleanup: {self.dump_file_path}", level="WARNING")
                return False
        except Exception as e:
            self.log(f"Error cleaning up database dump file: {e}", level="ERROR")
            return False

    def get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        # DB Type
        ttk.Label(frame, text="Database Type:").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        db_type_var = tk.StringVar(value=self.db_type)
        ttk.Combobox(frame, textvariable=db_type_var, values=["postgresql", "mysql", "sqlite"], state="readonly").grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_type"] = db_type_var

        # DB Host
        ttk.Label(frame, text="Host:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        db_host_var = tk.StringVar(value=self.db_host)
        ttk.Entry(frame, textvariable=db_host_var).grid(row=1, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_host"] = db_host_var

        # DB Port
        ttk.Label(frame, text="Port:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        db_port_var = tk.StringVar(value=self.db_port)
        ttk.Entry(frame, textvariable=db_port_var).grid(row=2, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_port"] = db_port_var

        # DB Name
        ttk.Label(frame, text="Database Name:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        db_name_var = tk.StringVar(value=self.db_name)
        ttk.Entry(frame, textvariable=db_name_var).grid(row=3, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_name"] = db_name_var

        # DB User
        ttk.Label(frame, text="User:").grid(row=4, column=0, padx=5, pady=2, sticky="w")
        db_user_var = tk.StringVar(value=self.db_user)
        ttk.Entry(frame, textvariable=db_user_var).grid(row=4, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_user"] = db_user_var

        # DB Password
        ttk.Label(frame, text="Password:").grid(row=5, column=0, padx=5, pady=2, sticky="w")
        db_password_var = tk.StringVar(value=self.db_password)
        ttk.Entry(frame, textvariable=db_password_var, show="*").grid(row=5, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["db_password"] = db_password_var

        # Dump File Path
        ttk.Label(frame, text="Dump File Path:").grid(row=6, column=0, padx=5, pady=2, sticky="w")
        dump_file_path_var = tk.StringVar(value=self.dump_file_path)
        ttk.Entry(frame, textvariable=dump_file_path_var).grid(row=6, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["dump_file_path"] = dump_file_path_var

        frame.columnconfigure(1, weight=1)
        return []

    def validate_config(self):
        if not self.db_name or not self.db_user:
            return False, "Database Name and User cannot be empty."
        # Weitere Validierungen basierend auf db_type
        if self.db_type == "postgresql":
            try:
                subprocess.run(["pg_dump", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, "pg_dump command not found. Please ensure PostgreSQL client tools are installed and in your PATH."
        elif self.db_type == "mysql":
            try:
                subprocess.run(["mysqldump", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                return False, "mysqldump command not found. Please ensure MySQL client tools are installed and in your PATH."

        return True, ""
