import pygame
import random
import time
import os
import copy
import json
import argparse
from .config_manager import ConfigManager, set_debug_mode as set_cm_debug_mode
from .constants import (
    BLACK, WHITE, CYAN, YELLOW, MAGENTA, GREEN, RED, BLUE, ORANGE, GREY, GARBAGE_COLOR,
    PIECE_COLORS, SHAPES,
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
    GRID_WIDTH, GRID_HEIGHT, BLOCK_SIZE, NEXT_PIECE_BLOCK_SIZE,
    GRID_OFFSET_X, GRID_OFFSET_Y,
    UI_INFO_X_OFFSET, UI_INFO_START_Y, UI_INFO_LINE_SPACING, NEXT_PIECE_BOX_SIZE,
    SCORE_FONT_SIZE, INFO_FONT_SIZE, TITLE_FONT_SIZE, GAME_OVER_FONT_SIZE,
    INITIAL_FALL_SPEED, FALL_SPEED_DECREMENT_PER_LEVEL, MIN_FALL_SPEED,
    LINES_PER_LEVEL, GARBAGE_START_LEVEL, MAX_GARBAGE_ROWS,
    AI_PLAYER_TOGGLE_KEY, RESTART_KEY, PAUSE_KEY, AI_MOVE_DELAY, LINE_ANIMATION_DURATION,
    PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT, PROGRESS_BAR_BACKGROUND_COLOR,
    PROGRESS_BAR_FILL_COLOR, PROGRESS_BAR_BORDER_COLOR
)
from .piece import Piece # Import Piece from its new location
from . import ai_player # Import the new AI player module

# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()
pygame.joystick.init()

DEBUG_MODE = False

# SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT are initialized in main()
SCORE_FONT = None; INFO_FONT = None; TITLE_FONT = None; GAME_OVER_FONT = None

SOUND_EFFECTS = {"move": None, "rotate": None, "drop": None, "line_clear": None, "tetris_clear": None, "level_up": None, "game_over": None}
SOUND_DIR = "sounds" # Specific to asset loading in tetris.py
sound_effects_enabled = True # Renamed from sound_enabled
shadow_enabled = True
line_blink_enabled = True
music_enabled = True         # Added

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path): print(f"Sound file not found: {path}"); return None
    try: sound = pygame.mixer.Sound(path); sound.set_volume(0.3); return sound
    except pygame.error as e: print(f"Error loading sound {filename}: {e}"); return None

def play_sound(sound_name):
    global sound_effects_enabled # Use new global name
    if not sound_effects_enabled:
        return
    if SOUND_EFFECTS.get(sound_name): SOUND_EFFECTS[sound_name].play()

