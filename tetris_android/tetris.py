import pygame
import random
import time
import os
import copy
import json
import argparse

# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()
pygame.joystick.init()

DEBUG_MODE = False

# Screen dimensions
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Tetris"

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
# ... other colors ...
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
MAGENTA = (255, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
GREY = (128, 128, 128)
GARBAGE_COLOR = (100, 100, 100)


PIECE_COLORS = [CYAN, YELLOW, MAGENTA, GREEN, RED, BLUE, ORANGE]
SHAPES = [
    [[(1, -2), (1, -1), (1, 0), (1, 1)], [(-1, 0), (0, 0), (1, 0), (2, 0)]], # I
    [[(0, 0), (0, 1), (1, 0), (1, 1)]], # O
    [ # T
        [(-1, 0), (0, 0), (1, 0), (0, -1)], [ (0, 1), (0, 0), (0, -1), (1, 0)],
        [(-1, 0), (0, 0), (1, 0), (0, 1)], [(-1, 0), (0, 1), (0, 0), (0, -1)]
    ],
    [[(0, 0), (0, 1), (1, -1), (1, 0)], [(-1, 0), (0, 0), (0, 1), (1, 1)]], # S
    [[(0, -1), (0, 0), (1, 0), (1, 1)], [(-1, 1), (0, 1), (0, 0), (1, 0)]], # Z
    [ # J
        [(-1, -1), (0, -1), (0, 0), (0, 1)], [(-1, 1), (-1, 0), (0, 0), (1, 0)],
        [(1, 1), (0, 1), (0, 0), (0, -1)], [(1, -1), (1, 0), (0, 0), (-1, 0)]
    ],
    [ # L
        [(-1, 1), (0, 1), (0, 0), (0, -1)], [(-1, -1), (-1, 0), (0, 0), (1, 0)],
        [(1, -1), (0, -1), (0, 0), (0, 1)], [(1, 1), (1, 0), (0, 0), (-1, 0)]
    ]
]

# Grid dimensions
GRID_WIDTH = 10
GRID_HEIGHT = 20
BLOCK_SIZE = 30 # Main game block size
NEXT_PIECE_BLOCK_SIZE = 20 # Smaller blocks for next piece display

GRID_OFFSET_X = (SCREEN_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
GRID_OFFSET_Y = (SCREEN_HEIGHT - GRID_HEIGHT * BLOCK_SIZE) // 2

# UI variables
UI_INFO_X_OFFSET = 20 # From right edge of grid
UI_INFO_START_Y = GRID_OFFSET_Y + 20
UI_INFO_LINE_SPACING = 10
NEXT_PIECE_BOX_SIZE = 5 * NEXT_PIECE_BLOCK_SIZE # Accommodate 4x4 piece + padding

# Game variables
# ... (level, difficulty, etc. remain same)
INITIAL_FALL_SPEED = 0.8; FALL_SPEED_DECREMENT_PER_LEVEL = 0.03; MIN_FALL_SPEED = 0.05
LINES_PER_LEVEL = 10; GARBAGE_START_LEVEL = 3; MAX_GARBAGE_ROWS = 5

SCORE_FONT_SIZE = 36
INFO_FONT_SIZE = 30
TITLE_FONT_SIZE = 24
GAME_OVER_FONT_SIZE = 72
AI_PLAYER_TOGGLE_KEY = pygame.K_a # Key to toggle AI player mode
RESTART_KEY = pygame.K_r # Key to restart the game after game over
PAUSE_KEY = pygame.K_p # Key to pause/unpause the game
AI_MOVE_DELAY = 0.05 # Time in seconds between AI moves, adjust for speed
LINE_ANIMATION_DURATION = 30  # Frames, approx 0.5s at 60fps

# Progress Bar UI Constants
PROGRESS_BAR_WIDTH = 150 # Width of the level progress bar in pixels
PROGRESS_BAR_HEIGHT = 20 # Height of the level progress bar in pixels
PROGRESS_BAR_BACKGROUND_COLOR = (50, 50, 50) # Dark Grey
PROGRESS_BAR_FILL_COLOR = GREEN # Using existing GREEN = (0, 255, 0)
PROGRESS_BAR_BORDER_COLOR = GREY  # Using existing GREY = (128, 128, 128)
SCORE_FONT = None; INFO_FONT = None; TITLE_FONT = None; GAME_OVER_FONT = None

SOUND_EFFECTS = {"move": None, "rotate": None, "drop": None, "line_clear": None, "tetris_clear": None, "level_up": None, "game_over": None}
SOUND_DIR = "sounds"
sound_enabled = True # Initialize sound_enabled globally at module level
shadow_enabled = True # Default initial value before config is loaded

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path): print(f"Sound file not found: {path}"); return None
    try: sound = pygame.mixer.Sound(path); sound.set_volume(0.3); return sound
    except pygame.error as e: print(f"Error loading sound {filename}: {e}"); return None

def play_sound(sound_name):
    global sound_enabled # Access the global sound_enabled state
    if not sound_enabled:
        return
    if SOUND_EFFECTS.get(sound_name): SOUND_EFFECTS[sound_name].play()

class Piece:
    def __init__(self, x, y, shape_type=None): # Allow forcing shape_type for next_piece
        if shape_type is None:
            self.shape_type = random.randint(0, len(SHAPES) - 1)
        else:
            self.shape_type = shape_type
        self.shape = SHAPES[self.shape_type]
        self.color = PIECE_COLORS[self.shape_type]
        self.rotation = 0
        self.x = x # Grid column for current piece, or abstract for next piece
        self.y = y # Grid row for current piece
        self.is_hard_dropping_animated = False # True if piece is currently in animated hard drop
        self.target_y_for_animated_drop = -1   # Stores the target Y row for the animated hard drop

    def current_shape_coords(self):
        coords = []
        for r_offset, c_offset in self.shape[self.rotation]:
            coords.append((self.y + r_offset, self.x + c_offset))
        return coords

    def get_shape_for_preview(self): # Get block coords relative to a 0,0 pivot for preview
        # Returns the coordinates of the first rotation for preview.
        return self.shape[0]


    def rotate(self, grid_data): # Only for main game piece
        original_rotation = self.rotation
        self.rotation = (self.rotation + 1) % len(self.shape)
        if not is_valid_position(self, grid_data):
            self.rotation = original_rotation
        else:
            play_sound("rotate")

# ... (create_grid, draw_grid_lines, draw_blocks, draw_piece - largely same)
def create_grid(fill_value=0): return [[fill_value for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
def draw_grid_lines(screen):
    for row in range(GRID_HEIGHT + 1): pygame.draw.line(screen, GREY, (GRID_OFFSET_X, GRID_OFFSET_Y + row * BLOCK_SIZE), (GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE, GRID_OFFSET_Y + row * BLOCK_SIZE))
    for col in range(GRID_WIDTH + 1): pygame.draw.line(screen, GREY, (GRID_OFFSET_X + col * BLOCK_SIZE, GRID_OFFSET_Y), (GRID_OFFSET_X + col * BLOCK_SIZE, GRID_OFFSET_Y + GRID_HEIGHT * BLOCK_SIZE))

def draw_blocks(screen, grid_data, lines_being_animated, animation_timer): # Draws landed blocks
    for r_idx, row in enumerate(grid_data):
        for c_idx, cell_color in enumerate(row):
            if cell_color != 0:
                current_block_color = cell_color # Start with the actual color

                if r_idx in lines_being_animated:
                    progress_frames = LINE_ANIMATION_DURATION - animation_timer
                    blink_phase_duration = LINE_ANIMATION_DURATION / 10
                    current_blink_phase = int(progress_frames / blink_phase_duration)

                    if current_blink_phase % 2 == 0: # Even phases - show white
                        current_block_color = WHITE
                    else: # Odd phases - show original color
                        current_block_color = cell_color

                    if animation_timer < (LINE_ANIMATION_DURATION / 5): # Last 1/5th of time
                        current_block_color = BLACK # Make them disappear

                pygame.draw.rect(screen, current_block_color, (GRID_OFFSET_X + c_idx * BLOCK_SIZE, GRID_OFFSET_Y + r_idx * BLOCK_SIZE, BLOCK_SIZE -1, BLOCK_SIZE -1))

def draw_current_piece_on_grid(screen, piece): # Renamed for clarity
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >= 0: # Only draw if within visible grid area
                pygame.draw.rect(screen, piece.color, (GRID_OFFSET_X + c_idx * BLOCK_SIZE, GRID_OFFSET_Y + r_idx * BLOCK_SIZE, BLOCK_SIZE -1, BLOCK_SIZE -1))

def is_valid_position(piece, grid_data, check_y_offset=0): # For main game piece
    if not piece: return False
    for r_idx, c_idx in piece.current_shape_coords():
        actual_r = r_idx + check_y_offset
        if not (0 <= c_idx < GRID_WIDTH): return False
        if not (actual_r < GRID_HEIGHT): return False
        if actual_r >= 0 and grid_data[actual_r][c_idx] != 0: return False
    return True

def add_to_grid(piece, grid_data):
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >=0: grid_data[r_idx][c_idx] = piece.color
        play_sound("drop")

def get_shadow_position_y(piece, grid_data):
    """
    Calculates the y-coordinate for the piece's shadow.
    Iterates downwards from the piece's current y position, checking
    if the piece would be in a valid position at y + 1.
    Uses is_valid_position for this check.
    Returns the last valid y coordinate before collision.
    """
    if not piece:
        return -1 # Or some other indicator of an invalid state

    current_y_offset = 0
    # We are checking for piece.y + current_y_offset + 1
    # So, is_valid_position needs to check for an offset from the piece's *original* y.
    # The 'check_y_offset' parameter in is_valid_position is relative to piece.y.
    # So, if piece is at y, and we are checking y + k, then check_y_offset = k.
    while is_valid_position(piece, grid_data, check_y_offset=current_y_offset + 1):
        current_y_offset += 1

    return piece.y + current_y_offset

def get_full_lines(grid_data):
    full_lines_indices = []
    # Iterate top to bottom to get indices in natural order.
    for r_idx in range(GRID_HEIGHT):
        if 0 not in grid_data[r_idx]: # Check if line is full
            full_lines_indices.append(r_idx)
    return full_lines_indices

def get_score_for_lines(lines_cleared, level): base_score = {1: 40, 2: 100, 3: 300, 4: 1200}; return base_score.get(lines_cleared, 0) * level

def spawn_piece_at_start(): # Renamed for clarity
    return Piece(GRID_WIDTH // 2, 0)

def calculate_fall_speed(level): return max(MIN_FALL_SPEED, INITIAL_FALL_SPEED - (level -1) * FALL_SPEED_DECREMENT_PER_LEVEL)
def add_garbage_blocks(grid_data, level):
    if level < GARBAGE_START_LEVEL: return False
    num_garbage_rows = min(MAX_GARBAGE_ROWS, (level - GARBAGE_START_LEVEL) // 2 + 1)

    # Check if top rows (that would be deleted) are empty enough
    for i in range(num_garbage_rows):
        if any(grid_data[i]): # If any cell in the top 'i' rows is occupied
            print("Warning: Not enough space to add full garbage without affecting potential top player blocks. Skipping.")
            return False

    # Shift existing grid content up by num_garbage_rows
    for _ in range(num_garbage_rows):
        del grid_data[0]; grid_data.append([0 for _ in range(GRID_WIDTH)])

    for i in range(num_garbage_rows):
        row_index = GRID_HEIGHT - 1 - i
        garbage_row = [GARBAGE_COLOR for _ in range(GRID_WIDTH)]; hole_position = random.randint(0, GRID_WIDTH - 1)
        garbage_row[hole_position] = 0; grid_data[row_index] = garbage_row

    temp_piece_for_check = Piece(GRID_WIDTH // 2, 0)
    return not is_valid_position(temp_piece_for_check, grid_data) # True if game over

# --- Time Formatting Function ---
def format_time(total_seconds):
    """Formats total seconds into MM:SS string."""
    minutes = int(total_seconds // 60) # Calculate whole minutes
    seconds = int(total_seconds % 60) # Calculate remaining seconds
    return f"{minutes:02d}:{seconds:02d}" # Format as MM:SS with leading zeros

def draw_next_piece_area(screen, next_piece, x_pos, y_pos):
    global TITLE_FONT
    if TITLE_FONT is None: TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE)

    next_text = TITLE_FONT.render("Next:", True, WHITE)
    screen.blit(next_text, (x_pos, y_pos))

    box_y_pos = y_pos + TITLE_FONT_SIZE + 5
    pygame.draw.rect(screen, GREY, (x_pos, box_y_pos, NEXT_PIECE_BOX_SIZE, NEXT_PIECE_BOX_SIZE), 1)

    if next_piece:
        shape_coords = next_piece.get_shape_for_preview()

        min_r_offset = min(r for r,c in shape_coords) if shape_coords else 0
        max_r_offset = max(r for r,c in shape_coords) if shape_coords else 0
        min_c_offset = min(c for r,c in shape_coords) if shape_coords else 0
        max_c_offset = max(c for r,c in shape_coords) if shape_coords else 0

        shape_width_blocks = max_c_offset - min_c_offset + 1
        shape_height_blocks = max_r_offset - min_r_offset + 1

        start_draw_x = x_pos + (NEXT_PIECE_BOX_SIZE - shape_width_blocks * NEXT_PIECE_BLOCK_SIZE) // 2
        start_draw_y = box_y_pos + (NEXT_PIECE_BOX_SIZE - shape_height_blocks * NEXT_PIECE_BLOCK_SIZE) // 2

        for r_offset, c_offset in shape_coords:
            block_x = start_draw_x + (c_offset - min_c_offset) * NEXT_PIECE_BLOCK_SIZE
            block_y = start_draw_y + (r_offset - min_r_offset) * NEXT_PIECE_BLOCK_SIZE
            pygame.draw.rect(screen, next_piece.color, (block_x, block_y, NEXT_PIECE_BLOCK_SIZE -1, NEXT_PIECE_BLOCK_SIZE -1))


def draw_full_ui(screen, score, level, lines_cleared_total, next_p, lines_for_current_level, ai_mode_is_active, formatted_time_str, best_score_data_dict): # Added best_score_data_dict
    global SCORE_FONT, INFO_FONT
    if SCORE_FONT is None: SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE)
    if INFO_FONT is None: INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)

    current_y = UI_INFO_START_Y
    ui_start_x = GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE + UI_INFO_X_OFFSET

    score_surface = SCORE_FONT.render(f"Score: {score}", True, WHITE)
    screen.blit(score_surface, (ui_start_x, current_y))
    current_y += SCORE_FONT_SIZE + UI_INFO_LINE_SPACING

    level_surface = INFO_FONT.render(f"Level: {level}", True, WHITE)
    screen.blit(level_surface, (ui_start_x, current_y))
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING

    lines_surface = INFO_FONT.render(f"Lines: {lines_cleared_total}", True, WHITE)
    screen.blit(lines_surface, (ui_start_x, current_y))
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING

    # AI Mode Indicator
    ai_mode_text = "AI Mode: " + ("ON" if ai_mode_is_active else "OFF")
    ai_status_color = GREEN if ai_mode_is_active else RED
    ai_surface = INFO_FONT.render(ai_mode_text, True, ai_status_color)
    screen.blit(ai_surface, (ui_start_x, current_y))
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING

    # Display Elapsed Time
    time_text_surface = INFO_FONT.render(f"Time: {formatted_time_str}", True, WHITE) # Render the time string
    screen.blit(time_text_surface, (ui_start_x, current_y)) # Blit time to screen
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING # Update y for next element

    # Display Best Score
    if best_score_data_dict and isinstance(best_score_data_dict.get("score"), int) and best_score_data_dict["score"] > 0:
        best_score_text = f"Best: {best_score_data_dict['username']} - {best_score_data_dict['score']}"
        best_score_surface = INFO_FONT.render(best_score_text, True, YELLOW) # Using YELLOW for emphasis
        screen.blit(best_score_surface, (ui_start_x, current_y))
        current_y += INFO_FONT.get_height() + UI_INFO_LINE_SPACING

    # Draw Level Progress Bar
    # Text label for progress bar is drawn by draw_level_progress_bar above the bar itself
    # INFO_FONT is used for the progress text by draw_level_progress_bar
    progress_text_height = INFO_FONT.get_height() if INFO_FONT else 20 # Estimate if font not loaded
    progress_bar_rect_y = current_y + progress_text_height + 5 # Y pos for bar, below its text label
    bar_outer_rect = pygame.Rect(ui_start_x, progress_bar_rect_y, PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT)
    progress_bar_colors = {"bg": PROGRESS_BAR_BACKGROUND_COLOR, "fill": PROGRESS_BAR_FILL_COLOR, "border": PROGRESS_BAR_BORDER_COLOR}
    # Ensure INFO_FONT is loaded before calling, or handle inside draw_level_progress_bar if it can be None
    if INFO_FONT: # Guard call if INFO_FONT might not be loaded (though it should be by this point)
        draw_level_progress_bar(screen, lines_for_current_level, LINES_PER_LEVEL, bar_outer_rect, progress_bar_colors, INFO_FONT, WHITE) # Call the function to draw the progress bar

    # Update current_y to be below the progress bar for the next UI element
    current_y = progress_bar_rect_y + PROGRESS_BAR_HEIGHT + UI_INFO_LINE_SPACING * 2 # Update current_y to position elements below the progress bar

    draw_next_piece_area(screen, next_p, ui_start_x, current_y)


# --- New Drawing Function for Level Progress Bar ---
def draw_level_progress_bar(screen, current_lines, lines_needed, bar_outer_rect, colors, font, text_color):
    """
    Draws a progress bar indicating progress towards the next level.
    Args:
        screen: Pygame screen surface.
        current_lines (int): Lines cleared for the current level.
        lines_needed (int): Total lines needed for the next level (LINES_PER_LEVEL).
        bar_outer_rect (pygame.Rect): The rectangle defining the outer bounds of the bar.
        colors (dict): Dictionary with keys 'bg', 'fill', 'border'.
        font (pygame.font.Font): Font for the text label.
        text_color (tuple): Color for the text label.
    """
    # Draw background
    pygame.draw.rect(screen, colors['bg'], bar_outer_rect)

    # Calculate fill percentage and width
    fill_percentage = 0.0
    if lines_needed > 0: # Avoid division by zero
        fill_percentage = min(1.0, float(current_lines) / lines_needed) # Cap at 100%

    fill_width = int(fill_percentage * bar_outer_rect.width)

    if fill_width > 0:
        fill_rect = pygame.Rect(bar_outer_rect.x, bar_outer_rect.y, fill_width, bar_outer_rect.height)
        pygame.draw.rect(screen, colors['fill'], fill_rect)

    # Draw border (optional)
    if 'border' in colors: # Allow border to be optional
        pygame.draw.rect(screen, colors['border'], bar_outer_rect, 1) # 1px border

    # Draw text label (e.g., "Progress: 3/10")
    progress_text_str = f"Progress: {current_lines}/{lines_needed}"
    text_surface = font.render(progress_text_str, True, text_color)

    # Position text above the bar, centered horizontally with the bar
    text_x = bar_outer_rect.centerx - text_surface.get_width() // 2
    text_y = bar_outer_rect.y - text_surface.get_height() - 2 # 2px padding above bar
    screen.blit(text_surface, (text_x, text_y))


# --- AI Helper Functions ---

def clone_grid(grid_data):
    """Creates and returns a deep copy of the given game grid."""
    return copy.deepcopy(grid_data)

def _get_cleared_lines_and_new_grid(grid_copy_to_check):
    """
    Checks for completed lines on a given grid copy and returns the number of lines
    cleared AND the grid state after clearing those lines.
    Args:
        grid_copy_to_check (list): The grid (a list of lists) to check.
    Returns:
        tuple: (lines_cleared_count, grid_after_clearing)
    """
    lines_cleared_count = 0
    grid_after_clearing = [row[:] for row in grid_copy_to_check]

    r = GRID_HEIGHT - 1
    while r >= 0:
        is_line_full = True
        for c in range(GRID_WIDTH):
            if grid_after_clearing[r][c] == 0:
                is_line_full = False
                break
        if is_line_full:
            lines_cleared_count += 1
            del grid_after_clearing[r]
            grid_after_clearing.insert(0, [0 for _ in range(GRID_WIDTH)])
        else:
            r -= 1

    return lines_cleared_count, grid_after_clearing

def simulate_place_piece(grid_to_simulate_on, piece_to_simulate, target_x, target_rotation):
    """
    Simulates placing a piece at a given x and rotation on a (deep)copy of the grid.
    Performs a hard drop and calculates the outcome.

    Args:
        grid_to_simulate_on (list): The grid state (must be a deep copy) to simulate on.
        piece_to_simulate (Piece): The piece object whose shape and color are used.
                                   This function creates its own temporary copy for simulation.
        target_x (int): The target column (piece_s x-coordinate) for placement.
        target_rotation (int): The target rotation index for the piece.

    Returns:
        tuple: (resulting_grid_after_clear, lines_cleared, landing_y, is_move_possible)
               - resulting_grid_after_clear (list or None): Grid state after piece placement AND line clearing. None if placement impossible.
               - lines_cleared (int): Number of lines cleared by this move.
               - landing_y (int): The y-coordinate (pivot) where the piece landed. -1 if not possible.
               - is_move_possible (bool): False if the piece cannot be placed at the given x/rotation (e.g., spawn obstructed).
    """
    sim_grid_current_move = clone_grid(grid_to_simulate_on)

    temp_piece = Piece(target_x, 0, piece_to_simulate.shape_type)
    temp_piece.rotation = target_rotation
    temp_piece.x = target_x

    min_r_offset = 0
    current_shape_blocks = temp_piece.shape[temp_piece.rotation]
    if current_shape_blocks:
        min_r_offset = min(r for r, c in current_shape_blocks)
    temp_piece.y = -min_r_offset # Adjust spawn y to be at the very top

    if not is_valid_position(temp_piece, sim_grid_current_move):
        return None, 0, -1, False

    landing_y = temp_piece.y
    while True:
        temp_piece.y += 1
        if not is_valid_position(temp_piece, sim_grid_current_move):
            temp_piece.y -= 1
            landing_y = temp_piece.y
            break

    for r_offset, c_offset in current_shape_blocks:
        block_r, block_c = landing_y + r_offset, temp_piece.x + c_offset
        if 0 <= block_r < GRID_HEIGHT and 0 <= block_c < GRID_WIDTH:
            sim_grid_current_move[block_r][block_c] = temp_piece.color

    lines_cleared, grid_after_clear = _get_cleared_lines_and_new_grid(sim_grid_current_move)

    return grid_after_clear, lines_cleared, landing_y, True


# --- Heuristic Evaluation Function ---

HEURISTIC_WEIGHTS = {
    'aggregate_height': -0.510066,
    'cleared_lines': 0.760666,
    'holes': -0.35663,
    'bumpiness': -0.184483,
    # Additional potential heuristics (can be added and weighted)
    # 'wells': -0.2, # Sum of depths of wells
    # 'blockades': -0.3, # Number of empty cells covered by a block
    # 'edge_blocks': 0.1 # Number of blocks touching the side walls (can be good or bad)
}

def evaluate_board_state(grid, lines_cleared_by_move):
    """
    Evaluates the given board state based on several heuristics.
    A higher score is better.

    Args:
        grid (list): The game grid (list of lists) to evaluate.
        lines_cleared_by_move (int): Number of lines cleared by the move that led to this state.

    Returns:
        float: The heuristic score for the board state.
    """
    score = 0

    # 1. Aggregate Height: Sum of the heights of all columns. Lower is better.
    #    Height of a column is GRID_HEIGHT minus the row of the highest block in that column.
    #    If column is empty, its height is 0.
    aggregate_height = 0
    column_heights = [0] * GRID_WIDTH
    for c in range(GRID_WIDTH):
        for r in range(GRID_HEIGHT):
            if grid[r][c] != 0:
                column_heights[c] = GRID_HEIGHT - r
                break
        aggregate_height += column_heights[c]
    score += HEURISTIC_WEIGHTS['aggregate_height'] * aggregate_height

    # 2. Cleared Lines: Number of lines cleared by the last move. More is better.
    #    This is directly passed as an argument.
    score += HEURISTIC_WEIGHTS['cleared_lines'] * lines_cleared_by_move

    # 3. Holes: Number of empty cells that have at least one block above them in the same column. Lower is better.
    holes = 0
    for c in range(GRID_WIDTH):
        block_above_found = False
        for r in range(GRID_HEIGHT): # Iterate from top to bottom
            if grid[r][c] != 0:
                block_above_found = True
            elif block_above_found and grid[r][c] == 0:
                holes += 1
    score += HEURISTIC_WEIGHTS['holes'] * holes

    # 4. Bumpiness: Sum of the absolute differences in height between adjacent columns. Lower is better.
    bumpiness = 0
    for c in range(GRID_WIDTH - 1):
        bumpiness += abs(column_heights[c] - column_heights[c+1])
    score += HEURISTIC_WEIGHTS['bumpiness'] * bumpiness

    # --- (Optional: Add other heuristics here if defined in HEURISTIC_WEIGHTS) ---
    # Example: Wells
    # wells_score = 0
    # if 'wells' in HEURISTIC_WEIGHTS:
    #     for c in range(GRID_WIDTH):
    #         for r in range(GRID_HEIGHT -1, -1, -1): # Iterate from bottom up
    #             if grid[r][c] == 0: # Found an empty cell
    #                 # Check left wall
    #                 left_wall = (c == 0) or (grid[r][c-1] != 0)
    #                 # Check right wall
    #                 right_wall = (c == GRID_WIDTH - 1) or (grid[r][c+1] != 0)
    #                 if left_wall and right_wall:
    #                     # This is the top of a well, count depth
    #                     depth = 0
    #                     for wr in range(r, GRID_HEIGHT):
    #                         if grid[wr][c] == 0:
    #                             depth +=1
    #                         else:
    #                             break
    #                     wells_score += depth # Simple sum of depths, could be sum of squares etc.
    #                 break # Move to next column once top of well or block is found
    #     score += HEURISTIC_WEIGHTS['wells'] * wells_score

    return score


# --- AI: Find Best Move Function ---

def find_best_move(grid_data, current_piece_obj, next_piece_obj):
    """
    Finds the best move (column and rotation) for the current piece by simulating
    all possible placements and evaluating the resulting board states.

    Args:
        grid_data (list): The current game grid.
        current_piece_obj (Piece): The current falling piece.
        next_piece_obj (Piece): The next piece (can be None or used for two-ply lookahead,
                                 but current implementation is one-ply).

    Returns:
        tuple: (best_x, best_rotation, best_score)
               - best_x (int): The target column for the best move.
               - best_rotation (int): The target rotation for the best move.
               - best_score (float): The score of the board state resulting from the best move.
                                     Returns -float('inf') if no moves are possible.
    """
    best_score = -float('inf')
    best_x = -1
    best_rotation = -1
    best_landing_y = -1 # Store the landing_y of the best move

    # Iterate through all possible rotations for the current piece
    for rotation_idx in range(len(current_piece_obj.shape)):
        # Iterate through all possible column placements
        # Piece x-coordinates are for the pivot. Need to determine valid range.
        # A simple range is from where leftmost block is at col 0
        # to where rightmost block is at col GRID_WIDTH - 1
        # This can be refined, but for now, let's try a broad range of columns.
        # Min/max c_offset for the current rotation will determine this.

        # Create a temporary piece to check its bounds for each rotation
        temp_eval_piece = Piece(0, 0, current_piece_obj.shape_type) # x,y are dummy here
        temp_eval_piece.rotation = rotation_idx

        current_shape_blocks = temp_eval_piece.shape[temp_eval_piece.rotation]
        min_c_offset_for_shape = 0
        max_c_offset_for_shape = 0
        if current_shape_blocks:
            min_c_offset_for_shape = min(c for r,c in current_shape_blocks)
            max_c_offset_for_shape = max(c for r,c in current_shape_blocks)

        # Iterate through all possible x positions for the piece's pivot
        for x_col in range(-min_c_offset_for_shape, GRID_WIDTH - max_c_offset_for_shape):
            # Simulate placing the piece at (x_col, rotation_idx)
            # The y-coordinate for simulation starts near the top and hard-drops.
            # simulate_place_piece handles the hard drop and landing.

            grid_copy = clone_grid(grid_data) # Use a fresh copy for each simulation

            # Pass the original current_piece_obj for its shape_type to simulate_place_piece
            resulting_grid, lines_cleared, landing_y, is_possible = \
                simulate_place_piece(grid_copy, current_piece_obj, x_col, rotation_idx)

            if is_possible:
                current_move_score = evaluate_board_state(resulting_grid, lines_cleared)

                # Basic tie-breaking: prefer lower landing height if scores are equal
                if current_move_score > best_score:
                    best_score = current_move_score
                    best_x = x_col
                    best_rotation = rotation_idx
                    best_landing_y = landing_y
                elif current_move_score == best_score:
                    # Tie-breaking: prefer moves that result in a lower (higher y-value) piece position
                    if landing_y > best_landing_y: # Higher y means lower on grid
                        best_x = x_col
                        best_rotation = rotation_idx
                        best_landing_y = landing_y
                        # best_score remains the same

    return {'x': best_x, 'rotation': best_rotation, 'score': best_score, 'landing_y': best_landing_y}

# --- Input Handling Sub-functions ---

def handle_game_over_inputs(event):
    """
    Handles input events when the game is over.
    Checks for restart or quit commands.

    Args:
        event (pygame.event.Event): The Pygame event to process.

    Returns:
        str or None: "RESTART", "QUIT", or None if no relevant action is triggered.
    """
    if event.type == pygame.QUIT:
        return "QUIT"
    if event.type == pygame.KEYDOWN:
        if event.key == RESTART_KEY: # RESTART_KEY should be defined globally
            return "RESTART"
        if event.key == pygame.K_ESCAPE: # Using ESC as a global quit key too
            return "QUIT"
    return None # No relevant action

def handle_player_piece_controls(event, current_piece, game_grid, soft_drop_active_flag):
    """
    Handles player inputs for controlling the current piece (movement, rotation, drop).
    Assumes current_piece exists, game is not over, AI is not active, and piece is not already hard dropping.

    Args:
        event (pygame.event.Event): The Pygame event to process.
        current_piece (Piece): The currently falling piece.
        game_grid (list): The main game grid.
        soft_drop_active_flag (bool): Current state of soft drop.

    Returns:
        bool: Updated state of soft_drop_active_flag.
    """
    if event.type == pygame.KEYDOWN:
        # These controls should not be active if the piece is in the middle of an animated hard drop
        if current_piece.is_hard_dropping_animated:
            return soft_drop_active_flag

        if event.key == pygame.K_UP:
            current_piece.rotate(game_grid)
        elif event.key == pygame.K_LEFT:
            current_piece.x -= 1
            if not is_valid_position(current_piece, game_grid):
                current_piece.x += 1
            else:
                play_sound("move")
        elif event.key == pygame.K_RIGHT:
            current_piece.x += 1
            if not is_valid_position(current_piece, game_grid):
                current_piece.x -= 1
            else:
                play_sound("move")
        elif event.key == pygame.K_DOWN: # Activate soft drop
            soft_drop_active_flag = True
        elif event.key == pygame.K_SPACE: # Initiate Animated Hard Drop
            # Calculate target_y for hard drop by simulating fall until invalid
            original_y = current_piece.y
            temp_piece_for_calc = Piece(current_piece.x, original_y, current_piece.shape_type)
            temp_piece_for_calc.rotation = current_piece.rotation
            calculated_target_y = original_y
            while is_valid_position(temp_piece_for_calc, game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                calculated_target_y += 1

            current_piece.target_y_for_animated_drop = calculated_target_y
            current_piece.is_hard_dropping_animated = True
            soft_drop_active_flag = False # Cancel soft drop if hard drop is initiated

    elif event.type == pygame.KEYUP: # Separate from KEYDOWN to handle soft drop release
        if event.key == pygame.K_DOWN:
            # Deactivate soft drop only if it was active and not overridden by hard drop animation
            if not current_piece.is_hard_dropping_animated:
                 soft_drop_active_flag = False

    return soft_drop_active_flag

# --- Game State Reset Function ---
def reset_game_state():
    """Initializes and returns all game state variables for a new game."""
    game_grid = create_grid()
    current_piece = spawn_piece_at_start()
    next_piece = Piece(0, 0) # Piece class handles random shape_type if None

    game_over = False
    if not is_valid_position(current_piece, game_grid):
        game_over = True
        current_piece = None # No piece if game over at start

    score = 0
    current_level = 1
    total_lines_cleared = 0
    lines_for_current_level = 0

    current_fall_speed = calculate_fall_speed(current_level)
    last_fall_time = time.time()
    soft_drop_active = False
    game_over_sound_played = False # Reset sound flag

    ai_mode_active = False # Default AI to off
    last_ai_move_time = time.time() # Initialize AI timer

    game_start_time = time.time() # New game start time
    final_game_time_str = None # Reset final time string

    game_paused = False
    time_at_pause = 0.0 # Time when game was last paused
    total_paused_duration = 0.0 # Accumulates total time spent paused

    return {
        "game_grid": game_grid, "current_piece": current_piece, "next_piece": next_piece,
        "score": score, "current_level": current_level, "total_lines_cleared": total_lines_cleared,
        "lines_for_current_level": lines_for_current_level, "game_over": game_over,
        "current_fall_speed": current_fall_speed, "last_fall_time": last_fall_time,
        "soft_drop_active": soft_drop_active, "game_over_sound_played": game_over_sound_played,
        "ai_mode_active": ai_mode_active, "last_ai_move_time": last_ai_move_time,
        "game_start_time": game_start_time, "final_game_time_str": final_game_time_str,
        "game_paused": game_paused, "time_at_pause": time_at_pause, "total_paused_duration": total_paused_duration
    }

def _handle_restart_action():
    # This function will be responsible for managing the game restart logic.
    # It calls reset_game_state to get a fresh set of game parameters.
    new_game_state = reset_game_state()
    return new_game_state

def _unpack_game_state(game_state_dict):
    game_grid = game_state_dict["game_grid"]
    current_piece = game_state_dict["current_piece"]
    next_piece = game_state_dict["next_piece"]
    score = game_state_dict["score"]
    current_level = game_state_dict["current_level"]
    total_lines_cleared = game_state_dict["total_lines_cleared"]
    lines_for_current_level = game_state_dict["lines_for_current_level"]
    game_over = game_state_dict["game_over"]
    current_fall_speed = game_state_dict["current_fall_speed"]
    last_fall_time = game_state_dict["last_fall_time"]
    soft_drop_active = game_state_dict["soft_drop_active"]
    game_over_sound_played = game_state_dict["game_over_sound_played"]
    ai_mode_active = game_state_dict["ai_mode_active"]
    last_ai_move_time = game_state_dict["last_ai_move_time"]
    game_start_time = game_state_dict["game_start_time"]
    final_game_time_str = game_state_dict["final_game_time_str"]
    game_paused = game_state_dict["game_paused"]
    time_at_pause = game_state_dict["time_at_pause"]
    total_paused_duration = game_state_dict["total_paused_duration"]

    return (game_grid, current_piece, next_piece, score, current_level,
            total_lines_cleared, lines_for_current_level, game_over,
            current_fall_speed, last_fall_time, soft_drop_active,
            game_over_sound_played, ai_mode_active, last_ai_move_time,
            game_start_time, final_game_time_str, game_paused,
            time_at_pause, total_paused_duration)

def load_config():
    filename = "config.json"
    default_config = {"sound_enabled": True, "shadow_enabled": True} # Updated default

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict): # Ensure data is a dictionary before using .get()
                if DEBUG_MODE: print(f"Warning: {filename} content is not a dictionary. Using defaults.")
                return default_config.copy() # Return a copy of default_config

            final_config = {}
            loaded_sound = data.get("sound_enabled")
            loaded_shadow = data.get("shadow_enabled")

            if isinstance(loaded_sound, bool):
                final_config["sound_enabled"] = loaded_sound
            else:
                final_config["sound_enabled"] = default_config["sound_enabled"]
                if DEBUG_MODE: print(f"Warning: 'sound_enabled' missing/invalid in {filename}. Using default.")

            if isinstance(loaded_shadow, bool):
                final_config["shadow_enabled"] = loaded_shadow
            else:
                final_config["shadow_enabled"] = default_config["shadow_enabled"]
                if DEBUG_MODE: print(f"Warning: 'shadow_enabled' missing/invalid in {filename}. Using default.")

            if DEBUG_MODE: print(f"Config processed from {filename}. Final values: {final_config}")
            return final_config

    except FileNotFoundError:
        if DEBUG_MODE: print(f"Info: {filename} not found. Using default config: {default_config}")
        return default_config.copy() # Return a copy
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filename}. File might be corrupted. Using defaults: {default_config}")
        return default_config.copy() # Return a copy
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: An unexpected error occurred loading {filename}: {e}. Using defaults: {default_config}")
        return default_config.copy() # Return a copy

def save_config(config_data):
    filename = "config.json"
    try:
        with open(filename, 'w') as f:
            json.dump(config_data, f, indent=4) # Save with indentation for readability
        if DEBUG_MODE: print(f"Config saved to {filename}: {config_data}")
    except IOError as e:
        if DEBUG_MODE: print(f"Error saving config to {filename}: {e}")
    except Exception as e: # Catch any other unexpected errors during save
        if DEBUG_MODE: print(f"An unexpected error occurred while saving config to {filename}: {e}")

def _load_best_score():
    filename = "best_score.json"
    default_score_data = {"username": "N/A", "score": 0, "time_str": "00:00"}

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            # Basic validation for expected structure
            if isinstance(data, dict) and \
               "username" in data and \
               "score" in data and \
               "time_str" in data and \
               isinstance(data["score"], int): # Ensure score is an int for comparison
                return data
            else:
                print(f"Warning: {filename} has invalid structure. Using defaults.")
                return copy.deepcopy(default_score_data)
    except FileNotFoundError:
        print(f"Info: {filename} not found. A new one will be created if a best score is achieved.")
        return copy.deepcopy(default_score_data)
    except json.JSONDecodeError:
        print(f"Warning: Error decoding {filename}. File might be corrupted. Using defaults.")
        return copy.deepcopy(default_score_data)
    except Exception as e:
        print(f"Warning: An unexpected error occurred loading {filename}: {e}. Using defaults.")
        return copy.deepcopy(default_score_data)

def _save_best_score(username, score, time_str):
    filename = "best_score.json"
    data_to_save = {
        "username": username,
        "score": score,
        "time_str": time_str
    }

    try:
        with open(filename, 'w') as f:
            json.dump(data_to_save, f, indent=4)
        print(f"New best score saved to {filename}.") # Informative print
    except Exception as e:
        print(f"Error saving best score to {filename}: {e}")

def _handle_events(events, game_over_flag, game_paused_flag, ai_mode_flag, soft_drop_flag, current_piece_obj, game_grid_data, running_flag, time_at_pause_val, total_paused_duration_val, last_fall_time_val, last_ai_move_time_val, joystick_obj, joystick_enabled_flag, help_screen_active_flag, game_phase_str, current_username_str, config_menu_active_flag, sound_enabled_flag, shadow_enabled_flag): # Added shadow_enabled_flag
    action_request = None
    # current_username_str is a string, reassignments will create new strings. Caller (main) will update its copy.

    for event in events:
        # Top-level quit check (handles window close)
        if event.type == pygame.QUIT:
            running_flag = False
            continue # Skip further processing for this event

        # Help Screen Toggle (H)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            help_screen_active_flag = not help_screen_active_flag
            if help_screen_active_flag:
                if not game_paused_flag: # Only set time_at_pause if game wasn't already paused by something else (e.g. config menu)
                    time_at_pause_val = time.time()
                game_paused_flag = True
                if DEBUG_MODE: print("Help screen NEWLY ACTIVATED. game_paused_flag set to True.")
            else: # Deactivating help screen
                if not config_menu_active_flag: # Only unpause if config menu is also not active
                    game_paused_flag = False
                    if time_at_pause_val > 0: # Ensure game was actually paused
                        total_paused_duration_val += time.time() - time_at_pause_val
                        time_at_pause_val = 0 # Reset time_at_pause_val
                    last_fall_time_val = time.time() # Reset fall timer
                    last_ai_move_time_val = time.time() # Reset AI timer
                if DEBUG_MODE: print("Help screen NEWLY DEACTIVATED. game_paused_flag logic applied.")
            continue

        # Config Menu Toggle (C)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            # If config menu is currently active, and ESC is pressed, this block handles it.
            # If 'c' is pressed again, it also toggles.
            if config_menu_active_flag and event.key == pygame.K_c : # Already handled by the config_menu_active_flag block later if menu is open
                 pass # Let the dedicated config menu handler do its job to avoid double processing
            else:
                config_menu_active_flag = not config_menu_active_flag
                if config_menu_active_flag:
                    if not game_paused_flag: # Only set time_at_pause if game wasn't already paused
                        time_at_pause_val = time.time()
                    game_paused_flag = True
                    if DEBUG_MODE: print("Config menu NEWLY ACTIVATED by C. game_paused_flag set to True.")
                else: # Deactivating config menu by 'C' key (when it's not open and gets toggled off - this case might be redundant if it implies it was already false)
                    if not help_screen_active_flag: # Only unpause if help screen is also not active
                        game_paused_flag = False
                        if time_at_pause_val > 0:
                            total_paused_duration_val += time.time() - time_at_pause_val
                            time_at_pause_val = 0 # Reset time_at_pause_val
                        last_fall_time_val = time.time() # Reset fall timer
                        last_ai_move_time_val = time.time() # Reset AI timer
                    if DEBUG_MODE: print("Config menu NEWLY DEACTIVATED by C. game_paused_flag logic applied.")
            continue


        # Close Help with ESC (respects config menu)
        if help_screen_active_flag and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            help_screen_active_flag = False
            if not config_menu_active_flag: # Only unpause if config menu is also not active
                game_paused_flag = False
                if time_at_pause_val > 0:
                    total_paused_duration_val += time.time() - time_at_pause_val
                    time_at_pause_val = 0 # Reset time_at_pause_val
                last_fall_time_val = time.time()
                last_ai_move_time_val = time.time()
            if DEBUG_MODE: print("Help screen deactivated by ESC. game_paused_flag logic applied.")
            continue

        if help_screen_active_flag: # If help is active, skip all other game inputs below this
            continue

        # Config Menu Active Handling (takes precedence over game phases if active, but after help)
        if config_menu_active_flag:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    sound_enabled_flag = not sound_enabled_flag
                    save_config({"sound_enabled": sound_enabled_flag, "shadow_enabled": shadow_enabled_flag})
                    if DEBUG_MODE: print(f"Sound setting toggled. Called save_config with sound: {sound_enabled_flag}, shadow: {shadow_enabled_flag}")
                    # Potentially play a sound here to indicate change, if sound is now ON
                elif event.key == pygame.K_d: # Toggle shadow
                    shadow_enabled_flag = not shadow_enabled_flag
                    save_config({"sound_enabled": sound_enabled_flag, "shadow_enabled": shadow_enabled_flag})
                    if DEBUG_MODE: print(f"Shadow setting toggled. Called save_config with sound: {sound_enabled_flag}, shadow: {shadow_enabled_flag}")
                elif event.key == pygame.K_ESCAPE or event.key == pygame.K_c:
                    config_menu_active_flag = False
                    # Only unpause if help screen is also not active
                    if not help_screen_active_flag:
                        game_paused_flag = False
                        # Correctly update pause duration and game timers
                        if time_at_pause_val > 0: # Ensure game was actually paused
                           total_paused_duration_val += time.time() - time_at_pause_val
                           time_at_pause_val = 0 # Reset time_at_pause_val
                        last_fall_time_val = time.time()
                        last_ai_move_time_val = time.time()
                    if DEBUG_MODE: print("Config menu DEACTIVATED by ESC/C key. game_paused_flag logic applied.")
            # IMPORTANT: Consume all events while config menu is active so they don't bleed through
            continue

        # Phase-specific event handling
        if game_phase_str == "GETTING_USERNAME":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    if current_username_str:
                        action_request = "SAVE_SCORE"
                    else:
                        action_request = "SKIP_SAVE"
                    continue
                elif event.key == pygame.K_ESCAPE:
                    action_request = "SKIP_SAVE"
                    continue
                elif event.key == pygame.K_BACKSPACE:
                    current_username_str = current_username_str[:-1]
                    continue
                elif len(current_username_str) < 15 and event.unicode.isalnum():
                    current_username_str += event.unicode.upper()
                    continue
            else: # If not KEYDOWN, but still in GETTING_USERNAME phase
                continue # Consume other event types too for this phase

        elif game_phase_str == "PLAYING":
            # Pause Toggle (P key)
            if event.type == pygame.KEYDOWN and event.key == PAUSE_KEY:
                game_paused_flag = not game_paused_flag # Toggle the pause state first
                if game_paused_flag: # Game is now paused by 'P'
                    time_at_pause_val = time.time() # Record time when paused
                    if DEBUG_MODE: print(f"Game Paused (P key). Paused: {game_paused_flag}")
                else: # Attempting to unpause via 'P'
                    if not help_screen_active_flag and not config_menu_active_flag: # Only truly unpause if no other modal is active
                        if time_at_pause_val > 0: # Ensure game was actually paused
                            total_paused_duration_val += time.time() - time_at_pause_val
                            time_at_pause_val = 0 # Reset pause timer
                        last_fall_time_val = time.time()
                        last_ai_move_time_val = time.time()
                        if DEBUG_MODE: print(f"Game Resumed (P key) - All clear. Paused: {game_paused_flag}")
                    else:
                        if DEBUG_MODE: print(f"Game Unpause (P key) deferred - Help/Config active. Paused: {game_paused_flag} (still true effectively, or will be set by other modals)")
                        # game_paused_flag remains False from the toggle, but other modals will keep it effectively paused or re-pause it.
                        # If other modals are active, they should be the ones to set game_paused_flag back to True if they are opened,
                        # or handle the unpausing when they are closed.
                        # The main thing is that total_paused_duration is not updated yet if another modal is active.
                continue

            if not game_paused_flag: # Only if game is not paused by 'P' (or help screen, or config menu, or joystick pause)
                # AI Mode Toggle (A key)
                if event.type == pygame.KEYDOWN and event.key == AI_PLAYER_TOGGLE_KEY:
                    ai_mode_flag = not ai_mode_flag
                    if DEBUG_MODE: print(f"AI Mode Toggled (A key). AI: {ai_mode_flag}")
                    if ai_mode_flag:
                        soft_drop_flag = False
                        if current_piece_obj: current_piece_obj.is_hard_dropping_animated = False
                        last_ai_move_time_val = time.time()
                    continue

                # Player-specific KEYBOARD controls for active play
                if current_piece_obj and not ai_mode_flag:
                    if DEBUG_MODE: print(f"DEBUG: Event for handle_player_piece_controls: type={event.type}, game_phase='{game_phase_str}', game_paused={game_paused_flag}, help_active={help_screen_active_flag}, ai_active={ai_mode_flag}")
                    soft_drop_flag = handle_player_piece_controls(event, current_piece_obj, game_grid_data, soft_drop_flag)

                # Joystick controls for active play (piece movement)
                if joystick_enabled_flag and joystick_obj and current_piece_obj and not ai_mode_flag:
                    if event.type == pygame.JOYAXISMOTION:
                        if event.joy == joystick_obj.get_id():
                            axis = event.axis
                            value = event.value
                            if not current_piece_obj.is_hard_dropping_animated:
                                if axis == 0: # X-axis
                                    if value < -0.5: current_piece_obj.x -= 1
                                    elif value > 0.5: current_piece_obj.x += 1
                                    if not is_valid_position(current_piece_obj, game_grid_data): current_piece_obj.x -= (1 if value > 0.5 else -1)
                                    else: play_sound("move")
                                elif axis == 1: # Y-axis
                                    if value > 0.5: soft_drop_flag = True
                                    else: soft_drop_flag = False
                    elif event.type == pygame.JOYHATMOTION:
                        if event.joy == joystick_obj.get_id():
                            hat_x, hat_y = event.value
                            if not current_piece_obj.is_hard_dropping_animated:
                                if hat_x == -1: current_piece_obj.x -= 1
                                elif hat_x == 1: current_piece_obj.x += 1
                                if not is_valid_position(current_piece_obj, game_grid_data): current_piece_obj.x -= (1 if hat_x == 1 else -1)
                                else: play_sound("move")

                                if hat_y == -1: soft_drop_flag = True
                                elif hat_y == 1: current_piece_obj.rotate(game_grid_data)
                                else: # Y is neutral
                                     if hat_x == 0 : soft_drop_flag = False # only reset soft_drop if X is also neutral

                    elif event.type == pygame.JOYBUTTONDOWN:
                         if event.joy == joystick_obj.get_id():
                            button = event.button
                            if button != 6 and button != 7: # Ensure not global action buttons
                                if not current_piece_obj.is_hard_dropping_animated:
                                    if button == 0:
                                        current_piece_obj.rotate(game_grid_data)
                                    elif button == 1:
                                        original_y = current_piece_obj.y
                                        temp_piece_for_calc = Piece(current_piece_obj.x, original_y, current_piece_obj.shape_type)
                                        temp_piece_for_calc.rotation = current_piece_obj.rotation
                                        calculated_target_y = original_y
                                        while is_valid_position(temp_piece_for_calc, game_grid_data, check_y_offset=(calculated_target_y - original_y + 1)):
                                            calculated_target_y += 1
                                        current_piece_obj.target_y_for_animated_drop = calculated_target_y
                                        current_piece_obj.is_hard_dropping_animated = True
                                        soft_drop_flag = False

        elif game_phase_str == "GAME_OVER":
            action = None
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN:
                action = handle_game_over_inputs(event)

            if action == "RESTART":
                action_request = "RESTART"
                break
            elif action == "QUIT":
                running_flag = False
                break
            if event.type == pygame.QUIT or event.type == pygame.KEYDOWN: # If it was a keydown/quit, and not restart/quit action
                 continue

        # Joystick button handling for global actions (Pause, AI) - outside phase-specific piece controls
        if joystick_enabled_flag and joystick_obj and event.type == pygame.JOYBUTTONDOWN:
            button = event.button
            if button == 7: # Start Button
                if game_phase_str == "PLAYING": # Pause/Resume only during active play
                    game_paused_flag = not game_paused_flag # Toggle the pause state
                    if game_paused_flag: # Game is now paused by Joystick
                        time_at_pause_val = time.time()
                        if DEBUG_MODE: print(f"Game Paused (Joystick Start). Paused: {game_paused_flag}")
                    else: # Attempting to unpause via Joystick
                        if not help_screen_active_flag and not config_menu_active_flag: # Only truly unpause if no other modal is active
                            if time_at_pause_val > 0: # Ensure game was actually paused
                                total_paused_duration_val += time.time() - time_at_pause_val
                                time_at_pause_val = 0 # Reset pause timer
                            last_fall_time_val = time.time()
                            last_ai_move_time_val = time.time()
                            if DEBUG_MODE: print(f"Game Resumed (Joystick Start) - All clear. Paused: {game_paused_flag}")
                        else:
                            if DEBUG_MODE: print(f"Game Unpause (Joystick Start) deferred - Help/Config active. Paused: {game_paused_flag} (still true effectively)")
                            # As with 'P' key, game_paused_flag is False from toggle, but timing updates are deferred.
                    continue
            elif button == 6: # Select Button
                 if game_phase_str == "PLAYING" and not game_paused_flag: # AI toggle only if playing and not paused
                    ai_mode_flag = not ai_mode_flag
                    if DEBUG_MODE: print(f"AI Mode Toggled (Joystick Select). AI: {ai_mode_flag}")
                    if ai_mode_flag:
                        soft_drop_flag = False
                        if current_piece_obj: current_piece_obj.is_hard_dropping_animated = False
                        last_ai_move_time_val = time.time()
                    continue

    return {
        "running": running_flag,
        "game_paused": game_paused_flag,
        "ai_mode_active": ai_mode_flag,
        "soft_drop_active": soft_drop_flag,
        "current_piece": current_piece_obj,
        "time_at_pause": time_at_pause_val,
        "total_paused_duration": total_paused_duration_val,
        "last_fall_time": last_fall_time_val,
        "last_ai_move_time": last_ai_move_time_val,
        "action_request": action_request,
        "help_screen_active": help_screen_active_flag,
        "config_menu_active": config_menu_active_flag,
        "sound_enabled": sound_enabled_flag,
        "shadow_enabled": shadow_enabled_flag, # Added
        "current_username_input": current_username_str,
        "game_phase_str": game_phase_str
    }

def _update_game_state(game_over_flag, game_paused_flag, ai_mode_flag, current_piece_obj, next_piece_obj, game_grid_data, score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val, current_fall_speed_val, last_fall_time_val, soft_drop_flag, game_over_sound_played_flag, last_ai_move_time_val, game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val, help_screen_active_flag, game_phase_str, lines_being_animated_list, line_animation_timer_val):
    # --- Game Logic (AI, Piece Movement, Physics) ---

    if game_phase_str == "LINE_ANIMATION":
        line_animation_timer_val -= 1
        if line_animation_timer_val <= 0:
            # Call _finalize_line_clear
            finalize_result = _finalize_line_clear(
                game_grid_data, lines_being_animated_list,
                score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val
            )
            # Update states from finalize_result
            game_grid_data = finalize_result["grid_data"]
            score_val = finalize_result["current_score"]
            current_level_val = finalize_result["level"]
            total_lines_cleared_val = finalize_result["total_lines"]
            lines_for_current_level_val = finalize_result["lines_for_lvl"]

            if finalize_result["leveled_up"]:
                current_fall_speed_val = calculate_fall_speed(current_level_val)
                # Call add_garbage_blocks and handle game_over if it returns True
                if add_garbage_blocks(game_grid_data, current_level_val):
                    game_over_flag = True
                    current_piece_obj = None # Ensure no piece if game over from garbage

            # Spawn next piece (only if not game over from garbage)
            if not game_over_flag:
                current_piece_obj = next_piece_obj
                if current_piece_obj:
                    current_piece_obj.x = GRID_WIDTH // 2
                    current_piece_obj.y = 0
                next_piece_obj = Piece(0, 0)
                if not is_valid_position(current_piece_obj, game_grid_data):
                    game_over_flag = True
                    current_piece_obj = None

            lines_being_animated_list = [] # Clear animated lines
            game_phase_str = "PLAYING"    # Transition back to playing
            last_fall_time_val = time.time()

    # Game logic should only run during "PLAYING" phase and if not paused (e.g. by help screen).
    elif game_phase_str == "PLAYING" and not game_paused_flag:
        # --- AI Player Decision Logic ---
        if ai_mode_flag and not game_over_flag and current_piece_obj and not current_piece_obj.is_hard_dropping_animated:
            if time.time() - last_ai_move_time_val > AI_MOVE_DELAY:
                grid_copy_for_ai = clone_grid(game_grid_data)
                best_move_info = find_best_move(grid_copy_for_ai, current_piece_obj, next_piece_obj)

                if best_move_info and best_move_info['x'] != -1:
                    current_piece_obj.rotation = best_move_info['rotation']
                    current_piece_obj.x = best_move_info['x']
                    current_piece_obj.target_y_for_animated_drop = best_move_info['landing_y']
                    current_piece_obj.is_hard_dropping_animated = True
                    soft_drop_flag = False
                else:
                    if DEBUG_MODE: print("AI: No valid moves found by find_best_move. Setting game over.")
                    game_over_flag = True
                last_ai_move_time_val = time.time()

        # --- Animated Hard Drop Logic ---
        if not game_over_flag and current_piece_obj and current_piece_obj.is_hard_dropping_animated:
            current_piece_obj.y += 1
            if current_piece_obj.y >= current_piece_obj.target_y_for_animated_drop:
                current_piece_obj.y = current_piece_obj.target_y_for_animated_drop
                current_piece_obj.is_hard_dropping_animated = False
                add_to_grid(current_piece_obj, game_grid_data)

                cleared_row_indices = get_full_lines(game_grid_data)
                if cleared_row_indices:
                    game_phase_str = "LINE_ANIMATION"
                    lines_being_animated_list = cleared_row_indices
                    line_animation_timer_val = LINE_ANIMATION_DURATION
                    if len(cleared_row_indices) == 4: play_sound("tetris_clear")
                    elif len(cleared_row_indices) > 0: play_sound("line_clear")
                    current_piece_obj = None # Piece locked, wait for animation
                else: # No lines cleared
                    current_piece_obj = next_piece_obj
                    if current_piece_obj:
                        current_piece_obj.x = GRID_WIDTH // 2; current_piece_obj.y = 0
                    next_piece_obj = Piece(0,0)
                    if not is_valid_position(current_piece_obj, game_grid_data):
                        game_over_flag = True; current_piece_obj = None

                last_fall_time_val = time.time()
                soft_drop_flag = False

        # --- Automatic Piece Descent ---
        if not game_over_flag and current_piece_obj and not current_piece_obj.is_hard_dropping_animated:
            fall_interval = current_fall_speed_val
            if soft_drop_flag: fall_interval = min(current_fall_speed_val, 0.05)

            if time.time() - last_fall_time_val > fall_interval:
                current_piece_obj.y += 1
                if not is_valid_position(current_piece_obj, game_grid_data):
                    current_piece_obj.y -= 1
                    add_to_grid(current_piece_obj, game_grid_data)

                    cleared_row_indices = get_full_lines(game_grid_data)
                    if cleared_row_indices:
                        game_phase_str = "LINE_ANIMATION"
                        lines_being_animated_list = cleared_row_indices
                        line_animation_timer_val = LINE_ANIMATION_DURATION
                        if len(cleared_row_indices) == 4: play_sound("tetris_clear")
                        elif len(cleared_row_indices) > 0: play_sound("line_clear")
                        current_piece_obj = None # Piece locked, wait for animation
                    else: # No lines cleared
                        current_piece_obj = next_piece_obj
                        if current_piece_obj:
                            current_piece_obj.x = GRID_WIDTH // 2; current_piece_obj.y = 0
                        next_piece_obj = Piece(0,0)
                        if not is_valid_position(current_piece_obj, game_grid_data):
                            game_over_flag = True; current_piece_obj = None

                    last_fall_time_val = time.time()
                    soft_drop_flag = False # Reset soft drop after piece lands
                else: # Piece still falling
                    last_fall_time_val = time.time()


    # --- Game Over State Update (after all game logic for the frame) ---
    if game_over_flag and not game_over_sound_played_flag:
        play_sound("game_over"); game_over_sound_played_flag = True
        current_piece_obj = None # Ensure no piece is active
        if final_game_time_str_val is None:
            current_elapsed_time = time.time() - game_start_time_val - total_paused_duration_val
            final_game_time_str_val = format_time(max(0, current_elapsed_time))

    # Determine the time string to display (live or final frozen time)
    calculated_formatted_time_str = ""
    if game_over_flag and final_game_time_str_val:
        calculated_formatted_time_str = final_game_time_str_val
    elif game_paused_flag:
        elapsed_at_pause_moment = (time_at_pause_val - game_start_time_val) - total_paused_duration_val
        calculated_formatted_time_str = format_time(max(0, elapsed_at_pause_moment))
    else:
        current_elapsed_seconds = (time.time() - game_start_time_val) - total_paused_duration_val
        calculated_formatted_time_str = format_time(max(0, current_elapsed_seconds))

    return {
        "game_over": game_over_flag,
        "current_piece": current_piece_obj, # Potentially set to None
        "next_piece": next_piece_obj,
        "game_grid": game_grid_data,
        "score": score_val,
        "current_level": current_level_val,
        "total_lines_cleared": total_lines_cleared_val,
        "lines_for_current_level": lines_for_current_level_val,
        "current_fall_speed": current_fall_speed_val,
        "last_fall_time": last_fall_time_val,
        "soft_drop_active": soft_drop_flag,
        "game_over_sound_played": game_over_sound_played_flag,
        "last_ai_move_time": last_ai_move_time_val,
        "final_game_time_str": final_game_time_str_val,
        "formatted_time": calculated_formatted_time_str,
        "game_phase_str": game_phase_str, # Updated
        "lines_being_animated": lines_being_animated_list, # Added
        "line_animation_timer": line_animation_timer_val, # Added
        "game_grid": game_grid_data, # Added (potentially modified)
        "score": score_val, # Added (potentially modified)
        "current_level": current_level_val, # Added (potentially modified)
        "total_lines_cleared": total_lines_cleared_val, # Added (potentially modified)
        "lines_for_current_level": lines_for_current_level_val, # Added (potentially modified)
        "current_fall_speed": current_fall_speed_val, # Added (potentially modified)
        "next_piece": next_piece_obj # Added (potentially modified)
    }

def _finalize_line_clear(grid_data, lines_to_remove_indices, current_score, level, total_lines, lines_for_lvl):
    lines_to_remove_indices.sort(reverse=True)

    num_cleared = len(lines_to_remove_indices)
    for r_idx in lines_to_remove_indices:
        del grid_data[r_idx]

    for _ in range(num_cleared):
        grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])

    current_score += get_score_for_lines(num_cleared, level)
    total_lines += num_cleared
    lines_for_lvl = total_lines % LINES_PER_LEVEL

    new_level_calc = (total_lines // LINES_PER_LEVEL) + 1
    leveled_up = False
    if new_level_calc > level:
        level = min(new_level_calc, 100) # Cap level
        play_sound("level_up")
        leveled_up = True

    return {
        "grid_data": grid_data,
        "current_score": current_score,
        "level": level,
        "total_lines": total_lines,
        "lines_for_lvl": lines_for_lvl,
        "leveled_up": leveled_up
    }

def _render_help_text_surfaces(title_font, section_font, info_font, text_color):
    help_lines_data = [
        ("TETRIS - HELP", title_font),
        ("", section_font), # Spacer
        ("Keyboard Controls:", section_font),
        ("  Left Arrow:  Move Piece Left", info_font),
        ("  Right Arrow: Move Piece Right", info_font),
        ("  Up Arrow:    Rotate Piece", info_font),
        ("  Down Arrow:  Soft Drop Piece", info_font),
        ("  Space Bar:   Hard Drop Piece", info_font),
        ("  P:           Pause / Resume Game", info_font),
        ("  A:           Toggle AI Mode", info_font),
        ("  R:           Restart Game (Game Over)", info_font),
        ("  H:           Show / Hide Help", info_font), # This line is already correct
        ("  ESC:         Quit Game / Close Help", info_font),
        ("", section_font), # Spacer
        ("Joystick Controls (Defaults):", section_font),
        ("  Analog X / D-Pad X:   Move Left/Right", info_font),
        ("  Analog Y / D-Pad Y (Down): Soft Drop", info_font),
        ("  D-Pad Y (Up):         Rotate Piece", info_font),
        ("  Button 0 (A/X):       Rotate Piece", info_font),
        ("  Button 1 (B/Circle):  Hard Drop Piece", info_font),
        ("  Button 7 (Start):     Pause/Resume/Restart", info_font),
        ("  Button 6 (Select):    Toggle AI Mode", info_font),
        ("", section_font), # Spacer
        ("Press 'H' or 'ESC' to close.", info_font) # This line is also already correct
    ]
    rendered_surfaces = []
    for text, font in help_lines_data:
        surface = font.render(text, True, text_color)
        rendered_surfaces.append(surface)
    return rendered_surfaces

def _draw_help_screen(screen_surface, help_text_surfaces_list):
    # Draw Overlay
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180)) # Black with ~70% opacity
    screen_surface.blit(overlay, (0,0))

    # Calculate Total Height and Starting Position
    total_text_height = 0
    line_padding = 5 # pixels
    for surface in help_text_surfaces_list:
        total_text_height += surface.get_height()
    total_height_with_padding = total_text_height + (len(help_text_surfaces_list) - 1) * line_padding
    start_y = (SCREEN_HEIGHT - total_height_with_padding) // 2

    # Blit Text Surfaces
    current_y = start_y
    for surface in help_text_surfaces_list:
        text_x = (SCREEN_WIDTH - surface.get_width()) // 2
        screen_surface.blit(surface, (text_x, current_y))
        current_y += surface.get_height() + line_padding

