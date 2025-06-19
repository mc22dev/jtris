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
from . import config_manager # Import the config manager
from . import input_handler # Import the new input handler module
from . import game_state # Import game_state module
from . import core_utils # Import core utilities
from . import ui_manager # Import the new UI manager module

# Initialize Pygame
pygame.init()
pygame.font.init()
pygame.mixer.init()
pygame.joystick.init()

DEBUG_MODE = False

# SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT are initialized in main()
SCORE_FONT = None; INFO_FONT = None; TITLE_FONT = None; GAME_OVER_FONT = None

# SOUND_EFFECTS, SOUND_DIR, sound_effects_enabled are now in core_utils.py
#SOUND_EFFECTS = {"move": None, "rotate": None, "drop": None, "line_clear": None, "tetris_clear": None, "level_up": None, "game_over": None}
#SOUND_DIR = "sounds"
#sound_effects_enabled = True # Now managed in core_utils

# shadow_enabled, line_blink_enabled, music_enabled will be initialized in main() from config
# and passed as parameters. Module-level defaults are removed.

# load_sound and play_sound are now in core_utils.py

# ... (create_grid is now in game_state.py)

# Drawing functions (draw_grid_lines, draw_blocks, draw_current_piece_on_grid, etc.)
# are now in ui_manager.py

# is_valid_position is now in core_utils.py
# add_to_grid is now in core_utils.py
# get_shadow_position_y is now in core_utils.py (ui_manager imports this directly)
# get_full_lines is now in core_utils.py
# get_score_for_lines is now in core_utils.py

