import unittest
import os
import json
from blockfall_android.config_manager import ConfigManager, DEFAULT_CONFIG

# Define a temporary config file name for testing
TEST_CONFIG_FILENAME = "test_config.json"
# Define a path for the test config file, assuming tests run from project root or a location
# where 'blockfall_android' is a subdirectory. Adjust if necessary.
# For simplicity, let's assume the test file will be created in the same dir as test_config_manager.py
TEST_CONFIG_FILE_PATH = os.path.join(os.path.dirname(__file__), TEST_CONFIG_FILENAME)


class TestConfigManager(unittest.TestCase):

    def setUp(self):
        # Ensure a clean state before each test
        self.remove_test_config_file()
        # Instantiate ConfigManager with the test file path
        self.config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        # Ensure DEBUG_MODE in config_manager is off for these tests unless specified
        from blockfall_android import config_manager as cm_module
        cm_module.DEBUG_MODE = False


    def tearDown(self):
        # Clean up after each test
        self.remove_test_config_file()

    def remove_test_config_file(self):
        if os.path.exists(TEST_CONFIG_FILE_PATH):
            os.remove(TEST_CONFIG_FILE_PATH)

    def test_load_config_file_not_found_returns_defaults(self):
        # Config file does not exist, should load default config
        self.assertEqual(self.config_manager.get_all(), DEFAULT_CONFIG)

    def test_load_config_invalid_json_returns_defaults(self):
        # Create a corrupted JSON file
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            f.write("this is not json")

        # Re-initialize to trigger _load with the corrupted file
        # ConfigManager's constructor calls _load, so we make a new one or call _load directly for testing this path
        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        self.assertEqual(current_config_manager.get_all(), DEFAULT_CONFIG)


    def test_load_config_empty_json_returns_defaults_with_filled_values(self):
        # Create an empty JSON object file
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            json.dump({}, f)

        # Re-initialize to trigger _load
        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        self.assertEqual(current_config_manager.get_all(), DEFAULT_CONFIG)

    def test_load_config_partial_valid_config(self):
        # Create a config file with some valid settings
        partial_settings = {"sound_effects_enabled": False, "music_enabled": True}
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            json.dump(partial_settings, f)

        # Re-initialize to trigger _load
        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        loaded_settings = current_config_manager.get_all()

        expected_settings = DEFAULT_CONFIG.copy()
        expected_settings.update(partial_settings)

        self.assertEqual(loaded_settings, expected_settings)

    def test_load_config_with_invalid_value_types(self):
        # Create a config file with invalid value types for settings
        invalid_settings = {"shadow_enabled": "not_a_boolean", "music_enabled": 123}
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            json.dump(invalid_settings, f)

        # Re-initialize to trigger _load
        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        loaded_settings = current_config_manager.get_all()

        # Expect defaults for the invalid keys, others default
        expected_settings = DEFAULT_CONFIG.copy()
        # 'shadow_enabled' and 'music_enabled' should revert to default due to invalid type

        self.assertEqual(loaded_settings["shadow_enabled"], DEFAULT_CONFIG["shadow_enabled"])
        self.assertEqual(loaded_settings["music_enabled"], DEFAULT_CONFIG["music_enabled"])
        # Check other keys remain default
        self.assertEqual(loaded_settings["sound_effects_enabled"], DEFAULT_CONFIG["sound_effects_enabled"])
        self.assertEqual(loaded_settings["line_blink_enabled"], DEFAULT_CONFIG["line_blink_enabled"])


    def test_save_and_load_config(self):
        # Modify some settings
        self.config_manager.set("sound_effects_enabled", False)
        self.config_manager.set("shadow_enabled", False)

        # The .set() method calls .save() internally.
        # Create a new ConfigManager instance to load from the saved file
        new_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)

        self.assertEqual(new_config_manager.get("sound_effects_enabled"), False)
        self.assertEqual(new_config_manager.get("shadow_enabled"), False)
        # Check other settings remain default
        self.assertEqual(new_config_manager.get("music_enabled"), DEFAULT_CONFIG["music_enabled"])
        self.assertEqual(new_config_manager.get("line_blink_enabled"), DEFAULT_CONFIG["line_blink_enabled"])

    def test_get_existing_key(self):
        self.assertEqual(self.config_manager.get("music_enabled"), DEFAULT_CONFIG["music_enabled"])

    def test_get_non_existing_key_returns_default_from_spec(self):
        # DEFAULT_CONFIG['non_existing_key'] would error, so we test get's own default
        self.assertIsNone(self.config_manager.get("non_existing_key"))
        self.assertEqual(self.config_manager.get("non_existing_key", "custom_default"), "custom_default")

    def test_set_known_key_valid_type(self):
        self.config_manager.set("music_enabled", False)
        self.assertEqual(self.config_manager.get("music_enabled"), False)
        # Check if saved correctly
        new_cm = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        self.assertEqual(new_cm.get("music_enabled"), False)

    def test_set_known_key_invalid_type(self):
        original_value = self.config_manager.get("music_enabled")
        self.config_manager.set("music_enabled", "not_a_boolean") # Should not change
        self.assertEqual(self.config_manager.get("music_enabled"), original_value)
        # Verify file also not changed for this key with invalid type
        # If the initial config was default, the file might not exist until a valid set.
        # If it exists, check its content.
        if os.path.exists(TEST_CONFIG_FILE_PATH):
            with open(TEST_CONFIG_FILE_PATH, 'r') as f:
                data = json.load(f)
            self.assertEqual(data.get("music_enabled"), original_value)


    def test_set_unknown_key(self):
        self.config_manager.set("new_unknown_key", True) # Should not add the key
        self.assertIsNone(self.config_manager.get("new_unknown_key"))
         # Verify file also not changed
        if os.path.exists(TEST_CONFIG_FILE_PATH):
            with open(TEST_CONFIG_FILE_PATH, 'r') as f:
                data = json.load(f)
            self.assertNotIn("new_unknown_key", data)
        # If set was called on default config (no file existed), file might still not exist.
        # self.assertFalse(os.path.exists(TEST_CONFIG_FILE_PATH)) # This could be true if only unknown keys are set on a fresh ConfigManager


    def test_load_config_backward_compatibility_sound_enabled(self):
        # Create a config file with the old 'sound_enabled' key
        old_settings = {"sound_enabled": False, "shadow_enabled": True}
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            json.dump(old_settings, f)

        # Re-initialize to trigger _load
        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        loaded_settings = current_config_manager.get_all()

        self.assertEqual(loaded_settings["sound_effects_enabled"], False) # Should pick up from 'sound_enabled'
        self.assertEqual(loaded_settings["shadow_enabled"], True)
        # Ensure other defaults are present
        self.assertEqual(loaded_settings["music_enabled"], DEFAULT_CONFIG["music_enabled"])
        self.assertEqual(loaded_settings["line_blink_enabled"], DEFAULT_CONFIG["line_blink_enabled"])

    def test_load_config_prefers_new_key_over_old_sound_enabled(self):
        # Both new 'sound_effects_enabled' and old 'sound_enabled' exist
        settings = {
            "sound_effects_enabled": True, # New key takes precedence
            "sound_enabled": False,        # Old key should be ignored
            "shadow_enabled": True
        }
        with open(TEST_CONFIG_FILE_PATH, 'w') as f:
            json.dump(settings, f)

        current_config_manager = ConfigManager(config_file_path=TEST_CONFIG_FILE_PATH)
        loaded_settings = current_config_manager.get_all()

        self.assertEqual(loaded_settings["sound_effects_enabled"], True) # New key's value
        self.assertEqual(loaded_settings["shadow_enabled"], True)


if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)
