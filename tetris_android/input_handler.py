import pygame
import time
from .game_state import GameState
from .piece import Piece
from .core_utils import is_valid_position, play_sound # Changed from .tetris to .core_utils
from .constants import AI_PLAYER_TOGGLE_KEY, RESTART_KEY, PAUSE_KEY
# Note: Constants like GRID_WIDTH might be needed if is_valid_position or Piece logic relies on them directly from this file.
# For now, assuming they are handled within the context of those functions or via gs.

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
        if event.key == RESTART_KEY:
            return "RESTART"
        if event.key == pygame.K_ESCAPE: # Using ESC as a global quit key too
            return "QUIT"
    return None

def handle_player_piece_controls(event, gs: GameState, soft_drop_active_flag: bool) -> bool:
    """
    Handles player inputs for controlling the current piece (movement, rotation, drop).
    Assumes gs.current_piece exists, game is not over, AI is not active, and piece is not already hard dropping.
    Args:
        event (pygame.event.Event): The Pygame event to process.
        gs (GameState): The current game state.
        soft_drop_active_flag (bool): Current state of soft drop.
    Returns:
        bool: Updated state of soft_drop_active_flag.
    """
    if not gs.current_piece: # Should not happen if called correctly
        return soft_drop_active_flag

    if event.type == pygame.KEYDOWN:
        if gs.current_piece.is_hard_dropping_animated:
            return soft_drop_active_flag

        if event.key == pygame.K_UP:
            gs.current_piece.rotate(gs.game_grid)
        elif event.key == pygame.K_LEFT:
            gs.current_piece.x -= 1
            if not is_valid_position(gs.current_piece, gs.game_grid):
                gs.current_piece.x += 1
            else:
                play_sound("move")
        elif event.key == pygame.K_RIGHT:
            gs.current_piece.x += 1
            if not is_valid_position(gs.current_piece, gs.game_grid):
                gs.current_piece.x -= 1
            else:
                play_sound("move")
        elif event.key == pygame.K_DOWN: # Activate soft drop
            soft_drop_active_flag = True
        elif event.key == pygame.K_SPACE: # Initiate Animated Hard Drop
            original_y = gs.current_piece.y
            # Create a temporary piece for calculation if Piece constructor needs shape_type
            temp_piece_for_calc = Piece(gs.current_piece.x, original_y, shape_type=gs.current_piece.shape_type) # Func params removed
            temp_piece_for_calc.rotation = gs.current_piece.rotation

            calculated_target_y = original_y
            # Need to ensure is_valid_position is accessible here
            while is_valid_position(temp_piece_for_calc, gs.game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                calculated_target_y += 1

            gs.current_piece.target_y_for_animated_drop = calculated_target_y
            gs.current_piece.is_hard_dropping_animated = True
            soft_drop_active_flag = False

    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_DOWN:
            if not gs.current_piece.is_hard_dropping_animated:
                 soft_drop_active_flag = False
    return soft_drop_active_flag

def process_event(event, gs: GameState, joystick_obj, joystick_enabled_flag: bool, game_phase_str: str, current_username_str: str):
    """
    Processes a single game event for phases/inputs that are delegated to input_handler.
    Returns a dictionary with outcomes.
    """
    action_request = None
    running_flag_event = True # Assume running unless QUIT
    # gs.soft_drop_active is modified directly if gs is passed and modified
    # current_username_str is returned as it's a local string in _handle_events

    if event.type == pygame.QUIT:
        running_flag_event = False
        return {"action_request": "QUIT_GAME", "running_flag_event": running_flag_event, "current_username_str": current_username_str}


    if game_phase_str == "GAME_OVER":
        action_request = handle_game_over_inputs(event)
        if action_request == "QUIT": # handle_game_over_inputs can signal QUIT
            running_flag_event = False
            action_request = "QUIT_GAME" # Standardize quit action

    elif game_phase_str == "GETTING_USERNAME":
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                action_request = "SAVE_SCORE" if current_username_str else "SKIP_SAVE"
            elif event.key == pygame.K_ESCAPE:
                action_request = "SKIP_SAVE"
            elif event.key == pygame.K_BACKSPACE:
                current_username_str = current_username_str[:-1]
            elif len(current_username_str) < 15 and event.unicode.isalnum():
                current_username_str += event.unicode.upper()

    elif game_phase_str == "PLAYING" and not gs.game_paused and gs.current_piece and not gs.ai_mode_active :
        # Keyboard piece controls
        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
             gs.soft_drop_active = handle_player_piece_controls(event, gs, gs.soft_drop_active)

        # Joystick piece controls
        if joystick_enabled_flag and joystick_obj:
            if not gs.current_piece.is_hard_dropping_animated:
                if event.type == pygame.JOYAXISMOTION:
                    if event.joy == joystick_obj.get_id():
                        axis = event.axis
                        value = event.value
                        if axis == 0: # X-axis
                            if value < -0.5: gs.current_piece.x -= 1
                            elif value > 0.5: gs.current_piece.x += 1
                            if not is_valid_position(gs.current_piece, gs.game_grid): gs.current_piece.x -= (1 if value > 0.5 else -1)
                            else: play_sound("move")
                        elif axis == 1: # Y-axis
                            if value > 0.5: gs.soft_drop_active = True
                            else: gs.soft_drop_active = False
                elif event.type == pygame.JOYHATMOTION:
                    if event.joy == joystick_obj.get_id():
                        hat_x, hat_y = event.value
                        if hat_x == -1: gs.current_piece.x -= 1
                        elif hat_x == 1: gs.current_piece.x += 1
                        if not is_valid_position(gs.current_piece, gs.game_grid): gs.current_piece.x -= (1 if hat_x == 1 else -1)
                        else: play_sound("move")

                        if hat_y == -1: gs.soft_drop_active = True # D-Pad Down for soft drop
                        elif hat_y == 1: gs.current_piece.rotate(gs.game_grid) # D-Pad Up to rotate
                        else: # Y is neutral
                                if hat_x == 0 : gs.soft_drop_active = False
                elif event.type == pygame.JOYBUTTONDOWN:
                     if event.joy == joystick_obj.get_id():
                        button = event.button
                        # Buttons 6 (Select/Back) and 7 (Start) are for global AI/Pause in tetris.py _handle_events
                        if button != 6 and button != 7:
                            if button == 0: # Typically A or X
                                gs.current_piece.rotate(gs.game_grid)
                            elif button == 1: # Typically B or Circle
                                original_y = gs.current_piece.y
                                temp_piece_for_calc = Piece(gs.current_piece.x, original_y, shape_type=gs.current_piece.shape_type) # Func params removed
                                temp_piece_for_calc.rotation = gs.current_piece.rotation
                                calculated_target_y = original_y
                                while is_valid_position(temp_piece_for_calc, gs.game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                                    calculated_target_y += 1
                                gs.current_piece.target_y_for_animated_drop = calculated_target_y
                                gs.current_piece.is_hard_dropping_animated = True
                                gs.soft_drop_active = False

    return {
        "action_request": action_request,
        "running_flag_event": running_flag_event,
        "current_username_str": current_username_str
        # gs.soft_drop_active is modified directly on gs instance
    }
