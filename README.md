# Python Tetris Game

A classic Tetris game implemented in Python using the Pygame library.

## Features
- Standard Tetris gameplay: move, rotate, and drop tetrominoes.
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

## How to Run (Desktop)

After the recent refactoring, the game uses relative imports and must be run as a Python module.

1.  Ensure you have Python 3.x and Pygame installed.
2.  The main game module is `tetris_android/tetris.py`.
3.  (Optional) Create `tetris_android/sounds/` for sound effects and ensure `tetris_android/DejaVuSans.ttf` is a valid font file.

**Recommended way to run:**
Use the provided helper script from the project root:
```bash
./run_game.sh
```
This script handles running the game as a module correctly.

**Alternative way (running as a module directly):**
From the project root directory, execute:
```bash
python3 -m tetris_android.tetris
```
(Or `python -m tetris_android.tetris` if `python` defaults to Python 3 on your system).

**Why the change?**
The codebase was refactored into multiple Python modules (e.g., `game_state.py`, `ui_manager.py`). These modules use relative imports (like `from .constants import ...`) to refer to each other. Running a script within the package directly (e.g., `python tetris_android/tetris.py`) makes Python treat that script as a top-level script, which causes these relative imports to fail with an `ImportError`. Running the game as a module (`-m tetris_android.tetris`) allows Python to correctly recognize the `tetris_android` directory as a package and resolve the relative imports.

## Controls (Desktop)
- **Left Arrow**: Move piece left
- **Right Arrow**: Move piece right
- **Up Arrow**: Rotate piece
- **Down Arrow**: Soft drop (increase fall speed)
- **Spacebar**: Hard drop (animate piece to final position and lock)
- **Esc / Close Window**: Quit game (standard Pygame events)

## Android Version (Experimental - using pgs4a)

An attempt has been made to structure this project for packaging as an Android APK using Pygame Subset for Android (pgs4a). The core game logic is in `tetris_android/tetris.py`.

**To build the Android APK yourself:**

1.  **Prerequisites:**
    *   You need a fully configured **pgs4a development environment**. This typically includes Python 2.7 (for pgs4a tools), the Android SDK, Android NDK, and Apache Ant. Setting this up is outside the scope of this guide; please refer to official pgs4a documentation.
    *   The game has been configured to use a bundled font. You **must** place a valid TrueType Font file named `DejaVuSans.ttf` into the `tetris_android/` directory. An empty placeholder file is included; replace it with a real font.
    *   (Optional) Place sound files (`.wav` or `.ogg`) into the `tetris_android/sounds/` directory if you wish to have sound effects.

2.  **Configuration & Build Steps (run from the project root directory):**
    *   **Configure the project for pgs4a:**
        ```bash
        pgs4a configure ./tetris_android
        ```
    *   **Build the release APK:**
        ```bash
        pgs4a build ./tetris_android release
        ```
    *   If the build is successful, the APK file (e.g., `PygameTetris-1.0-release.apk`) will typically be found in a `bin/` subdirectory within `tetris_android/`.

3.  **Installation & Running on Android:**
    *   Transfer the generated APK to your Android device.
    *   Enable "Installation from Unknown Sources" in your Android settings.
    *   Install the APK and run the game.

4.  **Important Notes for Android Version:**
    *   **Input:** This game is configured for **keyboard input only**. To play on an Android device, you will likely need a physical keyboard connected or use an on-screen keyboard app that can emulate hardware key presses for arrow keys and spacebar. Touch controls have not been implemented.
    *   **Performance:** Performance on Android devices can vary.
    *   **pgs4a Status:** pgs4a is an older project. Compatibility with modern Android versions and build tools might vary.

This provides the basic steps for attempting an Android build. Success is dependent on a correctly set up pgs4a environment.
