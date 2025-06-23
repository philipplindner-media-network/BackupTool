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
git clone https://github.com/IhrBenutzername/BackupTool.git
cd BackupTool
```
*Remember to replace `IhrBenutzername` with your actual GitHub username and `BackupTool` with your repository name.*

#### Option B: Download ZIP

Go to the [BackupTool GitHub page](https://github.com/IhrBenutzername/BackupTool) (replace `IhrBenutzername`) and click the green "Code" button, then "Download ZIP".  
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
