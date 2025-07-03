#!/bin/bash

echo "Starting BackupTool installation for Linux/macOS..."

# --- Prerequisites Check ---
# Check for Python 3
if ! command -v python3 &> /dev/null
then
    echo "Error: Python 3 could not be found. Please install Python 3.8 or newer."
    echo "You can usually install it via your package manager (e.g., 'sudo apt install python3' or 'brew install python@3')."
    exit 1
fi

# Check for pip3
if ! command -v pip3 &> /dev/null
then
    echo "Warning: pip3 could not be found. Attempting to install pip for Python 3..."
    python3 -m ensurepip --default-pip
    if ! command -v pip3 &> /dev/null
    then
        echo "Error: Failed to install pip3. Please install it manually (e.g., 'sudo apt install python3-pip')."
        exit 1
    fi
fi

# --- Virtual Environment Setup ---
PROJECT_ROOT="$(dirname "$(readlink -f "$0")")" # Get the directory where this script is located
VENV_DIR="$PROJECT_ROOT/venv"

echo "Project root detected: $PROJECT_ROOT"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment. Please check permissions or disk space."
        exit 1
    fi
else
    echo "Virtual environment already exists ($VENV_DIR). Skipping creation."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment. Please check the 'venv' directory."
    exit 1
fi

# --- Install Python Packages ---
echo "Installing required Python packages: paramiko cryptography ttkthemes..."
pip install paramiko cryptography ttkthemes

if [ $? -ne 0 ]; then
    echo "Error: Failed to install Python packages. Please check your internet connection or try again."
    deactivate # Deactivate venv on failure
    exit 1
fi

echo "Python packages installed successfully."

# --- Create Launcher Script ---
LAUNCHER_DIR="$HOME/.local/bin"
LAUNCHER_SCRIPT="$LAUNCHER_DIR/backuptool"

mkdir -p "$LAUNCHER_DIR" # Ensure the directory exists

echo "Creating launcher script at $LAUNCHHER_SCRIPT..."
cat << EOF > "$LAUNCHER_SCRIPT"
#!/bin/bash
# This script launches the BackupTool GUI application.

# Navigate to the project root
# This assumes the launcher script is in ~/.local/bin and the project is one level up
# from where the install script was run (i.e., this launcher will cd into the directory
# containing main.py and venv/).
CURRENT_SCRIPT_DIR="\$(dirname "\$(readlink -f "\$0")")"
PROJECT_DIR="\$(dirname "\$CURRENT_SCRIPT_DIR")" # One level up from ~/.local/bin if installed there

# If the installer created a direct link, the project_dir is the same as current_script_dir
# Check if the venv exists relative to the current script's parent (assuming typical install)
if [ -d "\$PROJECT_DIR/venv" ]; then
    cd "\$PROJECT_DIR"
elif [ -d "\$(dirname "\$(readlink -f "\$0")")/venv" ]; then # Fallback if script is directly in project
    cd "\$(dirname "\$(readlink -f "\$0")")"
else
    echo "Error: Could not find project directory or virtual environment."
    exit 1
fi

# Activate the virtual environment
source venv/bin/activate

# Run the main application
python3 main.py "\$@"

# Deactivate the virtual environment
deactivate
EOF

chmod +x "$LAUNCHER_SCRIPT"

echo "Installation complete!"
echo "You can now run BackupTool by typing 'backuptool' in your terminal."
echo "------------------------------------------------------------------"
echo "IMPORTANT: Ensure '$HOME/.local/bin' is in your system's PATH."
echo "You might need to restart your terminal or log out and back in for the 'backuptool' command to work."
echo "Alternatively, you can run it directly from the project directory:"
echo "  cd $PROJECT_ROOT"
echo "  source venv/bin/activate"
echo "  python3 main.py"
echo "------------------------------------------------------------------"

deactivate # Deactivate venv after installation
