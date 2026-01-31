import json
import os
from PySide6.QtCore import QObject

class SettingsManager:
    REPO_SETTINGS_FILE = os.path.join(os.getcwd(), 'settings.json')
    CUSTOM_SETTINGS_FILE = os.path.join(os.getcwd(), 'custom_settings.json')
    
    DEFAULT_SETTINGS = {
        "work_minutes": 25,
        "break_minutes": 5,
        "work_color": "#FFA500",
        "break_color": "#32CD32",
        "text_size": 40,
        "text_opacity": 1.0,
        "bg_opacity": 0.0,
        "work_volume": 50,
        "break_volume": 50,
        "run_at_startup": True,
        "timer_style": "orange",
        "orange_opacity": 0.25,
        "work_log_enabled": False
    }

    @staticmethod
    def load_settings():
        """
        Load settings with a fallback hierarchy:
        1. Hardcoded DEFAULT_SETTINGS
        2. settings.json (Repo defaults)
        3. custom_settings.json (User overrides)
        """
        settings = SettingsManager.DEFAULT_SETTINGS.copy()
        
        # 1. Merge with Repo Defaults (settings.json)
        if os.path.exists(SettingsManager.REPO_SETTINGS_FILE):
            try:
                with open(SettingsManager.REPO_SETTINGS_FILE, 'r') as f:
                    repo_settings = json.load(f)
                    settings.update(repo_settings)
            except Exception as e:
                print(f"Error loading repo settings: {e}")

        # 2. Merge with User Overrides (custom_settings.json)
        if os.path.exists(SettingsManager.CUSTOM_SETTINGS_FILE):
            try:
                with open(SettingsManager.CUSTOM_SETTINGS_FILE, 'r') as f:
                    custom_settings = json.load(f)
                    settings.update(custom_settings)
            except Exception as e:
                print(f"Error loading custom settings: {e}")
                
        return settings

    @staticmethod
    def save_settings(settings_dict):
        """Save settings dict to custom_settings.json to avoid polluting the repo."""
        try:
            with open(SettingsManager.CUSTOM_SETTINGS_FILE, 'w') as f:
                json.dump(settings_dict, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
