import os
import shutil
import zipfile
import tarfile
import hashlib
import paramiko # Für SFTP
import datetime
import stat # Für SFTP Berechtigungen
import tempfile # Für temporäre Dateien
import io # Für In-Memory-Operationen
from cryptography.fernet import Fernet # Für die eingebaute AES-Verschlüsselung

# Importiere Schnittstellen (brauchen wir hier für Type-Hinting und Instanzprüfung)
from plugin_interfaces import BackupDestinationPlugin, EncryptionPlugin

# --- Encryption Functions (Built-in AES) ---
def generate_and_save_config_key(key_path):
    """
    Generates a new encryption key if one doesn't exist,
    or loads an existing one from the specified path.
    """
    if os.path.exists(key_path):
        with open(key_path, "rb") as key_file:
            key = key_file.read()
        return key
    else:
        key = Fernet.generate_key()
        # The 'key_path' already contains the full path and filename
        # No need to join again or assume it's a directory
        with open(key_path, "wb") as key_file: 
            key_file.write(key)
        return key

def encrypt_string_with_key(data_to_encrypt: bytes, passphrase: str):
    """
    Verschlüsselt Bytes mit der Hauptkonfigurations-Passphrase.
    Die Fernet-Key-Erzeugung aus der Passphrase ist hier nur eine simple Lösung.
    Für stärkere Sicherheit sollten KDFs wie PBKDF2 verwendet werden.
    """
    try:
        # Hier nutzen wir die Passphrase direkt als Schlüssel (nicht ideal für Sicherheit, aber einfach).
        # In einer echten Anwendung müsste die Passphrase in einen sicheren Schlüssel umgewandelt werden (z.B. mit PBKDF2).
        # Für Fernet benötigen wir einen 32 URL-safe base64-encoded bytes key.
        # Dies ist eine Vereinfachung für das Beispiel.
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        f = Fernet(key)
        encrypted_data = f.encrypt(data_to_encrypt)
        return encrypted_data, None
    except Exception as e:
        return None, f"Built-in AES Encryption Error: {e}"

def decrypt_string_with_key(encrypted_data: bytes, passphrase: str):
    """
    Entschlüsselt Bytes mit der Hauptkonfigurations-Passphrase.
    """
    try:
        key = base64.urlsafe_b64encode(hashlib.sha256(passphrase.encode()).digest())
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data)
        return decrypted_data, None
    except Exception as e:
        return None, f"Built-in AES Decryption Error: {e}. Check passphrase or file corruption."


# --- SFTP Utility Functions ---
def sftp_connect(sftp_details, log_callback):
    try:
        host_port = sftp_details["host"].split(':')
        hostname = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 22
        
        transport = paramiko.Transport((hostname, port))
        transport.connect(username=sftp_details["username"], password=sftp_details["password"])
        sftp = paramiko.SFTPClient.from_transport(transport)
        log_callback(f"SFTP connection established to {hostname}:{port}", level="DEBUG")
        return sftp, None
    except paramiko.AuthenticationException:
        return None, "Authentication failed. Check username and password."
    except paramiko.SSHException as ssh_err:
        return None, f"SSH error: {ssh_err}. Check host and port."
    except Exception as e:
        return None, f"SFTP connection failed: {e}"

def test_sftp_connection(sftp_details, log_callback):
    sftp, error = sftp_connect(sftp_details, log_callback)
    if sftp:
        try:
            sftp.close()
            log_callback(f"SFTP connection test successful for {sftp_details['host']}", level="INFO")
            return True, "Connection successful."
        except Exception as e:
            log_callback(f"SFTP disconnection error: {e}", level="WARNING")
            return True, "Connection established, but error on close."
    else:
        log_callback(f"SFTP connection test failed for {sftp_details['host']}: {error}", level="ERROR")
        return False, error

def sftp_makedirs(sftp, remote_path, log_callback):
    """Ensure remote path exists."""
    dirs = []
    # Normalize path to handle both / and \
    parts = remote_path.replace("\\", "/").split('/')
    
    # Filter out empty strings that result from leading/trailing slashes or multiple slashes
    current_path = []
    for part in parts:
        if part: # Only process non-empty parts
            current_path.append(part)
            dir_to_create = "/".join(current_path)
            if dir_to_create and dir_to_create != '/': # Avoid trying to make the root directory
                dirs.append(dir_to_create)

    for dir_path in dirs:
        try:
            sftp.stat(dir_path)
            log_callback(f"Remote directory exists: {dir_path}", level="DEBUG")
        except FileNotFoundError:
            try:
                sftp.mkdir(dir_path)
                log_callback(f"Created remote directory: {dir_path}", level="INFO")
            except Exception as e:
                log_callback(f"Failed to create remote directory {dir_path}: {e}", level="ERROR")
                return False, f"Failed to create remote directory {dir_path}: {e}"
    return True, None


