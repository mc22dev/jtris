#!/bin/bash

# Create resources directory if it doesn't exist
mkdir -p resources

# Create a virtual environment (optional, but recommended for Python tools)
if [ ! -d ".venv_resources" ]; then
    echo "Creating virtual environment .venv_resources..."
    python3 -m venv .venv_resources
    echo "Virtual environment .venv_resources created."
    echo "Please activate it using 'source .venv_resources/bin/activate' and install necessary tools like jukebox_sdk if you haven't already."
fi

echo ""
echo "---------------------------------------------------------------------------------"
echo "IMPORTANT: This script assumes 'jukebox_sdk' is installed and accessible."
echo "If 'jukebox_sdk generate-default-sounds' fails, please ensure 'jukebox_sdk' is"
echo "installed correctly (e.g., via pip install <jukebox_sdk_package_name>)"
echo "or available in your PATH or in the .venv_resources virtual environment."
echo "---------------------------------------------------------------------------------"
echo ""

# Download background music
wget -O resources/background_music.mp3 https://cdn.pixabay.com/download/audio/2025/05/29/audio_b92a610839.mp3?filename=eona-emotional-ambient-pop-351436.mp3

# Generate default sounds
# Ensure you are in the correct environment if jukebox_sdk is installed in a venv
# For example, if you created .venv_resources and installed jukebox_sdk there:
# source .venv_resources/bin/activate
# python -m jukebox_sdk generate-default-sounds --output_directory resources/sounds
# deactivate
#
# Or, if jukebox_sdk is globally available:
echo "Attempting to generate default sounds with jukebox_sdk..."
jukebox_sdk generate-default-sounds --output_directory resources/sounds

if [ $? -ne 0 ]; then
    echo "ERROR: jukebox_sdk command failed. Please check your installation."
else
    echo "Default sounds generated successfully."
fi
