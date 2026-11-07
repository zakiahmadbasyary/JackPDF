"""
convert_images_to_pdf_page.py - Convert Images to PDF UI page for JackPDF.

Allows users to select multiple images (JPG, PNG, BMP, TIFF, WEBP), arrange their order,
configure page sizes (Fit to Image, A4 Portrait, A4 Landscape) and margins,
and convert them into a single PDF document asynchronously with progress tracking.
"""

import os
from typing import Any, Dict, List, Optional, Tuple
from PySide6.QtCore import QMimeData, QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QDrag, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.convert_images_to_pdf_service import (
    A4_HEIGHT,
    A4_WIDTH,
    SUPPORTED_IMAGE_EXTENSIONS,
    is_supported_image,
    validate_image_file,
)
from app.services.settings_service import get_effective_output_dir, get_settings_service
from app.utils.file_utils import (
    format_file_size,
    get_safe_destination_path,
    open_file_with_default_app,
    open_in_file_manager,
)
from app.utils.icon_utils import get_feature_icon
from app.utils.resource_utils import get_resource_path
from app.workers.convert_images_to_pdf_worker import ConvertImagesToPdfWorker


class ImageDropZone(QFrame):
    """
    Drop zone displayed when no images are loaded yet.
    Supports drag and drop of files or clicking to browse.
    """
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 28, 16, 28)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        ph_path = get_resource_path("assets/icons/image_placeholder.png")
        if os.path.exists(ph_path):
            pix = QPixmap(ph_path).scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setText("🖼️")
            icon_label.setStyleSheet("font-size: 32pt;")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Pilih file gambar untuk dikonversi")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("atau tarik dan lepaskan file gambar di sini (JPG, PNG, BMP, TIFF, WEBP)")
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(12)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        browse_btn = QPushButton("Pilih Gambar...")
        browse_btn.setObjectName("SecondaryButton")
        browse_btn.setFixedWidth(150)
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse_clicked)

        browse_folder_btn = QPushButton("Pilih Folder...")
        browse_folder_btn.setObjectName("SecondaryButton")
        browse_folder_btn.setFixedWidth(140)
        browse_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_btn.clicked.connect(self._on_browse_folder_clicked)

        btn_box.addWidget(browse_btn)
        btn_box.addWidget(browse_folder_btn)

        layout.addWidget(icon_label)
        layout.addWidget(title)
        layout.addWidget(hint)
        layout.addLayout(btn_box)

    def _on_browse_clicked(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih File Gambar",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp);;All Files (*.*)",
        )
        if files:
            self.files_dropped.emit(files)

    def _on_browse_folder_clicked(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Berisi Gambar")
        if folder:
            images = self._scan_folder_for_images(folder)
            if images:
                self.files_dropped.emit(images)

    def _scan_folder_for_images(self, folder_path: str) -> List[str]:
        found = []
        try:
            for item in sorted(os.listdir(folder_path)):
                p = os.path.join(folder_path, item)
                if os.path.isfile(p) and is_supported_image(p):
                    found.append(p)
        except Exception:
            pass
        return found

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
        all_paths = []
        for url in urls:
            path = url.toLocalFile()
            if os.path.isdir(path):
                all_paths.extend(self._scan_folder_for_images(path))
            elif is_supported_image(path):
                all_paths.append(path)

        if all_paths:
            self.files_dropped.emit(all_paths)
        event.acceptProposedAction()


class ImageOrderTable(QTableWidget):
    """
    Enhanced QTableWidget supporting:
    1. Custom drag-and-drop row reordering.
    2. Direct drop of image files or folders from Windows Explorer.
    3. Visual drop indicator line during drag.
    4. Extended row selection.
    """
    rows_reordered = Signal(list, int)
    files_dropped = Signal(list, int)

    def __init__(self):
        super().__init__()
        self.setObjectName("FileTable")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDropIndicatorShown(False)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setWordWrap(False)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.verticalHeader().setDefaultSectionSize(46)
        self.verticalHeader().setVisible(False)

        self._drag_start_rows: List[int] = []
        self._drop_target_row: Optional[int] = None

    def startDrag(self, supportedActions):
        selected = sorted(set(index.row() for index in self.selectedIndexes()))
        if not selected:
            return
        self._drag_start_rows = selected

        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-jackpdf-image-order", b"")
        drag.setMimeData(mime)

        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_rows = []
        self._drop_target_row = None
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-jackpdf-image-order"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-jackpdf-image-order"):
            pos = event.position().toPoint()
            target_row = self.rowAt(pos.y())
            if target_row == -1:
                target_row = self.rowCount()
            else:
                item = self.item(target_row, 0)
                if item:
                    rect = self.visualItemRect(item)
                    if pos.y() > rect.center().y():
                        target_row += 1
            if self._drop_target_row != target_row:
                self._drop_target_row = target_row
                self.viewport().update()
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self._drop_target_row = None
        self.viewport().update()
        event.accept()

    def dropEvent(self, event):
        pos = event.position().toPoint()
        target_row = self.rowAt(pos.y())
        if target_row == -1:
            target_row = self.rowCount()
        else:
            item = self.item(target_row, 0)
            if item:
                rect = self.visualItemRect(item)
                if pos.y() > rect.center().y():
                    target_row += 1

        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            paths = []
            for url in urls:
                path = url.toLocalFile()
                if os.path.isdir(path):
                    for root, _, files in os.walk(path):
                        for f in sorted(files):
                            fp = os.path.join(root, f)
                            if is_supported_image(fp):
                                paths.append(fp)
                elif is_supported_image(path):
                    paths.append(path)
            if paths:
                self.files_dropped.emit(paths, target_row)
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-jackpdf-image-order"):
            selected_rows = list(self._drag_start_rows)
            if selected_rows:
                self.rows_reordered.emit(selected_rows, target_row)
            event.acceptProposedAction()
        else:
            event.ignore()

        self._drag_start_rows = []
        self._drop_target_row = None
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._drop_target_row is not None:
            painter = QPainter(self.viewport())
            pen = QPen(QColor("#1D6FEA"), 3)
            painter.setPen(pen)

            if self._drop_target_row >= self.rowCount():
                if self.rowCount() > 0:
                    rect = self.visualItemRect(self.item(self.rowCount() - 1, 0))
                    y = rect.bottom()
                else:
                    y = 0
            else:
                rect = self.visualItemRect(self.item(self._drop_target_row, 0))
                y = rect.top()

            painter.drawLine(0, y, self.viewport().width(), y)
            painter.end()


