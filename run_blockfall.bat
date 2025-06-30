@echo off
REM Launcher script for BlockFall

REM Ensure we are in the script's directory (project root)
cd "%~dp0"

REM Run the game as a module
echo Launching BlockFall from project root...
python -m blockfall_android.main

REM Optional: Pause if the user wants to see output before the window closes,
REM especially if there's an error running python.
REM pause
