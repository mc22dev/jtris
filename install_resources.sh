#!/bin/bash

# Create resources directory if it doesn't exist
mkdir -p resources

# Check if python3-venv is installed, install if not
if ! python3 -m venv --help &> /dev/null
then
    echo "python3-venv could not be found, attempting to install..."
    sudo apt-get update
    sudo apt-get install -y python3-venv
fi

# Create a virtual environment
if [ ! -d ".venv_jukebox" ]; then
    echo "Creating virtual environment for jukebox_sdk..."
    python3 -m venv .venv_jukebox
fi

# Activate virtual environment and install jukebox_sdk
echo "Activating virtual environment and installing/checking jukebox_sdk..."
source .venv_jukebox/bin/activate

# Check if jukebox_sdk is installed in the venv, install if not
if ! pip show jukebox_sdk &> /dev/null
then
    echo "jukebox_sdk not found in venv, installing..."
    pip install jukebox_sdk
else
    echo "jukebox_sdk already installed in venv."
fi

# Download background music
wget -O resources/background_music.mp3 https://cdn.pixabay.com/download/audio/2025/05/29/audio_b92a610839.mp3?filename=eona-emotional-ambient-pop-351436.mp3

# Generate default sounds using the venv's jukebox_sdk
echo "Generating default sounds..."
python -m jukebox_sdk generate-default-sounds --output_directory resources/sounds

# Deactivate virtual environment
deactivate
echo "Deactivated virtual environment."
