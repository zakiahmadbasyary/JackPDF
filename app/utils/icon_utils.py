import os
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPainterPath, QPixmap

ICONS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icons")
)

FEATURE_ICON_FILES = {
    "Merge PDF": "icon merge.png",
    "Split PDF": "icon split.png",
    "Compress PDF": "icon compres.png",
    "Convert to PNG": "icon convert.png",
    "Crop PDF": "icon crop.png",
}


def get_icon_path(filename: str) -> str:
    """Return the absolute path to an icon file in assets/icons."""
    return os.path.join(ICONS_DIR, filename)


def load_rounded_pixmap(image_path: str, size: int = 48, radius: Optional[float] = None) -> QPixmap:
    """Load an image and mask it with anti-aliased rounded corners to remove border artifacts."""
    if not os.path.isabs(image_path):
        image_path = get_icon_path(image_path)

    if not os.path.exists(image_path):
        return QPixmap()

    src = QPixmap(image_path)
    if src.isNull():
        return src

    if radius is None:
        radius = size * 0.22

    scaled = src.scaled(
        size,
        size,
        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
        Qt.TransformationMode.SmoothTransformation,
    )

    dest = QPixmap(size, size)
    dest.fill(Qt.GlobalColor.transparent)

    painter = QPainter(dest)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    path = QPainterPath()
    path.addRoundedRect(0, 0, size, size, radius, radius)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, scaled)
    painter.end()

    return dest


def get_feature_icon(feature_name: str, size: int = 48) -> QPixmap:
    """Get the rounded pixmap for a specific feature."""
    filename = FEATURE_ICON_FILES.get(feature_name)
    if filename:
        return load_rounded_pixmap(filename, size=size)
    return QPixmap()


def get_app_logo(size: int = 32) -> QPixmap:
    """Get the rounded app logo pixmap."""
    return load_rounded_pixmap("logo.png", size=size)


def get_app_icon() -> QIcon:
    """Get the QIcon for the application."""
    logo_path = get_icon_path("logo.png")
    if os.path.exists(logo_path):
        return QIcon(logo_path)
    return QIcon()
