import pygame
import time
from .game_state import GameState
from .piece import Piece # Changed from .blockfall_game to .piece
from .blockfall_game import is_valid_position # Piece removed from this import
from . import constants # Import the new constants module

# --- Constants are now in constants.py ---
# Colors, Grid dimensions, UI layout, Font sizes, Animation duration

def _draw_grid_lines(screen_surface):
    for row in range(constants.GRID_HEIGHT + 1): pygame.draw.line(screen_surface, constants.GREY, (constants.GRID_OFFSET_X, constants.GRID_OFFSET_Y + row * constants.BLOCK_SIZE), (constants.GRID_OFFSET_X + constants.GRID_WIDTH * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y + row * constants.BLOCK_SIZE))
    for col in range(constants.GRID_WIDTH + 1): pygame.draw.line(screen_surface, constants.GREY, (constants.GRID_OFFSET_X + col * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y), (constants.GRID_OFFSET_X + col * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y + constants.GRID_HEIGHT * constants.BLOCK_SIZE))

def _draw_blocks(screen_surface, game_grid, lines_being_animated, animation_timer, line_blink_enabled_flag):
    for r_idx, row in enumerate(game_grid):
        for c_idx, cell_color in enumerate(row):
            if cell_color != 0:
                current_block_color = cell_color
                if r_idx in lines_being_animated:
                    if line_blink_enabled_flag:
                        progress_frames = constants.LINE_ANIMATION_DURATION - animation_timer
                        blink_phase_duration = constants.LINE_ANIMATION_DURATION / 10
                        current_blink_phase = int(progress_frames / blink_phase_duration)
                        if current_blink_phase % 2 == 0:
                            current_block_color = constants.WHITE
                        else:
                            current_block_color = cell_color
                        if animation_timer < (constants.LINE_ANIMATION_DURATION / 5):
                            current_block_color = constants.BLACK
                    else:
                        current_block_color = constants.BLACK
                pygame.draw.rect(screen_surface, current_block_color, (constants.GRID_OFFSET_X + c_idx * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y + r_idx * constants.BLOCK_SIZE, constants.BLOCK_SIZE -1, constants.BLOCK_SIZE -1))

def _draw_current_piece_on_grid(screen_surface, piece):
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >= 0:
                pygame.draw.rect(screen_surface, piece.color, (constants.GRID_OFFSET_X + c_idx * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y + r_idx * constants.BLOCK_SIZE, constants.BLOCK_SIZE -1, constants.BLOCK_SIZE -1))

def _get_shadow_position_y(piece, grid_data): # is_valid_position is imported
    if not piece: return -1
    current_y_offset = 0
    while is_valid_position(piece, grid_data, check_y_offset=current_y_offset + 1):
        current_y_offset += 1
    return piece.y + current_y_offset

def _draw_next_piece_area(screen_surface, piece_to_draw, x_pos, y_pos, title_str, fonts):
    title_surface = fonts['title'].render(title_str, True, constants.WHITE)
    screen_surface.blit(title_surface, (x_pos, y_pos))
    box_y_pos = y_pos + title_surface.get_height() + 5
    pygame.draw.rect(screen_surface, constants.GREY, (x_pos, box_y_pos, constants.NEXT_PIECE_BOX_SIZE, constants.NEXT_PIECE_BOX_SIZE), 1)
    if piece_to_draw:
        shape_coords = piece_to_draw.get_shape_for_preview()
        min_r_offset = min(r for r,c in shape_coords) if shape_coords else 0
        max_r_offset = max(r for r,c in shape_coords) if shape_coords else 0
        min_c_offset = min(c for r,c in shape_coords) if shape_coords else 0
        max_c_offset = max(c for r,c in shape_coords) if shape_coords else 0
        shape_width_blocks = max_c_offset - min_c_offset + 1
        shape_height_blocks = max_r_offset - min_r_offset + 1
        start_draw_x = x_pos + (constants.NEXT_PIECE_BOX_SIZE - shape_width_blocks * constants.NEXT_PIECE_BLOCK_SIZE) // 2
        start_draw_y = box_y_pos + (constants.NEXT_PIECE_BOX_SIZE - shape_height_blocks * constants.NEXT_PIECE_BLOCK_SIZE) // 2
        for r_offset, c_offset in shape_coords:
            block_x = start_draw_x + (c_offset - min_c_offset) * constants.NEXT_PIECE_BLOCK_SIZE
            block_y = start_draw_y + (r_offset - min_r_offset) * constants.NEXT_PIECE_BLOCK_SIZE
            pygame.draw.rect(screen_surface, piece_to_draw.color, (block_x, block_y, constants.NEXT_PIECE_BLOCK_SIZE -1, constants.NEXT_PIECE_BLOCK_SIZE -1))

