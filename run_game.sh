#!/bin/bash
# Helper script to run the Tetris game

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Change to the script's directory (project root) to ensure correct module resolution
cd "$SCRIPT_DIR"

echo "Running Tetris from $SCRIPT_DIR using module execution..."
python3 -m tetris_android.main "$@"
