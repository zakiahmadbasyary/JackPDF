"""
crop_page.py - User Interface for JackPDF Crop PDF feature.

Provides interactive visual crop handles, manual millimeter margin inputs,
live preview synchronization, page selection, and background processing.
"""

import os
from enum import Enum
from typing import Dict, List, Optional, Tuple

import pymupdf as fitz
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QImage,
    QMouseEvent,
    QPainter,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.services.convert_png_service import format_page_selection, parse_page_selection
from app.services.crop_service import (
    get_default_output_filename,
    get_default_output_path,
)
from app.services.settings_service import get_effective_output_dir, get_settings_service
from app.utils.file_utils import (
    format_file_size,
    get_safe_destination_path,
    open_file_with_default_app,
    open_in_file_manager,
)
from app.utils.icon_utils import get_feature_icon
from app.utils.pdf_geometry import (
    CropMargins,
    calculate_crop_rect,
    display_rect_to_pdf_rect,
    margins_from_crop_rect,
    mm_to_points,
    pdf_rect_to_display_rect,
    points_to_mm,
    validate_crop_margins,
)
from app.utils.validators import validate_pdf_file
from app.workers.crop_worker import CropWorker


class DragHandle(Enum):
    NONE = 0
    MOVE = 1
    TOP_LEFT = 2
    TOP = 3
    TOP_RIGHT = 4
    RIGHT = 5
    BOTTOM_RIGHT = 6
    BOTTOM = 7
    BOTTOM_LEFT = 8
    LEFT = 9