def _draw_level_progress_bar(screen_surface, current_lines, lines_needed, bar_outer_rect, colors, font, text_color):
    pygame.draw.rect(screen_surface, colors['bg'], bar_outer_rect)
    fill_percentage = 0.0
    if lines_needed > 0: fill_percentage = min(1.0, float(current_lines) / lines_needed)
    fill_width = int(fill_percentage * bar_outer_rect.width)
    if fill_width > 0:
        fill_rect = pygame.Rect(bar_outer_rect.x, bar_outer_rect.y, fill_width, bar_outer_rect.height)
        pygame.draw.rect(screen_surface, colors['fill'], fill_rect)
    if 'border' in colors: pygame.draw.rect(screen_surface, colors['border'], bar_outer_rect, 1)
    progress_text_str = f"Progress: {current_lines}/{lines_needed}"
    text_surface = font.render(progress_text_str, True, text_color)
    text_x = bar_outer_rect.centerx - text_surface.get_width() // 2
    text_y = bar_outer_rect.y - text_surface.get_height() - 2
    screen_surface.blit(text_surface, (text_x, text_y))

def _draw_full_ui(screen_surface, gs: GameState, fonts, formatted_time_str, top_scores_list):
    current_y = constants.UI_INFO_START_Y
    ui_start_x = constants.GRID_OFFSET_X + constants.GRID_WIDTH * constants.BLOCK_SIZE + constants.UI_INFO_X_OFFSET

    score_surface = fonts['score'].render(f"Score: {gs.score}", True, constants.WHITE)
    screen_surface.blit(score_surface, (ui_start_x, current_y))
    current_y += fonts['score'].get_height() + constants.UI_INFO_LINE_SPACING

    level_surface = fonts['info'].render(f"Level: {gs.current_level}", True, constants.WHITE)
    screen_surface.blit(level_surface, (ui_start_x, current_y))
    current_y += fonts['info'].get_height() + constants.UI_INFO_LINE_SPACING

    lines_surface = fonts['info'].render(f"Lines: {gs.total_lines_cleared}", True, constants.WHITE)
    screen_surface.blit(lines_surface, (ui_start_x, current_y))
    current_y += fonts['info'].get_height() + constants.UI_INFO_LINE_SPACING

    ai_mode_text = "AI Mode: " + ("ON" if gs.ai_mode_active else "OFF")
    ai_status_color = constants.GREEN if gs.ai_mode_active else constants.RED
    ai_surface = fonts['info'].render(ai_mode_text, True, ai_status_color)
    screen_surface.blit(ai_surface, (ui_start_x, current_y))
    current_y += fonts['info'].get_height() + constants.UI_INFO_LINE_SPACING

    time_text_surface = fonts['info'].render(f"Time: {formatted_time_str}", True, constants.WHITE)
    screen_surface.blit(time_text_surface, (ui_start_x, current_y))
    current_y += fonts['info'].get_height() + constants.UI_INFO_LINE_SPACING

    if top_scores_list:
        top_score_entry = top_scores_list[0]
        if isinstance(top_score_entry, dict) and "username" in top_score_entry and "score" in top_score_entry:
            if top_score_entry.get("score", 0) > 0:
                best_score_text = f"Best: {top_score_entry['username']} - {top_score_entry['score']}"
                best_score_surface = fonts['info'].render(best_score_text, True, constants.YELLOW)
                screen_surface.blit(best_score_surface, (ui_start_x, current_y))
                current_y += fonts['info'].get_height() + constants.UI_INFO_LINE_SPACING

    progress_text_height = fonts['info'].get_height()
    progress_bar_rect_y = current_y + progress_text_height + 5
    bar_outer_rect = pygame.Rect(ui_start_x, progress_bar_rect_y, constants.PROGRESS_BAR_WIDTH, constants.PROGRESS_BAR_HEIGHT)
    progress_bar_colors = {"bg": constants.PROGRESS_BAR_BACKGROUND_COLOR, "fill": constants.PROGRESS_BAR_FILL_COLOR, "border": constants.PROGRESS_BAR_BORDER_COLOR}
    _draw_level_progress_bar(screen_surface, gs.lines_for_current_level, constants.LINES_PER_LEVEL, bar_outer_rect, progress_bar_colors, fonts['info'], constants.WHITE)
    current_y = progress_bar_rect_y + constants.PROGRESS_BAR_HEIGHT + constants.UI_INFO_LINE_SPACING * 2

    _draw_next_piece_area(screen_surface, gs.next_piece_1 if not gs.game_over else None, ui_start_x, current_y, "Next 1:", fonts)
    title_height_estimate = fonts['title'].get_height()
    current_y += title_height_estimate + 5 + constants.NEXT_PIECE_BOX_SIZE + constants.UI_INFO_LINE_SPACING * 2
    _draw_next_piece_area(screen_surface, gs.next_piece_2 if not gs.game_over else None, ui_start_x, current_y, "Next 2:", fonts)

