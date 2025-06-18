@echo off
REM Launcher script for Tetris

REM Change to the directory where the script is located, then into tetris_android
cd "%~dp0tetris_android"

REM Run the game
echo Launching Tetris...
python main.py

REM Optional: Pause if the user wants to see output before the window closes,
REM especially if there's an error running python.
REM pause
