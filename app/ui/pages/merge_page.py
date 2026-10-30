import os
import re
from typing import List, Dict, Any, Optional

from PySide6.QtCore import Qt, Signal, QPoint, QMimeData
from PySide6.QtGui import QDrag, QPainter, QPen, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.merge_service import merge_pdfs
from app.utils.file_utils import format_file_size, open_in_file_manager
from app.utils.validators import validate_pdf_file
from app.workers.pdf_worker import PdfTaskWorker


def natural_sort_key(s: str) -> list:
    """Helper for natural alphanumeric sorting (e.g. Doc 2 comes before Doc 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r"(\d+)", s)]


class MergeDropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 20, 16, 20)
        layout.setSpacing(6)

        title = QLabel("Tarik dan lepaskan file PDF ke sini")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("atau klik untuk memilih file PDF dari komputer")
        hint.setObjectName("DropHint")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(hint)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [url.toLocalFile() for url in urls if url.toLocalFile().lower().endswith(".pdf")]
        if paths:
            self.files_dropped.emit(paths)
        event.acceptProposedAction()


class MergeTableWidget(QTableWidget):
    """
    Enhanced QTableWidget supporting:
    1. Custom drag-and-drop row reordering (drag up/down without item deletion).
    2. Direct drop of external PDF files from Windows Explorer.
    3. Visual drop indicator line during drag.
    4. Multi-selection support.
    """
    rows_reordered = Signal(list, int)  # selected_rows, target_row
    files_dropped = Signal(list, int)   # file_paths, target_row

    def __init__(self):
        super().__init__()
        self.setObjectName("FileTable")
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.viewport().setAcceptDrops(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDropIndicatorShown(False)  # Handled by custom paintEvent for clean visual line
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.setWordWrap(False)
        self.setMinimumHeight(240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set consistent, comfortable row height so buttons are never clipped
        self.verticalHeader().setDefaultSectionSize(40)
        self.verticalHeader().setVisible(False)

        self._drag_start_rows: List[int] = []
        self._drop_target_row: Optional[int] = None

    def startDrag(self, supportedActions):
        selected = sorted(set(index.row() for index in self.selectedIndexes()))
        if not selected:
            return
        self._drag_start_rows = selected

        # Use custom QDrag without super().startDrag() so Qt doesn't delete dragged cells
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-jackpdf-row-order", b"")
        drag.setMimeData(mime)

        drag.exec(Qt.DropAction.MoveAction)
        self._drag_start_rows = []
        self._drop_target_row = None
        self.viewport().update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-jackpdf-row-order"):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-jackpdf-row-order"):
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
            paths = [
                url.toLocalFile()
                for url in urls
                if url.toLocalFile().lower().endswith(".pdf")
            ]
            if paths:
                self.files_dropped.emit(paths, target_row)
            event.acceptProposedAction()
        elif event.mimeData().hasFormat("application/x-jackpdf-row-order"):
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
        if self._drop_target_row is not None and self.rowCount() > 0:
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor("#2563EB"), 3))
            if self._drop_target_row < self.rowCount():
                item = self.item(self._drop_target_row, 0)
                if item:
                    y = self.visualItemRect(item).top()
                else:
                    y = 0
            else:
                item = self.item(self.rowCount() - 1, 0)
                if item:
                    y = self.visualItemRect(item).bottom()
                else:
                    y = self.viewport().height()
            painter.drawLine(0, y, self.viewport().width(), y)


class MergePage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.file_list: List[Dict[str, Any]] = []
        self.worker: Optional[PdfTaskWorker] = None
        self.last_output_file: str = ""

        # Main Layout with Scroll Area for responsive sizing
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("ContentScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("ContentWidget")
        self.content_layout = QVBoxLayout(content)
        self.content_layout.setContentsMargins(32, 28, 32, 28)
        self.content_layout.setSpacing(18)

        # Header Section
        header = QHBoxLayout()
        back_btn = QPushButton("←  Kembali")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setToolTip("Kembali ke halaman utama JackPDF.")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back.emit)

        title_box = QVBoxLayout()
        title = QLabel("Merge PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Gabungkan beberapa dokumen PDF menjadi satu file berurutan.")
        subtitle.setObjectName("PageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(back_btn)
        header.addSpacing(12)
        header.addLayout(title_box)
        header.addStretch()
        self.content_layout.addLayout(header)

        # Drag and Drop Zone (Top Area)
        self.drop_zone = MergeDropZone()
        self.drop_zone.setToolTip("Klik atau seret file PDF ke sini untuk ditambahkan ke daftar.")
        self.drop_zone.files_dropped.connect(self.add_files)
        self.drop_zone.mousePressEvent = lambda e: self.browse_files()
        self.content_layout.addWidget(self.drop_zone)

        # Action Toolbar for List Management
        self.toolbar = QHBoxLayout()
        self.toolbar.setSpacing(8)

        self.add_btn = QPushButton("+ Tambah PDF")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setToolTip("Pilih file PDF tambahan dari penyimpanan komputer.")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.browse_files)

        # Sort Dropdown Menu Button (Formal label)
        self.sort_btn = QPushButton("Urutkan ▾")
        self.sort_btn.setObjectName("SecondaryButton")
        self.sort_btn.setToolTip("Urutkan file secara otomatis berdasarkan nama, ukuran, atau jumlah halaman.")
        self.sort_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setup_sort_menu()

        self.up_btn = QPushButton("↑ Naik")
        self.up_btn.setObjectName("SecondaryButton")
        self.up_btn.setToolTip("Pindahkan file yang dipilih satu tingkat ke atas.")
        self.up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.up_btn.clicked.connect(self.move_up)

        self.down_btn = QPushButton("↓ Turun")
        self.down_btn.setObjectName("SecondaryButton")
        self.down_btn.setToolTip("Pindahkan file yang dipilih satu tingkat ke bawah.")
        self.down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_btn.clicked.connect(self.move_down)

        self.del_btn = QPushButton("Hapus Pilihan")
        self.del_btn.setObjectName("SecondaryButton")
        self.del_btn.setToolTip("Hapus file yang sedang dipilih dari daftar.")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self.remove_selected)

        self.clear_btn = QPushButton("Hapus Semua")
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.setToolTip("Kosongkan seluruh daftar file.")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_all)

        self.toolbar.addWidget(self.add_btn)
        self.toolbar.addWidget(self.sort_btn)
        self.toolbar.addWidget(self.up_btn)
        self.toolbar.addWidget(self.down_btn)
        self.toolbar.addWidget(self.del_btn)
        self.toolbar.addWidget(self.clear_btn)
        self.toolbar.addStretch()
        self.content_layout.addLayout(self.toolbar)

        # Informational Hint for Drag & Drop (Formal text)
        self.hint_label = QLabel(
            "Petunjuk: Seret baris pada tabel untuk mengatur urutan dokumen, atau tarik file PDF langsung ke tabel."
        )
        self.hint_label.setObjectName("TableHint")
        self.content_layout.addWidget(self.hint_label)

        # Table of Added Files with Drag-and-Drop Reordering
        self.table = MergeTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Urutan",
            "Nama File",
            "Ukuran",
            "Halaman",
            "Aksi",
        ])

        # Precise, responsive column sizing
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(0, 65)

        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)

        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(2, 90)

        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(3, 85)

        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.table.setColumnWidth(4, 95)

        self.table.rows_reordered.connect(self.on_rows_reordered)
        self.table.files_dropped.connect(self.add_files)
        self.content_layout.addWidget(self.table)

        # Progress & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)
        self.content_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Tambahkan minimal 2 file PDF untuk mulai menggabungkan.")
        self.status_label.setObjectName("StatusLabel")
        self.content_layout.addWidget(self.status_label)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.merge_btn = QPushButton("Gabungkan PDF Sekarang")
        self.merge_btn.setObjectName("ActionLargeButton")
        self.merge_btn.setToolTip("Pilih lokasi penyimpanan dan gabungkan semua file PDF sesuai urutan tabel.")
        self.merge_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_btn.setEnabled(False)
        self.merge_btn.clicked.connect(self.start_merge)

        self.open_folder_btn = QPushButton("Buka Folder Hasil")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setToolTip("Buka folder tempat file hasil disimpan di Windows Explorer.")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        bottom_bar.addWidget(self.merge_btn)
        bottom_bar.addWidget(self.open_folder_btn)
        bottom_bar.addStretch()
        self.content_layout.addLayout(bottom_bar)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        # Responsive padding & compact toolbar for narrower windows
        if width < 640:
            self.content_layout.setContentsMargins(16, 16, 16, 16)
            self.content_layout.setSpacing(12)
            self.add_btn.setText("+ Tambah")
            self.up_btn.setText("↑")
            self.down_btn.setText("↓")
            self.del_btn.setText("Hapus")
            self.clear_btn.setText("Kosongkan")
        else:
            self.content_layout.setContentsMargins(32, 28, 32, 28)
            self.content_layout.setSpacing(18)
            self.add_btn.setText("+ Tambah PDF")
            self.up_btn.setText("↑ Naik")
            self.down_btn.setText("↓ Turun")
            self.del_btn.setText("Hapus Pilihan")
            self.clear_btn.setText("Hapus Semua")

    def setup_sort_menu(self):
        sort_menu = QMenu(self)
        sort_menu.setObjectName("StyledMenu")

        act_name_asc = sort_menu.addAction("Nama File (A → Z)")
        act_name_asc.triggered.connect(lambda: self.sort_by_name(reverse=False))

        act_name_desc = sort_menu.addAction("Nama File (Z → A)")
        act_name_desc.triggered.connect(lambda: self.sort_by_name(reverse=True))

        sort_menu.addSeparator()

        act_size_asc = sort_menu.addAction("Ukuran (Terkecil → Terbesar)")
        act_size_asc.triggered.connect(lambda: self.sort_by_size(reverse=False))

        act_size_desc = sort_menu.addAction("Ukuran (Terbesar → Terkecil)")
        act_size_desc.triggered.connect(lambda: self.sort_by_size(reverse=True))

        sort_menu.addSeparator()

        act_pages_asc = sort_menu.addAction("Jumlah Halaman (Sedikit → Banyak)")
        act_pages_asc.triggered.connect(lambda: self.sort_by_pages(reverse=False))

        act_pages_desc = sort_menu.addAction("Jumlah Halaman (Banyak → Sedikit)")
        act_pages_desc.triggered.connect(lambda: self.sort_by_pages(reverse=True))

        sort_menu.addSeparator()

        act_reverse = sort_menu.addAction("Balikkan Urutan (Reverse)")
        act_reverse.triggered.connect(self.reverse_order)

        self.sort_btn.setMenu(sort_menu)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih Dokumen PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if files:
            self.add_files(files)

    def add_files(self, paths: List[str], target_row: Optional[int] = None):
        existing_paths = {item["path"] for item in self.file_list}
        new_items = []

        for path in paths:
            norm_path = os.path.abspath(path)
            if norm_path in existing_paths:
                continue

            is_valid, err_msg, page_count = validate_pdf_file(norm_path)
            if not is_valid:
                QMessageBox.warning(
                    self,
                    "File Tidak Valid",
                    f"File '{os.path.basename(norm_path)}' tidak dapat ditambahkan:\n{err_msg}",
                )
                continue

            size_bytes = os.path.getsize(norm_path)
            new_items.append(
                {
                    "path": norm_path,
                    "name": os.path.basename(norm_path),
                    "size": format_file_size(size_bytes),
                    "size_bytes": size_bytes,
                    "pages": page_count,
                }
            )
            existing_paths.add(norm_path)

        if new_items:
            if target_row is not None and 0 <= target_row <= len(self.file_list):
                for i, item in enumerate(new_items):
                    self.file_list.insert(target_row + i, item)
            else:
                self.file_list.extend(new_items)
            self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, item in enumerate(self.file_list):
            # Col 0: Drag handle & order index (Formal grip symbol)
            item_order = QTableWidgetItem(f"⋮  {row + 1}")
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_order.setToolTip("Seret baris ini ke atas atau ke bawah untuk mengubah urutan.")
            item_order.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )

            # Col 1: Filename
            item_name = QTableWidgetItem(item["name"])
            item_name.setToolTip(item["path"])
            item_name.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )

            # Col 2: Size
            item_size = QTableWidgetItem(item["size"])
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_size.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )

            # Col 3: Pages
            item_pages = QTableWidgetItem(f"{item['pages']} hal")
            item_pages.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pages.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )

            self.table.setItem(row, 0, item_order)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_size)
            self.table.setItem(row, 3, item_pages)

            # Col 4: Action (Only formal Delete button, vertically centered)
            action_widget = QWidget()
            action_widget.setObjectName("RowActionContainer")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setSpacing(0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            del_btn = QPushButton("Hapus")
            del_btn.setObjectName("TableDeleteBtn")
            del_btn.setToolTip("Hapus file ini dari daftar.")
            del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            del_btn.clicked.connect(lambda checked=False, p=item["path"]: self.remove_by_path(p))

            action_layout.addWidget(del_btn)
            self.table.setCellWidget(row, 4, action_widget)

        count = len(self.file_list)
        if count >= 2:
            self.merge_btn.setEnabled(True)
            total_pages = sum(item["pages"] for item in self.file_list)
            self.status_label.setText(f"{count} file siap digabungkan (Total {total_pages} halaman).")
        elif count == 1:
            self.merge_btn.setEnabled(False)
            self.status_label.setText("Tambahkan minimal 1 file lagi untuk digabungkan.")
        else:
            self.merge_btn.setEnabled(False)
            self.status_label.setText("Tambahkan minimal 2 file PDF untuk mulai menggabungkan.")

    def on_rows_reordered(self, selected_rows: List[int], target_row: int):
        selected_indices = sorted(set(selected_rows))
        if not selected_indices:
            return

        items_to_move = [self.file_list[i] for i in selected_indices]
        remaining = [item for i, item in enumerate(self.file_list) if i not in selected_indices]

        num_before = sum(1 for r in selected_indices if r < target_row)
        new_insert_index = max(0, min(len(remaining), target_row - num_before))

        self.file_list = (
            remaining[:new_insert_index] + items_to_move + remaining[new_insert_index:]
        )
        self.refresh_table()

        # Re-select moved rows in their new positions
        self.table.clearSelection()
        for r in range(new_insert_index, new_insert_index + len(items_to_move)):
            self.table.selectRow(r)

    def remove_by_path(self, path: str):
        self.file_list = [f for f in self.file_list if f["path"] != path]
        self.refresh_table()

    def remove_at_row(self, row: int):
        if 0 <= row < len(self.file_list):
            del self.file_list[row]
            self.refresh_table()

    def move_up(self):
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()))
        if not selected_rows or selected_rows[0] == 0:
            return

        for r in selected_rows:
            self.file_list[r], self.file_list[r - 1] = self.file_list[r - 1], self.file_list[r]
        self.refresh_table()

        self.table.clearSelection()
        for r in selected_rows:
            self.table.selectRow(r - 1)

    def move_down(self):
        selected_rows = sorted(
            set(index.row() for index in self.table.selectedIndexes()), reverse=True
        )
        if not selected_rows or selected_rows[0] >= len(self.file_list) - 1:
            return

        for r in selected_rows:
            self.file_list[r], self.file_list[r + 1] = self.file_list[r + 1], self.file_list[r]
        self.refresh_table()

        self.table.clearSelection()
        for r in selected_rows:
            self.table.selectRow(r + 1)

    def sort_by_name(self, reverse: bool = False):
        if len(self.file_list) < 2:
            return
        self.file_list.sort(key=lambda x: natural_sort_key(x["name"]), reverse=reverse)
        self.refresh_table()

    def sort_by_size(self, reverse: bool = False):
        if len(self.file_list) < 2:
            return
        self.file_list.sort(key=lambda x: x.get("size_bytes", 0), reverse=reverse)
        self.refresh_table()

    def sort_by_pages(self, reverse: bool = False):
        if len(self.file_list) < 2:
            return
        self.file_list.sort(key=lambda x: x.get("pages", 0), reverse=reverse)
        self.refresh_table()

    def reverse_order(self):
        if len(self.file_list) < 2:
            return
        self.file_list.reverse()
        self.refresh_table()

    def remove_selected(self):
        selected_rows = sorted(
            set(index.row() for index in self.table.selectedIndexes()), reverse=True
        )
        if not selected_rows:
            return
        for row in selected_rows:
            if 0 <= row < len(self.file_list):
                del self.file_list[row]
        self.refresh_table()

    def clear_all(self):
        if not self.file_list:
            return
        self.file_list.clear()
        self.refresh_table()

    def start_merge(self):
        if len(self.file_list) < 2:
            QMessageBox.information(self, "Perhatian", "Pilih minimal 2 file PDF untuk digabungkan.")
            return

        # Determine default directory from first input file
        default_dir = os.path.dirname(self.file_list[0]["path"])
        default_save_path = os.path.join(default_dir, "JackPDF_Merged.pdf")

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan File Hasil Penggabungan",
            default_save_path,
            "PDF Files (*.pdf)",
        )

        if not save_path:
            return

        if not save_path.lower().endswith(".pdf"):
            save_path += ".pdf"

        # Check collision with input files
        norm_save = os.path.normcase(os.path.abspath(save_path))
        for item in self.file_list:
            if os.path.normcase(os.path.abspath(item["path"])) == norm_save:
                QMessageBox.critical(
                    self,
                    "Nama File Tidak Diizinkan",
                    "File output tidak boleh menimpa salah satu file input yang sedang digabungkan.\nSilakan pilih nama atau lokasi lain.",
                )
                return

        # UI State during processing
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(self.file_list))
        self.progress_bar.setValue(0)
        self.status_label.setText("Menyiapkan penggabungan...")

        input_paths = [item["path"] for item in self.file_list]

        # Launch background worker thread
        self.worker = PdfTaskWorker(merge_pdfs, input_paths, save_path)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(lambda s, m, d: self.on_finished(s, m, save_path))
        self.worker.start()

    def on_progress(self, current: int, total: int, message: str):
        self.progress_bar.setValue(current)
        self.status_label.setText(message)

    def on_finished(self, success: bool, message: str, output_path: str):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)

        if success:
            self.last_output_file = output_path
            self.status_label.setText(f"Selesai! Disimpan ke: {os.path.basename(output_path)}")
            self.open_folder_btn.setVisible(True)

            reply = QMessageBox.information(
                self,
                "Berhasil Menggabungkan PDF",
                f"{message}\n\nLokasi file:\n{output_path}\n\nApakah kamu ingin membuka folder penyimpanan sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.open_output_folder()
        else:
            self.status_label.setText("Penggabungan gagal.")
            QMessageBox.critical(self, "Penggabungan Gagal", message)

    def set_ui_busy(self, busy: bool):
        self.merge_btn.setEnabled(not busy)
        self.add_btn.setEnabled(not busy)
        self.sort_btn.setEnabled(not busy)
        self.up_btn.setEnabled(not busy)
        self.down_btn.setEnabled(not busy)
        self.del_btn.setEnabled(not busy)
        self.clear_btn.setEnabled(not busy)
        self.table.setEnabled(not busy)

    def open_output_folder(self):
        if self.last_output_file and os.path.exists(self.last_output_file):
            open_in_file_manager(self.last_output_file)
        elif self.last_output_file:
            folder = os.path.dirname(self.last_output_file)
            if os.path.exists(folder):
                open_in_file_manager(folder)
