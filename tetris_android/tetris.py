import pygame
import random
import time
import os
import copy

# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()

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

# Progress Bar UI Constants
PROGRESS_BAR_WIDTH = 150 # Width of the level progress bar in pixels
PROGRESS_BAR_HEIGHT = 20 # Height of the level progress bar in pixels
PROGRESS_BAR_BACKGROUND_COLOR = (50, 50, 50) # Dark Grey
PROGRESS_BAR_FILL_COLOR = GREEN # Using existing GREEN = (0, 255, 0)
PROGRESS_BAR_BORDER_COLOR = GREY  # Using existing GREY = (128, 128, 128)
SCORE_FONT = None; INFO_FONT = None; TITLE_FONT = None; GAME_OVER_FONT = None

SOUND_EFFECTS = {"move": None, "rotate": None, "drop": None, "line_clear": None, "tetris_clear": None, "level_up": None, "game_over": None}
SOUND_DIR = "sounds"

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path): print(f"Sound file not found: {path}"); return None
    try: sound = pygame.mixer.Sound(path); sound.set_volume(0.3); return sound
    except pygame.error as e: print(f"Error loading sound {filename}: {e}"); return None

def play_sound(sound_name):
    if SOUND_EFFECTS.get(sound_name): SOUND_EFFECTS[sound_name].play()

class Piece:
    def __init__(self, x, y, shape_type=None): # Allow forcing shape_type for next_piece
        if shape_type is None:
            self.shape_type = random.randint(0, len(SHAPES) - 1)
        else:
            self.shape_type = shape_type
        self.shape = SHAPES[self.shape_type]
        self.color = PIECE_COLORS[self.shape_type]
        # Ensure color is RGB (tuple of 3) and derive RGBA shadow_color (tuple of 4)
        if len(self.color) == 3:
            self.shadow_color = (self.color[0], self.color[1], self.color[2], 100)
        else: # Assuming color might already have alpha, just adjust it or use as is
            self.shadow_color = (self.color[0], self.color[1], self.color[2], 100) # Or handle error/logging
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
def draw_blocks(screen, grid_data): # Draws landed blocks
    for r_idx, row in enumerate(grid_data):
        for c_idx, cell_color in enumerate(row):
            if cell_color != 0:
                pygame.draw.rect(screen, cell_color, (GRID_OFFSET_X + c_idx * BLOCK_SIZE, GRID_OFFSET_Y + r_idx * BLOCK_SIZE, BLOCK_SIZE -1, BLOCK_SIZE -1))
def draw_current_piece_on_grid(screen, piece): # Renamed for clarity
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >= 0: # Only draw if within visible grid area
                pygame.draw.rect(screen, piece.color, (GRID_OFFSET_X + c_idx * BLOCK_SIZE, GRID_OFFSET_Y + r_idx * BLOCK_SIZE, BLOCK_SIZE -1, BLOCK_SIZE -1))

def draw_shadow_piece(screen, piece, shadow_y):
    """Draws the transparent shadow of a piece at the given shadow_y."""
    if not piece or piece.shadow_color is None:
        return

    shape_to_draw = piece.shape[piece.rotation]
    for r_offset, c_offset in shape_to_draw:
        # Grid coordinates for this block of the shadow piece
        grid_r = shadow_y + r_offset
        grid_c = piece.x + c_offset

        # Only draw if within the visible part of the grid (especially top boundary)
        # and also within horizontal grid boundaries.
        if grid_r >= 0 and 0 <= grid_c < GRID_WIDTH:
            draw_x = GRID_OFFSET_X + grid_c * BLOCK_SIZE
            draw_y = GRID_OFFSET_Y + grid_r * BLOCK_SIZE

            # Create a temporary surface for the shadow block to handle transparency
            shadow_block_surface = pygame.Surface((BLOCK_SIZE - 1, BLOCK_SIZE - 1), pygame.SRCALPHA)
            shadow_block_surface.fill(piece.shadow_color) # Fill with RGBA color
            screen.blit(shadow_block_surface, (draw_x, draw_y))

