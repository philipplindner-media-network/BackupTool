##DE
# BackupTool

Eine grafische Desktop-Anwendung zur Verwaltung lokaler Backups, NAS-Backups und Hetzner Storage Box-Backups.
Dieses Tool vereinfacht die Erstellung und Wiederherstellung von Backups sowie die Implementierung von Aufbewahrungsrichtlinien.
Mit plattformübergreifenden Planungsfunktionen (Cron für Linux/macOS, Taskplaner für Windows).

## Funktionen

* **Flexible Backup-Quellen und -Ziele:** Sichern Sie von lokalen Ordnern auf lokale/NAS-Pfade oder die Hetzner Storage Box (SFTP).
* **Komprimierung und Verschlüsselung:** Wählen Sie Komprimierungsstufen und verschlüsseln Sie sensible Konfigurationsdaten.
* **Wiederherstellungsfunktion:** Stellen Sie Backups einfach an einem festgelegten Ziel wieder her.
* **Aufbewahrungsrichtlinien:** Automatische Verwaltung alter Backups basierend auf Anzahl oder Alter für lokale und Hetzner-Ziele.
* **Plattformübergreifende Planung:**
* **Linux/macOS:** Integration mit Cron für automatisierte Backups.
* **Windows:** Nutzen Sie den Taskplaner für eine zuverlässige Planung.
* **Intuitive GUI:** Benutzerfreundliche Oberfläche mit Tkinter.

## Installation

### Voraussetzungen

* Python 3.x
* `pip` (Python-Paketinstallationsprogramm)

### Erforderliche Python-Bibliotheken

Vor der Ausführung müssen Sie die folgenden Python-Bibliotheken installieren:

```bash
pip install paramiko cryptography ttkthemes
====
##EN
# BackupTool

A graphical desktop application for managing local, NAS, and Hetzner Storage Box backups.
This tool simplifies backup creation, restoration, and implements retention policies,
with cross-platform scheduling capabilities (Cron for Linux/macOS, Task Scheduler for Windows).

## Features

* **Flexible Backup Sources & Destinations:** Backup from local folders to local/NAS paths or Hetzner Storage Box (SFTP).
* **Compression & Encryption:** Choose compression levels and encrypt sensitive configuration data.
* **Restore Functionality:** Easily restore backups to a specified destination.
* **Retention Policies:** Automatically manage old backups based on count or age for both local and Hetzner destinations.
* **Cross-Platform Scheduling:**
    * **Linux/macOS:** Integrate with Cron for automated backups.
    * **Windows:** Utilize Task Scheduler for reliable scheduling.
* **Intuitive GUI:** User-friendly interface built with Tkinter.

## Installation

### Prerequisites

* Python 3.x
* `pip` (Python package installer)

### Required Python Libraries

Before running, you need to install the following Python libraries:

```bash
pip install paramiko cryptography ttkthemes

Installation on Linux / macOS
Clone the repository:
Bash

git clone [https://github.com/IhrBenutzername/BackupTool.git](https://github.com/IhrBenutzername/BackupTool.git)
cd BackupTool
Run the installation script:
Bash

bash install_linux.sh
This script will:
Install required Python packages.
Create a virtual environment (recommended).
Set up a launcher script in your user's local bin directory (e.g., ~/.local/bin/backuptool).

Installation on Windows
Download the repository: Download the ZIP file from GitHub and extract it, or clone it using Git.
Open Command Prompt (CMD) or PowerShell and navigate to the extracted BackupTool directory.
Run the installation script:
DOS

install_windows.bat
This script will:
Install required Python packages.
Create a virtual environment (recommended).
Create a simple batch file (backuptool.bat) in the project directory to easily launch the application.

