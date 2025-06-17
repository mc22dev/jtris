import random
from .constants import SHAPES, PIECE_COLORS

class Piece:
    def __init__(self, x, y, shape_type=None, is_valid_position_func=None, play_sound_func=None): # Allow forcing shape_type for next_piece
        self.is_valid_position = is_valid_position_func
        self.play_sound = play_sound_func

        if shape_type is None:
            self.shape_type = random.randint(0, len(SHAPES) - 1)
        else:
            self.shape_type = shape_type
        self.shape = SHAPES[self.shape_type]
        self.color = PIECE_COLORS[self.shape_type]
        self.rotation = 0
        self.x = x # Grid column for current piece, or abstract for next piece
        self.y = y # Grid row for current piece
        self.is_hard_dropping_animated = False # True if piece is currently in animated hard drop
        self.target_y_for_animated_drop = -1   # Stores the target Y row for the animated hard drop

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
        if not self.is_valid_position(self, grid_data): # Use passed in function
            self.rotation = original_rotation
        else:
            if self.play_sound: # Check if function is provided
                self.play_sound("rotate")
