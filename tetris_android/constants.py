import pygame

# Screen dimensions
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
SCREEN_TITLE = "Tetris"

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
YELLOW = (255, 255, 0)
MAGENTA = (255, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
GREY = (128, 128, 128)
GARBAGE_COLOR = (100, 100, 100)

# Piece definitions
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
GRID_WIDTH_NORMAL = 10
GRID_HEIGHT_NORMAL = 20
GRID_WIDTH_LARGE = 20
GRID_HEIGHT_LARGE = 25

# Default to normal size
GRID_WIDTH = GRID_WIDTH_NORMAL
GRID_HEIGHT = GRID_HEIGHT_NORMAL
BLOCK_SIZE = 30 # Main game block size
NEXT_PIECE_BLOCK_SIZE = 20 # Smaller blocks for next piece display

# Calculated UI layout constants (dependent on above)
GRID_OFFSET_X = (SCREEN_WIDTH - GRID_WIDTH * BLOCK_SIZE) // 2
GRID_OFFSET_Y = (SCREEN_HEIGHT - GRID_HEIGHT * BLOCK_SIZE) // 2

# UI variables
UI_INFO_X_OFFSET = 20 # From right edge of grid
UI_INFO_START_Y = GRID_OFFSET_Y + 20
UI_INFO_LINE_SPACING = 10
NEXT_PIECE_BOX_SIZE = 5 * NEXT_PIECE_BLOCK_SIZE # Accommodate 4x4 piece + padding

# Font sizes
SCORE_FONT_SIZE = 36
INFO_FONT_SIZE = 30
TITLE_FONT_SIZE = 24
GAME_OVER_FONT_SIZE = 72

# Animation
LINE_ANIMATION_DURATION = 30  # Frames, approx 0.5s at 60fps

# Progress Bar UI Constants
PROGRESS_BAR_WIDTH = 150 # Width of the level progress bar in pixels
PROGRESS_BAR_HEIGHT = 20 # Height of the level progress bar in pixels
PROGRESS_BAR_BACKGROUND_COLOR = (50, 50, 50) # Dark Grey
PROGRESS_BAR_FILL_COLOR = GREEN
PROGRESS_BAR_BORDER_COLOR = GREY

# Game variables
INITIAL_FALL_SPEED = 0.8
FALL_SPEED_DECREMENT_PER_LEVEL = 0.03
MIN_FALL_SPEED = 0.05
LINES_PER_LEVEL = 10
GARBAGE_START_LEVEL = 3
MAX_GARBAGE_ROWS = 5

# Keys and timing
AI_PLAYER_TOGGLE_KEY = pygame.K_a
RESTART_KEY = pygame.K_r
PAUSE_KEY = pygame.K_p
AI_MOVE_DELAY = 0.05
