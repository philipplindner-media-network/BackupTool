## DE
# BackupTool

Eine grafische Desktop-Anwendung zur Verwaltung von lokalen Backups, NAS-Backups und Hetzner Storage Box Backups.  
Dieses Tool vereinfacht das Erstellen und Wiederherstellen von Backups und bietet Aufbewahrungsrichtlinien sowie plattformübergreifende Planung (Cron für Linux/macOS, Aufgabenplanung für Windows).

---

## Funktionen

- **Flexible Backup-Quellen & -Ziele:**  
  Sichere lokale Ordner auf lokale/NAS-Pfade oder eine Hetzner Storage Box (SFTP).
- **Kompression & Verschlüsselung:**  
  Wähle Kompressionsstufen und verschlüssele sensible Konfigurationsdaten.
- **Wiederherstellungsfunktion:**  
  Stelle Backups einfach an einen gewünschten Ort wieder her.
- **Aufbewahrungsrichtlinien:**  
  Verwalte alte Backups automatisch nach Anzahl oder Alter – sowohl lokal als auch auf der Hetzner Storage Box.
- **Plattformübergreifende Planung:**  
  - **Linux/macOS:** Integration in Cron für automatisierte Backups.
  - **Windows:** Nutzung der Aufgabenplanung für verlässliche Zeitpläne.
- **Intuitive GUI:**  
  Benutzerfreundliche Oberfläche auf Basis von Tkinter.

---

## Installation & Einrichtung

Um mit BackupTool zu starten, lade das Projekt herunter und führe das passende Installationsskript für dein Betriebssystem aus.  
Die Skripte richten Python und alle benötigten Bibliotheken ein und erstellen einen Starter für die Anwendung.

### 1. Projekt herunterladen

Du kannst das Projekt auf zwei Arten herunterladen:

#### Option A: Klonen mit Git (empfohlen für Updates)

Wenn du Git installiert hast, öffne dein Terminal (Linux/macOS) oder die Eingabeaufforderung/PowerShell (Windows) und führe Folgendes aus:

```bash
git clone https://github.com/philipplindner-media-network/BackupTool.git
cd BackupTool
```


#### Option B: ZIP herunterladen