def upload_file_sftp(local_file_path, remote_file_name, sftp_details, log_callback):
    sftp, error = sftp_connect(sftp_details, log_callback)
    if not sftp:
        return False, error
    
    remote_dir = sftp_details["remote_path"]
    remote_full_path = os.path.join(remote_dir, remote_file_name).replace("\\", "/") # Normalize for SFTP

    try:
        # Ensure remote directory exists
        success, msg = sftp_makedirs(sftp, remote_dir, log_callback)
        if not success:
            return False, msg

        log_callback(f"Uploading {local_file_path} to {remote_full_path} (SFTP)", level="INFO")
        sftp.put(local_file_path, remote_full_path)
        log_callback(f"SFTP upload successful for {remote_file_name}", level="INFO")
        return True, "Upload successful."
    except Exception as e:
        log_callback(f"SFTP upload failed for {remote_file_name}: {e}", level="ERROR")
        return False, f"SFTP upload failed: {e}"
    finally:
        if sftp and sftp.get_transport():
            sftp.close()
            sftp.get_transport().close()


def list_files_sftp(remote_path, sftp_details, log_callback):
    sftp, error = sftp_connect(sftp_details, log_callback)
    if not sftp:
        return [], error
    
    normalized_remote_path = remote_path.replace("\\", "/")
    if not normalized_remote_path.endswith('/'):
        normalized_remote_path += '/'

    try:
        files = sftp.listdir(normalized_remote_path)
        return files, None
    except FileNotFoundError:
        return [], f"Remote path not found: {remote_path}"
    except Exception as e:
        return [], f"Failed to list SFTP files: {e}"
    finally:
        if sftp and sftp.get_transport():
            sftp.close()
            sftp.get_transport().close()

def delete_file_sftp(remote_file_path, sftp_details, log_callback):
    sftp, error = sftp_connect(sftp_details, log_callback)
    if not sftp:
        return False, error

    normalized_remote_file_path = remote_file_path.replace("\\", "/")
    try:
        sftp.remove(normalized_remote_file_path)
        log_callback(f"Deleted SFTP file: {normalized_remote_file_path}", level="INFO")
        return True, "File deleted."
    except FileNotFoundError:
        return False, f"File not found on SFTP: {remote_file_path}"
    except Exception as e:
        log_callback(f"Failed to delete SFTP file {remote_file_path}: {e}", level="ERROR")
        return False, f"Failed to delete SFTP file: {e}"
    finally:
        if sftp and sftp.get_transport():
            sftp.close()
            sftp.get_transport().close()

