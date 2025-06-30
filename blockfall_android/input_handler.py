import pygame
import time
from .game_state import GameState
from .piece import Piece
from .blockfall_game import is_valid_position, play_sound
from .constants import RESTART_KEY

def handle_game_over_inputs(event):
    if event.type == pygame.QUIT:
        return "QUIT"
    if event.type == pygame.KEYDOWN:
        if event.key == RESTART_KEY:
            return "RESTART"
        if event.key == pygame.K_ESCAPE:
            return "QUIT"
    return None

def handle_player_piece_controls(event, gs: GameState, soft_drop_active_flag: bool) -> tuple[bool, bool]:
    action_taken = False
    if not gs.current_piece:
        return soft_drop_active_flag, action_taken

    if event.type == pygame.KEYDOWN:
        if gs.current_piece.is_hard_dropping_animated:
            return soft_drop_active_flag, action_taken

        if event.key == pygame.K_UP:
            gs.current_piece.rotate(gs.game_grid)
            action_taken = True
        elif event.key == pygame.K_LEFT:
            original_x = gs.current_piece.x
            gs.current_piece.x -= 1
            if not is_valid_position(gs.current_piece, gs.game_grid):
                gs.current_piece.x += 1
            else:
                play_sound("move")
                action_taken = True
        elif event.key == pygame.K_RIGHT:
            original_x = gs.current_piece.x
            gs.current_piece.x += 1
            if not is_valid_position(gs.current_piece, gs.game_grid):
                gs.current_piece.x -= 1
            else:
                play_sound("move")
                action_taken = True
        elif event.key == pygame.K_DOWN:
            soft_drop_active_flag = True
            action_taken = True
        elif event.key == pygame.K_SPACE:
            original_y = gs.current_piece.y
            temp_piece_for_calc = Piece(gs.current_piece.x, original_y, shape_type=gs.current_piece.shape_type, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
            temp_piece_for_calc.rotation = gs.current_piece.rotation
            calculated_target_y = original_y
            while is_valid_position(temp_piece_for_calc, gs.game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                calculated_target_y += 1
            gs.current_piece.target_y_for_animated_drop = calculated_target_y
            gs.current_piece.is_hard_dropping_animated = True
            soft_drop_active_flag = False
            action_taken = True

    elif event.type == pygame.KEYUP:
        if event.key == pygame.K_DOWN:
            if not gs.current_piece.is_hard_dropping_animated:
                soft_drop_active_flag = False
                action_taken = True
    return soft_drop_active_flag, action_taken

def process_event(event, gs: GameState, joystick_obj, joystick_enabled_flag: bool, game_phase_str: str, current_username_str: str):
    action_request = None
    running_flag_event = True
    event_processed = False

    if event.type == pygame.QUIT:
        running_flag_event = False
        action_request = "QUIT_GAME"
        event_processed = True
        return {
            "action_request": action_request,
            "running_flag_event": running_flag_event,
            "current_username_str": current_username_str,
            "event_processed_by_handler": event_processed
        }

    if game_phase_str == "GAME_OVER":
        action_request = handle_game_over_inputs(event)
        if action_request:
            event_processed = True
            if action_request == "QUIT":
                running_flag_event = False
                action_request = "QUIT_GAME"
    elif game_phase_str == "GETTING_USERNAME":
        if event.type == pygame.KEYDOWN:
            event_processed = True
            if event.key == pygame.K_RETURN:
                action_request = "SAVE_SCORE" if current_username_str else "SKIP_SAVE"
            elif event.key == pygame.K_ESCAPE:
                action_request = "SKIP_SAVE"
            elif event.key == pygame.K_BACKSPACE:
                current_username_str = current_username_str[:-1]
            elif len(current_username_str) < 15 and event.unicode.isalnum():
                current_username_str += event.unicode.upper()
            else:
                event_processed = False
    elif game_phase_str == "PLAYING" and not gs.game_paused and gs.current_piece and not gs.ai_mode_active:
        player_controls_action_taken = False
        if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
            gs.soft_drop_active, player_controls_action_taken = handle_player_piece_controls(event, gs, gs.soft_drop_active)
            if player_controls_action_taken: event_processed = True

        if joystick_enabled_flag and joystick_obj and not event_processed:
            if gs.current_piece and not gs.current_piece.is_hard_dropping_animated:
                joystick_action_taken = False
                if event.type == pygame.JOYAXISMOTION:
                    if event.joy == joystick_obj.get_id():
                        axis = event.axis
                        value = event.value
                        if axis == 0:
                            original_x = gs.current_piece.x
                            if value < -0.5: gs.current_piece.x -= 1
                            elif value > 0.5: gs.current_piece.x += 1
                            if gs.current_piece.x != original_x:
                                if not is_valid_position(gs.current_piece, gs.game_grid): gs.current_piece.x = original_x
                                else: play_sound("move"); joystick_action_taken = True
                        elif axis == 1:
                            if value > 0.5:
                                if not gs.soft_drop_active: joystick_action_taken = True
                                gs.soft_drop_active = True
                            else:
                                if gs.soft_drop_active: joystick_action_taken = True
                                gs.soft_drop_active = False
                elif event.type == pygame.JOYHATMOTION:
                    if event.joy == joystick_obj.get_id():
                        hat_x, hat_y = event.value
                        original_x = gs.current_piece.x
                        if hat_x == -1: gs.current_piece.x -= 1
                        elif hat_x == 1: gs.current_piece.x += 1
                        if original_x != gs.current_piece.x:
                            if not is_valid_position(gs.current_piece, gs.game_grid): gs.current_piece.x = original_x
                            else: play_sound("move"); joystick_action_taken = True

                        if hat_y == -1:
                            if not gs.soft_drop_active: joystick_action_taken = True
                            gs.soft_drop_active = True
                        elif hat_y == 1: gs.current_piece.rotate(gs.game_grid); joystick_action_taken = True
                        else:
                            if hat_x == 0 and gs.soft_drop_active : joystick_action_taken = True
                            if hat_x == 0 : gs.soft_drop_active = False
                elif event.type == pygame.JOYBUTTONDOWN:
                    if event.joy == joystick_obj.get_id():
                        button = event.button
                        if button != 6 and button != 7:
                            if button == 0:
                                gs.current_piece.rotate(gs.game_grid); joystick_action_taken = True
                            elif button == 1:
                                original_y = gs.current_piece.y
                                temp_piece_for_calc = Piece(gs.current_piece.x, original_y, shape_type=gs.current_piece.shape_type, is_valid_position_func=is_valid_position, play_sound_func=play_sound)
                                temp_piece_for_calc.rotation = gs.current_piece.rotation
                                calculated_target_y = original_y
                                while is_valid_position(temp_piece_for_calc, gs.game_grid, check_y_offset=(calculated_target_y - original_y + 1)):
                                    calculated_target_y += 1
                                gs.current_piece.target_y_for_animated_drop = calculated_target_y
                                gs.current_piece.is_hard_dropping_animated = True
                                gs.soft_drop_active = False; joystick_action_taken = True
                if joystick_action_taken: event_processed = True

    return {
        "action_request": action_request,
        "running_flag_event": running_flag_event,
        "current_username_str": current_username_str,
        "event_processed_by_handler": event_processed
    }
