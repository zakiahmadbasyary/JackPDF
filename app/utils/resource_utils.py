"""
resource_utils.py - Centralized resource path resolver for JackPDF.

Provides reliable path resolution across development and PyInstaller frozen modes.
"""
import os
import sys
from pathlib import Path


def get_base_dir() -> Path:
    """Return the base directory of the application bundle or repository root."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    # When running from source: app/utils/resource_utils.py -> parent x 3 = project root
    return Path(__file__).resolve().parent.parent.parent


def get_resource_path(relative_path: str) -> str:
    """
    Resolve a relative resource path (e.g. 'assets/styles/light.qss' or 'assets/icons/logo.png')
    to an absolute filesystem path.
    """
    return str(get_base_dir() / relative_path)

