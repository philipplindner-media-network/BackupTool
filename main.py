import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import subprocess
import platform
import sys
import datetime # Für Zeitstempel in Logs

# Importieren Sie Ihre lokalen Module
from backup_logic import perform_backup, perform_restore, get_archive_contents
from config_manager import ConfigManager

class BackupToolGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Backup Tool")
        self.root.geometry("800x750")
        self.root.resizable(False, False) # Fixed size for now

        # Initialize ConfigManager
        self.config_manager = ConfigManager()
        self.app_data_dir = self.config_manager.app_data_dir # Use the directory from config_manager

        # Ensure the application data directory exists for logs etc.
        os.makedirs(self.app_data_dir, exist_ok=True)

        # UI Variables for Backup Tab
        self.source_path_var = tk.StringVar()
        self.destination_path_var = tk.StringVar()
        self.destination_nas_enabled_var = tk.BooleanVar(value=True)
        self.destination_hetzner_enabled_var = tk.BooleanVar(value=False)
        self.include_subfolders_var = tk.BooleanVar(value=True)
        self.compression_level_var = tk.StringVar(value="Default")
        self.archive_format_var = tk.StringVar(value="zip")

        # UI Variables for Restore Tab
        self.restore_path_var = tk.StringVar() # This will be the local/NAS archive path for restore
        self.restore_destination_var = tk.StringVar()
        self.overwrite_restore_var = tk.BooleanVar(value=True)
        self.restore_source_var = tk.StringVar(value="nas_local") # NEW: Default to NAS/Local
        self.hetzner_restore_source_path_var = tk.StringVar() # NEW: For SFTP source path on Hetzner

        # UI Variables for Settings Tab
        self.encryption_enabled_var = tk.BooleanVar(value=False)
        self.encryption_password_var = tk.StringVar()
        self.encryption_password_confirm_var = tk.StringVar()
        self.hetzner_enabled_var = tk.BooleanVar(value=False)
        self.hetzner_host_var = tk.StringVar()
        self.hetzner_port_var = tk.StringVar(value="23")
        self.hetzner_username_var = tk.StringVar()
        self.hetzner_password_var = tk.StringVar()

        # UI Variables for Schedule Tab
        # Retention Policy
        self.retention_enabled_var = tk.BooleanVar(value=False)
        self.retention_type_var = tk.StringVar(value="count")
        self.retention_value_var = tk.StringVar(value="5") # Keep 5 backups or 5 days/weeks/etc.
        self.retention_unit_var = tk.StringVar(value="days") # For age-based retention
        self.retention_nas_var = tk.BooleanVar(value=True)
        self.retention_hetzner_var = tk.BooleanVar(value=False)

        # Cron Scheduling (Linux/macOS)
        self.schedule_frequency_var = tk.StringVar(value="daily")
        self.schedule_time_var = tk.StringVar(value="03:00") # Default to 3 AM
        self.schedule_day_of_week_var = tk.StringVar(value="Mon")
        self.schedule_day_of_month_var = tk.StringVar(value="1")
        self.schedule_cron_string_var = tk.StringVar(value="* * * * *") # Default for custom

        # Windows Task Scheduler
        self.win_schedule_frequency_var = tk.StringVar(value="DAILY")
        self.win_schedule_time_var = tk.StringVar(value="03:00")
        self.win_schedule_day_of_week_var = tk.StringVar(value="MON")
        self.win_schedule_day_of_month_var = tk.StringVar(value="1")


        # Load existing configuration
        self._load_config()

        # Create Notebook (Tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(pady=10, expand=True, fill="both")

        self.create_notebook_tabs()

        # Progress Bar and Log Area
        self.progress_frame = ttk.LabelFrame(root, text="Progress & Log", padding="10")
        self.progress_frame.pack(pady=10, fill="x", padx=5)

        self.progress_bar = ttk.Progressbar(self.progress_frame, orient="horizontal", length=600, mode="indeterminate")
        self.progress_bar.pack(pady=5)

        self.log_text = tk.Text(self.progress_frame, height=10, state="disabled", wrap="word", bg="#333", fg="#eee", font=("Consolas", 9))
        self.log_text.pack(pady=5, fill="both", expand=True)

        # Apply a dark theme (requires ttkthemes)
        try:
            from ttkthemes import ThemedTk
            root.set_theme("black") # or "equilux", "plastik", "arc", "adapta"
            self.log_message("Dark theme applied (ttkthemes).", level="DEBUG")
        except ImportError:
            self.log_message("ttkthemes not found, using default theme.", level="WARNING")

        # IMPORTANT: Call these *after* all tabs and their widgets have been created
        self._toggle_encryption_options()
        self._toggle_hetzner_options()
        self._toggle_destination_options() # Also ensure backup tab's destination options are updated
        self._toggle_retention_options() # Ensure retention policy options are correctly displayed
        self._on_retention_type_change(self.retention_type_var.get()) # To set initial unit visibility

        # Ensure correct schedule options are shown based on loaded config
        if platform.system() in ["Linux", "Darwin"]:
            self._on_schedule_frequency_change(self.schedule_frequency_var.get())
        elif platform.system() == "Windows":
            self._on_win_schedule_frequency_change(self.win_schedule_frequency_var.get())


    def _load_config(self):
        config_data = self.config_manager.load_config()
        if config_data:
            # Backup Tab
            self.source_path_var.set(config_data.get('source_path', ''))
            self.destination_path_var.set(config_data.get('destination_path', ''))
            self.destination_nas_enabled_var.set(config_data.get('destination_nas_enabled', True))
            self.destination_hetzner_enabled_var.set(config_data.get('destination_hetzner_enabled', False))
            self.include_subfolders_var.set(config_data.get('include_subfolders', True))
            self.compression_level_var.set(config_data.get('compression_level', 'Default'))
            self.archive_format_var.set(config_data.get('archive_format', 'zip'))

            # Restore Tab
            self.restore_path_var.set(config_data.get('restore_path', '')) # Local/NAS restore source path
            self.restore_destination_var.set(config_data.get('restore_destination', ''))
            self.overwrite_restore_var.set(config_data.get('overwrite_restore', True))
            self.restore_source_var.set(config_data.get('restore_source', 'nas_local')) # NEW: Restore source type
            self.hetzner_restore_source_path_var.set(config_data.get('hetzner_restore_source_path', '')) # NEW: Hetzner SFTP restore source path


            # Settings Tab
            self.encryption_enabled_var.set(config_data.get('encryption_enabled', False))
            # Decrypt password for display if it exists and encryption is enabled for internal use, but we won't set it to the entry field for security
            # self.encryption_password_var.set(self.config_manager.decrypt_data(config_data.get('encryption_password', '')))
            self.hetzner_enabled_var.set(config_data.get('hetzner_enabled', False))
            self.hetzner_host_var.set(config_data.get('hetzner_host', ''))
            self.hetzner_port_var.set(config_data.get('hetzner_port', '23'))
            self.hetzner_username_var.set(config_data.get('hetzner_username', ''))
            # Hetzner password is not loaded into var for security. It's retrieved directly from config_manager when needed.

            # Schedule Tab (Retention)
            self.retention_enabled_var.set(config_data.get('retention_enabled', False))
            self.retention_type_var.set(config_data.get('retention_type', 'count'))
            self.retention_value_var.set(config_data.get('retention_value', '5'))
            self.retention_unit_var.set(config_data.get('retention_unit', 'days'))
            self.retention_nas_var.set(config_data.get('retention_nas', True))
            self.retention_hetzner_var.set(config_data.get('retention_hetzner', False))

            # Schedule Tab (Scheduling)
            self.schedule_frequency_var.set(config_data.get('schedule_frequency', 'daily'))
            self.schedule_time_var.set(config_data.get('schedule_time', '03:00'))
            self.schedule_day_of_week_var.set(config_data.get('schedule_day_of_week', 'Mon'))
            self.schedule_day_of_month_var.set(config_data.get('schedule_day_of_month', '1'))
            self.schedule_cron_string_var.set(config_data.get('schedule_cron_string', '* * * * *'))

            self.win_schedule_frequency_var.set(config_data.get('win_schedule_frequency', 'DAILY'))
            self.win_schedule_time_var.set(config_data.get('win_schedule_time', '03:00'))
            self.win_schedule_day_of_week_var.set(config_data.get('win_schedule_day_of_week', 'MON'))
            self.win_schedule_day_of_month_var.set(config_data.get('win_schedule_day_of_month', '1'))

            self.log_message("Configuration loaded.", level="INFO")
        else:
            self.log_message("No existing configuration found. Using default settings.", level="INFO")

    def _save_config(self):
        config_data = {
            # Backup Tab
            'source_path': self.source_path_var.get(),
            'destination_path': self.destination_path_var.get(),
            'destination_nas_enabled': self.destination_nas_enabled_var.get(),
            'destination_hetzner_enabled': self.destination_hetzner_enabled_var.get(),
            'include_subfolders': self.include_subfolders_var.get(),
            'compression_level': self.compression_level_var.get(),
            'archive_format': self.archive_format_var.get(),

            # Restore Tab
            'restore_path': self.restore_path_var.get(),
            'restore_destination': self.restore_destination_var.get(),
            'overwrite_restore': self.overwrite_restore_var.get(),
            'restore_source': self.restore_source_var.get(), # NEW
            'hetzner_restore_source_path': self.hetzner_restore_source_path_var.get(), # NEW

            # Settings Tab
            'encryption_enabled': self.encryption_enabled_var.get(),
            # Password handled directly by config_manager's save_config for encryption
            'hetzner_enabled': self.hetzner_enabled_var.get(),
            'hetzner_host': self.hetzner_host_var.get(),
            'hetzner_port': self.hetzner_port_var.get(),
            'hetzner_username': self.hetzner_username_var.get(),

            # Schedule Tab (Retention)
            'retention_enabled': self.retention_enabled_var.get(),
            'retention_type': self.retention_type_var.get(),
            'retention_value': self.retention_value_var.get(),
            'retention_unit': self.retention_unit_var.get(),
            'retention_nas': self.retention_nas_var.get(),
            'retention_hetzner': self.retention_hetzner_var.get(),

            # Schedule Tab (Scheduling)
            'schedule_frequency': self.schedule_frequency_var.get(),
            'schedule_time': self.schedule_time_var.get(),
            'schedule_day_of_week': self.schedule_day_of_week_var.get(),
            'schedule_day_of_month': self.schedule_day_of_month_var.get(),
            'schedule_cron_string': self.schedule_cron_string_var.get(),

            'win_schedule_frequency': self.win_schedule_frequency_var.get(),
            'win_schedule_time': self.win_schedule_time_var.get(),
            'win_schedule_day_of_week': self.win_schedule_day_of_week_var.get(),
            'win_schedule_day_of_month': self.win_schedule_day_of_month_var.get(),
        }

        # Pass sensitive data directly from UI variables for saving/encryption
        success = self.config_manager.save_config(
            config_data,
            encryption_password=self.encryption_password_var.get(),
            hetzner_password=self.hetzner_password_var.get()
        )
        if success:
            self.log_message("Configuration saved successfully.", level="INFO")
            # Clear password fields after saving for security
            self.encryption_password_var.set("")
            self.encryption_password_confirm_var.set("")
            self.hetzner_password_var.set("")
        else:
            self.log_message("Failed to save configuration.", level="ERROR")


    def create_notebook_tabs(self):
        self.create_backup_tab()
        self.create_restore_tab()
        self.create_settings_tab()
        self.create_schedule_tab() # This must be called before _toggle_hetzner_options if it references widgets in it

    # ====================================================================
    # BACKUP TAB
    # ====================================================================
    def create_backup_tab(self):
        self.backup_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.backup_frame, text="Backup")

        # Source Path
        source_frame = ttk.LabelFrame(self.backup_frame, text="Source Folder", padding="10")
        source_frame.pack(pady=10, fill="x", padx=5)

        ttk.Label(source_frame, text="Path:").grid(row=0, column=0, sticky="w", pady=5)
        source_entry = ttk.Entry(source_frame, textvariable=self.source_path_var, width=50)
        source_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        browse_source_button = ttk.Button(source_frame, text="Browse", command=self.browse_source_path)
        browse_source_button.grid(row=0, column=2, sticky="e", pady=2)

        ttk.Checkbutton(source_frame, text="Include Subfolders", variable=self.include_subfolders_var).grid(row=1, column=0, columnspan=3, sticky="w", pady=5)


        # Destination Paths
        destination_frame = ttk.LabelFrame(self.backup_frame, text="Destination Options", padding="10")
        destination_frame.pack(pady=10, fill="x", padx=5)

        ttk.Label(destination_frame, text="Backup to:").grid(row=0, column=0, sticky="w", pady=5)
        self.destination_nas_checkbox = ttk.Checkbutton(destination_frame, text="NAS/Local Path", variable=self.destination_nas_enabled_var, command=self._toggle_destination_options)
        self.destination_nas_checkbox.grid(row=1, column=0, sticky="w", padx=5, pady=2)
        self.destination_hetzner_checkbox = ttk.Checkbutton(destination_frame, text="Hetzner Storage Box (SFTP)", variable=self.destination_hetzner_enabled_var, command=self._toggle_destination_options)
        self.destination_hetzner_checkbox.grid(row=1, column=1, sticky="w", padx=5, pady=2)

        self.nas_path_label = ttk.Label(destination_frame, text="NAS/Local Destination Path:")
        self.nas_path_label.grid(row=2, column=0, sticky="w", pady=5)
        self.destination_entry = ttk.Entry(destination_frame, textvariable=self.destination_path_var, width=50)
        self.destination_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)
        self.browse_destination_button = ttk.Button(destination_frame, text="Browse", command=self.browse_destination_path)
        self.browse_destination_button.grid(row=2, column=2, sticky="e", pady=2)


        # Compression & Archive Format
        compression_frame = ttk.LabelFrame(self.backup_frame, text="Compression & Format", padding="10")
        compression_frame.pack(pady=10, fill="x", padx=5)

        ttk.Label(compression_frame, text="Compression Level:").grid(row=0, column=0, sticky="w", pady=5)
        compression_menu = ttk.OptionMenu(compression_frame, self.compression_level_var, self.compression_level_var.get(), "None", "Fast", "Default", "Best")
        compression_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(compression_frame, text="Archive Format:").grid(row=1, column=0, sticky="w", pady=5)
        format_menu = ttk.OptionMenu(compression_frame, self.archive_format_var, self.archive_format_var.get(), "zip", "tar.gz")
        format_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=2)


        # Backup Button
        backup_button = ttk.Button(self.backup_frame, text="Start Backup", command=self.start_backup)
        backup_button.pack(pady=20)

        # Initial call to set correct visibility based on loaded config
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._toggle_destination_options()

    def browse_source_path(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.source_path_var.set(folder_selected)

    def browse_destination_path(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.destination_path_var.set(folder_selected)

    def _toggle_destination_options(self):
        if self.destination_nas_enabled_var.get():
            self.nas_path_label.grid()
            self.destination_entry.grid()
            self.browse_destination_button.grid()
        else:
            self.nas_path_label.grid_remove()
            self.destination_entry.grid_remove()
            self.browse_destination_button.grid_remove()
        
        # We don't hide Hetzner options here, as they are in the settings tab
        # but we might want to grey out the button if Hetzner is not configured

        self.backup_frame.update_idletasks() # Refresh layout

    def start_backup(self):
        source_path = self.source_path_var.get()
        destination_path = self.destination_path_var.get()
        dest_nas_enabled = self.destination_nas_enabled_var.get()
        dest_hetzner_enabled = self.destination_hetzner_enabled_var.get()
        include_subfolders = self.include_subfolders_var.get()
        compression_level = self.compression_level_var.get()
        archive_format = self.archive_format_var.get()

        if not source_path or not os.path.isdir(source_path):
            messagebox.showerror("Error", "Please select a valid source folder.")
            return

        if not dest_nas_enabled and not dest_hetzner_enabled:
            messagebox.showerror("Error", "Please select at least one backup destination (NAS/Local or Hetzner Storage Box).")
            return
        
        if dest_nas_enabled and (not destination_path or not os.path.isdir(destination_path)):
            messagebox.showerror("Error", "Please select a valid NAS/Local destination folder.")
            return
        
        if dest_hetzner_enabled:
            config = self.config_manager.get_config()
            if not config.get('hetzner_host') or not config.get('hetzner_username') or not config.get('hetzner_password'):
                messagebox.showerror("Error", "Hetzner Storage Box is enabled as a destination, but credentials are not configured in the 'Settings' tab. Please configure them first.")
                return

        self.progress_bar.start()
        self.log_message("Starting backup process...", level="INFO")

        # Pass self.config_manager to the backup thread to access encrypted credentials
        threading.Thread(target=self._backup_thread, args=(source_path, destination_path, dest_nas_enabled, dest_hetzner_enabled,
                                                          include_subfolders, compression_level, archive_format,
                                                          self.config_manager)).start()

    def _backup_thread(self, source_path, destination_path, dest_nas_enabled, dest_hetzner_enabled,
                       include_subfolders, compression_level, archive_format, config_manager_instance):
        try:
            # Perform backup using the backup_logic
            success, message = perform_backup(
                source_path, destination_path, dest_nas_enabled, dest_hetzner_enabled,
                include_subfolders, compression_level, archive_format,
                config_manager_instance, # Pass the config manager instance
                self.log_message # Pass the logging callback
            )

            self.root.after(0, self.progress_bar.stop)
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Backup Complete", message))
                self.log_message(message, level="INFO")
            else:
                self.root.after(0, lambda: messagebox.showerror("Backup Failed", message))
                self.log_message(message, level="ERROR")
        except Exception as e:
            self.root.after(0, self.progress_bar.stop)
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred during backup: {e}"))
            self.log_message(f"An unexpected error occurred during backup: {e}", level="ERROR")

    # ====================================================================
    # RESTORE TAB
    # ====================================================================
    def create_restore_tab(self):
        self.restore_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.restore_frame, text="Restore")

        # NEW: Restore Source Selection
        restore_source_selection_frame = ttk.LabelFrame(self.restore_frame, text="Select Restore Source", padding="10")
        restore_source_selection_frame.pack(pady=10, fill="x", padx=5)

        ttk.Radiobutton(restore_source_selection_frame, text="From Local/NAS Path", variable=self.restore_source_var, value="nas_local", command=self._toggle_restore_source_options).pack(anchor="w", pady=2)
        ttk.Radiobutton(restore_source_selection_frame, text="From Hetzner Storage Box (SFTP)", variable=self.restore_source_var, value="hetzner_sftp", command=self._toggle_restore_source_options).pack(anchor="w", pady=2)

        # Restore Source Path Input (Adjusted)
        self.restore_source_path_frame = ttk.LabelFrame(self.restore_frame, text="Source Archive Path", padding="10")
        self.restore_source_path_frame.pack(pady=10, fill="x", padx=5)

        # Path for Local/NAS Source (existing, just adjusted label)
        self.nas_restore_source_path_label = ttk.Label(self.restore_source_path_frame, text="Local/NAS Archive Path:")
        self.nas_restore_source_path_label.grid(row=0, column=0, sticky="w", pady=5)
        self.restore_path_entry = ttk.Entry(self.restore_source_path_frame, textvariable=self.restore_path_var, width=50)
        self.restore_path_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.browse_restore_path_button = ttk.Button(self.restore_source_path_frame, text="Browse", command=self.browse_restore_path)
        self.browse_restore_path_button.grid(row=0, column=2, sticky="e", pady=2)

        # NEW: Path for Hetzner SFTP Source (initially hidden)
        self.hetzner_restore_source_path_label = ttk.Label(self.restore_source_path_frame, text="Hetzner SFTP Archive Path (e.g., /backups/my_archive.zip):")
        self.hetzner_restore_source_path_label.grid(row=1, column=0, sticky="w", pady=5)
        self.hetzner_restore_source_path_entry = ttk.Entry(self.restore_source_path_frame, textvariable=self.hetzner_restore_source_path_var, width=50)
        self.hetzner_restore_source_path_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        # No browse button for SFTP path, as it's remote

        # Initially hide Hetzner specific options (will be shown by _toggle_restore_source_options)
        self.hetzner_restore_source_path_label.grid_remove()
        self.hetzner_restore_source_path_entry.grid_remove()

        # Restore Destination Path Input
        restore_destination_frame = ttk.LabelFrame(self.restore_frame, text="Restore Destination Path", padding="10")
        restore_destination_frame.pack(pady=10, fill="x", padx=5)

        ttk.Label(restore_destination_frame, text="Destination Folder:").grid(row=0, column=0, sticky="w", pady=5)
        self.restore_destination_entry = ttk.Entry(restore_destination_frame, textvariable=self.restore_destination_var, width=50)
        self.restore_destination_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)
        self.browse_restore_destination_button = ttk.Button(restore_destination_frame, text="Browse", command=self.browse_restore_destination)
        self.browse_restore_destination_button.grid(row=0, column=2, sticky="e", pady=2)


        # Restore Options and Button
        restore_options_frame = ttk.LabelFrame(self.restore_frame, text="Restore Options", padding="10")
        restore_options_frame.pack(pady=10, fill="x", padx=5)

        self.overwrite_restore_var = tk.BooleanVar(value=True) # Default to overwrite
        ttk.Checkbutton(restore_options_frame, text="Overwrite existing files", variable=self.overwrite_restore_var).pack(anchor="w")

        restore_button = ttk.Button(self.restore_frame, text="Start Restore", command=self.restore_backup)
        restore_button.pack(pady=10)

        # Initial call to set correct visibility based on default value or loaded config
        self._toggle_restore_source_options()


    def _toggle_restore_source_options(self):
        selected_source = self.restore_source_var.get()
        if selected_source == "nas_local":
            self.nas_restore_source_path_label.grid()
            self.restore_path_entry.grid()
            self.browse_restore_path_button.grid()
            self.hetzner_restore_source_path_label.grid_remove()
            self.hetzner_restore_source_path_entry.grid_remove()
            self.restore_source_path_frame.config(text="Local/NAS Source Archive Path")
        elif selected_source == "hetzner_sftp":
            self.nas_restore_source_path_label.grid_remove()
            self.restore_path_entry.grid_remove()
            self.browse_restore_path_button.grid_remove()
            self.hetzner_restore_source_path_label.grid()
            self.hetzner_restore_source_path_entry.grid()
            self.restore_source_path_frame.config(text="Hetzner SFTP Source Archive Path")
        self.restore_source_path_frame.update_idletasks() # Refresh layout


    def browse_restore_path(self):
        file_selected = filedialog.askopenfilename(
            filetypes=[("Archive Files", "*.zip *.tar.gz *.tgz *.gz"), ("All Files", "*.*")]
        )
        if file_selected:
            self.restore_path_var.set(file_selected)

    def browse_restore_destination(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.restore_destination_var.set(folder_selected)

    def restore_backup(self):
        restore_destination = self.restore_destination_var.get()
        overwrite_existing = self.overwrite_restore_var.get()
        selected_source = self.restore_source_var.get() # Get selected source

        if not restore_destination:
            messagebox.showerror("Error", "Please select a restore destination folder.")
            return
        if not os.path.isdir(restore_destination):
            try:
                os.makedirs(restore_destination)
            except Exception as e:
                messagebox.showerror("Error", f"Invalid restore destination path or failed to create: {e}")
                return

        # Determine source path and credentials based on selection
        source_path = ""
        sftp_config = {}
        
        if selected_source == "nas_local":
            source_path = self.restore_path_var.get()
            if not source_path:
                messagebox.showerror("Error", "Please select a local/NAS archive path to restore from.")
                return
            if not os.path.exists(source_path):
                messagebox.showerror("Error", f"Source archive path does not exist: {source_path}")
                return
            if not source_path.lower().endswith(('.zip', '.tar.gz', '.tgz', '.gz')):
                messagebox.showwarning("Warning", "The selected file does not appear to be a common archive type (.zip, .tar.gz, etc.). Proceeding anyway.")

        elif selected_source == "hetzner_sftp":
            source_path = self.hetzner_restore_source_path_var.get().strip()
            if not source_path:
                messagebox.showerror("Error", "Please enter the SFTP archive path on the Hetzner Storage Box.")
                return
            
            # Retrieve Hetzner credentials from config manager
            config = self.config_manager.get_config()
            if not config.get('hetzner_host') or not config.get('hetzner_username') or not config.get('hetzner_password'):
                messagebox.showerror("Error", "Hetzner Storage Box credentials are not configured in the 'Settings' tab. Please configure them first.")
                return
            
            sftp_config = {
                'host': config['hetzner_host'],
                'port': int(config.get('hetzner_port', 23)), # Use default 23 if not set
                'username': config['hetzner_username'],
                'password': self.config_manager.decrypt_data(config['hetzner_password'])
            }

            if not source_path.startswith('/'):
                messagebox.showwarning("Warning", "SFTP path should usually start with '/'. Please check the path.")

        else:
            messagebox.showerror("Error", "Invalid restore source selected.")
            return

        # Start restore in a separate thread
        self.progress_bar.start()
        self.log_message("Starting restore process...", level="INFO")
        threading.Thread(target=self._restore_thread, args=(selected_source, source_path, restore_destination, overwrite_existing, sftp_config)).start()

    def _restore_thread(self, selected_source, source_path, restore_destination, overwrite_existing, sftp_config):
        try:
            # Call perform_restore from backup_logic with all necessary parameters
            success, message = perform_restore(selected_source, source_path, restore_destination, overwrite_existing, sftp_config, self.log_message)
            
            self.root.after(0, self.progress_bar.stop)
            if success:
                self.root.after(0, lambda: messagebox.showinfo("Restore Complete", message))
                self.log_message(message, level="INFO")
            else:
                self.root.after(0, lambda: messagebox.showerror("Restore Failed", message))
                self.log_message(message, level="ERROR")
        except Exception as e:
            self.root.after(0, self.progress_bar.stop)
            self.root.after(0, lambda: messagebox.showerror("Error", f"An unexpected error occurred during restore: {e}"))
            self.log_message(f"An unexpected error occurred during restore: {e}", level="ERROR")

    # ====================================================================
    # SETTINGS TAB
    # ====================================================================
    def create_settings_tab(self):
        self.settings_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.settings_frame, text="Settings")

        # Encryption Settings
        encryption_frame = ttk.LabelFrame(self.settings_frame, text="Encryption Settings", padding="10")
        encryption_frame.pack(pady=10, fill="x", padx=5)

        self.encryption_enabled_checkbox = ttk.Checkbutton(encryption_frame, text="Enable Encryption for Config File", variable=self.encryption_enabled_var, command=self._toggle_encryption_options)
        self.encryption_enabled_checkbox.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        self.encryption_password_label = ttk.Label(encryption_frame, text="Encryption Password:")
        self.encryption_password_label.grid(row=1, column=0, sticky="w", pady=5)
        self.encryption_password_entry = ttk.Entry(encryption_frame, textvariable=self.encryption_password_var, show="*", width=30)
        self.encryption_password_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        self.encryption_password_confirm_label = ttk.Label(encryption_frame, text="Confirm Password:")
        self.encryption_password_confirm_label.grid(row=2, column=0, sticky="w", pady=5)
        self.encryption_password_confirm_entry = ttk.Entry(encryption_frame, textvariable=self.encryption_password_confirm_var, show="*", width=30)
        self.encryption_password_confirm_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # Hetzner Storage Box Settings
        hetzner_frame = ttk.LabelFrame(self.settings_frame, text="Hetzner Storage Box (SFTP) Settings", padding="10")
        hetzner_frame.pack(pady=10, fill="x", padx=5)

        self.hetzner_enabled_checkbox = ttk.Checkbutton(hetzner_frame, text="Enable Hetzner Storage Box Integration", variable=self.hetzner_enabled_var, command=self._toggle_hetzner_options)
        self.hetzner_enabled_checkbox.grid(row=0, column=0, columnspan=2, sticky="w", pady=5)

        ttk.Label(hetzner_frame, text="Host:").grid(row=1, column=0, sticky="w", pady=5)
        self.hetzner_host_entry = ttk.Entry(hetzner_frame, textvariable=self.hetzner_host_var, width=30)
        self.hetzner_host_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(hetzner_frame, text="Port (default 23):").grid(row=2, column=0, sticky="w", pady=5)
        self.hetzner_port_entry = ttk.Entry(hetzner_frame, textvariable=self.hetzner_port_var, width=10)
        self.hetzner_port_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(hetzner_frame, text="Username:").grid(row=3, column=0, sticky="w", pady=5)
        self.hetzner_username_entry = ttk.Entry(hetzner_frame, textvariable=self.hetzner_username_var, width=30)
        self.hetzner_username_entry.grid(row=3, column=1, sticky="ew", padx=5, pady=2)

        ttk.Label(hetzner_frame, text="Password:").grid(row=4, column=0, sticky="w", pady=5)
        self.hetzner_password_entry = ttk.Entry(hetzner_frame, textvariable=self.hetzner_password_var, show="*", width=30)
        self.hetzner_password_entry.grid(row=4, column=1, sticky="ew", padx=5, pady=2)

        # Save Settings Button
        save_button = ttk.Button(self.settings_frame, text="Save Settings", command=self.save_settings)
        save_button.pack(pady=20)

        # Initial call to set correct visibility for encryption and Hetzner options
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._toggle_encryption_options()
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._toggle_hetzner_options()

    def _toggle_encryption_options(self):
        state = "normal" if self.encryption_enabled_var.get() else "disabled"
        self.encryption_password_label.config(state=state)
        self.encryption_password_entry.config(state=state)
        self.encryption_password_confirm_label.config(state=state)
        self.encryption_password_confirm_entry.config(state=state)

    def _toggle_hetzner_options(self):
        state = "normal" if self.hetzner_enabled_var.get() else "disabled"
        self.hetzner_host_entry.config(state=state)
        self.hetzner_port_entry.config(state=state)
        self.hetzner_username_entry.config(state=state)
        self.hetzner_password_entry.config(state=state)

        # Also, if Hetzner is disabled in settings, disable it in backup tab
        if not self.hetzner_enabled_var.get():
            self.destination_hetzner_enabled_var.set(False)
            self._toggle_destination_options() # Update backup tab GUI
        
        # Enable/disable Hetzner retention checkbox - THIS IS THE PROBLEM LINE if called too early
        # Ensure self.retention_hetzner_checkbox exists before configuring it
        if hasattr(self, 'retention_hetzner_checkbox'):
            self.retention_hetzner_checkbox.config(state=state)
            if not self.hetzner_enabled_var.get():
                self.retention_hetzner_var.set(False) # Uncheck it if Hetzner is disabled globally


    def save_settings(self):
        # Validate encryption passwords if enabled
        if self.encryption_enabled_var.get():
            if not self.encryption_password_var.get():
                messagebox.showerror("Input Error", "Encryption password cannot be empty.")
                return
            if self.encryption_password_var.get() != self.encryption_password_confirm_var.get():
                messagebox.showerror("Input Error", "Encryption passwords do not match.")
                return

        # Validate Hetzner settings if enabled
        if self.hetzner_enabled_var.get():
            if not self.hetzner_host_var.get() or not self.hetzner_username_var.get():
                messagebox.showerror("Input Error", "Hetzner Host and Username cannot be empty if enabled.")
                return
            try:
                port = int(self.hetzner_port_var.get())
                if not (1 <= port <= 65535):
                    raise ValueError
            except ValueError:
                messagebox.showerror("Input Error", "Hetzner Port must be a valid number between 1 and 65535.")
                return
            if not self.hetzner_password_var.get() and not self.config_manager.get_config().get('hetzner_password'):
                messagebox.showwarning("Warning", "Hetzner Password is empty. If this is a new setup, it will be saved as empty. If you are updating, the old password will remain if not changed.")


        self._save_config() # This handles encryption and stores passwords securely
        messagebox.showinfo("Settings Saved", "Your settings have been saved successfully.")


    # ====================================================================
    # SCHEDULE TAB
    # ====================================================================
    def create_schedule_tab(self):
        self.schedule_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.schedule_frame, text="Schedule")

        # Retention Policy (Bleibt bestehen)
        self.retention_frame = ttk.LabelFrame(self.schedule_frame, text="Retention Policy Settings", padding="10")
        self.retention_frame.pack(pady=10, fill="x", padx=5)

        self.retention_enabled_checkbox = ttk.Checkbutton(self.retention_frame, text="Enable Retention Policy", variable=self.retention_enabled_var)
        self.retention_enabled_checkbox.grid(row=0, column=0, columnspan=3, sticky="w", pady=5)
        self.retention_enabled_checkbox.bind("<ButtonRelease-1>", lambda event: self._toggle_retention_options()) # Bind to update visibility

        ttk.Label(self.retention_frame, text="Retention Type:").grid(row=1, column=0, sticky="w", pady=5)
        self.retention_type_menu = ttk.OptionMenu(self.retention_frame, self.retention_type_var, self.retention_type_var.get(), "count", "age", command=self._on_retention_type_change)
        self.retention_type_menu.grid(row=2, column=0, sticky="w", padx=5, pady=2)

        ttk.Label(self.retention_frame, text="Value:").grid(row=1, column=1, sticky="w", pady=5)
        self.retention_value_entry = ttk.Entry(self.retention_frame, textvariable=self.retention_value_var, width=10)
        self.retention_value_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

        ttk.Label(self.retention_frame, text="Unit (for 'Age'):").grid(row=1, column=2, sticky="w", pady=5)
        self.retention_unit_menu = ttk.OptionMenu(self.retention_frame, self.retention_unit_var, self.retention_unit_var.get(), "days", "weeks", "months", "years")
        self.retention_unit_menu.grid(row=2, column=2, sticky="w", padx=5, pady=2)

        ttk.Label(self.retention_frame, text="Apply to Destinations:").grid(row=3, column=0, sticky="w", pady=5)
        self.retention_nas_checkbox = ttk.Checkbutton(self.retention_frame, text="NAS/Local", variable=self.retention_nas_var)
        self.retention_nas_checkbox.grid(row=4, column=0, sticky="w", padx=5, pady=2)
        # THIS IS THE CHECKBOX THAT WAS NOT YET CREATED WHEN _toggle_hetzner_options WAS CALLED
        self.retention_hetzner_checkbox = ttk.Checkbutton(self.retention_frame, text="Hetzner Storage Box", variable=self.retention_hetzner_var)
        self.retention_hetzner_checkbox.grid(row=4, column=1, sticky="w", padx=5, pady=2)

        # NEW: Scheduling Section
        self.schedule_section_frame = ttk.LabelFrame(self.schedule_frame, text="Automated Backup Scheduling", padding="10")
        self.schedule_section_frame.pack(pady=15, fill="x", padx=5)

        # Only show Cron options on Linux/macOS
        if platform.system() in ["Linux", "Darwin"]: # Darwin is macOS
            ttk.Label(self.schedule_section_frame, text="Schedule Type: Cron (Linux/macOS)").grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

            ttk.Label(self.schedule_section_frame, text="Frequency:").grid(row=1, column=0, sticky="w", pady=5)
            self.schedule_frequency_menu = ttk.OptionMenu(self.schedule_section_frame, self.schedule_frequency_var, self.schedule_frequency_var.get(),
                                                            "daily", "weekly", "monthly", "custom", command=self._on_schedule_frequency_change)
            self.schedule_frequency_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

            ttk.Label(self.schedule_section_frame, text="Time (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
            self.schedule_time_entry = ttk.Entry(self.schedule_section_frame, textvariable=self.schedule_time_var, width=10)
            self.schedule_time_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

            self.schedule_day_of_week_label = ttk.Label(self.schedule_section_frame, text="Day of Week (Mon-Sun):")
            self.schedule_day_of_week_label.grid(row=3, column=0, sticky="w", pady=5)
            self.schedule_day_of_week_var = tk.StringVar(value="Mon")
            self.schedule_day_of_week_menu = ttk.OptionMenu(self.schedule_section_frame, self.schedule_day_of_week_var, self.schedule_day_of_week_var.get(),
                                                              "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
            self.schedule_day_of_week_menu.grid(row=3, column=1, sticky="w", padx=5, pady=2)
            self.schedule_day_of_week_label.grid_remove() # Hide by default
            self.schedule_day_of_week_menu.grid_remove() # Hide by default

            self.schedule_day_of_month_label = ttk.Label(self.schedule_section_frame, text="Day of Month (1-31):")
            self.schedule_day_of_month_label.grid(row=4, column=0, sticky="w", pady=5)
            self.schedule_day_of_month_var = tk.StringVar(value="1")
            self.schedule_day_of_month_entry = ttk.Entry(self.schedule_section_frame, textvariable=self.schedule_day_of_month_var, width=5)
            self.schedule_day_of_month_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
            self.schedule_day_of_month_label.grid_remove() # Hide by default
            self.schedule_day_of_month_entry.grid_remove() # Hide by default

            self.schedule_cron_string_label = ttk.Label(self.schedule_section_frame, text="Custom Cron String:")
            self.schedule_cron_string_label.grid(row=5, column=0, sticky="w", pady=5)
            self.schedule_cron_string_entry = ttk.Entry(self.schedule_section_frame, textvariable=self.schedule_cron_string_var, width=30)
            self.schedule_cron_string_entry.grid(row=5, column=1, columnspan=2, sticky="ew", padx=5, pady=2)
            self.schedule_cron_string_label.grid_remove() # Hide by default
            self.schedule_cron_string_entry.grid_remove() # Hide by default

            self.create_schedule_button = ttk.Button(self.schedule_section_frame, text="Create/Update Cron Job", command=self.create_update_cron_job)
            self.create_schedule_button.grid(row=6, column=0, sticky="w", pady=10)

            self.remove_schedule_button = ttk.Button(self.schedule_section_frame, text="Remove Cron Job", command=self.remove_cron_job)
            self.remove_schedule_button.grid(row=6, column=1, sticky="w", pady=10)

            self.view_schedule_button = ttk.Button(self.schedule_section_frame, text="View My Cron Jobs", command=self.view_my_cron_jobs)
            self.view_schedule_button.grid(row=6, column=2, sticky="w", pady=10)

            # Initial call to set correct visibility for schedule options
            # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._on_schedule_frequency_change(self.schedule_frequency_var.get())

        elif platform.system() == "Windows":
            ttk.Label(self.schedule_section_frame, text="Schedule Type: Windows Task Scheduler").grid(row=0, column=0, columnspan=3, sticky="w", pady=5)

            ttk.Label(self.schedule_section_frame, text="Frequency:").grid(row=1, column=0, sticky="w", pady=5)
            self.win_schedule_frequency_menu = ttk.OptionMenu(self.schedule_section_frame, self.win_schedule_frequency_var, self.win_schedule_frequency_var.get(),
                                                            "DAILY", "WEEKLY", "MONTHLY", command=self._on_win_schedule_frequency_change)
            self.win_schedule_frequency_menu.grid(row=1, column=1, sticky="ew", padx=5, pady=2)

            ttk.Label(self.schedule_section_frame, text="Time (HH:MM):").grid(row=2, column=0, sticky="w", pady=5)
            self.win_schedule_time_entry = ttk.Entry(self.schedule_section_frame, textvariable=self.win_schedule_time_var, width=10)
            self.win_schedule_time_entry.grid(row=2, column=1, sticky="w", padx=5, pady=2)

            self.win_schedule_day_of_week_label = ttk.Label(self.schedule_section_frame, text="Day of Week (Mon-Sun):")
            self.win_schedule_day_of_week_label.grid(row=3, column=0, sticky="w", pady=5)
            self.win_schedule_day_of_week_var = tk.StringVar(value="MON")
            self.win_schedule_day_of_week_menu = ttk.OptionMenu(self.schedule_section_frame, self.win_schedule_day_of_week_var, self.win_schedule_day_of_week_var.get(),
                                                              "MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
            self.win_schedule_day_of_week_menu.grid(row=3, column=1, sticky="w", padx=5, pady=2)
            self.win_schedule_day_of_week_label.grid_remove() # Hide by default
            self.win_schedule_day_of_week_menu.grid_remove() # Hide by default

            self.win_schedule_day_of_month_label = ttk.Label(self.schedule_section_frame, text="Day of Month (1-31):")
            self.win_schedule_day_of_month_label.grid(row=4, column=0, sticky="w", pady=5)
            self.win_schedule_day_of_month_var = tk.StringVar(value="1")
            self.win_schedule_day_of_month_entry = ttk.Entry(self.schedule_section_frame, textvariable=self.win_schedule_day_of_month_var, width=5)
            self.win_schedule_day_of_month_entry.grid(row=4, column=1, sticky="w", padx=5, pady=2)
            self.win_schedule_day_of_month_label.grid_remove() # Hide by default
            self.win_schedule_day_of_month_entry.grid_remove() # Hide by default

            self.create_win_schedule_button = ttk.Button(self.schedule_section_frame, text="Create/Update Scheduled Task", command=self.create_update_win_task)
            self.create_win_schedule_button.grid(row=5, column=0, sticky="w", pady=10)

            self.remove_win_schedule_button = ttk.Button(self.schedule_section_frame, text="Remove Scheduled Task", command=self.remove_win_task)
            self.remove_win_schedule_button.grid(row=5, column=1, sticky="w", pady=10)

            self.view_win_schedule_button = ttk.Button(self.schedule_section_frame, text="View My Scheduled Tasks", command=self.view_my_win_tasks)
            self.view_win_schedule_button.grid(row=5, column=2, sticky="w", pady=10)
            
            # Initial call to set correct visibility for schedule options
            # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._on_win_schedule_frequency_change(self.win_schedule_frequency_var.get())

        else: # For other OS (e.g., FreeBSD, Solaris, etc.)
            ttk.Label(self.schedule_section_frame, text="Scheduling for this OS is not yet implemented.").pack(pady=10)
            ttk.Label(self.schedule_section_frame, text="Please use manual backup or external scheduling tools for now.").pack()
        
        # Initial calls to set correct visibility for retention options
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._toggle_retention_options()
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self._on_retention_type_change(self.retention_type_var.get()) # To set initial unit visibility

        # Ensure Hetzner retention checkbox reflects current Hetzner settings
        # MOVED TO __init__ AFTER ALL TABS ARE CREATED: self.root.after(100, self._toggle_hetzner_options) # Call after GUI fully drawn


    def _toggle_retention_options(self):
        state = "normal" if self.retention_enabled_var.get() else "disabled"
        self.retention_type_menu.config(state=state)
        self.retention_value_entry.config(state=state)
        self.retention_unit_menu.config(state=state)
        self.retention_nas_checkbox.config(state=state)
        
        # Hetzner checkbox state also depends on whether Hetzner is generally enabled
        # This check is now safe because the checkbox should exist by the time this is called from __init__
        hetzner_global_state = "normal" if self.hetzner_enabled_var.get() else "disabled"
        combined_state = "normal" if self.retention_enabled_var.get() and hetzner_global_state == "normal" else "disabled"
        self.retention_hetzner_checkbox.config(state=combined_state)

        # Update unit menu visibility if state changes
        if state == "disabled":
            self.retention_unit_menu.grid_remove()
        else:
            self._on_retention_type_change(self.retention_type_var.get())

    def _on_retention_type_change(self, selected_type):
        if self.retention_enabled_var.get(): # Only show if retention is enabled
            if selected_type == "age":
                self.retention_unit_menu.grid()
            else:
                self.retention_unit_menu.grid_remove()
        else:
            self.retention_unit_menu.grid_remove()

    # ====================================================================================================
    # CRON JOB LOGIC (Linux/macOS)
    # ====================================================================================================

    def _on_schedule_frequency_change(self, selected_frequency):
        # Hide all specific scheduling options first
        self.schedule_day_of_week_label.grid_remove()
        self.schedule_day_of_week_menu.grid_remove()
        self.schedule_day_of_month_label.grid_remove()
        self.schedule_day_of_month_entry.grid_remove()
        self.schedule_cron_string_label.grid_remove()
        self.schedule_cron_string_entry.grid_remove()

        # Show options based on selected frequency
        if selected_frequency == "weekly":
            self.schedule_day_of_week_label.grid()
            self.schedule_day_of_week_menu.grid()
        elif selected_frequency == "monthly":
            self.schedule_day_of_month_label.grid()
            self.schedule_day_of_month_entry.grid()
        elif selected_frequency == "custom":
            self.schedule_cron_string_label.grid()
            self.schedule_cron_string_entry.grid()

        self.schedule_section_frame.update_idletasks() # Refresh layout

    def create_update_cron_job(self):
        if platform.system() not in ["Linux", "Darwin"]:
            messagebox.showinfo("Not Supported", "Cron jobs are only supported on Linux/macOS.")
            return

        frequency = self.schedule_frequency_var.get()
        time_str = self.schedule_time_var.get()

        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time format or range.")
        except ValueError:
            messagebox.showerror("Input Error", "Invalid time format. Please use HH:MM (e.g., 03:00).")
            return

        # Build cron string based on frequency
        cron_string = ""
        if frequency == "daily":
            cron_string = f"{minute} {hour} * * *"
        elif frequency == "weekly":
            day_of_week_map = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 0} # Cron uses 0 for Sunday
            day_of_week = day_of_week_map[self.schedule_day_of_week_var.get()]
            cron_string = f"{minute} {hour} * * {day_of_week}"
        elif frequency == "monthly":
            day_of_month = self.schedule_day_of_month_var.get()
            try:
                day = int(day_of_month)
                if not (1 <= day <= 31):
                    raise ValueError("Day of month must be between 1 and 31.")
            except ValueError:
                messagebox.showerror("Input Error", "Invalid day of month. Please enter a number between 1 and 31.")
                return
            cron_string = f"{minute} {hour} {day} * *"
        elif frequency == "custom":
            cron_string = self.schedule_cron_string_var.get()
            # Basic validation: check if it has 5 parts
            if len(cron_string.split()) != 5:
                messagebox.showerror("Input Error", "Custom Cron String must have 5 parts (minute hour day_of_month month day_of_week).")
                return

        # The command to run your backup tool in scheduled mode
        script_path = os.path.abspath(__file__) # Path to this main.py file
        # Use sys.executable to ensure the correct Python interpreter is used (e.g., from venv)
        python_executable = sys.executable 
        
        # Ensure that the command can find config.json and logs in the correct app_data_dir
        # By default, os.path.expanduser("~") will point to user's home directory.
        # Your config_manager is already set up to use this.
        
        # Redirect output to a log file
        log_dir = os.path.join(os.path.expanduser("~"), ".backup_tool")
        os.makedirs(log_dir, exist_ok=True) # Ensure log directory exists
        cron_log_file = os.path.join(log_dir, "scheduled_backup.log")

        # Command to be added to cron
        # We redirect output (stdout and stderr) to a log file
        # Ensure paths with spaces are quoted
        command = f'"{python_executable}" "{script_path}" --run-scheduled-backup --verbose >> "{cron_log_file}" 2>&1'
        
        # Cron job identifier comment
        job_comment = "# BackupTool_ScheduledBackup_Job"
        
        # Build cron line
        cron_line = f"{cron_string} {command} {job_comment}"

        try:
            # Read existing cron jobs
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
            current_crontab = result.stdout
            
            new_crontab_lines = []
            job_found = False

            # Update or add the job
            for line in current_crontab.splitlines():
                if job_comment in line:
                    new_crontab_lines.append(cron_line)
                    job_found = True
                    self.log_message(f"Updated existing cron job: {cron_line}", level="INFO")
                else:
                    new_crontab_lines.append(line)
            
            if not job_found:
                new_crontab_lines.append(cron_line)
                self.log_message(f"Added new cron job: {cron_line}", level="INFO")
            
            # Write the new crontab
            process = subprocess.run(["crontab", "-"], input="\n".join(new_crontab_lines) + "\n", capture_output=True, text=True, check=True)
            self.log_message(f"Cron job created/updated successfully: {process.stdout}", level="INFO")
            messagebox.showinfo("Success", "Cron job created/updated successfully.")

        except FileNotFoundError:
            self.log_message("crontab command not found. Please ensure cron is installed and in your PATH.", level="ERROR")
            messagebox.showerror("Error", "'crontab' command not found. Please ensure cron is installed and in your system PATH.")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to create/update cron job: {e.stderr}", level="ERROR")
            messagebox.showerror("Cron Error", f"Failed to create/update cron job: {e.stderr}")
        except Exception as e:
            self.log_message(f"An unexpected error occurred: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def remove_cron_job(self):
        if platform.system() not in ["Linux", "Darwin"]:
            messagebox.showinfo("Not Supported", "Cron jobs are only supported on Linux/macOS.")
            return

        job_comment = "# BackupTool_ScheduledBackup_Job"

        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
            current_crontab_lines = result.stdout.splitlines()

            new_crontab_lines = [line for line in current_crontab_lines if job_comment not in line]

            if len(new_crontab_lines) == len(current_crontab_lines):
                messagebox.showinfo("Info", "No existing BackupTool cron job found.")
                self.log_message("No existing BackupTool cron job found for removal.", level="INFO")
                return

            process = subprocess.run(["crontab", "-"], input="\n".join(new_crontab_lines) + "\n", capture_output=True, text=True, check=True)
            self.log_message(f"Cron job removed successfully: {process.stdout}", level="INFO")
            messagebox.showinfo("Success", "Cron job removed successfully.")

        except FileNotFoundError:
            self.log_message("crontab command not found.", level="ERROR")
            messagebox.showerror("Error", "'crontab' command not found. Please ensure cron is installed and in your system PATH.")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to remove cron job: {e.stderr}", level="ERROR")
            messagebox.showerror("Cron Error", f"Failed to remove cron job: {e.stderr}")
        except Exception as e:
            self.log_message(f"An unexpected error occurred: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def view_my_cron_jobs(self):
        if platform.system() not in ["Linux", "Darwin"]:
            messagebox.showinfo("Not Supported", "Cron jobs are only supported on Linux/macOS.")
            return

        job_comment = "# BackupTool_ScheduledBackup_Job"

        try:
            result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=True)
            my_cron_job = [line for line in result.stdout.splitlines() if job_comment in line]

            if my_cron_job:
                messagebox.showinfo("My Backup Tool Cron Job", "\n".join(my_cron_job))
            else:
                messagebox.showinfo("My Backup Tool Cron Job", "No BackupTool cron job found.")
            
        except FileNotFoundError:
            self.log_message("crontab command not found.", level="ERROR")
            messagebox.showerror("Error", "'crontab' command not found. Please ensure cron is installed and in your system PATH.")
        except subprocess.CalledProcessError as e:
            self.log_message(f"Error viewing cron jobs: {e.stderr}", level="ERROR")
            messagebox.showerror("Cron Error", f"Could not view cron jobs: {e.stderr}")
        except Exception as e:
            self.log_message(f"An unexpected error occurred: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    # ====================================================================================================
    # WINDOWS TASK SCHEDULER LOGIC
    # ====================================================================================================

    def _on_win_schedule_frequency_change(self, selected_frequency):
        # Hide all specific scheduling options first
        self.win_schedule_day_of_week_label.grid_remove()
        self.win_schedule_day_of_week_menu.grid_remove()
        self.win_schedule_day_of_month_label.grid_remove()
        self.win_schedule_day_of_month_entry.grid_remove()

        # Show options based on selected frequency
        if selected_frequency == "WEEKLY":
            self.win_schedule_day_of_week_label.grid()
            self.win_schedule_day_of_week_menu.grid()
        elif selected_frequency == "MONTHLY":
            self.win_schedule_day_of_month_label.grid()
            self.win_schedule_day_of_month_entry.grid()

        self.schedule_section_frame.update_idletasks()


    def create_update_win_task(self):
        if platform.system() != "Windows":
            messagebox.showinfo("Not Supported", "Windows Task Scheduler is only supported on Windows.")
            return

        frequency = self.win_schedule_frequency_var.get()
        time_str = self.win_schedule_time_var.get()
        
        try:
            hour, minute = map(int, time_str.split(':'))
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError("Invalid time format or range.")
            start_time = f"{hour:02d}:{minute:02d}" # Format as HH:MM
        except ValueError:
            messagebox.showerror("Input Error", "Invalid time format. Please use HH:MM (e.g., 03:00).")
            return

        task_name = "BackupTool_ScheduledBackup"
        script_path = os.path.abspath(__file__)
        python_executable = sys.executable

        # Command to be executed by the task scheduler
        # We use 'start "" /B' to prevent a new cmd window from staying open
        # and redirect output to a log file.
        log_dir = os.path.join(os.path.expanduser("~"), ".backup_tool")
        os.makedirs(log_dir, exist_ok=True)
        task_log_file = os.path.join(log_dir, "scheduled_backup.log")
        
        # Enclose paths with spaces in quotes
        command = f'"{python_executable}" "{script_path}" --run-scheduled-backup --verbose >> "{task_log_file}" 2>&1'
        
        # Prepare schtasks arguments
        # /TR "Task Run" - The command to execute
        # /SC "Schedule" - Frequency (DAILY, WEEKLY, MONTHLY)
        # /ST "Start Time" - HH:MM
        # /RU "Run As User" - Current user. /RP "Run As Password" - Optional, generally not needed for current user unless password policy is strict
        # /RL HIGHEST - Run with highest privileges (optional, but good for backups)
        # /F - Force overwrite if task exists
        
        schtasks_cmd = ["schtasks", "/create", "/tn", task_name, "/tr", command, "/sc", frequency, "/st", start_time, "/f"]

        if frequency == "WEEKLY":
            day_of_week = self.win_schedule_day_of_week_var.get()
            # Windows uses MON, TUE, WED, etc. for /D
            schtasks_cmd.extend(["/d", day_of_week])
        elif frequency == "MONTHLY":
            day_of_month = self.win_schedule_day_of_month_var.get()
            try:
                day = int(day_of_month)
                if not (1 <= day <= 31):
                    raise ValueError("Day of month must be between 1 and 31.")
            except ValueError:
                messagebox.showerror("Input Error", "Invalid day of month. Please enter a number between 1 and 31.")
                return
            schtasks_cmd.extend(["/d", str(day)]) # /D specifies day of month for monthly

        try:
            self.log_message(f"Creating/updating Windows task: {' '.join(schtasks_cmd)}", level="INFO")
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True, encoding='cp850', errors='replace') # cp850 is common for cmd.exe
            
            self.log_message(f"Windows task created/updated successfully: {result.stdout}", level="INFO")
            messagebox.showinfo("Success", f"Windows scheduled task '{task_name}' created/updated successfully.\nOutput redirected to '{task_log_file}'.\nYou might need to confirm a UAC prompt.")

        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to create/update Windows task: {e.stderr}", level="ERROR")
            messagebox.showerror("Task Scheduler Error", f"Failed to create/update task: {e.stderr}\nError: {e.stdout}")
        except FileNotFoundError:
            self.log_message("schtasks.exe not found. Please ensure it's in your PATH.", level="ERROR")
            messagebox.showerror("Error", "'schtasks.exe' not found. Please ensure it's in your system PATH.")
        except Exception as e:
            self.log_message(f"An unexpected error occurred during task creation: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def remove_win_task(self):
        if platform.system() != "Windows":
            messagebox.showinfo("Not Supported", "Windows Task Scheduler is only supported on Windows.")
            return

        task_name = "BackupTool_ScheduledBackup"
        
        # /TN "Task Name" - The name of the task
        # /F - Force delete without confirmation
        schtasks_cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]

        try:
            self.log_message(f"Attempting to delete Windows task: {task_name}", level="INFO")
            # Check if task exists first to give a better message
            check_cmd = ["schtasks", "/query", "/tn", task_name]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True, encoding='cp850', errors='replace')

            if "ERROR: The system cannot find the task specified." in check_result.stderr or check_result.returncode != 0:
                messagebox.showinfo("Info", f"Windows scheduled task '{task_name}' not found.")
                self.log_message(f"Windows scheduled task '{task_name}' not found for deletion.", level="INFO")
                return

            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=True, encoding='cp850', errors='replace')
            
            self.log_message(f"Windows task '{task_name}' removed successfully: {result.stdout}", level="INFO")
            messagebox.showinfo("Success", f"Windows scheduled task '{task_name}' removed successfully.")

        except subprocess.CalledProcessError as e:
            self.log_message(f"Failed to remove Windows task: {e.stderr}", level="ERROR")
            messagebox.showerror("Task Scheduler Error", f"Failed to remove task: {e.stderr}")
        except FileNotFoundError:
            self.log_message("schtasks.exe not found.", level="ERROR")
            messagebox.showerror("Error", "'schtasks.exe' not found. Please ensure it's in your system PATH.")
        except Exception as e:
            self.log_message(f"An unexpected error occurred during task removal: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def view_my_win_tasks(self):
        if platform.system() != "Windows":
            messagebox.showinfo("Not Supported", "Windows Task Scheduler is only supported on Windows.")
            return
        
        task_name = "BackupTool_ScheduledBackup"
        schtasks_cmd = ["schtasks", "/query", "/tn", task_name] # Query specific task
        
        try:
            self.log_message(f"Querying Windows task: {task_name}", level="INFO")
            result = subprocess.run(schtasks_cmd, capture_output=True, text=True, check=False, encoding='cp850', errors='replace')

            if result.returncode == 0:
                # Check if the specific task name appears in the output
                if task_name in result.stdout:
                    # Parse the output for relevant information
                    output_lines = result.stdout.splitlines()
                    task_info = [line for line in output_lines if line.strip() and not line.strip().startswith("TaskName") and not line.strip().startswith("----------")]
                    
                    if task_info:
                        messagebox.showinfo("My Backup Tool Scheduled Task", f"Task '{task_name}' Found:\n\n" + "\n".join(task_info))
                        self.log_message(f"Displayed info for Windows task: {task_name}", level="INFO")
                    else:
                        messagebox.showinfo("My Backup Tool Scheduled Task", f"Task '{task_name}' found, but no detailed info parsed.")
                        self.log_message(f"Task '{task_name}' found, but no detailed info parsed.", level="INFO")
                else:
                    messagebox.showinfo("My Backup Tool Scheduled Task", f"Task '{task_name}' not found.")
                    self.log_message(f"Windows task '{task_name}' not found.", level="INFO")
            else:
                # Common case for schtasks /query when task doesn't exist
                if "ERROR: The system cannot find the task specified." in result.stderr:
                    messagebox.showinfo("My Backup Tool Scheduled Task", f"Task '{task_name}' not found.")
                    self.log_message(f"Windows task '{task_name}' not found.", level="INFO")
                else:
                    self.log_message(f"Error viewing Windows tasks: {result.stderr}", level="ERROR")
                    messagebox.showerror("Task Scheduler Error", f"Could not view task: {result.stderr}")
        except FileNotFoundError:
            self.log_message("schtasks.exe not found.", level="ERROR")
            messagebox.showerror("Error", "'schtasks.exe' not found. Please ensure it's in your system PATH.")
        except Exception as e:
            self.log_message(f"An unexpected error occurred during task view: {e}", level="ERROR")
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    # ====================================================================
    # LOGGING
    # ====================================================================
    def log_message(self, message, level="INFO"):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        log_entry = f"{timestamp} [{level}] {message}\n"

        self.root.after(0, lambda: self._update_log_text(log_entry, level))

        # Also write to a persistent log file
        log_file_path = os.path.join(self.app_data_dir, "backup_tool.log")
        try:
            with open(log_file_path, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"Error writing to log file: {e}") # Fallback to console print

    def _update_log_text(self, log_entry, level):
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END) # Auto-scroll to the end

        # Optional: Apply color tags
        if level == "INFO":
            self.log_text.tag_configure("INFO", foreground="white")
            self.log_text.tag_add("INFO", "end-2l", "end-1c")
        elif level == "WARNING":
            self.log_text.tag_configure("WARNING", foreground="yellow")
            self.log_text.tag_add("WARNING", "end-2l", "end-1c")
        elif level == "ERROR":
            self.log_text.tag_configure("ERROR", foreground="red")
            self.log_text.tag_add("ERROR", "end-2l", "end-1c")
        elif level == "DEBUG":
            self.log_text.tag_configure("DEBUG", foreground="lightgray")
            self.log_text.tag_add("DEBUG", "end-2l", "end-1c")

        self.log_text.config(state="disabled")

    def run(self):
        self.root.mainloop()

# ====================================================================
# SCHEDULED BACKUP EXECUTION (When script is run with --run-scheduled-backup)
# ====================================================================
def run_scheduled_backup():
    """
    Function to be called when the script is run from a scheduler.
    It performs the backup and then the retention policy.
    """
    config_manager = ConfigManager()
    config = config_manager.load_config()

    if not config:
        print("Error: Could not load configuration for scheduled backup. Exiting.")
        return

    # Create a simple logging function for CLI mode
    def cli_log(message, level="INFO"):
        timestamp = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        print(f"{timestamp} [{level}] {message}")

    cli_log("Starting scheduled backup run...", level="INFO")

    # Retrieve parameters for backup
    source_path = config.get('source_path')
    destination_path = config.get('destination_path')
    dest_nas_enabled = config.get('destination_nas_enabled', False)
    dest_hetzner_enabled = config.get('destination_hetzner_enabled', False)
    include_subfolders = config.get('include_subfolders', True)
    compression_level = config.get('compression_level', 'Default')
    archive_format = config.get('archive_format', 'zip')

    if not source_path or (not dest_nas_enabled and not dest_hetzner_enabled):
        cli_log("Scheduled backup skipped: Source path not set or no destinations enabled.", level="WARNING")
        return

    if dest_nas_enabled and (not destination_path):
        cli_log("Scheduled backup skipped: NAS/Local destination enabled but path not set.", level="WARNING")
        return
    
    if dest_hetzner_enabled:
        if not config.get('hetzner_host') or not config.get('hetzner_username') or not config.get('hetzner_password'):
            cli_log("Scheduled backup skipped: Hetzner destination enabled but credentials not configured.", level="WARNING")
            return


    # Perform the backup
    backup_success, backup_message = perform_backup(
        source_path, destination_path, dest_nas_enabled, dest_hetzner_enabled,
        include_subfolders, compression_level, archive_format,
        config_manager, cli_log
    )
    cli_log(f"Backup result: {backup_message}", level="INFO" if backup_success else "ERROR")

    # ====================================================================
    # Apply Retention Policy after backup
    # ====================================================================
    retention_enabled = config.get('retention_enabled', False)
    if retention_enabled:
        cli_log("Applying retention policy...", level="INFO")
        
        retention_type = config.get('retention_type', 'count')
        retention_value = int(config.get('retention_value', 5)) # Ensure it's an int
        retention_unit = config.get('retention_unit', 'days') # For age-based
        retention_nas = config.get('retention_nas', False)
        retention_hetzner = config.get('retention_hetzner', False)

        if not retention_nas and not retention_hetzner:
            cli_log("Retention policy enabled but no destinations selected for cleanup. Skipping.", level="WARNING")
            return
        
        # Determine paths to clean for NAS/Local
        if retention_nas and destination_path:
            cli_log(f"Applying retention to NAS/Local: {destination_path}", level="INFO")
            try:
                # Get list of archive files in the destination_path (assuming backups are there)
                # You might need to refine this to only target files created by this tool
                archive_files = [
                    os.path.join(destination_path, f)
                    for f in os.listdir(destination_path)
                    if f.endswith(('.zip', '.tar.gz', '.tgz', '.gz')) # Filter for archive types
                    # Consider adding a specific prefix if your backups have one (e.g., "BackupTool_")
                ]
                archive_files.sort(key=os.path.getmtime) # Sort by modification time (oldest first)

                files_to_delete = []

                if retention_type == "count":
                    if len(archive_files) > retention_value:
                        files_to_delete = archive_files[:-retention_value] # Keep the newest 'retention_value'
                        cli_log(f"Retention (count): Found {len(files_to_delete)} old files to delete on NAS/Local.", level="INFO")
                elif retention_type == "age":
                    now = datetime.datetime.now()
                    for f in archive_files:
                        file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(f))
                        age = now - file_mtime
                        
                        delete = False
                        if retention_unit == "days" and age.days > retention_value:
                            delete = True
                        elif retention_unit == "weeks" and age.days / 7 > retention_value:
                            delete = True
                        elif retention_unit == "months" and age.days / 30.44 > retention_value: # Approximation
                            delete = True
                        elif retention_unit == "years" and age.days / 365.25 > retention_value: # Approximation
                            delete = True
                        
                        if delete:
                            files_to_delete.append(f)
                    cli_log(f"Retention (age): Found {len(files_to_delete)} old files to delete on NAS/Local.", level="INFO")
                
                for file_to_delete in files_to_delete:
                    try:
                        os.remove(file_to_delete)
                        cli_log(f"Deleted old backup: {file_to_delete}", level="INFO")
                    except Exception as e:
                        cli_log(f"Error deleting {file_to_delete}: {e}", level="ERROR")

            except Exception as e:
                cli_log(f"Error applying NAS/Local retention policy: {e}", level="ERROR")


        # Determine paths to clean for Hetzner
        if retention_hetzner:
            cli_log(f"Applying retention to Hetzner Storage Box...", level="INFO")
            
            # Retrieve Hetzner credentials
            hetzner_config = {
                'host': config['hetzner_host'],
                'port': int(config.get('hetzner_port', 23)),
                'username': config['hetzner_username'],
                'password': config_manager.decrypt_data(config['hetzner_password'])
            }

            try:
                import paramiko
                transport = paramiko.Transport((hetzner_config['host'], hetzner_config['port']))
                transport.connect(username=hetzner_config['username'], password=hetzner_config['password'])
                sftp = paramiko.SFTPClient.from_transport(transport)

                # Assume backups are in the root directory or a known subdirectory
                # You might need a setting for the remote backup folder on Hetzner
                remote_backup_dir = "/backups" # This should ideally be configurable if not fixed

                # Get list of files on SFTP server
                sftp_files = []
                try:
                    for entry in sftp.listdir_attr(remote_backup_dir):
                        if entry.filename.endswith(('.zip', '.tar.gz', '.tgz', '.gz')):
                            sftp_files.append(os.path.join(remote_backup_dir, entry.filename))
                except FileNotFoundError:
                    cli_log(f"Remote directory {remote_backup_dir} not found on Hetzner. Skipping retention.", level="WARNING")
                    return

                sftp_files.sort() # Sorting alphabetically/lexicographically often works for timestamped files
                
                files_to_delete_sftp = []

                if retention_type == "count":
                    if len(sftp_files) > retention_value:
                        files_to_delete_sftp = sftp_files[:-retention_value] # Keep the newest 'retention_value'
                        cli_log(f"Retention (count): Found {len(files_to_delete_sftp)} old files to delete on Hetzner.", level="INFO")
                elif retention_type == "age":
                    # This is more complex for SFTP as paramiko.SFTPAttributes only has st_mtime (unix timestamp)
                    now_timestamp = datetime.datetime.now().timestamp()
                    for f_path in sftp_files:
                        attrs = sftp.stat(f_path)
                        file_mtime_timestamp = attrs.st_mtime
                        age_seconds = now_timestamp - file_mtime_timestamp
                        
                        delete = False
                        if retention_unit == "days" and age_seconds / (24 * 3600) > retention_value:
                            delete = True
                        elif retention_unit == "weeks" and age_seconds / (7 * 24 * 3600) > retention_value:
                            delete = True
                        elif retention_unit == "months" and age_seconds / (30.44 * 24 * 3600) > retention_value:
                            delete = True
                        elif retention_unit == "years" and age_seconds / (365.25 * 24 * 3600) > retention_value:
                            delete = True
                        
                        if delete:
                            files_to_delete_sftp.append(f_path)
                    cli_log(f"Retention (age): Found {len(files_to_delete_sftp)} old files to delete on Hetzner.", level="INFO")

                for file_to_delete in files_to_delete_sftp:
                    try:
                        sftp.remove(file_to_delete)
                        cli_log(f"Deleted old Hetzner backup: {file_to_delete}", level="INFO")
                    except Exception as e:
                        cli_log(f"Error deleting {file_to_delete} from Hetzner: {e}", level="ERROR")

            except paramiko.AuthenticationException:
                cli_log("SFTP Authentication failed for Hetzner retention. Check username/password.", level="ERROR")
            except paramiko.SSHException as e:
                cli_log(f"Could not establish SFTP connection for Hetzner retention: {e}", level="ERROR")
            except Exception as e:
                cli_log(f"An unexpected error occurred during Hetzner retention: {e}", level="ERROR")
            finally:
                if 'sftp' in locals() and sftp:
                    sftp.close()
                if 'transport' in locals() and transport:
                    transport.close()
    else:
        cli_log("Retention policy not enabled or no destinations selected.", level="INFO")

    cli_log("Scheduled backup run finished.", level="INFO")


# ====================================================================
# MAIN EXECUTION BLOCK
# ====================================================================
if __name__ == "__main__":
    if "--run-scheduled-backup" in sys.argv:
        # This branch is executed when the script is called by cron/task scheduler
        # We need a basic ConfigManager instance for it
        run_scheduled_backup()
    else:
        # This branch is executed when the GUI is started normally
        root = tk.Tk()
        app = BackupToolGUI(root)
        app.run()