def _draw_game_screen(screen_surface, game_grid_data, current_piece_obj, next_piece_obj, score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val, ai_mode_flag, formatted_time_str, game_over_flag, game_paused_flag, clock_obj, help_screen_active_flag, help_text_surfaces_list, game_phase_str, current_username_str, best_score_data_dict, lines_being_animated_list, line_animation_timer_val, config_menu_active_flag, sound_enabled_flag, shadow_enabled_flag): # Added shadow_enabled_flag
    # Drawing
    screen_surface.fill(BLACK) # Always fill screen first
    # Regular game drawing (grid, current piece, main UI)
    draw_grid_lines(screen_surface)
    draw_blocks(screen_surface, game_grid_data, lines_being_animated_list, line_animation_timer_val) # Pass animation states

    # Draw shadow piece before the actual piece
    if shadow_enabled_flag: # New condition for drawing shadow
        if not game_over_flag and current_piece_obj and game_phase_str == "PLAYING": # Keep existing conditions too
            shadow_y = get_shadow_position_y(current_piece_obj, game_grid_data)
            shadow_color = GREY # Or a more transparent color later

        # Check if current_piece_obj is still valid (it should be if we are in "PLAYING" phase)
        # and also ensure its shape and rotation are valid, though get_shadow_position_y implies validity.
        if current_piece_obj.shape and current_piece_obj.rotation < len(current_piece_obj.shape):
            for r_offset, c_offset in current_piece_obj.shape[current_piece_obj.rotation]:
                block_r = shadow_y + r_offset
                block_c = current_piece_obj.x + c_offset
                # Ensure block is within grid boundaries before drawing shadow
                if 0 <= block_r < GRID_HEIGHT and 0 <= block_c < GRID_WIDTH:
                    # Check if the cell for the shadow is empty (optional, but good for visual clarity)
                    # This prevents drawing shadow over existing landed blocks if logic is imperfect.
                    # However, get_shadow_position_y should give a position where it *can* land.
                    # For simplicity, we'll draw it directly.
                     pygame.draw.rect(screen_surface, shadow_color, (GRID_OFFSET_X + block_c * BLOCK_SIZE, GRID_OFFSET_Y + block_r * BLOCK_SIZE, BLOCK_SIZE -1, BLOCK_SIZE -1))

    if not game_over_flag and current_piece_obj and game_phase_str != "GETTING_USERNAME" and game_phase_str != "LINE_ANIMATION": # Don't draw falling piece during name input or line animation
         draw_current_piece_on_grid(screen_surface, current_piece_obj)

    draw_full_ui(screen_surface, score_val, current_level_val, total_lines_cleared_val, next_piece_obj if not game_over_flag else None, lines_for_current_level_val, ai_mode_flag, formatted_time_str, best_score_data_dict)

    if game_phase_str == "GETTING_USERNAME":
        # Draw "GAME OVER" and final score first
        game_over_text_surf = GAME_OVER_FONT.render("GAME OVER", True, RED)
        final_score_text = f"Final Score: {score_val}"
        final_score_surf = INFO_FONT.render(final_score_text, True, WHITE)
        text_rect_game_over = game_over_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - final_score_surf.get_height() / 2 - 40)) # Shift up
        text_rect_score = final_score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + game_over_text_surf.get_height() / 2 - 40)) # Shift up
        screen_surface.blit(game_over_text_surf, text_rect_game_over)
        screen_surface.blit(final_score_surf, text_rect_score)

        # Then draw the username input prompt
        prompt_font = INFO_FONT
        prompt_text_surface = prompt_font.render("New Best! Enter Name (Max 15):", True, WHITE)
        prompt_rect = prompt_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40))
        screen_surface.blit(prompt_text_surface, prompt_rect)

        name_input_surface = prompt_font.render(current_username_str, True, YELLOW)
        name_input_rect = name_input_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 80))
        screen_surface.blit(name_input_surface, name_input_rect)

        if time.time() % 1 < 0.5: # Blinking effect for cursor
            cursor_surface = prompt_font.render("_", True, YELLOW)
            # Position cursor next to the text, or at the center if text is empty
            cursor_x = name_input_rect.right + 2 if current_username_str else name_input_rect.centerx
            cursor_rect = cursor_surface.get_rect(topleft=(cursor_x, name_input_rect.top))
            screen_surface.blit(cursor_surface, cursor_rect)

    elif game_over_flag: # Normal "GAME_OVER" phase (not getting username)
        game_over_text_surf = GAME_OVER_FONT.render("GAME OVER", True, RED)
        final_score_text = f"Final Score: {score_val}"
        final_score_surf = INFO_FONT.render(final_score_text, True, WHITE)
        text_rect_game_over = game_over_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - final_score_surf.get_height() / 2))
        text_rect_score = final_score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + game_over_text_surf.get_height() / 2))
        screen_surface.blit(game_over_text_surf, text_rect_game_over)
        screen_surface.blit(final_score_surf, text_rect_score)
        restart_text_surf = INFO_FONT.render("Press 'R' to Restart", True, WHITE)
        quit_text_surf = INFO_FONT.render("Press 'ESC' to Quit", True, WHITE)
        y_pos_restart = text_rect_score.bottom + 20
        text_rect_restart = restart_text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos_restart + restart_text_surf.get_height() // 2))
        screen_surface.blit(restart_text_surf, text_rect_restart)
        y_pos_quit = text_rect_restart.bottom + 10
        text_rect_quit = quit_text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos_quit + quit_text_surf.get_height() // 2))
        screen_surface.blit(quit_text_surf, text_rect_quit)

    # Display PAUSED message if game is paused (and not game over, and help screen not active, and not getting username)
    # This condition needs to be more specific now: only show generic "PAUSED" if no other modal is active.
    if game_paused_flag and not game_over_flag and not help_screen_active_flag and not config_menu_active_flag and game_phase_str != "GETTING_USERNAME":
        pause_text_surface = GAME_OVER_FONT.render("PAUSED", True, YELLOW) # Using GAME_OVER_FONT for size
        text_rect_pause = pause_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        screen_surface.blit(pause_text_surface, text_rect_pause)

    # Draw help screen if active (on top of everything else)
    if help_screen_active_flag:
        _draw_help_screen(screen_surface, help_text_surfaces_list) # Ensure this uses the passed parameter
    elif config_menu_active_flag: # Use elif as help and config shouldn't be simultaneously active based on event logic
        # Draw Overlay for Config Menu
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180)) # Black with ~70% opacity
        screen_surface.blit(overlay, (0,0))

        # Config Menu Title
        # Assuming GAME_OVER_FONT and INFO_FONT are loaded globally and available
        title_text_surf = GAME_OVER_FONT.render("CONFIGURATION MENU", True, WHITE)
        title_rect = title_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        screen_surface.blit(title_text_surf, title_rect)

        # Sound Option Text
        sound_status_str = "ON" if sound_enabled_flag else "OFF"
        sound_option_text_str = f"Sound: {sound_status_str} (Press S to toggle)"
        sound_option_surf = INFO_FONT.render(sound_option_text_str, True, WHITE)
        sound_option_rect = sound_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20)) # Adjusted Y
        screen_surface.blit(sound_option_surf, sound_option_rect)

        # Shadow Option Text
        shadow_status_str = "ON" if shadow_enabled_flag else "OFF"
        shadow_option_text_str = f"Shadow: {shadow_status_str} (Press D to toggle)"
        shadow_option_surf = INFO_FONT.render(shadow_option_text_str, True, WHITE)
        shadow_option_rect = shadow_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)) # Adjusted Y
        screen_surface.blit(shadow_option_surf, shadow_option_rect)

        # Close Menu Hint
        close_hint_surf = INFO_FONT.render("Press C or ESC to close", True, GREY)
        close_hint_rect = close_hint_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100)) # Adjusted Y
        screen_surface.blit(close_hint_surf, close_hint_rect)

    pygame.display.flip()
    if clock_obj: # Ensure clock_obj is provided before ticking
        clock_obj.tick(60)

