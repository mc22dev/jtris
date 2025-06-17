# Configuration Manager for Tetris Android

import json
import os

CONFIG_SUBDIR = "config"

def load_config(DEBUG_MODE):
    filename = os.path.join(CONFIG_SUBDIR, "config.json")
    default_config = {
        "sound_effects_enabled": True,
        "shadow_enabled": True,
        "line_blink_enabled": True,
        "music_enabled": True
    }

    try:
        with open(filename, 'r') as f:
            data = json.load(f)
            if not isinstance(data, dict): # Ensure data is a dictionary before using .get()
                if DEBUG_MODE: print(f"Warning: {filename} content is not a dictionary. Using defaults.")
                return default_config.copy()

            final_config = {}

            # Handle sound_effects_enabled (with backward compatibility for 'sound_enabled')
            loaded_sound_fx = data.get("sound_effects_enabled")
            if isinstance(loaded_sound_fx, bool):
                final_config["sound_effects_enabled"] = loaded_sound_fx
            else:
                old_sound_enabled = data.get("sound_enabled") # Check old key
                if isinstance(old_sound_enabled, bool):
                    final_config["sound_effects_enabled"] = old_sound_enabled
                    if DEBUG_MODE: print(f"DEBUG: Migrated 'sound_enabled' to 'sound_effects_enabled' from {filename}.")
                else:
                    final_config["sound_effects_enabled"] = default_config["sound_effects_enabled"]
                    if DEBUG_MODE: print(f"Warning: 'sound_effects_enabled' (and old 'sound_enabled') missing/invalid in {filename}. Using default.")

            # Handle shadow_enabled
            loaded_shadow = data.get("shadow_enabled")
            if isinstance(loaded_shadow, bool):
                final_config["shadow_enabled"] = loaded_shadow
            else:
                final_config["shadow_enabled"] = default_config["shadow_enabled"]
                if DEBUG_MODE: print(f"Warning: 'shadow_enabled' missing/invalid in {filename}. Using default.")

            # Handle line_blink_enabled
            loaded_line_blink = data.get("line_blink_enabled")
            if isinstance(loaded_line_blink, bool):
                final_config["line_blink_enabled"] = loaded_line_blink
            else:
                final_config["line_blink_enabled"] = default_config["line_blink_enabled"]
                if DEBUG_MODE: print(f"Warning: 'line_blink_enabled' missing/invalid in {filename}. Using default.")

            # Handle new music_enabled key
            loaded_music = data.get("music_enabled")
            if isinstance(loaded_music, bool):
                final_config["music_enabled"] = loaded_music
            else:
                final_config["music_enabled"] = default_config["music_enabled"]
                if DEBUG_MODE: print(f"Warning: 'music_enabled' missing/invalid in {filename}. Using default.")

            if DEBUG_MODE: print(f"Config processed from {filename}. Final values: {final_config}")
            return final_config

    except FileNotFoundError:
        if DEBUG_MODE: print(f"Info: {filename} not found. Using default config: {default_config}")
        return default_config.copy()
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filename}. File might be corrupted. Using defaults: {default_config}")
        return default_config.copy()
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: An unexpected error occurred loading {filename}: {e}. Using defaults: {default_config}")
        return default_config.copy()

def save_config(config_data, DEBUG_MODE):
    filepath = os.path.join(CONFIG_SUBDIR, "config.json")
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(config_data, f, indent=4) # Save with indentation for readability
        if DEBUG_MODE: print(f"Config saved to {filepath}: {config_data}")
    except IOError as e:
        if DEBUG_MODE: print(f"Error saving config to {filepath}: {e}")
    except Exception as e: # Catch any other unexpected errors during save
        if DEBUG_MODE: print(f"An unexpected error occurred while saving config to {filepath}: {e}")

def _update_and_save_top_scores(new_score_entry, DEBUG_MODE):
    filepath = os.path.join(CONFIG_SUBDIR, "best_score.json")

    # 1. Load existing scores
    current_top_scores = []
    try:
        with open(filepath, 'r') as f: # Changed filename to filepath
            loaded_data = json.load(f)
            if isinstance(loaded_data, list):
                # Basic validation for entries when loading for update
                for entry in loaded_data:
                    if isinstance(entry, dict) and \
                       "username" in entry and isinstance(entry["username"], str) and \
                       "score" in entry and isinstance(entry["score"], int) and \
                       "time_str" in entry and isinstance(entry["time_str"], str):
                        current_top_scores.append(entry)
                    # Silently skip invalid entries when loading for update, or log if DEBUG_MODE
                    elif DEBUG_MODE:
                        print(f"Skipping invalid entry during load for update: {entry}")
    except FileNotFoundError:
        # It's okay if the file doesn't exist, means current_top_scores is empty.
        if DEBUG_MODE: print(f"Info: {filepath} not found while trying to update scores. Starting fresh list.")
        pass # current_top_scores remains []
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filepath} during update. Score list might be reset/corrupted if saved now.")
        current_top_scores = []
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: Unexpected error loading {filepath} for update: {e}. Proceeding with empty list.")
        current_top_scores = []

    # 2. Add the new score entry
    current_top_scores.append(new_score_entry)

    # 3. Sort the list by score (descending)
    current_top_scores.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 4. Truncate the list to the top 10 scores
    updated_top_10_scores = current_top_scores[:10]

    # 5. Write the updated list back to best_score.json
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f: # Changed filename to filepath
            json.dump(updated_top_10_scores, f, indent=4)
        if DEBUG_MODE: print(f"Top scores saved to {filepath}: {updated_top_10_scores}")
    except IOError as e:
        if DEBUG_MODE: print(f"Error saving top scores to {filepath}: {e}")
    except Exception as e:
        if DEBUG_MODE: print(f"An unexpected error occurred while saving top scores to {filepath}: {e}")

def _load_best_score(DEBUG_MODE):
    filename = os.path.join(CONFIG_SUBDIR, "best_score.json")
    default_scores_list = []

    try:
        with open(filename, 'r') as f:
            data = json.load(f)

            if not isinstance(data, list):
                if DEBUG_MODE: print(f"Warning: {filename} content is not a list. Returning empty list.")
                return default_scores_list

            valid_scores = []
            for entry in data:
                if isinstance(entry, dict) and \
                   "username" in entry and isinstance(entry["username"], str) and \
                   "score" in entry and isinstance(entry["score"], int) and \
                   "time_str" in entry and isinstance(entry["time_str"], str):
                    valid_scores.append(entry)
                else:
                    if DEBUG_MODE: print(f"Warning: Invalid score entry found in {filename}: {entry}. Skipping.")

            valid_scores.sort(key=lambda x: x.get("score", 0), reverse=True)
            top_10_scores = valid_scores[:10]

            if DEBUG_MODE: print(f"Top scores loaded from {filename}: {top_10_scores}")
            return top_10_scores

    except FileNotFoundError:
        if DEBUG_MODE: print(f"Info: {filename} not found. Returning empty list.")
        return default_scores_list
    except json.JSONDecodeError:
        if DEBUG_MODE: print(f"Warning: Error decoding {filename}. File might be corrupted. Returning empty list.")
        return default_scores_list
    except Exception as e:
        if DEBUG_MODE: print(f"Warning: An unexpected error occurred loading {filename}: {e}. Returning empty list.")
        return default_scores_list
