# Python BlockFall Game

A classic BlockFall game implemented in Python using the Pygame library.

## Features
- Standard BlockFall gameplay: move, rotate, and drop tetrominoes.
- Line clearing and scoring.
- Increasing difficulty with levels (faster fall speed, garbage blocks).
- Sound effects for game events (requires sound files in a 'sounds/' directory).
- UI displaying score, level, lines cleared, and next piece.
- Animated hard drop.
- Full HD display (1920x1080).

## Requirements
- Python 3.x
- Pygame library

To install Pygame:
```bash
pip install pygame
```
(Or using the requirements.txt: `pip install -r requirements.txt`)

## Installation of Resources
This project requires external resources like background music. To download these resources, run the install script:
```bash
./install_resources.sh
```
Make sure the script is executable: `chmod +x install_resources.sh`.

## How to Run (Desktop)
1. Ensure you have Python and Pygame installed.
2. The main game script is `blockfall_android/main.py` (which runs `blockfall_android/blockfall.py`).
3. Create a directory named `blockfall_android/sounds/` if you want to use sound effects (sound files not provided). Ensure `DejaVuSans.ttf` (a real font file, not the placeholder) is in `blockfall_android/`.
4. Run the game from the project root using:
```bash
python -m blockfall_android.main
```

## Using Launcher Scripts

For convenience, launcher scripts are provided in the project root:

*   **For Linux/macOS:**
    Open your terminal, navigate to the project root directory, and run:
    ```bash
    ./run_blockfall.sh
    ```
    If you get a permission error, you might need to make it executable first (this should have been set by git, but just in case): `chmod +x run_blockfall.sh`.

*   **For Windows:**
    Open Command Prompt or PowerShell, navigate to the project root directory, and run:
    ```bat
    .\run_blockfall.bat
    ```
    Alternatively, you can usually double-click `run_blockfall.bat` from the File Explorer.

## Controls (Desktop)
- **Left Arrow**: Move piece left
- **Right Arrow**: Move piece right
- **Up Arrow**: Rotate piece
- **Down Arrow**: Soft drop (increase fall speed)
- **Spacebar**: Hard drop (animate piece to final position and lock)
- **Esc / Close Window**: Quit game (standard Pygame events)

## Android Version (Experimental - using pgs4a)

An attempt has been made to structure this project for packaging as an Android APK using Pygame Subset for Android (pgs4a). The core game logic is in `blockfall_android/blockfall.py`.

**To build the Android APK yourself:**

1.  **Prerequisites:**
    *   You need a fully configured **pgs4a development environment**. This typically includes Python 2.7 (for pgs4a tools), the Android SDK, Android NDK, and Apache Ant. Setting this up is outside the scope of this guide; please refer to official pgs4a documentation.
    *   The game has been configured to use a bundled font. You **must** place a valid TrueType Font file named `DejaVuSans.ttf` into the `blockfall_android/` directory. An empty placeholder file is included; replace it with a real font.
    *   (Optional) Place sound files (`.wav` or `.ogg`) into the `blockfall_android/sounds/` directory if you wish to have sound effects.

2.  **Configuration & Build Steps (run from the project root directory):**
    *   **Configure the project for pgs4a:**
        ```bash
        pgs4a configure ./blockfall_android
        ```
    *   **Build the release APK:**
        ```bash
        pgs4a build ./blockfall_android release
        ```
    *   If the build is successful, the APK file (e.g., `PygameBlockFall-1.0-release.apk`) will typically be found in a `bin/` subdirectory within `blockfall_android/`.

3.  **Installation & Running on Android:**
    *   Transfer the generated APK to your Android device.
    *   Enable "Installation from Unknown Sources" in your Android settings.
    *   Install the APK and run the game.

4.  **Important Notes for Android Version:**
    *   **Input:** This game is configured for **keyboard input only**. To play on an Android device, you will likely need a physical keyboard connected or use an on-screen keyboard app that can emulate hardware key presses for arrow keys and spacebar. Touch controls have not been implemented.
    *   **Performance:** Performance on Android devices can vary.
    *   **pgs4a Status:** pgs4a is an older project. Compatibility with modern Android versions and build tools might vary.

This provides the basic steps for attempting an Android build. Success is dependent on a correctly set up pgs4a environment.
