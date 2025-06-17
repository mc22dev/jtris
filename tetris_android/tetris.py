import pygame
import random
import time
import os
import copy
import json
import argparse
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
from . import config_manager # Import config_manager
from .game_state import GameState # Import GameState

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

# create_grid is a utility, can stay for now or be moved later.
def create_grid(fill_value=0): return [[fill_value for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
# All local UI drawing functions (draw_grid_lines, draw_blocks, draw_current_piece_on_grid,
# get_shadow_position_y, draw_next_piece_area, draw_full_ui, draw_level_progress_bar,
# _render_help_text_surfaces, _draw_help_screen, _draw_high_score_screen, _draw_game_screen)
# are now removed as their functionality is in ui_manager.py.

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
# --- Time Formatting Function ---
# format_time is a general utility.
def format_time(total_seconds):
    """Formats total seconds into MM:SS string."""
    minutes = int(total_seconds // 60) # Calculate whole minutes
    seconds = int(total_seconds % 60) # Calculate remaining seconds
    return f"{minutes:02d}:{seconds:02d}" # Format as MM:SS with leading zeros

# Helper functions for _update_game_state are defined above.
# Local input functions (handle_game_over_inputs, handle_player_piece_controls) are now removed.
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
            gs.game_over = True # Make sure gs.game_over is set
        gs.last_ai_move_time = time.time()

def _process_animated_hard_drop(gs, play_sound_func, is_valid_position_func, line_blink_enabled_flag):
    # Animated Hard Drop Logic
    gs.current_piece.y += 1
    if gs.current_piece.y >= gs.current_piece.target_y_for_animated_drop:
        gs.current_piece.y = gs.current_piece.target_y_for_animated_drop
        gs.current_piece.is_hard_dropping_animated = False
        add_to_grid(gs.current_piece, gs.game_grid)

        cleared_row_indices = get_full_lines(gs.game_grid)
        if cleared_row_indices:
            if len(cleared_row_indices) == 4: play_sound_func("tetris_clear")
            elif len(cleared_row_indices) > 0: play_sound_func("line_clear")
            gs.current_piece = None
            return {
                'game_phase_str': "LINE_ANIMATION",
                'lines_being_animated': cleared_row_indices,
                'line_animation_timer': LINE_ANIMATION_DURATION if line_blink_enabled_flag else 1
            }
        else:
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
    fall_interval = gs.current_fall_speed
    if gs.soft_drop_active: fall_interval = min(gs.current_fall_speed, 0.05)

    if time.time() - gs.last_fall_time > fall_interval:
        gs.current_piece.y += 1
        if not is_valid_position_func(gs.current_piece, gs.game_grid):
            gs.current_piece.y -= 1
            add_to_grid(gs.current_piece, gs.game_grid)

            cleared_row_indices = get_full_lines(gs.game_grid)
            if cleared_row_indices:
                if len(cleared_row_indices) == 4: play_sound_func("tetris_clear")
                elif len(cleared_row_indices) > 0: play_sound_func("line_clear")
                gs.current_piece = None
                return {
                    'game_phase_str': "LINE_ANIMATION",
                    'lines_being_animated': cleared_row_indices,
                    'line_animation_timer': LINE_ANIMATION_DURATION if line_blink_enabled_flag else 1
                }
            else:
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
        else:
            gs.last_fall_time = time.time()
    return None

def _process_line_animation(gs, play_sound_func, is_valid_position_func, line_animation_timer_val, lines_being_animated_list, line_blink_enabled_flag):
    # Line Animation Phase
    line_animation_timer_val -= 1
    new_game_phase_str = "LINE_ANIMATION"

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
            # add_garbage_blocks calls Piece constructor internally, needs funcs
            if add_garbage_blocks(gs.game_grid, gs.current_level):
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

# --- Game State Reset Function ---
# handle_game_over_inputs and handle_player_piece_controls are now removed.
# Their logic is handled by input_handler.process_event, called from _handle_events.
def reset_game_state() -> GameState:
    """Initializes and returns a new GameState object."""
    game_grid_data = create_grid()
    current_piece_obj = spawn_piece_at_start()
    next_piece_1_obj = Piece(0, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
    next_piece_2_obj = Piece(0, 0, is_valid_position_func=is_valid_position, play_sound_func=play_sound)

    game_over_flag = False
    if current_piece_obj and not is_valid_position(current_piece_obj, game_grid_data): # Check current_piece_obj not None
        game_over_flag = True
        current_piece_obj = None

    return GameState(
        game_grid=game_grid_data,
        current_piece=current_piece_obj,
        next_piece_1=next_piece_1_obj,
        next_piece_2=next_piece_2_obj,
        score=0,
        current_level=1,
        total_lines_cleared=0,
        lines_for_current_level=0,
        game_over=game_over_flag,
        current_fall_speed=calculate_fall_speed(1),
        last_fall_time=time.time(),
        soft_drop_active=False,
        game_over_sound_played=False,
        ai_mode_active=False,
        last_ai_move_time=time.time(),
        game_start_time=time.time(),
        final_game_time_str=None,
        game_paused=False,
        time_at_pause=0.0,
        total_paused_duration=0.0
    )

def _handle_restart_action() -> GameState: # Ensure it returns GameState
    return reset_game_state()

# _unpack_game_state is removed as GameState object 'gs' will be used directly.
# Local config functions removed, config_manager versions are used.

# This function was replaced by _update_and_save_top_scores
# def _save_best_score(username, score, time_str):
#     filename = "best_score.json"
#     data_to_save = {
#         "username": username,
#         "score": score,
#         "time_str": time_str
#     }

#     try:
#         with open(filename, 'w') as f:
#             json.dump(data_to_save, f, indent=4)
#         print(f"New best score saved to {filename}.") # Informative print
#     except Exception as e:
#         print(f"Error saving best score to {filename}: {e}")

def _handle_events(events, gs: GameState, running_flag: bool, joystick_obj, joystick_enabled_flag: bool, help_screen_active_flag: bool, game_phase_str: str, current_username_str: str, config_menu_active_flag: bool, sound_effects_enabled_flag: bool, shadow_enabled_flag: bool, line_blink_enabled_flag: bool, music_enabled_flag: bool):
    action_request = None
    # gs object's attributes are modified directly.

    for event in events:
        # Top-level quit check (handles window close)
        if event.type == pygame.QUIT:
            running_flag = False
            continue # Skip further processing for this event

        # Help Screen Toggle (H)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            help_screen_active_flag = not help_screen_active_flag
            if help_screen_active_flag:
                if not gs.game_paused:
                    gs.time_at_pause = time.time()
                gs.game_paused = True
                if DEBUG_MODE: print("Help screen NEWLY ACTIVATED. game_paused_flag set to True.")
            else:
                if not config_menu_active_flag:
                    gs.game_paused = False
                    if gs.time_at_pause > 0:
                        gs.total_paused_duration += time.time() - gs.time_at_pause
                        gs.time_at_pause = 0
                    gs.last_fall_time = time.time()
                    gs.last_ai_move_time = time.time()
                if DEBUG_MODE: print("Help screen NEWLY DEACTIVATED. game_paused_flag logic applied.")
            continue

        # Config Menu Toggle (C)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            # If config menu is currently active, and ESC is pressed, this block handles it.
            # If 'c' is pressed again, it also toggles.
            if config_menu_active_flag and event.key == pygame.K_c :
                 pass
            else:
                config_menu_active_flag = not config_menu_active_flag
                if config_menu_active_flag:
                    if not gs.game_paused:
                        gs.time_at_pause = time.time()
                    gs.game_paused = True
                    if DEBUG_MODE: print("Config menu NEWLY ACTIVATED by C. game_paused_flag set to True.")
                else:
                    if not help_screen_active_flag:
                        gs.game_paused = False
                        if gs.time_at_pause > 0:
                            gs.total_paused_duration += time.time() - gs.time_at_pause
                            gs.time_at_pause = 0
                        gs.last_fall_time = time.time()
                        gs.last_ai_move_time = time.time()
                    if DEBUG_MODE: print("Config menu NEWLY DEACTIVATED by C. game_paused_flag logic applied.")
            continue


        # Close Help with ESC (respects config menu)
        if help_screen_active_flag and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            help_screen_active_flag = False
            if not config_menu_active_flag:
                gs.game_paused = False
                if gs.time_at_pause > 0:
                    gs.total_paused_duration += time.time() - gs.time_at_pause
                    gs.time_at_pause = 0
                gs.last_fall_time = time.time()
                gs.last_ai_move_time = time.time()
            if DEBUG_MODE: print("Help screen deactivated by ESC. game_paused_flag logic applied.")
            continue

        if help_screen_active_flag: # If help is active, skip all other game inputs below this
            continue

        # Config Menu Active Handling (takes precedence over game phases if active, but after help)
        if config_menu_active_flag:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s: # Sound Effects Toggle
                    sound_effects_enabled_flag = not sound_effects_enabled_flag
                    config_manager.save_config({
                        "sound_effects_enabled": sound_effects_enabled_flag,
                        "shadow_enabled": shadow_enabled_flag,
                        "line_blink_enabled": line_blink_enabled_flag,
                        "music_enabled": music_enabled_flag
                    }, DEBUG_MODE)
                    if DEBUG_MODE: print(f"Sound Effects setting toggled. New state: {sound_effects_enabled_flag}. Config saved.")
                elif event.key == pygame.K_m: # Music Toggle
                    music_enabled_flag = not music_enabled_flag
                    config_manager.save_config({
                        "sound_effects_enabled": sound_effects_enabled_flag,
                        "shadow_enabled": shadow_enabled_flag,
                        "line_blink_enabled": line_blink_enabled_flag,
                        "music_enabled": music_enabled_flag
                    }, DEBUG_MODE)
                    if DEBUG_MODE: print(f"Music setting toggled. New state: {music_enabled_flag}. Config saved.")
                elif event.key == pygame.K_d: # Shadow Toggle
                    shadow_enabled_flag = not shadow_enabled_flag
                    config_manager.save_config({
                        "sound_effects_enabled": sound_effects_enabled_flag,
                        "shadow_enabled": shadow_enabled_flag,
                        "line_blink_enabled": line_blink_enabled_flag,
                        "music_enabled": music_enabled_flag
                    }, DEBUG_MODE)
                    if DEBUG_MODE: print(f"Shadow setting toggled. New state: {shadow_enabled_flag}. Config saved.")
                elif event.key == pygame.K_b: # Line Blink Toggle
                    line_blink_enabled_flag = not line_blink_enabled_flag
                    config_manager.save_config({
                        "sound_effects_enabled": sound_effects_enabled_flag,
                        "shadow_enabled": shadow_enabled_flag,
                        "line_blink_enabled": line_blink_enabled_flag,
                        "music_enabled": music_enabled_flag
                    }, DEBUG_MODE)
                    if DEBUG_MODE: print(f"Line Blink setting toggled. New state: {line_blink_enabled_flag}. Config saved.")
                elif event.key == pygame.K_ESCAPE or event.key == pygame.K_c:
                    config_menu_active_flag = False
                    if not help_screen_active_flag:
                        gs.game_paused = False
                        if gs.time_at_pause > 0:
                           gs.total_paused_duration += time.time() - gs.time_at_pause
                           gs.time_at_pause = 0
                        gs.last_fall_time = time.time()
                        gs.last_ai_move_time = time.time()
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
                gs.game_paused = not gs.game_paused
                if gs.game_paused:
                    gs.time_at_pause = time.time()
                    if DEBUG_MODE: print(f"Game Paused (P key). Paused: {gs.game_paused}")
                else:
                    if not help_screen_active and not config_menu_active:
                        if gs.time_at_pause > 0:
                            gs.total_paused_duration += time.time() - gs.time_at_pause
                            gs.time_at_pause = 0
                        gs.last_fall_time = time.time()
                        gs.last_ai_move_time = time.time()
                        if DEBUG_MODE: print(f"Game Resumed (P key) - All clear. Paused: {gs.game_paused}")
                    else:
                        if DEBUG_MODE: print(f"Game Unpause (P key) deferred - Help/Config active. Paused: {gs.game_paused} (still true effectively)")
                continue

            if not gs.game_paused:
                # AI Mode Toggle (A key)
                if event.type == pygame.KEYDOWN and event.key == AI_PLAYER_TOGGLE_KEY:
                    gs.ai_mode_active = not gs.ai_mode_active
                    if DEBUG_MODE: print(f"AI Mode Toggled (A key). AI: {gs.ai_mode_active}")
                    if gs.ai_mode_active:
                        gs.soft_drop_active = False
                        if gs.current_piece: gs.current_piece.is_hard_dropping_animated = False
                        gs.last_ai_move_time = time.time()
                    continue

                # Use input_handler for player controls
                # This assumes input_handler.process_event is designed to take gs and modify it
                # or return specific changes. For now, we assume it handles its part.
                # The original call to handle_player_piece_controls is removed.
                # The call to input_handler.process_event should be here if this _handle_events
                # is the main dispatcher for PLAYING phase events.
                # However, the subtask was to REMOVE handle_player_piece_controls and handle_game_over_inputs
                # and ensure calls go to input_handler.process_event.
                # This implies _handle_events itself might be simplified or input_handler.process_event
                # is called directly from the main loop for these types of events.
                # For now, I will assume that player piece controls are handled by input_handler.process_event
                # which would be called for relevant event types (KEYDOWN, KEYUP, JOY...)
                # This part of _handle_events becomes a pass-through or calls input_handler.
                # The existing structure of input_handler.process_event already handles this.
                pass


        elif game_phase_str == "GAME_OVER":
            # This was handle_game_over_inputs(event)
            # Now, input_handler.process_event should cover this when game_phase_str is "GAME_OVER"
            # So, the specific call to handle_game_over_inputs is removed.
            # The logic will be inside the more general input_handler.process_event call below.
            pass # Logic now in input_handler.process_event

        # General call to input_handler for events not handled by global toggles (H, C, P, A)
        # This will cover piece controls, game over inputs, username entry
        # We need to make sure this call is structured correctly based on input_handler.process_event's needs
        if not (event.type == pygame.KEYDOWN and event.key in [pygame.K_h, pygame.K_c, PAUSE_KEY, AI_PLAYER_TOGGLE_KEY]):
             handler_result = input_handler.process_event(event, gs, joystick_obj, joystick_enabled_flag, game_phase_str, current_username_str)
             if handler_result.get("action_request"):
                 action_request = handler_result["action_request"]
             if "running_flag_event" in handler_result and not handler_result["running_flag_event"]:
                 running_flag = False # Propagate quit signal
             current_username_str = handler_result.get("current_username_str", current_username_str)
             # gs.soft_drop_active might be modified by input_handler.process_event

        # Joystick button handling for global actions (Pause, AI)
        # (This logic for global joystick actions remains in _handle_events)
        if joystick_enabled_flag and joystick_obj and event.type == pygame.JOYBUTTONDOWN:
            button = event.button
            if button == 7: # Start Button for Pause/Resume
                if game_phase_str == "PLAYING":
                    gs.game_paused = not gs.game_paused
                    if gs.game_paused:
                        gs.time_at_pause = time.time()
                    else:
                        if not help_screen_active and not config_menu_active:
                            if gs.time_at_pause > 0:
                                gs.total_paused_duration += time.time() - gs.time_at_pause
                                gs.time_at_pause = 0
                            gs.last_fall_time = time.time()
                            gs.last_ai_move_time = time.time()
                    continue
            elif button == 6: # Select Button for AI toggle
                 if game_phase_str == "PLAYING" and not gs.game_paused:
                    gs.ai_mode_active = not gs.ai_mode_active
                    if gs.ai_mode_active:
                        gs.soft_drop_active = False
                        if gs.current_piece: gs.current_piece.is_hard_dropping_animated = False
                        gs.last_ai_move_time = time.time()
                    continue

    # Return values that are managed by main or are local to _handle_events's scope
    return {
        "running": running_flag,
        "game_paused": gs.game_paused, # Return updated state from gs
        "ai_mode_active": gs.ai_mode_active, # Return updated state from gs
        "soft_drop_active": gs.soft_drop_active, # Return updated state from gs
        "current_piece": gs.current_piece, # Return updated state from gs
        "time_at_pause": gs.time_at_pause, # Return updated state from gs
        "total_paused_duration": gs.total_paused_duration, # Return updated state from gs
        "last_fall_time": gs.last_fall_time, # Return updated state from gs
        "last_ai_move_time": gs.last_ai_move_time, # Return updated state from gs
        "game_over": gs.game_over, # Return updated state from gs
        "action_request": action_request,
        "help_screen_active": help_screen_active,
        "config_menu_active": config_menu_active,
        "sound_effects_enabled": sound_effects_enabled_flag,
        "shadow_enabled": shadow_enabled_flag,
        "line_blink_enabled": line_blink_enabled_flag,
        "music_enabled": music_enabled_flag,
        "current_username_input": current_username_str,
        "game_phase_str": game_phase_str
    }

def _update_game_state(gs: GameState, current_game_phase: str, current_lines_being_animated: list, current_line_animation_timer: int, line_blink_enabled_flag: bool):
    # Note: game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val removed from params
    # These are now expected to be part of gs if needed by time calculation, or time calc is done in main.
    # For this iteration, final time string update is kept here using gs attributes.

    if current_game_phase == "LINE_ANIMATION":
        current_line_animation_timer, current_lines_being_animated, current_game_phase = \
            _process_line_animation(gs, play_sound, is_valid_position, current_line_animation_timer, current_lines_being_animated, line_blink_enabled_flag)

    elif current_game_phase == "PLAYING" and not gs.game_paused:
        if gs.ai_mode_active and gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
            _process_ai_move(gs, play_sound, is_valid_position)

        if gs.current_piece and gs.current_piece.is_hard_dropping_animated:
            if not gs.game_over:
                hard_drop_result = _process_animated_hard_drop(gs, play_sound, is_valid_position, line_blink_enabled_flag)
                if hard_drop_result:
                    current_game_phase = hard_drop_result['game_phase_str']
                    current_lines_being_animated = hard_drop_result['lines_being_animated']
                    current_line_animation_timer = hard_drop_result['line_animation_timer']

        elif gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
             if not gs.game_over:
                descent_result = _process_piece_descent(gs, play_sound, is_valid_position, line_blink_enabled_flag)
                if descent_result:
                    current_game_phase = descent_result['game_phase_str']
                    current_lines_being_animated = descent_result['lines_being_animated']
                    current_line_animation_timer = descent_result['line_animation_timer']

    if gs.game_over and not gs.game_over_sound_played:
        play_sound("game_over")
        gs.game_over_sound_played = True
        gs.current_piece = None
        if gs.final_game_time_str is None:
            current_elapsed_time = time.time() - gs.game_start_time - gs.total_paused_duration
            gs.final_game_time_str = format_time(max(0, current_elapsed_time))

    calculated_formatted_time_str = ""
    if gs.game_over and gs.final_game_time_str:
        calculated_formatted_time_str = gs.final_game_time_str
    elif gs.game_paused:
        elapsed_at_pause_moment = (gs.time_at_pause - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = format_time(max(0, elapsed_at_pause_moment))
    else:
        current_elapsed_seconds = (time.time() - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = format_time(max(0, current_elapsed_seconds))

    return {
        "formatted_time": calculated_formatted_time_str,
        "game_phase_str": current_game_phase, # Return the (potentially updated) phase
        "lines_being_animated": current_lines_being_animated, # Return (potentially updated) list
        "line_animation_timer": current_line_animation_timer, # Return (potentially updated) timer
        # Note: The GameState 'gs' is directly modified, so changes to its attributes
        # (like gs.score, gs.game_over, etc.) are persistent in the calling scope (main loop)
        # if 'gs' in main is the same GameState object instance.
    }

def _finalize_line_clear(grid_data, lines_to_remove_indices, current_score, level, total_lines, lines_for_lvl):
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
    # --- End Argument Parsing ---
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS
    global sound_effects_enabled # Renamed
    global shadow_enabled
    global line_blink_enabled
    global music_enabled         # Added

    # Load configuration
    loaded_config = config_manager.load_config(DEBUG_MODE) # Call via config_manager

    # Initialize module globals from the fully populated loaded_config
    # Fallback to existing global values (which are module-level defaults) if a key is somehow missing,
    # though load_config is designed to always provide all keys with their defaults.
    sound_effects_enabled = loaded_config.get("sound_effects_enabled", sound_effects_enabled)
    shadow_enabled = loaded_config.get("shadow_enabled", shadow_enabled)
    line_blink_enabled = loaded_config.get("line_blink_enabled", line_blink_enabled)
    music_enabled = loaded_config.get("music_enabled", music_enabled)
    # The isinstance check for loaded_config itself is already handled robustly by load_config returning a default dict.

    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE); INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)
    # Pre-render help text surfaces (using appropriate fonts)
    help_text_surfaces = _render_help_text_surfaces(GAME_OVER_FONT, SCORE_FONT, INFO_FONT, WHITE)
    top_scores_list = config_manager._load_best_score(DEBUG_MODE) # Call via config_manager

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
    gs = reset_game_state() # Now returns a GameState object

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
        # Pass relevant parts of gs to _handle_events, or refactor _handle_events to take gs
        event_handling_result = _handle_events(
            events,
            gs.game_over, gs.game_paused, gs.ai_mode_active, gs.soft_drop_active,
            gs.current_piece, gs.game_grid,
            running,
            gs.time_at_pause, gs.total_paused_duration, gs.last_fall_time, gs.last_ai_move_time,
            joystick, joystick_enabled,
            help_screen_active, # help_screen_active is local to main
            game_phase,
            current_username_input,
            config_menu_active, # config_menu_active is local to main
            sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled
        )

        running = event_handling_result["running"]
        # Update gs attributes based on what _handle_events returns
        gs.game_paused = event_handling_result["game_paused"]
        gs.ai_mode_active = event_handling_result["ai_mode_active"]
        gs.soft_drop_active = event_handling_result["soft_drop_active"]
        gs.current_piece = event_handling_result["current_piece"]
        gs.time_at_pause = event_handling_result["time_at_pause"]
        gs.total_paused_duration = event_handling_result["total_paused_duration"]
        gs.last_fall_time = event_handling_result["last_fall_time"]
        gs.last_ai_move_time = event_handling_result["last_ai_move_time"]

        action_request = event_handling_result.get("action_request")
        help_screen_active = event_handling_result["help_screen_active"]
        config_menu_active = event_handling_result["config_menu_active"]
        sound_effects_enabled = event_handling_result.get("sound_effects_enabled", sound_effects_enabled)
        shadow_enabled = event_handling_result.get("shadow_enabled", shadow_enabled)
        line_blink_enabled = event_handling_result.get("line_blink_enabled", line_blink_enabled)
        music_enabled = event_handling_result.get("music_enabled", music_enabled)
        current_username_input = event_handling_result["current_username_input"]

        if "game_phase_str" in event_handling_result and event_handling_result["game_phase_str"] != game_phase:
            game_phase = event_handling_result["game_phase_str"]

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
            gs = _handle_restart_action() # Returns a new GameState object
            formatted_time = "00:00" # Reset display time
            help_screen_active = False
            game_phase = "PLAYING" # Reset game phase
            current_username_input = ""
            continue

        if action_request == "SAVE_SCORE":
            new_entry = {
                "username": current_username_input,
                "score": gs.score, # Use gs.score
                "time_str": gs.final_game_time_str if gs.final_game_time_str else formatted_time
            }
            config_manager._update_and_save_top_scores(new_entry, DEBUG_MODE)
            top_scores_list = config_manager._load_best_score(DEBUG_MODE)
            game_phase = "HIGH_SCORE_DISPLAY"
            current_username_input = ""
            if DEBUG_MODE: print(f"DEBUG MainLoop: Score saved. game_phase set to '{game_phase}'.")
        elif action_request == "SKIP_SAVE":
            game_phase = "HIGH_SCORE_DISPLAY"
            current_username_input = ""
            if DEBUG_MODE: print(f"DEBUG MainLoop: Score save skipped. game_phase set to '{game_phase}'.")

        prev_game_over = gs.game_over

        update_result = _update_game_state(
            gs, game_phase, lines_being_animated, line_animation_timer,
            line_blink_enabled
        )

        formatted_time = update_result["formatted_time"]
        game_phase = update_result["game_phase_str"]
        lines_being_animated = update_result["lines_being_animated"]
        line_animation_timer = update_result["line_animation_timer"]

        if DEBUG_MODE: print(f"DEBUG MainLoop: game_over={gs.game_over}, prev_game_over={prev_game_over}, score={gs.score}, current_game_phase='{game_phase}'")

        if gs.game_over and not prev_game_over:
            if DEBUG_MODE: print(f"DEBUG MainLoop: Game JUST ENDED. Checking score ({gs.score}) against top scores.")

            is_top_score = False
            if len(top_scores_list) < 10:
                is_top_score = True
            elif gs.score > 0 and gs.score > top_scores_list[-1].get("score", 0):
                is_top_score = True

            if gs.score > 0 and is_top_score:
                game_phase = "GETTING_USERNAME"
                current_username_input = ""
                if DEBUG_MODE: print(f"DEBUG MainLoop: New top 10 score! game_phase set to '{game_phase}'.")
            else:
                game_phase = "HIGH_SCORE_DISPLAY"
                if DEBUG_MODE: print(f"DEBUG MainLoop: Not a new top 10 score (Score: {gs.score}). game_phase set to '{game_phase}'.")

        # Drawing - Call ui_manager.draw_main_ui
        fonts = {"game_over": GAME_OVER_FONT, "score": SCORE_FONT, "info": INFO_FONT, "title": TITLE_FONT}
        ui_manager.draw_main_ui(
            screen, gs, fonts, clock,
            help_screen_active, help_text_surfaces,
            game_phase, current_username_input, top_scores_list,
            lines_being_animated, line_animation_timer,
            config_menu_active,
            sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled,
            formatted_time, DEBUG_MODE
        )

    if background_music_loaded:
        pygame.mixer.music.stop()
        if DEBUG_MODE: print("DEBUG: Background music stopped on game exit.")

    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