def _render_help_text_surfaces(fonts, text_color): # text_color is constants.WHITE
    help_lines_data = [
        ("BlockFall - HELP", fonts['game_over']), # Typically larger font for title
        ("", fonts['info']), # Spacer
        ("Keyboard Controls:", fonts['score']), # Slightly larger for section titles
        ("  Left Arrow:  Move Piece Left", fonts['info']),
        ("  Right Arrow: Move Piece Right", fonts['info']),
        ("  Up Arrow:    Rotate Piece", fonts['info']),
        ("  Down Arrow:  Soft Drop Piece", fonts['info']),
        ("  Space Bar:   Hard Drop Piece", fonts['info']),
        ("  P:           Pause / Resume Game", fonts['info']),
        ("  A:           Toggle AI Mode", fonts['info']),
        ("  R:           Restart Game (Game Over)", fonts['info']),
        ("  H:           Show / Hide Help", fonts['info']),
        ("  C:           Config Menu", fonts['info']),
        ("  ESC:         Quit Game / Close Help/Menu", fonts['info']),
        ("", fonts['info']),
        ("Joystick Controls (Defaults):", fonts['score']),
        ("  Analog X / D-Pad X:   Move Left/Right", fonts['info']),
        ("  Analog Y / D-Pad Y (Down): Soft Drop", fonts['info']),
        ("  D-Pad Y (Up):         Rotate Piece", fonts['info']),
        ("  Button 0 (A/X):       Rotate Piece", fonts['info']),
        ("  Button 1 (B/Circle):  Hard Drop Piece", fonts['info']),
        ("  Button 7 (Start):     Pause/Resume/Restart", fonts['info']),
        ("  Button 6 (Select):    Toggle AI Mode", fonts['info']),
        ("", fonts['info']),
        ("Press 'H' or 'ESC' to close.", fonts['info'])
    ]
    rendered_surfaces = []
    for text, font_obj in help_lines_data:
        surface = font_obj.render(text, True, text_color)
        rendered_surfaces.append(surface)
    return rendered_surfaces

def _draw_help_screen(screen_surface, help_text_surfaces_list):
    screen_width = screen_surface.get_width()
    screen_height = screen_surface.get_height()
    overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    screen_surface.blit(overlay, (0,0))
    total_text_height = sum(s.get_height() for s in help_text_surfaces_list)
    line_padding = 5
    total_height_with_padding = total_text_height + (len(help_text_surfaces_list) - 1) * line_padding
    start_y = (screen_height - total_height_with_padding) // 2
    current_y = start_y
    for surface in help_text_surfaces_list:
        text_x = (screen_width - surface.get_width()) // 2
        screen_surface.blit(surface, (text_x, current_y))
        current_y += surface.get_height() + line_padding

