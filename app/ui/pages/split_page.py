import os
from typing import List, Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.split_service import (
    split_pdf_by_range,
    split_pdf_each_page,
    split_pdf_fixed_size,
)
from app.utils.file_utils import format_file_size, open_in_file_manager
from app.utils.validators import parse_page_range, validate_pdf_file
from app.workers.pdf_worker import PdfTaskWorker


class SplitDropZone(QFrame):
    file_dropped = Signal(str)

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

        hint = QLabel("atau klik untuk memilih 1 file PDF yang ingin dipisahkan")
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
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith(".pdf"):
                self.file_dropped.emit(path)
                break
        event.acceptProposedAction()


class SplitPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.current_page_count: int = 0
        self.output_dir: str = ""
        self.worker: Optional[PdfTaskWorker] = None
        self.last_output_dir: str = ""

        # Scroll Area for responsive sizing
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
        title = QLabel("Split PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Pisahkan halaman dokumen PDF sesuai kebutuhan Anda.")
        subtitle.setObjectName("PageSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header.addWidget(back_btn)
        header.addSpacing(12)
        header.addLayout(title_box)
        header.addStretch()
        layout.addLayout(header)

        # Drop Zone
        self.drop_zone = SplitDropZone()
        self.drop_zone.setToolTip("Klik atau seret file PDF ke sini untuk memilih file.")
        self.drop_zone.file_dropped.connect(self.load_pdf_file)
        self.drop_zone.mousePressEvent = lambda e: self.browse_single_file()
        layout.addWidget(self.drop_zone)

        # File Info Card (Hidden until file selected)
        self.info_card = QFrame()
        self.info_card.setObjectName("InfoCard")
        self.info_card.setVisible(False)
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 14, 16, 14)

        icon_label = QLabel("PDF")
        icon_label.setObjectName("FeatureIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(40, 40)
        info_layout.addWidget(icon_label)

        self.file_details_label = QLabel("Detail File")
        self.file_details_label.setObjectName("FileDetailsText")
        info_layout.addWidget(self.file_details_label, 1)

        change_btn = QPushButton("Ganti File")
        change_btn.setObjectName("SecondaryButton")
        change_btn.setToolTip("Pilih file PDF lain dari komputer.")
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.clicked.connect(self.browse_single_file)
        info_layout.addWidget(change_btn)

        layout.addWidget(self.info_card)

        # Mode Selection Card
        self.mode_card = QFrame()
        self.mode_card.setObjectName("FeatureCard")
        mode_layout = QVBoxLayout(self.mode_card)
        mode_layout.setContentsMargins(20, 18, 20, 18)
        mode_layout.setSpacing(12)

        mode_title = QLabel("Pilih Metode Pemisahan")
        mode_title.setObjectName("SectionTitle")
        mode_layout.addWidget(mode_title)

        self.btn_group = QButtonGroup(self)

        # Option 1: Custom page range
        self.radio_range = QRadioButton("Rentang Halaman Tertentu")
        self.radio_range.setObjectName("RadioChoice")
        self.radio_range.setChecked(True)
        self.radio_range.setToolTip("Ekspor halaman tertentu sesuai nomor atau rentang yang Anda tulis.")
        self.btn_group.addButton(self.radio_range, 1)
        mode_layout.addWidget(self.radio_range)

        self.range_input_box = QVBoxLayout()
        self.range_input_box.setContentsMargins(24, 0, 0, 8)
        self.range_edit = QLineEdit()
        self.range_edit.setObjectName("StyledInput")
        self.range_edit.setPlaceholderText("Contoh: 1-3, 5, 8-10")
        self.range_edit.setToolTip("Format: angka tunggal (5), rentang (1-3), pisahkan dengan koma.")
        self.range_edit.textChanged.connect(self.validate_inputs)
        self.range_input_box.addWidget(self.range_edit)

        self.range_hint = QLabel("Contoh penulisan: 1-3, 5, 8-10 (tidak boleh ada halaman 0 atau duplikat).")
        self.range_hint.setObjectName("InputHint")
        self.range_input_box.addWidget(self.range_hint)
        mode_layout.addLayout(self.range_input_box)

        # Option 2: Each page
        self.radio_each = QRadioButton("Satu File Per Halaman")
        self.radio_each.setObjectName("RadioChoice")
        self.radio_each.setToolTip("Setiap halaman PDF akan diekspor menjadi 1 file terpisah (nama_page_001.pdf).")
        self.btn_group.addButton(self.radio_each, 2)
        mode_layout.addWidget(self.radio_each)

        # Option 3: Fixed chunk size
        self.radio_chunk = QRadioButton("Rentang Berukuran Tetap (Bagi Rata)")
        self.radio_chunk.setObjectName("RadioChoice")
        self.radio_chunk.setToolTip("Bagi dokumen menjadi beberapa file dengan jumlah halaman yang sama per file.")
        self.btn_group.addButton(self.radio_chunk, 3)
        mode_layout.addWidget(self.radio_chunk)

        self.chunk_input_box = QHBoxLayout()
        self.chunk_input_box.setContentsMargins(24, 0, 0, 4)
        chunk_lbl = QLabel("Jumlah halaman per file:")
        self.chunk_spin = QSpinBox()
        self.chunk_spin.setObjectName("StyledSpinBox")
        self.chunk_spin.setRange(1, 9999)
        self.chunk_spin.setValue(2)
        self.chunk_spin.setToolTip("Tentukan berapa halaman yang ingin dimasukkan ke dalam setiap file output.")
        self.chunk_spin.valueChanged.connect(self.validate_inputs)
        self.chunk_input_box.addWidget(chunk_lbl)
        self.chunk_input_box.addWidget(self.chunk_spin)
        self.chunk_input_box.addStretch()
        mode_layout.addLayout(self.chunk_input_box)

        self.btn_group.idToggled.connect(self.on_mode_changed)
        layout.addWidget(self.mode_card)

        # Output Folder Selection Card
        output_card = QFrame()
        output_card.setObjectName("FeatureCard")
        out_layout = QVBoxLayout(output_card)
        out_layout.setContentsMargins(20, 16, 20, 16)
        out_layout.setSpacing(8)

        out_title = QLabel("Folder Tujuan Penyimpanan")
        out_title.setObjectName("SectionTitle")
        out_layout.addWidget(out_title)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setObjectName("StyledInput")
        self.folder_edit.setReadOnly(True)
        self.folder_edit.setPlaceholderText("Pilih folder untuk menyimpan file hasil...")
        self.folder_edit.setToolTip("Folder tempat file-file hasil split akan disimpan.")
        folder_row.addWidget(self.folder_edit)

        browse_folder_btn = QPushButton("Pilih Folder...")
        browse_folder_btn.setObjectName("SecondaryButton")
        browse_folder_btn.setToolTip("Buka dialog untuk memilih folder penyimpanan di komputer.")
        browse_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_folder_btn.clicked.connect(self.browse_output_dir)
        folder_row.addWidget(browse_folder_btn)
        out_layout.addLayout(folder_row)
        layout.addWidget(output_card)

        # Progress & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Pilih file PDF terlebih dahulu untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        layout.addWidget(self.status_label)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.split_btn = QPushButton("Split PDF Sekarang")
        self.split_btn.setObjectName("ActionLargeButton")
        self.split_btn.setToolTip("Mulai memisahkan file PDF sesuai metode yang dipilih.")
        self.split_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.split_btn.setEnabled(False)
        self.split_btn.clicked.connect(self.start_split)

        self.reset_btn = QPushButton("Reset Form")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setToolTip("Kosongkan file yang dipilih dan reset pengaturan.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        self.open_folder_btn = QPushButton("Buka Folder Hasil")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setToolTip("Buka folder tempat file hasil disimpan di Windows Explorer.")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.setVisible(False)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        bottom_bar.addWidget(self.split_btn)
        bottom_bar.addWidget(self.reset_btn)
        bottom_bar.addWidget(self.open_folder_btn)
        bottom_bar.addStretch()
        layout.addLayout(bottom_bar)

        scroll.setWidget(content)
        root_layout.addWidget(scroll)

    def browse_single_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Pilih Dokumen PDF",
            "",
            "PDF Files (*.pdf)",
        )
        if file_path:
            self.load_pdf_file(file_path)

    def load_pdf_file(self, file_path: str):
        norm_path = os.path.abspath(file_path)
        is_valid, err_msg, page_count = validate_pdf_file(norm_path)
        if not is_valid:
            QMessageBox.warning(
                self,
                "File PDF Tidak Valid",
                f"File '{os.path.basename(norm_path)}' tidak dapat diproses:\n{err_msg}",
            )
            return

        self.current_file = norm_path
        self.current_page_count = page_count
        self.output_dir = os.path.dirname(norm_path)
        self.folder_edit.setText(self.output_dir)

        # Update info card
        size_bytes = os.path.getsize(norm_path)
        size_str = format_file_size(size_bytes)
        self.file_details_label.setText(
            f"<b>{os.path.basename(norm_path)}</b><br>"
            f"<span style='color: #697586;'>Ukuran: {size_str}  •  Total: {page_count} Halaman</span>"
        )
        self.info_card.setVisible(True)
        self.drop_zone.setVisible(False)
        self.chunk_spin.setMaximum(max(1, page_count))

        self.validate_inputs()

    def browse_output_dir(self):
        start_dir = self.output_dir if self.output_dir else ""
        chosen_dir = QFileDialog.getExistingDirectory(
            self, "Pilih Folder Penyimpanan Hasil", start_dir
        )
        if chosen_dir:
            self.output_dir = os.path.abspath(chosen_dir)
            self.folder_edit.setText(self.output_dir)
            self.validate_inputs()

    def on_mode_changed(self):
        is_range = self.radio_range.isChecked()
        is_chunk = self.radio_chunk.isChecked()
        self.range_edit.setEnabled(is_range)
        self.chunk_spin.setEnabled(is_chunk)
        self.validate_inputs()

    def validate_inputs(self):
        if not self.current_file:
            self.split_btn.setEnabled(False)
            self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")
            return

        if not self.output_dir or not os.path.exists(self.output_dir):
            self.split_btn.setEnabled(False)
            self.status_label.setText("Pilih folder tujuan yang valid.")
            return

        if self.radio_range.isChecked():
            txt = self.range_edit.text().strip()
            if not txt:
                self.split_btn.setEnabled(False)
                self.status_label.setText("Masukkan rentang halaman yang ingin diekstrak.")
                return

            valid, pages, err = parse_page_range(txt, self.current_page_count)
            if not valid:
                self.split_btn.setEnabled(False)
                self.status_label.setText(f"Validasi: {err}")
                return
            else:
                self.split_btn.setEnabled(True)
                self.status_label.setText(
                    f"Rentang valid: {len(pages)} halaman akan diekstrak menjadi 1 file PDF."
                )

        elif self.radio_each.isChecked():
            self.split_btn.setEnabled(True)
            self.status_label.setText(
                f"Mode aktif: Akan menghasilkan {self.current_page_count} file PDF terpisah."
            )

        elif self.radio_chunk.isChecked():
            chunk_val = self.chunk_spin.value()
            if chunk_val < 1:
                self.split_btn.setEnabled(False)
                self.status_label.setText("Jumlah halaman per file minimal 1.")
                return
            est_files = (self.current_page_count + chunk_val - 1) // chunk_val
            self.split_btn.setEnabled(True)
            self.status_label.setText(
                f"Mode aktif: Akan membagi {self.current_page_count} halaman menjadi ~{est_files} file PDF."
            )

    def start_split(self):
        if not self.current_file or not self.output_dir:
            return

        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.status_label.setText("Memulai proses pemisahan...")

        target_dir = self.output_dir

        if self.radio_range.isChecked():
            range_txt = self.range_edit.text().strip()
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            out_filename = f"{base_name}_split_range.pdf"
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan File Hasil Ekstrak",
                os.path.join(target_dir, out_filename),
                "PDF Files (*.pdf)",
            )
            if not save_path:
                self.set_ui_busy(False)
                self.progress_bar.setVisible(False)
                self.validate_inputs()
                return

            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"

            self.worker = PdfTaskWorker(
                split_pdf_by_range, self.current_file, range_txt, save_path
            )
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.finished.connect(
                lambda s, m, d: self.on_worker_finished(s, m, d, os.path.dirname(save_path))
            )
            self.worker.start()

        elif self.radio_each.isChecked():
            self.worker = PdfTaskWorker(split_pdf_each_page, self.current_file, target_dir)
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.finished.connect(
                lambda s, m, d: self.on_worker_finished(s, m, d, target_dir)
            )
            self.worker.start()

        elif self.radio_chunk.isChecked():
            chunk_size = self.chunk_spin.value()
            self.worker = PdfTaskWorker(
                split_pdf_fixed_size, self.current_file, target_dir, chunk_size
            )
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.finished.connect(
                lambda s, m, d: self.on_worker_finished(s, m, d, target_dir)
            )
            self.worker.start()

    def on_worker_progress(self, current: int, total: int, message: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        self.status_label.setText(message)

    def on_worker_finished(
        self, success: bool, message: str, generated_files: List[str], folder_path: str
    ):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)

        if success:
            self.last_output_dir = folder_path
            count = len(generated_files) if generated_files else 0
            self.status_label.setText(f"Selesai! {count} file berhasil dibuat di: {folder_path}")
            self.open_folder_btn.setVisible(True)

            reply = QMessageBox.information(
                self,
                "Berhasil Split PDF",
                f"{message}\n\nFolder penyimpanan:\n{folder_path}\n\nBuka folder penyimpanan sekarang?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.open_output_folder()
        else:
            self.status_label.setText("Pemisahan gagal.")
            QMessageBox.critical(self, "Proses Split Gagal", message)

    def set_ui_busy(self, busy: bool):
        self.split_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.mode_card.setEnabled(not busy)
        self.info_card.setEnabled(not busy)

    def reset_form(self):
        self.current_file = None
        self.current_page_count = 0
        self.output_dir = ""
        self.folder_edit.clear()
        self.range_edit.clear()
        self.chunk_spin.setValue(2)
        self.radio_range.setChecked(True)
        self.info_card.setVisible(False)
        self.drop_zone.setVisible(True)
        self.open_folder_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        self.validate_inputs()

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            open_in_file_manager(self.last_output_dir)
