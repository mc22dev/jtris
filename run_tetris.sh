#!/bin/bash
# Launcher script for Tetris

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the tetris_android directory relative to the script location
cd "$SCRIPT_DIR/tetris_android"

# Run the game using python3; fallback to python if python3 is not found
if command -v python3 &> /dev/null
then
    python3 main.py
elif command -v python &> /dev/null
then
    python main.py
else
    echo "Python interpreter not found. Please install Python 3 or Python."
    exit 1
fi
