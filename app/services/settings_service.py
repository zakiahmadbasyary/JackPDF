"""
settings_service.py - Persistent application settings manager for JackPDF.

Uses QSettings with local fallback to store user preferences across sessions.
"""

import os
import shutil
import tempfile
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, QSettings, Signal

ORG_NAME = "JackPDF"
APP_NAME = "JackPDF"

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Output & Storage
    "output_mode": "source",          # 'source' or 'custom'
    "custom_output_dir": "",
    "conflict_action": "confirm",     # 'confirm' or 'auto_number'
    "auto_open_folder": False,
    "auto_open_file": False,

    # Feature Defaults
    "default_png_dpi": 200,           # 150, 200, 300
    "default_png_color": "rgb",       # 'rgb' or 'grayscale'
    "default_compress_preset": "recommended",  # 'low', 'recommended', 'high'
    "default_crop_unit": "mm",        # 'mm' or 'inch'
}


class SettingsService(QObject):
    """Manages reading, writing, and resetting application settings."""

    settings_changed = Signal()

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._qsettings = QSettings(ORG_NAME, APP_NAME)

    def get(self, key: str, default: Any = None) -> Any:
        if default is None:
            default = DEFAULT_SETTINGS.get(key)

        val = self._qsettings.value(key, default)

        # QSettings on Windows stores booleans and integers as strings or native types
        if isinstance(default, bool):
            if isinstance(val, str):
                return val.lower() in ("true", "1", "yes")
            return bool(val)
        elif isinstance(default, int):
            try:
                return int(val)
            except (ValueError, TypeError):
                return default
        return val

    def set(self, key: str, value: Any) -> None:
        self._qsettings.setValue(key, value)
        self._qsettings.sync()
        self.settings_changed.emit()

    def get_all(self) -> Dict[str, Any]:
        result = {}
        for k in DEFAULT_SETTINGS:
            result[k] = self.get(k)
        return result

    def save_all(self, settings_dict: Dict[str, Any]) -> None:
        for k, v in settings_dict.items():
            if k in DEFAULT_SETTINGS:
                self._qsettings.setValue(k, v)
        self._qsettings.sync()
        self.settings_changed.emit()

    def reset_to_defaults(self) -> None:
        for k, v in DEFAULT_SETTINGS.items():
            self._qsettings.setValue(k, v)
        self._qsettings.sync()
        self.settings_changed.emit()

    def clear_cache(self) -> int:
        """
        Clean temporary files and cached render artifacts.
        Returns the number of deleted items.
        """
        count = 0
        temp_dir = tempfile.gettempdir()
        jack_prefix = "jackpdf_"

        try:
            for item in os.listdir(temp_dir):
                if item.lower().startswith(jack_prefix):
                    full_p = os.path.join(temp_dir, item)
                    try:
                        if os.path.isdir(full_p):
                            shutil.rmtree(full_p, ignore_errors=True)
                        else:
                            os.remove(full_p)
                        count += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return count


# Singleton instance
_service_instance = None


def get_settings_service() -> SettingsService:
    global _service_instance
    if _service_instance is None:
        _service_instance = SettingsService()
    return _service_instance


def get_effective_output_dir(source_file_path: Optional[str] = None) -> str:
    """
    Returns the resolved output directory based on user settings:
    - If output_mode == 'custom' and custom_output_dir is valid/created, returns custom_output_dir.
    - Otherwise (or fallback), returns directory of source_file_path if provided.
    - If no source file, returns system Documents folder or current working directory.
    """
    service = get_settings_service()
    if service.get("output_mode") == "custom":
        custom = service.get("custom_output_dir", "")
        if custom:
            try:
                os.makedirs(custom, exist_ok=True)
                if os.path.isdir(custom):
                    return os.path.abspath(custom)
            except Exception:
                pass

    if source_file_path and os.path.exists(source_file_path):
        return os.path.dirname(os.path.abspath(source_file_path))

    docs = os.path.expanduser("~/Documents")
    if os.path.isdir(docs):
        return os.path.abspath(docs)
    return os.path.abspath(".")