class CropCanvasWidget(QWidget):
    """
    Interactive canvas displaying the rendered PDF page with:
    - 8 drag handles for resizing the crop boundary
    - Center move capability
    - Dark semi-transparent overlay on excluded regions
    - Live synchronization with CropMargins (in mm)
    """

    margins_changed = Signal(CropMargins)

    HANDLE_SIZE = 10.0  # px
    HIT_TOLERANCE = 5.0  # px

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setMinimumSize(320, 420)

        self.pixmap: Optional[QPixmap] = None
        self.page_box: fitz.Rect = fitz.Rect(0, 0, 595.0, 842.0)  # default A4
        self.margins: CropMargins = CropMargins(0.0, 0.0, 0.0, 0.0)

        self.active_handle = DragHandle.NONE
        self.drag_start_pos = QPointF()
        self.initial_margins = CropMargins()
        self.canvas_rect = QRectF()

    def set_page_data(self, pixmap: QPixmap, page_box: fitz.Rect):
        self.pixmap = pixmap
        self.page_box = fitz.Rect(page_box)
        self.update()

    def set_margins(self, margins: CropMargins):
        self.margins = CropMargins(
            margins.top_mm,
            margins.bottom_mm,
            margins.left_mm,
            margins.right_mm,
        )
        self.update()

    def get_crop_rect_points(self) -> fitz.Rect:
        return calculate_crop_rect(self.page_box, self.margins)

    def _compute_canvas_rect(self) -> QRectF:
        """Compute rect of rendered page centered within the widget."""
        if not self.pixmap or self.pixmap.isNull():
            return QRectF(20, 20, max(10, self.width() - 40), max(10, self.height() - 40))

        w_avail = max(10, self.width() - 32)
        h_avail = max(10, self.height() - 32)

        pix_w = self.pixmap.width()
        pix_h = self.pixmap.height()

        scale = min(w_avail / pix_w, h_avail / pix_h)
        disp_w = pix_w * scale
        disp_h = pix_h * scale

        x = (self.width() - disp_w) / 2.0
        y = (self.height() - disp_h) / 2.0
        return QRectF(x, y, disp_w, disp_h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Clear background
        painter.fillRect(self.rect(), QColor("#F7F9FC"))

        self.canvas_rect = self._compute_canvas_rect()
        if not self.pixmap or self.pixmap.isNull():
            painter.setPen(QColor("#98A6B8"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Tidak ada dokumen yang dimuat.",
            )
            return

        # 1. Draw page pixmap with white paper background & subtle shadow
        painter.fillRect(self.canvas_rect, QColor("#FFFFFF"))
        painter.drawPixmap(self.canvas_rect.toRect(), self.pixmap)
        painter.setPen(QPen(QColor("#DCE3EC"), 1))
        painter.drawRect(self.canvas_rect)

        # 2. Compute display crop rect
        crop_pt = self.get_crop_rect_points()
        disp_rect = pdf_rect_to_display_rect(crop_pt, self.page_box, self.canvas_rect)

        # 3. Draw darkened semi-transparent overlay on regions outside crop rect
        overlay_color = QColor(7, 20, 38, 120)  # Navy with ~47% alpha

        # Top
        if disp_rect.top() > self.canvas_rect.top():
            painter.fillRect(
                QRectF(
                    self.canvas_rect.left(),
                    self.canvas_rect.top(),
                    self.canvas_rect.width(),
                    disp_rect.top() - self.canvas_rect.top(),
                ),
                overlay_color,
            )
        # Bottom
        if disp_rect.bottom() < self.canvas_rect.bottom():
            painter.fillRect(
                QRectF(
                    self.canvas_rect.left(),
                    disp_rect.bottom(),
                    self.canvas_rect.width(),
                    self.canvas_rect.bottom() - disp_rect.bottom(),
                ),
                overlay_color,
            )
        # Left
        if disp_rect.left() > self.canvas_rect.left():
            painter.fillRect(
                QRectF(
                    self.canvas_rect.left(),
                    disp_rect.top(),
                    disp_rect.left() - self.canvas_rect.left(),
                    disp_rect.height(),
                ),
                overlay_color,
            )
        # Right
        if disp_rect.right() < self.canvas_rect.right():
            painter.fillRect(
                QRectF(
                    disp_rect.right(),
                    disp_rect.top(),
                    self.canvas_rect.right() - disp_rect.right(),
                    disp_rect.height(),
                ),
                overlay_color,
            )

        # 4. Draw crop rectangle border
        border_pen = QPen(QColor("#1D6FEA"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(border_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRect(disp_rect)

        # 5. Draw 8 interactive handles
        handles = self._get_handle_rects(disp_rect)
        handle_pen = QPen(QColor("#1D6FEA"), 2)
        painter.setPen(handle_pen)
        painter.setBrush(QColor("#FFFFFF"))

        for h_rect in handles.values():
            painter.drawRect(h_rect)

    def _get_handle_rects(self, disp_rect: QRectF) -> Dict[DragHandle, QRectF]:
        hs = self.HANDLE_SIZE
        half = hs / 2.0
        cx = disp_rect.center().x()
        cy = disp_rect.center().y()

        return {
            DragHandle.TOP_LEFT: QRectF(disp_rect.left() - half, disp_rect.top() - half, hs, hs),
            DragHandle.TOP: QRectF(cx - half, disp_rect.top() - half, hs, hs),
            DragHandle.TOP_RIGHT: QRectF(disp_rect.right() - half, disp_rect.top() - half, hs, hs),
            DragHandle.RIGHT: QRectF(disp_rect.right() - half, cy - half, hs, hs),
            DragHandle.BOTTOM_RIGHT: QRectF(disp_rect.right() - half, disp_rect.bottom() - half, hs, hs),
            DragHandle.BOTTOM: QRectF(cx - half, disp_rect.bottom() - half, hs, hs),
            DragHandle.BOTTOM_LEFT: QRectF(disp_rect.left() - half, disp_rect.bottom() - half, hs, hs),
            DragHandle.LEFT: QRectF(disp_rect.left() - half, cy - half, hs, hs),
        }

    def _hit_test(self, pos: QPointF) -> DragHandle:
        if not self.pixmap:
            return DragHandle.NONE

        crop_pt = self.get_crop_rect_points()
        disp_rect = pdf_rect_to_display_rect(crop_pt, self.page_box, self.canvas_rect)
        handles = self._get_handle_rects(disp_rect)

        # Expand hit test area slightly for usability
        for handle_type, rect in handles.items():
            hit_rect = rect.adjusted(
                -self.HIT_TOLERANCE,
                -self.HIT_TOLERANCE,
                self.HIT_TOLERANCE,
                self.HIT_TOLERANCE,
            )
            if hit_rect.contains(pos):
                return handle_type

        # Inside crop rect -> MOVE
        if disp_rect.contains(pos):
            return DragHandle.MOVE

        return DragHandle.NONE

    def _update_cursor_for_handle(self, handle: DragHandle):
        if handle in (DragHandle.TOP_LEFT, DragHandle.BOTTOM_RIGHT):
            self.setCursor(Qt.CursorShape.SizeFDiagCursor)
        elif handle in (DragHandle.TOP_RIGHT, DragHandle.BOTTOM_LEFT):
            self.setCursor(Qt.CursorShape.SizeBDiagCursor)
        elif handle in (DragHandle.TOP, DragHandle.BOTTOM):
            self.setCursor(Qt.CursorShape.SizeVerCursor)
        elif handle in (DragHandle.LEFT, DragHandle.RIGHT):
            self.setCursor(Qt.CursorShape.SizeHorCursor)
        elif handle == DragHandle.MOVE:
            self.setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            self.active_handle = self._hit_test(pos)
            if self.active_handle != DragHandle.NONE:
                self.drag_start_pos = pos
                self.initial_margins = CropMargins(
                    self.margins.top_mm,
                    self.margins.bottom_mm,
                    self.margins.left_mm,
                    self.margins.right_mm,
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        pos = event.position()

        if self.active_handle != DragHandle.NONE:
            # We are currently dragging
            dx_px = pos.x() - self.drag_start_pos.x()
            dy_px = pos.y() - self.drag_start_pos.y()

            if self.canvas_rect.width() > 0 and self.canvas_rect.height() > 0:
                scale_x = self.page_box.width / self.canvas_rect.width()
                scale_y = self.page_box.height / self.canvas_rect.height()

                dx_mm = points_to_mm(dx_px * scale_x)
                dy_mm = points_to_mm(dy_px * scale_y)

                self._apply_drag(dx_mm, dy_mm)
                self.margins_changed.emit(self.margins)
                self.update()
            event.accept()
            return

        # Hover state: update cursor
        handle = self._hit_test(pos)
        self._update_cursor_for_handle(handle)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and self.active_handle != DragHandle.NONE:
            self.active_handle = DragHandle.NONE
            self.margins_changed.emit(self.margins)
            self.update()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _apply_drag(self, dx_mm: float, dy_mm: float):
        page_w_mm = points_to_mm(self.page_box.width)
        page_h_mm = points_to_mm(self.page_box.height)
        min_rem_mm = 5.0  # Keep at least 5mm visible

        init = self.initial_margins
        h = self.active_handle

        if h == DragHandle.MOVE:
            # Move entire crop box
            box_w_mm = page_w_mm - (init.left_mm + init.right_mm)
            box_h_mm = page_h_mm - (init.top_mm + init.bottom_mm)

            new_left = max(0.0, min(page_w_mm - box_w_mm, init.left_mm + dx_mm))
            new_top = max(0.0, min(page_h_mm - box_h_mm, init.top_mm + dy_mm))
            new_right = max(0.0, page_w_mm - (new_left + box_w_mm))
            new_bottom = max(0.0, page_h_mm - (new_top + box_h_mm))

            self.margins = CropMargins(new_top, new_bottom, new_left, new_right).round_values(1)
            return

        top = init.top_mm
        bottom = init.bottom_mm
        left = init.left_mm
        right = init.right_mm

        # Top handles
        if h in (DragHandle.TOP_LEFT, DragHandle.TOP, DragHandle.TOP_RIGHT):
            max_top = page_h_mm - bottom - min_rem_mm
            top = max(0.0, min(max_top, init.top_mm + dy_mm))

        # Bottom handles
        if h in (DragHandle.BOTTOM_LEFT, DragHandle.BOTTOM, DragHandle.BOTTOM_RIGHT):
            max_bottom = page_h_mm - top - min_rem_mm
            bottom = max(0.0, min(max_bottom, init.bottom_mm - dy_mm))

        # Left handles
        if h in (DragHandle.TOP_LEFT, DragHandle.LEFT, DragHandle.BOTTOM_LEFT):
            max_left = page_w_mm - right - min_rem_mm
            left = max(0.0, min(max_left, init.left_mm + dx_mm))

        # Right handles
        if h in (DragHandle.TOP_RIGHT, DragHandle.RIGHT, DragHandle.BOTTOM_RIGHT):
            max_right = page_w_mm - left - min_rem_mm
            right = max(0.0, min(max_right, init.right_mm - dx_mm))

        self.margins = CropMargins(top, bottom, left, right).round_values(1)


class CropDropZone(QFrame):
    """
    Dropzone frame supporting drag-and-drop of a single PDF file
    or clicking to browse.
    """

    file_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Pilih file PDF")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("atau tarik dan letakkan file di sini")
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("Browse File")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setFixedWidth(140)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse_clicked)

        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addWidget(browse_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    def _on_browse_clicked(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Dokumen PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.file_dropped.emit(file_path)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_browse_clicked()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.file_dropped.emit(path)
                break
        event.acceptProposedAction()


class CropPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.current_password: Optional[str] = None
        self.current_page_count: int = 0
        self.current_page_num: int = 1  # 1-based index
        self.zoom_factor: float = 1.0
        self.current_margins = CropMargins(0.0, 0.0, 0.0, 0.0)
        self.last_output_file: str = ""
        self.worker: Optional[CropWorker] = None
        self._updating_margins = False

        # Root layout holding scroll area
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
        self.content_layout.setSpacing(18)

        # Header Section
        header = QHBoxLayout()
        header.setSpacing(12)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        back_btn = QPushButton("←  Kembali")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setToolTip("Kembali ke halaman utama JackPDF.")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back.emit)

        header_icon = QLabel()
        feat_pix = get_feature_icon("Crop PDF", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Crop PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Potong area halaman PDF sesuai kebutuhan.")
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

        # Dropzone Section
        self.drop_zone = CropDropZone()
        self.drop_zone.file_dropped.connect(self.load_pdf_file)
        self.content_layout.addWidget(self.drop_zone)

        # File Info Card (hidden until file is loaded)
        self.info_card = QFrame()
        self.info_card.setObjectName("InfoCard")
        self.info_card.setVisible(False)
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(12)

        info_icon = QLabel()
        info_icon.setObjectName("FeatureIcon")
        info_icon.setFixedSize(40, 40)
        if not feat_pix.isNull():
            info_icon.setPixmap(feat_pix)
        else:
            info_icon.setText("PDF")
        info_layout.addWidget(info_icon)

        self.file_details_label = QLabel("Detail File")
        self.file_details_label.setObjectName("FileDetailsText")
        info_layout.addWidget(self.file_details_label, 1)

        change_btn = QPushButton("Ganti File")
        change_btn.setObjectName("SecondaryButton")
        change_btn.setToolTip("Pilih file PDF lain dari komputer.")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.clicked.connect(self.browse_single_file)
        info_layout.addWidget(change_btn)

        self.toggle_preview_btn = QPushButton("Sembunyikan Pratinjau")
        self.toggle_preview_btn.setObjectName("SecondaryButton")
        self.toggle_preview_btn.setToolTip("Tampilkan atau sembunyikan kolom pratinjau dokumen.")
        self.toggle_preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_preview_btn.setCheckable(True)
        self.toggle_preview_btn.setChecked(True)
        self.toggle_preview_btn.setVisible(False)
        self.toggle_preview_btn.toggled.connect(self.on_toggle_preview)
        info_layout.addWidget(self.toggle_preview_btn)

        self.content_layout.addWidget(self.info_card)

        # --- TWO-COLUMN BODY LAYOUT ---
        self.body_layout = QHBoxLayout()
        self.body_layout.setSpacing(18)

        # LEFT COLUMN: Settings & Action Controls
        self.left_settings_widget = QWidget()
        self.left_settings_widget.setFixedWidth(380)
        left_layout = QVBoxLayout(self.left_settings_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)

        # 1. Settings Card
        self.settings_card = QFrame()
        self.settings_card.setObjectName("FeatureCard")
        self.settings_card.setVisible(False)
        settings_card_layout = QVBoxLayout(self.settings_card)
        settings_card_layout.setContentsMargins(20, 18, 20, 18)
        settings_card_layout.setSpacing(14)

        # 1.1 Crop Margin Section
        margin_sec_title = QLabel("Area Pemotongan (Margin)")
        margin_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(margin_sec_title)

        # Dimensions Badges
        dim_layout = QHBoxLayout()
        dim_layout.setSpacing(8)

        self.orig_dim_label = QLabel("Ukuran Asli: —")
        self.orig_dim_label.setObjectName("PreviewBadge")
        self.orig_dim_label.setStyleSheet(
            "background: #EEF2F7; color: #263445; font-size: 8.5pt; font-weight: 600; padding: 4px 8px; border-radius: 6px;"
        )

        self.crop_dim_label = QLabel("Hasil Crop: —")
        self.crop_dim_label.setObjectName("PreviewBadge")
        self.crop_dim_label.setStyleSheet(
            "background: #DCEBFF; color: #1557B0; font-size: 8.5pt; font-weight: 600; padding: 4px 8px; border-radius: 6px;"
        )

        dim_layout.addWidget(self.orig_dim_label)
        dim_layout.addWidget(self.crop_dim_label)
        dim_layout.addStretch()
        settings_card_layout.addLayout(dim_layout)

        # Margin SpinBoxes Grid (Top, Bottom, Left, Right in mm)
        margins_grid = QGridLayout()
        margins_grid.setSpacing(10)

        # Top
        top_lbl = QLabel("Atas (Top):")
        top_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")
        self.top_spin = QDoubleSpinBox()
        self.top_spin.setObjectName("StyledSpinBox")
        self.top_spin.setRange(0.0, 2000.0)
        self.top_spin.setDecimals(1)
        self.top_spin.setSingleStep(1.0)
        self.top_spin.setSuffix(" mm")
        self.top_spin.valueChanged.connect(self._on_margin_spin_changed)
        margins_grid.addWidget(top_lbl, 0, 0)
        margins_grid.addWidget(self.top_spin, 0, 1)

        # Bottom
        bottom_lbl = QLabel("Bawah (Bottom):")
        bottom_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")
        self.bottom_spin = QDoubleSpinBox()
        self.bottom_spin.setObjectName("StyledSpinBox")
        self.bottom_spin.setRange(0.0, 2000.0)
        self.bottom_spin.setDecimals(1)
        self.bottom_spin.setSingleStep(1.0)
        self.bottom_spin.setSuffix(" mm")
        self.bottom_spin.valueChanged.connect(self._on_margin_spin_changed)
        margins_grid.addWidget(bottom_lbl, 0, 2)
        margins_grid.addWidget(self.bottom_spin, 0, 3)

        # Left
        left_lbl = QLabel("Kiri (Left):")
        left_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")
        self.left_spin = QDoubleSpinBox()
        self.left_spin.setObjectName("StyledSpinBox")
        self.left_spin.setRange(0.0, 2000.0)
        self.left_spin.setDecimals(1)
        self.left_spin.setSingleStep(1.0)
        self.left_spin.setSuffix(" mm")
        self.left_spin.valueChanged.connect(self._on_margin_spin_changed)
        margins_grid.addWidget(left_lbl, 1, 0)
        margins_grid.addWidget(self.left_spin, 1, 1)

        # Right
        right_lbl = QLabel("Kanan (Right):")
        right_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")
        self.right_spin = QDoubleSpinBox()
        self.right_spin.setObjectName("StyledSpinBox")
        self.right_spin.setRange(0.0, 2000.0)
        self.right_spin.setDecimals(1)
        self.right_spin.setSingleStep(1.0)
        self.right_spin.setSuffix(" mm")
        self.right_spin.valueChanged.connect(self._on_margin_spin_changed)
        margins_grid.addWidget(right_lbl, 1, 2)
        margins_grid.addWidget(self.right_spin, 1, 3)

        settings_card_layout.addLayout(margins_grid)

        # Margin action buttons (Reset Crop & Center Crop)
        margin_btn_row = QHBoxLayout()
        margin_btn_row.setSpacing(8)

        self.reset_crop_btn = QPushButton("Reset Margin")
        self.reset_crop_btn.setObjectName("SecondaryButton")
        self.reset_crop_btn.setToolTip("Kembalikan area pemotongan ke seluruh halaman (margin 0 mm).")
        self.reset_crop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_crop_btn.clicked.connect(self.reset_margins_to_full)

        self.center_crop_btn = QPushButton("Pusatkan Crop")
        self.center_crop_btn.setObjectName("SecondaryButton")
        self.center_crop_btn.setToolTip("Ratakan margin kiri-kanan dan atas-bawah agar crop berada di tengah.")
        self.center_crop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.center_crop_btn.clicked.connect(self.center_crop_margins)

        margin_btn_row.addWidget(self.reset_crop_btn)
        margin_btn_row.addWidget(self.center_crop_btn)
        margin_btn_row.addStretch()
        settings_card_layout.addLayout(margin_btn_row)

        self.margin_error_label = QLabel("")
        self.margin_error_label.setStyleSheet("color: #D64545; font-size: 8.5pt; font-weight: 500;")
        self.margin_error_label.setVisible(False)
        settings_card_layout.addWidget(self.margin_error_label)
        settings_card_layout.addSpacing(4)

        # 1.2 Target Pages Section
        pages_sec_title = QLabel("Terapkan ke Halaman")
        pages_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(pages_sec_title)

        page_opts_layout = QVBoxLayout()
        page_opts_layout.setSpacing(8)

        self.radio_current_page = QRadioButton("Halaman Saat Ini Saja")
        self.radio_current_page.setObjectName("RadioChoice")
        self.radio_current_page.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_current_page.toggled.connect(self._on_target_pages_mode_changed)

        self.radio_all_pages = QRadioButton("Semua Halaman")
        self.radio_all_pages.setObjectName("RadioChoice")
        self.radio_all_pages.setChecked(True)
        self.radio_all_pages.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_all_pages.toggled.connect(self._on_target_pages_mode_changed)

        self.radio_custom_pages = QRadioButton("Pilih Halaman Tertentu")
        self.radio_custom_pages.setObjectName("RadioChoice")
        self.radio_custom_pages.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_custom_pages.toggled.connect(self._on_target_pages_mode_changed)

        self.page_opts_group = QButtonGroup(self)
        self.page_opts_group.addButton(self.radio_current_page)
        self.page_opts_group.addButton(self.radio_all_pages)
        self.page_opts_group.addButton(self.radio_custom_pages)

        page_opts_layout.addWidget(self.radio_all_pages)
        page_opts_layout.addWidget(self.radio_current_page)
        page_opts_layout.addWidget(self.radio_custom_pages)

        # Custom Page Range Input Container (visible only when custom is selected)
        self.custom_pages_container = QWidget()
        self.custom_pages_container.setVisible(False)
        custom_vbox = QVBoxLayout(self.custom_pages_container)
        custom_vbox.setContentsMargins(20, 2, 0, 0)
        custom_vbox.setSpacing(4)

        self.manual_range_edit = QLineEdit()
        self.manual_range_edit.setObjectName("StyledInput")
        self.manual_range_edit.setPlaceholderText("Contoh: 1, 3, 5-8")
        self.manual_range_edit.textChanged.connect(self._on_manual_range_changed)

        range_hint = QLabel("Gunakan koma untuk memisahkan, tanda hubung untuk rentang (misal: 1, 3-5).")
        range_hint.setStyleSheet("color: #697586; font-size: 8.5pt;")

        self.page_summary_label = QLabel("")
        self.page_summary_label.setStyleSheet("color: #1D6FEA; font-weight: 600; font-size: 8.5pt;")

        self.page_error_label = QLabel("")
        self.page_error_label.setStyleSheet("color: #D64545; font-size: 8.5pt; font-weight: 500;")
        self.page_error_label.setVisible(False)

        custom_vbox.addWidget(self.manual_range_edit)
        custom_vbox.addWidget(range_hint)
        custom_vbox.addWidget(self.page_summary_label)
        custom_vbox.addWidget(self.page_error_label)
        page_opts_layout.addWidget(self.custom_pages_container)

        multi_hint = QLabel("ℹ Area crop diterapkan ke halaman terpilih berdasarkan margin fisik (mm).")
        multi_hint.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        page_opts_layout.addWidget(multi_hint)

        settings_card_layout.addLayout(page_opts_layout)
        settings_card_layout.addSpacing(4)

        # 1.3 Output Folder & File Name Section
        out_sec_title = QLabel("Pengaturan Output")
        out_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(out_sec_title)

        out_grid = QGridLayout()
        out_grid.setSpacing(8)

        fn_lbl = QLabel("Nama File Output:")
        fn_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")
        self.output_filename_edit = QLineEdit()
        self.output_filename_edit.setObjectName("StyledInput")
        self.output_filename_edit.setPlaceholderText("nama_file_cropped.pdf")
        self.output_filename_edit.textChanged.connect(self.validate_state)

        folder_lbl = QLabel("Folder Tujuan:")
        folder_lbl.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(6)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setObjectName("StyledInput")
        self.output_dir_edit.setPlaceholderText("Folder penyimpanan...")
        self.output_dir_edit.textChanged.connect(self.validate_state)

        browse_folder_btn = QPushButton("Pilih...")
        browse_folder_btn.setObjectName("SecondaryButton")
        browse_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_btn.clicked.connect(self.browse_output_dir)

        folder_row.addWidget(self.output_dir_edit, 1)
        folder_row.addWidget(browse_folder_btn)

        out_grid.addWidget(fn_lbl, 0, 0)
        out_grid.addWidget(self.output_filename_edit, 0, 1)
        out_grid.addWidget(folder_lbl, 1, 0)
        out_grid.addLayout(folder_row, 1, 1)

        settings_card_layout.addLayout(out_grid)
        left_layout.addWidget(self.settings_card)

        # --- RESULT SUMMARY CARD (hidden until finished) ---
        self.result_card = QFrame()
        self.result_card.setObjectName("ResultSummaryCard")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(12)

        res_title = QLabel("Hasil Crop PDF")
        res_title.setObjectName("ResultTitle")
        result_layout.addWidget(res_title)

        self.result_details_label = QLabel()
        self.result_details_label.setStyleSheet("color: #263445; font-size: 9.5pt;")
        self.result_details_label.setWordWrap(True)
        result_layout.addWidget(self.result_details_label)

        res_btn_row = QHBoxLayout()
        res_btn_row.setSpacing(10)

        self.open_file_btn = QPushButton("Buka File Hasil")
        self.open_file_btn.setObjectName("PrimaryButton")
        self.open_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_file_btn.clicked.connect(self.open_output_file)

        self.open_folder_btn = QPushButton("Buka Folder")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        self.crop_another_btn = QPushButton("Crop File Lain")
        self.crop_another_btn.setObjectName("SecondaryButton")
        self.crop_another_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crop_another_btn.clicked.connect(self.reset_form)

        res_btn_row.addWidget(self.open_file_btn)
        res_btn_row.addWidget(self.open_folder_btn)
        res_btn_row.addWidget(self.crop_another_btn)
        res_btn_row.addStretch()
        result_layout.addLayout(res_btn_row)

        left_layout.addWidget(self.result_card)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Pilih file PDF terlebih dahulu untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)
        left_layout.addWidget(self.status_label)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        self.crop_btn = QPushButton("Crop PDF")
        self.crop_btn.setObjectName("ActionLargeButton")
        self.crop_btn.setToolTip("Mulai proses pemotongan halaman PDF.")
        self.crop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crop_btn.setEnabled(False)
        self.crop_btn.clicked.connect(self.start_crop)

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setObjectName("TableDeleteBtn")
        self.cancel_btn.setToolTip("Hentikan proses yang sedang berjalan.")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_crop)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setToolTip("Kosongkan form dan pilih file lain.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        bottom_bar.addWidget(self.crop_btn)
        bottom_bar.addWidget(self.cancel_btn)
        bottom_bar.addWidget(self.reset_btn)
        bottom_bar.addStretch()
        left_layout.addLayout(bottom_bar)
        left_layout.addStretch()

        # RIGHT COLUMN: Interactive Visual Preview Panel
        self.preview_panel = QFrame()
        self.preview_panel.setObjectName("PreviewCard")
        self.preview_panel.setMinimumWidth(380)
        self.preview_panel.setVisible(False)
        preview_panel_layout = QVBoxLayout(self.preview_panel)
        preview_panel_layout.setContentsMargins(14, 14, 14, 14)
        preview_panel_layout.setSpacing(10)

        # Preview Header: Title + Page navigation + Zoom buttons
        prev_header = QHBoxLayout()
        prev_header.setSpacing(8)

        prev_title = QLabel("Pratinjau Crop")
        prev_title.setObjectName("PreviewTitle")

        # Page nav controls: Prev / Page Label / Next
        self.prev_page_btn = QPushButton("◀")
        self.prev_page_btn.setObjectName("PreviewNavBtn")
        self.prev_page_btn.setToolTip("Halaman sebelumnya")
        self.prev_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.prev_page_btn.clicked.connect(self.prev_page)

        self.page_nav_label = QLabel("Hal 1 / 1")
        self.page_nav_label.setObjectName("PreviewNavLabel")
        self.page_nav_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.next_page_btn = QPushButton("▶")
        self.next_page_btn.setObjectName("PreviewNavBtn")
        self.next_page_btn.setToolTip("Halaman selanjutnya")
        self.next_page_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.next_page_btn.clicked.connect(self.next_page)

        # Zoom controls
        self.zoom_out_btn = QPushButton("🔍 -")
        self.zoom_out_btn.setObjectName("PreviewNavBtn")
        self.zoom_out_btn.setToolTip("Perkecil pratinjau")
        self.zoom_out_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_out_btn.clicked.connect(self.zoom_out)

        self.zoom_fit_btn = QPushButton("Fit")
        self.zoom_fit_btn.setObjectName("PreviewNavBtn")
        self.zoom_fit_btn.setToolTip("Sesuaikan dengan ukuran tampilan")
        self.zoom_fit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_fit_btn.clicked.connect(self.zoom_fit)

        self.zoom_in_btn = QPushButton("🔍 +")
        self.zoom_in_btn.setObjectName("PreviewNavBtn")
        self.zoom_in_btn.setToolTip("Perbesar pratinjau")
        self.zoom_in_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.zoom_in_btn.clicked.connect(self.zoom_in)

        prev_header.addWidget(prev_title)
        prev_header.addStretch()
        prev_header.addWidget(self.prev_page_btn)
        prev_header.addWidget(self.page_nav_label)
        prev_header.addWidget(self.next_page_btn)
        prev_header.addSpacing(6)
        prev_header.addWidget(self.zoom_out_btn)
        prev_header.addWidget(self.zoom_fit_btn)
        prev_header.addWidget(self.zoom_in_btn)
        preview_panel_layout.addLayout(prev_header)

        # Canvas Area for interactive crop handles
        self.canvas = CropCanvasWidget()
        self.canvas.margins_changed.connect(self._on_canvas_margins_changed)
        preview_panel_layout.addWidget(self.canvas, 1)

        # Quick tip under canvas
        canvas_tip = QLabel("💡 Tarik garis batas atau sudut kotak biru untuk menyesuaikan area pemotongan.")
        canvas_tip.setStyleSheet("color: #697586; font-size: 8.5pt;")
        canvas_tip.setWordWrap(True)
        preview_panel_layout.addWidget(canvas_tip)

        # Assemble two columns into body
        self.body_layout.addWidget(self.left_settings_widget, stretch=0)
        self.body_layout.addWidget(self.preview_panel, stretch=1)
        self.content_layout.addLayout(self.body_layout)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

        # Connect settings update listener
        get_settings_service().settings_changed.connect(self._on_settings_changed)

    def _on_settings_changed(self):
        if self.current_file:
            self.output_dir_edit.setText(get_effective_output_dir(self.current_file))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        if width < 640:
            self.content_layout.setContentsMargins(16, 16, 16, 16)
            self.content_layout.setSpacing(12)
        else:
            self.content_layout.setContentsMargins(32, 28, 32, 28)
            self.content_layout.setSpacing(18)

    def on_toggle_preview(self, checked: bool):
        self.preview_panel.setVisible(checked)
        if checked:
            self.toggle_preview_btn.setText("Sembunyikan Pratinjau")
            self._render_current_page()
        else:
            self.toggle_preview_btn.setText("Tampilkan Pratinjau")

    def browse_single_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Dokumen PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.load_pdf_file(file_path)

    def browse_output_dir(self):
        start_dir = self.output_dir_edit.text().strip() or get_effective_output_dir(self.current_file)
        chosen_dir = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Penyimpanan File Hasil",
            start_dir,
        )
        if chosen_dir:
            self.output_dir_edit.setText(os.path.abspath(chosen_dir))

    def load_pdf_file(self, file_path: str):
        norm_path = os.path.abspath(file_path)
        password = None

        is_valid, err_msg, page_count = validate_pdf_file(norm_path)
        if not is_valid and "password" in err_msg.lower():
            pw, ok = QInputDialog.getText(
                self,
                "PDF Dilindungi Password",
                f"File '{os.path.basename(norm_path)}' dilindungi password.\nMasukkan password dokumen:",
                QLineEdit.EchoMode.Password,
            )
            if not ok or not pw:
                QMessageBox.warning(
                    self,
                    "Akses Ditolak",
                    "PDF ini dilindungi password. Masukkan password atau pilih file lain.",
                )
                return
            password = pw
            is_valid, err_msg, page_count = validate_pdf_file(norm_path, password=password)

        if not is_valid:
            QMessageBox.warning(
                self,
                "File PDF Tidak Valid",
                f"File '{os.path.basename(norm_path)}' tidak dapat diproses:\n{err_msg}",
            )
            return

        self.current_file = norm_path
        self.current_password = password
        self.current_page_count = page_count
        self.current_page_num = 1
        self.zoom_factor = 1.0

        # Update Info Card
        size_bytes = os.path.getsize(norm_path)
        size_str = format_file_size(size_bytes)
        self.file_details_label.setText(
            f"<b>{os.path.basename(norm_path)}</b><br>"
            f"<span style='color: #697586;'>Ukuran: {size_str}  •  Total: {page_count} Halaman</span>"
        )
        self.info_card.setVisible(True)
        self.drop_zone.setVisible(False)
        self.settings_card.setVisible(True)
        self.result_card.setVisible(False)

        # Output Defaults
        self.output_filename_edit.setText(get_default_output_filename(norm_path))
        self.output_dir_edit.setText(get_effective_output_dir(norm_path))

        # Reset Margins
        self.current_margins = CropMargins(0.0, 0.0, 0.0, 0.0)
        self._sync_margins_to_spinboxes(self.current_margins)

        # Default Page Selection
        self.radio_all_pages.setChecked(True)
        self.custom_pages_container.setVisible(False)
        self.manual_range_edit.setText(f"1-{page_count}")
        self.page_summary_label.setText(f"Semua {page_count} halaman dipilih")

        # Load into preview
        self.preview_panel.setVisible(self.toggle_preview_btn.isChecked())
        self.toggle_preview_btn.setVisible(True)
        self._render_current_page()
        self.validate_state()

    def _render_current_page(self):
        """Render the active page in PyMuPDF and update the canvas."""
        if not self.current_file or self.current_page_count < 1:
            return

        idx = self.current_page_num - 1
        try:
            doc = fitz.open(self.current_file)
            if doc.is_encrypted and self.current_password:
                doc.authenticate(self.current_password)

            page = doc[idx]
            page_box = page.rect

            # Base zoom calculation: 120 DPI gives crisp preview
            base_dpi = 120.0 * self.zoom_factor
            zoom_matrix = fitz.Matrix(base_dpi / 72.0, base_dpi / 72.0)
            pix = page.get_pixmap(matrix=zoom_matrix, alpha=False)

            qimg = QImage(
                pix.samples,
                pix.width,
                pix.height,
                pix.stride,
                QImage.Format.Format_RGB888,
            )
            qpixmap = QPixmap.fromImage(qimg.copy())
            doc.close()

            self.canvas.set_page_data(qpixmap, page_box)
            self.canvas.set_margins(self.current_margins)

            # Update nav controls
            self.page_nav_label.setText(f"Hal {self.current_page_num} / {self.current_page_count}")
            self.prev_page_btn.setEnabled(self.current_page_num > 1)
            self.next_page_btn.setEnabled(self.current_page_num < self.current_page_count)

            # Update dimensions badges
            w_mm = points_to_mm(page_box.width)
            h_mm = points_to_mm(page_box.height)
            self.orig_dim_label.setText(f"Ukuran Asli: {w_mm:.1f} × {h_mm:.1f} mm")
            self._update_crop_dim_badge()

        except Exception as e:
            self.status_label.setText(f"Gagal merender halaman: {e}")

    def _update_crop_dim_badge(self):
        """Update badge showing resulting cropped dimensions in mm."""
        if not self.current_file:
            return
        page_box = self.canvas.page_box
        page_w_mm = points_to_mm(page_box.width)
        page_h_mm = points_to_mm(page_box.height)

        crop_w_mm = max(0.0, page_w_mm - (self.current_margins.left_mm + self.current_margins.right_mm))
        crop_h_mm = max(0.0, page_h_mm - (self.current_margins.top_mm + self.current_margins.bottom_mm))
        self.crop_dim_label.setText(f"Hasil Crop: {crop_w_mm:.1f} × {crop_h_mm:.1f} mm")

    def prev_page(self):
        if self.current_page_num > 1:
            self.current_page_num -= 1
            self._render_current_page()
            if self.radio_current_page.isChecked():
                self.validate_state()

    def next_page(self):
        if self.current_page_num < self.current_page_count:
            self.current_page_num += 1
            self._render_current_page()
            if self.radio_current_page.isChecked():
                self.validate_state()

    def zoom_in(self):
        self.zoom_factor = min(2.5, self.zoom_factor * 1.25)
        self._render_current_page()

    def zoom_out(self):
        self.zoom_factor = max(0.5, self.zoom_factor / 1.25)
        self._render_current_page()

    def zoom_fit(self):
        self.zoom_factor = 1.0
        self._render_current_page()

    def _on_canvas_margins_changed(self, margins: CropMargins):
        """Called when user drags handles on canvas -> update spinboxes."""
        self.current_margins = CropMargins(
            margins.top_mm,
            margins.bottom_mm,
            margins.left_mm,
            margins.right_mm,
        )
        self._sync_margins_to_spinboxes(self.current_margins)
        self._update_crop_dim_badge()
        self.validate_state()

    def _on_margin_spin_changed(self):
        """Called when user changes spinbox values -> update canvas."""
        if self._updating_margins:
            return

        self.current_margins = CropMargins(
            top_mm=self.top_spin.value(),
            bottom_mm=self.bottom_spin.value(),
            left_mm=self.left_spin.value(),
            right_mm=self.right_spin.value(),
        )
        self.canvas.set_margins(self.current_margins)
        self._update_crop_dim_badge()
        self.validate_state()

    def _sync_margins_to_spinboxes(self, margins: CropMargins):
        self._updating_margins = True
        self.top_spin.setValue(margins.top_mm)
        self.bottom_spin.setValue(margins.bottom_mm)
        self.left_spin.setValue(margins.left_mm)
        self.right_spin.setValue(margins.right_mm)
        self._updating_margins = False

    def reset_margins_to_full(self):
        """Reset margins to 0 mm (entire page)."""
        self.current_margins = CropMargins(0.0, 0.0, 0.0, 0.0)
        self._sync_margins_to_spinboxes(self.current_margins)
        self.canvas.set_margins(self.current_margins)
        self._update_crop_dim_badge()
        self.validate_state()

    def center_crop_margins(self):
        """Evenly balance margins so the crop box is centered."""
        page_box = self.canvas.page_box
        page_w_mm = points_to_mm(page_box.width)
        page_h_mm = points_to_mm(page_box.height)

        cur = self.current_margins
        cur_w_mm = page_w_mm - (cur.left_mm + cur.right_mm)
        cur_h_mm = page_h_mm - (cur.top_mm + cur.bottom_mm)

        even_horiz = max(0.0, (page_w_mm - cur_w_mm) / 2.0)
        even_vert = max(0.0, (page_h_mm - cur_h_mm) / 2.0)

        self.current_margins = CropMargins(
            top_mm=round(even_vert, 1),
            bottom_mm=round(even_vert, 1),
            left_mm=round(even_horiz, 1),
            right_mm=round(even_horiz, 1),
        )
        self._sync_margins_to_spinboxes(self.current_margins)
        self.canvas.set_margins(self.current_margins)
        self._update_crop_dim_badge()
        self.validate_state()

    def _on_target_pages_mode_changed(self):
        is_custom = self.radio_custom_pages.isChecked()
        self.custom_pages_container.setVisible(is_custom)
        if is_custom:
            self._validate_custom_pages()
        else:
            self.page_error_label.setVisible(False)
        self.validate_state()

    def _on_manual_range_changed(self, text: str):
        if self.radio_custom_pages.isChecked():
            self._validate_custom_pages()
            self.validate_state()

    def _validate_custom_pages(self) -> bool:
        if not self.current_file or self.current_page_count < 1:
            return False

        text = self.manual_range_edit.text().strip()
        if not text:
            self.page_error_label.setText("Ketik nomor halaman yang ingin di-crop.")
            self.page_error_label.setVisible(True)
            self.page_summary_label.setText("")
            return False

        ok, pages, err = parse_page_selection(text, self.current_page_count)
        if not ok:
            self.page_error_label.setText(err)
            self.page_error_label.setVisible(True)
            self.page_summary_label.setText("")
            return False

        self.page_error_label.setVisible(False)
        count = len(pages)
        total = self.current_page_count
        self.page_summary_label.setText(
            f"✓ {count} dari {total} halaman dipilih ({format_page_selection(pages)})"
        )
        return True

    def get_selected_pages(self) -> List[int]:
        if not self.current_file or self.current_page_count < 1:
            return []

        if self.radio_all_pages.isChecked():
            return list(range(1, self.current_page_count + 1))
        elif self.radio_current_page.isChecked():
            return [self.current_page_num]
        else:
            text = self.manual_range_edit.text().strip()
            ok, pages, _ = parse_page_selection(text, self.current_page_count)
            return pages if ok else []

    def get_full_output_path(self) -> str:
        folder = self.output_dir_edit.text().strip()
        filename = self.output_filename_edit.text().strip()
        if not filename.lower().endswith(".pdf"):
            filename += ".pdf"
        return os.path.join(folder, filename)

    def validate_state(self):
        if not self.current_file:
            self.crop_btn.setEnabled(False)
            self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")
            return

        # 1. Validate margins against current page
        page_box = self.canvas.page_box
        valid_m, err_m = validate_crop_margins(
            page_box.width, page_box.height, self.current_margins
        )
        if not valid_m:
            self.margin_error_label.setText(err_m)
            self.margin_error_label.setVisible(True)
            self.crop_btn.setEnabled(False)
            self.status_label.setText("Margin tidak valid. Periksa nilai margin.")
            return
        else:
            self.margin_error_label.setVisible(False)

        # 2. Validate selected pages
        selected_pages = self.get_selected_pages()
        if not selected_pages:
            self.crop_btn.setEnabled(False)
            self.status_label.setText("Pilih minimal satu halaman untuk di-crop.")
            return

        # 3. Validate output paths
        out_folder = self.output_dir_edit.text().strip()
        out_name = self.output_filename_edit.text().strip()
        if not out_folder or not out_name:
            self.crop_btn.setEnabled(False)
            self.status_label.setText("Tentukan nama file dan folder tujuan.")
            return

        out_full = self.get_full_output_path()
        if out_full.lower() == os.path.abspath(self.current_file).lower():
            self.crop_btn.setEnabled(False)
            self.status_label.setText("Output tidak boleh sama dengan file sumber asli.")
            return

        self.crop_btn.setEnabled(True)
        count = len(selected_pages)
        self.status_label.setText(
            f"Siap memotong {count} halaman (Margin: T={self.current_margins.top_mm:.1f}, "
            f"B={self.current_margins.bottom_mm:.1f}, L={self.current_margins.left_mm:.1f}, "
            f"R={self.current_margins.right_mm:.1f} mm)."
        )

    def start_crop(self):
        if not self.current_file:
            return

        selected_pages = self.get_selected_pages()
        if not selected_pages:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu halaman untuk di-crop.")
            return

        out_path = self.get_full_output_path()

        if out_path.lower() == os.path.abspath(self.current_file).lower():
            QMessageBox.warning(
                self,
                "Lokasi Tidak Valid",
                "Nama atau folder file output tidak boleh sama dengan file sumber asli.",
            )
            return

        # Overwrite confirmation or auto-numbering based on settings
        settings = get_settings_service()
        conflict_action = settings.get("conflict_action", "confirm")

        if os.path.exists(out_path):
            if conflict_action == "auto_number":
                folder = self.output_dir_edit.text().strip()
                filename = self.output_filename_edit.text().strip()
                if not filename.lower().endswith(".pdf"):
                    filename += ".pdf"
                out_path = get_safe_destination_path(folder, filename)
                self.output_filename_edit.setText(os.path.basename(out_path))
            else:
                confirm = QMessageBox.question(
                    self,
                    "Konfirmasi Penimpaan File",
                    f"File '{os.path.basename(out_path)}' sudah ada di folder tujuan.\n"
                    "Apakah Anda ingin menimpa file tersebut?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

        # Start background worker
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)
        self.result_card.setVisible(False)
        self.status_label.setText("Memulai proses crop...")

        self.worker = CropWorker(
            input_path=self.current_file,
            output_path=out_path,
            margins=self.current_margins,
            pages=selected_pages,
            password=self.current_password,
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def cancel_crop(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Membatalkan proses crop...")
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def on_worker_progress(self, current: int, total: int, message: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        self.status_label.setText(message)

    def on_worker_finished(self, success: bool, message: str, result_data: Optional[dict]):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

        if success and result_data:
            self.last_output_file = result_data.get("output_path", "")
            cropped_count = result_data.get("total_cropped", 0)
            failed_pages = result_data.get("failed_pages", [])
            is_cancelled = result_data.get("is_cancelled", False)

            status_text = (
                f"<b>{message}</b><br><br>"
                f"• Jumlah halaman dipotong: <b>{cropped_count} halaman</b><br>"
                f"• Lokasi file: <code>{self.last_output_file}</code><br><br>"
                f"<span style='color: #697586; font-size: 8.5pt;'>"
                f"Catatan: Pemotongan menggunakan CropBox mengubah area tampilan halaman PDF. File asli tidak diubah."
                f"</span>"
            )

            if failed_pages:
                failed_str = ", ".join(map(str, failed_pages))
                status_text += f"<br><span style='color: #D64545;'>• Halaman dilewati: {failed_str}</span>"

            if is_cancelled:
                status_text += "<br><span style='color: #D99116;'>• Proses dihentikan oleh pengguna.</span>"

            self.result_details_label.setText(status_text)
            self.result_card.setVisible(True)
            self.status_label.setText(f"Selesai! File tersimpan di: {self.last_output_file}")

            # Check post-processing settings
            settings = get_settings_service()
            if settings.get("auto_open_folder"):
                self.open_output_folder()
            if settings.get("auto_open_file"):
                self.open_output_file()
        else:
            self.status_label.setText("Proses crop gagal.")
            QMessageBox.critical(self, "Crop Gagal", message)

    def open_output_file(self):
        if self.last_output_file and os.path.exists(self.last_output_file):
            open_file_with_default_app(self.last_output_file)

    def open_output_folder(self):
        target = os.path.dirname(self.last_output_file) if self.last_output_file else ""
        if target and os.path.exists(target):
            open_in_file_manager(target)

    def set_ui_busy(self, busy: bool):
        self.crop_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.settings_card.setEnabled(not busy)
        self.info_card.setEnabled(not busy)
        self.canvas.setEnabled(not busy)

    def reset_form(self):
        self.current_file = None
        self.current_password = None
        self.current_page_count = 0
        self.current_page_num = 1
        self.last_output_file = ""

        self.info_card.setVisible(False)
        self.settings_card.setVisible(False)
        self.result_card.setVisible(False)
        self.drop_zone.setVisible(True)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.crop_btn.setEnabled(False)
        self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")

        self.output_filename_edit.clear()
        self.output_dir_edit.clear()
        self.manual_range_edit.clear()
        self.page_error_label.setVisible(False)
        self.margin_error_label.setVisible(False)

        self.current_margins = CropMargins(0.0, 0.0, 0.0, 0.0)
        self._sync_margins_to_spinboxes(self.current_margins)

        self.radio_all_pages.setChecked(True)
        self.custom_pages_container.setVisible(False)

        self.canvas.set_page_data(QPixmap(), fitz.Rect(0, 0, 595, 842))
        self.preview_panel.setVisible(False)
        self.toggle_preview_btn.setVisible(False)
