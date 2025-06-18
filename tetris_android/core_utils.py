import os
import pygame # For pygame.mixer.Sound
from .constants import GRID_WIDTH, GRID_HEIGHT # For is_valid_position, get_full_lines etc.
# Piece type hinting / direct attribute access might be needed if not changing function signatures for piece data
# from .piece import Piece # Not strictly needed if functions take piece attributes directly, but good for type hints if Piece objects are passed

# Global sound-related variables
SOUND_EFFECTS = {}
sound_effects_enabled = True # Default value, will be updated from config in main game
SOUND_DIR = "sounds"

# --- Utility Functions (Moved from tetris.py) ---

def load_sound(filename):
    """Loads a sound file from the SOUND_DIR."""
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path):
        print(f"Sound file not found: {path}")
        return None
    try:
        sound = pygame.mixer.Sound(path)
        sound.set_volume(0.3) # Default volume
        return sound
    except pygame.error as e:
        print(f"Error loading sound {filename}: {e}")
        return None

def play_sound(sound_name):
    """Plays a sound if sound effects are enabled."""
    global sound_effects_enabled, SOUND_EFFECTS # Ensure we're using the globals from this module
    if not sound_effects_enabled:
        return
    if SOUND_EFFECTS.get(sound_name):
        SOUND_EFFECTS[sound_name].play()

def is_valid_position(piece, grid_data, check_y_offset=0): # piece is an instance of Piece class
    """Checks if the piece is in a valid position on the grid."""
    if not piece: return False
    # piece.current_shape_coords() returns absolute grid coordinates (y,x) for each block of the piece
    # check_y_offset is an additional vertical shift to apply for collision checking
    for r_coord, c_coord in piece.current_shape_coords():
        actual_r = r_coord + check_y_offset
        actual_c = c_coord # c_coord is already absolute

        if not (0 <= actual_c < GRID_WIDTH): return False
        if not (actual_r < GRID_HEIGHT): return False # Allow pieces to be above the grid (actual_r < 0)
        if actual_r >= 0 and grid_data[actual_r][actual_c] != 0: return False
    return True

def add_to_grid(piece, grid_data): # piece is an instance of Piece class
    """Adds the current piece to the grid."""
    if piece:
        for r_coord, c_coord in piece.current_shape_coords(): # These are absolute grid coords
            if r_coord >=0: # Ensure it's within grid rows
                 grid_data[r_coord][c_coord] = piece.color
        play_sound("drop") # play_sound is now local to this module

def get_shadow_position_y(piece, grid_data): # piece is an instance of Piece class
    """
    Calculates the y-coordinate for the piece's shadow.
    Uses the local is_valid_position.
    """
    if not piece:
        return -1

    # The piece object's (piece.x, piece.y) is its current pivot.
    # is_valid_position checks the piece at its current x,y with an *additional* check_y_offset.
    # We want to find how many steps (current_y_offset) the piece can move down from its current position.
    current_y_offset = 0
    while is_valid_position(piece, grid_data, check_y_offset=current_y_offset + 1):
        current_y_offset += 1
    return piece.y + current_y_offset # This is the final absolute y pivot for the shadow


def get_full_lines(grid_data):
    """Identifies and returns indices of full lines in the grid."""
    full_lines_indices = []
    for r_idx in range(GRID_HEIGHT): # GRID_HEIGHT from .constants
        if 0 not in grid_data[r_idx]: # Check if line is full (no empty cells)
            full_lines_indices.append(r_idx)
    return full_lines_indices

def get_score_for_lines(lines_cleared, level):
    """Calculates the score for the number of lines cleared at a given level."""
    base_score = {1: 40, 2: 100, 3: 300, 4: 1200}
    return base_score.get(lines_cleared, 0) * level

def format_time(total_seconds):
    """Formats total seconds into MM:SS string."""
    minutes = int(total_seconds // 60)
    seconds = int(total_seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"
