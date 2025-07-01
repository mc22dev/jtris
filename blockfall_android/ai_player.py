from .piece import Piece
from . import constants as game_constants

HEURISTIC_WEIGHTS = {
    'aggregate_height': -0.510066,
    'cleared_lines': 0.760666,
    'holes': -0.35663,
    'bumpiness': -0.184483,
}

def clone_grid(grid_data):
    """Creates and returns a deep copy of the given game grid."""
    return [row[:] for row in grid_data]

def _get_cleared_lines_and_new_grid(grid_copy_to_check):
    """
    Checks for completed lines on a given grid copy and returns the number of lines
    cleared AND the grid state after clearing those lines.
    """
    lines_cleared_count = 0
    grid_after_clearing = [row[:] for row in grid_copy_to_check]
    r = game_constants.GRID_HEIGHT - 1
    while r >= 0:
        is_line_full = True
        for c in range(game_constants.GRID_WIDTH):
            if grid_after_clearing[r][c] == 0:
                is_line_full = False
                break
        if is_line_full:
            lines_cleared_count += 1
            del grid_after_clearing[r]
            grid_after_clearing.insert(0, [0 for _ in range(game_constants.GRID_WIDTH)])
        else:
            r -= 1
    return lines_cleared_count, grid_after_clearing

def simulate_place_piece(grid_to_simulate_on, piece_to_simulate, target_x, target_rotation, is_valid_position_func, play_sound_func): # Removed piece_set_type parameter
    """
    Simulates placing a piece at a given x and rotation on a (deep)copy of the grid.
    Performs a hard drop and calculates the outcome.
    """
    sim_grid_current_move = clone_grid(grid_to_simulate_on)
    if not piece_to_simulate: # Safety check
        return None, 0, -1, False

    temp_piece = Piece(target_x, 0, shape_type=piece_to_simulate.shape_type,
                       is_valid_position_func=is_valid_position_func,
                       play_sound_func=play_sound_func,
                       piece_set_type=piece_to_simulate.piece_set_type) # Use piece_to_simulate's type
    temp_piece.rotation = target_rotation
    temp_piece.x = target_x

    min_r_offset = 0
    current_shape_blocks = temp_piece.shape[temp_piece.rotation]
    if current_shape_blocks:
        min_r_offset = min(r for r, c in current_shape_blocks)
    temp_piece.y = -min_r_offset

    if not is_valid_position_func(temp_piece, sim_grid_current_move): # Use passed function
        return None, 0, -1, False

    landing_y = temp_piece.y
    while True:
        temp_piece.y += 1
        if not is_valid_position_func(temp_piece, sim_grid_current_move): # Use passed function
            temp_piece.y -= 1
            landing_y = temp_piece.y
            break

    for r_offset, c_offset in current_shape_blocks:
        block_r, block_c = landing_y + r_offset, temp_piece.x + c_offset
        if 0 <= block_r < game_constants.GRID_HEIGHT and 0 <= block_c < game_constants.GRID_WIDTH:
            sim_grid_current_move[block_r][block_c] = temp_piece.color

    lines_cleared, grid_after_clear = _get_cleared_lines_and_new_grid(sim_grid_current_move)
    return grid_after_clear, lines_cleared, landing_y, True

def evaluate_board_state(grid, lines_cleared_by_move):
    """
    Evaluates the given board state based on several heuristics.
    A higher score is better.
    """
    score = 0
    aggregate_height = 0
    column_heights = [0] * game_constants.GRID_WIDTH
    for c in range(game_constants.GRID_WIDTH):
        for r in range(game_constants.GRID_HEIGHT):
            if grid[r][c] != 0:
                column_heights[c] = game_constants.GRID_HEIGHT - r
                break
        aggregate_height += column_heights[c]
    score += HEURISTIC_WEIGHTS['aggregate_height'] * aggregate_height
    score += HEURISTIC_WEIGHTS['cleared_lines'] * lines_cleared_by_move

    holes = 0
    for c in range(game_constants.GRID_WIDTH):
        block_above_found = False
        for r in range(game_constants.GRID_HEIGHT):
            if grid[r][c] != 0:
                block_above_found = True
            elif block_above_found and grid[r][c] == 0:
                holes += 1
    score += HEURISTIC_WEIGHTS['holes'] * holes

    bumpiness = 0
    for c in range(game_constants.GRID_WIDTH - 1):
        bumpiness += abs(column_heights[c] - column_heights[c+1])
    score += HEURISTIC_WEIGHTS['bumpiness'] * bumpiness
    return score