# ... (create_grid, draw_grid_lines, draw_blocks, draw_piece - largely same)
def create_grid(fill_value=0): return [[fill_value for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
def draw_grid_lines(screen):
    for row in range(GRID_HEIGHT + 1): pygame.draw.line(screen, GREY, (GRID_OFFSET_X, GRID_OFFSET_Y + row * BLOCK_SIZE), (GRID_OFFSET_X + GRID_WIDTH * BLOCK_SIZE, GRID_OFFSET_Y + row * BLOCK_SIZE))
    for col in range(GRID_WIDTH + 1): pygame.draw.line(screen, GREY, (GRID_OFFSET_X + col * BLOCK_SIZE, GRID_OFFSET_Y), (GRID_OFFSET_X + col * BLOCK_SIZE, GRID_OFFSET_Y + GRID_HEIGHT * BLOCK_SIZE))

def draw_blocks(screen, grid_data, lines_being_animated, animation_timer, line_blink_enabled_flag): # Draws landed blocks
    for r_idx, row in enumerate(grid_data):
        for c_idx, cell_color in enumerate(row):
            if cell_color != 0:
                current_block_color = cell_color # Start with the actual color

                if r_idx in lines_being_animated:
                    if line_blink_enabled_flag: # Check the new flag
                        # --- Keep existing blinking logic ---
                        progress_frames = LINE_ANIMATION_DURATION - animation_timer
                        blink_phase_duration = LINE_ANIMATION_DURATION / 10
                        current_blink_phase = int(progress_frames / blink_phase_duration)

                        if current_blink_phase % 2 == 0:
                            current_block_color = WHITE
                        else:
                            current_block_color = cell_color

                        if animation_timer < (LINE_ANIMATION_DURATION / 5): # Final phase of blinking
                            current_block_color = BLACK
                        # --- End of existing blinking logic ---
                    else:
                        # If blinking is disabled, make blocks in clearing lines disappear immediately
                        current_block_color = BLACK

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
    return Piece(GRID_WIDTH // 2, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)

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

    temp_piece_for_check = Piece(GRID_WIDTH // 2, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
    return not is_valid_position(temp_piece_for_check, grid_data) # True if game over

# --- Time Formatting Function ---
def format_time(total_seconds):
    """Formats total seconds into MM:SS string."""
    minutes = int(total_seconds // 60) # Calculate whole minutes
    seconds = int(total_seconds % 60) # Calculate remaining seconds
    return f"{minutes:02d}:{seconds:02d}" # Format as MM:SS with leading zeros

def draw_next_piece_area(screen, piece_to_draw, x_pos, y_pos, title_str):
    global TITLE_FONT
    if TITLE_FONT is None: TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE)

    title_surface = TITLE_FONT.render(title_str, True, WHITE)
    screen.blit(title_surface, (x_pos, y_pos))

    box_y_pos = y_pos + title_surface.get_height() + 5
    pygame.draw.rect(screen, GREY, (x_pos, box_y_pos, NEXT_PIECE_BOX_SIZE, NEXT_PIECE_BOX_SIZE), 1)

    if piece_to_draw:
        shape_coords = piece_to_draw.get_shape_for_preview()

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
            pygame.draw.rect(screen, piece_to_draw.color, (block_x, block_y, NEXT_PIECE_BLOCK_SIZE -1, NEXT_PIECE_BLOCK_SIZE -1))


def draw_full_ui(screen, score, level, lines_cleared_total, next_piece_1_obj, next_piece_2_obj, lines_for_current_level, ai_mode_is_active, formatted_time_str, top_scores_list): # Updated next piece params
    global SCORE_FONT, INFO_FONT, TITLE_FONT # Ensure TITLE_FONT is global here for height calculation
    if SCORE_FONT is None: SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE)
    if INFO_FONT is None: INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    if TITLE_FONT is None: TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE) # Load if not already

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
    if top_scores_list: # Check if the list is not empty
        top_score_entry = top_scores_list[0] # Get the first entry (highest score)
        # Ensure the entry is valid before trying to access keys
        if isinstance(top_score_entry, dict) and "username" in top_score_entry and "score" in top_score_entry:
            if top_score_entry.get("score", 0) > 0: # Only display if the top score is greater than 0
                best_score_text = f"Best: {top_score_entry['username']} - {top_score_entry['score']}"
                best_score_surface = INFO_FONT.render(best_score_text, True, YELLOW)
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
    current_y = progress_bar_rect_y + PROGRESS_BAR_HEIGHT + UI_INFO_LINE_SPACING * 2

    # Draw First Next Piece
    draw_next_piece_area(screen, next_piece_1_obj, ui_start_x, current_y, "Next 1:")

    title_height_estimate = TITLE_FONT.get_height()
    current_y += title_height_estimate + 5 + NEXT_PIECE_BOX_SIZE + UI_INFO_LINE_SPACING * 2

    # Draw Second Next Piece
    draw_next_piece_area(screen, next_piece_2_obj, ui_start_x, current_y, "Next 2:")

    # current_y += title_height_estimate + 5 + NEXT_PIECE_BOX_SIZE + UI_INFO_LINE_SPACING # If more elements followed


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

# --- Input Handling Sub-functions ---

# Helper functions for _update_game_state
def _process_ai_move(gs, play_sound_func, is_valid_position_func):
    # AI Player Decision Logic
    # gs.ai_mode_active, gs.game_over, gs.current_piece, gs.last_ai_move_time,
    # gs.soft_drop_active are modified here.
    # Dependencies: ai_player.clone_grid, ai_player.find_best_move, DEBUG_MODE
    if time.time() - gs.last_ai_move_time > AI_MOVE_DELAY:
        grid_copy_for_ai = ai_player.clone_grid(gs.game_grid)
        best_move_info = ai_player.find_best_move(
            grid_copy_for_ai, gs.current_piece, gs.next_piece_1,
            is_valid_position_func=is_valid_position_func,
            play_sound_func=play_sound_func
        )

        if best_move_info and best_move_info['x'] != -1:
            gs.current_piece.rotation = best_move_info['rotation']
            gs.current_piece.x = best_move_info['x']
            gs.current_piece.target_y_for_animated_drop = best_move_info['landing_y']
            gs.current_piece.is_hard_dropping_animated = True
            gs.soft_drop_active = False
        else:
            if DEBUG_MODE: print("AI: No valid moves found by find_best_move. Setting game over.")
            gs.game_over = True
        gs.last_ai_move_time = time.time()

def _process_animated_hard_drop(gs, play_sound_func, is_valid_position_func, line_blink_enabled_flag):
    # Animated Hard Drop Logic
    # Modifies: gs.current_piece, gs.game_grid, gs.next_piece_1, gs.next_piece_2,
    # gs.last_fall_time, gs.soft_drop_active, gs.game_over
    # Returns: dict for game phase transition if line clear, else None
    # Dependencies: add_to_grid, get_full_lines, play_sound_func, Piece, is_valid_position_func,
    # LINE_ANIMATION_DURATION, GRID_WIDTH
    gs.current_piece.y += 1
    if gs.current_piece.y >= gs.current_piece.target_y_for_animated_drop:
        gs.current_piece.y = gs.current_piece.target_y_for_animated_drop
        gs.current_piece.is_hard_dropping_animated = False
        add_to_grid(gs.current_piece, gs.game_grid) # Uses global play_sound

        cleared_row_indices = get_full_lines(gs.game_grid)
        if cleared_row_indices:
            if len(cleared_row_indices) == 4: play_sound_func("tetris_clear")
            elif len(cleared_row_indices) > 0: play_sound_func("line_clear")
            gs.current_piece = None # Piece locked, wait for animation
            return {
                'game_phase_str': "LINE_ANIMATION",
                'lines_being_animated': cleared_row_indices,
                'line_animation_timer': LINE_ANIMATION_DURATION if line_blink_enabled_flag else 1
            }
        else: # No lines cleared
            gs.current_piece = gs.next_piece_1
            if gs.current_piece:
                gs.current_piece.x = GRID_WIDTH // 2
                gs.current_piece.y = 0
                gs.current_piece.is_valid_position = is_valid_position_func
                gs.current_piece.play_sound = play_sound_func

            gs.next_piece_1 = gs.next_piece_2
            if gs.next_piece_1:
                gs.next_piece_1.is_valid_position = is_valid_position_func
                gs.next_piece_1.play_sound = play_sound_func

            gs.next_piece_2 = Piece(0, 0, is_valid_position_func=is_valid_position_func, play_sound_func=play_sound_func)

            if gs.current_piece and not is_valid_position_func(gs.current_piece, gs.game_grid):
                gs.game_over = True
                gs.current_piece = None
        gs.last_fall_time = time.time()
        gs.soft_drop_active = False
    return None

def _process_piece_descent(gs, play_sound_func, is_valid_position_func, line_blink_enabled_flag):
    # Automatic Piece Descent
    # Modifies: gs.current_piece, gs.game_grid, gs.next_piece_1, gs.next_piece_2,
    # gs.last_fall_time, gs.soft_drop_active, gs.game_over
    # Returns: dict for game phase transition if line clear, else None
    # Dependencies: add_to_grid, get_full_lines, play_sound_func, Piece, is_valid_position_func,
    # LINE_ANIMATION_DURATION, GRID_WIDTH
    fall_interval = gs.current_fall_speed
    if gs.soft_drop_active: fall_interval = min(gs.current_fall_speed, 0.05)

    if time.time() - gs.last_fall_time > fall_interval:
        gs.current_piece.y += 1
        if not is_valid_position_func(gs.current_piece, gs.game_grid):
            gs.current_piece.y -= 1
            add_to_grid(gs.current_piece, gs.game_grid) # Uses global play_sound

            cleared_row_indices = get_full_lines(gs.game_grid)
            if cleared_row_indices:
                if len(cleared_row_indices) == 4: play_sound_func("tetris_clear")
                elif len(cleared_row_indices) > 0: play_sound_func("line_clear")
                gs.current_piece = None # Piece locked, wait for animation
                return {
                    'game_phase_str': "LINE_ANIMATION",
                    'lines_being_animated': cleared_row_indices,
                    'line_animation_timer': LINE_ANIMATION_DURATION if line_blink_enabled_flag else 1
                }
            else: # No lines cleared
                gs.current_piece = gs.next_piece_1
                if gs.current_piece:
                    gs.current_piece.x = GRID_WIDTH // 2
                    gs.current_piece.y = 0
                    gs.current_piece.is_valid_position = is_valid_position_func
                    gs.current_piece.play_sound = play_sound_func

                gs.next_piece_1 = gs.next_piece_2
                if gs.next_piece_1:
                    gs.next_piece_1.is_valid_position = is_valid_position_func
                    gs.next_piece_1.play_sound = play_sound_func

                gs.next_piece_2 = Piece(0, 0, is_valid_position_func=is_valid_position_func, play_sound_func=play_sound_func)

                if gs.current_piece and not is_valid_position_func(gs.current_piece, gs.game_grid):
                    gs.game_over = True
                    gs.current_piece = None
            gs.last_fall_time = time.time()
            gs.soft_drop_active = False
        else: # Piece still falling
            gs.last_fall_time = time.time()
    return None

def _process_line_animation(gs, play_sound_func, is_valid_position_func, line_animation_timer_val, lines_being_animated_list, line_blink_enabled_flag):
    # Line Animation Phase
    # Modifies: gs (grid, score, level, etc.), gs.current_piece, gs.next_piece_1, gs.next_piece_2, gs.game_over
    # Returns: updated line_animation_timer_val, lines_being_animated_list, new_game_phase_str
    # Dependencies: _finalize_line_clear, calculate_fall_speed, add_garbage_blocks, is_valid_position_func, Piece

    line_animation_timer_val -= 1
    new_game_phase_str = "LINE_ANIMATION" # Default to staying in this phase

    if line_animation_timer_val <= 0:
        finalize_result = _finalize_line_clear(
            gs.game_grid, lines_being_animated_list,
            gs.score, gs.current_level, gs.total_lines_cleared, gs.lines_for_current_level
        )
        gs.game_grid = finalize_result["grid_data"]
        gs.score = finalize_result["current_score"]
        gs.current_level = finalize_result["level"]
        gs.total_lines_cleared = finalize_result["total_lines"]
        gs.lines_for_current_level = finalize_result["lines_for_lvl"]

        if finalize_result["leveled_up"]:
            gs.current_fall_speed = calculate_fall_speed(gs.current_level)
            if add_garbage_blocks(gs.game_grid, gs.current_level): # add_garbage_blocks uses global Piece
                gs.game_over = True
                gs.current_piece = None

        if not gs.game_over:
            gs.current_piece = gs.next_piece_1
            if gs.current_piece:
                gs.current_piece.x = GRID_WIDTH // 2
                gs.current_piece.y = 0
                gs.current_piece.is_valid_position = is_valid_position_func
                gs.current_piece.play_sound = play_sound_func

            gs.next_piece_1 = gs.next_piece_2
            if gs.next_piece_1:
                gs.next_piece_1.is_valid_position = is_valid_position_func
                gs.next_piece_1.play_sound = play_sound_func

            gs.next_piece_2 = Piece(0, 0, is_valid_position_func=is_valid_position_func, play_sound_func=play_sound_func)

            if gs.current_piece and not is_valid_position_func(gs.current_piece, gs.game_grid):
                gs.game_over = True
                gs.current_piece = None

        lines_being_animated_list = []
        new_game_phase_str = "PLAYING"
        gs.last_fall_time = time.time()

    return line_animation_timer_val, lines_being_animated_list, new_game_phase_str


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
            temp_piece_for_calc = Piece(current_piece.x, original_y, shape_type=current_piece.shape_type, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
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
    current_piece = spawn_piece_at_start() # Already passes functions
    next_piece_1 = Piece(0, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
    next_piece_2 = Piece(0, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)

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
        "game_grid": game_grid, "current_piece": current_piece,
        "next_piece_1": next_piece_1, "next_piece_2": next_piece_2,
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
    next_piece_1 = game_state_dict["next_piece_1"]
    next_piece_2 = game_state_dict["next_piece_2"]
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

    return (game_grid, current_piece, next_piece_1, next_piece_2, score, current_level,
            total_lines_cleared, lines_for_current_level, game_over,
            current_fall_speed, last_fall_time, soft_drop_active,
            game_over_sound_played, ai_mode_active, last_ai_move_time,
            game_start_time, final_game_time_str, game_paused,
            time_at_pause, total_paused_duration)

# load_config and save_config are now handled by ConfigManager

def _update_and_save_top_scores(new_score_entry):
    filename = "best_score.json"

    # 1. Load existing scores
    current_top_scores = []
    try:
        with open(filename, 'r') as f:
            loaded_data = json.load(f)
            if isinstance(loaded_data, list):
                # Basic validation for entries when loading for update
                for entry in loaded_data:
                    if isinstance(entry, dict) and \
                       "username" in entry and isinstance(entry["username"], str) and \
                       "score" in entry and isinstance(entry["score"], int) and \
                       "time_str" in entry and isinstance(entry["time_str"], str):
                        current_top_scores.append(entry)
                    # Silently skip invalid entries when loading for update, or log if DEBUG_MODE
                    elif DEBUG_MODE:
                        print(f"Skipping invalid entry during load for update: {entry}")
    except FileNotFoundError:
        # It's okay if the file doesn't exist, means current_top_scores is empty.
        if DEBUG_MODE: print(f"Info: {filename} not found while trying to update scores. Starting fresh list.")
        pass # current_top_scores remains []
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filename} during update. Score list might be reset/corrupted if saved now.")
        # Decide if we should proceed with an empty list or abort. For now, proceed with empty.
        current_top_scores = []
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: Unexpected error loading {filename} for update: {e}. Proceeding with empty list.")
        current_top_scores = []

    # 2. Add the new score entry
    current_top_scores.append(new_score_entry)

    # 3. Sort the list by score (descending)
    #    Use .get("score", 0) for robustness in sorting, though entries added should be valid.
    current_top_scores.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 4. Truncate the list to the top 10 scores
    updated_top_10_scores = current_top_scores[:10]

    # 5. Write the updated list back to best_score.json
    try:
        with open(filename, 'w') as f:
            json.dump(updated_top_10_scores, f, indent=4)
        if DEBUG_MODE: print(f"Top scores saved to {filename}: {updated_top_10_scores}")
    except IOError as e:
        if DEBUG_MODE: print(f"Error saving top scores to {filename}: {e}")
    except Exception as e:
        if DEBUG_MODE: print(f"An unexpected error occurred while saving top scores to {filename}: {e}")

def _load_best_score():
    filename = "best_score.json"
    # Default return is now an empty list if file is problematic
    default_scores_list = []

    try:
        with open(filename, 'r') as f:
            data = json.load(f)

            # Validate that data is a list
            if not isinstance(data, list):
                if DEBUG_MODE: print(f"Warning: {filename} content is not a list. Returning empty list.")
                return default_scores_list

            valid_scores = []
            for entry in data:
                # Validate each entry in the list
                if isinstance(entry, dict) and \
                   "username" in entry and isinstance(entry["username"], str) and \
                   "score" in entry and isinstance(entry["score"], int) and \
                   "time_str" in entry and isinstance(entry["time_str"], str):
                    valid_scores.append(entry)
                else:
                    if DEBUG_MODE: print(f"Warning: Invalid score entry found in {filename}: {entry}. Skipping.")

            # Sort by score descending and truncate to top 10
            valid_scores.sort(key=lambda x: x.get("score", 0), reverse=True)
            top_10_scores = valid_scores[:10]

            if DEBUG_MODE: print(f"Top scores loaded from {filename}: {top_10_scores}")
            return top_10_scores

    except FileNotFoundError:
        if DEBUG_MODE: print(f"Info: {filename} not found. Returning empty list.")
        return default_scores_list # Return copy if mutable, but [] is fine
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filename}. File might be corrupted. Returning empty list.")
        return default_scores_list
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: An unexpected error occurred loading {filename}: {e}. Returning empty list.")
        return default_scores_list

def _handle_events(events, game_over_flag, game_paused_flag, ai_mode_flag, soft_drop_flag, current_piece_obj, game_grid_data, running_flag, time_at_pause_val, total_paused_duration_val, last_fall_time_val, last_ai_move_time_val, joystick_obj, joystick_enabled_flag, help_screen_active_flag, game_phase_str, current_username_str, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag):
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
                if event.key == pygame.K_s: # Sound Effects Toggle
                    sound_effects_enabled_flag = not sound_effects_enabled_flag
                    config_manager.set("sound_effects_enabled", sound_effects_enabled_flag)
                    if DEBUG_MODE: print(f"Sound Effects setting toggled. New state: {sound_effects_enabled_flag}. Config saved via ConfigManager.")
                elif event.key == pygame.K_m: # Music Toggle
                    music_enabled_flag = not music_enabled_flag
                    config_manager.set("music_enabled", music_enabled_flag)
                    if DEBUG_MODE: print(f"Music setting toggled. New state: {music_enabled_flag}. Config saved via ConfigManager.")
                elif event.key == pygame.K_d: # Shadow Toggle
                    shadow_enabled_flag = not shadow_enabled_flag
                    config_manager.set("shadow_enabled", shadow_enabled_flag)
                    if DEBUG_MODE: print(f"Shadow setting toggled. New state: {shadow_enabled_flag}. Config saved via ConfigManager.")
                elif event.key == pygame.K_b: # Line Blink Toggle
                    line_blink_enabled_flag = not line_blink_enabled_flag
                    config_manager.set("line_blink_enabled", line_blink_enabled_flag)
                    if DEBUG_MODE: print(f"Line Blink setting toggled. New state: {line_blink_enabled_flag}. Config saved via ConfigManager.")
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
        if game_phase_str == "HIGH_SCORE_DISPLAY":
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running_flag = False # Signal to quit the game
                    if DEBUG_MODE: print("DEBUG _handle_events: ESCAPE pressed on High Score screen. Setting running_flag=False.")
                else:
                    # Any other key press triggers a restart
                    action_request = "RESTART"
                    if DEBUG_MODE: print(f"DEBUG _handle_events: Key {event.key} pressed on High Score screen. Requesting RESTART.")

            if event.type == pygame.QUIT: # Still handle window close
                 running_flag = False
            continue # Consume the event, stop further processing

        elif game_phase_str == "GETTING_USERNAME":
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
        "sound_effects_enabled": sound_effects_enabled_flag, # Renamed key
        "shadow_enabled": shadow_enabled_flag,
        "line_blink_enabled": line_blink_enabled_flag,
        "music_enabled": music_enabled_flag, # Added key
        "current_username_input": current_username_str,
        "game_phase_str": game_phase_str
    }

def _update_game_state(game_over_flag, game_paused_flag, ai_mode_flag, current_piece_obj, next_piece_1_obj, next_piece_2_obj, game_grid_data, score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val, current_fall_speed_val, last_fall_time_val, soft_drop_flag, game_over_sound_played_flag, last_ai_move_time_val, game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val, help_screen_active_flag, game_phase_str, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag): # Added line_blink_enabled_flag, next_piece_1_obj, next_piece_2_obj
    # Create a GameState object to pass around
    gs = type('GameState', (), {})() # Simple namespace object for now
    gs.game_over = game_over_flag
    gs.ai_mode_active = ai_mode_flag # This was 'ai_mode_flag' in old signature
    gs.current_piece = current_piece_obj
    gs.next_piece_1 = next_piece_1_obj
    gs.next_piece_2 = next_piece_2_obj
    gs.game_grid = game_grid_data
    gs.score = score_val
    gs.current_level = current_level_val
    gs.total_lines_cleared = total_lines_cleared_val
    gs.lines_for_current_level = lines_for_current_level_val
    gs.current_fall_speed = current_fall_speed_val
    gs.last_fall_time = last_fall_time_val
    gs.soft_drop_active = soft_drop_flag
    gs.game_over_sound_played = game_over_sound_played_flag
    gs.last_ai_move_time = last_ai_move_time_val
    # game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val are mostly for time display
    gs.game_paused = game_paused_flag # Added from original signature

    # Local vars for phase transitions, to be returned
    current_game_phase = game_phase_str
    current_lines_being_animated = lines_being_animated_list
    current_line_animation_timer = line_animation_timer_val

    if current_game_phase == "LINE_ANIMATION":
        current_line_animation_timer, current_lines_being_animated, current_game_phase = \
            _process_line_animation(gs, play_sound, is_valid_position, current_line_animation_timer, current_lines_being_animated, line_blink_enabled_flag)

    elif current_game_phase == "PLAYING" and not gs.game_paused:
        if gs.ai_mode_active and gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
            _process_ai_move(gs, play_sound, is_valid_position)
            # AI move might set piece to hard drop or cause game over

        # IMPORTANT: Check gs.current_piece again as AI might have made it None (e.g. game over)
        # or if it completed a hard drop in a theoretical synchronous way (not current design but good check)
        if gs.current_piece and gs.current_piece.is_hard_dropping_animated:
            if not gs.game_over: # Don't process if AI already detected game over
                hard_drop_result = _process_animated_hard_drop(gs, play_sound, is_valid_position, line_blink_enabled_flag)
                if hard_drop_result:
                    current_game_phase = hard_drop_result['game_phase_str']
                    current_lines_being_animated = hard_drop_result['lines_being_animated']
                    current_line_animation_timer = hard_drop_result['line_animation_timer']

        # IMPORTANT: Check gs.current_piece again as hard drop might have cleared lines and set it to None
        elif gs.current_piece and not gs.current_piece.is_hard_dropping_animated: # Note: added elif
             if not gs.game_over: # Don't process if AI/Hard drop already detected game over
                descent_result = _process_piece_descent(gs, play_sound, is_valid_position, line_blink_enabled_flag)
                if descent_result:
                    current_game_phase = descent_result['game_phase_str']
                    current_lines_being_animated = descent_result['lines_being_animated']
                    current_line_animation_timer = descent_result['line_animation_timer']

    # --- Game Over State Update (after all game logic for the frame) ---
    if gs.game_over and not gs.game_over_sound_played:
        play_sound("game_over")
        gs.game_over_sound_played = True
        gs.current_piece = None # Ensure no piece is active
        if final_game_time_str_val is None: # final_game_time_str_val is from original signature
            current_elapsed_time = time.time() - game_start_time_val - total_paused_duration_val
            final_game_time_str_val = format_time(max(0, current_elapsed_time)) # This should be gs.final_game_time_str

    # Determine the time string to display
    calculated_formatted_time_str = ""
    if gs.game_over and final_game_time_str_val: # final_game_time_str_val from original signature
        calculated_formatted_time_str = final_game_time_str_val
    elif gs.game_paused:
        # time_at_pause_val and game_start_time_val are from original signature
        elapsed_at_pause_moment = (time_at_pause_val - game_start_time_val) - total_paused_duration_val
        calculated_formatted_time_str = format_time(max(0, elapsed_at_pause_moment))
    else:
        current_elapsed_seconds = (time.time() - game_start_time_val) - total_paused_duration_val
        calculated_formatted_time_str = format_time(max(0, current_elapsed_seconds))

    # Return values based on the updated gs and local phase vars
    return {
        "game_over": gs.game_over,
        "current_piece": gs.current_piece,
        "next_piece_1": gs.next_piece_1,
        "next_piece_2": gs.next_piece_2,
        "game_grid": gs.game_grid,
        "score": gs.score,
        "current_level": gs.current_level,
        "total_lines_cleared": gs.total_lines_cleared,
        "lines_for_current_level": gs.lines_for_current_level,
        "current_fall_speed": gs.current_fall_speed,
        "last_fall_time": gs.last_fall_time,
        "soft_drop_active": gs.soft_drop_active,
        "game_over_sound_played": gs.game_over_sound_played,
        "last_ai_move_time": gs.last_ai_move_time,
        "final_game_time_str": final_game_time_str_val, # from original signature, should be gs.final_game_time_str
        "formatted_time": calculated_formatted_time_str,
        "game_phase_str": current_game_phase,
        "lines_being_animated": current_lines_being_animated,
        "line_animation_timer": current_line_animation_timer,
        # For any other gs attributes that might have been in the original return dict implicitly
        "ai_mode_active": gs.ai_mode_active, # ensure all relevant gs fields are part of the effective return
        "game_paused": gs.game_paused,
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

def _draw_high_score_screen(screen_surface, top_scores_list, fonts):
    # """
    # Draws the high score screen.
    # Args:
    #     screen_surface: Pygame screen surface.
    #     top_scores_list (list): List of top score dictionaries.
    #     fonts (dict): Dictionary containing Pygame font objects (e.g., fonts["title"], fonts["score"], fonts["info"]).
    # """
    screen_surface.fill(BLACK) # This is the added line

    title_font = fonts.get("title", pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE))
    score_font = fonts.get("score", pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE))
    info_font = fonts.get("info", pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE))

    # Title
    title_surf = title_font.render("Top 10 Scores", True, WHITE)
    title_rect = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200))
    screen_surface.blit(title_surf, title_rect)

    start_y_scores = title_rect.bottom + 40
    line_height = score_font.get_height() + 10

    if not top_scores_list:
        no_scores_surf = info_font.render("No high scores yet!", True, WHITE)
        no_scores_rect = no_scores_surf.get_rect(center=(SCREEN_WIDTH // 2, start_y_scores + line_height * 2))
        screen_surface.blit(no_scores_surf, no_scores_rect)
    else:
        rank_x = SCREEN_WIDTH // 2 - 250
        name_x = SCREEN_WIDTH // 2 - 150
        score_val_x = SCREEN_WIDTH // 2 + 100
        # time_str_x = SCREEN_WIDTH // 2 + 250 # Time column commented out for now

        header_rank_surf = score_font.render("Rank", True, YELLOW)
        header_name_surf = score_font.render("Name", True, YELLOW)
        header_score_surf = score_font.render("Score", True, YELLOW)

        screen_surface.blit(header_rank_surf, (rank_x, start_y_scores))
        screen_surface.blit(header_name_surf, (name_x, start_y_scores))
        # For score header, position its right edge at score_val_x + some padding for values, or center it above values
        screen_surface.blit(header_score_surf, (score_val_x + 50 - header_score_surf.get_width(), start_y_scores))


        current_y = start_y_scores + line_height

        for i, entry in enumerate(top_scores_list):
            if i >= 10:
                break

            rank_str = f"{i + 1}."
            username_str = entry.get("username", "N/A")[:15] # Truncate username if too long
            score_str = str(entry.get("score", 0))

            rank_surf = score_font.render(rank_str, True, WHITE)
            name_surf = score_font.render(username_str, True, WHITE)
            score_val_surf = score_font.render(score_str, True, WHITE)

            screen_surface.blit(rank_surf, (rank_x, current_y))
            screen_surface.blit(name_surf, (name_x, current_y))
            # Align score value to the right
            screen_surface.blit(score_val_surf, (score_val_x + 50 - score_val_surf.get_width(), current_y))

            current_y += line_height

    instruction_y = SCREEN_HEIGHT - 100
    instruction_surf = info_font.render("Press any key to Restart, ESC to Quit", True, WHITE)
    instruction_rect = instruction_surf.get_rect(center=(SCREEN_WIDTH // 2, instruction_y))
    screen_surface.blit(instruction_surf, instruction_rect)

def _draw_game_screen(screen_surface, game_grid_data, current_piece_obj, next_piece_1_obj, next_piece_2_obj, score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val, ai_mode_flag, formatted_time_str, game_over_flag, game_paused_flag, clock_obj, help_screen_active_flag, help_text_surfaces_list, game_phase_str, current_username_str, top_scores_list, lines_being_animated_list, line_animation_timer_val, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag): # Signature updated
    # Drawing
    screen_surface.fill(BLACK) # Always fill screen first
    # Regular game drawing (grid, current piece, main UI)
    draw_grid_lines(screen_surface)
    # Pass line_blink_enabled_flag to draw_blocks
    draw_blocks(screen_surface, game_grid_data, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag)

    # Draw shadow piece before the actual piece
    if shadow_enabled_flag:
        # Only attempt to calculate and draw shadow if piece exists and game is in correct state
        if not game_over_flag and current_piece_obj and game_phase_str == "PLAYING":
            # current_piece_obj is confirmed to be not None here.
            shadow_y = get_shadow_position_y(current_piece_obj, game_grid_data)
            shadow_color = GREY

            # Now, proceed to get its shape and draw, as current_piece_obj is valid.
            # The check for .shape and .rotation is for data integrity of a valid piece.
            if current_piece_obj.shape and current_piece_obj.rotation < len(current_piece_obj.shape):
                for r_offset, c_offset in current_piece_obj.shape[current_piece_obj.rotation]:
                    block_r = shadow_y + r_offset
                    block_c = current_piece_obj.x + c_offset
                    if 0 <= block_r < GRID_HEIGHT and 0 <= block_c < GRID_WIDTH:
                        pygame.draw.rect(screen_surface, shadow_color, (
                            GRID_OFFSET_X + block_c * BLOCK_SIZE,
                            GRID_OFFSET_Y + block_r * BLOCK_SIZE,
                            BLOCK_SIZE - 1, BLOCK_SIZE - 1))
            # Optional: else block for debugging if a non-None piece has bad shape/rotation data
            # else:
            #    if DEBUG_MODE: print(f"DEBUG: Shadow draw for valid piece {current_piece_obj} skipped due to invalid shape/rotation.")

    if not game_over_flag and current_piece_obj and game_phase_str != "GETTING_USERNAME" and game_phase_str != "LINE_ANIMATION": # Don't draw falling piece during name input or line animation
         draw_current_piece_on_grid(screen_surface, current_piece_obj)

    # Pass next_piece_1_obj and next_piece_2_obj to draw_full_ui
    # Note: _draw_game_screen receives next_piece_obj which is actually next_piece_1_obj from main loop.
    # This will be fully harmonized when _draw_game_screen signature is updated, for now, we use what it receives as next_piece_1.
    # A placeholder or None might be needed for next_piece_2_obj if _draw_game_screen doesn't have it yet.
    # However, the previous step *should* have updated _draw_game_screen's signature.
    # Assuming _draw_game_screen has next_piece_1_obj and next_piece_2_obj parameters from main:
    draw_full_ui(screen_surface, score_val, current_level_val, total_lines_cleared_val,
                   next_piece_1_obj if not game_over_flag else None,
                   next_piece_2_obj if not game_over_flag else None,
                   lines_for_current_level_val, ai_mode_flag, formatted_time_str, top_scores_list) # Pass top_scores_list

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
        title_rect = title_text_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 140)) # Adjusted Y
        screen_surface.blit(title_text_surf, title_rect)

        # Sound FX Option Text
        sound_fx_status_str = "ON" if sound_effects_enabled_flag else "OFF"
        sound_fx_option_text_str = f"Sound FX: {sound_fx_status_str} (Press S to toggle)"
        sound_fx_option_surf = INFO_FONT.render(sound_fx_option_text_str, True, WHITE)
        sound_fx_option_rect = sound_fx_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80)) # Adjusted Y
        screen_surface.blit(sound_fx_option_surf, sound_fx_option_rect)

        # Music Option Text (New)
        music_status_str = "ON" if music_enabled_flag else "OFF"
        music_option_text_str = f"Music: {music_status_str} (Press M to toggle)"
        music_option_surf = INFO_FONT.render(music_option_text_str, True, WHITE)
        music_option_rect = music_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40)) # Adjusted Y
        screen_surface.blit(music_option_surf, music_option_rect)

        # Shadow Option Text
        shadow_status_str = "ON" if shadow_enabled_flag else "OFF"
        shadow_option_text_str = f"Shadow: {shadow_status_str} (Press D to toggle)"
        shadow_option_surf = INFO_FONT.render(shadow_option_text_str, True, WHITE)
        shadow_option_rect = shadow_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 0)) # Adjusted Y
        screen_surface.blit(shadow_option_surf, shadow_option_rect)

        # Line Blink Option Text
        line_blink_status_str = "ON" if line_blink_enabled_flag else "OFF"
        line_blink_option_text_str = f"Line Blink: {line_blink_status_str} (Press B to toggle)"
        line_blink_option_surf = INFO_FONT.render(line_blink_option_text_str, True, WHITE)
        line_blink_option_rect = line_blink_option_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 40)) # Adjusted Y
        screen_surface.blit(line_blink_option_surf, line_blink_option_rect)

        # Close Menu Hint
        close_hint_surf = INFO_FONT.render("Press C or ESC to close", True, GREY)
        close_hint_rect = close_hint_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 100)) # Adjusted Y
        screen_surface.blit(close_hint_surf, close_hint_rect)
    elif game_phase_str == "HIGH_SCORE_DISPLAY":
        fonts_for_scores = {
            "title": GAME_OVER_FONT,
            "score": INFO_FONT,
            "info": INFO_FONT
        }
        _draw_high_score_screen(screen_surface, top_scores_list, fonts_for_scores)


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

    # Set debug mode for ConfigManager as well
    set_cm_debug_mode(DEBUG_MODE)

    # Instantiate ConfigManager
    # Assumes config.json is in the same directory as tetris.py (tetris_android/)
    config_manager = ConfigManager(config_file_path="config.json")

    # --- End Argument Parsing ---
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS
    global sound_effects_enabled # Renamed
    global shadow_enabled
    global line_blink_enabled
    global music_enabled         # Added

    # Load configuration using ConfigManager
    loaded_config = config_manager.get_all()

    # Initialize module globals from the fully populated loaded_config
    sound_effects_enabled = loaded_config.get("sound_effects_enabled", True) # Default True if somehow missing
    shadow_enabled = loaded_config.get("shadow_enabled", True)             # Default True
    line_blink_enabled = loaded_config.get("line_blink_enabled", True)       # Default True
    music_enabled = loaded_config.get("music_enabled", True)               # Default True

    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE); INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)
    # Pre-render help text surfaces (using appropriate fonts)
    help_text_surfaces = _render_help_text_surfaces(GAME_OVER_FONT, SCORE_FONT, INFO_FONT, WHITE)
    top_scores_list = _load_best_score() # Renamed variable

    # --- Background Music Loading ---
    background_music_file = "background_01.mp3"
    background_music_loaded = False
    if os.path.isdir(SOUND_DIR): # Only attempt to load if sound directory exists
        try:
            music_path = os.path.join(SOUND_DIR, background_music_file)
            if not os.path.exists(music_path):
                if DEBUG_MODE: print(f"DEBUG: Background music file not found at {music_path}")
                # background_music_loaded remains False
            else:
                pygame.mixer.music.load(music_path)
                if DEBUG_MODE: print(f"DEBUG: Background music loaded from {music_path}")
                background_music_loaded = True
        except pygame.error as e:
            if DEBUG_MODE: print(f"DEBUG: Error loading background music: {e}")
            # background_music_loaded remains False
    else:
        if DEBUG_MODE: print(f"DEBUG: Sound directory '{SOUND_DIR}' not found. Skipping music and sound effects loading.")
        # sound_enabled might be set to False here if desired, or handled by individual play calls

    # --- Sound Effects Loading ---
    if not os.path.isdir(SOUND_DIR): print(f"Sound directory '{SOUND_DIR}' not found.") # This check is somewhat redundant if already done for music, but kept for clarity for SFX
    else:
        SOUND_EFFECTS["move"]=load_sound("move.wav"); SOUND_EFFECTS["rotate"]=load_sound("rotate.wav")
        SOUND_EFFECTS["drop"]=load_sound("drop.wav"); SOUND_EFFECTS["line_clear"]=load_sound("line_clear.wav")
        SOUND_EFFECTS["tetris_clear"]=load_sound("tetris_clear.wav"); SOUND_EFFECTS["level_up"]=load_sound("level_up.wav")
        SOUND_EFFECTS["game_over"]=load_sound("game_over.wav")

    # --- Initial Music Playback ---
    if background_music_loaded and music_enabled: # Changed sound_enabled to music_enabled
        pygame.mixer.music.set_volume(0.5) # Set desired volume (0.0 to 1.0)
        pygame.mixer.music.play(loops=-1) # Start playing in a loop
        if DEBUG_MODE: print("DEBUG: Background music started playing (music_enabled is True).")
    elif background_music_loaded and not music_enabled: # Changed sound_enabled to music_enabled
        pygame.mixer.music.set_volume(0.5) # Set volume anyway, so it's ready
        if DEBUG_MODE: print("DEBUG: Background music loaded, but music_enabled is initially False. Music not started.")

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
    (game_grid, current_piece, next_piece_1, next_piece_2, score, current_level,
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
            game_phase, current_username_input, config_menu_active,
            sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled, # Pass to _handle_events
            config_manager # Pass config_manager instance
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
        config_menu_active = event_handling_result["config_menu_active"]
        sound_effects_enabled = event_handling_result["sound_effects_enabled"] # Key updated
        shadow_enabled = event_handling_result["shadow_enabled"]
        line_blink_enabled = event_handling_result["line_blink_enabled"]
        music_enabled = event_handling_result["music_enabled"] # Added
        current_username_input = event_handling_result["current_username_input"]
        # game_phase is now primarily managed by main based on action_request or game_over state changes

        # --- Runtime Music Management ---
        if background_music_loaded: # Only manage music if it was loaded successfully
            if music_enabled: # Use the dedicated music_enabled global
                if not pygame.mixer.music.get_busy(): # If not currently playing
                    pygame.mixer.music.unpause() # Try to unpause first
                    if not pygame.mixer.music.get_busy(): # If still not playing
                        pygame.mixer.music.play(loops=-1) # Play from beginning
                    if DEBUG_MODE: print("DEBUG: music_enabled is True. Ensured music is playing/unpaused.")
            else: # music_enabled is False
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause() # Pause the music
                    if DEBUG_MODE: print("DEBUG: music_enabled is False. Music paused.")

        if not running:
            break

        if action_request == "RESTART":
            game_state_dict = _handle_restart_action()
            (game_grid, current_piece, next_piece_1, next_piece_2, score, current_level,
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
            new_entry = {
                "username": current_username_input,
                "score": score,
                "time_str": final_game_time_str if final_game_time_str else formatted_time
            }
            _update_and_save_top_scores(new_entry)
            top_scores_list = _load_best_score() # Reload to get the updated list for display
            game_phase = "HIGH_SCORE_DISPLAY" # NEW BEHAVIOR
            current_username_input = ""
            if DEBUG_MODE: print(f"DEBUG MainLoop: Score saved. game_phase set to '{game_phase}'.")
        elif action_request == "SKIP_SAVE":
            game_phase = "HIGH_SCORE_DISPLAY" # NEW BEHAVIOR
            current_username_input = ""
            if DEBUG_MODE: print(f"DEBUG MainLoop: Score save skipped. game_phase set to '{game_phase}'.")

        prev_game_over = game_over

        game_logic_result = _update_game_state(
            game_over, game_paused, ai_mode_active, current_piece, next_piece_1, next_piece_2, # Updated next_piece args
            game_grid, score, current_level, total_lines_cleared,
            lines_for_current_level, current_fall_speed, last_fall_time,
            soft_drop_active, game_over_sound_played, last_ai_move_time,
            game_start_time, final_game_time_str, total_paused_duration, time_at_pause,
            help_screen_active, game_phase,
            lines_being_animated, line_animation_timer, # Existing animation params
            line_blink_enabled  # Add the new flag here
        )

        game_over = game_logic_result["game_over"]
        current_piece = game_logic_result["current_piece"]
        next_piece_1 = game_logic_result["next_piece_1"] # Unpack next_piece_1
        next_piece_2 = game_logic_result["next_piece_2"] # Unpack next_piece_2
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
        if DEBUG_MODE: print(f"DEBUG MainLoop: game_over={game_over}, prev_game_over={prev_game_over}, score={score}, current_game_phase='{game_phase}'")

        # Game Phase Transition Logic (after game logic updates game_over)
        if game_over and not prev_game_over: # Game just ended
            if DEBUG_MODE: print(f"DEBUG MainLoop: Game JUST ENDED. Checking score ({score}) against top scores.")

            is_top_score = False
            if len(top_scores_list) < 10: # List has less than 10 scores
                is_top_score = True
            # If list has 10 scores, check if current score is higher than the lowest score in the list
            elif score > 0 and score > top_scores_list[-1].get("score", 0):
                is_top_score = True
            # Existing DEBUG print for top_scores_list in _load_best_score will show its state.

            if score > 0 and is_top_score: # Ensure score is positive to prompt for name
                game_phase = "GETTING_USERNAME"
                current_username_input = ""
                if DEBUG_MODE: print(f"DEBUG MainLoop: New top 10 score! game_phase set to '{game_phase}'.")
            else:
                game_phase = "HIGH_SCORE_DISPLAY" # NEW BEHAVIOR
                if DEBUG_MODE: print(f"DEBUG MainLoop: Not a new top 10 score (Score: {score}). game_phase set to '{game_phase}'.")

        # Drawing
        _draw_game_screen(
            screen, game_grid, current_piece, next_piece_1, next_piece_2, score, current_level, # Pass next_piece_1 and next_piece_2
            total_lines_cleared, lines_for_current_level, ai_mode_active,
            formatted_time, game_over, game_paused, clock,
            help_screen_active, help_text_surfaces,
            game_phase, current_username_input, top_scores_list,
            lines_being_animated, line_animation_timer,
            config_menu_active, sound_effects_enabled, shadow_enabled, # Renamed
            line_blink_enabled, music_enabled # Added
        )

    if background_music_loaded: # Check if music was loaded
        pygame.mixer.music.stop()
        if DEBUG_MODE: print("DEBUG: Background music stopped on game exit.")

    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