Rufe die [BackupTool GitHub-Seite](https://github.com/philipplindner-media-network/BackupTool/) auf und klicke auf den grünen "Code"-Button, dann auf "Download ZIP".  
Entpacke die ZIP-Datei an einen Ort deiner Wahl (z.B. `C:\BackupTool` unter Windows oder `~/BackupTool` unter Linux).

### 2. Installationsskript ausführen

Wechsle in den `BackupTool`-Ordner, den du heruntergeladen oder entpackt hast.

#### Unter Linux / macOS

1. Öffne dein Terminal.
2. Wechsle in das `BackupTool`-Verzeichnis:
    ```bash
    cd pfad/zum/BackupTool # z.B. cd ~/BackupTool
    ```
3. Führe das Installationsskript aus:
    ```bash
    bash install_linux.sh
    ```
    *Das Skript führt dich durch die Installation, richtet alle Python-Komponenten ein, erstellt eine virtuelle Umgebung und einen Starter (`backuptool`) im System-PATH.*

#### Unter Windows

1. Öffne die Eingabeaufforderung (CMD) oder PowerShell.
2. Wechsle in das `BackupTool`-Verzeichnis:
    ```cmd
    cd C:\pfad\zu\BackupTool # z.B. cd C:\Users\DeinBenutzer\Downloads\BackupTool
    ```
3. Führe das Installationsskript aus:
    ```cmd
    install_windows.bat
    ```
    *Das Skript installiert die Python-Abhängigkeiten, erstellt eine virtuelle Umgebung und legt eine Batch-Datei (`backuptool.bat`) im Projektordner an.*

---

## Verwendung

### Anwendung starten

- **Linux/macOS:**  
  Nach der Installation öffne dein Terminal und tippe:
  ```bash
  backuptool
  ```
  *Falls der Befehl nicht gefunden wird, starte das Terminal neu oder melde dich ab und wieder an.  
  Alternativ kannst du das Tool direkt aus dem Projektordner starten mit `python3 main.py` (vorher virtuelle Umgebung aktivieren: `source venv/bin/activate`).*

- **Windows:**  
  Nach der Installation navigiere im Explorer in den `BackupTool`-Ordner und doppelklicke auf `backuptool.bat`.  
  Alternativ öffne die Eingabeaufforderung/PowerShell im Projektordner und führe aus:
  ```cmd
  backuptool.bat
  ```

### Backups planen

Wechsle im Programm auf den Reiter „Zeitplan“, um automatische Backups über Cron (Linux/macOS) oder die Aufgabenplanung (Windows) einzurichten.

---

## Wichtige Hinweise

- **Sicherheit:**  
  Dein Verschlüsselungsschlüssel (`secret.key`) und die Konfiguration (`config.json`) werden in einem benutzerspezifischen Anwendungsdaten-Ordner gespeichert (z.B. `~/.backup_tool` unter Linux, `%APPDATA%\BackupTool` unter Windows).  
  **Teile deinen `secret.key` niemals und sichere ihn gegebenenfalls separat!**
- **Cron/Aufgabenplanung:**  
  Bei geplanten Aufgaben läuft das Programm im Nicht-GUI-Modus. Alle Ausgaben werden in `~/.backup_tool/scheduled_backup.log` (Linux/macOS) oder `%APPDATA%\BackupTool\scheduled_backup.log` (Windows) geloggt.
- **Hetzner-Zugangsdaten:**  
  Stelle sicher, dass deine Hetzner Storage Box-Zugangsdaten im Reiter „Einstellungen“ korrekt eingetragen sind, bevor du Hetzner-Funktionen nutzt.

---

## Mitwirken

Beiträge sind willkommen! Öffne gerne Issues oder erstelle Pull Requests.

---

## Lizenz

Dieses Projekt steht unter der MIT-Lizenz – siehe die Datei [LICENSE](LICENSE) für Details.

---

## Danksagungen

- [paramiko](https://www.paramiko.org/) für SFTP-Funktionalität
- [cryptography](https://cryptography.io/) für Verschlüsselung
- [ttkthemes](https://ttkthemes.readthedocs.io/) für moderne GUI-Themes


---

## EN
# BackupTool

A graphical desktop application for managing local, NAS, and Hetzner Storage Box backups.  
This tool simplifies backup creation, restoration, and implements retention policies, with cross-platform scheduling capabilities (Cron for Linux/macOS, Task Scheduler for Windows).

---

## Features

- **Flexible Backup Sources & Destinations:**  
  Backup from local folders to local/NAS paths or Hetzner Storage Box (SFTP).
- **Compression & Encryption:**  
  Choose compression levels and encrypt sensitive configuration data.
- **Restore Functionality:**  
  Easily restore backups to a specified destination.
- **Retention Policies:**  
  Automatically manage old backups based on count or age for both local and Hetzner destinations.
- **Cross-Platform Scheduling:**  
  - **Linux/macOS:** Integrate with Cron for automated backups.
  - **Windows:** Utilize Task Scheduler for reliable scheduling.
- **Intuitive GUI:**  
  User-friendly interface built with Tkinter.

---

## Installation & Setup

To get started with BackupTool, download the project and run the appropriate installation script for your operating system.  
The scripts will handle the setup of Python, required libraries, and create a launcher for the application.

### 1. Download the Project

You can download the project in two ways:

#### Option A: Clone with Git (Recommended for updates)

If you have Git installed, open your terminal (Linux/macOS) or Command Prompt/PowerShell (Windows) and run:

```bash
git clone https://github.com/philipplindner-media-network/BackupTool.git
cd BackupTool
```


#### Option B: Download ZIP

Go to the [BackupTool GitHub page](https://github.com/philipplindner-media-network/BackupTool)  and click the green "Code" button, then "Download ZIP".  
Extract the downloaded ZIP file to a location of your choice (e.g., `C:\BackupTool` on Windows, `~/BackupTool` on Linux).

### 2. Run the Installation Script

Navigate into the `BackupTool` folder that you cloned or extracted.

#### On Linux / macOS

1. Open your terminal.
2. Navigate to the `BackupTool` directory:
    ```bash
    cd path/to/BackupTool # e.g., cd ~/BackupTool
    ```
3. Run the installation script:
    ```bash
    bash install_linux.sh
    ```
    *The script will guide you through the process, install necessary Python components, create a virtual environment, and set up a launcher command (`backuptool`) in your system's PATH.*

#### On Windows

1. Open Command Prompt (CMD) or PowerShell.
2. Navigate to the `BackupTool` directory:
    ```cmd
    cd C:\path\to\BackupTool # e.g., cd C:\Users\YourUser\Downloads\BackupTool
    ```
3. Run the installation script:
    ```cmd
    install_windows.bat
    ```
    *The script will install Python dependencies, create a virtual environment, and set up a batch file (`backuptool.bat`) within the project folder for easy launching.*

---

## Usage

### Launching the Application

- **Linux/macOS:**  
  After installation, open your terminal and type:
  ```bash
  backuptool
  ```
  *If the command is not found, restart your terminal or log out and back in.  
  Alternatively, launch directly from the project directory with `python3 main.py` after activating the virtual environment: `source venv/bin/activate`.*

- **Windows:**  
  After installation, navigate to the `BackupTool` directory in File Explorer and double-click `backuptool.bat`.  
  Alternatively, open Command Prompt/PowerShell in the `BackupTool` directory and run:
  ```cmd
  backuptool.bat
  ```

### Scheduling Backups

Navigate to the "Schedule" tab within the application to set up automated backups via Cron (Linux/macOS) or Task Scheduler (Windows).

---

## Important Notes

- **Security:**  
  Your encryption key (`secret.key`) and configuration (`config.json`) are stored in a user-specific application data directory (e.g., `~/.backup_tool` on Linux, `%APPDATA%\BackupTool` on Windows).  
  **Do NOT share your `secret.key` and back it up if necessary.**
- **Cron/Task Scheduler:**  
  When setting up scheduled tasks, the application runs in a non-GUI mode. All output will be logged to `~/.backup_tool/scheduled_backup.log` (Linux/macOS) or `%APPDATA%\BackupTool\scheduled_backup.log` (Windows).
- **Hetzner Credentials:**  
  Ensure your Hetzner Storage Box details are correctly configured in the "Settings" tab before attempting Hetzner-related operations.

---

## Contributing

Contributions are welcome! Please feel free to open issues or submit pull requests.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgements

- [paramiko](https://www.paramiko.org/) for SFTP capabilities.
- [cryptography](https://cryptography.io/) for encryption.
- [ttkthemes](https://ttkthemes.readthedocs.io/) for modern GUI themes.
