import pygame
import random
import time
import os
import copy
import json
import argparse
from .config_manager import ConfigManager, set_debug_mode as set_cm_debug_mode
from . import constants as game_constants # Import constants module
from .constants import (
    BLACK, WHITE, CYAN, YELLOW, MAGENTA, GREEN, RED, BLUE, ORANGE, GREY, GARBAGE_COLOR,
    PIECE_COLORS, SHAPES,
    SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE,
    NEXT_PIECE_BLOCK_SIZE,
    UI_INFO_X_OFFSET, UI_INFO_START_Y, UI_INFO_LINE_SPACING, NEXT_PIECE_BOX_SIZE,
    SCORE_FONT_SIZE, INFO_FONT_SIZE, TITLE_FONT_SIZE, GAME_OVER_FONT_SIZE,
    INITIAL_FALL_SPEED, FALL_SPEED_DECREMENT_PER_LEVEL, MIN_FALL_SPEED,
    LINES_PER_LEVEL, GARBAGE_START_LEVEL, MAX_GARBAGE_ROWS,
    AI_PLAYER_TOGGLE_KEY, RESTART_KEY, PAUSE_KEY, AI_MOVE_DELAY, LINE_ANIMATION_DURATION,
    PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT, PROGRESS_BAR_BACKGROUND_COLOR,
    PROGRESS_BAR_FILL_COLOR, PROGRESS_BAR_BORDER_COLOR
)
from .piece import Piece
from . import ai_player

pygame.init()
pygame.font.init()
pygame.mixer.init()
pygame.joystick.init()

DEBUG_MODE = False

def load_font(size):
    font_name = "DejaVuSans.ttf"
    try:
        return pygame.font.Font(font_name, size)
    except (pygame.error, FileNotFoundError) as e:
        if DEBUG_MODE:
            print(f"DEBUG: Font '{font_name}' not found or failed to load: {e}. Falling back to system default.")
        try:
            return pygame.font.SysFont(None, size)
        except pygame.error as e_sys:
            if DEBUG_MODE:
                print(f"DEBUG: System default font also failed to load: {e_sys}. Returning None.")
            return None

SCORE_FONT = None; INFO_FONT = None; TITLE_FONT = None; GAME_OVER_FONT = None
SOUND_EFFECTS = {"move": None, "rotate": None, "drop": None, "line_clear": None, "blockfall_clear": None, "level_up": None, "game_over": None}
SOUND_DIR = "sounds"
sound_effects_enabled = True
shadow_enabled = True
line_blink_enabled = True
music_enabled = True

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path): print(f"Sound file not found: {path}"); return None
    try: sound = pygame.mixer.Sound(path); sound.set_volume(0.3); return sound
    except pygame.error as e: print(f"Error loading sound {filename}: {e}"); return None

def play_sound(sound_name):
    global sound_effects_enabled
    if not sound_effects_enabled: return
    if SOUND_EFFECTS.get(sound_name): SOUND_EFFECTS[sound_name].play()

def create_grid(fill_value=0): return [[fill_value for _ in range(game_constants.GRID_WIDTH)] for _ in range(game_constants.GRID_HEIGHT)]
def draw_grid_lines(screen):
    for row in range(game_constants.GRID_HEIGHT + 1): pygame.draw.line(screen, GREY, (game_constants.GRID_OFFSET_X, game_constants.GRID_OFFSET_Y + row * game_constants.BLOCK_SIZE), (game_constants.GRID_OFFSET_X + game_constants.GRID_WIDTH * game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y + row * game_constants.BLOCK_SIZE))
    for col in range(game_constants.GRID_WIDTH + 1): pygame.draw.line(screen, GREY, (game_constants.GRID_OFFSET_X + col * game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y), (game_constants.GRID_OFFSET_X + col * game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y + game_constants.GRID_HEIGHT * game_constants.BLOCK_SIZE))

def draw_blocks(screen, grid_data, lines_being_animated, animation_timer, line_blink_enabled_flag):
    for r_idx, row in enumerate(grid_data):
        for c_idx, cell_color in enumerate(row):
            if cell_color != 0:
                current_block_color = cell_color
                if r_idx in lines_being_animated:
                    if line_blink_enabled_flag:
                        progress_frames = LINE_ANIMATION_DURATION - animation_timer
                        blink_phase_duration = LINE_ANIMATION_DURATION / 10
                        current_blink_phase = int(progress_frames / blink_phase_duration)
                        if current_blink_phase % 2 == 0: current_block_color = WHITE
                        else: current_block_color = cell_color
                        if animation_timer < (LINE_ANIMATION_DURATION / 5): current_block_color = BLACK
                    else: current_block_color = BLACK
                pygame.draw.rect(screen, current_block_color, (game_constants.GRID_OFFSET_X + c_idx * game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y + r_idx * game_constants.BLOCK_SIZE, game_constants.BLOCK_SIZE -1, game_constants.BLOCK_SIZE -1))

