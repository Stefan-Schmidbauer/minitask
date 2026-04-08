#!/bin/bash
#
# Quickstrap Developer Mode Activation
#
# Source this file in your shell to activate the virtual environment
# for development sessions:
#
#   source quickstrap/activate.sh
#
# This provides:
# - Activated virtual environment
# - Quickstrap environment variables (QUICKSTRAP_APP_NAME, QUICKSTRAP_CONFIG_DIR, QUICKSTRAP_PROJECT_ROOT)
# - Updated PATH with venv binaries
#

# Function to read INI file values
read_ini_value() {
    local file="$1"
    local section="$2"
    local key="$3"

    awk -v section="[$section]" -v key="$key" '
        $0 == section { in_section=1; next }
        /^\[/ { in_section=0 }
        in_section && match($0, "^[[:space:]]*"key"[[:space:]]*=") {
            val = substr($0, RSTART + RLENGTH)
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
            print val
            exit
        }
    ' "$file"
}

# Determine script directory (works even when sourced)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if venv exists
VENV_PATH="$PROJECT_ROOT/venv"
if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run ./install.py first to create the virtual environment"
    return 1 2>/dev/null || exit 1
fi

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Load Quickstrap metadata from installation_profiles.ini
CONFIG_FILE="$PROJECT_ROOT/quickstrap/installation_profiles.ini"
if [ -f "$CONFIG_FILE" ]; then
    export QUICKSTRAP_APP_NAME=$(read_ini_value "$CONFIG_FILE" "metadata" "app_name")
    export QUICKSTRAP_CONFIG_DIR="$PROJECT_ROOT"
    export QUICKSTRAP_PROJECT_ROOT="$PROJECT_ROOT"
fi

# Show activation message
echo "╭───────────────────────────────────────────────╮"
echo "│  Quickstrap Developer Mode Activated         │"
echo "╰───────────────────────────────────────────────╯"
echo ""
echo "Environment:"
echo "  • Virtual environment: $VENV_PATH"
[ -n "$QUICKSTRAP_APP_NAME" ] && echo "  • App name: $QUICKSTRAP_APP_NAME"
[ -n "$QUICKSTRAP_CONFIG_DIR" ] && echo "  • Config dir: $QUICKSTRAP_CONFIG_DIR"
[ -n "$QUICKSTRAP_PROJECT_ROOT" ] && echo "  • Project root: $QUICKSTRAP_PROJECT_ROOT"
echo ""
echo "Python: $(python --version)"
echo ""
echo "To deactivate, run: deactivate"
