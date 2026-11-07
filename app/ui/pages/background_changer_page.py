"""
background_changer_page.py - Background Changer UI Page for JackPDF.

Allows users to upload photos, remove background using local AI (rembg),
choose from 5 formal background colors (Merah, Biru, Putih, Kuning, Hijau),
apply Pas Foto aspect ratios (2x3, 3x4, 4x6 cm), and export as JPG or PNG.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image
from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDragEnterEvent, QDropEvent, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.background_changer_service import (
    BACKGROUND_COLORS,
    PAS_FOTO_SPECS,
    SUPPORTED_IMAGE_EXTENSIONS,
    apply_background_color,
    crop_to_pas_foto,
    is_supported_image,
    load_and_orient_image,
    save_result_image,
    validate_image_file,
)
from app.services.settings_service import get_effective_output_dir, get_settings_service
from app.utils.file_utils import (
    format_file_size,
    open_file_with_default_app,
    open_in_file_manager,
)
from app.utils.icon_utils import get_feature_icon
from app.utils.resource_utils import get_resource_path
from app.workers.background_changer_worker import BackgroundChangerWorker


class ColorSwatchWidget(QFrame):
    """Interactive color swatch button representing one of the 5 background colors."""
    selected = Signal(str)

    def __init__(self, color_key: str, parent=None):
        super().__init__(parent)
        self.color_key = color_key
        data = BACKGROUND_COLORS[color_key]
        self.color_name = data["name"]
        self.hex_color = data["hex"]
        self.is_active = False

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(56)
        self.setMinimumWidth(100)
        self.setObjectName("ColorSwatch")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 12, 8)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        # Circle color swatch indicator
        self.circle_label = QLabel()
        self.circle_label.setFixedSize(28, 28)
        self._update_circle_pixmap()

        # Text labels
        text_layout = QVBoxLayout()
        text_layout.setSpacing(1)
        text_layout.setContentsMargins(0, 0, 0, 0)

        name_lbl = QLabel(self.color_name)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 9.5pt; color: #111B29;")

        hex_lbl = QLabel(self.hex_color)
        hex_lbl.setStyleSheet("font-size: 7.5pt; color: #64748B;")

        text_layout.addWidget(name_lbl)
        text_layout.addWidget(hex_lbl)

        layout.addWidget(self.circle_label)
        layout.addLayout(text_layout)

        self.update_style()

    def _update_circle_pixmap(self):
        pix = QPixmap(28, 28)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Fill circle
        p.setBrush(QColor(self.hex_color))
        # Add subtle border especially for white color
        border_color = QColor("#CBD5E1") if self.hex_color == "#FFFFFF" else QColor(0, 0, 0, 40)
        p.setPen(border_color)
        p.drawEllipse(1, 1, 26, 26)
        p.end()

        self.circle_label.setPixmap(pix)

    def set_active(self, active: bool):
        self.is_active = active
        self.update_style()

    def update_style(self):
        if self.is_active:
            self.setStyleSheet(
                "QFrame#ColorSwatch {"
                "    background: #EFF6FF;"
                "    border: 2px solid #1D6FEA;"
                "    border-radius: 8px;"
                "}"
            )
        else:
            self.setStyleSheet(
                "QFrame#ColorSwatch {"
                "    background: #FFFFFF;"
                "    border: 1px solid #DCE3EC;"
                "    border-radius: 8px;"
                "}"
                "QFrame#ColorSwatch:hover {"
                "    background: #F8FAFC;"
                "    border-color: #94A3B8;"
                "}"
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.color_key)
        super().mousePressEvent(event)


class BackgroundDropZone(QFrame):
    """Drop zone for initial photo upload."""
    file_dropped = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(160)
        self.setMaximumHeight(210)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 22, 16, 22)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        ph_path = get_resource_path("assets/icons/image_placeholder.png")
        if os.path.exists(ph_path):
            pix = QPixmap(ph_path).scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("🖼️")
            icon_label.setStyleSheet("font-size: 28pt;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Pilih Foto untuk Ganti Background")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("Tarik dan letakkan foto di sini, atau klik tombol di bawah\n(Mendukung format JPG, JPEG, PNG, WEBP)")
        hint.setObjectName("DropHint")
        hint.setWordWrap(True)
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("Pilih Foto...")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setFixedWidth(150)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._browse)

        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._browse()
        super().mousePressEvent(event)

    def _browse(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Foto",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*.*)",
        )
        if file_path:
            self.file_dropped.emit(file_path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            p = url.toLocalFile()
            if is_supported_image(p):
                self.file_dropped.emit(p)
                break
        event.acceptProposedAction()


class BackgroundChangerPage(QWidget):
    go_back = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_path: Optional[str] = None
        self.original_pil_image: Optional[Image.Image] = None
        self.foreground_pil_image: Optional[Image.Image] = None  # RGBA image after AI removal
        self.composited_pil_image: Optional[Image.Image] = None  # Processed with chosen color and crop
        self.selected_color_key: str = "Merah"  # Default formal red
        self.current_mode: str = "formal"  # "formal" or "free"
        self.selected_pas_foto_size: str = "Original"
        self.worker: Optional[BackgroundChangerWorker] = None
        self.last_saved_path: Optional[str] = None

        # Root scroll layout
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("ContentScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("ContentWidget")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(32, 28, 32, 28)
        self.content_layout.setSpacing(16)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 1. Header Section
        header = QHBoxLayout()
        header.setSpacing(12)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        back_btn = QPushButton("←  Kembali")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setToolTip("Kembali ke menu utama JackPDF.")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back.emit)

        header_icon = QLabel()
        feat_pix = get_feature_icon("Background Changer", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Background Changer")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Hapus dan ganti warna latar belakang foto secara otomatis dengan AI lokal.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setWordWrap(True)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(back_btn)
        if not feat_pix.isNull():
            header.addWidget(header_icon)
        header.addLayout(title_box)
        header.addStretch()
        self.content_layout.addLayout(header)

        # 2. Upload Drop Zone (shown when no image is loaded)
        self.drop_zone = BackgroundDropZone()
        self.drop_zone.file_dropped.connect(self.load_image_file)
        self.content_layout.addWidget(self.drop_zone)

        # 3. Main Workspace Container (shown when image is loaded)
        self.workspace_widget = QWidget()
        self.workspace_layout = QVBoxLayout(self.workspace_widget)
        self.workspace_layout.setContentsMargins(0, 0, 0, 0)
        self.workspace_layout.setSpacing(14)
        self.workspace_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Top Bar: Loaded Photo Information
        self.info_card = QFrame()
        self.info_card.setObjectName("FeatureCard")
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(14)

        self.info_thumb = QLabel()
        self.info_thumb.setFixedSize(42, 42)
        self.info_thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_thumb.setStyleSheet("border-radius: 4px; background: #F1F5F9;")

        info_text_layout = QVBoxLayout()
        info_text_layout.setSpacing(2)
        self.file_name_label = QLabel("nama_foto.jpg")
        self.file_name_label.setStyleSheet("font-weight: 600; font-size: 10pt; color: #111B29;")
        self.file_meta_label = QLabel("1200 × 1600 px  •  1.4 MB")
        self.file_meta_label.setStyleSheet("font-size: 8.5pt; color: #64748B;")
        info_text_layout.addWidget(self.file_name_label)
        info_text_layout.addWidget(self.file_meta_label)

        self.change_photo_btn = QPushButton("Ganti Foto...")
        self.change_photo_btn.setObjectName("SecondaryButton")
        self.change_photo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.change_photo_btn.clicked.connect(self._browse_new_photo)

        info_layout.addWidget(self.info_thumb)
        info_layout.addLayout(info_text_layout, 1)
        info_layout.addWidget(self.change_photo_btn)
        self.workspace_layout.addWidget(self.info_card)

        # Mode Selection Card (Foto Formal vs Foto Bebas)
        self.mode_card = QFrame()
        self.mode_card.setObjectName("FeatureCard")
        mode_layout = QVBoxLayout(self.mode_card)
        mode_layout.setContentsMargins(16, 14, 16, 14)
        mode_layout.setSpacing(10)

        mode_header = QLabel("Pilih Mode Foto:")
        mode_header.setObjectName("SectionTitle")
        mode_layout.addWidget(mode_header)

        mode_radios = QHBoxLayout()
        mode_radios.setSpacing(18)

        self.radio_mode_formal = QRadioButton("Foto Formal (Pas Foto)")
        self.radio_mode_formal.setObjectName("RadioChoice")
        self.radio_mode_formal.setChecked(True)
        self.radio_mode_formal.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_mode_formal.toggled.connect(self._on_mode_changed)

        self.radio_mode_free = QRadioButton("Foto Bebas")
        self.radio_mode_free.setObjectName("RadioChoice")
        self.radio_mode_free.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_mode_free.toggled.connect(self._on_mode_changed)

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.radio_mode_formal)
        self.mode_group.addButton(self.radio_mode_free)

        mode_radios.addWidget(self.radio_mode_formal)
        mode_radios.addWidget(self.radio_mode_free)
        mode_radios.addStretch()
        mode_layout.addLayout(mode_radios)

        # Pas Foto Size Options (visible only in Foto Formal mode)
        self.pas_foto_container = QWidget()
        pas_foto_layout = QHBoxLayout(self.pas_foto_container)
        pas_foto_layout.setContentsMargins(0, 4, 0, 0)
        pas_foto_layout.setSpacing(12)

        size_title = QLabel("Ukuran:")
        size_title.setStyleSheet("font-weight: 600; font-size: 9pt; color: #263445;")
        pas_foto_layout.addWidget(size_title)

        self.size_radio_buttons: Dict[str, QRadioButton] = {}
        self.size_group = QButtonGroup(self)

        for key, spec in PAS_FOTO_SPECS.items():
            btn = QRadioButton(spec["label"])
            btn.setObjectName("RadioChoice")
            btn.setToolTip(spec["desc"])
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if key == "Original":
                btn.setChecked(True)
            btn.toggled.connect(lambda checked=False, k=key: self._on_size_changed(k, checked))
            self.size_radio_buttons[key] = btn
            self.size_group.addButton(btn)
            pas_foto_layout.addWidget(btn)

        pas_foto_layout.addStretch()
        mode_layout.addWidget(self.pas_foto_container)

        self.workspace_layout.addWidget(self.mode_card)

        # Interactive Color Swatches Selection (5 Colors)
        self.color_card = QFrame()
        self.color_card.setObjectName("FeatureCard")
        color_card_layout = QVBoxLayout(self.color_card)
        color_card_layout.setContentsMargins(16, 14, 16, 14)
        color_card_layout.setSpacing(10)

        color_header = QLabel("Pilih Warna Background Baru:")
        color_header.setObjectName("SectionTitle")
        color_card_layout.addWidget(color_header)

        swatches_row = QHBoxLayout()
        swatches_row.setSpacing(12)

        self.swatch_widgets: Dict[str, ColorSwatchWidget] = {}
        for c_key in ["Merah", "Biru", "Putih", "Kuning", "Hijau"]:
            swatch = ColorSwatchWidget(c_key)
            swatch.selected.connect(self.select_background_color)
            self.swatch_widgets[c_key] = swatch
            swatches_row.addWidget(swatch)

        color_card_layout.addLayout(swatches_row)
        self.workspace_layout.addWidget(self.color_card)

        # 4. Two-Column Preview Area (Before vs After)
        self.preview_card = QFrame()
        self.preview_card.setObjectName("FeatureCard")
        preview_layout = QVBoxLayout(self.preview_card)
        preview_layout.setContentsMargins(16, 16, 16, 16)
        preview_layout.setSpacing(10)

        preview_top_bar = QHBoxLayout()
        preview_top_title = QLabel("Pratinjau Hasil")
        preview_top_title.setObjectName("SectionTitle")

        # View Toggle (Side by Side vs Tabbed)
        self.toggle_view_btn = QPushButton("Bandingkan Foto Asli")
        self.toggle_view_btn.setObjectName("SecondaryButton")
        self.toggle_view_btn.setCheckable(True)
        self.toggle_view_btn.setChecked(False)
        self.toggle_view_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_view_btn.toggled.connect(self._on_toggle_view)

        preview_top_bar.addWidget(preview_top_title)
        preview_top_bar.addStretch()
        preview_top_bar.addWidget(self.toggle_view_btn)
        preview_layout.addLayout(preview_top_bar)

        # Canvas Display Row
        self.canvas_row = QHBoxLayout()
        self.canvas_row.setSpacing(16)

        # Original Canvas
        self.orig_canvas_box = QVBoxLayout()
        self.orig_canvas_lbl = QLabel("Foto Asli")
        self.orig_canvas_lbl.setStyleSheet("font-weight: 600; color: #64748B; font-size: 8.5pt;")
        self.orig_canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.orig_image_label = QLabel()
        self.orig_image_label.setObjectName("PreviewCanvas")
        self.orig_image_label.setMinimumHeight(320)
        self.orig_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.orig_image_label.setStyleSheet("border: 1px solid #DCE3EC; border-radius: 8px; background: #F8FAFC;")

        self.orig_canvas_box.addWidget(self.orig_canvas_lbl)
        self.orig_canvas_box.addWidget(self.orig_image_label)

        # Result Canvas
        self.result_canvas_box = QVBoxLayout()
        self.result_canvas_lbl = QLabel("Hasil AI & Warna Background")
        self.result_canvas_lbl.setStyleSheet("font-weight: 600; color: #1D6FEA; font-size: 8.5pt;")
        self.result_canvas_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.result_image_label = QLabel()
        self.result_image_label.setObjectName("PreviewCanvas")
        self.result_image_label.setMinimumHeight(320)
        self.result_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_image_label.setStyleSheet("border: 1px solid #DCE3EC; border-radius: 8px; background: #FFFFFF;")

        self.result_canvas_box.addWidget(self.result_canvas_lbl)
        self.result_canvas_box.addWidget(self.result_image_label)

        # By default start with Result Canvas maximized
        self.orig_canvas_box_widget = QWidget()
        self.orig_canvas_box_widget.setLayout(self.orig_canvas_box)
        self.orig_canvas_box_widget.setVisible(False)

        self.result_canvas_box_widget = QWidget()
        self.result_canvas_box_widget.setLayout(self.result_canvas_box)

        self.canvas_row.addWidget(self.orig_canvas_box_widget, 1)
        self.canvas_row.addWidget(self.result_canvas_box_widget, 1)
        preview_layout.addLayout(self.canvas_row)

        self.workspace_layout.addWidget(self.preview_card)

        # 5. Progress Bar & Status Message
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("TaskProgressBar")
        self.progress_bar.setRange(0, 0)  # Indeterminate for AI inference
        self.progress_bar.setVisible(False)
        self.workspace_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Foto siap diproses. Klik 'Hapus Background' untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)
        self.workspace_layout.addWidget(self.status_label)

        # 6. Action Bar (Remove Background, Cancel, Reset, Save JPG, Save PNG)
        action_bar = QHBoxLayout()
        action_bar.setSpacing(10)

        self.remove_bg_btn = QPushButton("✨ Hapus Background")
        self.remove_bg_btn.setObjectName("PrimaryButton")
        self.remove_bg_btn.setFixedHeight(42)
        self.remove_bg_btn.setFixedWidth(190)
        self.remove_bg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.remove_bg_btn.clicked.connect(self.start_remove_background)

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setFixedHeight(42)
        self.cancel_btn.setFixedWidth(90)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_processing)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setFixedHeight(42)
        self.reset_btn.setFixedWidth(90)
        self.reset_btn.setToolTip("Kembalikan pengaturan ke kondisi awal.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        self.save_jpg_btn = QPushButton("💾 Simpan JPG")
        self.save_jpg_btn.setObjectName("PrimaryButton")
        self.save_jpg_btn.setFixedHeight(42)
        self.save_jpg_btn.setFixedWidth(140)
        self.save_jpg_btn.setEnabled(False)
        self.save_jpg_btn.setToolTip("Simpan hasil foto dengan background solid terpilih (300 DPI).")
        self.save_jpg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_jpg_btn.clicked.connect(lambda: self.export_image("JPG"))

        self.save_png_btn = QPushButton("Simpan PNG")
        self.save_png_btn.setObjectName("SecondaryButton")
        self.save_png_btn.setFixedHeight(42)
        self.save_png_btn.setFixedWidth(130)
        self.save_png_btn.setEnabled(False)
        self.save_png_btn.setToolTip("Simpan hasil foto dalam format PNG lossless.")
        self.save_png_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_png_btn.clicked.connect(lambda: self.export_image("PNG"))

        action_bar.addWidget(self.remove_bg_btn)
        action_bar.addWidget(self.cancel_btn)
        action_bar.addWidget(self.reset_btn)
        action_bar.addStretch()
        action_bar.addWidget(self.save_jpg_btn)
        action_bar.addWidget(self.save_png_btn)
        self.workspace_layout.addLayout(action_bar)

        # 7. Result Card (displayed after saving)
        self.result_card = QFrame()
        self.result_card.setObjectName("ResultCard")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(10)

        self.result_msg_label = QLabel("<b>Foto berhasil disimpan!</b>")
        self.result_msg_label.setStyleSheet("color: #0F5132; font-size: 11pt;")

        self.result_details_label = QLabel()
        self.result_details_label.setStyleSheet("color: #263445; font-size: 9pt;")
        self.result_details_label.setWordWrap(True)

        res_btn_row = QHBoxLayout()
        res_btn_row.setSpacing(10)

        self.open_file_btn = QPushButton("Buka Foto")
        self.open_file_btn.setObjectName("PrimaryButton")
        self.open_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_file_btn.clicked.connect(self._open_saved_file)

        self.open_folder_btn = QPushButton("Buka Folder Hasil")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._open_saved_folder)

        self.process_another_btn = QPushButton("Ganti Background Foto Lain")
        self.process_another_btn.setObjectName("SecondaryButton")
        self.process_another_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.process_another_btn.clicked.connect(self.reset_form)

        res_btn_row.addWidget(self.open_file_btn)
        res_btn_row.addWidget(self.open_folder_btn)
        res_btn_row.addWidget(self.process_another_btn)
        res_btn_row.addStretch()

        result_layout.addWidget(self.result_msg_label)
        result_layout.addWidget(self.result_details_label)
        result_layout.addLayout(res_btn_row)
        self.workspace_layout.addWidget(self.result_card)

        self.workspace_widget.setVisible(False)
        self.content_layout.addWidget(self.workspace_widget)
        self.content_layout.addStretch(1)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

        # Set default active color swatch
        self.select_background_color("Merah")

    def load_image_file(self, file_path: str):
        """Load an image file and transition from DropZone to Workspace."""
        ok, err_msg, meta = validate_image_file(file_path)
        if not ok:
            QMessageBox.warning(self, "File Tidak Valid", err_msg)
            return

        self.current_image_path = os.path.abspath(file_path)
        try:
            self.original_pil_image = load_and_orient_image(self.current_image_path)
        except Exception as e:
            QMessageBox.critical(self, "Gagal Membuka Gambar", f"Tidak dapat membaca gambar: {str(e)}")
            return

        self.foreground_pil_image = None
        self.composited_pil_image = None
        self.last_saved_path = None
        self.result_card.setVisible(False)

        # Update info labels
        fname = meta.get("filename", os.path.basename(file_path))
        w = meta.get("width", self.original_pil_image.width)
        h = meta.get("height", self.original_pil_image.height)
        sz = format_file_size(meta.get("size_bytes", os.path.getsize(file_path)))

        self.file_name_label.setText(fname)
        self.file_meta_label.setText(f"{w} × {h} px  •  {sz}")

        # Miniature thumbnail
        orig_pix = QPixmap(self.current_image_path)
        if not orig_pix.isNull():
            self.info_thumb.setPixmap(
                orig_pix.scaled(42, 42, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

        # Show original image in preview
        self._display_original_preview()
        self._display_result_preview(self.original_pil_image, is_original=True)

        # Switch view
        self.drop_zone.setVisible(False)
        self.workspace_widget.setVisible(True)
        self.remove_bg_btn.setEnabled(True)
        self.save_jpg_btn.setEnabled(False)
        self.save_png_btn.setEnabled(False)
        self.status_label.setText("Foto siap diproses. Klik 'Hapus Background' untuk memulai.")

    def _browse_new_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Foto Baru",
            "",
            "Image Files (*.jpg *.jpeg *.png *.webp *.bmp);;All Files (*.*)",
        )
        if file_path:
            self.load_image_file(file_path)

    def select_background_color(self, color_key: str):
        """Change the active background color and immediately update result preview."""
        if color_key not in BACKGROUND_COLORS:
            return

        self.selected_color_key = color_key
        for key, swatch in self.swatch_widgets.items():
            swatch.set_active(key == color_key)

        # Instantly update composite if foreground is already extracted
        if self.foreground_pil_image is not None:
            self._update_composite_and_preview()

    def _on_mode_changed(self):
        is_formal = self.radio_mode_formal.isChecked()
        self.current_mode = "formal" if is_formal else "free"
        self.pas_foto_container.setVisible(is_formal)

        if not is_formal:
            # Revert to original size if in free mode
            self.selected_pas_foto_size = "Original"

        if self.foreground_pil_image is not None:
            self._update_composite_and_preview()

    def _on_size_changed(self, size_key: str, checked: bool):
        if checked:
            self.selected_pas_foto_size = size_key
            if self.foreground_pil_image is not None:
                self._update_composite_and_preview()

    def _on_toggle_view(self, checked: bool):
        """Toggle side-by-side comparison with original photo."""
        self.orig_canvas_box_widget.setVisible(checked)
        self.toggle_view_btn.setText("Sembunyikan Foto Asli" if checked else "Bandingkan Foto Asli")

    def _display_original_preview(self):
        if self.original_pil_image is None:
            return
        pix = self._pil_to_pixmap(self.original_pil_image, max_w=400, max_h=380)
        self.orig_image_label.setPixmap(pix)

    def _display_result_preview(self, pil_img: Image.Image, is_original: bool = False):
        pix = self._pil_to_pixmap(pil_img, max_w=440, max_h=400)
        self.result_image_label.setPixmap(pix)
        if is_original:
            self.result_canvas_lbl.setText("Foto Asli (Klik 'Hapus Background' untuk memproses)")
        else:
            c_name = self.selected_color_key
            size_name = self.selected_pas_foto_size
            self.result_canvas_lbl.setText(f"Hasil AI: Background {c_name} • Ukuran {size_name}")

    def _pil_to_pixmap(self, pil_img: Image.Image, max_w: int = 400, max_h: int = 380) -> QPixmap:
        """Convert Pillow Image to scaled QPixmap for responsive preview display."""
        import io
        bio = io.BytesIO()
        pil_img.save(bio, format="PNG")
        pix = QPixmap()
        pix.loadFromData(bio.getvalue())
        return pix.scaled(
            max_w,
            max_h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def _update_composite_and_preview(self):
        """
        Alpha-composite the foreground over selected color and apply Pas Foto crop.
        Runs in milliseconds without re-invoking AI inference!
        """
        if self.foreground_pil_image is None:
            return

        # 1. Apply selected background color
        colored_img = apply_background_color(self.foreground_pil_image, self.selected_color_key)

        # 2. Apply Pas Foto crop if in formal mode and size specified
        if self.current_mode == "formal" and self.selected_pas_foto_size != "Original":
            final_img = crop_to_pas_foto(colored_img, self.selected_pas_foto_size, dpi=300)
        else:
            final_img = colored_img

        self.composited_pil_image = final_img
        self._display_result_preview(final_img, is_original=False)
        self.save_jpg_btn.setEnabled(True)
        self.save_png_btn.setEnabled(True)

    def start_remove_background(self):
        """Trigger background removal via background worker thread."""
        if not self.current_image_path or not os.path.exists(self.current_image_path):
            QMessageBox.warning(self, "Peringatan", "Foto belum dipilih.")
            return

        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.cancel_btn.setVisible(True)
        self.status_label.setText("Memulai proses penghapusan background dengan AI...")

        self.worker = BackgroundChangerWorker(
            image_path=self.current_image_path,
            model_name="u2netp",
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def cancel_processing(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Membatalkan proses...")
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def on_worker_progress(self, message: str):
        self.status_label.setText(message)

    def on_worker_finished(self, success: bool, message: str, result_fg: Optional[Image.Image]):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

        if success and result_fg is not None:
            self.foreground_pil_image = result_fg
            self.status_label.setText("Background berhasil dihapus! Pilih warna background yang diinginkan.")
            self._update_composite_and_preview()
        else:
            if "dibatalkan" in message.lower():
                self.status_label.setText("Proses dibatalkan oleh pengguna.")
            else:
                self.status_label.setText("Gagal menghapus background.")
                QMessageBox.critical(self, "Proses Gagal", message)

    def export_image(self, format_type: str = "JPG"):
        """Save the processed image to destination file."""
        if self.composited_pil_image is None:
            QMessageBox.warning(self, "Peringatan", "Belum ada hasil untuk disimpan. Klik 'Hapus Background' terlebih dahulu.")
            return

        default_dir = get_effective_output_dir(self.current_image_path)
        base_name = os.path.splitext(os.path.basename(self.current_image_path))[0]
        c_name = self.selected_color_key.lower()
        ext = ".jpg" if format_type.upper() == "JPG" else ".png"

        size_suffix = f"_{self.selected_pas_foto_size.replace(' ', '').replace('×', 'x')}" if self.selected_pas_foto_size != "Original" else ""
        default_filename = f"{base_name}_{c_name}{size_suffix}{ext}"

        filter_str = "JPEG Image (*.jpg *.jpeg)" if format_type.upper() == "JPG" else "PNG Image (*.png)"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Simpan Foto ({format_type.upper()})",
            os.path.join(default_dir, default_filename),
            filter_str,
        )

        if not save_path:
            return

        ok, res_path = save_result_image(
            self.composited_pil_image,
            save_path,
            format_type=format_type,
            dpi=300,
        )

        if ok:
            self.last_saved_path = res_path
            w, h = self.composited_pil_image.size
            sz = format_file_size(os.path.getsize(res_path))

            self.result_msg_label.setText("<b>Foto berhasil disimpan!</b>")
            self.result_details_label.setText(
                f"• Lokasi: <code>{res_path}</code><br>"
                f"• Dimensi: <b>{w} × {h} px</b> (300 DPI)<br>"
                f"• Ukuran File: <b>{sz}</b>"
            )
            self.result_card.setVisible(True)
            self.status_label.setText(f"Selesai! Tersimpan di: {res_path}")

            # Settings check for auto opening
            settings = get_settings_service()
            if settings.get("auto_open_folder"):
                self._open_saved_folder()
            if settings.get("auto_open_file"):
                self._open_saved_file()
        else:
            QMessageBox.critical(self, "Gagal Menyimpan", res_path)

    def _open_saved_file(self):
        if self.last_saved_path and os.path.exists(self.last_saved_path):
            open_file_with_default_app(self.last_saved_path)

    def _open_saved_folder(self):
        if self.last_saved_path and os.path.exists(self.last_saved_path):
            open_in_file_manager(self.last_saved_path)
        elif self.current_image_path:
            open_in_file_manager(os.path.dirname(self.current_image_path))

    def reset_form(self):
        """Reset the entire page back to initial upload state."""
        self.current_image_path = None
        self.original_pil_image = None
        self.foreground_pil_image = None
        self.composited_pil_image = None
        self.last_saved_path = None

        self.radio_mode_formal.setChecked(True)
        self.size_radio_buttons["Original"].setChecked(True)
        self.select_background_color("Merah")

        self.orig_image_label.clear()
        self.result_image_label.clear()
        self.toggle_view_btn.setChecked(False)
        self.orig_canvas_box_widget.setVisible(False)

        self.result_card.setVisible(False)
        self.progress_bar.setVisible(False)
        self.save_jpg_btn.setEnabled(False)
        self.save_png_btn.setEnabled(False)

        self.workspace_widget.setVisible(False)
        self.drop_zone.setVisible(True)
        self.status_label.setText("Pilih foto untuk mulai mengganti background.")

    def set_ui_busy(self, busy: bool):
        self.remove_bg_btn.setEnabled(not busy)
        self.change_photo_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.save_jpg_btn.setEnabled(not busy and self.composited_pil_image is not None)
        self.save_png_btn.setEnabled(not busy and self.composited_pil_image is not None)
        self.color_card.setEnabled(not busy)
        self.mode_card.setEnabled(not busy)

