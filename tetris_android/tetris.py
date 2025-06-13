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


def draw_full_ui(screen, score, level, lines_cleared_total, next_p, lines_for_current_level):
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
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING # Space after Lines text

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
                elif current_move_score == best_score:
                    # Prefer moves that result in lower piece height (less risk)
                    # This requires landing_y from simulate_place_piece
                    # For now, just take the first best score found.
                    # A more sophisticated tie-breaker could be added here.
                    pass # Keep first best if scores are equal

    return best_x, best_rotation, best_score


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

    game_grid = create_grid(); score = 0; current_level = 1; total_lines_cleared = 0
    lines_for_current_level = 0 # Lines cleared since last level up, for progress bar

    current_piece = spawn_piece_at_start()
    next_piece = Piece(0,0)

    game_over = False
    if not is_valid_position(current_piece, game_grid): game_over = True; current_piece = None

    last_fall_time = time.time(); current_fall_speed = calculate_fall_speed(current_level)
    soft_drop_active = False; running = True; clock = pygame.time.Clock()
    game_over_sound_played = False
    ai_mode_active = False # True if AI is controlling the game


    while running:
        AI_MOVE_DELAY = 0.1 # Seconds between AI moves, can be adjusted. Set to 0 for max speed.
        # last_ai_move_time = time.time() # Initialize AI move timer - This should be outside the main loop or it resets every frame. Moved to main init.
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False

            # AI Mode Toggle Event
            if event.type == pygame.KEYDOWN:
                if event.key == AI_PLAYER_TOGGLE_KEY:
                    ai_mode_active = not ai_mode_active
                    print(f"AI Mode Toggled: {ai_mode_active}")
                    if ai_mode_active:
                        # When AI activates, reset any player-induced states for the current piece
                        soft_drop_active = False
                        if current_piece:
                            current_piece.is_hard_dropping_animated = False # Cancel player hard drop
                        last_ai_move_time = time.time() # Allow AI to make a move soon
                    # else: # Optional: when AI deactivates, maybe reset piece to top?
                        # current_piece = spawn_piece_at_start()
                        # next_piece = Piece(0,0)
                        # if current_piece and not is_valid_position(current_piece, game_grid): game_over = True; current_piece = None

            if not game_over and current_piece and not ai_mode_active: # Player input for piece control gated if AI active
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP and not (current_piece and current_piece.is_hard_dropping_animated): current_piece.rotate(game_grid)
                    elif event.key == pygame.K_LEFT and not (current_piece and current_piece.is_hard_dropping_animated):
                        current_piece.x -= 1
                        if not is_valid_position(current_piece, game_grid): current_piece.x += 1
                        else: play_sound("move")
                    elif event.key == pygame.K_RIGHT and not (current_piece and current_piece.is_hard_dropping_animated):
                        current_piece.x += 1
                        if not is_valid_position(current_piece, game_grid): current_piece.x -= 1
                        else: play_sound("move")
                    elif event.key == pygame.K_DOWN and not (current_piece and current_piece.is_hard_dropping_animated): soft_drop_active = True
                    elif event.key == pygame.K_SPACE: # Initiate Animated Hard Drop
                        if current_piece and not current_piece.is_hard_dropping_animated: # Prevent re-triggering during animation
                            original_y = current_piece.y # Store current Y before calculation
                            # Calculate target_y without actually moving the piece for animation yet

                            # Create a temporary piece for calculation to avoid altering current_piece's state
                            temp_piece_for_calc = Piece(current_piece.x, original_y, current_piece.shape_type)
                            temp_piece_for_calc.rotation = current_piece.rotation # Match rotation

                            calculated_target_y = original_y # Start calculation from current y
                            # Calculate target_y by checking downwards until an invalid position is found
                            # Loop to find how far down the piece can go from its *original_y*
                            # check_y_offset is relative to the piece's *current* y, which is original_y for temp_piece_for_calc
                            while is_valid_position(temp_piece_for_calc, game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                                calculated_target_y += 1

                            current_piece.target_y_for_animated_drop = calculated_target_y # Store the final landing Y
                            # current_piece.y is NOT changed here; it remains original_y. Animation handles the visual drop.
                            current_piece.is_hard_dropping_animated = True # Activate animation state
                            soft_drop_active = False # Ensure soft drop is not active during animation
                            # last_fall_time = time.time() # Optional: Reset fall timer for smoother anim start

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN and not (current_piece and current_piece.is_hard_dropping_animated) and not ai_mode_active: soft_drop_active = False # Disable soft drop deactivation during animation & AI mode

        # --- AI Player Decision Logic ---
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

        if game_over and not game_over_sound_played:
            play_sound("game_over"); game_over_sound_played = True
            current_piece = None

        # Drawing
        screen.fill(BLACK)
        draw_grid_lines(screen)
        draw_blocks(screen, game_grid)
        if not game_over and current_piece:
             draw_current_piece_on_grid(screen, current_piece)

        draw_full_ui(screen, score, current_level, total_lines_cleared, next_piece if not game_over else None, lines_for_current_level)

        if game_over:
            game_over_text_surf = GAME_OVER_FONT.render("GAME OVER", True, RED)
            final_score_text = f"Final Score: {score}"
            final_score_surf = INFO_FONT.render(final_score_text, True, WHITE)

            text_rect_game_over = game_over_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - final_score_surf.get_height() / 2))
            text_rect_score = final_score_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + game_over_text_surf.get_height() / 2))

            screen.blit(game_over_text_surf, text_rect_game_over)
            screen.blit(final_score_surf, text_rect_score)

        pygame.display.flip()
        clock.tick(60)

    # This sleep is outside the main running loop, so it executes after pygame.quit() if not careful
    # pygame.quit() should be the very last thing related to pygame.

    # Keep window open for a bit after game over, only if game_over is true
    # The main loop `while running` now handles this by continuing to draw the game over screen
    # until `running` is set to False (e.g., by QUIT event).
    # The sleep here is effectively for console applications or if quit is immediate.
    # For Pygame, the loop itself manages visibility.
    # if game_over: time.sleep(3) # This might be problematic if pygame is already quit.

    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