def find_best_move(grid_data, current_piece_obj, next_piece_1_obj, next_piece_2_obj, is_valid_position_func, play_sound_func, piece_set_type="standard"):
    """
    Finds the best move (column and rotation) for the current piece,
    considering the placement of the next piece.
    """
    best_score = -float('inf')
    best_x = -1
    best_rotation = -1
    best_landing_y = -1

    if not current_piece_obj: # Added safety check
        return {'x': best_x, 'rotation': best_rotation, 'score': best_score, 'landing_y': best_landing_y}

    # The piece_set_type parameter for find_best_move is for the current game mode (e.g. for next piece eval)
    # For simulating the current_piece_obj, we must use its own piece_set_type.
    for rotation_idx in range(len(current_piece_obj.shape)):
        temp_eval_piece = Piece(0, 0, shape_type=current_piece_obj.shape_type,
                                is_valid_position_func=is_valid_position_func,
                                play_sound_func=play_sound_func,
                                piece_set_type=current_piece_obj.piece_set_type) # Use current_piece_obj's own type
        temp_eval_piece.rotation = rotation_idx
        current_shape_blocks = temp_eval_piece.shape[temp_eval_piece.rotation]
        min_c_offset_for_shape = 0
        max_c_offset_for_shape = 0
        if current_shape_blocks:
            min_c_offset_for_shape = min(c for r,c in current_shape_blocks)
            max_c_offset_for_shape = max(c for r,c in current_shape_blocks)

        for x_col in range(-min_c_offset_for_shape, game_constants.GRID_WIDTH - max_c_offset_for_shape):
            grid_copy = clone_grid(grid_data)
            # current_piece_obj is passed to simulate_place_piece, which will use its piece_set_type
            resulting_grid, lines_cleared, landing_y, is_possible = \
                simulate_place_piece(grid_copy, current_piece_obj, x_col, rotation_idx, is_valid_position_func, play_sound_func)

            if is_possible:
                # Score for the current piece's placement
                score_after_current_piece = evaluate_board_state(resulting_grid, lines_cleared)

                current_total_score = score_after_current_piece

                # Now, consider the next_piece_1_obj
                if next_piece_1_obj:
                    best_score_after_next_1 = -float('inf')
                    best_grid_after_next_1 = None

                    for rotation_idx_next_1 in range(len(next_piece_1_obj.shape)):
                        temp_eval_piece_next_1 = Piece(0, 0, shape_type=next_piece_1_obj.shape_type,
                                                       is_valid_position_func=is_valid_position_func,
                                                       play_sound_func=play_sound_func,
                                                       piece_set_type=next_piece_1_obj.piece_set_type)
                        temp_eval_piece_next_1.rotation = rotation_idx_next_1
                        current_shape_blocks_next_1 = temp_eval_piece_next_1.shape[temp_eval_piece_next_1.rotation]
                        min_c_offset_next_1 = 0
                        max_c_offset_next_1 = 0
                        if current_shape_blocks_next_1:
                            min_c_offset_next_1 = min(c for r, c in current_shape_blocks_next_1)
                            max_c_offset_next_1 = max(c for r, c in current_shape_blocks_next_1)

                        for x_col_next_1 in range(-min_c_offset_next_1, game_constants.GRID_WIDTH - max_c_offset_next_1):
                            # Simulate placing next_piece_1_obj on the 'resulting_grid' (grid after current_piece_obj)
                            grid_after_current_piece_copy = clone_grid(resulting_grid)
                            resulting_grid_next_1, lines_cleared_next_1, _, is_possible_next_1 = \
                                simulate_place_piece(grid_after_current_piece_copy, next_piece_1_obj, x_col_next_1, rotation_idx_next_1, is_valid_position_func, play_sound_func)

                            if is_possible_next_1:
                                score_next_1_move = evaluate_board_state(resulting_grid_next_1, lines_cleared_next_1)
                                if score_next_1_move > best_future_score:
                                    best_future_score = score_next_1_move

                    if best_future_score != -float('inf'):
                        # Add the weighted score of the best outcome for next_piece_1_obj
                        # The weight (e.g., 0.5) can be tuned. A smaller weight means less emphasis on future pieces.
                        current_total_score += 0.5 * best_future_score

                if current_total_score > best_score:
                    best_score = current_total_score
                    best_x = x_col
                    best_rotation = rotation_idx
                    best_landing_y = landing_y
                elif current_total_score == best_score:  # Corrected variable name here
                    if landing_y > best_landing_y:
                        best_x = x_col
                        best_rotation = rotation_idx
                        best_landing_y = landing_y
    return {'x': best_x, 'rotation': best_rotation, 'score': best_score, 'landing_y': best_landing_y}
