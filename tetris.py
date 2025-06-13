import pygame
import random
import time
import os

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
    if TITLE_FONT is None: TITLE_FONT = pygame.font.SysFont("Arial", TITLE_FONT_SIZE)

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


def draw_full_ui(screen, score, level, lines_cleared_total, next_p):
    global SCORE_FONT, INFO_FONT
    if SCORE_FONT is None: SCORE_FONT = pygame.font.SysFont("Arial", SCORE_FONT_SIZE)
    if INFO_FONT is None: INFO_FONT = pygame.font.SysFont("Arial", INFO_FONT_SIZE)

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
    current_y += INFO_FONT_SIZE + UI_INFO_LINE_SPACING * 2

    draw_next_piece_area(screen, next_p, ui_start_x, current_y)


def main():
    global SCORE_FONT, INFO_FONT, TITLE_FONT, GAME_OVER_FONT, SOUND_EFFECTS
    SCORE_FONT = pygame.font.SysFont("Arial", SCORE_FONT_SIZE); INFO_FONT = pygame.font.SysFont("Arial", INFO_FONT_SIZE)
    TITLE_FONT = pygame.font.SysFont("Arial", TITLE_FONT_SIZE); GAME_OVER_FONT = pygame.font.SysFont("Arial", GAME_OVER_FONT_SIZE)

    if not os.path.isdir(SOUND_DIR): print(f"Sound directory '{SOUND_DIR}' not found.") # Check isdir
    else:
        SOUND_EFFECTS["move"]=load_sound("move.wav"); SOUND_EFFECTS["rotate"]=load_sound("rotate.wav")
        SOUND_EFFECTS["drop"]=load_sound("drop.wav"); SOUND_EFFECTS["line_clear"]=load_sound("line_clear.wav")
        SOUND_EFFECTS["tetris_clear"]=load_sound("tetris_clear.wav"); SOUND_EFFECTS["level_up"]=load_sound("level_up.wav")
        SOUND_EFFECTS["game_over"]=load_sound("game_over.wav")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption(SCREEN_TITLE)

    game_grid = create_grid(); score = 0; current_level = 1; total_lines_cleared = 0

    current_piece = spawn_piece_at_start()
    next_piece = Piece(0,0)

    game_over = False
    if not is_valid_position(current_piece, game_grid): game_over = True; current_piece = None

    last_fall_time = time.time(); current_fall_speed = calculate_fall_speed(current_level)
    soft_drop_active = False; running = True; clock = pygame.time.Clock()
    game_over_sound_played = False


    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            if not game_over and current_piece:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP: current_piece.rotate(game_grid)
                    elif event.key == pygame.K_LEFT:
                        current_piece.x -= 1
                        if not is_valid_position(current_piece, game_grid): current_piece.x += 1
                        else: play_sound("move")
                    elif event.key == pygame.K_RIGHT:
                        current_piece.x += 1
                        if not is_valid_position(current_piece, game_grid): current_piece.x -= 1
                        else: play_sound("move")
                    elif event.key == pygame.K_DOWN: soft_drop_active = True
                    elif event.key == pygame.K_SPACE:
                        while is_valid_position(current_piece, game_grid, check_y_offset=1): current_piece.y += 1
                        add_to_grid(current_piece, game_grid)
                        lines_this_drop = check_and_clear_lines(game_grid)
                        if lines_this_drop > 0:
                            score += get_score_for_lines(lines_this_drop, current_level); total_lines_cleared += lines_this_drop
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

                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN: soft_drop_active = False

        if not game_over and current_piece: # Automatic piece descent
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

        draw_full_ui(screen, score, current_level, total_lines_cleared, next_piece if not game_over else None)

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
