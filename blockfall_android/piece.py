import random
from .constants import SHAPES, PIECE_COLORS, PENTOMINO_SHAPES, PENTOMINO_PIECE_COLORS

class Piece:
    def __init__(self, x, y, shape_type=None, is_valid_position_func=None, play_sound_func=None, piece_set_type="standard"): # Allow forcing shape_type for next_piece
        self.is_valid_position = is_valid_position_func
        self.play_sound = play_sound_func
        self.piece_set_type = piece_set_type

        current_shapes = SHAPES
        current_colors = PIECE_COLORS
        if self.piece_set_type == "pentomino":
            current_shapes = PENTOMINO_SHAPES
            current_colors = PENTOMINO_PIECE_COLORS

        if shape_type is None:
            self.shape_type = random.randint(0, len(current_shapes) - 1)
        else:
            self.shape_type = shape_type

        # Ensure shape_type is valid for the chosen set, especially if forced (e.g. for next_piece preview)
        if self.shape_type >= len(current_shapes):
            # Fallback or error: For now, default to the first shape of the current set if out of bounds
            # This might happen if shape_type was for standard (0-6) but piece_set_type is pentomino (0-11)
            # or vice-versa, or if an invalid shape_type is passed.
            # A more robust solution might be needed depending on how shape_type is used for next_piece
            # when switching modes. For now, let's pick a valid random one from the current set.
            print(f"Warning: shape_type {shape_type} is out of bounds for piece_set_type '{self.piece_set_type}'. Resetting to random.")
            self.shape_type = random.randint(0, len(current_shapes) - 1)

        self.shape = current_shapes[self.shape_type]
        self.color = current_colors[self.shape_type]
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
