import os
from typing import List, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.merge_service import merge_pdfs
from app.utils.file_utils import format_file_size, open_in_file_manager
from app.utils.validators import validate_pdf_file
from app.workers.pdf_worker import PdfTaskWorker


class MergeDropZone(QFrame):
    files_dropped = Signal(list)

    def __init__(self):
        super().__init__()
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 24, 16, 24)
        layout.setSpacing(6)

        title = QLabel("Tarik dan lepaskan file PDF ke sini")
        title.setObjectName("DropTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel("atau klik untuk memilih beberapa file PDF dari komputer")
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


class MergePage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.file_list: List[Dict[str, Any]] = []
        self.worker: PdfTaskWorker = None
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
        layout = QVBoxLayout(content)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

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
        layout.addLayout(header)

        # Drag and Drop Zone
        self.drop_zone = MergeDropZone()
        self.drop_zone.setToolTip("Klik atau seret file PDF ke sini untuk ditambahkan ke daftar.")
        self.drop_zone.files_dropped.connect(self.add_files)
        self.drop_zone.mousePressEvent = lambda e: self.browse_files()
        layout.addWidget(self.drop_zone)

        # Action Toolbar for List Management
        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)

        self.add_btn = QPushButton("+ Tambah PDF")
        self.add_btn.setObjectName("PrimaryButton")
        self.add_btn.setToolTip("Pilih file PDF tambahan dari penyimpanan komputer.")
        self.add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_btn.clicked.connect(self.browse_files)

        self.up_btn = QPushButton("▲ Naikkan")
        self.up_btn.setObjectName("SecondaryButton")
        self.up_btn.setToolTip("Pindahkan file yang dipilih satu tingkat ke atas.")
        self.up_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.up_btn.clicked.connect(self.move_up)

        self.down_btn = QPushButton("▼ Turunkan")
        self.down_btn.setObjectName("SecondaryButton")
        self.down_btn.setToolTip("Pindahkan file yang dipilih satu tingkat ke bawah.")
        self.down_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.down_btn.clicked.connect(self.move_down)

        self.del_btn = QPushButton("Hapus Pilihan")
        self.del_btn.setObjectName("SecondaryButton")
        self.del_btn.setToolTip("Hapus file yang dipilih saat ini dari daftar.")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.clicked.connect(self.remove_selected)

        self.clear_btn = QPushButton("Hapus Semua")
        self.clear_btn.setObjectName("SecondaryButton")
        self.clear_btn.setToolTip("Kosongkan seluruh daftar file.")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_all)

        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.up_btn)
        toolbar.addWidget(self.down_btn)
        toolbar.addWidget(self.del_btn)
        toolbar.addWidget(self.clear_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Table of Added Files
        self.table = QTableWidget()
        self.table.setObjectName("FileTable")
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Urutan", "Nama File", "Ukuran", "Jumlah Halaman"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setMinimumHeight(220)
        layout.addWidget(self.table)

        # Progress & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Tambahkan minimal 2 file PDF untuk mulai menggabungkan.")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

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
        layout.addLayout(bottom_bar)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def browse_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Pilih Dokumen PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if files:
            self.add_files(files)

    def add_files(self, paths: List[str]):
        added_count = 0
        existing_paths = {item["path"] for item in self.file_list}

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
            self.file_list.append(
                {
                    "path": norm_path,
                    "name": os.path.basename(norm_path),
                    "size": format_file_size(size_bytes),
                    "pages": page_count,
                }
            )
            existing_paths.add(norm_path)
            added_count += 1

        self.refresh_table()

    def refresh_table(self):
        self.table.setRowCount(len(self.file_list))
        for row, item in enumerate(self.file_list):
            item_order = QTableWidgetItem(f"{row + 1}")
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_name = QTableWidgetItem(item["name"])
            item_name.setToolTip(item["path"])
            item_size = QTableWidgetItem(item["size"])
            item_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item_pages = QTableWidgetItem(f"{item['pages']} hal")
            item_pages.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            self.table.setItem(row, 0, item_order)
            self.table.setItem(row, 1, item_name)
            self.table.setItem(row, 2, item_size)
            self.table.setItem(row, 3, item_pages)

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

    def move_up(self):
        selected_row = self.table.currentRow()
        if selected_row > 0:
            self.file_list[selected_row], self.file_list[selected_row - 1] = (
                self.file_list[selected_row - 1],
                self.file_list[selected_row],
            )
            self.refresh_table()
            self.table.selectRow(selected_row - 1)

    def move_down(self):
        selected_row = self.table.currentRow()
        if 0 <= selected_row < len(self.file_list) - 1:
            self.file_list[selected_row], self.file_list[selected_row + 1] = (
                self.file_list[selected_row + 1],
                self.file_list[selected_row],
            )
            self.refresh_table()
            self.table.selectRow(selected_row + 1)

    def remove_selected(self):
        selected_row = self.table.currentRow()
        if 0 <= selected_row < len(self.file_list):
            del self.file_list[selected_row]
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
