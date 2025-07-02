#!/bin/bash

# Create resources directory if it doesn't exist
mkdir -p resources

# Check if pip is installed, install if not (common on minimal systems)
if ! command -v pip &> /dev/null
then
    echo "pip could not be found, attempting to install..."
    sudo apt-get update
    sudo apt-get install -y python3-pip
fi

# Check if jukebox_sdk is installed, install if not
if ! command -v jukebox_sdk &> /dev/null
then
    echo "jukebox_sdk could not be found, attempting to install..."
    pip install jukebox_sdk
fi

# Download background music
wget -O resources/background_music.mp3 https://cdn.pixabay.com/download/audio/2025/05/29/audio_b92a610839.mp3?filename=eona-emotional-ambient-pop-351436.mp3

# Generate default sounds
jukebox_sdk generate-default-sounds --output_directory resources/sounds