def _draw_high_score_screen(screen_surface, top_scores_list, fonts):
    screen_width = screen_surface.get_width()
    screen_height = screen_surface.get_height()
    screen_surface.fill(constants.BLACK)
    title_surf = fonts['game_over'].render("Top 10 Scores", True, constants.WHITE)
    title_rect = title_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 200))
    screen_surface.blit(title_surf, title_rect)
    start_y_scores = title_rect.bottom + 40
    line_height = fonts['info'].get_height() + 10
    if not top_scores_list:
        no_scores_surf = fonts['info'].render("No high scores yet!", True, constants.WHITE)
        no_scores_rect = no_scores_surf.get_rect(center=(screen_width // 2, start_y_scores + line_height * 2))
        screen_surface.blit(no_scores_surf, no_scores_rect)
    else:
        rank_x = screen_width // 2 - 250
        name_x = screen_width // 2 - 150
        score_val_x = screen_width // 2 + 100
        header_rank_surf = fonts['score'].render("Rank", True, constants.YELLOW)
        header_name_surf = fonts['score'].render("Name", True, constants.YELLOW)
        header_score_surf = fonts['score'].render("Score", True, constants.YELLOW)
        screen_surface.blit(header_rank_surf, (rank_x, start_y_scores))
        screen_surface.blit(header_name_surf, (name_x, start_y_scores))
        screen_surface.blit(header_score_surf, (score_val_x + 50 - header_score_surf.get_width(), start_y_scores))
        current_y = start_y_scores + line_height
        for i, entry in enumerate(top_scores_list):
            if i >= 10: break
            rank_str = f"{i + 1}."
            username_str = entry.get("username", "N/A")[:15]
            score_str = str(entry.get("score", 0))
            rank_surf = fonts['info'].render(rank_str, True, constants.WHITE)
            name_surf = fonts['info'].render(username_str, True, constants.WHITE)
            score_val_surf = fonts['info'].render(score_str, True, constants.WHITE)
            screen_surface.blit(rank_surf, (rank_x, current_y))
            screen_surface.blit(name_surf, (name_x, current_y))
            screen_surface.blit(score_val_surf, (score_val_x + 50 - score_val_surf.get_width(), current_y))
            current_y += line_height
    instruction_y = screen_height - 100
    instruction_surf = fonts['info'].render("Press any key to Restart, ESC to Quit", True, constants.WHITE)
    instruction_rect = instruction_surf.get_rect(center=(screen_width // 2, instruction_y))
    screen_surface.blit(instruction_surf, instruction_rect)

def draw_main_ui(screen_surface, gs: GameState, fonts, clock_obj, help_screen_active_flag, help_text_surfaces_list, game_phase_str, current_username_str, top_scores_list, lines_being_animated_list, line_animation_timer_val, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag, formatted_time_str, DEBUG_MODE):
    screen_width = screen_surface.get_width()
    screen_height = screen_surface.get_height()
    screen_surface.fill(constants.BLACK)
    _draw_grid_lines(screen_surface)
    _draw_blocks(screen_surface, gs.game_grid, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag)

    if shadow_enabled_flag:
        if not gs.game_over and gs.current_piece and game_phase_str == "PLAYING":
            shadow_y = _get_shadow_position_y(gs.current_piece, gs.game_grid)
            shadow_color = constants.GREY
            if gs.current_piece.shape and gs.current_piece.rotation < len(gs.current_piece.shape):
                for r_offset, c_offset in gs.current_piece.shape[gs.current_piece.rotation]:
                    block_r, block_c = shadow_y + r_offset, gs.current_piece.x + c_offset
                    if 0 <= block_r < constants.GRID_HEIGHT and 0 <= block_c < constants.GRID_WIDTH:
                        pygame.draw.rect(screen_surface, shadow_color, (constants.GRID_OFFSET_X + block_c * constants.BLOCK_SIZE, constants.GRID_OFFSET_Y + block_r * constants.BLOCK_SIZE, constants.BLOCK_SIZE - 1, constants.BLOCK_SIZE - 1))

    if not gs.game_over and gs.current_piece and game_phase_str != "GETTING_USERNAME" and game_phase_str != "LINE_ANIMATION":
         _draw_current_piece_on_grid(screen_surface, gs.current_piece)

    _draw_full_ui(screen_surface, gs, fonts, formatted_time_str, top_scores_list)

    if game_phase_str == "GETTING_USERNAME":
        game_over_text_surf = fonts['game_over'].render("GAME OVER", True, constants.RED)
        final_score_text = f"Final Score: {gs.score}"
        final_score_surf = fonts['info'].render(final_score_text, True, constants.WHITE)
        text_rect_game_over = game_over_text_surf.get_rect(center=(screen_width // 2, screen_height // 2 - final_score_surf.get_height() / 2 - 40))
        text_rect_score = final_score_surf.get_rect(center=(screen_width // 2, screen_height // 2 + game_over_text_surf.get_height() / 2 - 40))
        screen_surface.blit(game_over_text_surf, text_rect_game_over)
        screen_surface.blit(final_score_surf, text_rect_score)
        prompt_text_surface = fonts['info'].render("New Best! Enter Name (Max 15):", True, constants.WHITE)
        prompt_rect = prompt_text_surface.get_rect(center=(screen_width // 2, screen_height // 2 + 40))
        screen_surface.blit(prompt_text_surface, prompt_rect)
        name_input_surface = fonts['info'].render(current_username_str, True, constants.YELLOW)
        name_input_rect = name_input_surface.get_rect(center=(screen_width // 2, screen_height // 2 + 80))
        screen_surface.blit(name_input_surface, name_input_rect)
        if time.time() % 1 < 0.5:
            cursor_surface = fonts['info'].render("_", True, constants.YELLOW)
            cursor_x = name_input_rect.right + 2 if current_username_str else name_input_rect.centerx
            cursor_rect = cursor_surface.get_rect(topleft=(cursor_x, name_input_rect.top))
            screen_surface.blit(cursor_surface, cursor_rect)
    elif gs.game_over:
        game_over_text_surf = fonts['game_over'].render("GAME OVER", True, constants.RED)
        final_score_text = f"Final Score: {gs.score}"
        final_score_surf = fonts['info'].render(final_score_text, True, constants.WHITE)
        text_rect_game_over = game_over_text_surf.get_rect(center=(screen_width // 2, screen_height // 2 - final_score_surf.get_height() / 2))
        text_rect_score = final_score_surf.get_rect(center=(screen_width // 2, screen_height // 2 + game_over_text_surf.get_height() / 2))
        screen_surface.blit(game_over_text_surf, text_rect_game_over)
        screen_surface.blit(final_score_surf, text_rect_score)
        restart_text_surf = fonts['info'].render("Press 'R' to Restart", True, constants.WHITE)
        quit_text_surf = fonts['info'].render("Press 'ESC' to Quit", True, constants.WHITE)
        y_pos_restart = text_rect_score.bottom + 20
        text_rect_restart = restart_text_surf.get_rect(center=(screen_width // 2, y_pos_restart + restart_text_surf.get_height() // 2))
        screen_surface.blit(restart_text_surf, text_rect_restart)
        y_pos_quit = text_rect_restart.bottom + 10
        text_rect_quit = quit_text_surf.get_rect(center=(screen_width // 2, y_pos_quit + quit_text_surf.get_height() // 2))
        screen_surface.blit(quit_text_surf, text_rect_quit)

    if gs.game_paused and not gs.game_over and not help_screen_active_flag and not config_menu_active_flag and game_phase_str != "GETTING_USERNAME":
        pause_text_surface = fonts['game_over'].render("PAUSED", True, constants.YELLOW)
        text_rect_pause = pause_text_surface.get_rect(center=(screen_width // 2, screen_height // 2))
        screen_surface.blit(pause_text_surface, text_rect_pause)

    if help_screen_active_flag:
        _draw_help_screen(screen_surface, help_text_surfaces_list)
    elif config_menu_active_flag:
        overlay = pygame.Surface((screen_width, screen_height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen_surface.blit(overlay, (0,0))
        title_text_surf = fonts['game_over'].render("CONFIGURATION MENU", True, constants.WHITE)
        title_rect = title_text_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 140))
        screen_surface.blit(title_text_surf, title_rect)
        sound_fx_status_str = "ON" if sound_effects_enabled_flag else "OFF"
        sound_fx_option_text_str = f"Sound FX: {sound_fx_status_str} (Press S to toggle)"
        sound_fx_option_surf = fonts['info'].render(sound_fx_option_text_str, True, constants.WHITE)
        sound_fx_option_rect = sound_fx_option_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 80))
        screen_surface.blit(sound_fx_option_surf, sound_fx_option_rect)
        music_status_str = "ON" if music_enabled_flag else "OFF"
        music_option_text_str = f"Music: {music_status_str} (Press M to toggle)"
        music_option_surf = fonts['info'].render(music_option_text_str, True, constants.WHITE)
        music_option_rect = music_option_surf.get_rect(center=(screen_width // 2, screen_height // 2 - 40))
        screen_surface.blit(music_option_surf, music_option_rect)
        shadow_status_str = "ON" if shadow_enabled_flag else "OFF"
        shadow_option_text_str = f"Shadow: {shadow_status_str} (Press D to toggle)"
        shadow_option_surf = fonts['info'].render(shadow_option_text_str, True, constants.WHITE)
        shadow_option_rect = shadow_option_surf.get_rect(center=(screen_width // 2, screen_height // 2 + 0))
        screen_surface.blit(shadow_option_surf, shadow_option_rect)
        line_blink_status_str = "ON" if line_blink_enabled_flag else "OFF"
        line_blink_option_text_str = f"Line Blink: {line_blink_status_str} (Press B to toggle)"
        line_blink_option_surf = fonts['info'].render(line_blink_option_text_str, True, constants.WHITE)
        line_blink_option_rect = line_blink_option_surf.get_rect(center=(screen_width // 2, screen_height // 2 + 40))
        screen_surface.blit(line_blink_option_surf, line_blink_option_rect)
        close_hint_surf = fonts['info'].render("Press C or ESC to close", True, constants.GREY)
        close_hint_rect = close_hint_surf.get_rect(center=(screen_width // 2, screen_height // 2 + 100))
        screen_surface.blit(close_hint_surf, close_hint_rect)
    elif game_phase_str == "HIGH_SCORE_DISPLAY":
        _draw_high_score_screen(screen_surface, top_scores_list, fonts)

    pygame.display.flip()
    if clock_obj:
        clock_obj.tick(60)