# --- Core Backup Logic ---
def calculate_file_hash(file_path, hash_algorithm="sha256"):
    hasher = hashlib.new(hash_algorithm)
    with open(file_path, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def perform_backup(
    source_paths: list,
    destinations: list, # List of dicts, now potentially containing "plugin_instance"
    archive_format: str,
    encryption_enabled: bool,
    passphrase: str,
    encryption_plugin: EncryptionPlugin = None, # Optional: Instanz des Verschlüsselungs-Plugins
    progress_callback=None,
    job_name="default_job"
):
    if not progress_callback:
        progress_callback = print

    if not source_paths:
        return False, "No source paths provided.", None, None

    archive_name = f"backup_{job_name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
    # Use a tempfile to ensure cleanup, even on errors
    temp_archive_fd, temp_archive_path = tempfile.mkstemp(suffix=f".{archive_format.replace('.', '')}")
    os.close(temp_archive_fd) # Close the file descriptor immediately

    progress_callback(f"Creating archive: {temp_archive_path}", level="INFO")
    try:
        if archive_format == "zip":
            with zipfile.ZipFile(temp_archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for path in source_paths:
                    if not os.path.exists(path):
                        progress_callback(f"Warning: Source path '{path}' does not exist, skipping.", level="WARNING")
                        continue
                    if os.path.isdir(path):
                        # Add directory contents
                        for root, _, files in os.walk(path):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # Relative path inside the archive
                                arcname = os.path.relpath(file_path, os.path.dirname(path)) 
                                zipf.write(file_path, arcname)
                                progress_callback(f"Adding to archive: {arcname}", level="DEBUG")
                    else: # It's a file
                        zipf.write(path, os.path.basename(path))
                        progress_callback(f"Adding to archive: {os.path.basename(path)}", level="DEBUG")
        elif archive_format.startswith("tar"):
            mode = 'w:gz' if archive_format == "tar.gz" else 'w:bz2' if archive_format == "tar.bz2" else 'w'
            with tarfile.open(temp_archive_path, mode) as tar:
                for path in source_paths:
                    if not os.path.exists(path):
                        progress_callback(f"Warning: Source path '{path}' does not exist, skipping.", level="WARNING")
                        continue
                    tar.add(path, arcname=os.path.basename(path)) # Add base name to archive
                    progress_callback(f"Adding to archive: {os.path.basename(path)}", level="DEBUG")
        else:
            return False, f"Unsupported archive format: {archive_format}", None, None
        
        progress_callback("Archive created successfully.", level="INFO")

    except Exception as e:
        progress_callback(f"Error creating archive: {e}", level="ERROR")
        # Clean up temp file on failure
        if os.path.exists(temp_archive_path):
            os.remove(temp_archive_path)
        return False, f"Error creating archive: {e}", None, None

    # Encryption (if enabled)
    final_archive_path = temp_archive_path
    if encryption_enabled:
        progress_callback("Encrypting archive...", level="INFO")
        try:
            with open(temp_archive_path, 'rb') as f:
                data_to_encrypt = f.read()

            encrypted_data = None
            encrypt_error = None

            if encryption_plugin: # Use the provided plugin
                try:
                    encrypted_data, encrypt_error = encryption_plugin.encrypt(data_to_encrypt, passphrase)
                except Exception as e:
                    encrypt_error = f"Error during plugin encryption: {e}"
            else: # Fallback to built-in AES if no plugin or plugin fails
                try:
                    encrypted_data, encrypt_error = encrypt_string_with_key(data_to_encrypt, passphrase)
                except Exception as e:
                    encrypt_error = f"Error during built-in AES encryption: {e}"

            if encrypt_error:
                progress_callback(f"Encryption failed: {encrypt_error}", level="ERROR")
                if os.path.exists(temp_archive_path): os.remove(temp_archive_path)
                return False, f"Encryption failed: {encrypt_error}", None, None

            encrypted_archive_path = temp_archive_path + ".enc"
            with open(encrypted_archive_path, 'wb') as f:
                f.write(encrypted_data)
            final_archive_path = encrypted_archive_path
            
            # Remove original (unencrypted) temporary archive
            if os.path.exists(temp_archive_path):
                os.remove(temp_archive_path)

            progress_callback("Archive encrypted successfully.", level="INFO")
        except Exception as e:
            progress_callback(f"Error during encryption process: {e}", level="ERROR")
            if os.path.exists(temp_archive_path): os.remove(temp_archive_path)
            if os.path.exists(final_archive_path) and final_archive_path != temp_archive_path: os.remove(final_archive_path)
            return False, f"Error during encryption process: {e}", None, None
    
    # Calculate hash of the final archive (encrypted or not)
    file_hash = calculate_file_hash(final_archive_path)
    progress_callback(f"Calculated hash of archive: {file_hash}", level="INFO")

    # Upload to destinations
    upload_success = True
    upload_messages = []

    for dest in destinations:
        dest_type = dest["type"]
        current_dest_success = False
        current_dest_message = ""

        if dest_type == "local":
            destination_path = dest["path"]
            progress_callback(f"Uploading to local/NAS: {destination_path}", level="INFO")
            try:
                os.makedirs(destination_path, exist_ok=True)
                shutil.copy(final_archive_path, os.path.join(destination_path, os.path.basename(final_archive_path)))
                current_dest_success = True
                current_dest_message = "Local/NAS upload successful."
            except Exception as e:
                current_dest_success = False
                current_dest_message = f"Local/NAS upload failed: {e}"
        
        elif dest_type == "hetzner_sftp":
            sftp_details = {
                "host": dest["host"],
                "username": dest["username"],
                "password": dest["password"], # Pass already decrypted password
                "remote_path": dest["remote_path"]
            }
            progress_callback(f"Uploading to Hetzner SFTP: {sftp_details['host']}{sftp_details['remote_path']}", level="INFO")
            current_dest_success, current_dest_message = upload_file_sftp(
                final_archive_path, os.path.basename(final_archive_path), sftp_details, progress_callback
            )
        
        else: # Plugin-Destination
            plugin_instance = dest.get("plugin_instance") # Should already be an instance from main.py
            if isinstance(plugin_instance, BackupDestinationPlugin):
                progress_callback(f"Uploading to plugin destination '{plugin_instance.get_name()}'...", level="INFO")
                try:
                    current_dest_success, current_dest_message = plugin_instance.upload_file(
                        final_archive_path, os.path.basename(final_archive_path)
                    )
                except Exception as e:
                    current_dest_success = False
                    current_dest_message = f"Error during plugin upload for '{plugin_instance.get_name()}': {e}"
            else:
                current_dest_success = False
                current_dest_message = f"Internal Error: Invalid plugin instance for type: {dest_type}"
        
        if not current_dest_success:
            upload_success = False
            progress_callback(f"Upload to {dest_type} failed: {current_dest_message}", level="ERROR")
        else:
            progress_callback(f"Upload to {dest_type} successful: {current_dest_message}", level="INFO")
        upload_messages.append(f"{dest_type}: {current_dest_message}")

    # Cleanup final archive (encrypted or not)
    try:
        if os.path.exists(final_archive_path):
            os.remove(final_archive_path)
        progress_callback("Temporary and final archives cleaned up.", level="INFO")
    except Exception as e:
        progress_callback(f"Error cleaning up temporary archive: {e}", level="ERROR")

    return upload_success, " ".join(upload_messages), file_hash, os.path.basename(final_archive_path)

# --- Core Restore Logic ---
def get_archive_contents(archive_path, passphrase, progress_callback=None, encryption_plugin: EncryptionPlugin = None):
    if not progress_callback:
        progress_callback = print

    if not os.path.exists(archive_path):
        return [], f"Archive file not found: {archive_path}"

    temp_decrypted_path = None
    try:
        if archive_path.endswith(".enc"):
            progress_callback("Attempting to decrypt archive for listing...", level="INFO")
            with open(archive_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = None
            decrypt_error = None

            if encryption_plugin:
                try:
                    decrypted_data, decrypt_error = encryption_plugin.decrypt(encrypted_data, passphrase)
                except Exception as e:
                    decrypt_error = f"Error during plugin decryption: {e}"
            else: # Fallback to built-in AES
                try:
                    decrypted_data, decrypt_error = decrypt_string_with_key(encrypted_data, passphrase)
                except Exception as e:
                    decrypt_error = f"Error during built-in AES decryption: {e}"

            if decrypt_error:
                progress_callback(f"Decryption failed: {decrypt_error}", level="ERROR")
                return [], f"Decryption failed: {decrypt_error}"
            
            temp_decrypted_fd, temp_decrypted_path = tempfile.mkstemp(suffix=".tmp_decrypted")
            os.close(temp_decrypted_fd)
            with open(temp_decrypted_path, 'wb') as f:
                f.write(decrypted_data)
            
            archive_to_open = temp_decrypted_path
            progress_callback("Archive decrypted for listing.", level="INFO")
        else:
            archive_to_open = archive_path

        contents = []
        if archive_to_open.endswith(".zip") or archive_to_open.endswith(".tmp_decrypted") and ".zip" in archive_to_open: # Check for zip content
            try:
                with zipfile.ZipFile(archive_to_open, 'r') as zipf:
                    contents = zipf.namelist()
            except zipfile.BadZipFile:
                progress_callback("Not a valid ZIP file.", level="ERROR")
                return [], "Not a valid ZIP file. Possibly incorrect decryption or format."
        elif archive_to_open.endswith(".tar.gz") or archive_to_open.endswith(".tar.bz2") or (archive_to_open.endswith(".tmp_decrypted") and (".tar.gz" in archive_to_open or ".tar.bz2" in archive_to_open)):
            try:
                mode = 'r:gz' if ".tar.gz" in archive_to_open else 'r:bz2'
                with tarfile.open(archive_to_open, mode) as tar:
                    contents = tar.getnames()
            except tarfile.ReadError:
                progress_callback("Not a valid TAR archive.", level="ERROR")
                return [], "Not a valid TAR archive. Possibly incorrect decryption or format."
        else:
            return [], "Unsupported archive format for listing."

        return contents, None

    except Exception as e:
        progress_callback(f"Error listing archive contents: {e}", level="ERROR")
        return [], f"Error listing archive contents: {e}"
    finally:
        if temp_decrypted_path and os.path.exists(temp_decrypted_path):
            os.remove(temp_decrypted_path)


def perform_restore(archive_path, destination_path, overwrite_existing, encryption_enabled, passphrase, progress_callback=None, encryption_plugin: EncryptionPlugin = None):
    if not progress_callback:
        progress_callback = print

    if not os.path.exists(archive_path):
        return False, f"Archive file not found: {archive_path}"
    if not os.path.isdir(destination_path):
        try:
            os.makedirs(destination_path, exist_ok=True)
            progress_callback(f"Created destination directory: {destination_path}", level="INFO")
        except Exception as e:
            return False, f"Failed to create destination directory: {e}"

    temp_decrypted_path = None
    try:
        if encryption_enabled:
            progress_callback("Attempting to decrypt archive for restore...", level="INFO")
            with open(archive_path, 'rb') as f:
                encrypted_data = f.read()
            
            decrypted_data = None
            decrypt_error = None

            if encryption_plugin:
                try:
                    decrypted_data, decrypt_error = encryption_plugin.decrypt(encrypted_data, passphrase)
                except Exception as e:
                    decrypt_error = f"Error during plugin decryption: {e}"
            else: # Fallback to built-in AES
                try:
                    decrypted_data, decrypt_error = decrypt_string_with_key(encrypted_data, passphrase)
                except Exception as e:
                    decrypt_error = f"Error during built-in AES decryption: {e}"

            if decrypt_error:
                progress_callback(f"Decryption failed: {decrypt_error}", level="ERROR")
                return False, f"Decryption failed: {decrypt_error}"
            
            temp_decrypted_fd, temp_decrypted_path = tempfile.mkstemp(suffix=".tmp_decrypted")
            os.close(temp_decrypted_fd)
            with open(temp_decrypted_path, 'wb') as f:
                f.write(decrypted_data)
            
            archive_to_open = temp_decrypted_path
            progress_callback("Archive decrypted for restore.", level="INFO")
        else:
            archive_to_open = archive_path

        if archive_to_open.endswith(".zip") or archive_to_open.endswith(".tmp_decrypted") and (".zip" in archive_to_open):
            with zipfile.ZipFile(archive_to_open, 'r') as zipf:
                for member in zipf.namelist():
                    member_path = os.path.join(destination_path, member)
                    if not overwrite_existing and os.path.exists(member_path):
                        progress_callback(f"Skipping existing file (overwrite disabled): {member_path}", level="WARNING")
                        continue
                    progress_callback(f"Extracting: {member_path}", level="DEBUG")
                    zipf.extract(member, destination_path)
            return True, "ZIP archive restored successfully."
        elif archive_to_open.endswith(".tar.gz") or archive_to_open.endswith(".tar.bz2") or (archive_to_open.endswith(".tmp_decrypted") and (".tar.gz" in archive_to_open or ".tar.bz2" in archive_to_open)):
            mode = 'r:gz' if ".tar.gz" in archive_to_open else 'r:bz2'
            with tarfile.open(archive_to_open, mode) as tar:
                for member in tar.getnames():
                    member_path = os.path.join(destination_path, member)
                    if not overwrite_existing and os.path.exists(member_path):
                        progress_callback(f"Skipping existing file (overwrite disabled): {member_path}", level="WARNING")
                        continue
                    progress_callback(f"Extracting: {member_path}", level="DEBUG")
                    tar.extract(member, destination_path)
            return True, "TAR archive restored successfully."
        else:
            return False, "Unsupported archive format for restore."

    except Exception as e:
        progress_callback(f"Error during restore: {e}", level="ERROR")
        return False, f"Error during restore: {e}"
    finally:
        if temp_decrypted_path and os.path.exists(temp_decrypted_path):
            os.remove(temp_decrypted_path)


# --- Retention Policy Logic ---
def apply_retention_policy_cli(
    destination_path,
    retention_enabled,
    retention_type,
    retention_value,
    is_sftp=False,
    sftp_details=None,
    destination_plugin_instance: BackupDestinationPlugin = None, # NEU
    cli_log_callback=None
):
    if not cli_log_callback:
        cli_log_callback = print

    if not retention_enabled:
        cli_log_callback("Retention policy is disabled. Skipping.", level="INFO")
        return

    cli_log_callback(f"Applying retention policy: type={retention_type}, value={retention_value}", level="INFO")

    files_in_dest = []
    if is_sftp and sftp_details:
        files_in_dest, error = list_files_sftp(destination_path, sftp_details, cli_log_callback)
        if error:
            cli_log_callback(f"Error listing SFTP files for retention: {error}", level="ERROR")
            return
    elif destination_plugin_instance: # NEU: Handle plugin destination
        try:
            files_in_dest, error_msg = destination_plugin_instance.list_files("") # Plugin handles its own paths
            if error_msg:
                cli_log_callback(f"Failed to list files for plugin destination '{destination_plugin_instance.get_name()}': {error_msg}", level="ERROR")
                return
        except Exception as e:
            cli_log_callback(f"Error listing files for plugin destination '{destination_plugin_instance.get_name()}': {e}", level="ERROR")
            return
    else: # Local/NAS
        if not os.path.isdir(destination_path):
            cli_log_callback(f"Local destination path '{destination_path}' not found for retention.", level="ERROR")
            return
        files_in_dest = [f for f in os.listdir(destination_path) if os.path.isfile(os.path.join(destination_path, f))]

    # Filter for backup files (e.g., "backup_jobname_YYYYMMDD_HHMMSS.zip")
    backup_files = []
    for f_name in files_in_dest:
        # Assuming backup files start with "backup_" and have a date/time stamp
        # This regex would be more robust: r"backup_[\w-]+_(\d{8}_\d{6})\.(zip|tar\.gz|tar\.bz2)(\.enc)?"
        if f_name.startswith("backup_") and any(ext in f_name for ext in [".zip", ".tar.gz", ".tar.bz2"]):
            try:
                # Extract datetime from filename (adjust regex if format changes)
                # Simple extraction: find YYYYMMDD_HHMMSS
                parts = f_name.split('_')
                if len(parts) >= 3:
                    date_time_str = parts[-2] + "_" + parts[-1].split('.')[0] # e.g. 20240101_123000
                    file_datetime = datetime.datetime.strptime(date_time_str, '%Y%m%d_%H%M%S')
                    backup_files.append((file_datetime, f_name))
            except ValueError:
                cli_log_callback(f"Could not parse datetime from filename: {f_name}", level="WARNING")
                continue

    backup_files.sort(key=lambda x: x[0], reverse=True) # Sort newest first

    files_to_delete = []

    if retention_type == "days":
        min_date = datetime.datetime.now() - datetime.timedelta(days=retention_value)
        for file_dt, file_name in backup_files:
            if file_dt < min_date:
                files_to_delete.append(file_name)
    elif retention_type == "count":
        if len(backup_files) > retention_value:
            files_to_delete = [file_name for _, file_name in backup_files[retention_value:]]
    else:
        cli_log_callback(f"Unknown retention type: {retention_type}", level="ERROR")
        return

    cli_log_callback(f"Found {len(files_to_delete)} files to delete based on retention policy.", level="INFO")

    for old_file in files_to_delete:
        full_path_to_delete = old_file # For plugins and SFTP, just the filename is passed to their methods
        if not is_sftp and not destination_plugin_instance: # Local/NAS
            full_path_to_delete = os.path.join(destination_path, old_file)
        
        try:
            if is_sftp and sftp_details:
                success, msg = delete_file_sftp(os.path.join(destination_path, old_file), sftp_details, cli_log_callback)
                if success:
                    cli_log_callback(f"Deleted old backup: {old_file} from SFTP.", level="INFO")
                else:
                    cli_log_callback(f"Failed to delete {old_file} from SFTP: {msg}", level="ERROR")
            elif destination_plugin_instance: # NEU: Handle plugin delete
                # Pass the filename/basename if the plugin expects that, or full path if it handles its own root.
                # Assuming plugin.delete_file expects the name as listed by plugin.list_files
                success, msg = destination_plugin_instance.delete_file(old_file) 
                if success:
                    cli_log_callback(f"Deleted old backup: {old_file} from plugin destination.", level="INFO")
                else:
                    cli_log_callback(f"Failed to delete {old_file} from plugin destination: {msg}", level="ERROR")
            else: # Local/NAS
                os.remove(full_path_to_delete)
                cli_log_callback(f"Deleted old backup: {full_path_to_delete}", level="INFO")
        except Exception as e:
            cli_log_callback(f"Error deleting old backup {old_file}: {e}", level="ERROR")
