import time
from .piece import Piece
from .constants import (
    GRID_WIDTH, GRID_HEIGHT, INITIAL_FALL_SPEED, MIN_FALL_SPEED, FALL_SPEED_DECREMENT_PER_LEVEL
)
# Functions like is_valid_position, play_sound will be passed if needed by functions moved here.

class GameState:
    def __init__(self,
                 game_grid,
                 current_piece,
                 next_piece_1,
                 next_piece_2,
                 score,
                 current_level,
                 total_lines_cleared,
                 lines_for_current_level,
                 game_over,
                 current_fall_speed,
                 last_fall_time,
                 soft_drop_active,
                 game_over_sound_played,
                 ai_mode_active,
                 last_ai_move_time,
                 game_start_time,
                 final_game_time_str,
                 game_paused,
                 time_at_pause,
                 total_paused_duration):
        self.game_grid = game_grid
        self.current_piece = current_piece
        self.next_piece_1 = next_piece_1
        self.next_piece_2 = next_piece_2
        self.score = score
        self.current_level = current_level
        self.total_lines_cleared = total_lines_cleared
        self.lines_for_current_level = lines_for_current_level
        self.game_over = game_over
        self.current_fall_speed = current_fall_speed
        self.last_fall_time = last_fall_time
        self.soft_drop_active = soft_drop_active
        self.game_over_sound_played = game_over_sound_played
        self.ai_mode_active = ai_mode_active
        self.last_ai_move_time = last_ai_move_time
        self.game_start_time = game_start_time
        self.final_game_time_str = final_game_time_str
        self.game_paused = game_paused
        self.time_at_pause = time_at_pause
        self.total_paused_duration = total_paused_duration

# --- Functions moved from tetris.py ---

def create_grid(fill_value=0):
    """Creates and returns a new game grid."""
    # Uses GRID_WIDTH, GRID_HEIGHT from .constants
    return [[fill_value for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]

def spawn_piece_at_start(is_valid_position_func, play_sound_func):
    """Spawns a new piece at the starting position."""
    # Uses Piece from .piece, GRID_WIDTH from .constants
    # is_valid_position_func and play_sound_func are passed in from tetris.py
    return Piece(GRID_WIDTH // 2, 0,
                 is_valid_position_func=is_valid_position_func,
                 play_sound_func=play_sound_func)

def calculate_fall_speed(level):
    """Calculates fall speed based on the current level."""
    # Uses constants MIN_FALL_SPEED, INITIAL_FALL_SPEED, FALL_SPEED_DECREMENT_PER_LEVEL from .constants
    return max(MIN_FALL_SPEED, INITIAL_FALL_SPEED - (level - 1) * FALL_SPEED_DECREMENT_PER_LEVEL)
