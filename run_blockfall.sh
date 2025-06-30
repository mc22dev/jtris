#!/bin/bash
# Launcher script for BlockFall

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Ensure we are in the script's directory (project root)
cd "$SCRIPT_DIR"

# Run the game as a module using python3; fallback to python if python3 is not found
echo "Launching BlockFall from project root..."
if command -v python3 &> /dev/null
then
    python3 -m tetris_android.main
elif command -v python &> /dev/null
then
    python -m tetris_android.main
else
    echo "Python interpreter not found. Please install Python 3 or Python."
    exit 1
fi
