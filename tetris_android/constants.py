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

# Pentomino definitions
# Each piece is defined by a list of shapes, where each shape is a list of (row, col) offsets from a pivot.
# The pivot is typically (0,0) in the coordinate set of each rotation.
# Rotations are defined to match common representations.
# For chiral pieces (F, L, N, P, Y, Z), all 8 orientations (4 rotations + 4 mirrored rotations) are listed if distinct.
# For other pieces, all distinct rotations are listed.

# Colors for Pentominoes - 12 distinct colors
PENTOMINO_PIECE_COLORS = [
    (255, 0, 0),      # Red (F)
    (0, 255, 0),      # Green (I)
    (0, 0, 255),      # Blue (L)
    (255, 255, 0),    # Yellow (P)
    (255, 0, 255),    # Magenta (N)
    (0, 255, 255),    # Cyan (T)
    (255, 165, 0),    # Orange (U)
    (128, 0, 128),    # Purple (V)
    (255, 192, 203),  # Pink (W)
    (165, 42, 42),    # Brown (X)
    (128, 128, 128),  # Grey (Y)
    (255, 215, 0)     # Gold (Z)
]

PENTOMINO_SHAPES = [
    # F (8 orientations) - Pivot: center block of the 'cross' part (0,0)
    [
        [(0, -1), (0, 0), (1, 0), (0, 1), (-1, 1)],  # F
        [(-1, -1), (0, -1), (0, 0), (1, 0), (0, 1)], # F rotated 90 deg clockwise
        [(0, -1), (-1, 0), (0, 0), (0, 1), (1, -1)], # F rotated 180 deg
        [(0, -1), (1, -1), (0, 0), (-1, 0), (0, 1)], # F rotated 270 deg clockwise
        # Mirrored F (F')
        [(0, -1), (0, 0), (-1, 0), (0, 1), (1, 1)],  # F'
        [(0, -1), (1, -1), (0, 0), (0, 1), (-1, -1)],# F' rotated 90 deg
        [(0, -1), (1, 0), (0, 0), (0, 1), (-1, -1)], # F' rotated 180 deg
        [(-1, 1), (0, 1), (0, 0), (1, 0), (0, -1)]   # F' rotated 270 deg
    ],
    # I (2 orientations) - Pivot: middle block (0,0)
    [
        [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0)], # I vertical
        [(0, -2), (0, -1), (0, 0), (0, 1), (0, 2)]  # I horizontal
    ],
    # L (8 orientations) - Pivot: corner of L (0,0)
    [
        [(-2,0), (-1,0), (0,0), (0,1), (0,2)], # L (long part up, short part right)
        [(-2,-1), (-1,-1), (0,-1), (0,0), (0,1)], # L 90 deg clockwise
        [(2,0), (1,0), (0,0), (0,-1), (0,-2)], # L 180 deg
        [(2,1), (1,1), (0,1), (0,0), (0,-1)], # L 270 deg clockwise
        # Mirrored L (J)
        [(-2,0), (-1,0), (0,0), (0,-1), (0,-2)], # J (long part up, short part left)
        [(2,-1), (1,-1), (0,-1), (0,0), (0,1)],  # J 90 deg
        [(2,0), (1,0), (0,0), (0,1), (0,2)],    # J 180 deg
        [(-2,1), (-1,1), (0,1), (0,0), (0,-1)]   # J 270 deg
    ],
    # P (8 orientations) - Pivot: (0,0) on the 2x2 block corner
    [
        [(0,0), (1,0), (0,1), (1,1), (0,2)],    # P (2x2 top left, 1 hanging down from left)
        [(0,0), (1,0), (0,-1), (1,-1), (-1,0)], # P 90 deg
        [(0,0), (-1,0), (0,-1), (-1,-1), (0,-2)],# P 180 deg
        [(0,0), (-1,0), (0,1), (-1,1), (1,0)],  # P 270 deg
        # Mirrored P (Q)
        [(0,0), (1,0), (0,1), (1,1), (1,2)],    # Q (2x2 top left, 1 hanging down from right)
        [(0,0), (0,-1), (1,-1), (1,0), (2,0)],  # Q 90 deg
        [(0,0), (0,-1), (-1,-1), (-1,0), (-1,-2)],# Q 180 deg
        [(0,0), (0,1), (-1,1), (-1,0), (-2,0)]  # Q 270 deg
    ],
    # N (8 orientations) - Pivot: 'center' kink (0,0)
    [
        [(1, -1), (0, -1), (0, 0), (-1, 0), (-1, 1)], # N
        [(-1, -1), (-1, 0), (0, 0), (0, 1), (1, 1)], # N 90 deg
        [(-1, 1), (0, 1), (0, 0), (1, 0), (1, -1)],  # N 180 deg
        [(1, 1), (1, 0), (0, 0), (0, -1), (-1, -1)], # N 270 deg
        # Mirrored N (N')
        [(-1, -1), (0, -1), (0, 0), (1, 0), (1, 1)],  # N'
        [(1, -1), (1, 0), (0, 0), (0, 1), (-1, 1)],  # N' 90 deg
        [(1, 1), (0, 1), (0, 0), (-1, 0), (-1, -1)], # N' 180 deg
        [(-1, 1), (-1, 0), (0, 0), (0, -1), (1, -1)] # N' 270 deg
    ],
    # T (4 orientations) - Pivot: center of crossbar (0,0) (where the three blocks meet)
    [
        [(-1, 0), (0, 0), (1, 0), (0, -1), (0, 1)], # T (original tetris T + one block on top of center) -> this is actually a cross shape, not T pentomino
        # Correct T-pentomino: ### with one below middle
        #                  #
        [(-1,0), (0,0), (1,0), (0,1), (0,2)], # T shape down
        [(0,-1), (0,0), (0,1), (-1,0), (-2,0)], # T shape left
        [(1,0), (0,0), (-1,0), (0,-1), (0,-2)], # T shape up
        [(0,1), (0,0), (0,-1), (1,0), (2,0)]  # T shape right
    ],
    # U (4 orientations) - Pivot: center of the 'bottom' of U (0,0)
    [
        [(-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)], # U shape
        [ (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)], # U 90 deg
        [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0)],# U 180 deg
        [(-1,-1), (-1,0), (-1,1), (0,-1), (0,1)]     # U 270 deg
    ],
    # V (4 orientations) - Pivot: corner (0,0)
    [
        [(0,0), (0,1), (0,2), (1,2), (2,2)], # V shape (L shape with one attached to the end of short arm)
        [(0,0), (1,0), (2,0), (2,-1), (2,-2)],# V 90 deg
        [(0,0), (0,-1), (0,-2), (-1,-2), (-2,-2)],# V 180 deg
        [(0,0), (-1,0), (-2,0), (-2,1), (-2,2)] # V 270 deg
    ],
    # W (4 orientations) - Pivot: 'center' lower block (0,0)
    [
        [(-1, -1), (0, -1), (0, 0), (1, 0), (1, 1)], # W
        [(-1, 1), (-1, 0), (0, 0), (0, -1), (1, -1)],# W 90 deg
        [(1, 1), (0, 1), (0, 0), (-1, 0), (-1, -1)], # W 180 deg
        [(1, -1), (1, 0), (0, 0), (0, 1), (-1, 1)]   # W 270 deg
    ],
    # X (1 orientation) - Pivot: center (0,0)
    [
        [(-1, 0), (0, -1), (0, 0), (0, 1), (1, 0)]  # X (cross shape)
    ],
    # Y (8 orientations) - Pivot: center of long bar (0,0)
    [
        [(-2,0), (-1,0), (0,0), (1,0), (0,1)],   # Y (4-line with one off center)
        [(0,-2), (0,-1), (0,0), (0,1), (1,0)],   # Y 90
        [(2,0), (1,0), (0,0), (-1,0), (0,-1)], # Y 180
        [(0,2), (0,1), (0,0), (0,-1), (-1,0)], # Y 270
        # Mirrored Y (Y')
        [(-2,0), (-1,0), (0,0), (1,0), (0,-1)],  # Y'
        [(0,2), (0,1), (0,0), (0,-1), (1,0)],  # Y' 90
        [(2,0), (1,0), (0,0), (-1,0), (0,1)],  # Y' 180
        [(0,-2), (0,-1), (0,0), (0,1), (-1,0)]   # Y' 270
    ],
    # Z (4 orientations - 2 distinct shapes due to point symmetry) - Pivot: center of middle bar (0,0)
    [
        [(-1, -1), (0, -1), (0, 0), (0, 1), (1, 1)], # Z pentomino
        [(-1, 1), (-1, 0), (0, 0), (1, 0), (1, -1)], # Z 90 deg
        # Mirrored Z (S-pentomino)
        [(1, -1), (0, -1), (0, 0), (0, 1), (-1, 1)], # S (Z mirrored)
        [(1, 1), (1, 0), (0, 0), (-1, 0), (-1, -1)]  # S 90 deg (Z mirrored 90 deg)
    ]
]
