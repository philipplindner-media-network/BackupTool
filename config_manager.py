import json
import os
from cryptography.fernet import Fernet
import base64
import hashlib

class ConfigManager:
    def __init__(self, config_filename="config.json", key_filename="secret.key"):
        self.app_data_dir = self._get_app_data_directory()
        self.config_filepath = os.path.join(self.app_data_dir, config_filename)
        self.key_filepath = os.path.join(self.app_data_dir, key_filename)
        self.fernet = self._load_or_generate_key()
        self.config = {} # To hold the loaded config data

    def _get_app_data_directory(self):
        """Determines the appropriate application data directory based on OS."""
        if platform.system() == "Windows":
            app_data = os.getenv('APPDATA')
            if app_data:
                return os.path.join(app_data, "BackupTool")
            else:
                # Fallback if APPDATA is not set for some reason
                return os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "BackupTool")
        elif platform.system() == "Darwin": # macOS
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "BackupTool")
        else: # Linux and other Unix-like systems
            return os.path.join(os.path.expanduser("~"), ".backup_tool") # Common for hidden config dirs
        
    def _load_or_generate_key(self):
        """Loads the encryption key or generates a new one if it doesn't exist."""
        os.makedirs(self.app_data_dir, exist_ok=True) # Ensure directory exists
        if os.path.exists(self.key_filepath):
            with open(self.key_filepath, "rb") as key_file:
                key = key_file.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_filepath, "wb") as key_file:
                key_file.write(key)
        return Fernet(key)

    def encrypt_data(self, data):
        """Encrypts a string."""
        if isinstance(data, str):
            data = data.encode('utf-8')
        return self.fernet.encrypt(data).decode('utf-8') # Store as string

    def decrypt_data(self, encrypted_data):
        """Decrypts an encrypted string."""
        if isinstance(encrypted_data, str):
            encrypted_data = encrypted_data.encode('utf-8')
        try:
            return self.fernet.decrypt(encrypted_data).decode('utf-8')
        except Exception as e:
            # Handle cases where decryption fails (e.g., wrong key, corrupted data)
            print(f"Decryption error: {e}")
            return "" # Return empty string or raise specific error

    def load_config(self):
        """Loads configuration from the file, decrypting sensitive fields if encrypted."""
        if not os.path.exists(self.config_filepath):
            self.config = {}
            return {}

        try:
            with open(self.config_filepath, "r", encoding="utf-8") as f:
                encrypted_config = json.load(f)
            
            self.config = {} # Start with empty config

            # Decrypt sensitive fields if they exist and encryption was enabled
            # Note: The 'encryption_enabled' flag itself is not encrypted.
            encryption_enabled_stored = encrypted_config.get('encryption_enabled', False)
            
            for key, value in encrypted_config.items():
                if key in ['encryption_password', 'hetzner_password']: # These are always stored encrypted if set
                    if value and encryption_enabled_stored:
                        self.config[key] = self.decrypt_data(value)
                    else:
                        self.config[key] = "" # If not encrypted or empty, store as empty
                else:
                    self.config[key] = value
            
            return self.config

        except json.JSONDecodeError as e:
            print(f"Error reading config file (JSON error): {e}")
            self.config = {}
            return {}
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}
            return {}

    def save_config(self, config_data, encryption_password=None, hetzner_password=None):
        """
        Saves configuration to the file, encrypting sensitive fields.
        'encryption_password' and 'hetzner_password' are passed separately
        to ensure they are processed correctly.
        """
        
        # Always store whether encryption is enabled
        self.config['encryption_enabled'] = config_data.get('encryption_enabled', False)

        # Handle encryption password
        if config_data.get('encryption_enabled'):
            if encryption_password: # Only update if a password was provided
                self.config['encryption_password'] = self.encrypt_data(encryption_password)
        else:
            # If encryption is disabled, clear any stored encryption password
            if 'encryption_password' in self.config:
                del self.config['encryption_password']
        
        # Handle Hetzner password
        if config_data.get('hetzner_enabled'):
            if hetzner_password: # Only update if a password was provided in the GUI
                self.config['hetzner_password'] = self.encrypt_data(hetzner_password)
            elif 'hetzner_password' not in self.config and not hetzner_password:
                # If Hetzner enabled, but no password was provided and none previously saved, set to empty encrypted string
                self.config['hetzner_password'] = self.encrypt_data("")
        else:
            # If Hetzner is disabled, clear any stored Hetzner password
            if 'hetzner_password' in self.config:
                del self.config['hetzner_password']


        # Update other fields (non-sensitive or already handled)
        for key, value in config_data.items():
            if key not in ['encryption_password', 'hetzner_password']: # Don't overwrite handled sensitive fields
                self.config[key] = value

        try:
            with open(self.config_filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

# Ensure platform is imported for _get_app_data_directory
import platform
