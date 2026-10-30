import os
from typing import List, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.split_service import split_pdf_multi_ranges
from app.ui.pages.merge_page import PdfPreviewPanel
from app.utils.file_utils import format_file_size, open_in_file_manager
from app.utils.icon_utils import get_feature_icon
from app.utils.validators import validate_pdf_file
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


class RangeRowWidget(QFrame):
    """
    A single range row with Start page, End page, calculation badge,
    and Delete button.
    """
    deleted = Signal(object)
    changed = Signal()
    page_focused = Signal(int)

    def __init__(
        self,
        index: int = 1,
        max_pages: int = 1,
        start: int = 1,
        end: int = 1,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("RangeRow")
        self.max_pages = max(1, max_pages)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        self.title_label = QLabel(f"Rentang {index}:")
        self.title_label.setObjectName("RangeTitle")

        from_label = QLabel("Dari Hal:")
        from_label.setStyleSheet("color: #5D6B7D; font-size: 9pt;")

        self.from_spin = QSpinBox()
        self.from_spin.setObjectName("StyledSpinBox")
        self.from_spin.setRange(1, self.max_pages)
        self.from_spin.setValue(max(1, min(start, self.max_pages)))
        self.from_spin.setFixedWidth(75)

        to_label = QLabel("s/d Hal:")
        to_label.setStyleSheet("color: #5D6B7D; font-size: 9pt;")

        self.to_spin = QSpinBox()
        self.to_spin.setObjectName("StyledSpinBox")
        self.to_spin.setRange(1, self.max_pages)
        self.to_spin.setValue(max(1, min(end, self.max_pages)))
        self.to_spin.setFixedWidth(75)

        self.count_label = QLabel()
        self.count_label.setObjectName("RangePageCount")

        self.del_btn = QPushButton("Hapus")
        self.del_btn.setObjectName("RangeDeleteBtn")
        self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.del_btn.setToolTip("Hapus rentang halaman ini")
        self.del_btn.clicked.connect(lambda: self.deleted.emit(self))

        self.from_spin.valueChanged.connect(self._on_values_changed)
        self.to_spin.valueChanged.connect(self._on_values_changed)

        layout.addWidget(self.title_label)
        layout.addWidget(from_label)
        layout.addWidget(self.from_spin)
        layout.addWidget(to_label)
        layout.addWidget(self.to_spin)
        layout.addWidget(self.count_label)
        layout.addStretch()
        layout.addWidget(self.del_btn)

        self.update_count()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.page_focused.emit(self.from_spin.value() - 1)

    def set_index(self, index: int):
        self.title_label.setText(f"Rentang {index}:")

    def set_max_pages(self, max_pages: int):
        self.max_pages = max(1, max_pages)
        self.from_spin.setMaximum(self.max_pages)
        self.to_spin.setMaximum(self.max_pages)
        self.update_count()

    def get_range(self) -> Tuple[int, int]:
        return (self.from_spin.value(), self.to_spin.value())

    def set_range(self, start: int, end: int):
        self.from_spin.setValue(max(1, min(start, self.max_pages)))
        self.to_spin.setValue(max(1, min(end, self.max_pages)))
        self.update_count()

    def set_delete_visible(self, visible: bool):
        self.del_btn.setVisible(visible)

    def is_valid(self) -> bool:
        return 1 <= self.from_spin.value() <= self.to_spin.value() <= self.max_pages

    def _on_values_changed(self):
        self.update_count()
        self.changed.emit()
        self.page_focused.emit(self.from_spin.value() - 1)

    def update_count(self):
        f = self.from_spin.value()
        t = self.to_spin.value()
        if f <= t:
            count = t - f + 1
            self.count_label.setText(f"({count} halaman)")
            self.count_label.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        else:
            self.count_label.setText("(Tidak valid: awal > akhir)")
            self.count_label.setStyleSheet("color: #D64545; font-size: 8.5pt; font-weight: 600;")


class SplitPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.current_page_count: int = 0
        self.worker: Optional[PdfTaskWorker] = None
        self.last_output_dir: str = ""
        self.range_rows: List[RangeRowWidget] = []

        # Scroll Area for responsive sizing
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

        # Header Section (Tightened & VCenter aligned)
        header = QHBoxLayout()
        header.setSpacing(12)
        header.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        back_btn = QPushButton("←  Kembali")
        back_btn.setObjectName("SecondaryButton")
        back_btn.setToolTip("Kembali ke halaman utama JackPDF.")
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.clicked.connect(self.go_back.emit)

        header_icon = QLabel()
        feat_pix = get_feature_icon("Split PDF", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Split PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Pisahkan halaman dokumen PDF sesuai rentang kebutuhan Anda.")
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

        # Drop Zone
        self.drop_zone = SplitDropZone()
        self.drop_zone.setToolTip("Klik atau seret file PDF ke sini untuk memilih file.")
        self.drop_zone.file_dropped.connect(self.load_pdf_file)
        self.drop_zone.mousePressEvent = lambda e: self.browse_single_file()
        self.content_layout.addWidget(self.drop_zone)

        # File Info Card (Hidden until file selected)
        self.info_card = QFrame()
        self.info_card.setObjectName("InfoCard")
        self.info_card.setVisible(False)
        info_layout = QHBoxLayout(self.info_card)
        info_layout.setContentsMargins(16, 12, 16, 12)
        info_layout.setSpacing(10)

        icon_label = QLabel()
        icon_label.setObjectName("FeatureIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(40, 40)
        if not feat_pix.isNull():
            icon_label.setPixmap(feat_pix)
        else:
            icon_label.setText("PDF")
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

        # Range Settings Card (Hidden until file loaded)
        self.range_card = QFrame()
        self.range_card.setObjectName("FeatureCard")
        self.range_card.setVisible(False)
        range_card_layout = QVBoxLayout(self.range_card)
        range_card_layout.setContentsMargins(20, 18, 20, 18)
        range_card_layout.setSpacing(12)

        range_title = QLabel("Pengaturan Rentang Halaman")
        range_title.setObjectName("SectionTitle")
        range_subtitle = QLabel(
            "Tentukan rentang nomor halaman yang ingin diekstrak. Anda dapat menambahkan beberapa rentang."
        )
        range_subtitle.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        range_subtitle.setWordWrap(True)
        range_card_layout.addWidget(range_title)
        range_card_layout.addWidget(range_subtitle)

        # Container for Range Rows
        self.range_list_layout = QVBoxLayout()
        self.range_list_layout.setSpacing(8)
        range_card_layout.addLayout(self.range_list_layout)

        # Button Add Range
        add_btn_row = QHBoxLayout()
        self.add_range_btn = QPushButton("+ Tambah Rentang")
        self.add_range_btn.setObjectName("SecondaryButton")
        self.add_range_btn.setToolTip("Tambahkan rentang halaman baru untuk diekstrak.")
        self.add_range_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.add_range_btn.clicked.connect(self.add_range_row)
        add_btn_row.addWidget(self.add_range_btn)
        add_btn_row.addStretch()
        range_card_layout.addLayout(add_btn_row)

        range_card_layout.addSpacing(4)

        # Checkbox Option: Merge Split into 1 PDF
        self.merge_checkbox = QCheckBox("Gabungkan semua rentang menjadi 1 file PDF (Merge Split)")
        self.merge_checkbox.setObjectName("StyledCheckBox")
        self.merge_checkbox.setChecked(True)
        self.merge_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.merge_checkbox.setToolTip(
            "Jika dicentang, seluruh rentang yang ditentukan akan disatukan berurutan ke dalam 1 dokumen PDF hasil."
        )
        self.merge_checkbox.stateChanged.connect(self.validate_inputs)
        range_card_layout.addWidget(self.merge_checkbox)

        merge_hint = QLabel(
            "Jika tidak dicentang, masing-masing rentang akan diekspor menjadi file PDF terpisah."
        )
        merge_hint.setStyleSheet("color: #5D6B7D; font-size: 8.5pt; margin-left: 25px;")
        merge_hint.setWordWrap(True)
        range_card_layout.addWidget(merge_hint)

        # Progress & Status Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("Pilih file PDF terlebih dahulu untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.split_btn = QPushButton("Split PDF Sekarang")
        self.split_btn.setObjectName("ActionLargeButton")
        self.split_btn.setToolTip("Mulai memisahkan file PDF sesuai rentang yang ditentukan.")
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

        # Left Settings Column
        self.left_settings_widget = QWidget()
        left_layout = QVBoxLayout(self.left_settings_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(self.range_card)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.status_label)
        left_layout.addLayout(bottom_bar)
        left_layout.addStretch()

        # Side Preview Panel
        self.preview_panel = PdfPreviewPanel()
        self.preview_panel.setVisible(False)

        # Two-Column Layout (Settings on Left, Preview Panel on Right)
        self.main_split_layout = QHBoxLayout()
        self.main_split_layout.setSpacing(16)
        self.main_split_layout.addWidget(self.left_settings_widget, stretch=1)
        self.main_split_layout.addWidget(self.preview_panel, stretch=0)
        self.content_layout.addLayout(self.main_split_layout)

        self.scroll.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        width = event.size().width()
        if width < 640:
            self.content_layout.setContentsMargins(16, 16, 16, 16)
            self.content_layout.setSpacing(12)
        else:
            self.content_layout.setContentsMargins(32, 28, 32, 28)
            self.content_layout.setSpacing(18)

        if width < 920:
            if hasattr(self, "toggle_preview_btn") and self.toggle_preview_btn.isChecked():
                self.toggle_preview_btn.setChecked(False)

    def on_toggle_preview(self, checked: bool):
        self.preview_panel.setVisible(checked)
        if checked:
            self.toggle_preview_btn.setText("Sembunyikan Pratinjau")
            if self.current_file and self.range_rows:
                start_p, _ = self.range_rows[0].get_range()
                self.preview_panel.go_to_page(start_p - 1)
        else:
            self.toggle_preview_btn.setText("Tampilkan Pratinjau")

    def on_range_page_focused(self, page_index: int):
        if hasattr(self, "preview_panel") and self.preview_panel.isVisible():
            self.preview_panel.go_to_page(page_index)

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

        # Update info card
        size_bytes = os.path.getsize(norm_path)
        size_str = format_file_size(size_bytes)
        self.file_details_label.setText(
            f"<b>{os.path.basename(norm_path)}</b><br>"
            f"<span style='color: #697586;'>Ukuran: {size_str}  •  Total: {page_count} Halaman</span>"
        )
        self.info_card.setVisible(True)
        self.drop_zone.setVisible(False)
        self.range_card.setVisible(True)

        # Clear previous rows and initialize with first default range
        self.clear_range_rows()
        default_end = min(3, page_count) if page_count > 1 else 1
        self.add_range_row(start=1, end=default_end)

        # Load document into preview panel
        self.preview_panel.load_document(norm_path, page_num=0)
        is_preview_on = self.toggle_preview_btn.isChecked()
        self.preview_panel.setVisible(is_preview_on)
        self.toggle_preview_btn.setVisible(True)

        self.validate_inputs()

    def clear_range_rows(self):
        for row in list(self.range_rows):
            self.range_list_layout.removeWidget(row)
            row.deleteLater()
        self.range_rows.clear()

    def add_range_row(self, start: Optional[int] = None, end: Optional[int] = None):
        if not self.current_file or self.current_page_count < 1:
            return

        max_p = self.current_page_count

        if start is None or end is None:
            # Smart default based on previous row
            if self.range_rows:
                prev_start, prev_end = self.range_rows[-1].get_range()
                if prev_end < max_p:
                    start = prev_end + 1
                    end = min(start + 2, max_p)
                else:
                    start = 1
                    end = max_p
            else:
                start = 1
                end = min(3, max_p)

        index = len(self.range_rows) + 1
        row_widget = RangeRowWidget(
            index=index,
            max_pages=max_p,
            start=start,
            end=end,
        )
        row_widget.deleted.connect(self.remove_range_row)
        row_widget.changed.connect(self.validate_inputs)
        row_widget.page_focused.connect(self.on_range_page_focused)

        self.range_rows.append(row_widget)
        self.range_list_layout.addWidget(row_widget)

        self._refresh_range_rows_state()
        self.validate_inputs()

    def remove_range_row(self, row_widget: RangeRowWidget):
        if row_widget in self.range_rows:
            self.range_rows.remove(row_widget)
            self.range_list_layout.removeWidget(row_widget)
            row_widget.deleteLater()

        self._refresh_range_rows_state()
        self.validate_inputs()

    def _refresh_range_rows_state(self):
        show_delete = len(self.range_rows) > 1
        for idx, row in enumerate(self.range_rows):
            row.set_index(idx + 1)
            row.set_delete_visible(show_delete)

        # Merge checkbox is only visually relevant when ranges > 1
        self.merge_checkbox.setVisible(len(self.range_rows) > 1)

    def validate_inputs(self):
        if not self.current_file:
            self.split_btn.setEnabled(False)
            self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")
            if hasattr(self, "preview_panel"):
                self.preview_panel.set_summary_badge("")
            return

        if not self.range_rows:
            self.split_btn.setEnabled(False)
            self.status_label.setText("Tambahkan minimal 1 rentang halaman.")
            if hasattr(self, "preview_panel"):
                self.preview_panel.set_summary_badge("")
            return

        total_pages_to_extract = 0

        for idx, row in enumerate(self.range_rows):
            if not row.is_valid():
                f, t = row.get_range()
                self.split_btn.setEnabled(False)
                self.status_label.setText(
                    f"Perhatian pada Rentang {idx + 1}: Halaman awal ({f}) tidak boleh lebih besar dari halaman akhir ({t})."
                )
                if hasattr(self, "preview_panel"):
                    self.preview_panel.set_summary_badge("")
                return
            s, e = row.get_range()
            total_pages_to_extract += (e - s + 1)

        num_ranges = len(self.range_rows)
        self.split_btn.setEnabled(True)

        if num_ranges == 1:
            self.status_label.setText(
                f"1 rentang siap diekstrak ({total_pages_to_extract} halaman terpilih)."
            )
            if hasattr(self, "preview_panel"):
                self.preview_panel.set_summary_badge(
                    f"Estimasi Hasil: 1 File PDF ({total_pages_to_extract} Hal)"
                )
        else:
            if self.merge_checkbox.isChecked():
                self.status_label.setText(
                    f"Siap menggabungkan {num_ranges} rentang (Total {total_pages_to_extract} halaman) ke 1 file PDF hasil."
                )
                if hasattr(self, "preview_panel"):
                    self.preview_panel.set_summary_badge(
                        f"Estimasi Hasil: 1 File PDF Gabungan ({total_pages_to_extract} Hal)"
                    )
            else:
                self.status_label.setText(
                    f"Siap memisahkan menjadi {num_ranges} file PDF terpisah (Total {total_pages_to_extract} halaman)."
                )
                if hasattr(self, "preview_panel"):
                    self.preview_panel.set_summary_badge(
                        f"Estimasi Hasil: {num_ranges} File PDF Terpisah ({total_pages_to_extract} Hal)"
                    )


    def start_split(self):
        if not self.current_file or not self.range_rows:
            return

        ranges = [row.get_range() for row in self.range_rows]
        for idx, (s, e) in enumerate(ranges):
            if s > e:
                QMessageBox.warning(
                    self,
                    "Rentang Tidak Valid",
                    f"Rentang {idx + 1} tidak valid: Halaman awal ({s}) lebih besar dari halaman akhir ({e}).",
                )
                return

        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        default_dir = os.path.dirname(self.current_file)
        is_merged = self.merge_checkbox.isChecked() or len(ranges) == 1

        if is_merged:
            default_out = os.path.join(default_dir, f"{base_name}_split.pdf")
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Simpan File PDF Hasil Split",
                default_out,
                "PDF Files (*.pdf)",
            )
            if not save_path:
                return

            if not save_path.lower().endswith(".pdf"):
                save_path += ".pdf"

            self.set_ui_busy(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("Memulai proses ekstraksi...")

            self.worker = PdfTaskWorker(
                split_pdf_multi_ranges, self.current_file, ranges, save_path, True
            )
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.finished.connect(
                lambda s, m, d: self.on_worker_finished(s, m, d, os.path.dirname(save_path))
            )
            self.worker.start()

        else:
            chosen_dir = QFileDialog.getExistingDirectory(
                self,
                "Pilih Folder Penyimpanan File Hasil",
                default_dir,
            )
            if not chosen_dir:
                return

            self.set_ui_busy(True)
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.status_label.setText("Memulai proses pemisahan...")

            self.worker = PdfTaskWorker(
                split_pdf_multi_ranges, self.current_file, ranges, chosen_dir, False
            )
            self.worker.progress.connect(self.on_worker_progress)
            self.worker.finished.connect(
                lambda s, m, d: self.on_worker_finished(s, m, d, chosen_dir)
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

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Berhasil Split PDF")
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setText(f"<b>{message}</b>")
            msg_box.setInformativeText(
                f"Folder penyimpanan:\n{folder_path}\n\nApakah Anda ingin membuka folder hasil sekarang?"
            )
            open_btn = msg_box.addButton("Buka Folder Hasil", QMessageBox.ButtonRole.AcceptRole)
            open_btn.setObjectName("PrimaryButton")
            open_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            close_btn = msg_box.addButton("Tutup", QMessageBox.ButtonRole.RejectRole)
            close_btn.setObjectName("SecondaryButton")
            close_btn.setCursor(Qt.CursorShape.PointingHandCursor)

            msg_box.setDefaultButton(open_btn)
            msg_box.exec()

            if msg_box.clickedButton() == open_btn:
                self.open_output_folder()
        else:
            self.status_label.setText("Pemisahan gagal.")
            QMessageBox.critical(self, "Proses Split Gagal", message)

    def set_ui_busy(self, busy: bool):
        self.split_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.range_card.setEnabled(not busy)
        self.info_card.setEnabled(not busy)

    def reset_form(self):
        self.current_file = None
        self.current_page_count = 0
        self.clear_range_rows()
        self.info_card.setVisible(False)
        self.range_card.setVisible(False)
        self.drop_zone.setVisible(True)
        self.open_folder_btn.setVisible(False)
        self.progress_bar.setVisible(False)
        if hasattr(self, "preview_panel"):
            self.preview_panel.clear_preview()
            self.preview_panel.setVisible(False)
        if hasattr(self, "toggle_preview_btn"):
            self.toggle_preview_btn.setVisible(False)
        self.validate_inputs()

    def open_output_folder(self):
        if self.last_output_dir and os.path.exists(self.last_output_dir):
            open_in_file_manager(self.last_output_dir)
