import os
import tarfile
import zipfile
import shutil
import hashlib
import paramiko
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from base64 import urlsafe_b64encode, urlsafe_b64decode
import secrets
import io
import tempfile
from datetime import datetime, timedelta
# WICHTIG: Wenn Sie genaue Monats- oder Jahresberechnungen für Retention Policy benötigen,
# müssen Sie 'pip install python-dateutil' ausführen und dies importieren:
# from dateutil.relativedelta import relativedelta


# ====================================================================================================
# HELPER FUNCTIONS
# ====================================================================================================

def derive_key_and_salt(passphrase: str, salt: bytes = None) -> (bytes, bytes):
    """
    Leitet einen Schlüssel und Salt von einer Passphrase ab.
    Wenn kein Salt bereitgestellt wird, wird ein neues generiert.
    """
    if salt is None:
        salt = secrets.token_bytes(16)  # 16-Byte Salt
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256-bit key for AES256
        salt=salt,
        iterations=100000, # Hohe Iterationszahl für Sicherheit
        backend=default_backend()
    )
    key = kdf.derive(passphrase.encode('utf-8'))
    return key, salt

def encrypt_data(data: bytes, passphrase: str) -> bytes:
    """
    Verschlüsselt Daten mit AES256 im GCM-Modus.
    Gibt Salt, Nonce (IV), verschlüsselte Daten und Authentifizierungs-Tag zurück.
    """
    key, salt = derive_key_and_salt(passphrase)
    
    # Nonce (Initialization Vector) generieren
    iv = os.urandom(12) # 96-bit Nonce für GCM

    cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    
    ciphertext = encryptor.update(data) + encryptor.finalize()
    tag = encryptor.tag # GCM Tag

    # Kombiniere Salt, IV, Tag und Ciphertext für die Speicherung
    # Format: salt (16 bytes) + iv (12 bytes) + tag (16 bytes) + ciphertext
    return salt + iv + tag + ciphertext