class ImagePreviewPanel(QFrame):
    """Side panel displaying high quality preview and metadata of the selected image."""

    def __init__(self):
        super().__init__()
        self.setObjectName("PreviewCard")
        self.setFixedWidth(260)
        self.setMinimumHeight(380)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Header with Title and Format Badge
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        self.title_label = QLabel("Pratinjau Gambar")
        self.title_label.setObjectName("PreviewTitle")

        self.format_badge = QLabel("—")
        self.format_badge.setObjectName("PreviewBadge")
        self.format_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.format_badge)
        layout.addLayout(header_layout)

        # Canvas Area for Image Thumbnail
        self.canvas = QFrame()
        self.canvas.setObjectName("PreviewCanvas")
        canvas_layout = QVBoxLayout(self.canvas)
        canvas_layout.setContentsMargins(8, 8, 8, 8)
        canvas_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel()
        self.image_label.setObjectName("PreviewImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setVisible(False)

        self.empty_widget = QWidget()
        empty_layout = QVBoxLayout(self.empty_widget)
        empty_layout.setContentsMargins(0, 30, 0, 30)
        empty_layout.setSpacing(8)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_icon = QLabel()
        ph_path = get_resource_path("assets/icons/image_placeholder.png")
        if os.path.exists(ph_path):
            pix = QPixmap(ph_path).scaled(54, 54, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            empty_icon.setPixmap(pix)
        else:
            empty_icon.setText("🖼️")
            empty_icon.setStyleSheet("font-size: 28pt;")
        empty_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_text = QLabel("Pilih gambar pada tabel\nuntuk melihat pratinjau.")
        empty_text.setObjectName("PreviewEmptyText")
        empty_text.setAlignment(Qt.AlignmentFlag.AlignCenter)

        empty_layout.addWidget(empty_icon)
        empty_layout.addWidget(empty_text)

        canvas_layout.addWidget(self.image_label)
        canvas_layout.addWidget(self.empty_widget)
        layout.addWidget(self.canvas, stretch=1)

        # Metadata Details
        self.meta_widget = QWidget()
        self.meta_widget.setObjectName("PreviewMetaWidget")
        meta_layout = QVBoxLayout(self.meta_widget)
        meta_layout.setContentsMargins(2, 4, 2, 2)
        meta_layout.setSpacing(4)

        self.name_label = QLabel("Tidak ada gambar terpilih")
        self.name_label.setObjectName("PreviewDocName")
        self.name_label.setWordWrap(True)

        self.details_label = QLabel("Pilih gambar untuk melihat dimensi dan ukuran.")
        self.details_label.setObjectName("PreviewDocMeta")
        self.details_label.setWordWrap(True)

        meta_layout.addWidget(self.name_label)
        meta_layout.addWidget(self.details_label)
        layout.addWidget(self.meta_widget)

    def load_image(self, item_data: Dict[str, Any]):
        path = item_data.get("path", "")
        if not path or not os.path.exists(path):
            self.clear_preview()
            return

        pix = QPixmap(path)
        if pix.isNull():
            self.clear_preview()
            return

        # Scaled smoothly to canvas constraints (max 250 x 300)
        scaled_pix = pix.scaled(
            250,
            300,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled_pix)
        self.image_label.setVisible(True)
        self.empty_widget.setVisible(False)

        fmt = item_data.get("format", "IMG").upper()
        self.format_badge.setText(fmt)

        w = item_data.get("width", 0)
        h = item_data.get("height", 0)
        sz_str = format_file_size(item_data.get("size_bytes", 0))

        self.name_label.setText(item_data.get("filename", os.path.basename(path)))
        self.details_label.setText(f"Resolusi: <b>{w} × {h} px</b><br>Ukuran: <b>{sz_str}</b>")

    def clear_preview(self):
        self.image_label.clear()
        self.image_label.setVisible(False)
        self.empty_widget.setVisible(True)
        self.format_badge.setText("—")
        self.name_label.setText("Tidak ada gambar terpilih")
        self.details_label.setText("Pilih gambar pada tabel untuk melihat pratinjau.")


class ConvertImagesToPdfPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.image_list: List[Dict[str, Any]] = []
        self.last_output_pdf: Optional[str] = None
        self.worker: Optional[ConvertImagesToPdfWorker] = None

        # Main scroll container
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
        feat_pix = get_feature_icon("Convert Images to PDF", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Convert Images to PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Gabungkan beberapa gambar menjadi satu dokumen PDF.")
        subtitle.setObjectName("PageSubtitle")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(back_btn)
        if not feat_pix.isNull():
            header.addWidget(header_icon)
        header.addLayout(title_box)
        header.addStretch()
        self.content_layout.addLayout(header)

        # Prominent Drop Zone (shown when image list is empty)
        self.drop_zone = ImageDropZone()
        self.drop_zone.files_dropped.connect(self.add_images)
        self.content_layout.addWidget(self.drop_zone)

        # Main Table Toolbar (shown when images are added)
        self.toolbar_widget = QWidget()
        toolbar_layout = QHBoxLayout(self.toolbar_widget)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)

        self.add_btn = QPushButton("+ Tambah Gambar")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setToolTip("Pilih file gambar tambahan dari komputer.")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.browse_images)

        self.add_folder_btn = QPushButton("📁 Tambah Folder")
        self.add_folder_btn.setObjectName("SecondaryButton")
        self.add_folder_btn.setToolTip("Pilih folder berisi gambar untuk ditambahkan.")
        self.add_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_folder_btn.clicked.connect(self.browse_folder)

        self.up_btn = QPushButton("↑ Naik")
        self.up_btn.setObjectName("SecondaryButton")
        self.up_btn.setToolTip("Pindahkan gambar yang dipilih satu tingkat ke atas.")
        self.up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.up_btn.clicked.connect(self.move_up)

        self.down_btn = QPushButton("↓ Turun")
        self.down_btn.setObjectName("SecondaryButton")
        self.down_btn.setToolTip("Pindahkan gambar yang dipilih satu tingkat ke bawah.")
        self.down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_btn.clicked.connect(self.move_down)

        self.del_btn = QPushButton("Hapus Pilihan")
        self.del_btn.setObjectName("SecondaryButton")
        self.del_btn.setToolTip("Hapus gambar terpilih dari daftar.")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self.remove_selected)

        self.clear_btn = QPushButton("Hapus Semua")
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.setToolTip("Kosongkan seluruh daftar gambar.")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_all)

        self.toggle_preview_btn = QPushButton("Sembunyikan Pratinjau")
        self.toggle_preview_btn.setObjectName("SecondaryButton")
        self.toggle_preview_btn.setToolTip("Tampilkan atau sembunyikan panel pratinjau gambar.")
        self.toggle_preview_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggle_preview_btn.setCheckable(True)
        self.toggle_preview_btn.setChecked(True)
        self.toggle_preview_btn.toggled.connect(self.on_toggle_preview)

        toolbar_layout.addWidget(self.add_btn)
        toolbar_layout.addWidget(self.add_folder_btn)
        toolbar_layout.addWidget(self.up_btn)
        toolbar_layout.addWidget(self.down_btn)
        toolbar_layout.addWidget(self.del_btn)
        toolbar_layout.addWidget(self.clear_btn)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.toggle_preview_btn)

        self.toolbar_widget.setVisible(False)
        self.content_layout.addWidget(self.toolbar_widget)

        # Informational Hint for Drag & Drop
        self.hint_label = QLabel(
            "Petunjuk: Seret baris untuk mengatur urutan halaman PDF, atau gunakan tombol Naik/Turun."
        )
        self.hint_label.setObjectName("TableHint")
        self.hint_label.setWordWrap(True)
        self.hint_label.setVisible(False)
        self.content_layout.addWidget(self.hint_label)

        # --- TABLE & PREVIEW WORKSPACE ---
        self.table_preview_layout = QHBoxLayout()
        self.table_preview_layout.setSpacing(16)

        # 1. Image Order Table
        self.table = ImageOrderTable()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["#", "Pratinjau", "Nama File", "Dimensi", "Ukuran", "Aksi"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.table.setColumnWidth(0, 42)
        self.table.setColumnWidth(1, 75)
        self.table.setColumnWidth(5, 85)

        self.table.rows_reordered.connect(self.on_rows_reordered)
        self.table.files_dropped.connect(self.on_files_dropped)
        self.table.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table.setVisible(False)

        # 2. Side Image Preview Panel
        self.preview_panel = ImagePreviewPanel()
        self.preview_panel.setVisible(False)

        self.table_preview_layout.addWidget(self.table, stretch=1)
        self.table_preview_layout.addWidget(self.preview_panel, stretch=0)
        self.content_layout.addLayout(self.table_preview_layout)

        # 3. Output & Format Settings Card
        self.settings_card = QFrame()
        self.settings_card.setObjectName("FeatureCard")
        self.settings_card.setVisible(False)
        settings_vbox = QVBoxLayout(self.settings_card)
        settings_vbox.setContentsMargins(18, 16, 18, 16)
        settings_vbox.setSpacing(12)

        sec_title = QLabel("Pengaturan Dokumen PDF")
        sec_title.setObjectName("SectionTitle")
        settings_vbox.addWidget(sec_title)

        # Row 1: Filename and Destination Folder
        row1 = QHBoxLayout()
        row1.setSpacing(14)

        name_box = QVBoxLayout()
        name_box.setSpacing(4)
        name_lbl = QLabel("Nama File Output:")
        name_lbl.setStyleSheet("font-weight: 600; color: #263445; font-size: 9pt;")
        self.filename_edit = QLineEdit("Converted_Images.pdf")
        self.filename_edit.setObjectName("StyledInput")
        name_box.addWidget(name_lbl)
        name_box.addWidget(self.filename_edit)

        folder_box = QVBoxLayout()
        folder_box.setSpacing(4)
        folder_lbl = QLabel("Folder Penyimpanan:")
        folder_lbl.setStyleSheet("font-weight: 600; color: #263445; font-size: 9pt;")

        folder_input_row = QHBoxLayout()
        folder_input_row.setSpacing(6)
        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName("StyledInput")
        self.folder_edit.setReadOnly(True)

        browse_folder_action = QPushButton("Telusuri...")
        browse_folder_action.setObjectName("SecondaryButton")
        browse_folder_action.setFixedWidth(90)
        browse_folder_action.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_action.clicked.connect(self.browse_destination_dir)

        folder_input_row.addWidget(self.folder_edit, 1)
        folder_input_row.addWidget(browse_folder_action)

        folder_box.addWidget(folder_lbl)
        folder_box.addLayout(folder_input_row)

        row1.addLayout(name_box, 1)
        row1.addLayout(folder_box, 1)
        settings_vbox.addLayout(row1)

        # Row 2: Page Size & Margin options in a clean grid
        options_grid = QGridLayout()
        options_grid.setHorizontalSpacing(16)
        options_grid.setVerticalSpacing(8)

        size_lbl = QLabel("Ukuran Halaman:")
        size_lbl.setStyleSheet("font-weight: 600; color: #263445; font-size: 9pt;")
        options_grid.addWidget(size_lbl, 0, 0)

        size_radios = QHBoxLayout()
        size_radios.setSpacing(14)
        self.radio_fit = QRadioButton("Fit to Image")
        self.radio_fit.setObjectName("RadioChoice")
        self.radio_fit.setToolTip("Ukuran halaman mengikuti dimensi gambar asli.")
        self.radio_fit.setChecked(True)
        self.radio_fit.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_a4_p = QRadioButton("A4 Portrait")
        self.radio_a4_p.setObjectName("RadioChoice")
        self.radio_a4_p.setToolTip("Halaman A4 vertikal (595 × 842 pt).")
        self.radio_a4_p.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_a4_l = QRadioButton("A4 Landscape")
        self.radio_a4_l.setObjectName("RadioChoice")
        self.radio_a4_l.setToolTip("Halaman A4 horizontal (842 × 595 pt).")
        self.radio_a4_l.setCursor(Qt.CursorShape.PointingHandCursor)

        self.size_group = QButtonGroup(self)
        self.size_group.addButton(self.radio_fit)
        self.size_group.addButton(self.radio_a4_p)
        self.size_group.addButton(self.radio_a4_l)

        size_radios.addWidget(self.radio_fit)
        size_radios.addWidget(self.radio_a4_p)
        size_radios.addWidget(self.radio_a4_l)
        size_radios.addStretch()
        options_grid.addLayout(size_radios, 0, 1)

        margin_lbl = QLabel("Margin Halaman:")
        margin_lbl.setStyleSheet("font-weight: 600; color: #263445; font-size: 9pt;")
        options_grid.addWidget(margin_lbl, 1, 0)

        margin_radios = QHBoxLayout()
        margin_radios.setSpacing(14)
        self.radio_m_none = QRadioButton("0 mm (Tanpa)")
        self.radio_m_none.setObjectName("RadioChoice")
        self.radio_m_none.setToolTip("Tanpa margin.")
        self.radio_m_none.setChecked(True)
        self.radio_m_none.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_m_small = QRadioButton("5 mm (Kecil)")
        self.radio_m_small.setObjectName("RadioChoice")
        self.radio_m_small.setToolTip("Margin kecil 5 mm.")
        self.radio_m_small.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_m_std = QRadioButton("12 mm (Standar)")
        self.radio_m_std.setObjectName("RadioChoice")
        self.radio_m_std.setToolTip("Margin standar 12 mm.")
        self.radio_m_std.setCursor(Qt.CursorShape.PointingHandCursor)

        self.margin_group = QButtonGroup(self)
        self.margin_group.addButton(self.radio_m_none)
        self.margin_group.addButton(self.radio_m_small)
        self.margin_group.addButton(self.radio_m_std)

        margin_radios.addWidget(self.radio_m_none)
        margin_radios.addWidget(self.radio_m_small)
        margin_radios.addWidget(self.radio_m_std)
        margin_radios.addStretch()
        options_grid.addLayout(margin_radios, 1, 1)

        settings_vbox.addLayout(options_grid)
        self.content_layout.addWidget(self.settings_card)

        # 4. Progress Bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("TaskProgressBar")
        self.progress_bar.setVisible(False)
        self.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Tambahkan gambar untuk mulai membuat PDF.")
        self.status_label.setObjectName("StatusLabel")
        self.content_layout.addWidget(self.status_label)

        # 5. Action Row (Convert Button, Cancel Button, Reset Button)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.convert_btn = QPushButton("Convert to PDF")
        self.convert_btn.setObjectName("PrimaryButton")
        self.convert_btn.setFixedHeight(42)
        self.convert_btn.setFixedWidth(200)
        self.convert_btn.setEnabled(False)
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.clicked.connect(self.start_convert)

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setFixedHeight(42)
        self.cancel_btn.setFixedWidth(100)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_convert)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setFixedHeight(42)
        self.reset_btn.setFixedWidth(100)
        self.reset_btn.setToolTip("Kosongkan daftar gambar dan reset seluruh pengaturan.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        action_row.addWidget(self.convert_btn)
        action_row.addWidget(self.cancel_btn)
        action_row.addWidget(self.reset_btn)
        action_row.addStretch()
        self.content_layout.addLayout(action_row)

        # 6. Result Card (displayed on completion)
        self.result_card = QFrame()
        self.result_card.setObjectName("ResultCard")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(12)

        self.result_msg_label = QLabel("<b>Images successfully converted to PDF.</b>")
        self.result_msg_label.setStyleSheet("color: #0F5132; font-size: 11pt;")

        self.result_details_label = QLabel()
        self.result_details_label.setStyleSheet("color: #263445; font-size: 9pt;")
        self.result_details_label.setWordWrap(True)

        res_btn_row = QHBoxLayout()
        res_btn_row.setSpacing(10)

        self.open_pdf_btn = QPushButton("Buka File PDF")
        self.open_pdf_btn.setObjectName("PrimaryButton")
        self.open_pdf_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_pdf_btn.clicked.connect(self.open_result_file)

        self.open_folder_btn = QPushButton("Buka Folder Hasil")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_result_folder)

        self.convert_another_btn = QPushButton("Konversi Gambar Lain")
        self.convert_another_btn.setObjectName("SecondaryButton")
        self.convert_another_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_another_btn.clicked.connect(self.reset_form)

        res_btn_row.addWidget(self.open_pdf_btn)
        res_btn_row.addWidget(self.open_folder_btn)
        res_btn_row.addWidget(self.convert_another_btn)
        res_btn_row.addStretch()

        result_layout.addWidget(self.result_msg_label)
        result_layout.addWidget(self.result_details_label)
        result_layout.addLayout(res_btn_row)

        self.content_layout.addWidget(self.result_card)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

        # Connect to settings updates
        get_settings_service().settings_changed.connect(self._on_settings_changed)

    def _on_settings_changed(self):
        first_path = self.image_list[0]["path"] if self.image_list else None
        eff_dir = get_effective_output_dir(first_path)
        self.folder_edit.setText(eff_dir)

    def on_toggle_preview(self, checked: bool):
        self.preview_panel.setVisible(checked)
        if checked:
            self.toggle_preview_btn.setText("Sembunyikan Pratinjau")
            self.on_table_selection_changed()
        else:
            self.toggle_preview_btn.setText("Tampilkan Pratinjau")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = event.size().width()
        if w < 960:
            self.content_layout.setContentsMargins(16, 16, 16, 16)
            self.content_layout.setSpacing(12)
            self.add_btn.setText("+ Tambah")
            self.add_folder_btn.setText("📁 Folder")
            self.up_btn.setText("↑")
            self.down_btn.setText("↓")
            self.del_btn.setText("Hapus")
            self.clear_btn.setText("Kosongkan")
            self.toggle_preview_btn.setText("Tutup" if self.toggle_preview_btn.isChecked() else "Pratinjau")
            if hasattr(self, "preview_panel"):
                self.preview_panel.setFixedWidth(240)
        else:
            self.content_layout.setContentsMargins(32, 28, 32, 28)
            self.content_layout.setSpacing(16)
            self.add_btn.setText("+ Tambah Gambar")
            self.add_folder_btn.setText("📁 Tambah Folder")
            self.up_btn.setText("↑ Naik")
            self.down_btn.setText("↓ Turun")
            self.del_btn.setText("Hapus Pilihan")
            self.clear_btn.setText("Hapus Semua")
            self.toggle_preview_btn.setText("Sembunyikan Pratinjau" if self.toggle_preview_btn.isChecked() else "Lihat Pratinjau")
            if hasattr(self, "preview_panel"):
                self.preview_panel.setFixedWidth(260)

    def browse_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih Dokumen Gambar",
            "",
            "Image Files (*.jpg *.jpeg *.png *.bmp *.tiff *.tif *.webp);;All Files (*.*)",
        )
        if files:
            self.add_images(files)

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Pilih Folder Berisi Gambar")
        if folder:
            paths = []
            try:
                for item in sorted(os.listdir(folder)):
                    p = os.path.join(folder, item)
                    if os.path.isfile(p) and is_supported_image(p):
                        paths.append(p)
            except Exception:
                pass
            if paths:
                self.add_images(paths)

    def browse_destination_dir(self):
        start = self.folder_edit.text().strip() or get_effective_output_dir()
        chosen = QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan PDF", start)
        if chosen:
            self.folder_edit.setText(os.path.abspath(chosen))

    def add_images(self, paths: List[str]):
        if not paths:
            return

        added_count = 0
        duplicate_count = 0
        invalid_files: List[Tuple[str, str]] = []

        existing_paths = {os.path.normcase(os.path.abspath(it["path"])) for it in self.image_list}

        for path in paths:
            norm_p = os.path.abspath(path)
            if os.path.normcase(norm_p) in existing_paths:
                duplicate_count += 1
                continue

            ok, err_msg, meta = validate_image_file(norm_p)
            if not ok:
                invalid_files.append((os.path.basename(norm_p), err_msg))
                continue

            # Generate miniature thumbnail for table display
            pix = QPixmap(norm_p)
            thumb = QPixmap()
            if not pix.isNull():
                thumb = pix.scaled(
                    38,
                    38,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

            item_data = {
                "path": norm_p,
                "filename": meta.get("filename", os.path.basename(norm_p)),
                "width": meta.get("width", 0),
                "height": meta.get("height", 0),
                "format": meta.get("format", ""),
                "size_bytes": meta.get("size_bytes", 0),
                "thumb": thumb,
            }
            self.image_list.append(item_data)
            existing_paths.add(os.path.normcase(norm_p))
            added_count += 1

        # Warn user if invalid files were encountered
        if invalid_files:
            details = "\n".join([f"• {name}: {err}" for name, err in invalid_files[:8]])
            if len(invalid_files) > 8:
                details += f"\n... dan {len(invalid_files) - 8} file lainnya."
            QMessageBox.warning(
                self,
                "File Tidak Valid",
                f"{len(invalid_files)} file gambar tidak dapat ditambahkan:\n\n{details}",
            )

        # Set default output directory if first time adding
        if self.image_list and not self.folder_edit.text().strip():
            self.folder_edit.setText(get_effective_output_dir(self.image_list[0]["path"]))

        self.refresh_table()

    def refresh_table(self):
        count = len(self.image_list)
        self.table.setRowCount(count)

        if count == 0:
            self.drop_zone.setVisible(True)
            self.toolbar_widget.setVisible(False)
            self.hint_label.setVisible(False)
            self.table.setVisible(False)
            self.settings_card.setVisible(False)
            self.convert_btn.setEnabled(False)
            self.status_label.setText("Tambahkan gambar untuk mulai membuat PDF.")
            self.preview_panel.setVisible(False)
            self.preview_panel.clear_preview()
            return

        self.drop_zone.setVisible(False)
        self.toolbar_widget.setVisible(True)
        self.hint_label.setVisible(True)
        self.table.setVisible(True)
        self.settings_card.setVisible(True)
        self.preview_panel.setVisible(self.toggle_preview_btn.isChecked())
        self.convert_btn.setEnabled(True)
        self.status_label.setText(f"{count} gambar siap dikonversi ke PDF.")

        for row, item in enumerate(self.image_list):
            # Col 0: Index
            item_idx = QTableWidgetItem(str(row + 1))
            item_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_idx.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Col 1: Thumbnail icon
            item_thumb = QTableWidgetItem()
            item_thumb.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if not item["thumb"].isNull():
                item_thumb.setIcon(QIcon(item["thumb"]))
            item_thumb.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Col 2: Filename
            item_name = QTableWidgetItem(item["filename"])
            item_name.setToolTip(item["path"])
            item_name.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Col 3: Dimension
            item_dim = QTableWidgetItem(f"{item['width']} × {item['height']}")
            item_dim.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_dim.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Col 4: Size
            sz_str = format_file_size(item["size_bytes"])
            item_sz = QTableWidgetItem(sz_str)
            item_sz.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_sz.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsDragEnabled)

            # Col 5: Delete button
            del_widget = QWidget()
            del_layout = QHBoxLayout(del_widget)
            del_layout.setContentsMargins(0, 0, 0, 0)
            del_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            del_btn = QPushButton("Hapus")
            del_btn.setObjectName("TableDeleteBtn")
            del_btn.setToolTip("Hapus gambar ini dari daftar.")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda ch=False, p=item["path"]: self.remove_by_path(p))
            del_layout.addWidget(del_btn)

            self.table.setItem(row, 0, item_idx)
            self.table.setItem(row, 1, item_thumb)
            self.table.setItem(row, 2, item_name)
            self.table.setItem(row, 3, item_dim)
            self.table.setItem(row, 4, item_sz)
            self.table.setCellWidget(row, 5, del_widget)

        # Select first row if nothing selected
        if self.table.selectedIndexes():
            self.on_table_selection_changed()
        else:
            self.table.selectRow(0)

    def on_table_selection_changed(self):
        selected_rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()))
        if selected_rows and selected_rows[0] < len(self.image_list):
            row = selected_rows[0]
            self.preview_panel.load_image(self.image_list[row])
        else:
            self.preview_panel.clear_preview()

    def remove_by_path(self, path: str):
        norm = os.path.normcase(os.path.abspath(path))
        self.image_list = [it for it in self.image_list if os.path.normcase(os.path.abspath(it["path"])) != norm]
        self.refresh_table()

    def remove_selected(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows:
            return
        for r in selected_rows:
            if 0 <= r < len(self.image_list):
                del self.image_list[r]
        self.refresh_table()

    def clear_all(self):
        if not self.image_list:
            return
        self.image_list.clear()
        self.refresh_table()

    def move_up(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()))
        if not selected_rows or selected_rows[0] == 0:
            return

        for r in selected_rows:
            self.image_list[r], self.image_list[r - 1] = self.image_list[r - 1], self.image_list[r]

        self.refresh_table()
        self.table.clearSelection()
        for r in selected_rows:
            self.table.selectRow(r - 1)

    def move_down(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        if not selected_rows or selected_rows[0] >= len(self.image_list) - 1:
            return

        for r in selected_rows:
            self.image_list[r], self.image_list[r + 1] = self.image_list[r + 1], self.image_list[r]

        self.refresh_table()
        self.table.clearSelection()
        for r in selected_rows:
            self.table.selectRow(r + 1)

    def on_rows_reordered(self, selected_rows: List[int], target_row: int):
        selected_indices = sorted(set(selected_rows))
        if not selected_indices:
            return

        moving_items = [self.image_list[r] for r in selected_indices]
        remaining = [item for idx, item in enumerate(self.image_list) if idx not in selected_indices]

        # Calculate insertion index in remaining list
        adjusted_target = target_row
        for idx in selected_indices:
            if idx < target_row:
                adjusted_target -= 1
        adjusted_target = max(0, min(adjusted_target, len(remaining)))

        new_list = remaining[:adjusted_target] + moving_items + remaining[adjusted_target:]
        self.image_list = new_list
        self.refresh_table()

        # Reselect moved rows
        self.table.clearSelection()
        for i in range(len(moving_items)):
            self.table.selectRow(adjusted_target + i)

    def on_files_dropped(self, paths: List[str], target_row: int):
        self.add_images(paths)

    def get_selected_page_format(self) -> str:
        if self.radio_a4_p.isChecked():
            return "a4_portrait"
        elif self.radio_a4_l.isChecked():
            return "a4_landscape"
        return "fit_to_image"

    def get_selected_margin_mm(self) -> float:
        if self.radio_m_small.isChecked():
            return 5.0
        elif self.radio_m_std.isChecked():
            return 12.0
        return 0.0

    def start_convert(self):
        if not self.image_list:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal 1 file gambar terlebih dahulu.")
            return

        out_name = self.filename_edit.text().strip()
        if not out_name:
            out_name = "Converted_Images.pdf"
            self.filename_edit.setText(out_name)
        elif not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"
            self.filename_edit.setText(out_name)

        folder = self.folder_edit.text().strip()
        if not folder or not os.path.exists(folder):
            folder = get_effective_output_dir(self.image_list[0]["path"])
            self.folder_edit.setText(folder)

        target_path = os.path.abspath(os.path.join(folder, out_name))

        # Check conflict handling
        settings = get_settings_service()
        conflict_action = settings.get("conflict_action", "confirm")

        if os.path.exists(target_path):
            if conflict_action == "auto_number":
                target_path = get_safe_destination_path(folder, out_name)
                self.filename_edit.setText(os.path.basename(target_path))
            else:
                confirm = QMessageBox.question(
                    self,
                    "Konfirmasi Penimpaan File",
                    f"File '{os.path.basename(target_path)}' sudah ada di folder tujuan.\n"
                    "Apakah Anda ingin menggantinya?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

        # Prepare UI for background processing
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.image_list))
        self.progress_bar.setValue(0)
        self.cancel_btn.setVisible(True)
        self.result_card.setVisible(False)
        self.status_label.setText("Memulai proses konversi gambar ke PDF...")

        image_paths = [it["path"] for it in self.image_list]
        page_format = self.get_selected_page_format()
        margin_mm = self.get_selected_margin_mm()

        self.worker = ConvertImagesToPdfWorker(
            image_paths=image_paths,
            output_path=target_path,
            page_format=page_format,
            margin_mm=margin_mm,
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def cancel_convert(self):
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Membatalkan proses konversi...")
            self.worker.cancel()
            self.cancel_btn.setEnabled(False)

    def on_worker_progress(self, current: int, total: int, message: str):
        if total > 0:
            self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def on_worker_finished(self, success: bool, message: str, result_data: Optional[Dict[str, Any]]):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

        if success and result_data:
            self.last_output_pdf = result_data.get("output_path", "")
            pages = result_data.get("total_pages", 0)
            sz_str = format_file_size(result_data.get("file_size", 0))

            self.result_msg_label.setText("<b>Images successfully converted to PDF.</b>")
            self.result_details_label.setText(
                f"• Jumlah Halaman: <b>{pages} halaman</b><br>"
                f"• Ukuran Dokumen: <b>{sz_str}</b><br>"
                f"• Lokasi Penyimpanan: <code>{self.last_output_pdf}</code>"
            )
            self.result_card.setVisible(True)
            self.status_label.setText(f"Selesai! File tersimpan di: {self.last_output_pdf}")

            # Check post-processing settings
            settings = get_settings_service()
            if settings.get("auto_open_folder"):
                self.open_result_folder()
            if settings.get("auto_open_file"):
                self.open_result_file()

        else:
            is_cancelled = result_data and result_data.get("is_cancelled", False)
            if is_cancelled:
                self.status_label.setText("Proses konversi dibatalkan.")
            else:
                self.status_label.setText("Konversi gagal.")
                QMessageBox.critical(self, "Konversi Gagal", message)

    def open_result_file(self):
        if self.last_output_pdf and os.path.exists(self.last_output_pdf):
            open_file_with_default_app(self.last_output_pdf)

    def open_result_folder(self):
        if self.last_output_pdf and os.path.exists(self.last_output_pdf):
            open_in_file_manager(self.last_output_pdf)
        else:
            folder = self.folder_edit.text().strip()
            if folder and os.path.exists(folder):
                open_in_file_manager(folder)

    def set_ui_busy(self, busy: bool):
        self.convert_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.add_btn.setEnabled(not busy)
        self.add_folder_btn.setEnabled(not busy)
        self.up_btn.setEnabled(not busy)
        self.down_btn.setEnabled(not busy)
        self.del_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.table.setEnabled(not busy)
        self.settings_card.setEnabled(not busy)

    def reset_form(self):
        """Reset the form and image list back to initial empty state."""
        self.image_list.clear()
        self.last_output_pdf = None
        self.filename_edit.setText("Converted_Images.pdf")
        self.radio_fit.setChecked(True)
        self.radio_m_none.setChecked(True)
        self.folder_edit.setText(get_effective_output_dir())
        self.result_card.setVisible(False)
        self.progress_bar.setVisible(False)
        self.refresh_table()
        self.status_label.setText("Tambahkan gambar untuk mulai membuat PDF.")

