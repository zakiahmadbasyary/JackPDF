import os
from typing import Dict, List, Optional, Set
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
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
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from app.services.convert_png_service import (
    format_page_selection,
    get_default_output_dir,
    get_output_filename,
    parse_page_selection,
)
from app.ui.pages.merge_page import PdfPreviewPanel
from app.utils.file_utils import format_file_size, open_in_file_manager
from app.utils.icon_utils import get_feature_icon
from app.utils.validators import validate_pdf_file
from app.workers.convert_png_worker import ConvertPngWorker


class ConvertDropZone(QFrame):
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


class ConvertPngPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.current_password: Optional[str] = None
        self.current_page_count: int = 0
        self.current_output_dir: str = ""
        self.last_output_dir: str = ""
        self.worker: Optional[ConvertPngWorker] = None

        # Main wrapper layout holding scroll area
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
        feat_pix = get_feature_icon("Convert to PNG", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Convert to PNG")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Ubah halaman PDF menjadi gambar PNG berkualitas tinggi.")
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

        # Drop Zone Section
        self.drop_zone = ConvertDropZone()
        self.drop_zone.file_dropped.connect(self.load_pdf_file)
        self.content_layout.addWidget(self.drop_zone)

        # File Info Card (hidden until file is selected)
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

        # --- SETTINGS CONTAINER CARD (hidden until file loaded) ---
        self.settings_card = QFrame()
        self.settings_card.setObjectName("FeatureCard")
        self.settings_card.setVisible(False)
        settings_card_layout = QVBoxLayout(self.settings_card)
        settings_card_layout.setContentsMargins(20, 18, 20, 18)
        settings_card_layout.setSpacing(14)

        # 1. Page Selection Header & Radio Options
        page_sec_title = QLabel("Pemilihan Halaman")
        page_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(page_sec_title)

        page_mode_layout = QHBoxLayout()
        page_mode_layout.setSpacing(20)

        self.radio_all_pages = QRadioButton("Semua Halaman")
        self.radio_all_pages.setObjectName("RadioChoice")
        self.radio_all_pages.setChecked(True)
        self.radio_all_pages.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio_all_pages.toggled.connect(self._on_page_mode_toggled)

        self.radio_custom_pages = QRadioButton("Pilih Halaman Tertentu")
        self.radio_custom_pages.setObjectName("RadioChoice")
        self.radio_custom_pages.setCursor(Qt.CursorShape.PointingHandCursor)

        self.page_mode_group = QButtonGroup(self)
        self.page_mode_group.addButton(self.radio_all_pages)
        self.page_mode_group.addButton(self.radio_custom_pages)

        page_mode_layout.addWidget(self.radio_all_pages)
        page_mode_layout.addWidget(self.radio_custom_pages)
        page_mode_layout.addStretch()
        settings_card_layout.addLayout(page_mode_layout)

        # Custom Page Selection Container (visible only when radio_custom_pages is selected)
        self.custom_pages_container = QWidget()
        self.custom_pages_container.setVisible(False)
        custom_vbox = QVBoxLayout(self.custom_pages_container)
        custom_vbox.setContentsMargins(0, 4, 0, 0)
        custom_vbox.setSpacing(6)

        manual_label = QLabel("Nomor atau rentang halaman:")
        manual_label.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 500;")

        self.manual_range_edit = QLineEdit()
        self.manual_range_edit.setObjectName("StyledInput")
        self.manual_range_edit.setPlaceholderText("Contoh: 1, 3, 5-8")
        self.manual_range_edit.textChanged.connect(self._on_manual_range_changed)

        manual_hint = QLabel("Gunakan koma untuk memisahkan halaman, tanda hubung untuk rentang (misal: 1, 3-5).")
        manual_hint.setStyleSheet("color: #697586; font-size: 8.5pt;")

        self.page_summary_label = QLabel("")
        self.page_summary_label.setStyleSheet("color: #1D6FEA; font-weight: 600; font-size: 8.5pt;")

        self.manual_error_label = QLabel("")
        self.manual_error_label.setStyleSheet("color: #D64545; font-size: 8.5pt; font-weight: 500;")
        self.manual_error_label.setVisible(False)

        custom_vbox.addWidget(manual_label)
        custom_vbox.addWidget(self.manual_range_edit)
        custom_vbox.addWidget(manual_hint)
        custom_vbox.addWidget(self.page_summary_label)
        custom_vbox.addWidget(self.manual_error_label)

        settings_card_layout.addWidget(self.custom_pages_container)
        settings_card_layout.addSpacing(6)

        # 2. Image Settings: Resolution (DPI) & Color Mode
        img_sec_title = QLabel("Pengaturan Gambar")
        img_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(img_sec_title)

        settings_grid = QGridLayout()
        settings_grid.setSpacing(12)

        # DPI section
        dpi_title = QLabel("Resolusi (DPI):")
        dpi_title.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 600;")
        settings_grid.addWidget(dpi_title, 0, 0)

        dpi_opts_layout = QHBoxLayout()
        dpi_opts_layout.setSpacing(14)

        self.radio_dpi_150 = QRadioButton("Standar (150 DPI)")
        self.radio_dpi_150.setObjectName("RadioChoice")
        self.radio_dpi_150.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_dpi_200 = QRadioButton("Tinggi (200 DPI)")
        self.radio_dpi_200.setObjectName("RadioChoice")
        self.radio_dpi_200.setChecked(True)
        self.radio_dpi_200.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_dpi_300 = QRadioButton("Sangat Tinggi (300 DPI)")
        self.radio_dpi_300.setObjectName("RadioChoice")
        self.radio_dpi_300.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_dpi_custom = QRadioButton("Kustom:")
        self.radio_dpi_custom.setObjectName("RadioChoice")
        self.radio_dpi_custom.setCursor(Qt.CursorShape.PointingHandCursor)

        self.custom_dpi_spin = QSpinBox()
        self.custom_dpi_spin.setObjectName("StyledSpinBox")
        self.custom_dpi_spin.setRange(72, 600)
        self.custom_dpi_spin.setValue(200)
        self.custom_dpi_spin.setFixedWidth(80)
        self.custom_dpi_spin.setEnabled(False)

        self.radio_dpi_custom.toggled.connect(self.custom_dpi_spin.setEnabled)

        self.dpi_group = QButtonGroup(self)
        self.dpi_group.addButton(self.radio_dpi_150)
        self.dpi_group.addButton(self.radio_dpi_200)
        self.dpi_group.addButton(self.radio_dpi_300)
        self.dpi_group.addButton(self.radio_dpi_custom)

        dpi_opts_layout.addWidget(self.radio_dpi_150)
        dpi_opts_layout.addWidget(self.radio_dpi_200)
        dpi_opts_layout.addWidget(self.radio_dpi_300)
        dpi_opts_layout.addWidget(self.radio_dpi_custom)
        dpi_opts_layout.addWidget(self.custom_dpi_spin)
        dpi_opts_layout.addStretch()

        settings_grid.addLayout(dpi_opts_layout, 0, 1)

        # Color mode section
        color_title = QLabel("Mode Warna:")
        color_title.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 600;")
        settings_grid.addWidget(color_title, 1, 0)

        color_opts_layout = QHBoxLayout()
        color_opts_layout.setSpacing(16)

        self.radio_color_rgb = QRadioButton("RGB (Warna Penuh)")
        self.radio_color_rgb.setObjectName("RadioChoice")
        self.radio_color_rgb.setChecked(True)
        self.radio_color_rgb.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_color_gray = QRadioButton("Grayscale (Hitam & Putih)")
        self.radio_color_gray.setObjectName("RadioChoice")
        self.radio_color_gray.setCursor(Qt.CursorShape.PointingHandCursor)

        self.color_group = QButtonGroup(self)
        self.color_group.addButton(self.radio_color_rgb)
        self.color_group.addButton(self.radio_color_gray)

        color_opts_layout.addWidget(self.radio_color_rgb)
        color_opts_layout.addWidget(self.radio_color_gray)
        color_opts_layout.addStretch()

        settings_grid.addLayout(color_opts_layout, 1, 1)
        settings_card_layout.addLayout(settings_grid)
        settings_card_layout.addSpacing(6)

        # 3. Output Folder Section
        out_sec_title = QLabel("Folder Penyimpanan Hasil")
        out_sec_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(out_sec_title)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self.output_dir_label = QLabel("Folder belum dipilih")
        self.output_dir_label.setObjectName("StyledInput")
        self.output_dir_label.setStyleSheet(
            "background: #F7F9FC; border: 1px solid #DCE3EC; border-radius: 8px; padding: 7px 12px; color: #263445;"
        )

        change_folder_btn = QPushButton("Pilih Folder...")
        change_folder_btn.setObjectName("SecondaryButton")
        change_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_folder_btn.clicked.connect(self.browse_output_dir)

        folder_row.addWidget(self.output_dir_label, 1)
        folder_row.addWidget(change_folder_btn)
        settings_card_layout.addLayout(folder_row)

        self.content_layout.addWidget(self.settings_card)

        # --- RESULT SUMMARY CARD (hidden until finished) ---
        self.result_card = QFrame()
        self.result_card.setObjectName("ResultSummaryCard")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(12)

        res_title = QLabel("Hasil Konversi ke PNG")
        res_title.setObjectName("ResultTitle")
        result_layout.addWidget(res_title)

        self.result_details_label = QLabel()
        self.result_details_label.setStyleSheet("color: #263445; font-size: 9.5pt;")
        self.result_details_label.setWordWrap(True)
        result_layout.addWidget(self.result_details_label)

        res_btn_row = QHBoxLayout()
        res_btn_row.setSpacing(10)

        self.open_folder_btn = QPushButton("Buka Folder Hasil")
        self.open_folder_btn.setObjectName("PrimaryButton")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        self.convert_another_btn = QPushButton("Konversi File Lain")
        self.convert_another_btn.setObjectName("SecondaryButton")
        self.convert_another_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_another_btn.clicked.connect(self.reset_form)

        res_btn_row.addWidget(self.open_folder_btn)
        res_btn_row.addWidget(self.convert_another_btn)
        res_btn_row.addStretch()
        result_layout.addLayout(res_btn_row)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("Pilih file PDF terlebih dahulu untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)

        # Bottom Action Bar
        bottom_bar = QHBoxLayout()
        self.convert_btn = QPushButton("Convert to PNG")
        self.convert_btn.setObjectName("ActionLargeButton")
        self.convert_btn.setToolTip("Mulai proses konversi halaman PDF ke PNG.")
        self.convert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self.start_convert)

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setObjectName("TableDeleteBtn")
        self.cancel_btn.setToolTip("Hentikan proses konversi yang sedang berjalan.")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.clicked.connect(self.cancel_convert)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setToolTip("Kosongkan file yang dipilih dan reset form.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        bottom_bar.addWidget(self.convert_btn)
        bottom_bar.addWidget(self.cancel_btn)
        bottom_bar.addWidget(self.reset_btn)
        bottom_bar.addStretch()

        # Left Settings Column
        self.left_settings_widget = QWidget()
        left_layout = QVBoxLayout(self.left_settings_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(14)
        left_layout.addWidget(self.settings_card)
        left_layout.addWidget(self.result_card)
        left_layout.addWidget(self.progress_bar)
        left_layout.addWidget(self.status_label)
        left_layout.addLayout(bottom_bar)
        left_layout.addStretch()

        # Side Document Preview Panel
        self.preview_panel = PdfPreviewPanel()
        self.preview_panel.setVisible(False)

        # Two-Column Layout (Settings on Left, Preview Panel on Right)
        self.main_layout = QHBoxLayout()
        self.main_layout.setSpacing(16)
        self.main_layout.addWidget(self.left_settings_widget, stretch=1)
        self.main_layout.addWidget(self.preview_panel, stretch=0)
        self.content_layout.addLayout(self.main_layout)

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
            if self.current_file:
                self.preview_panel.load_document(self.current_file, page_num=0)
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
        start_dir = self.current_output_dir or (
            os.path.dirname(self.current_file) if self.current_file else ""
        )
        chosen_dir = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Penyimpanan File PNG",
            start_dir,
        )
        if chosen_dir:
            self.current_output_dir = os.path.abspath(chosen_dir)
            self.output_dir_label.setText(self.current_output_dir)

    def load_pdf_file(self, file_path: str):
        norm_path = os.path.abspath(file_path)
        password = None

        # Check validity and handle encrypted PDF
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

        # Default output directory
        self.current_output_dir = get_default_output_dir(norm_path)
        self.output_dir_label.setText(self.current_output_dir)

        # Update info card
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

        # Load into preview panel
        self.preview_panel.load_document(norm_path, page_num=0)
        self.preview_panel.set_summary_badge(f"Dokumen Asli ({page_count} Halaman)")
        is_preview_on = self.toggle_preview_btn.isChecked()
        self.preview_panel.setVisible(is_preview_on)
        self.toggle_preview_btn.setVisible(True)

        self.radio_all_pages.setChecked(True)
        self.custom_pages_container.setVisible(False)
        self.manual_range_edit.setText(f"1-{page_count}")
        self.manual_error_label.setVisible(False)
        self.validate_state()

    def _on_page_mode_toggled(self, checked: bool):
        is_all = self.radio_all_pages.isChecked()
        self.custom_pages_container.setVisible(not is_all)
        if not is_all:
            if not self.manual_range_edit.text().strip() and self.current_page_count > 0:
                self.manual_range_edit.setText(f"1-{self.current_page_count}")
            self._validate_custom_pages()
        else:
            self.manual_error_label.setVisible(False)
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
            self.manual_error_label.setText("Ketik nomor halaman yang ingin dikonversi.")
            self.manual_error_label.setVisible(True)
            self.page_summary_label.setText("")
            return False

        ok, pages, err = parse_page_selection(text, self.current_page_count)
        if not ok:
            self.manual_error_label.setText(err)
            self.manual_error_label.setVisible(True)
            self.page_summary_label.setText("")
            return False

        self.manual_error_label.setVisible(False)
        count = len(pages)
        total = self.current_page_count
        self.page_summary_label.setText(f"✓ {count} dari {total} halaman dipilih ({format_page_selection(pages)})")
        return True

    def get_selected_pages(self) -> List[int]:
        if not self.current_file or self.current_page_count < 1:
            return []

        if self.radio_all_pages.isChecked():
            return list(range(1, self.current_page_count + 1))

        text = self.manual_range_edit.text().strip()
        ok, pages, _ = parse_page_selection(text, self.current_page_count)
        return pages if ok else []

    def get_selected_dpi(self) -> int:
        if self.radio_dpi_150.isChecked():
            return 150
        elif self.radio_dpi_200.isChecked():
            return 200
        elif self.radio_dpi_300.isChecked():
            return 300
        else:
            return self.custom_dpi_spin.value()

    def get_selected_color_mode(self) -> str:
        if self.radio_color_gray.isChecked():
            return "grayscale"
        return "rgb"

    def validate_state(self):
        if not self.current_file:
            self.convert_btn.setEnabled(False)
            self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")
            return

        selected = self.get_selected_pages()
        if not selected:
            self.convert_btn.setEnabled(False)
            self.status_label.setText("Pilih minimal satu halaman untuk dikonversi.")
            return

        self.convert_btn.setEnabled(True)
        count = len(selected)
        dpi = self.get_selected_dpi()
        mode = "RGB" if self.get_selected_color_mode() == "rgb" else "Grayscale"
        self.status_label.setText(
            f"{count} halaman siap dikonversi ke PNG ({dpi} DPI, Mode {mode})."
        )

    def start_convert(self):
        if not self.current_file:
            return

        selected_pages = self.get_selected_pages()
        if not selected_pages:
            QMessageBox.warning(self, "Peringatan", "Pilih minimal satu halaman untuk dikonversi.")
            return

        dpi = self.get_selected_dpi()
        color_mode = self.get_selected_color_mode()

        if not self.current_output_dir or not self.current_output_dir.strip():
            QMessageBox.warning(self, "Peringatan", "Folder tujuan penyimpanan belum ditentukan.")
            return

        # Check existing PNG pattern in output folder
        base_name = os.path.splitext(os.path.basename(self.current_file))[0]
        if os.path.exists(self.current_output_dir):
            existing_pngs = [
                f
                for f in os.listdir(self.current_output_dir)
                if f.lower().endswith(".png") and f.startswith(f"{base_name}_page-")
            ]
            if existing_pngs:
                confirm = QMessageBox.question(
                    self,
                    "Konfirmasi Penimpaan File",
                    f"Ditemukan {len(existing_pngs)} file PNG dengan nama serupa di folder tujuan.\n"
                    "Apakah Anda ingin melanjutkan dan menimpa file yang sudah ada?",
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
        self.status_label.setText("Memulai proses konversi...")
        self.result_card.setVisible(False)

        self.worker = ConvertPngWorker(
            input_path=self.current_file,
            output_dir=self.current_output_dir,
            pages=selected_pages,
            dpi=dpi,
            color_mode=color_mode,
            password=self.current_password,
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
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        self.status_label.setText(message)

    def on_worker_finished(self, success: bool, message: str, result_data: Optional[dict]):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)

        if result_data:
            self.last_output_dir = result_data.get("output_dir", self.current_output_dir)
            total_success = result_data.get("total_success", 0)
            total_req = result_data.get("total_requested", 0)
            failed_pages = result_data.get("failed_pages", [])
            dpi = result_data.get("dpi", 200)
            color_mode = "RGB" if result_data.get("color_mode") == "rgb" else "Grayscale"
            is_cancelled = result_data.get("is_cancelled", False)

            status_text = (
                f"<b>{message}</b><br><br>"
                f"• Jumlah file berhasil: <b>{total_success} dari {total_req} halaman</b><br>"
                f"• Resolusi gambar: <b>{dpi} DPI</b>  •  Mode: <b>{color_mode}</b><br>"
                f"• Lokasi folder: <code>{self.last_output_dir}</code>"
            )

            if failed_pages:
                failed_str = ", ".join(map(str, failed_pages))
                status_text += f"<br><span style='color: #D64545;'>• Halaman yang gagal: {failed_str}</span>"

            if is_cancelled:
                status_text += "<br><span style='color: #D99116;'>• Proses dihentikan oleh pengguna.</span>"

            self.result_details_label.setText(status_text)
            self.result_card.setVisible(True)
            self.status_label.setText(
                f"Selesai! {total_success} file gambar PNG tersimpan di: {self.last_output_dir}"
            )
        else:
            self.status_label.setText("Proses konversi gagal.")
            QMessageBox.critical(self, "Konversi Gagal", message)

    def open_output_folder(self):
        target = self.last_output_dir or self.current_output_dir
        if target and os.path.exists(target):
            open_in_file_manager(target)

    def set_ui_busy(self, busy: bool):
        self.convert_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.settings_card.setEnabled(not busy)
        self.info_card.setEnabled(not busy)

    def reset_form(self):
        self.current_file = None
        self.current_password = None
        self.current_page_count = 0
        self.last_output_dir = ""

        self.info_card.setVisible(False)
        self.settings_card.setVisible(False)
        self.result_card.setVisible(False)
        self.drop_zone.setVisible(True)
        self.progress_bar.setVisible(False)
        self.cancel_btn.setVisible(False)
        self.convert_btn.setEnabled(False)
        self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")
        self.manual_range_edit.clear()
        self.manual_error_label.setVisible(False)
        self.page_summary_label.setText("")

        self.radio_all_pages.setChecked(True)
        self.custom_pages_container.setVisible(False)

        # Reset DPI and Color to defaults
        self.radio_dpi_200.setChecked(True)
        self.custom_dpi_spin.setEnabled(False)
        self.custom_dpi_spin.setValue(200)
        self.radio_color_rgb.setChecked(True)

        if hasattr(self, "preview_panel"):
            self.preview_panel.clear_preview()
            self.preview_panel.setVisible(False)
        if hasattr(self, "toggle_preview_btn"):
            self.toggle_preview_btn.setVisible(False)
