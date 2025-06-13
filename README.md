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

## How to Run
1. Ensure you have Python and Pygame installed.
2. Create a directory named `sounds` in the same directory as `tetris.py` if you want to use sound effects (sound files not provided in this repository).
3. Run the game using:
```bash
python tetris.py
```

## Controls
- **Left Arrow**: Move piece left
- **Right Arrow**: Move piece right
- **Up Arrow**: Rotate piece
- **Down Arrow**: Soft drop (increase fall speed)
- **Spacebar**: Hard drop (animate piece to final position and lock)
- **Esc / Close Window**: Quit game (standard Pygame events)