# spawn_piece_at_start is now in game_state.py
# calculate_fall_speed is now in game_state.py
def add_garbage_blocks(grid_data, level): # Note: This function itself was not in the list to move
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

    temp_piece_for_check = Piece(GRID_WIDTH // 2, 0) # Updated Piece instantiation
    return not core_utils.is_valid_position(temp_piece_for_check, grid_data) # True if game over

# format_time is now in core_utils.py

# draw_next_piece_area is now in ui_manager.py
# draw_full_ui is now in ui_manager.py
# draw_level_progress_bar is now in ui_manager.py

# --- Input Handling Sub-functions ---

# Helper functions for _update_game_state
def _process_ai_move(gs): # Removed play_sound_func, is_valid_position_func
    # AI Player Decision Logic
    # gs.ai_mode_active, gs.game_over, gs.current_piece, gs.last_ai_move_time,
    # gs.soft_drop_active are modified here.
    # Dependencies: ai_player.clone_grid, ai_player.find_best_move, DEBUG_MODE
    if time.time() - gs.last_ai_move_time > AI_MOVE_DELAY:
        grid_copy_for_ai = ai_player.clone_grid(gs.game_grid)
        best_move_info = ai_player.find_best_move( # Call updated, no longer needs funcs
            grid_copy_for_ai, gs.current_piece, gs.next_piece_1
        )

        if best_move_info and best_move_info['x'] != -1:
            gs.current_piece.rotation = best_move_info['rotation']
            gs.current_piece.x = best_move_info['x']
            gs.current_piece.target_y_for_animated_drop = best_move_info['landing_y']
            gs.current_piece.is_hard_dropping_animated = True
            gs.soft_drop_active = False
        else:
            if DEBUG_MODE: print("AI: No valid moves found by find_best_move. Setting game over.") # DEBUG_MODE is global in tetris.py
            gs.game_over = True
        gs.last_ai_move_time = time.time()

def _process_animated_hard_drop(gs, line_blink_enabled_flag): # Removed play_sound_func, is_valid_position_func
    # Animated Hard Drop Logic
    # Modifies: gs.current_piece, gs.game_grid, gs.next_piece_1, gs.next_piece_2,
    # gs.last_fall_time, gs.soft_drop_active, gs.game_over
    # Returns: dict for game phase transition if line clear, else None
    # Dependencies: core_utils.add_to_grid, core_utils.get_full_lines, play_sound_func (passed), Piece, is_valid_position_func (passed),
    # LINE_ANIMATION_DURATION, GRID_WIDTH
    gs.current_piece.y += 1
    if gs.current_piece.y >= gs.current_piece.target_y_for_animated_drop:
        gs.current_piece.y = gs.current_piece.target_y_for_animated_drop
        gs.current_piece.is_hard_dropping_animated = False
        core_utils.add_to_grid(gs.current_piece, gs.game_grid) # Uses core_utils.play_sound internally

        cleared_row_indices = core_utils.get_full_lines(gs.game_grid)
        if cleared_row_indices:
            if len(cleared_row_indices) == 4: play_sound_func("tetris_clear") # play_sound_func is core_utils.play_sound passed in
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
                # Removed .is_valid_position and .play_sound assignments

            gs.next_piece_1 = gs.next_piece_2
            # Removed .is_valid_position and .play_sound assignments for next_piece_1

            gs.next_piece_2 = Piece(0, 0) # Updated Piece instantiation

            if gs.current_piece and not core_utils.is_valid_position(gs.current_piece, gs.game_grid): # Use core_utils
                gs.game_over = True
                gs.current_piece = None
        gs.last_fall_time = time.time()
        gs.soft_drop_active = False
    return None

def _process_piece_descent(gs, line_blink_enabled_flag): # Removed play_sound_func, is_valid_position_func
    # Automatic Piece Descent
    # Modifies: gs.current_piece, gs.game_grid, gs.next_piece_1, gs.next_piece_2,
    # gs.last_fall_time, gs.soft_drop_active, gs.game_over
    # Returns: dict for game phase transition if line clear, else None
    # Dependencies: core_utils.add_to_grid, core_utils.get_full_lines, play_sound_func (passed), Piece, is_valid_position_func (passed),
    # LINE_ANIMATION_DURATION, GRID_WIDTH
    fall_interval = gs.current_fall_speed
    if gs.soft_drop_active: fall_interval = min(gs.current_fall_speed, 0.05)

    if time.time() - gs.last_fall_time > fall_interval:
        gs.current_piece.y += 1
        if not core_utils.is_valid_position(gs.current_piece, gs.game_grid): # Use core_utils.is_valid_position
            gs.current_piece.y -= 1
            core_utils.add_to_grid(gs.current_piece, gs.game_grid)

            cleared_row_indices = core_utils.get_full_lines(gs.game_grid)
            if cleared_row_indices:
                if len(cleared_row_indices) == 4: core_utils.play_sound("tetris_clear") # Use core_utils.play_sound
                elif len(cleared_row_indices) > 0: core_utils.play_sound("line_clear")
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
                # Removed .is_valid_position and .play_sound assignments

                gs.next_piece_1 = gs.next_piece_2
            # Removed .is_valid_position and .play_sound assignments for next_piece_1

            gs.next_piece_2 = Piece(0, 0) # Updated Piece instantiation

            if gs.current_piece and not core_utils.is_valid_position(gs.current_piece, gs.game_grid): # Use core_utils
                    gs.game_over = True
                    gs.current_piece = None
            gs.last_fall_time = time.time()
            gs.soft_drop_active = False
        else: # Piece still falling
            gs.last_fall_time = time.time()
    return None

def _process_line_animation(gs, line_animation_timer_val, lines_being_animated_list, line_blink_enabled_flag): # Removed play_sound_func, is_valid_position_func
    # Line Animation Phase
    # Modifies: gs (grid, score, level, etc.), gs.current_piece, gs.next_piece_1, gs.next_piece_2, gs.game_over
    # Returns: updated line_animation_timer_val, lines_being_animated_list, new_game_phase_str
    # Dependencies: _finalize_line_clear, game_state.calculate_fall_speed, add_garbage_blocks, core_utils.is_valid_position, Piece

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
            gs.current_fall_speed = game_state.calculate_fall_speed(gs.current_level) # Updated call
            if add_garbage_blocks(gs.game_grid, gs.current_level):
                gs.game_over = True
                gs.current_piece = None

        if not gs.game_over:
            gs.current_piece = gs.next_piece_1
            if gs.current_piece:
                gs.current_piece.x = GRID_WIDTH // 2
                gs.current_piece.y = 0
                # Removed .is_valid_position and .play_sound assignments

            gs.next_piece_1 = gs.next_piece_2
            # Removed .is_valid_position and .play_sound assignments for next_piece_1

            gs.next_piece_2 = Piece(0, 0) # Updated Piece instantiation

            if gs.current_piece and not core_utils.is_valid_position(gs.current_piece, gs.game_grid): # Use core_utils
                gs.game_over = True
                gs.current_piece = None

        lines_being_animated_list = []
        new_game_phase_str = "PLAYING"
        gs.last_fall_time = time.time()

    return line_animation_timer_val, lines_being_animated_list, new_game_phase_str

# Input functions handle_game_over_inputs and handle_player_piece_controls
# are now in input_handler.py

# --- Game State Reset Function ---
def reset_game_state():
    """Initializes and returns all game state variables for a new game."""
    # This function now returns a dictionary. To align with GameState object usage,
    # this should ideally return an instance of game_state.GameState.
    # For now, keeping it as a dictionary as per existing structure in output [82]
    # The refactor to GameState object will be handled in the main() function adjustment.
    game_grid = game_state.create_grid()
    current_piece = game_state.spawn_piece_at_start()
    next_piece_1 = Piece(0, 0)
    next_piece_2 = Piece(0, 0)

    game_over = False
    if current_piece and not core_utils.is_valid_position(current_piece, game_grid):
        game_over = True
        current_piece = None

    score = 0
    current_level = 1
    total_lines_cleared = 0
    lines_for_current_level = 0

    current_fall_speed = game_state.calculate_fall_speed(current_level)
    last_fall_time = time.time()
    soft_drop_active = False
    game_over_sound_played = False

    ai_mode_active = False
    last_ai_move_time = time.time()

    game_start_time = time.time()
    final_game_time_str = None

    game_paused = False
    time_at_pause = 0.0
    total_paused_duration = 0.0

    # This dictionary structure will be used to create the GameState object in main
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
    # It should return a GameState object if main is to use it directly.
    # For now, it returns a dict, to be converted in main.
    new_game_state_dict = reset_game_state()
    return new_game_state_dict # Will be used to create a new GameState object in main

# _unpack_game_state is removed as main will use GameState object directly.

# All local drawing functions (_render_help_text_surfaces, _draw_help_screen,
# _draw_high_score_screen, _draw_game_screen) are now confirmed removed.
# Their functionality is in ui_manager.py.

# Config functions are now in config_manager.py

def _handle_events(events, gs: game_state.GameState, running_flag, time_at_pause_val, total_paused_duration_val, last_fall_time_val, last_ai_move_time_val, joystick_obj, joystick_enabled_flag, help_screen_active_flag, game_phase_str, current_username_str, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag, DEBUG_MODE_param):
    # Modified signature to accept gs: GameState object
    action_request = None
    # Local copies of mutable states for this event handling cycle
    # These should ideally come from gs and be returned to update gs if they are part of game state
    # For now, mirroring the existing logic and _handle_events will return a dict of changes.
    current_game_paused = gs.game_paused
    current_ai_mode_active = gs.ai_mode_active
    current_soft_drop_active = gs.soft_drop_active
    current_help_screen_active = help_screen_active_flag
    current_config_menu_active = config_menu_active_flag
    # Timers might be reset by global controls
    current_last_fall_time = last_fall_time_val
    current_last_ai_move_time = last_ai_move_time_val
    current_time_at_pause = time_at_pause_val
    current_total_paused_duration = total_paused_duration_val
    # running_flag and current_username_str are directly modified or returned
    # shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag are settings, not dynamic state from gs here.

    for event in events:
        processed_by_global_handler = False
        if event.type == pygame.QUIT:
            running_flag = False
            processed_by_global_handler = True
            continue

        # Help Screen Toggle (H)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            current_help_screen_active = not current_help_screen_active
            if current_help_screen_active:
                if not current_game_paused: # current_game_paused is from gs.game_paused
                    current_time_at_pause = time.time()
                current_game_paused = True # This should update gs.game_paused eventually
                if DEBUG_MODE_param: print("Help screen NEWLY ACTIVATED.")
            else:
                if not current_config_menu_active: # if config is not also active
                    current_game_paused = False # This should update gs.game_paused
                    if current_time_at_pause > 0:
                        current_total_paused_duration += time.time() - current_time_at_pause
                        current_time_at_pause = 0
                    # Reset timers that depend on pause state
                    current_last_fall_time = time.time()
                    current_last_ai_move_time = time.time()
                if DEBUG_MODE_param: print("Help screen NEWLY DEACTIVATED.")
            processed_by_global_handler = True

        # Config Menu Toggle (C)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            if not (current_config_menu_active and event.key == pygame.K_c) :
                current_config_menu_active = not current_config_menu_active
                if current_config_menu_active:
                    if not current_game_paused:
                        current_time_at_pause = time.time()
                    current_game_paused = True
                    if DEBUG_MODE_param: print("Config menu NEWLY ACTIVATED by C.")
                else:
                    if not current_help_screen_active: # if help is not also active
                        current_game_paused = False
                        if current_time_at_pause > 0:
                            current_total_paused_duration += time.time() - current_time_at_pause
                            current_time_at_pause = 0
                        current_last_fall_time = time.time()
                        current_last_ai_move_time = time.time()
                    if DEBUG_MODE_param: print("Config menu NEWLY DEACTIVATED by C.")
            processed_by_global_handler = True

        # Close Help with ESC (respects config menu)
        elif current_help_screen_active and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_help_screen_active = False
            if not current_config_menu_active: # Only unpause if config is also not open
                current_game_paused = False
                if current_time_at_pause > 0:
                    current_total_paused_duration += time.time() - current_time_at_pause
                    current_time_at_pause = 0
                current_last_fall_time = time.time()
                current_last_ai_move_time = time.time()
            if DEBUG_MODE_param: print("Help screen deactivated by ESC.")
            processed_by_global_handler = True

        if current_help_screen_active:
            continue

        if current_config_menu_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    sound_effects_enabled_flag = not sound_effects_enabled_flag # This is a local setting var
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_m:
                    music_enabled_flag = not music_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_d:
                    shadow_enabled_flag = not shadow_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_b:
                    line_blink_enabled_flag = not line_blink_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_ESCAPE or event.key == pygame.K_c:
                    current_config_menu_active = False
                    if not current_help_screen_active: # Only unpause if help is also not open
                        current_game_paused = False
                        if current_time_at_pause > 0:
                           current_total_paused_duration += time.time() - current_time_at_pause
                           current_time_at_pause = 0
                        current_last_fall_time = time.time()
                        current_last_ai_move_time = time.time()
                    if DEBUG_MODE_param: print("Config menu DEACTIVATED by ESC/C key.")
            processed_by_global_handler = True

        if processed_by_global_handler:
            continue

        # Create a temporary gs_for_input_handler, but use the main gs for context
        # input_handler.process_event might modify gs.soft_drop_active directly
        event_result = input_handler.process_event(
            event, gs, joystick_obj, joystick_enabled_flag, # Pass the main gs object
            game_phase_str, current_username_str
        )

        if event_result.get("action_request") == "QUIT_GAME": running_flag = False
        action_request = event_result.get("action_request", action_request)
        current_username_str = event_result.get("current_username_str", current_username_str)
        # gs.soft_drop_active would have been updated in-place by input_handler.process_event

        if not current_help_screen_active and not current_config_menu_active :
            if event.type == pygame.KEYDOWN and event.key == PAUSE_KEY:
                current_game_paused = not current_game_paused # This will update gs.game_paused in main loop
                if current_game_paused: current_time_at_pause = time.time()
                else:
                    if current_time_at_pause > 0: current_total_paused_duration += time.time() - current_time_at_pause; current_time_at_pause = 0
                    current_last_fall_time = time.time(); current_last_ai_move_time = time.time()

            if event.type == pygame.KEYDOWN and event.key == AI_PLAYER_TOGGLE_KEY:
                if game_phase_str == "PLAYING":
                    current_ai_mode_active = not current_ai_mode_active # This will update gs.ai_mode_active
                    if current_ai_mode_active: gs.soft_drop_active = False; current_last_ai_move_time = time.time()

            if joystick_enabled_flag and joystick_obj and event.type == pygame.JOYBUTTONDOWN:
                button = event.button
                if button == 7:
                    if game_phase_str == "PLAYING":
                        current_game_paused = not current_game_paused
                        if current_game_paused: current_time_at_pause = time.time()
                        else:
                            if current_time_at_pause > 0: current_total_paused_duration += time.time() - current_time_at_pause; current_time_at_pause = 0
                            current_last_fall_time = time.time(); current_last_ai_move_time = time.time()
                elif button == 6:
                    if game_phase_str == "PLAYING" and not current_game_paused :
                        current_ai_mode_active = not current_ai_mode_active
                        if current_ai_mode_active: gs.soft_drop_active = False; current_last_ai_move_time = time.time()

    return {
        "running": running_flag,
        "game_paused_update": current_game_paused, # Signal to update gs.game_paused
        "ai_mode_active_update": current_ai_mode_active, # Signal to update gs.ai_mode_active
        # gs.soft_drop_active is updated in place by input_handler
        "time_at_pause": current_time_at_pause,
        "total_paused_duration": current_total_paused_duration,
        "last_fall_time": current_last_fall_time,
        "last_ai_move_time": current_last_ai_move_time,
        "action_request": action_request,
        "help_screen_active": current_help_screen_active,
        "config_menu_active": current_config_menu_active,
        "sound_effects_enabled": sound_effects_enabled_flag, # This is a setting, not from gs
        "shadow_enabled": shadow_enabled_flag,       # This is a setting
        "line_blink_enabled": line_blink_enabled_flag, # This is a setting
        "music_enabled": music_enabled_flag,         # This is a setting
        "current_username_input": current_username_str,
        "game_phase_str": game_phase_str
    }

def _update_game_state(gs: game_state.GameState, game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val, help_screen_active_flag, game_phase_str, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag):
    # Modified signature to accept gs: GameState object
    # Most other parameters are now part of gs or local to the game loop (like timers, phases)
    # game_start_time_val, final_game_time_str_val etc. are related to time display, might be part of gs or passed for calc

    current_game_phase = game_phase_str
    current_lines_being_animated = lines_being_animated_list
    current_line_animation_timer = line_animation_timer_val

    if current_game_phase == "LINE_ANIMATION":
        current_line_animation_timer, current_lines_being_animated, current_game_phase = \
            _process_line_animation(gs, current_line_animation_timer, current_lines_being_animated, line_blink_enabled_flag)

    elif current_game_phase == "PLAYING" and not gs.game_paused:
        if gs.ai_mode_active and gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
            _process_ai_move(gs)

        if gs.current_piece and gs.current_piece.is_hard_dropping_animated:
            if not gs.game_over:
                hard_drop_result = _process_animated_hard_drop(gs, line_blink_enabled_flag)
                if hard_drop_result:
                    current_game_phase = hard_drop_result['game_phase_str']
                    current_lines_being_animated = hard_drop_result['lines_being_animated']
                    current_line_animation_timer = hard_drop_result['line_animation_timer']

        elif gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
             if not gs.game_over:
                descent_result = _process_piece_descent(gs, line_blink_enabled_flag)
                if descent_result:
                    current_game_phase = descent_result['game_phase_str']
                    current_lines_being_animated = descent_result['lines_being_animated']
                    current_line_animation_timer = descent_result['line_animation_timer']

    if gs.game_over and not gs.game_over_sound_played:
        core_utils.play_sound("game_over")
        gs.game_over_sound_played = True
        gs.current_piece = None
        if gs.final_game_time_str is None: # final_game_time_str_val becomes gs.final_game_time_str
            current_elapsed_time = time.time() - gs.game_start_time - gs.total_paused_duration # Use gs attributes
            gs.final_game_time_str = core_utils.format_time(max(0, current_elapsed_time))

    calculated_formatted_time_str = ""
    if gs.game_over and gs.final_game_time_str:
        calculated_formatted_time_str = gs.final_game_time_str
    elif gs.game_paused:
        # Use gs.time_at_pause, gs.game_start_time, gs.total_paused_duration
        elapsed_at_pause_moment = (gs.time_at_pause - gs.game_start_time) - gs.total_paused_duration if gs.time_at_pause > 0 else (time.time() - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = core_utils.format_time(max(0, elapsed_at_pause_moment))
    else:
        # Use gs.game_start_time, gs.total_paused_duration
        current_elapsed_seconds = (time.time() - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = core_utils.format_time(max(0, current_elapsed_seconds))

    # gs object is modified in place. Return phase and time updates.
    return {
        "formatted_time": calculated_formatted_time_str,
        "game_phase_str": current_game_phase,
        "lines_being_animated": current_lines_being_animated,
        "line_animation_timer": current_line_animation_timer,
        # gs itself is updated, so no need to return all its fields unless they are shadowed by local vars
    }

def _finalize_line_clear(grid_data, lines_to_remove_indices, current_score, level, total_lines, lines_for_lvl):
    lines_to_remove_indices.sort(reverse=True)
    # _render_help_text_surfaces is now in ui_manager.py
    # _draw_help_screen is now in ui_manager.py
    # _draw_high_score_screen is now in ui_manager.py
    # _draw_game_screen (the main drawing orchestrator) is being replaced by ui_manager.draw_main_ui call

# Config functions are now in config_manager.py

def _handle_events(events, gs: game_state.GameState, running_flag, time_at_pause_val, total_paused_duration_val, last_fall_time_val, last_ai_move_time_val, joystick_obj, joystick_enabled_flag, help_screen_active_flag, game_phase_str, current_username_str, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag, DEBUG_MODE_param):
    # Modified signature to accept gs: GameState object
    action_request = None
    # Local copies of mutable states for this event handling cycle
    # These should ideally come from gs and be returned to update gs if they are part of game state
    # For now, mirroring the existing logic and _handle_events will return a dict of changes.
    current_game_paused = gs.game_paused
    current_ai_mode_active = gs.ai_mode_active
    current_soft_drop_active = gs.soft_drop_active
    current_help_screen_active = help_screen_active_flag
    current_config_menu_active = config_menu_active_flag
    # Timers might be reset by global controls
    current_last_fall_time = last_fall_time_val
    current_last_ai_move_time = last_ai_move_time_val
    current_time_at_pause = time_at_pause_val
    current_total_paused_duration = total_paused_duration_val
    # running_flag and current_username_str are directly modified or returned
    # shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag are settings, not dynamic state from gs here.

    for event in events:
        processed_by_global_handler = False
        if event.type == pygame.QUIT:
            running_flag = False
            processed_by_global_handler = True
            continue

        # Help Screen Toggle (H)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_h:
            current_help_screen_active = not current_help_screen_active
            if current_help_screen_active:
                if not current_game_paused: # current_game_paused is from gs.game_paused
                    current_time_at_pause = time.time()
                current_game_paused = True # This should update gs.game_paused eventually
                if DEBUG_MODE_param: print("Help screen NEWLY ACTIVATED.")
            else:
                if not current_config_menu_active: # if config is not also active
                    current_game_paused = False # This should update gs.game_paused
                    if current_time_at_pause > 0:
                        current_total_paused_duration += time.time() - current_time_at_pause
                        current_time_at_pause = 0
                    # Reset timers that depend on pause state
                    current_last_fall_time = time.time()
                    current_last_ai_move_time = time.time()
                if DEBUG_MODE_param: print("Help screen NEWLY DEACTIVATED.")
            processed_by_global_handler = True

        # Config Menu Toggle (C)
        elif event.type == pygame.KEYDOWN and event.key == pygame.K_c:
            if not (current_config_menu_active and event.key == pygame.K_c) :
                current_config_menu_active = not current_config_menu_active
                if current_config_menu_active:
                    if not current_game_paused:
                        current_time_at_pause = time.time()
                    current_game_paused = True
                    if DEBUG_MODE_param: print("Config menu NEWLY ACTIVATED by C.")
                else:
                    if not current_help_screen_active: # if help is not also active
                        current_game_paused = False
                        if current_time_at_pause > 0:
                            current_total_paused_duration += time.time() - current_time_at_pause
                            current_time_at_pause = 0
                        current_last_fall_time = time.time()
                        current_last_ai_move_time = time.time()
                    if DEBUG_MODE_param: print("Config menu NEWLY DEACTIVATED by C.")
            processed_by_global_handler = True

        # Close Help with ESC (respects config menu)
        elif current_help_screen_active and event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            current_help_screen_active = False
            if not current_config_menu_active: # Only unpause if config is also not open
                current_game_paused = False
                if current_time_at_pause > 0:
                    current_total_paused_duration += time.time() - current_time_at_pause
                    current_time_at_pause = 0
                current_last_fall_time = time.time()
                current_last_ai_move_time = time.time()
            if DEBUG_MODE_param: print("Help screen deactivated by ESC.")
            processed_by_global_handler = True

        if current_help_screen_active:
            continue

        if current_config_menu_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    sound_effects_enabled_flag = not sound_effects_enabled_flag # This is a local setting var
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_m:
                    music_enabled_flag = not music_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_d:
                    shadow_enabled_flag = not shadow_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_b:
                    line_blink_enabled_flag = not line_blink_enabled_flag
                    config_manager.save_config({"sound_effects_enabled": sound_effects_enabled_flag, "shadow_enabled": shadow_enabled_flag, "line_blink_enabled": line_blink_enabled_flag, "music_enabled": music_enabled_flag}, DEBUG_MODE_param)
                elif event.key == pygame.K_ESCAPE or event.key == pygame.K_c:
                    current_config_menu_active = False
                    if not current_help_screen_active: # Only unpause if help is also not open
                        current_game_paused = False
                        if current_time_at_pause > 0:
                           current_total_paused_duration += time.time() - current_time_at_pause
                           current_time_at_pause = 0
                        current_last_fall_time = time.time()
                        current_last_ai_move_time = time.time()
                    if DEBUG_MODE_param: print("Config menu DEACTIVATED by ESC/C key.")
            processed_by_global_handler = True

        if processed_by_global_handler:
            continue

        # Create a temporary gs_for_input_handler, but use the main gs for context
        # input_handler.process_event might modify gs.soft_drop_active directly
        event_result = input_handler.process_event(
            event, gs, joystick_obj, joystick_enabled_flag, # Pass the main gs object
            game_phase_str, current_username_str
        )

        if event_result.get("action_request") == "QUIT_GAME": running_flag = False
        action_request = event_result.get("action_request", action_request)
        current_username_str = event_result.get("current_username_str", current_username_str)
        # gs.soft_drop_active would have been updated in-place by input_handler.process_event

        if not current_help_screen_active and not current_config_menu_active :
            if event.type == pygame.KEYDOWN and event.key == PAUSE_KEY:
                current_game_paused = not current_game_paused # This will update gs.game_paused in main loop
                if current_game_paused: current_time_at_pause = time.time()
                else:
                    if current_time_at_pause > 0: current_total_paused_duration += time.time() - current_time_at_pause; current_time_at_pause = 0
                    current_last_fall_time = time.time(); current_last_ai_move_time = time.time()

            if event.type == pygame.KEYDOWN and event.key == AI_PLAYER_TOGGLE_KEY:
                if game_phase_str == "PLAYING":
                    current_ai_mode_active = not current_ai_mode_active # This will update gs.ai_mode_active
                    if current_ai_mode_active: gs.soft_drop_active = False; current_last_ai_move_time = time.time()

            if joystick_enabled_flag and joystick_obj and event.type == pygame.JOYBUTTONDOWN:
                button = event.button
                if button == 7:
                    if game_phase_str == "PLAYING":
                        current_game_paused = not current_game_paused
                        if current_game_paused: current_time_at_pause = time.time()
                        else:
                            if current_time_at_pause > 0: current_total_paused_duration += time.time() - current_time_at_pause; current_time_at_pause = 0
                            current_last_fall_time = time.time(); current_last_ai_move_time = time.time()
                elif button == 6:
                    if game_phase_str == "PLAYING" and not current_game_paused :
                        current_ai_mode_active = not current_ai_mode_active
                        if current_ai_mode_active: gs.soft_drop_active = False; current_last_ai_move_time = time.time()

    return {
        "running": running_flag,
        "game_paused_update": current_game_paused, # Signal to update gs.game_paused
        "ai_mode_active_update": current_ai_mode_active, # Signal to update gs.ai_mode_active
        # gs.soft_drop_active is updated in place by input_handler
        "time_at_pause": current_time_at_pause,
        "total_paused_duration": current_total_paused_duration,
        "last_fall_time": current_last_fall_time,
        "last_ai_move_time": current_last_ai_move_time,
        "action_request": action_request,
        "help_screen_active": current_help_screen_active,
        "config_menu_active": current_config_menu_active,
        "sound_effects_enabled": sound_effects_enabled_flag, # This is a setting, not from gs
        "shadow_enabled": shadow_enabled_flag,       # This is a setting
        "line_blink_enabled": line_blink_enabled_flag, # This is a setting
        "music_enabled": music_enabled_flag,         # This is a setting
        "current_username_input": current_username_str,
        "game_phase_str": game_phase_str
    }

def _update_game_state(gs: game_state.GameState, game_start_time_val, final_game_time_str_val, total_paused_duration_val, time_at_pause_val, help_screen_active_flag, game_phase_str, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag):
    # Modified signature to accept gs: GameState object
    # Most other parameters are now part of gs or local to the game loop (like timers, phases)
    # game_start_time_val, final_game_time_str_val etc. are related to time display, might be part of gs or passed for calc

    current_game_phase = game_phase_str
    current_lines_being_animated = lines_being_animated_list
    current_line_animation_timer = line_animation_timer_val

    if current_game_phase == "LINE_ANIMATION":
        current_line_animation_timer, current_lines_being_animated, current_game_phase = \
            _process_line_animation(gs, current_line_animation_timer, current_lines_being_animated, line_blink_enabled_flag)

    elif current_game_phase == "PLAYING" and not gs.game_paused:
        if gs.ai_mode_active and gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
            _process_ai_move(gs)

        if gs.current_piece and gs.current_piece.is_hard_dropping_animated:
            if not gs.game_over:
                hard_drop_result = _process_animated_hard_drop(gs, line_blink_enabled_flag)
                if hard_drop_result:
                    current_game_phase = hard_drop_result['game_phase_str']
                    current_lines_being_animated = hard_drop_result['lines_being_animated']
                    current_line_animation_timer = hard_drop_result['line_animation_timer']

        elif gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
             if not gs.game_over:
                descent_result = _process_piece_descent(gs, line_blink_enabled_flag)
                if descent_result:
                    current_game_phase = descent_result['game_phase_str']
                    current_lines_being_animated = descent_result['lines_being_animated']
                    current_line_animation_timer = descent_result['line_animation_timer']

    if gs.game_over and not gs.game_over_sound_played:
        core_utils.play_sound("game_over")
        gs.game_over_sound_played = True
        gs.current_piece = None
        if gs.final_game_time_str is None: # final_game_time_str_val becomes gs.final_game_time_str
            current_elapsed_time = time.time() - gs.game_start_time - gs.total_paused_duration # Use gs attributes
            gs.final_game_time_str = core_utils.format_time(max(0, current_elapsed_time))

    calculated_formatted_time_str = ""
    if gs.game_over and gs.final_game_time_str:
        calculated_formatted_time_str = gs.final_game_time_str
    elif gs.game_paused:
        # Use gs.time_at_pause, gs.game_start_time, gs.total_paused_duration
        elapsed_at_pause_moment = (gs.time_at_pause - gs.game_start_time) - gs.total_paused_duration if gs.time_at_pause > 0 else (time.time() - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = core_utils.format_time(max(0, elapsed_at_pause_moment))
    else:
        # Use gs.game_start_time, gs.total_paused_duration
        current_elapsed_seconds = (time.time() - gs.game_start_time) - gs.total_paused_duration
        calculated_formatted_time_str = core_utils.format_time(max(0, current_elapsed_seconds))

    # gs object is modified in place. Return phase and time updates.
    return {
        "formatted_time": calculated_formatted_time_str,
        "game_phase_str": current_game_phase,
        "lines_being_animated": current_lines_being_animated,
        "line_animation_timer": current_line_animation_timer,
        # gs itself is updated, so no need to return all its fields unless they are shadowed by local vars
    }

def _finalize_line_clear(grid_data, lines_to_remove_indices, current_score, level, total_lines, lines_for_lvl):
    lines_to_remove_indices.sort(reverse=True)

    num_cleared = len(lines_to_remove_indices)
    for r_idx in lines_to_remove_indices:
        del grid_data[r_idx]

    for _ in range(num_cleared):
        grid_data.insert(0, [0 for _ in range(GRID_WIDTH)])

    current_score += core_utils.get_score_for_lines(num_cleared, level) # Updated call
    total_lines += num_cleared
    lines_for_lvl = total_lines % LINES_PER_LEVEL

    new_level_calc = (total_lines // LINES_PER_LEVEL) + 1
    leveled_up = False
    if new_level_calc > level:
        level = min(new_level_calc, 100) # Cap level
        core_utils.play_sound("level_up") # Updated call
        leveled_up = True

    return {
        "grid_data": grid_data,
        "current_score": current_score,
        "level": level,
        "total_lines": total_lines,
        "lines_for_lvl": lines_for_lvl,
        "leveled_up": leveled_up
    }

# All local drawing functions (_render_help_text_surfaces, _draw_help_screen,
# _draw_high_score_screen, _draw_game_screen) are now confirmed removed.
# Their functionality is in ui_manager.py.

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
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT
    # Removed sound_effects_enabled, shadow_enabled, etc. from globals here, they'll be handled locally in main or via core_utils

    # Load configuration
    loaded_config = config_manager.load_config(DEBUG_MODE)

    # Initialize settings from the loaded configuration.
    # config_manager.load_config ensures all keys are present, using defaults if not in file.
    core_utils.sound_effects_enabled = loaded_config["sound_effects_enabled"]

    # These variables are local to main and passed to _handle_events and _draw_game_screen.
    # _handle_events returns their potentially modified values.
    shadow_enabled = loaded_config["shadow_enabled"]
    line_blink_enabled = loaded_config["line_blink_enabled"]
    music_enabled = loaded_config["music_enabled"]

    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE); INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)
    # Pre-render help text surfaces (now uses fonts dict)
    # Assuming _render_help_text_surfaces is moved to ui_manager and takes fonts dict
    # For now, tetris.py still has _render_help_text_surfaces. This will be removed later.
    # If ui_manager._render_help_text_surfaces is used, it will need the fonts dict.
    # This part needs to align with where _render_help_text_surfaces lives.
    # For this step, we assume help_text_surfaces is created using the new fonts dict.
    help_text_surfaces = ui_manager._render_help_text_surfaces(fonts, WHITE)


    top_scores_list = config_manager._load_best_score(DEBUG_MODE)

    # --- Background Music Loading ---
    background_music_file = "background_01.mp3"
    background_music_loaded = False
    if os.path.isdir(core_utils.SOUND_DIR): # Only attempt to load if sound directory exists
        try:
            music_path = os.path.join(core_utils.SOUND_DIR, background_music_file)
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
    # SOUND_DIR is now in core_utils, SOUND_EFFECTS is in core_utils
    if not os.path.isdir(core_utils.SOUND_DIR): print(f"Sound directory '{core_utils.SOUND_DIR}' not found.")
    else:
        core_utils.SOUND_EFFECTS["move"]=core_utils.load_sound("move.wav")
        core_utils.SOUND_EFFECTS["rotate"]=core_utils.load_sound("rotate.wav")
        core_utils.SOUND_EFFECTS["drop"]=core_utils.load_sound("drop.wav")
        core_utils.SOUND_EFFECTS["line_clear"]=core_utils.load_sound("line_clear.wav")
        core_utils.SOUND_EFFECTS["tetris_clear"]=core_utils.load_sound("tetris_clear.wav")
        core_utils.SOUND_EFFECTS["level_up"]=core_utils.load_sound("level_up.wav")
        core_utils.SOUND_EFFECTS["game_over"]=core_utils.load_sound("game_over.wav")

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

    # --- End Argument Parsing ---
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT
    # Removed sound_effects_enabled, shadow_enabled, etc. from globals here, they'll be handled locally in main or via core_utils

    # Load configuration
    loaded_config = config_manager.load_config(DEBUG_MODE)

    # Initialize settings from the loaded configuration.
    core_utils.sound_effects_enabled = loaded_config["sound_effects_enabled"]
    shadow_enabled = loaded_config["shadow_enabled"]
    line_blink_enabled = loaded_config["line_blink_enabled"]
    music_enabled = loaded_config["music_enabled"]

    # Initialize Fonts
    SCORE_FONT = pygame.font.Font("DejaVuSans.ttf", SCORE_FONT_SIZE)
    INFO_FONT = pygame.font.Font("DejaVuSans.ttf", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.Font("DejaVuSans.ttf", TITLE_FONT_SIZE)
    GAME_OVER_FONT = pygame.font.Font("DejaVuSans.ttf", GAME_OVER_FONT_SIZE)
    fonts = {
        "score": SCORE_FONT, "info": INFO_FONT,
        "title": TITLE_FONT, "game_over": GAME_OVER_FONT
    }
    # Pre-render help text surfaces (now uses fonts dict)
    # Assuming _render_help_text_surfaces is moved to ui_manager and takes fonts dict
    # For now, tetris.py still has _render_help_text_surfaces. This will be removed later.
    # If ui_manager._render_help_text_surfaces is used, it will need the fonts dict.
    # This part needs to align with where _render_help_text_surfaces lives.
    # For this step, we assume help_text_surfaces is created using the new fonts dict.
    help_text_surfaces = ui_manager._render_help_text_surfaces(fonts, WHITE) if hasattr(ui_manager, '_render_help_text_surfaces') else _render_help_text_surfaces(GAME_OVER_FONT, SCORE_FONT, INFO_FONT, WHITE)


    top_scores_list = config_manager._load_best_score(DEBUG_MODE)

    # --- Background Music Loading ---
    background_music_file = "background_01.mp3"
    background_music_loaded = False
    if os.path.isdir(core_utils.SOUND_DIR):
        try:
            music_path = os.path.join(core_utils.SOUND_DIR, background_music_file)
            if not os.path.exists(music_path):
                if DEBUG_MODE: print(f"DEBUG: Background music file not found at {music_path}")
            else:
                pygame.mixer.music.load(music_path)
                if DEBUG_MODE: print(f"DEBUG: Background music loaded from {music_path}")
                background_music_loaded = True
        except pygame.error as e:
            if DEBUG_MODE: print(f"DEBUG: Error loading background music: {e}")
    else:
        if DEBUG_MODE: print(f"DEBUG: Sound directory '{core_utils.SOUND_DIR}' not found. Skipping music and sound effects loading.")

    # --- Sound Effects Loading ---
    if not os.path.isdir(core_utils.SOUND_DIR): print(f"Sound directory '{core_utils.SOUND_DIR}' not found.")
    else:
        core_utils.SOUND_EFFECTS["move"]=core_utils.load_sound("move.wav")
        core_utils.SOUND_EFFECTS["rotate"]=core_utils.load_sound("rotate.wav")
        core_utils.SOUND_EFFECTS["drop"]=core_utils.load_sound("drop.wav")
        core_utils.SOUND_EFFECTS["line_clear"]=core_utils.load_sound("line_clear.wav")
        core_utils.SOUND_EFFECTS["tetris_clear"]=core_utils.load_sound("tetris_clear.wav")
        core_utils.SOUND_EFFECTS["level_up"]=core_utils.load_sound("level_up.wav")
        core_utils.SOUND_EFFECTS["game_over"]=core_utils.load_sound("game_over.wav")

    if background_music_loaded and music_enabled:
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(loops=-1)
        if DEBUG_MODE: print("DEBUG: Background music started playing (music_enabled is True).")
    elif background_music_loaded and not music_enabled:
        pygame.mixer.music.set_volume(0.5)
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

    clock = pygame.time.Clock()

    # Initial game state setup using GameState object
    gs = game_state.GameState(**reset_game_state()) # Create GameState from the dict

    running = True
    help_screen_active = False
    config_menu_active = False
    game_phase = "PLAYING" # Initial game phase
    current_username_input = ""
    formatted_time = "" # Will be updated by _update_game_state
    lines_being_animated = [] # Part of game drawing state, managed locally in loop
    line_animation_timer = 0  # Part of game drawing state, managed locally in loop

    while running:
        events = pygame.event.get()
        # Pass gs object to _handle_events. Other time-related params are part of gs or managed by _handle_events' return.
        event_handling_result = _handle_events(
            events, gs, running, # Pass gs object
            gs.time_at_pause, gs.total_paused_duration, gs.last_fall_time, gs.last_ai_move_time, # Pass relevant gs fields
            joystick, joystick_enabled, help_screen_active,
            game_phase, current_username_input, config_menu_active,
            core_utils.sound_effects_enabled, # This is a global setting from core_utils
            shadow_enabled, line_blink_enabled, music_enabled, # These are local settings in main
            DEBUG_MODE
        )

        running = event_handling_result["running"]
        # Update gs based on event_handling_result
        gs.game_paused = event_handling_result["game_paused_update"]
        gs.ai_mode_active = event_handling_result["ai_mode_active_update"]
        # gs.soft_drop_active is updated by input_handler via gs
        gs.time_at_pause = event_handling_result["time_at_pause"]
        gs.total_paused_duration = event_handling_result["total_paused_duration"]
        gs.last_fall_time = event_handling_result["last_fall_time"]
        gs.last_ai_move_time = event_handling_result["last_ai_move_time"]

        action_request = event_handling_result["action_request"]
        help_screen_active = event_handling_result["help_screen_active"]
        config_menu_active = event_handling_result["config_menu_active"]
        # Settings are updated directly based on return dict, not via gs for these
        core_utils.sound_effects_enabled = event_handling_result["sound_effects_enabled"]
        shadow_enabled = event_handling_result["shadow_enabled"]
        line_blink_enabled = event_handling_result["line_blink_enabled"]
        music_enabled = event_handling_result["music_enabled"]
        current_username_input = event_handling_result["current_username_input"]
        # game_phase is updated from result, not from gs directly in this part of loop
        # game_phase = event_handling_result["game_phase_str"] # game_phase is managed by main loop logic

        if background_music_loaded:
            if music_enabled:
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.unpause()
                    if not pygame.mixer.music.get_busy():
                        pygame.mixer.music.play(loops=-1)
                    if DEBUG_MODE: print("DEBUG: music_enabled is True. Ensured music is playing/unpaused.")
            else:
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.pause()
                    if DEBUG_MODE: print("DEBUG: music_enabled is False. Music paused.")

        if not running:
            break

        if action_request == "RESTART":
            gs = game_state.GameState(**_handle_restart_action()) # Create new GameState
            formatted_time = ""
            help_screen_active = False # Reset UI state vars
            config_menu_active = False
            game_phase = "PLAYING"
            current_username_input = ""
            lines_being_animated = []
            line_animation_timer = 0
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

        prev_game_over = gs.game_over # Use gs.game_over

        # _update_game_state should now primarily modify gs in place.
        # It returns specific values like formatted_time and phase updates.
        game_logic_result = _update_game_state(
            gs, # Pass the GameState object
            # Time-related values from gs are used internally by _update_game_state
            # No longer need to pass game_start_time, final_game_time_str, total_paused_duration, time_at_pause explicitly if they are in gs
            # However, current _update_game_state takes them. For now, let's pass them from gs.
            gs.game_start_time, gs.final_game_time_str, gs.total_paused_duration, gs.time_at_pause,
            help_screen_active, game_phase, # Pass local UI states
            lines_being_animated, line_animation_timer,
            line_blink_enabled
        )

        # gs is updated in-place by _update_game_state and its helpers.
        formatted_time = game_logic_result["formatted_time"]
        game_phase = game_logic_result["game_phase_str"]
        lines_being_animated = game_logic_result["lines_being_animated"]
        line_animation_timer = game_logic_result["line_animation_timer"]

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

        # Drawing call is now correctly to ui_manager.draw_main_ui as per previous patch.
        # This diff focuses on removing the orphaned local drawing functions.
        ui_manager.draw_main_ui(
            screen, gs, fonts, clock,
            help_screen_active, help_text_surfaces,
            game_phase, current_username_input, top_scores_list,
            lines_being_animated, line_animation_timer,
            config_menu_active,
            core_utils.sound_effects_enabled, # Global via core_utils
            shadow_enabled,     # Local setting in main
            line_blink_enabled, # Local setting in main
            music_enabled,      # Local setting in main
            formatted_time,     # Calculated time string
            DEBUG_MODE
        )

    if background_music_loaded:
        pygame.mixer.music.stop()
        if DEBUG_MODE: print("DEBUG: Background music stopped on game exit.")

    pygame.mixer.quit()
    pygame.font.quit()
    pygame.quit()

if __name__ == '__main__':
    main()
