import os
import subprocess
import sys


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable string (KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_safe_destination_path(destination_dir: str, filename: str) -> str:
    """Return a unique file path if file already exists in destination directory."""
    base_name, ext = os.path.splitext(filename)
    candidate = os.path.join(destination_dir, filename)
    counter = 1
    while os.path.exists(candidate):
        candidate = os.path.join(destination_dir, f"{base_name}_{counter:03d}{ext}")
        counter += 1
    return candidate


def open_in_file_manager(path: str) -> bool:
    """Open the directory or select the file in Windows Explorer."""
    try:
        norm_path = os.path.normpath(path)
        if not os.path.exists(norm_path):
            return False

        if os.path.isfile(norm_path):
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", norm_path], check=False)
                return True
            else:
                norm_path = os.path.dirname(norm_path)

        if sys.platform == "win32":
            os.startfile(norm_path)
            return True
        elif sys.platform == "darwin":
            subprocess.run(["open", norm_path], check=False)
            return True
        else:
            subprocess.run(["xdg-open", norm_path], check=False)
            return True
    except Exception:
        return False
