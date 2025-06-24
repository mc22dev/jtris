import json
import os

# Default configuration settings
DEFAULT_CONFIG = {
    "sound_effects_enabled": True,
    "shadow_enabled": True,
    "line_blink_enabled": True,
    "music_enabled": True,
    "grid_size": "normal"
}

CONFIG_FILENAME = "config.json"
DEBUG_MODE = False # Or get it from environment/global settings if available

class ConfigManager:
    def __init__(self, config_file_path=CONFIG_FILENAME):
        self.config_file_path = config_file_path
        self.config = self._load()

    def _load(self):
        """Loads configuration from the JSON file.
        Returns default configuration if the file is not found or is invalid.
        """
        try:
            if os.path.exists(self.config_file_path):
                with open(self.config_file_path, 'r') as f:
                    data = json.load(f)
                    if not isinstance(data, dict):
                        if DEBUG_MODE:
                            print(f"Warning: {self.config_file_path} content is not a dictionary. Using defaults.")
                        return DEFAULT_CONFIG.copy()

                    # Validate and fill missing keys with defaults
                    loaded_config = DEFAULT_CONFIG.copy()
                    for key in DEFAULT_CONFIG:
                        if key == "grid_size":
                            if key in data and isinstance(data[key], str) and data[key] in ["normal", "large"]:
                                loaded_config[key] = data[key]
                            elif key in data: # Invalid value
                                if DEBUG_MODE:
                                    print(f"Warning: Invalid value for '{key}' in {self.config_file_path}. Using default.")
                            # If key not in data, default is already set
                        elif key in DEFAULT_CONFIG: # Existing logic for boolean keys
                            if key in data and isinstance(data[key], bool):
                                loaded_config[key] = data[key]
                            elif key in data:
                                if DEBUG_MODE:
                                    print(f"Warning: Invalid type for '{key}' in {self.config_file_path}. Using default.")
                        # If key is not in data, default is already set in loaded_config

                    # Handle potential old key 'sound_enabled' for backward compatibility
                    if "sound_effects_enabled" not in data and "sound_enabled" in data:
                        if isinstance(data["sound_enabled"], bool):
                            loaded_config["sound_effects_enabled"] = data["sound_enabled"]
                            if DEBUG_MODE:
                                print(f"DEBUG: Migrated 'sound_enabled' to 'sound_effects_enabled' from {self.config_file_path}.")
                        elif DEBUG_MODE: # Old key present but invalid type
                            print(f"Warning: Invalid type for old key 'sound_enabled' in {self.config_file_path}. Using default for 'sound_effects_enabled'.")

                    if DEBUG_MODE:
                        print(f"Config loaded from {self.config_file_path}: {loaded_config}")
                    return loaded_config
            else:
                if DEBUG_MODE:
                    print(f"Info: {self.config_file_path} not found. Using default config: {DEFAULT_CONFIG}")
                return DEFAULT_CONFIG.copy()
        except json.JSONDecodeError:
            if DEBUG_MODE:
                print(f"Warning: Error decoding {self.config_file_path}. File might be corrupted. Using defaults: {DEFAULT_CONFIG}")
            return DEFAULT_CONFIG.copy()
        except Exception as e:
            if DEBUG_MODE:
                print(f"Warning: An unexpected error occurred loading {self.config_file_path}: {e}. Using defaults: {DEFAULT_CONFIG}")
            return DEFAULT_CONFIG.copy()

    def get(self, key, default_value=None):
        """Retrieves a configuration value by key."""
        return self.config.get(key, default_value if default_value is not None else DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        """Sets a configuration value by key and saves the configuration."""
        if key == "grid_size":
            if isinstance(value, str) and value in ["normal", "large"]:
                self.config[key] = value
                self.save()
            elif DEBUG_MODE:
                print(f"Warning: Invalid value for key '{key}'. Not setting. Must be 'normal' or 'large'.")
        elif key in DEFAULT_CONFIG: # Existing logic for boolean keys
            if isinstance(value, type(DEFAULT_CONFIG[key])):
                self.config[key] = value
                self.save()
            elif DEBUG_MODE:
                print(f"Warning: Invalid type for key '{key}'. Not setting.")
        elif DEBUG_MODE:
            print(f"Warning: Unknown configuration key '{key}'. Not setting.")

    def save(self):
        """Saves the current configuration to the JSON file."""
        try:
            with open(self.config_file_path, 'w') as f:
                json.dump(self.config, f, indent=4)
            if DEBUG_MODE:
                print(f"Config saved to {self.config_file_path}: {self.config}")
        except IOError as e:
            if DEBUG_MODE:
                print(f"Error saving config to {self.config_file_path}: {e}")
        except Exception as e:
            if DEBUG_MODE:
                print(f"An unexpected error occurred while saving config to {self.config_file_path}: {e}")

    def get_all(self):
        """Returns a copy of the entire configuration dictionary."""
        return self.config.copy()

# Example of how to set DEBUG_MODE if it's globally managed, e.g., by tetris.py
# This is just illustrative; the actual mechanism might differ.
def set_debug_mode(is_debug):
    global DEBUG_MODE
    DEBUG_MODE = is_debug