def draw_current_piece_on_grid(screen, piece):
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >= 0:
                pygame.draw.rect(screen, piece.color, (game_constants.GRID_OFFSET_X + c_idx * game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y + r_idx * game_constants.BLOCK_SIZE, game_constants.BLOCK_SIZE -1, game_constants.BLOCK_SIZE -1))

def is_valid_position(piece, grid_data, check_y_offset=0):
    if not piece: return False
    for r_idx, c_idx in piece.current_shape_coords():
        actual_r = r_idx + check_y_offset
        if not (0 <= c_idx < game_constants.GRID_WIDTH and actual_r < game_constants.GRID_HEIGHT): return False
        if 0 <= actual_r < game_constants.GRID_HEIGHT and grid_data[actual_r][c_idx] != 0: return False
    return True

def add_to_grid(piece, grid_data):
    if piece:
        for r_idx, c_idx in piece.current_shape_coords():
            if r_idx >=0: grid_data[r_idx][c_idx] = piece.color
        play_sound("drop")

def get_shadow_position_y(piece, grid_data):
    if not piece: return -1
    current_y_offset = 0
    while is_valid_position(piece, grid_data, check_y_offset=current_y_offset + 1): current_y_offset += 1
    return piece.y + current_y_offset

def get_full_lines(grid_data):
    return [r_idx for r_idx, row in enumerate(grid_data) if 0 not in row]

def get_score_for_lines(lines_cleared, level): base_score = {1:40,2:100,3:300,4:1200}; return base_score.get(lines_cleared,0)*level

