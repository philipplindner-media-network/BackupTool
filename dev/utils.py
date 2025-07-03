import hashlib
import os

def calculate_sha256(file_path: str, progress_callback=None) -> str:
    """
    Berechnet den SHA256-Hash einer Datei.
    progress_callback (optional): Eine Funktion, die für Fortschritts-Updates aufgerufen wird.
    """
    sha256_hash = hashlib.sha256()
    buffer_size = 65536 # 64KB Puffer

    if not os.path.exists(file_path):
        if progress_callback:
            progress_callback(f"ERROR: File not found for SHA256 calculation: {file_path}", level="ERROR")
        return None

    try:
        file_size = os.path.getsize(file_path)
        bytes_read = 0
        with open(file_path, "rb") as f:
            while True:
                data = f.read(buffer_size)
                if not data:
                    break
                sha256_hash.update(data)
                bytes_read += len(data)
                if progress_callback:
                    # Der Fortschritt beim Hashen ist oft der letzte Schritt vor dem Abschluss
                    # und sollte nicht zu granular sein, um die GUI nicht zu überfluten.
                    # Wir können hier eine prozentuale Fortschrittsaktualisierung hinzufügen.
                    percentage = (bytes_read / file_size) * 100
                    # progress_callback wird in main.py für den Gesamtprozess genutzt
                    # Hier könnte man einen separaten "sub-progress" oder nur grobe Updates geben.
                    # Für diesen Zweck ist es oft besser, dies nur als "Calculating..." zu melden
                    # oder nur bei größeren Schritten zu aktualisieren (z.B. alle 10%).
                    # Hier nur ein Beispiel, wie es integriert werden könnte, wenn gewünscht:
                    # progress_callback(f"Hashing: {bytes_read}/{file_size} bytes ({percentage:.1f}%)", percentage=percentage)
                    pass # Standardmäßig nichts tun, nur für das Haupt-Backup/Restore den Fortschritt zeigen.
        return sha256_hash.hexdigest()
    except Exception as e:
        if progress_callback:
            progress_callback(f"ERROR: Failed to calculate SHA256 for {file_path}: {e}", level="ERROR")
        return None