def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Tetris Game with an AI player option.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging to console.")
    args = parser.parse_args()

    global DEBUG_MODE # Declare intent to modify the global DEBUG_MODE
    if args.debug:
        DEBUG_MODE = True
        print("DEBUG MODE ENABLED")
    # --- End Argument Parsing ---
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS
    global sound_enabled # Ensure main uses and can modify the global sound_enabled
    global shadow_enabled # Ensure main uses and can modify the global shadow_enabled

    # Load configuration
    loaded_config = load_config()
    # load_config ensures that both keys are present and are booleans.
    # Using .get() as an additional safety for direct access, though load_config should prevent KeyErrors.
    if isinstance(loaded_config, dict):
        sound_enabled = loaded_config.get("sound_enabled", True)
        shadow_enabled = loaded_config.get("shadow_enabled", True)
    else:
        # This case should be rare if load_config is robust as implemented
        if DEBUG_MODE: print("Warning: load_config did not return a dictionary. Using default settings for sound and shadow.")
        sound_enabled = True
        shadow_enabled = True

    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE); INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)
    # Pre-render help text surfaces (using appropriate fonts)
    help_text_surfaces = _render_help_text_surfaces(GAME_OVER_FONT, SCORE_FONT, INFO_FONT, WHITE)
    best_score_data = _load_best_score()


    if not os.path.isdir(SOUND_DIR): print(f"Sound directory '{SOUND_DIR}' not found.")
    else:
        SOUND_EFFECTS["move"]=load_sound("move.wav"); SOUND_EFFECTS["rotate"]=load_sound("rotate.wav")
        SOUND_EFFECTS["drop"]=load_sound("drop.wav"); SOUND_EFFECTS["line_clear"]=load_sound("line_clear.wav")
        SOUND_EFFECTS["tetris_clear"]=load_sound("tetris_clear.wav"); SOUND_EFFECTS["level_up"]=load_sound("level_up.wav")
        SOUND_EFFECTS["game_over"]=load_sound("game_over.wav")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(SCREEN_TITLE)

    joystick = None
    joystick_enabled = False
    if pygame.joystick.get_count() > 0:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        joystick_enabled = True
        print(f"Joystick enabled: {joystick.get_name()}")
    else:
        print("No joystick detected.")

    clock = pygame.time.Clock() # Moved clock initialization here as it's used by _draw_game_screen

    # Initial game state setup
    game_state_dict = reset_game_state()
    (game_grid, current_piece, next_piece, score, current_level,
     total_lines_cleared, lines_for_current_level, game_over,
     current_fall_speed, last_fall_time, soft_drop_active,
     game_over_sound_played, ai_mode_active, last_ai_move_time,
     game_start_time, final_game_time_str, game_paused,
     time_at_pause, total_paused_duration) = _unpack_game_state(game_state_dict)

    running = True
    help_screen_active = False
    config_menu_active = False # New variable for config menu
    # sound_enabled is now a global, initialized by load_config() just above.
    # The global declaration for sound_enabled is now placed higher, before load_config() call.
    # No need for another `global sound_enabled` here as it's already done before load_config.
    game_phase = "PLAYING"
    current_username_input = ""
    formatted_time = ""
    lines_being_animated = []
    line_animation_timer = 0

    while running:
        # Event Handling
        events = pygame.event.get()
        event_handling_result = _handle_events(
            events, game_over, game_paused, ai_mode_active, soft_drop_active,
            current_piece, game_grid, running,
            time_at_pause, total_paused_duration, last_fall_time, last_ai_move_time,
            joystick, joystick_enabled, help_screen_active,
            game_phase, current_username_input, config_menu_active, sound_enabled, shadow_enabled # Pass current global states
        )

        running = event_handling_result["running"]
        game_paused = event_handling_result["game_paused"]
        ai_mode_active = event_handling_result["ai_mode_active"]
        soft_drop_active = event_handling_result["soft_drop_active"]
        current_piece = event_handling_result["current_piece"]
        time_at_pause = event_handling_result["time_at_pause"]
        total_paused_duration = event_handling_result["total_paused_duration"]
        last_fall_time = event_handling_result["last_fall_time"]
        last_ai_move_time = event_handling_result["last_ai_move_time"]
        action_request = event_handling_result["action_request"]
        help_screen_active = event_handling_result["help_screen_active"]
        config_menu_active = event_handling_result["config_menu_active"] # Update local var from return
        sound_enabled = event_handling_result["sound_enabled"]           # Update global var from return
        shadow_enabled = event_handling_result["shadow_enabled"]         # Update global var from return
        current_username_input = event_handling_result["current_username_input"]
        # game_phase is now primarily managed by main based on action_request or game_over state changes

        if not running:
            break

        if action_request == "RESTART":
            game_state_dict = _handle_restart_action()
            (game_grid, current_piece, next_piece, score, current_level,
             total_lines_cleared, lines_for_current_level, game_over,
             current_fall_speed, last_fall_time, soft_drop_active,
             game_over_sound_played, ai_mode_active, last_ai_move_time,
             game_start_time, final_game_time_str, game_paused,
             time_at_pause, total_paused_duration) = _unpack_game_state(game_state_dict)
            formatted_time = ""
            help_screen_active = False
            game_phase = "PLAYING"
            current_username_input = ""
            continue

        if action_request == "SAVE_SCORE":
            _save_best_score(current_username_input, score, final_game_time_str if final_game_time_str else formatted_time)
            best_score_data = _load_best_score()
            game_phase = "GAME_OVER"
            current_username_input = ""
        elif action_request == "SKIP_SAVE":
            game_phase = "GAME_OVER"
            current_username_input = ""

        prev_game_over = game_over

        game_logic_result = _update_game_state(
            game_over, game_paused, ai_mode_active, current_piece, next_piece,
            game_grid, score, current_level, total_lines_cleared,
            lines_for_current_level, current_fall_speed, last_fall_time,
            soft_drop_active, game_over_sound_played, last_ai_move_time,
            game_start_time, final_game_time_str, total_paused_duration, time_at_pause,
            help_screen_active, game_phase,
            lines_being_animated, line_animation_timer # Pass new animation states
        )

        game_over = game_logic_result["game_over"]
        current_piece = game_logic_result["current_piece"]
        next_piece = game_logic_result["next_piece"]
        game_grid = game_logic_result["game_grid"]
        score = game_logic_result["score"]
        current_level = game_logic_result["current_level"]
        total_lines_cleared = game_logic_result["total_lines_cleared"]
        lines_for_current_level = game_logic_result["lines_for_current_level"]
        current_fall_speed = game_logic_result["current_fall_speed"]
        last_fall_time = game_logic_result["last_fall_time"]
        soft_drop_active = game_logic_result["soft_drop_active"]
        game_over_sound_played = game_logic_result["game_over_sound_played"]
        last_ai_move_time = game_logic_result["last_ai_move_time"]
        final_game_time_str = game_logic_result["final_game_time_str"]
        formatted_time = game_logic_result["formatted_time"]
        game_phase = game_logic_result["game_phase_str"] # Unpack game_phase
        lines_being_animated = game_logic_result["lines_being_animated"] # Unpack lines_being_animated
        line_animation_timer = game_logic_result["line_animation_timer"] # Unpack line_animation_timer


        # (This should be after game_over is updated by _update_game_state result,
        # and before the if game_over and not prev_game_over block)
        if DEBUG_MODE: print(f"DEBUG MainLoop: game_over={game_over}, prev_game_over={prev_game_over}, score={score}, best_score={best_score_data.get('score')}, current_game_phase='{game_phase}'")

        # Game Phase Transition Logic (after game logic updates game_over)
        if game_over and not prev_game_over: # Game just ended
            if DEBUG_MODE: print(f"DEBUG MainLoop: Game JUST ENDED. Comparing score ({score}) with best_score ({best_score_data.get('score')}).")
            if score > best_score_data["score"]:
                game_phase = "GETTING_USERNAME"
                current_username_input = "" # Ensure it's reset
                if DEBUG_MODE: print(f"DEBUG MainLoop: New best score! game_phase set to '{game_phase}'.")
                # game_paused is likely already true if help screen was used, or should be set
                # game_paused = True # Ensure game is paused for name input
            else:
                game_phase = "GAME_OVER"
                if DEBUG_MODE: print(f"DEBUG MainLoop: Not a new best score. game_phase set to '{game_phase}'.")

        # Drawing
        _draw_game_screen(
            screen, game_grid, current_piece, next_piece, score, current_level,
            total_lines_cleared, lines_for_current_level, ai_mode_active,
            formatted_time, game_over, game_paused, clock,
            help_screen_active, help_text_surfaces,
            game_phase, current_username_input, best_score_data,
            lines_being_animated, line_animation_timer,
            config_menu_active, sound_enabled, shadow_enabled # Pass all flags
        )
    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