def is_valid_position(piece, grid_data, check_y_offset=0): # For main game piece
    if not piece: return False
    for r_idx, c_idx in piece.current_shape_coords():
        actual_r = r_idx + check_y_offset
        if not (0 <= c_idx < GRID_WIDTH): return False
        if not (actual_r < GRID_HEIGHT): return False
        if actual_r >= 0 and grid_data[actual_r][c_idx] != 0: return False
    return True

def get_shadow_position(piece, grid_data):
    """
    Calculates the lowest possible y coordinate (row) for a piece before collision.
    Uses the check_y_offset parameter of is_valid_position to avoid modifying the piece.
    """
    if not piece:
        return -1 # Or some other indicator of an invalid input or inability to calculate

    current_y_offset = 0
    # Starting from 0 offset (current piece.y), check downwards
    # Increment offset as long as the position with that offset is valid
    while is_valid_position(piece, grid_data, check_y_offset=current_y_offset + 1):
        current_y_offset += 1

    # The final landing position's y is piece.y + current_y_offset
    # current_shape_coords() uses piece.y, so we return the absolute y coordinate
    # that the piece's pivot would be at.
    return piece.y + current_y_offset

def add_to_grid(piece, grid_data):
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >=0: grid_data[r_idx][c_idx] = piece.color
        play_sound("drop")

def check_and_clear_lines(grid_data):
    lines_cleared = 0; r = GRID_HEIGHT - 1
    while r >= 0:
        if 0 not in grid_data[r]: lines_cleared += 1; del grid_data[r]; grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])
        else: r -= 1
    if lines_cleared > 0:
        if lines_cleared == 4: play_sound("tetris_clear")
        else: play_sound("line_clear")
    return lines_cleared

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


def draw_full_ui(screen, score, level, lines_cleared_total, next_p, lines_for_current_level, ai_mode_is_active, formatted_time_str): # Added formatted_time_str
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
            return "INITIATE_RESTART" # Changed from "RESTART"
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

def trigger_game_restart():
    """Calls reset_game_state and returns the new state. Centralizes restart triggering."""
    return reset_game_state()