def spawn_piece_at_start(piece_set_type="standard"):
    return Piece(game_constants.GRID_WIDTH//2,0,is_valid_position,play_sound,piece_set_type)

def calculate_fall_speed(level): return max(MIN_FALL_SPEED,INITIAL_FALL_SPEED-(level-1)*FALL_SPEED_DECREMENT_PER_LEVEL)

def add_garbage_blocks(grid_data, level, piece_set_type="standard"):
    if level < GARBAGE_START_LEVEL: return False
    num_garbage_rows = min(MAX_GARBAGE_ROWS, (level - GARBAGE_START_LEVEL) // 2 + 1)
    for i in range(num_garbage_rows):
        if any(grid_data[i]): print("Warning: Not enough space for garbage."); return False
    for _ in range(num_garbage_rows): del grid_data[0]; grid_data.append([0]*game_constants.GRID_WIDTH)
    for i in range(num_garbage_rows):
        row_idx = game_constants.GRID_HEIGHT-1-i; garbage_row = [GARBAGE_COLOR]*game_constants.GRID_WIDTH
        garbage_row[random.randint(0,game_constants.GRID_WIDTH-1)]=0; grid_data[row_idx]=garbage_row
    return not is_valid_position(Piece(game_constants.GRID_WIDTH//2,0,is_valid_position,play_sound,piece_set_type),grid_data)

def format_time(s): m=int(s//60); s=int(s%60); return f"{m:02d}:{s:02d}"

def draw_next_piece_area(screen, piece, x, y, title):
    global TITLE_FONT
    if TITLE_FONT is None: TITLE_FONT = load_font(TITLE_FONT_SIZE)
    box_y = y + 20
    if TITLE_FONT:
        surf = TITLE_FONT.render(title, True, WHITE); screen.blit(surf, (x,y)); box_y = y + surf.get_height() + 5
    pygame.draw.rect(screen,GREY,(x,box_y,NEXT_PIECE_BOX_SIZE,NEXT_PIECE_BOX_SIZE),1)
    if piece:
        coords = piece.get_shape_for_preview()
        min_r,max_r = (min(r for r,c in coords),max(r for r,c in coords)) if coords else (0,0)
        min_c,max_c = (min(c for r,c in coords),max(c for r,c in coords)) if coords else (0,0)
        w,h = max_c-min_c+1, max_r-min_r+1
        sx = x + (NEXT_PIECE_BOX_SIZE - w*NEXT_PIECE_BLOCK_SIZE)//2
        sy = box_y + (NEXT_PIECE_BOX_SIZE - h*NEXT_PIECE_BLOCK_SIZE)//2
        for r_off, c_off in coords:
            pygame.draw.rect(screen,piece.color,(sx+(c_off-min_c)*NEXT_PIECE_BLOCK_SIZE, sy+(r_off-min_r)*NEXT_PIECE_BLOCK_SIZE, NEXT_PIECE_BLOCK_SIZE-1,NEXT_PIECE_BLOCK_SIZE-1))

def draw_full_ui(screen,score,level,lines_total,next_p1,next_p2,lines_curr_lvl,ai_on,time_str,top_scores):
    global SCORE_FONT,INFO_FONT,TITLE_FONT
    if SCORE_FONT is None: SCORE_FONT = load_font(SCORE_FONT_SIZE)
    if INFO_FONT is None: INFO_FONT = load_font(INFO_FONT_SIZE)
    if TITLE_FONT is None: TITLE_FONT = load_font(TITLE_FONT_SIZE)

    curr_y = UI_INFO_START_Y; x_off = game_constants.GRID_OFFSET_X + game_constants.GRID_WIDTH*game_constants.BLOCK_SIZE + UI_INFO_X_OFFSET

    def blit_text(font, text, val_color=WHITE):
        nonlocal curr_y
        if font: surf=font.render(text,True,val_color); screen.blit(surf,(x_off,curr_y)); curr_y+=font.get_height()+UI_INFO_LINE_SPACING
        else: curr_y += 20 + UI_INFO_LINE_SPACING

    blit_text(SCORE_FONT, f"Score: {score}")
    blit_text(INFO_FONT, f"Level: {level}")
    blit_text(INFO_FONT, f"Lines: {lines_total}")
    blit_text(INFO_FONT, f"AI Mode: {'ON' if ai_on else 'OFF'}", GREEN if ai_on else RED)
    blit_text(INFO_FONT, f"Time: {time_str}")

    if INFO_FONT and top_scores and top_scores[0].get("score",0)>0:
        entry=top_scores[0]; blit_text(INFO_FONT,f"Best: {entry['username']} - {entry['score']}",YELLOW)
    elif top_scores and top_scores[0].get("score",0)>0 : curr_y += 20 + UI_INFO_LINE_SPACING # Fallback space

    prog_text_h = INFO_FONT.get_height() if INFO_FONT else 20
    prog_bar_y = curr_y + prog_text_h + 5
    bar_rect = pygame.Rect(x_off, prog_bar_y, PROGRESS_BAR_WIDTH, PROGRESS_BAR_HEIGHT)
    colors = {"bg":PROGRESS_BAR_BACKGROUND_COLOR,"fill":PROGRESS_BAR_FILL_COLOR,"border":PROGRESS_BAR_BORDER_COLOR}
    if INFO_FONT: draw_level_progress_bar(screen,lines_curr_lvl,LINES_PER_LEVEL,bar_rect,colors,INFO_FONT,WHITE)

    curr_y = prog_bar_y + PROGRESS_BAR_HEIGHT + UI_INFO_LINE_SPACING*2
    draw_next_piece_area(screen,next_p1,x_off,curr_y,"Next 1:")
    title_h = TITLE_FONT.get_height() if TITLE_FONT else 20
    curr_y += title_h + 5 + NEXT_PIECE_BOX_SIZE + UI_INFO_LINE_SPACING*2
    draw_next_piece_area(screen,next_p2,x_off,curr_y,"Next 2:")

def draw_level_progress_bar(s,curr,needed,rect,colors,font,txt_color):
    pygame.draw.rect(s,colors['bg'],rect)
    fill_pct = min(1.0,float(curr)/needed) if needed>0 else 0.0
    fill_w = int(fill_pct*rect.width)
    if fill_w>0: pygame.draw.rect(s,colors['fill'],pygame.Rect(rect.x,rect.y,fill_w,rect.height))
    if 'border' in colors: pygame.draw.rect(s,colors['border'],rect,1)
    if font: txt_surf=font.render(f"Progress: {curr}/{needed}",True,txt_color); s.blit(txt_surf,(rect.centerx-txt_surf.get_width()//2, rect.y-txt_surf.get_height()-2))

# ... (rest of the functions like _process_ai_move, _process_animated_hard_drop, etc. would follow)
# For brevity, I'm assuming these functions are largely unchanged from the previous version provided,
# as the UnboundLocalError is specific to the main game loop's event handling.

def _finalize_line_clear(grid_data, lines_to_remove_indices, current_score, level, total_lines, lines_for_lvl):
    lines_to_remove_indices.sort(reverse=True)
    num_cleared = len(lines_to_remove_indices)
    for r_idx in lines_to_remove_indices: del grid_data[r_idx]
    for _ in range(num_cleared): grid_data.insert(0, [0 for _ in range(game_constants.GRID_WIDTH)])
    current_score += get_score_for_lines(num_cleared, level); total_lines += num_cleared
    lines_for_lvl = total_lines % LINES_PER_LEVEL
    new_level_calc = (total_lines // LINES_PER_LEVEL) + 1
    leveled_up = False
    if new_level_calc > level: level = min(new_level_calc, 100); play_sound("level_up"); leveled_up = True
    return {"grid_data": grid_data, "current_score": current_score, "level": level, "total_lines": total_lines, "lines_for_lvl": lines_for_lvl, "leveled_up": leveled_up}

def _render_help_text_surfaces(title_font, section_font, info_font, text_color):
    help_lines_data = [("BlockFall - HELP", title_font), ("", section_font), ("Keyboard Controls:", section_font), ("  Left Arrow:  Move Piece Left", info_font), ("  Right Arrow: Move Piece Right", info_font), ("  Up Arrow:    Rotate Piece", info_font), ("  Down Arrow:  Soft Drop Piece", info_font), ("  Space Bar:   Hard Drop Piece", info_font), ("  P:           Pause / Resume Game", info_font), ("  A:           Toggle AI Mode", info_font), ("  R:           Restart Game (Game Over)", info_font), ("  H:           Show / Hide Help", info_font), ("  ESC:         Quit Game / Close Help", info_font), ("", section_font), ("Joystick Controls (Defaults):", section_font), ("  Analog X / D-Pad X:   Move Left/Right", info_font), ("  Analog Y / D-Pad Y (Down): Soft Drop", info_font), ("  D-Pad Y (Up):         Rotate Piece", info_font), ("  Button 0 (A/X):       Rotate Piece", info_font), ("  Button 1 (B/Circle):  Hard Drop Piece", info_font), ("  Button 7 (Start):     Pause/Resume/Restart", info_font), ("  Button 6 (Select):    Toggle AI Mode", info_font), ("", section_font), ("Press 'H' or 'ESC' to close.", info_font)]
    if not all([title_font, section_font, info_font]): return []
    return [font.render(text, True, text_color) for text, font in help_lines_data]

def _draw_help_screen(screen_surface, help_text_surfaces_list):
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180)); screen_surface.blit(overlay, (0,0))
    total_text_height = sum(s.get_height() for s in help_text_surfaces_list) + (len(help_text_surfaces_list)-1)*5 if help_text_surfaces_list else 0
    current_y = (SCREEN_HEIGHT - total_text_height) // 2
    for surface in help_text_surfaces_list: screen_surface.blit(surface, ((SCREEN_WIDTH - surface.get_width())//2, current_y)); current_y += surface.get_height() + 5

def _draw_high_score_screen(screen_surface, top_scores_list, fonts):
    screen_surface.fill(BLACK)
    title_font, score_font, info_font = fonts.get("title"), fonts.get("score"), fonts.get("info")
    if not all([title_font, score_font, info_font]):
        if DEBUG_MODE: print("DEBUG: Fonts missing for high score screen.");
        temp_font = pygame.font.SysFont(None, 30); surf = temp_font.render("Font Error", True, RED); screen_surface.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
        return
    title_surf = title_font.render("Top 10 Scores", True, WHITE); screen_surface.blit(title_surf, title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200)))
    start_y = title_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 200)).bottom + 40; line_h = score_font.get_height() + 10
    if not top_scores_list: screen_surface.blit(info_font.render("No high scores yet!", True, WHITE), info_font.render("No high scores yet!", True, WHITE).get_rect(center=(SCREEN_WIDTH // 2, start_y + line_h * 2)))
    else:
        cols = {"Rank": SCREEN_WIDTH//2 - 250, "Name": SCREEN_WIDTH//2 - 150, "Score": SCREEN_WIDTH//2 + 100}
        for col_name, x_pos in cols.items(): screen_surface.blit(score_font.render(col_name, True, YELLOW), (x_pos if col_name != "Score" else x_pos + 50 - score_font.render(col_name, True, YELLOW).get_width(), start_y))
        current_y = start_y + line_h
        for i, entry in enumerate(top_scores_list[:10]):
            screen_surface.blit(score_font.render(f"{i+1}.", True, WHITE), (cols["Rank"], current_y))
            screen_surface.blit(score_font.render(entry.get("username", "N/A")[:15], True, WHITE), (cols["Name"], current_y))
            score_val_surf = score_font.render(str(entry.get("score",0)), True, WHITE); screen_surface.blit(score_val_surf, (cols["Score"] + 50 - score_val_surf.get_width(), current_y))
            current_y += line_h
    instr_surf = info_font.render("Press any key to Restart, ESC to Quit", True, WHITE); screen_surface.blit(instr_surf, instr_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)))

def _draw_game_screen(screen_surface, game_grid_data, current_piece_obj, next_piece_1_obj, next_piece_2_obj, score_val, current_level_val, total_lines_cleared_val, lines_for_current_level_val, ai_mode_flag, formatted_time_str, game_over_flag, game_paused_flag, clock_obj, help_screen_active_flag, help_text_surfaces_list, game_phase_str, current_username_str, top_scores_list, lines_being_animated_list, line_animation_timer_val, config_menu_active_flag, sound_effects_enabled_flag, shadow_enabled_flag, line_blink_enabled_flag, music_enabled_flag, current_grid_config_str, config_manager):
    screen_surface.fill(BLACK); draw_grid_lines(screen_surface); draw_blocks(screen_surface, game_grid_data, lines_being_animated_list, line_animation_timer_val, line_blink_enabled_flag)
    if shadow_enabled_flag and not game_over_flag and current_piece_obj and game_phase_str == "PLAYING":
        shadow_y = get_shadow_position_y(current_piece_obj, game_grid_data)
        if current_piece_obj.shape and current_piece_obj.rotation < len(current_piece_obj.shape):
            for r_offset, c_offset in current_piece_obj.shape[current_piece_obj.rotation]:
                if 0 <= shadow_y + r_offset < game_constants.GRID_HEIGHT and 0 <= current_piece_obj.x + c_offset < game_constants.GRID_WIDTH: pygame.draw.rect(screen_surface, GREY, (game_constants.GRID_OFFSET_X + (current_piece_obj.x+c_offset)*game_constants.BLOCK_SIZE, game_constants.GRID_OFFSET_Y + (shadow_y+r_offset)*game_constants.BLOCK_SIZE, game_constants.BLOCK_SIZE-1, game_constants.BLOCK_SIZE-1))
    if not game_over_flag and current_piece_obj and game_phase_str not in ["GETTING_USERNAME", "LINE_ANIMATION"]: draw_current_piece_on_grid(screen_surface, current_piece_obj)
    draw_full_ui(screen_surface, score_val, current_level_val, total_lines_cleared_val, next_piece_1_obj if not game_over_flag else None, next_piece_2_obj if not game_over_flag else None, lines_for_current_level_val, ai_mode_flag, formatted_time_str, top_scores_list)
    font_check = {"GAME_OVER_FONT": GAME_OVER_FONT, "INFO_FONT": INFO_FONT}
    if game_phase_str == "GETTING_USERNAME":
        if all(font_check.values()):
            game_over_surf = GAME_OVER_FONT.render("GAME OVER", True, RED); score_surf = INFO_FONT.render(f"Final Score: {score_val}", True, WHITE)
            screen_surface.blit(game_over_surf, game_over_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - score_surf.get_height()//2 - 40))); screen_surface.blit(score_surf, score_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + game_over_surf.get_height()//2 - 40)))
            prompt_surf = INFO_FONT.render("New Best! Enter Name (Max 15):", True, WHITE); screen_surface.blit(prompt_surf, prompt_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2+40)))
            name_surf = INFO_FONT.render(current_username_str, True, YELLOW); name_rect = name_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2+80)); screen_surface.blit(name_surf, name_rect)
            if time.time()%1 < 0.5: cursor_surf = INFO_FONT.render("_", True, YELLOW); screen_surface.blit(cursor_surf, cursor_surf.get_rect(topleft=(name_rect.right+2 if current_username_str else name_rect.centerx, name_rect.top)))
    elif game_over_flag:
        if all(font_check.values()):
            go_surf = GAME_OVER_FONT.render("GAME OVER", True, RED); fs_surf = INFO_FONT.render(f"Final Score: {score_val}", True, WHITE)
            screen_surface.blit(go_surf, go_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2-fs_surf.get_height()//2))); screen_surface.blit(fs_surf, fs_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2+go_surf.get_height()//2)))
            rs_surf = INFO_FONT.render("Press 'R' to Restart", True, WHITE); qt_surf = INFO_FONT.render("Press 'ESC' to Quit", True, WHITE)
            screen_surface.blit(rs_surf, rs_surf.get_rect(center=(SCREEN_WIDTH//2, fs_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2+go_surf.get_height()//2)).bottom + 20 + rs_surf.get_height()//2)))
            screen_surface.blit(qt_surf, qt_surf.get_rect(center=(SCREEN_WIDTH//2, rs_surf.get_rect(center=(SCREEN_WIDTH//2, fs_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2+go_surf.get_height()//2)).bottom + 20 + rs_surf.get_height()//2)).bottom + 10 + qt_surf.get_height()//2)))
    if game_paused_flag and not game_over_flag and not help_screen_active_flag and not config_menu_active_flag and game_phase_str != "GETTING_USERNAME":
        if GAME_OVER_FONT: screen_surface.blit(GAME_OVER_FONT.render("PAUSED", True, YELLOW), GAME_OVER_FONT.render("PAUSED", True, YELLOW).get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2)))
    if help_screen_active_flag: _draw_help_screen(screen_surface, help_text_surfaces_list)
    elif config_menu_active_flag:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,180)); screen_surface.blit(overlay,(0,0))
        if all(font_check.values()):
            menu_items_y_start = SCREEN_HEIGHT//2 - 140; spacing = 40
            screen_surface.blit(GAME_OVER_FONT.render("CONFIGURATION MENU", True, WHITE), GAME_OVER_FONT.render("CONFIGURATION MENU", True, WHITE).get_rect(center=(SCREEN_WIDTH//2, menu_items_y_start)))
            options = [ (f"Sound FX: {'ON' if sound_effects_enabled_flag else 'OFF'} (S)", sound_effects_enabled_flag), (f"Music: {'ON' if music_enabled_flag else 'OFF'} (M)", music_enabled_flag), (f"Shadow: {'ON' if shadow_enabled_flag else 'OFF'} (D)", shadow_enabled_flag), (f"Line Blink: {'ON' if line_blink_enabled_flag else 'OFF'} (B)", line_blink_enabled_flag), (f"Grid Size: {current_grid_config_str.capitalize()} (G)", current_grid_config_str), (f"Game Mode: {config_manager.get('gamemode','standard').capitalize()} (K)", config_manager.get('gamemode','standard'))]
            for i, (text, _) in enumerate(options): surf = INFO_FONT.render(text, True, WHITE); screen_surface.blit(surf, surf.get_rect(center=(SCREEN_WIDTH//2, menu_items_y_start + (i+1.5)*spacing)))
            hint_y_base = menu_items_y_start + (len(options)+1.5)*spacing
            screen_surface.blit(INFO_FONT.render("Restart game for some settings to apply.", True, GREY), INFO_FONT.render("Restart game for some settings to apply.", True, GREY).get_rect(center=(SCREEN_WIDTH//2, hint_y_base + spacing*0.5)))
            screen_surface.blit(INFO_FONT.render("Press C or ESC to close", True, GREY), INFO_FONT.render("Press C or ESC to close", True, GREY).get_rect(center=(SCREEN_WIDTH//2, hint_y_base + spacing*1.5)))
    elif game_phase_str == "HIGH_SCORE_DISPLAY": _draw_high_score_screen(screen_surface, top_scores_list, {"title":GAME_OVER_FONT, "score":INFO_FONT, "info":INFO_FONT})
    pygame.display.flip()
    if clock_obj: clock_obj.tick(60)

def main():
    parser = argparse.ArgumentParser(description="BlockFall Game with an AI player option."); parser.add_argument("--debug", action="store_true", help="Enable debug logging to console."); args = parser.parse_args()
    global DEBUG_MODE;
    if args.debug: DEBUG_MODE = True; print("DEBUG MODE ENABLED")
    set_cm_debug_mode(DEBUG_MODE)
    config_manager = ConfigManager(config_file_path="config.json")
    config_grid_size = config_manager.get("grid_size", "normal")
    if config_grid_size == "large": game_constants.GRID_WIDTH, game_constants.GRID_HEIGHT = game_constants.GRID_WIDTH_LARGE, game_constants.GRID_HEIGHT_LARGE
    else: game_constants.GRID_WIDTH, game_constants.GRID_HEIGHT = game_constants.GRID_WIDTH_NORMAL, game_constants.GRID_HEIGHT_NORMAL
    game_constants.GRID_OFFSET_X = (game_constants.SCREEN_WIDTH - game_constants.GRID_WIDTH * game_constants.BLOCK_SIZE) // 2
    game_constants.GRID_OFFSET_Y = (game_constants.SCREEN_HEIGHT - game_constants.GRID_HEIGHT * game_constants.BLOCK_SIZE) // 2

    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS, sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled
    loaded_config = config_manager.get_all()
    sound_effects_enabled = loaded_config.get("sound_effects_enabled", True); shadow_enabled = loaded_config.get("shadow_enabled", True)
    line_blink_enabled = loaded_config.get("line_blink_enabled", True); music_enabled = loaded_config.get("music_enabled", True)

    SCORE_FONT = load_font(SCORE_FONT_SIZE); INFO_FONT = load_font(INFO_FONT_SIZE)
    TITLE_FONT = load_font(TITLE_FONT_SIZE); GAME_OVER_FONT = load_font(GAME_OVER_FONT_SIZE)

    help_text_surfaces = _render_help_text_surfaces(GAME_OVER_FONT, SCORE_FONT, INFO_FONT, WHITE)
    top_scores_list = _load_best_score()

    background_music_loaded = False
    if os.path.isdir(SOUND_DIR):
        try:
            music_path = os.path.join(SOUND_DIR, "background_01.mp3")
            if os.path.exists(music_path): pygame.mixer.music.load(music_path); background_music_loaded = True
        except pygame.error as e: print(f"DEBUG: Error loading music: {e}" if DEBUG_MODE else "")

    if not os.path.isdir(SOUND_DIR): print(f"Sound directory '{SOUND_DIR}' not found.")
    else:
        for effect, filename in [("move","move.wav"), ("rotate","rotate.wav"), ("drop","drop.wav"), ("line_clear","line_clear.wav"), ("blockfall_clear","blockfall_clear.wav"), ("level_up","level_up.wav"), ("game_over","game_over.wav")]:
            SOUND_EFFECTS[effect] = load_sound(filename)

    if background_music_loaded and music_enabled: pygame.mixer.music.set_volume(0.5); pygame.mixer.music.play(loops=-1)

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT)); pygame.display.set_caption(SCREEN_TITLE)
    joystick = None; joystick_enabled = False
    if pygame.joystick.get_count() > 0: joystick = pygame.joystick.Joystick(0); joystick.init(); joystick_enabled = True; print(f"Joystick: {joystick.get_name()}")
    else: print("No joystick.")

    clock = pygame.time.Clock()
    game_state_vars = reset_game_state(config_manager.get("gamemode", "standard"))
    (game_grid, current_piece, next_piece_1, next_piece_2, score, current_level, total_lines_cleared,
     lines_for_current_level, game_over, current_fall_speed, last_fall_time, soft_drop_active,
     game_over_sound_played, ai_mode_active, last_ai_move_time, game_start_time,
     final_game_time_str, game_paused, time_at_pause, total_paused_duration) = _unpack_game_state(game_state_vars)

    running = True; help_screen_active = False; config_menu_active = False
    game_phase = "PLAYING"; current_username_input = ""; formatted_time = ""
    lines_being_animated = []; line_animation_timer = 0
    action_request = None # Initialize action_request before the loop

    while running:
        events = pygame.event.get()
        event_handling_result = _handle_events(events, game_over, game_paused, ai_mode_active, soft_drop_active, current_piece, game_grid, running, time_at_pause, total_paused_duration, last_fall_time, last_ai_move_time, joystick, joystick_enabled, help_screen_active, game_phase, current_username_input, config_menu_active, sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled, config_manager)

        # Explicitly unpack results
        running = event_handling_result["running"]
        game_paused = event_handling_result["game_paused"]
        ai_mode_active = event_handling_result["ai_mode_active"]
        soft_drop_active = event_handling_result["soft_drop_active"]
        current_piece = event_handling_result["current_piece"] # Can be None
        time_at_pause = event_handling_result["time_at_pause"]
        total_paused_duration = event_handling_result["total_paused_duration"]
        last_fall_time = event_handling_result["last_fall_time"]
        last_ai_move_time = event_handling_result["last_ai_move_time"]
        action_request = event_handling_result["action_request"] # This is the important one
        help_screen_active = event_handling_result["help_screen_active"]
        config_menu_active = event_handling_result["config_menu_active"]
        sound_effects_enabled = event_handling_result["sound_effects_enabled"]
        shadow_enabled = event_handling_result["shadow_enabled"]
        line_blink_enabled = event_handling_result["line_blink_enabled"]
        music_enabled = event_handling_result["music_enabled"]
        current_username_input = event_handling_result["current_username_input"]
        # game_phase is also in event_handling_result but often set by game logic below, ensure consistency if needed

        current_piece_set_type = config_manager.get("gamemode", "standard")
        if background_music_loaded:
            if music_enabled and not pygame.mixer.music.get_busy(): pygame.mixer.music.unpause(); pygame.mixer.music.play(loops=-1)
            elif not music_enabled and pygame.mixer.music.get_busy(): pygame.mixer.music.pause()
        if not running: break

        if action_request == "RESTART":
            game_state_vars = reset_game_state(current_piece_set_type)
            (game_grid, current_piece, next_piece_1, next_piece_2, score, current_level, total_lines_cleared, lines_for_current_level, game_over, current_fall_speed, last_fall_time, soft_drop_active, game_over_sound_played, ai_mode_active, last_ai_move_time, game_start_time, final_game_time_str, game_paused, time_at_pause, total_paused_duration) = _unpack_game_state(game_state_vars)
            formatted_time = ""; help_screen_active = False; game_phase = "PLAYING"; current_username_input = ""; lines_being_animated = []; line_animation_timer = 0
            action_request = None
            continue

        if action_request == "SAVE_SCORE":
            _update_and_save_top_scores({"username": current_username_input, "score": score, "time_str": final_game_time_str or formatted_time})
            top_scores_list = _load_best_score(); game_phase = "HIGH_SCORE_DISPLAY"; current_username_input = ""; action_request = None
        elif action_request == "SKIP_SAVE":
            game_phase = "HIGH_SCORE_DISPLAY"; current_username_input = ""; action_request = None

        prev_game_over = game_over
        game_logic_result = _update_game_state(game_over, game_paused, ai_mode_active, current_piece, next_piece_1, next_piece_2, game_grid, score, current_level, total_lines_cleared, lines_for_current_level, current_fall_speed, last_fall_time, soft_drop_active, game_over_sound_played, last_ai_move_time, game_start_time, final_game_time_str, total_paused_duration, time_at_pause, help_screen_active, game_phase, lines_being_animated, line_animation_timer, line_blink_enabled, current_piece_set_type)
        # Explicitly unpack results from game_logic_result
        game_over = game_logic_result["game_over"]; current_piece = game_logic_result["current_piece"] # Can be None
        next_piece_1 = game_logic_result["next_piece_1"]; next_piece_2 = game_logic_result["next_piece_2"]
        game_grid = game_logic_result["game_grid"]; score = game_logic_result["score"]; current_level = game_logic_result["current_level"]
        total_lines_cleared = game_logic_result["total_lines_cleared"]; lines_for_current_level = game_logic_result["lines_for_current_level"]
        current_fall_speed = game_logic_result["current_fall_speed"]; last_fall_time = game_logic_result["last_fall_time"]
        soft_drop_active = game_logic_result["soft_drop_active"]; game_over_sound_played = game_logic_result["game_over_sound_played"]
        last_ai_move_time = game_logic_result["last_ai_move_time"]; final_game_time_str = game_logic_result["final_game_time_str"]
        formatted_time = game_logic_result["formatted_time"]; game_phase = game_logic_result["game_phase_str"]
        lines_being_animated = game_logic_result["lines_being_animated"]; line_animation_timer = game_logic_result["line_animation_timer"]
        ai_mode_active = game_logic_result["ai_mode_active"]; # Ensure all returned state is updated
        game_paused = game_logic_result["game_paused"]; # Ensure all returned state is updated

        if game_over and not prev_game_over:
            is_top_score = len(top_scores_list) < 10 or (score > 0 and score > top_scores_list[-1].get("score",0))
            if score > 0 and is_top_score: game_phase = "GETTING_USERNAME"; current_username_input = ""
            else: game_phase = "HIGH_SCORE_DISPLAY"

        _draw_game_screen(screen, game_grid, current_piece, next_piece_1, next_piece_2, score, current_level, total_lines_cleared, lines_for_current_level, ai_mode_active, formatted_time, game_over, game_paused, clock, help_screen_active, help_text_surfaces, game_phase, current_username_input, top_scores_list, lines_being_animated, line_animation_timer, config_menu_active, sound_effects_enabled, shadow_enabled, line_blink_enabled, music_enabled, config_manager.get("grid_size","normal"), config_manager)

    if background_music_loaded: pygame.mixer.music.stop()
    pygame.mixer.quit(); pygame.font.quit(); pygame.quit()

if __name__ == '__main__':
    main()
