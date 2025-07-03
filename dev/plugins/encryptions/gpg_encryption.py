# /home/philipp/Dokumente/BAckUp_tool_py/plugins/encryption/gpg_encryption.py

from plugin_interfaces import EncryptionPlugin
import subprocess
import os
import shutil # Für temporäre Dateien
import tkinter as tk
from tkinter import ttk

class GPGEncryptionPlugin(EncryptionPlugin):
    def __init__(self, config_data=None, log_callback=None):
        super().__init__(config_data, log_callback)

        # Beispiel: Standard-Key-ID oder Pfad zur Keyring-Datei
        self.encryption_key_id = self.config_data.get("gpg_key_id", "your_gpg_key_id_here") 
        self.log_callback = log_callback

    def get_name(self):
        return "GPG Encryption"

    def get_description(self): # <-- DIESE METHODE HINZUFÜGEN
        return "Encrypts/Decrypts files using GnuPG."

    def encrypt(self, input_filepath, output_filepath):
        try:
            # Beispiel: Verschlüsseln mit einem Public Key
            # Wichtig: Der Public Key muss in Ihrem GPG-Keyring vorhanden sein
            command = [
                "gpg", "--encrypt", "--recipient", self.encryption_key_id,
                "--output", output_filepath, input_filepath
            ]

            self.log(f"Executing GPG encryption command: {' '.join(command)}", level="DEBUG")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.log(f"GPG Encrypt Stdout: {result.stdout}", level="DEBUG")
            if result.stderr:
                self.log(f"GPG Encrypt Stderr: {result.stderr}", level="WARNING")

            self.log(f"File '{input_filepath}' encrypted to '{output_filepath}'.", level="INFO")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"GPG encryption failed for '{input_filepath}': {e.stderr}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during GPG encryption: {e}", level="ERROR")
            return False

    def decrypt(self, input_filepath, output_filepath):
        try:
            # Beispiel: Entschlüsseln
            command = [
                "gpg", "--decrypt", "--output", output_filepath, input_filepath
            ]

            self.log(f"Executing GPG decryption command: {' '.join(command)}", level="DEBUG")
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            self.log(f"GPG Decrypt Stdout: {result.stdout}", level="DEBUG")
            if result.stderr:
                self.log(f"GPG Decrypt Stderr: {result.stderr}", level="WARNING")

            self.log(f"File '{input_filepath}' decrypted to '{output_filepath}'.", level="INFO")
            return True
        except subprocess.CalledProcessError as e:
            self.log(f"GPG decryption failed for '{input_filepath}': {e.stderr}", level="ERROR")
            return False
        except Exception as e:
            self.log(f"An unexpected error occurred during GPG decryption: {e}", level="ERROR")
            return False

    def get_ui_elements(self, parent_frame: ttk.Frame, tk_vars_dict: dict) -> list[tk.Widget]:
        frame = ttk.Frame(parent_frame)
        frame.pack(fill="both", expand=True, padx=5, pady=5)
        ttk.Label(frame, text="GPG Key ID (Recipient):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        gpg_key_id_var = tk.StringVar(value=self.encryption_key_id)
        ttk.Entry(frame, textvariable=gpg_key_id_var).grid(row=0, column=1, padx=5, pady=2, sticky="ew")
        tk_vars_dict["gpg_key_id"] = gpg_key_id_var
        frame.columnconfigure(1, weight=1)
        return []

    def validate_config(self):
        if not self.encryption_key_id:
            return False, "GPG Key ID cannot be empty."
        # Optional: Prüfen, ob der Schlüssel im GPG-Keyring existiert
        try:
            subprocess.run(["gpg", "--list-keys", self.encryption_key_id], 
                            capture_output=True, text=True, check=True)
            return True, ""
        except subprocess.CalledProcessError:
            return False, f"GPG Key ID '{self.encryption_key_id}' not found in GPG keyring."
        except FileNotFoundError:
            return False, "GPG (GnuPG) command not found. Please ensure it is installed and in your PATH."