def main():
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS
    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE); INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)

    if not os.path.isdir(SOUND_DIR): print(f"Sound directory '{SOUND_DIR}' not found.") # Check isdir
    else:
        SOUND_EFFECTS["move"]=load_sound("move.wav"); SOUND_EFFECTS["rotate"]=load_sound("rotate.wav")
        SOUND_EFFECTS["drop"]=load_sound("drop.wav"); SOUND_EFFECTS["line_clear"]=load_sound("line_clear.wav")
        SOUND_EFFECTS["tetris_clear"]=load_sound("tetris_clear.wav"); SOUND_EFFECTS["level_up"]=load_sound("level_up.wav")
        SOUND_EFFECTS["game_over"]=load_sound("game_over.wav")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(SCREEN_TITLE)

    # Initial game state setup using the reset function
    game_state = reset_game_state()
    # Unpack all game state variables from the dictionary
    game_grid = game_state["game_grid"]; current_piece = game_state["current_piece"]; next_piece = game_state["next_piece"]
    score = game_state["score"]; current_level = game_state["current_level"]; total_lines_cleared = game_state["total_lines_cleared"]
    lines_for_current_level = game_state["lines_for_current_level"]; game_over = game_state["game_over"]
    current_fall_speed = game_state["current_fall_speed"]; last_fall_time = game_state["last_fall_time"]
    soft_drop_active = game_state["soft_drop_active"]; game_over_sound_played = game_state["game_over_sound_played"]
    ai_mode_active = game_state["ai_mode_active"]; last_ai_move_time = game_state["last_ai_move_time"]
    game_start_time = game_state["game_start_time"]; final_game_time_str = game_state["final_game_time_str"]
    game_paused = game_state["game_paused"]; time_at_pause = game_state["time_at_pause"]; total_paused_duration = game_state["total_paused_duration"]

    running = True; clock = pygame.time.Clock()
    AI_MOVE_DELAY = 0.05 # Time in seconds between AI moves, adjust for speed

    while running:
        for event in pygame.event.get():
            # Top-level quit check (handles window close)
            if event.type == pygame.QUIT:
                running = False
                continue # Skip further processing for this event

            # Game Over State Input Handling
            if game_over:
                action = handle_game_over_inputs(event) # Check for restart or quit commands
                if action == "INITIATE_RESTART": # Changed condition
                    game_state = trigger_game_restart() # Call the new restart trigger function
                    # Unpack all game state variables from the dictionary for the new game
                    game_grid = game_state["game_grid"]
                    current_piece = game_state["current_piece"]
                    next_piece = game_state["next_piece"]
                    score = game_state["score"]
                    current_level = game_state["current_level"]
                    total_lines_cleared = game_state["total_lines_cleared"]
                    lines_for_current_level = game_state["lines_for_current_level"]
                    game_over = game_state["game_over"] # This will be False from reset_game_state
                    current_fall_speed = game_state["current_fall_speed"]
                    last_fall_time = game_state["last_fall_time"]
                    soft_drop_active = game_state["soft_drop_active"]
                    game_over_sound_played = game_state["game_over_sound_played"]
                    ai_mode_active = game_state["ai_mode_active"]
                    last_ai_move_time = game_state["last_ai_move_time"]
                    game_start_time = game_state["game_start_time"]
                    final_game_time_str = game_state["final_game_time_str"]
                    game_paused = game_state["game_paused"]
                    time_at_pause = game_state["time_at_pause"]
                    total_paused_duration = game_state["total_paused_duration"]
                    continue # Important to process next frame with the new game state
                elif action == "QUIT":
                    running = False # Set running to false to exit the main loop
                    continue # Skip further processing for this event

            # Active Gameplay Input Handling (Not Game Over)
            else:
                # Pause Toggle (handles KEYDOWN for PAUSE_KEY)
                if event.type == pygame.KEYDOWN and event.key == PAUSE_KEY:
                    game_paused = not game_paused
                    if game_paused:
                        time_at_pause = time.time() # Record time when paused
                        print("Game Paused")
                        # play_sound("pause") # Optional: if pause sound exists
                    else: # Game is unpausing
                        # Add the duration of this pause to total_paused_duration
                        total_paused_duration += time.time() - time_at_pause
                        # Adjust last_fall_time and last_ai_move_time to prevent sudden catch-up
                        # This makes the piece and AI resume from the moment of unpause, not "catching up" on paused time.
                        last_fall_time = time.time()
                        last_ai_move_time = time.time()
                        print("Game Resumed")
                        # play_sound("unpause") # Optional: if unpause sound exists

                # Process other game inputs only if not paused
                if not game_paused:
                    # AI Mode Toggle (handles KEYDOWN for AI_PLAYER_TOGGLE_KEY)
                    if event.type == pygame.KEYDOWN and event.key == AI_PLAYER_TOGGLE_KEY:
                        ai_mode_active = not ai_mode_active
                        print(f"AI Mode Toggled: {ai_mode_active}")
                        if ai_mode_active: # When AI is activated
                            soft_drop_active = False # Ensure player's soft drop is off
                            if current_piece: current_piece.is_hard_dropping_animated = False # Cancel any ongoing player hard drop
                            last_ai_move_time = time.time() # Allow AI to make a move relatively soon

                    # Player-specific controls: only if a piece exists and AI mode is OFF
                    if current_piece and not ai_mode_active:
                        # Player piece controls are handled by this function (KEYDOWN for movements, KEYUP for K_DOWN release).
                        # It internally checks for is_hard_dropping_animated to prevent conflicts.
                        soft_drop_active = handle_player_piece_controls(event, current_piece, game_grid, soft_drop_active)

        # --- Game Logic (AI, Piece Movement, Physics) ---
        # These sections only run if the game is not paused.
        if not game_paused:
            # --- AI Player Decision Logic ---
            # This remains outside the event loop, processed each frame if AI is active
            if ai_mode_active and not game_over and current_piece and not current_piece.is_hard_dropping_animated:
                if time.time() - last_ai_move_time > AI_MOVE_DELAY: # Control AI thinking/move frequency
                    grid_copy_for_ai = clone_grid(game_grid) # Give AI a fresh copy of the board
                # Pass current_piece and next_piece (if AI uses it)
                # The find_best_move function was updated to return a dictionary
                best_move_info = find_best_move(grid_copy_for_ai, current_piece, next_piece)

                if best_move_info and best_move_info['x'] != -1: # Check if a valid move was found
                    # print(f"AI move: r={best_move_info['rotation']}, x={best_move_info['x']}, y_land={best_move_info['landing_y']}, s={best_move_info['score']:.2f}")
                    current_piece.rotation = best_move_info['rotation']
                    current_piece.x = best_move_info['x']
                    # AI always hard drops; use the animation for visual feedback
                    current_piece.target_y_for_animated_drop = best_move_info['landing_y']
                    current_piece.is_hard_dropping_animated = True
                    soft_drop_active = False # Ensure soft drop is off for AI moves
                else:
                    # This case implies AI found no valid moves. Should ideally not happen unless game is about to be over.
                    print("AI: No valid moves found by find_best_move. Setting game over.")
                    game_over = True # If AI cannot find a move, game is likely over or in an unrecoverable state.
                last_ai_move_time = time.time() # Reset AI move timer

        # --- Animated Hard Drop Logic (executes if is_hard_dropping_animated is True) ---
        if not game_over and current_piece and current_piece.is_hard_dropping_animated:
            current_piece.y += 1 # Move piece down for animation frame
            # Check if piece reached or passed its target landing position
            if current_piece.y >= current_piece.target_y_for_animated_drop:
                current_piece.y = current_piece.target_y_for_animated_drop # Ensure it lands exactly on target
                current_piece.is_hard_dropping_animated = False # Deactivate animation state
                # current_piece.target_y_for_animated_drop = -1 # Reset target_y (optional)
                # --- Piece has landed: Lock piece and handle consequences (lines, score, next piece) ---
                add_to_grid(current_piece, game_grid)
                lines_this_drop = check_and_clear_lines(game_grid)
                if lines_this_drop > 0:
                    score += get_score_for_lines(lines_this_drop, current_level)
                    total_lines_cleared += lines_this_drop
                    lines_for_current_level = total_lines_cleared % LINES_PER_LEVEL # Update progress for current level's bar
                    new_level_calc = (total_lines_cleared // LINES_PER_LEVEL) + 1
                    if new_level_calc > current_level:
                        current_level = min(new_level_calc, 100)
                        current_fall_speed = calculate_fall_speed(current_level)
                        play_sound("level_up")
                        if add_garbage_blocks(game_grid, current_level):
                            game_over = True; current_piece = None
                if not game_over:
                    current_piece = next_piece
                    current_piece.x = GRID_WIDTH // 2; current_piece.y = 0
                    next_piece = Piece(0,0)
                    if not is_valid_position(current_piece, game_grid):
                        game_over = True; current_piece = None
                last_fall_time = time.time()
                soft_drop_active = False # Cancel soft drop after any lock
            # else: piece continues animating downwards next frame

        # Automatic piece descent (handles normal fall and soft drop)
        if not game_over and current_piece and not current_piece.is_hard_dropping_animated: # Normal piece fall, only if not hard drop animating
            fall_interval = current_fall_speed
            if soft_drop_active: fall_interval = min(current_fall_speed, 0.05)

            if time.time() - last_fall_time > fall_interval:
                current_piece.y += 1
                if not is_valid_position(current_piece, game_grid):
                    current_piece.y -= 1
                    add_to_grid(current_piece, game_grid)
                    lines_this_drop = check_and_clear_lines(game_grid)
                    if lines_this_drop > 0:
                        score += get_score_for_lines(lines_this_drop, current_level); total_lines_cleared += lines_this_drop
                        lines_for_current_level = total_lines_cleared % LINES_PER_LEVEL # Update progress for current level's bar
                        new_level_calc = (total_lines_cleared // LINES_PER_LEVEL) + 1
                        if new_level_calc > current_level:
                            current_level = min(new_level_calc, 100); current_fall_speed = calculate_fall_speed(current_level)
                            play_sound("level_up")
                            if add_garbage_blocks(game_grid, current_level): game_over = True; current_piece = None

                    if not game_over:
                        current_piece = next_piece
                        current_piece.x = GRID_WIDTH // 2; current_piece.y = 0
                        next_piece = Piece(0,0)
                        if not is_valid_position(current_piece, game_grid): game_over = True; current_piece = None
                last_fall_time = time.time()

        # --- Game Over State Update (after all game logic for the frame) ---
        if game_over and not game_over_sound_played:
            play_sound("game_over"); game_over_sound_played = True
            current_piece = None
            if final_game_time_str is None: # Capture time only once
                # Ensure this uses the most up-to-date game_start_time and total_paused_duration
                current_elapsed_time = time.time() - game_start_time - total_paused_duration
                final_game_time_str = format_time(max(0, current_elapsed_time)) # Capture final time accurately, ensure non-negative

        # Determine the time string to display (live or final frozen time)
        if game_over and final_game_time_str:
            # If game is over and final time is captured, use it
            formatted_time = final_game_time_str
        elif game_paused:
            # If game is paused, display the time as it was at the moment of pausing
            # total_paused_duration here reflects pauses *before* the current one.
            elapsed_at_pause_moment = (time_at_pause - game_start_time) - total_paused_duration
            formatted_time = format_time(max(0, elapsed_at_pause_moment)) # Ensure non-negative
        else:
            # Game is active and not paused, calculate current live time including all pause durations
            current_elapsed_seconds = (time.time() - game_start_time) - total_paused_duration
            formatted_time = format_time(max(0, current_elapsed_seconds)) # Ensure non-negative

        # Drawing
        screen.fill(BLACK)
        draw_grid_lines(screen)
        draw_blocks(screen, game_grid) # Draws landed blocks

        # Draw shadow piece (ghost piece)
        if not game_over and current_piece:
            shadow_y = get_shadow_position(current_piece, game_grid)
            draw_shadow_piece(screen, current_piece, shadow_y)

        # Draw current falling piece
        if not game_over and current_piece:
             draw_current_piece_on_grid(screen, current_piece)

        draw_full_ui(screen, score, current_level, total_lines_cleared, next_piece if not game_over else None, lines_for_current_level, ai_mode_active, formatted_time) # Pass formatted_time (and ai_mode_active)

        if game_over:
            # Display Game Over and Final Score (Time is handled by draw_full_ui)
            game_over_text_surf = GAME_OVER_FONT.render("GAME OVER", True, RED)
            final_score_text = f"Final Score: {score}"
            final_score_surf = INFO_FONT.render(final_score_text, True, WHITE)

            text_rect_game_over = game_over_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - final_score_surf.get_height() / 2))
            text_rect_score = final_score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + game_over_text_surf.get_height() / 2))

            screen.blit(game_over_text_surf, text_rect_game_over)
            screen.blit(final_score_surf, text_rect_score)

            # Add Restart and Quit instructions to Game Over screen
            restart_text_surf = INFO_FONT.render("Press 'R' to Restart", True, WHITE)
            quit_text_surf = INFO_FONT.render("Press 'ESC' to Quit", True, WHITE)

            y_pos_restart = text_rect_score.bottom + 20 # Position below final score
            text_rect_restart = restart_text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos_restart + restart_text_surf.get_height() // 2))
            screen.blit(restart_text_surf, text_rect_restart)

            y_pos_quit = text_rect_restart.bottom + 10 # Padding
            text_rect_quit = quit_text_surf.get_rect(center=(SCREEN_WIDTH // 2, y_pos_quit + quit_text_surf.get_height() // 2))
            screen.blit(quit_text_surf, text_rect_quit)

        # Display PAUSED message if game is paused (and not game over)
        if game_paused and not game_over:
            pause_text_surface = GAME_OVER_FONT.render("PAUSED", True, YELLOW) # Using GAME_OVER_FONT for size
            text_rect_pause = pause_text_surface.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            screen.blit(pause_text_surface, text_rect_pause)

        pygame.display.flip()
        clock.tick(60)

    # This sleep is outside the main running loop, so it executes after pygame.quit() if not careful
    # pygame.quit() should be the very last thing related to pygame.

    # Keep window open for a bit after game over, only if game_over is true
    # The main loop `while running` now handles this by continuing to draw the game over screen
    # until `running` is set to False (e.g., by QUIT event).
    # The sleep here is effectively for console applications or if quit is immediate.
    # For Pygame, the loop itself manages visibility.
    # No time.sleep(3) here as game over screen is part of the loop.

    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