def decrypt_data(encrypted_data: bytes, passphrase: str) -> bytes:
    """
    Entschlüsselt Daten, die mit AES256 im GCM-Modus verschlüsselt wurden.
    Erwartet das Format: salt (16 bytes) + iv (12 bytes) + tag (16 bytes) + ciphertext.
    """
    if len(encrypted_data) < 44: # 16 (salt) + 12 (iv) + 16 (tag)
        raise ValueError("Encrypted data is too short to contain salt, IV, and tag.")

    salt = encrypted_data[:16]
    iv = encrypted_data[16:28]
    tag = encrypted_data[28:44]
    ciphertext = encrypted_data[44:]

    key, _ = derive_key_and_salt(passphrase, salt)
    
    cipher = Cipher(algorithms.AES(key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    
    try:
        decrypted_data = decryptor.update(ciphertext) + decryptor.finalize()
        return decrypted_data
    except Exception as e:
        raise ValueError(f"Decryption failed, likely due to incorrect passphrase or corrupted data: {e}")

def calculate_sha256(file_path):
    """Berechnet den SHA256-Hash einer Datei."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        # Lesen in Blöcken, um große Dateien zu handhaben
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def calculate_sha256_from_bytes(data_bytes):
    """Berechnet den SHA256-Hash von Bytes-Daten."""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data_bytes)
    return sha256_hash.hexdigest()

def get_sftp_client(sftp_host, sftp_username, sftp_password):
    """Erstellt und gibt einen SFTPClient zurück."""
    try:
        # SFTP Host kann auch Port enthalten (user@host:port)
        hostname = sftp_host
        port = 22
        if ':' in sftp_host:
            hostname_parts = sftp_host.rsplit(':', 1)
            hostname = hostname_parts[0]
            port = int(hostname_parts[1])
        
        # Extrahiere Benutzername, falls im Hoststring enthalten (z.B. user@host)
        if '@' in hostname:
            sftp_username = hostname.split('@')[0]
            hostname = hostname.split('@')[1]

        transport = paramiko.Transport((hostname, port))
        transport.connect(username=sftp_username, password=sftp_password)
        sftp_client = paramiko.SFTPClient.from_transport(transport)
        return sftp_client, transport
    except Exception as e:
        raise Exception(f"Failed to connect to SFTP server: {e}")

# ====================================================================================================
# BACKUP LOGIC
# ====================================================================================================

def perform_backup(source_paths, nas_path, hetzner_host, hetzner_password,
                   compress_type, encrypt_enabled, passphrase, progress_callback):
    
    backup_filename_base = datetime.now().strftime("backup_%Y%m%d_%H%M%S")
    temp_archive_path = os.path.join(tempfile.gettempdir(), backup_filename_base)

    if compress_type == "tar.gz":
        temp_archive_path += ".tar.gz"
    elif compress_type == "zip":
        temp_archive_path += ".zip"

    final_backup_path = temp_archive_path # Pfad zur unverschlüsselten/unverschlüsselten Datei
    calculated_hash = None
    
    progress_callback(f"Starting backup process. Archiving to {temp_archive_path}...", 5)

    try:
        # 1. Archive sources
        if compress_type == "tar.gz":
            with tarfile.open(temp_archive_path, "w:gz") as tar:
                for path in source_paths:
                    if os.path.exists(path):
                        tar.add(path, arcname=os.path.basename(path))
                        progress_callback(f"Added {os.path.basename(path)} to archive.", 10 + source_paths.index(path) * (20 / len(source_paths)))
                    else:
                        progress_callback(f"Warning: Source path not found: {path}. Skipping.", level="WARNING")
                        
        elif compress_type == "zip":
            with zipfile.ZipFile(temp_archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for path in source_paths:
                    if os.path.exists(path):
                        for root, _, files in os.walk(path):
                            for file in files:
                                full_file_path = os.path.join(root, file)
                                archive_name = os.path.relpath(full_file_path, os.path.dirname(path))
                                zipf.write(full_file_path, archive_name)
                                progress_callback(f"Added {archive_name} to archive.", 10 + source_paths.index(path) * (20 / len(source_paths)))
                    else:
                        progress_callback(f"Warning: Source path not found: {path}. Skipping.", level="WARNING")

        progress_callback("Archiving complete.", 30)

        # 2. Encrypt if enabled
        if encrypt_enabled:
            progress_callback("Encrypting archive...", 35)
            if not passphrase:
                progress_callback("Error: Encryption enabled but no passphrase provided.", level="ERROR")
                return False, None, None
            
            with open(temp_archive_path, "rb") as f_in:
                data_to_encrypt = f_in.read()
            
            encrypted_data = encrypt_data(data_to_encrypt, passphrase)
            
            os.remove(temp_archive_path) # Originaldatei löschen
            final_backup_path = temp_archive_path + ".enc"
            with open(final_backup_path, "wb") as f_out:
                f_out.write(encrypted_data)
            progress_callback("Encryption complete.", 45)

        # 3. Calculate SHA256 Hash
        progress_callback("Calculating SHA256 hash...", 50)
        calculated_hash = calculate_sha256(final_backup_path)
        progress_callback(f"SHA256 Hash: {calculated_hash}", 60, level="INFO")

        # 4. Upload to destinations
        upload_success = True
        
        # Upload to NAS
        if nas_path:
            progress_callback(f"Uploading to NAS: {nas_path}", 65)
            try:
                dest_nas_path = os.path.join(nas_path, os.path.basename(final_backup_path))
                shutil.copy2(final_backup_path, dest_nas_path)
                progress_callback(f"Backup uploaded to NAS: {dest_nas_path}", 75)
            except Exception as e:
                progress_callback(f"Error uploading to NAS: {e}", level="ERROR")
                upload_success = False

        # Upload to Hetzner Storage Box (SFTP)
        if hetzner_host and hetzner_password:
            progress_callback(f"Uploading to Hetzner Storage Box ({hetzner_host})...", 80)
            sftp_client = None
            transport = None
            try:
                # Assuming username is part of hetzner_host (user@host:port) or passed separately
                # For SFTP, we pass username explicitly to get_sftp_client
                username_for_sftp = hetzner_host.split('@')[0] if '@' in hetzner_host else "your_sftp_user" # Default if not in host string
                
                sftp_client, transport = get_sftp_client(hetzner_host, username_for_sftp, hetzner_password)
                
                remote_path = os.path.basename(final_backup_path)
                sftp_client.put(final_backup_path, remote_path)
                progress_callback(f"Backup uploaded to Hetzner Storage Box: {remote_path}", 90)
            except Exception as e:
                progress_callback(f"Error uploading to Hetzner Storage Box: {e}", level="ERROR")
                upload_success = False
            finally:
                if sftp_client:
                    sftp_client.close()
                if transport:
                    transport.close()

        if upload_success:
            progress_callback("All uploads completed.", 95)
        else:
            progress_callback("Warning: Some uploads failed.", level="WARNING")
            return False, calculated_hash, os.path.basename(final_backup_path) # Return hash and filename even if upload partially fails

        return True, calculated_hash, os.path.basename(final_backup_path)

    except Exception as e:
        progress_callback(f"An unexpected error occurred during backup: {e}", level="ERROR")
        return False, None, None
    finally:
        # Clean up temporary archive file
        if os.path.exists(final_backup_path):
            os.remove(final_backup_path)
            progress_callback(f"Temporary archive deleted: {final_backup_path}", 100)
        elif os.path.exists(temp_archive_path): # falls Verschlüsselung fehlschlug
             os.remove(temp_archive_path)
             progress_callback(f"Temporary archive deleted: {temp_archive_path}", 100)

# ====================================================================================================
# RESTORE LOGIC
# ====================================================================================================

def perform_restore(source_type, source_path, destination_path, overwrite_existing, sftp_config, log_callback):
    """
    Führt eine Wiederherstellung aus.

    Args:
        source_type (str): 'nas_local' oder 'hetzner_sftp'.
        source_path (str): Der Pfad zum Archiv (lokal oder auf SFTP-Server).
        destination_path (str): Der Zielpfad für die Wiederherstellung.
        overwrite_existing (bool): True, um existierende Dateien zu überschreiben.
        sftp_config (dict): SFTP-Verbindungsinformationen (host, port, username, password) wenn source_type 'hetzner_sftp' ist.
        log_callback (function): Callback-Funktion zum Loggen von Nachrichten.
    """
    log_callback(f"Starting restore from {source_type} path: {source_path} to {destination_path}", level="INFO")

    if not os.path.exists(destination_path):
        try:
            os.makedirs(destination_path)
            log_callback(f"Created destination directory: {destination_path}", level="INFO")
        except OSError as e:
            return False, f"Failed to create destination directory {destination_path}: {e}"

    # Determine the archive path on the local filesystem (after download if SFTP)
    local_archive_path = None

    if source_type == "nas_local":
        local_archive_path = source_path
    elif source_type == "hetzner_sftp":
        try:
            log_callback(f"Attempting to download archive from SFTP: {source_path}", level="INFO")
            
            transport = paramiko.Transport((sftp_config['host'], sftp_config['port']))
            transport.connect(username=sftp_config['username'], password=sftp_config['password'])
            sftp = paramiko.SFTPClient.from_transport(transport)

            # Create a temporary file for the downloaded archive
            temp_dir = os.path.join(os.path.expanduser("~"), ".backup_tool", "temp_restore")
            os.makedirs(temp_dir, exist_ok=True)
            local_archive_path = os.path.join(temp_dir, os.path.basename(source_path))

            # Download the file
            sftp.get(source_path, local_archive_path)
            log_callback(f"Successfully downloaded {source_path} to {local_archive_path}", level="INFO")

        except paramiko.AuthenticationException:
            return False, "SFTP Authentication failed. Check username/password."
        except paramiko.SSHException as e:
            return False, f"Could not establish SFTP connection or transfer file: {e}"
        except Exception as e:
            return False, f"An unexpected error occurred during SFTP download: {e}"
        finally:
            if 'sftp' in locals() and sftp:
                sftp.close()
            if 'transport' in locals() and transport:
                transport.close()
    else:
        return False, "Invalid source type specified for restore."

    if not local_archive_path or not os.path.exists(local_archive_path):
        return False, f"Archive file not found locally: {local_archive_path}"

    # Proceed with extraction based on file type
    try:
        if zipfile.is_zipfile(local_archive_path):
            with zipfile.ZipFile(local_archive_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    member_path = os.path.join(destination_path, member)
                    if overwrite_existing or not os.path.exists(member_path):
                        zip_ref.extract(member, destination_path)
                        log_callback(f"Extracted {member}", level="DEBUG")
                    else:
                        log_callback(f"Skipped {member} (file exists and overwrite is false)", level="DEBUG")
            log_callback(f"Successfully restored from ZIP archive {local_archive_path} to {destination_path}", level="INFO")
            
        elif tarfile.is_tarfile(local_archive_path):
            with tarfile.open(local_archive_path, 'r:gz') as tar_ref: # Assuming it's a .tar.gz
                for member in tar_ref.getmembers():
                    member_path = os.path.join(destination_path, member.name)
                    if overwrite_existing or not os.path.exists(member_path):
                        tar_ref.extract(member, destination_path)
                        log_callback(f"Extracted {member.name}", level="DEBUG")
                    else:
                        log_callback(f"Skipped {member.name} (file exists and overwrite is false)", level="DEBUG")
            log_callback(f"Successfully restored from TAR.GZ archive {local_archive_path} to {destination_path}", level="INFO")

        else:
            return False, "Unsupported archive format. Only .zip and .tar.gz are supported."
        
        return True, "Restore completed successfully."

    except Exception as e:
        return False, f"Failed to extract archive {os.path.basename(local_archive_path)}: {e}"
    finally:
        # Clean up temporary downloaded file if it came from SFTP
        if source_type == "hetzner_sftp" and os.path.exists(local_archive_path):
            try:
                os.remove(local_archive_path)
                log_callback(f"Cleaned up temporary downloaded archive: {local_archive_path}", level="DEBUG")
            except Exception as e:
                log_callback(f"Warning: Could not remove temporary archive {local_archive_path}: {e}", level="WARNING")



def get_archive_contents(source_backup_path, is_encrypted, passphrase,
                         is_sftp_source, sftp_host, sftp_username, sftp_password,
                         progress_callback):
    """
    Ruft den Inhalt eines Backup-Archivs ab, ohne es vollständig wiederherzustellen.
    """
    temp_download_path = None
    archive_file_to_process = source_backup_path
    contents = []

    try:
        if is_sftp_source:
            progress_callback(f"Downloading archive from SFTP to view contents: {sftp_host}/{source_backup_path}", 10)
            temp_download_path = os.path.join(tempfile.gettempdir(), os.path.basename(source_backup_path))
            sftp_client = None
            transport = None
            try:
                sftp_client, transport = get_sftp_client(sftp_host, sftp_username, sftp_password)
                sftp_client.get(source_backup_path, temp_download_path)
                archive_file_to_process = temp_download_path
                progress_callback("SFTP download complete for content view.", 30)
            except Exception as e:
                progress_callback(f"Error downloading from SFTP for content view: {e}", level="ERROR")
                return None
            finally:
                if sftp_client:
                    sftp_client.close()
                if transport:
                    transport.close()
        else:
            if not os.path.exists(source_backup_path):
                progress_callback(f"Error: Local backup file not found for content view: {source_backup_path}", level="ERROR")
                return None
            progress_callback(f"Using local backup file for content view: {source_backup_path}", 30)

        # Entschlüsseln, falls verschlüsselt
        actual_archive_path_for_read = archive_file_to_process
        if is_encrypted:
            progress_callback("Decrypting archive for content view...", 40)
            if not passphrase:
                progress_callback("Error: Archive is encrypted but no passphrase provided for content view.", level="ERROR")
                return None
            
            try:
                with open(archive_file_to_process, "rb") as f_in:
                    encrypted_data = f_in.read()
                
                decrypted_data = decrypt_data(encrypted_data, passphrase)
                
                temp_decrypted_path = os.path.join(tempfile.gettempdir(), "decrypted_view_" + os.path.basename(source_backup_path).replace(".enc", ""))
                with open(temp_decrypted_path, "wb") as f_out:
                    f_out.write(decrypted_data)
                
                actual_archive_path_for_read = temp_decrypted_path
                progress_callback("Decryption complete for content view.", 60)
            except ValueError as ve:
                progress_callback(f"Decryption error for content view: {ve}", level="ERROR")
                return None
            except Exception as e:
                progress_callback(f"An unexpected error occurred during decryption for content view: {e}", level="ERROR")
                return None

        # Inhalte auflisten
        progress_callback(f"Listing contents of archive: {os.path.basename(actual_archive_path_for_read)}", 70)
        if actual_archive_path_for_read.endswith(".tar.gz"):
            try:
                with tarfile.open(actual_archive_path_for_read, "r:gz") as tar:
                    contents = [member.name for member in tar.getmembers() if member.isreg()] # Nur reguläre Dateien
                progress_callback("Tar.gz contents listed.", 90)
            except tarfile.ReadError as e:
                progress_callback(f"Error reading tar.gz file: {e}. File might be corrupted or not a valid tar.gz.", level="ERROR")
                return None
        elif actual_archive_path_for_read.endswith(".zip"):
            try:
                with zipfile.ZipFile(actual_archive_path_for_read, 'r') as zipf:
                    contents = [info.filename for info in zipf.infolist() if not info.is_dir()] # Nur Dateien, keine Verzeichnisse
                progress_callback("Zip contents listed.", 90)
            except zipfile.BadZipFile as e:
                progress_callback(f"Error reading zip file: {e}. File might be corrupted or not a valid zip.", level="ERROR")
                return None
        else:
            progress_callback(f"Error: Unknown archive format for content view: {os.path.basename(actual_archive_path_for_read)}", level="ERROR")
            return None

        progress_callback("Archive contents retrieved successfully.", 100)
        return contents

    except Exception as e:
        progress_callback(f"An unexpected error occurred while getting archive contents: {e}", level="ERROR")
        return None
    finally:
        # Temporäre Dateien bereinigen
        if temp_download_path and os.path.exists(temp_download_path):
            os.remove(temp_download_path)
            progress_callback(f"Temporary download file deleted for content view: {temp_download_path}", 100)
        
        if actual_archive_path_for_read and actual_archive_path_for_read != source_backup_path and os.path.exists(actual_archive_path_for_read):
            os.remove(actual_archive_path_for_read)
            progress_callback(f"Temporary decrypted file deleted for content view: {actual_archive_path_for_read}", 100)

# ====================================================================================================
# RETENTION POLICY LOGIC (NEU)
# ====================================================================================================

def get_backup_files_in_directory(path, is_sftp, sftp_client=None):
    """
    Listet Backup-Dateien in einem Verzeichnis auf (lokal oder SFTP),
    filtert nach dem erwarteten Backup-Dateinamenformat und extrahiert Zeitstempel.
    Gibt eine Liste von (datetime_obj, filename) Tupeln zurück.
    """
    backup_files = []
    
    if is_sftp:
        try:
            # listdir gibt nur Dateinamen zurück, keine Pfade
            for entry in sftp_client.listdir(path):
                # Beispiel: backup_20250622_180000.tar.gz.enc
                if entry.startswith("backup_") and ('.tar.gz' in entry or '.zip' in entry):
                    try:
                        # Extrahiere Datum und Uhrzeit
                        parts = entry.split('_')
                        date_str = parts[1] # YYYYMMDD
                        time_str = parts[2].split('.')[0] # HHMMSS
                        
                        dt_obj = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                        backup_files.append((dt_obj, entry))
                    except (IndexError, ValueError):
                        # Ignoriere Dateien, die nicht unserem Format entsprechen
                        continue
        except Exception as e:
            raise Exception(f"Failed to list SFTP directory {path}: {e}")
    else:
        try:
            for entry in os.listdir(path):
                # Beispiel: backup_20250622_180000.tar.gz.enc
                if entry.startswith("backup_") and ('.tar.gz' in entry or '.zip' in entry):
                    try:
                        # Extrahiere Datum und Uhrzeit
                        parts = entry.split('_')
                        date_str = parts[1] # YYYYMMDD
                        time_str = parts[2].split('.')[0] # HHMMSS
                        
                        dt_obj = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")
                        backup_files.append((dt_obj, entry))
                    except (IndexError, ValueError):
                        # Ignoriere Dateien, die nicht unserem Format entsprechen
                        continue
        except Exception as e:
            raise Exception(f"Failed to list local directory {path}: {e}")
            
    # Sortiere die Dateien chronologisch (älteste zuerst)
    backup_files.sort(key=lambda x: x[0])
    return backup_files


def delete_backup_file(path, filename, is_sftp, sftp_client=None):
    """
    Löscht eine einzelne Backup-Datei.
    """
    # Für SFTP ist 'path' der Remote-Pfad (oft nur '.') und 'filename' ist der Dateiname
    # Für lokale Dateien ist 'path' das Verzeichnis und 'filename' der Dateiname
    
    if is_sftp:
        full_path_remote = os.path.join(path, filename).replace("\\", "/") # SFTP nutzt Forward Slashes
        try:
            sftp_client.remove(full_path_remote)
            return True, f"Successfully deleted SFTP file: {full_path_remote}"
        except paramiko.SFTPError as e:
            return False, f"SFTP error deleting {full_path_remote}: {e}"
        except Exception as e:
            return False, f"Error deleting SFTP file {full_path_remote}: {e}"
    else:
        full_path_local = os.path.join(path, filename)
        try:
            os.remove(full_path_local)
            return True, f"Successfully deleted local file: {full_path_local}"
        except OSError as e:
            return False, f"OS error deleting {full_path_local}: {e}"
        except Exception as e:
            return False, f"Error deleting local file {full_path_local}: {e}"


def apply_retention_policy(policy_settings, nas_path, hetzner_host, hetzner_password, progress_callback):
    """
    Wendet die Aufbewahrungsrichtlinie auf die Backup-Ziele an.
    policy_settings: Dictionary mit 'enabled', 'type', 'value', 'unit', 'nas', 'hetzner'
    """
    if not policy_settings.get('enabled'):
        progress_callback("Retention policy is disabled. Skipping.", 100, level="INFO")
        return True # Nichts zu tun, daher Erfolg

    progress_callback("Applying retention policy...", 0)

    retention_type = policy_settings['type']
    retention_value = policy_settings['value']
    retention_unit = policy_settings.get('unit', 'days') # Nur relevant für Typ 'age'

    overall_success = True

    # --- Apply to NAS ---
    if policy_settings.get('nas') and nas_path:
        progress_callback(f"Applying retention to NAS: {nas_path}", 10)
        try:
            backup_files = get_backup_files_in_directory(nas_path, is_sftp=False)
            files_to_delete = []

            if retention_type == "count":
                # Behalte die N neuesten Backups
                if len(backup_files) > retention_value:
                    files_to_delete = backup_files[:-retention_value] # Lösche die ältesten
            elif retention_type == "age":
                cutoff_date = datetime.now()
                if retention_unit == "days":
                    cutoff_date -= timedelta(days=retention_value)
                elif retention_unit == "weeks":
                    cutoff_date -= timedelta(weeks=retention_value)
                elif retention_unit == "months":
                    # Für Monate und Jahre ist relativedelta von dateutil genauer.
                    # Wenn Sie python-dateutil installiert haben, verwenden Sie es:
                    # from dateutil.relativedelta import relativedelta
                    # cutoff_date -= relativedelta(months=retention_value)
                    
                    # Ohne relativedelta: Einfache Annäherung (30.4 Tage/Monat, 365 Tage/Jahr)
                    cutoff_date -= timedelta(days=retention_value * 30.4) 
                elif retention_unit == "years":
                    # cutoff_date -= relativedelta(years=retention_value)
                    cutoff_date -= timedelta(days=retention_value * 365) # Vereinfachung
                
                for dt_obj, filename in backup_files:
                    if dt_obj < cutoff_date:
                        files_to_delete.append((dt_obj, filename))

            if files_to_delete:
                progress_callback(f"Found {len(files_to_delete)} old NAS backups to delete...", 20)
                for i, (dt_obj, filename) in enumerate(files_to_delete):
                    success, msg = delete_backup_file(nas_path, filename, is_sftp=False)
                    progress_callback(msg, 20 + (i / len(files_to_delete)) * 30)
                    if not success:
                        overall_success = False
                        progress_callback(f"Failed to delete NAS file: {filename} - {msg}", level="ERROR")
            else:
                progress_callback("No old NAS backups to delete.", 40)

        except Exception as e:
            overall_success = False
            progress_callback(f"Error applying retention to NAS: {e}", 0, level="ERROR")

    # --- Apply to Hetzner Storage Box ---
    if policy_settings.get('hetzner') and hetzner_host and hetzner_password:
        progress_callback(f"Applying retention to Hetzner Storage Box ({hetzner_host})...", 50)
        sftp_client = None
        transport = None
        try:
            # Extrahiere Benutzername und Host/Port aus hetzner_host
            username = hetzner_host.split('@')[0] if '@' in hetzner_host else "your_sftp_user" # Default
            
            sftp_client, transport = get_sftp_client(hetzner_host, username, hetzner_password)
            
            # Annahme: SFTP-Backups liegen im Root-Verzeichnis des SFTP-Accounts
            sftp_backup_path = "." # Aktuelles Verzeichnis

            backup_files = get_backup_files_in_directory(sftp_backup_path, is_sftp=True, sftp_client=sftp_client)
            files_to_delete = []

            if retention_type == "count":
                if len(backup_files) > retention_value:
                    files_to_delete = backup_files[:-retention_value] # Lösche die ältesten
            elif retention_type == "age":
                cutoff_date = datetime.now()
                if retention_unit == "days":
                    cutoff_date -= timedelta(days=retention_value)
                elif retention_unit == "weeks":
                    cutoff_date -= timedelta(weeks=retention_value)
                elif retention_unit == "months":
                    # Wenn relativedelta verfügbar, hier verwenden
                    # cutoff_date -= relativedelta(months=retention_value)
                    cutoff_date -= timedelta(days=retention_value * 30.4) 
                elif retention_unit == "years":
                    # cutoff_date -= relativedelta(years=retention_value)
                    cutoff_date -= timedelta(days=retention_value * 365)
                
                for dt_obj, filename in backup_files:
                    if dt_obj < cutoff_date:
                        files_to_delete.append((dt_obj, filename))

            if files_to_delete:
                progress_callback(f"Found {len(files_to_delete)} old Hetzner backups to delete...", 60)
                for i, (dt_obj, filename) in enumerate(files_to_delete):
                    # Für SFTP delete_backup_file, path ist der 'remote_path' ('.'), filename ist der Dateiname
                    success, msg = delete_backup_file(sftp_backup_path, filename, is_sftp=True, sftp_client=sftp_client)
                    progress_callback(msg, 60 + (i / len(files_to_delete)) * 30)
                    if not success:
                        overall_success = False
                        progress_callback(f"Failed to delete Hetzner file: {filename} - {msg}", level="ERROR")
            else:
                progress_callback("No old Hetzner backups to delete.", 90)

        except Exception as e:
            overall_success = False
            progress_callback(f"Error applying retention to Hetzner: {e}", 0, level="ERROR")
        finally:
            if sftp_client:
                sftp_client.close()
            if transport:
                transport.close()

    progress_callback("Retention policy application finished.", 100, level="INFO")
    return overall_success
