import os
from typing import Optional, Dict, Any
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.compress_service import PRESET_CONFIGS, compress_pdf
from app.services.settings_service import get_effective_output_dir, get_settings_service
from app.ui.pages.merge_page import PdfPreviewPanel
from app.utils.file_utils import (
    format_file_size,
    get_safe_destination_path,
    open_file_with_default_app,
    open_in_file_manager,
)
from app.utils.icon_utils import get_feature_icon
from app.utils.validators import (
    check_pdf_signatures,
    validate_output_filename,
    validate_pdf_file,
)
from app.workers.pdf_worker import PdfTaskWorker


class CompressDropZone(QFrame):
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


class PresetCard(QFrame):
    """
    Radio card representing a compression preset.
    Clicking anywhere on the card selects it.
    """
    selected = Signal(str)

    def __init__(
        self,
        preset_key: str,
        title: str,
        description: str,
        badge_text: str = "",
        is_checked: bool = False,
    ):
        super().__init__()
        self.preset_key = preset_key
        self.setObjectName("PresetCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(12)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.radio = QRadioButton()
        self.radio.setObjectName("RadioChoice")
        self.radio.setChecked(is_checked)
        self.radio.setCursor(Qt.CursorShape.PointingHandCursor)
        self.radio.clicked.connect(self._on_radio_clicked)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel(title)
        title_label.setObjectName("PresetTitle")
        header_layout.addWidget(title_label)

        if badge_text:
            badge_label = QLabel(badge_text)
            badge_label.setObjectName("PresetBadge")
            header_layout.addWidget(badge_label)

        header_layout.addStretch()

        desc_label = QLabel(description)
        desc_label.setObjectName("PresetDesc")
        desc_label.setWordWrap(True)

        text_layout.addLayout(header_layout)
        text_layout.addWidget(desc_label)

        main_layout.addWidget(self.radio)
        main_layout.addLayout(text_layout, 1)

        self.set_selected(is_checked)

    def _on_radio_clicked(self):
        self.selected.emit(self.preset_key)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.preset_key)
        super().mousePressEvent(event)

    def set_selected(self, checked: bool):
        self.radio.setChecked(checked)
        self.setProperty("selected", "true" if checked else "false")
        self.style().unpolish(self)
        self.style().polish(self)


class CompressPage(QWidget):
    go_back = Signal()

    def __init__(self):
        super().__init__()
        self.current_file: Optional[str] = None
        self.current_password: Optional[str] = None
        self.current_page_count: int = 0
        self.current_output_dir: str = ""
        self.selected_preset: str = "balanced"
        self.last_compressed_file: Optional[str] = None
        self.worker: Optional[PdfTaskWorker] = None

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
        feat_pix = get_feature_icon("Compress PDF", size=40)
        if not feat_pix.isNull():
            header_icon.setPixmap(feat_pix)
            header_icon.setFixedSize(40, 40)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title_box.setContentsMargins(0, 0, 0, 0)

        title = QLabel("Compress PDF")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Kurangi ukuran file PDF agar lebih mudah disimpan dan dibagikan.")
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
        self.drop_zone = CompressDropZone()
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

        # Compression Settings Card (hidden until file is loaded)
        self.settings_card = QFrame()
        self.settings_card.setObjectName("FeatureCard")
        self.settings_card.setVisible(False)
        settings_card_layout = QVBoxLayout(self.settings_card)
        settings_card_layout.setContentsMargins(20, 18, 20, 18)
        settings_card_layout.setSpacing(14)

        preset_title = QLabel("Pilihan Kompresi")
        preset_title.setObjectName("SectionTitle")
        preset_subtitle = QLabel(
            "Pilih preset optimasi. Preset 'Seimbang' disarankan untuk sebagian besar dokumen."
        )
        preset_subtitle.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        settings_card_layout.addWidget(preset_title)
        settings_card_layout.addWidget(preset_subtitle)

        # Presets container
        self.preset_cards: Dict[str, PresetCard] = {}
        preset_list_layout = QVBoxLayout()
        preset_list_layout.setSpacing(8)

        card_high = PresetCard(
            "high",
            "Kualitas Tinggi",
            "Menjaga kualitas visual terbaik. Optimasi struktur dokumen dan stream tanpa downsampling gambar yang mencolok.",
            badge_text="",
            is_checked=False,
        )
        card_balanced = PresetCard(
            "balanced",
            "Seimbang",
            "Kompromi ideal antara pengurangan ukuran file dan kualitas visual gambar.",
            badge_text="Rekomendasi",
            is_checked=True,
        )
        card_small = PresetCard(
            "small",
            "Ukuran Lebih Kecil",
            "Memprioritaskan ukuran file sekecil mungkin. Downsampling gambar agresif (kualitas visual gambar dapat menurun).",
            badge_text="",
            is_checked=False,
        )

        for card in [card_balanced, card_high, card_small]:
            card.selected.connect(self.select_preset)
            self.preset_cards[card.preset_key] = card
            preset_list_layout.addWidget(card)

        settings_card_layout.addLayout(preset_list_layout)
        settings_card_layout.addSpacing(6)

        # Output destination section
        out_title = QLabel("Tujuan File Hasil")
        out_title.setObjectName("SectionTitle")
        settings_card_layout.addWidget(out_title)

        # Output filename input
        out_name_layout = QVBoxLayout()
        out_name_layout.setSpacing(4)
        out_name_label = QLabel("Nama File Hasil:")
        out_name_label.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 600;")
        self.output_name_edit = QLineEdit()
        self.output_name_edit.setObjectName("StyledInput")
        self.output_name_edit.setPlaceholderText("nama_file_compressed.pdf")
        out_name_layout.addWidget(out_name_label)
        out_name_layout.addWidget(self.output_name_edit)
        settings_card_layout.addLayout(out_name_layout)

        # Output folder selection
        folder_layout = QVBoxLayout()
        folder_layout.setSpacing(4)
        folder_label = QLabel("Folder Penyimpanan:")
        folder_label.setStyleSheet("color: #263445; font-size: 9pt; font-weight: 600;")

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)
        self.output_dir_label = QLabel()
        self.output_dir_label.setObjectName("StyledInput")
        self.output_dir_label.setStyleSheet(
            "background: #F7F9FC; border: 1px solid #DCE3EC; border-radius: 8px; padding: 7px 12px; color: #263445;"
        )
        self.output_dir_label.setText("Folder belum dipilih")

        change_folder_btn = QPushButton("Pilih Folder...")
        change_folder_btn.setObjectName("SecondaryButton")
        change_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_folder_btn.clicked.connect(self.browse_output_dir)

        folder_row.addWidget(self.output_dir_label, 1)
        folder_row.addWidget(change_folder_btn)

        folder_layout.addWidget(folder_label)
        folder_layout.addLayout(folder_row)
        settings_card_layout.addLayout(folder_layout)

        # Result Summary Card (hidden until compression completes)
        self.result_card = QFrame()
        self.result_card.setObjectName("ResultSummaryCard")
        self.result_card.setVisible(False)
        result_layout = QVBoxLayout(self.result_card)
        result_layout.setContentsMargins(18, 16, 18, 16)
        result_layout.setSpacing(12)

        res_title = QLabel("Hasil Kompresi PDF")
        res_title.setObjectName("ResultTitle")
        result_layout.addWidget(res_title)

        # Metrics row (Original, Compressed, Savings badge)
        metrics_row = QHBoxLayout()
        metrics_row.setSpacing(20)

        # Col 1: Original Size
        col1 = QVBoxLayout()
        col1.setSpacing(2)
        c1_title = QLabel("Ukuran Awal:")
        c1_title.setObjectName("MetricTitle")
        self.orig_size_label = QLabel("0 B")
        self.orig_size_label.setObjectName("MetricValue")
        col1.addWidget(c1_title)
        col1.addWidget(self.orig_size_label)

        # Arrow indicator
        arrow_label = QLabel("➔")
        arrow_label.setStyleSheet("font-size: 14pt; color: #98A6B8; padding-top: 12px;")

        # Col 2: Compressed Size
        col2 = QVBoxLayout()
        col2.setSpacing(2)
        c2_title = QLabel("Ukuran Akhir:")
        c2_title.setObjectName("MetricTitle")
        self.final_size_label = QLabel("0 B")
        self.final_size_label.setObjectName("MetricValue")
        col2.addWidget(c2_title)
        col2.addWidget(self.final_size_label)

        # Col 3: Difference Badge
        col3 = QVBoxLayout()
        col3.setSpacing(2)
        c3_title = QLabel("Perubahan:")
        c3_title.setObjectName("MetricTitle")
        self.savings_badge = QLabel("Hemat 0%")
        self.savings_badge.setObjectName("BadgeSuccess")
        col3.addWidget(c3_title)
        col3.addWidget(self.savings_badge)

        metrics_row.addLayout(col1)
        metrics_row.addWidget(arrow_label)
        metrics_row.addLayout(col2)
        metrics_row.addSpacing(16)
        metrics_row.addLayout(col3)
        metrics_row.addStretch()
        result_layout.addLayout(metrics_row)

        self.larger_note_label = QLabel(
            "Catatan: File sumber sudah teroptimasi dengan sangat baik sehingga kompresi ulang tidak mengurangi ukurannya."
        )
        self.larger_note_label.setStyleSheet("color: #D99116; font-size: 8.5pt;")
        self.larger_note_label.setWordWrap(True)
        self.larger_note_label.setVisible(False)
        result_layout.addWidget(self.larger_note_label)

        # Result Action Buttons
        result_btn_row = QHBoxLayout()
        result_btn_row.setSpacing(10)

        self.open_file_btn = QPushButton("Buka File")
        self.open_file_btn.setObjectName("PrimaryButton")
        self.open_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_file_btn.clicked.connect(self.open_compressed_file)

        self.open_folder_btn = QPushButton("Buka Folder")
        self.open_folder_btn.setObjectName("SecondaryButton")
        self.open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self.open_output_folder)

        self.another_file_btn = QPushButton("Kompres File Lain")
        self.another_file_btn.setObjectName("SecondaryButton")
        self.another_file_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.another_file_btn.clicked.connect(self.reset_form)

        result_btn_row.addWidget(self.open_file_btn)
        result_btn_row.addWidget(self.open_folder_btn)
        result_btn_row.addWidget(self.another_file_btn)
        result_btn_row.addStretch()
        result_layout.addLayout(result_btn_row)

        # Progress bar & Status
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("MergeProgressBar")
        self.progress_bar.setVisible(False)

        self.status_label = QLabel("Pilih file PDF terlebih dahulu untuk memulai.")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setWordWrap(True)

        # Bottom action bar
        bottom_bar = QHBoxLayout()
        self.compress_btn = QPushButton("Compress PDF")
        self.compress_btn.setObjectName("ActionLargeButton")
        self.compress_btn.setToolTip("Mulai proses kompresi dokumen PDF.")
        self.compress_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.compress_btn.setEnabled(False)
        self.compress_btn.clicked.connect(self.start_compress)

        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setToolTip("Kosongkan file yang dipilih dan reset form.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self.reset_form)

        bottom_bar.addWidget(self.compress_btn)
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

        # Apply settings defaults & connect listener
        self._apply_settings_defaults()
        get_settings_service().settings_changed.connect(self._on_settings_changed)

    def _apply_settings_defaults(self):
        settings = get_settings_service()
        preset = settings.get("default_compress_preset", "recommended")
        if preset in self.preset_cards:
            self.select_preset(preset)

    def _on_settings_changed(self):
        if self.current_file:
            self.current_output_dir = get_effective_output_dir(self.current_file)
            self.output_dir_label.setText(self.current_output_dir)

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

    def select_preset(self, preset_key: str):
        self.selected_preset = preset_key
        for key, card in self.preset_cards.items():
            card.set_selected(key == preset_key)

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
        start_dir = self.current_output_dir or get_effective_output_dir(self.current_file)
        chosen_dir = QFileDialog.getExistingDirectory(
            self,
            "Pilih Folder Penyimpanan File Hasil",
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
            # Prompt user for password
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

        # Set default output name and folder
        base_name, _ = os.path.splitext(os.path.basename(norm_path))
        default_output_name = f"{base_name}_compressed.pdf"
        self.output_name_edit.setText(default_output_name)

        self.current_output_dir = get_effective_output_dir(norm_path)
        self.output_dir_label.setText(self.current_output_dir)

        # Apply default preset from settings
        self._apply_settings_defaults()

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

        self.compress_btn.setEnabled(True)
        self.status_label.setText("Dokumen siap dikompresi. Tentukan preset dan klik 'Compress PDF'.")

    def start_compress(self):
        if not self.current_file:
            QMessageBox.warning(self, "Peringatan", "Silakan pilih file PDF terlebih dahulu.")
            return

        out_name = self.output_name_edit.text().strip()
        ok_name, err_name = validate_output_filename(out_name)
        if not ok_name:
            QMessageBox.warning(self, "Nama File Tidak Valid", err_name)
            return

        if not out_name.lower().endswith(".pdf"):
            out_name += ".pdf"
            self.output_name_edit.setText(out_name)

        if not self.current_output_dir or not os.path.exists(self.current_output_dir):
            QMessageBox.warning(self, "Folder Tidak Valid", "Folder tujuan tidak dapat diakses.")
            return

        target_path = os.path.abspath(os.path.join(self.current_output_dir, out_name))

        # Check if output is identical to input
        if os.path.normcase(target_path) == os.path.normcase(self.current_file):
            QMessageBox.warning(
                self,
                "Nama Output Tidak Diperbolehkan",
                "Nama file output tidak boleh sama dengan file sumber.\n"
                "Demi keamanan data Anda, JackPDF tidak akan menimpa file asli.",
            )
            return

        # Check if target already exists and handle conflict according to settings
        settings = get_settings_service()
        conflict_action = settings.get("conflict_action", "confirm")

        if os.path.exists(target_path):
            if conflict_action == "auto_number":
                target_path = get_safe_destination_path(self.current_output_dir, out_name)
                self.output_name_edit.setText(os.path.basename(target_path))
            else:
                confirm = QMessageBox.question(
                    self,
                    "Konfirmasi Penimpaan File",
                    f"File '{out_name}' sudah ada di folder tujuan.\nApakah Anda ingin menggantinya?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if confirm != QMessageBox.StandardButton.Yes:
                    return

        # Check for digital signatures
        if check_pdf_signatures(self.current_file, self.current_password):
            sig_warn = QMessageBox.warning(
                self,
                "Peringatan Tanda Tangan Digital",
                "Dokumen ini terdeteksi memiliki tanda tangan digital.\n\n"
                "Menyimpan ulang PDF selama proses kompresi dapat membatalkan atau merusak keabsahan tanda tangan digital.\n\n"
                "Apakah Anda ingin tetap melanjutkan proses kompresi?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if sig_warn != QMessageBox.StandardButton.Yes:
                return

        # Start background compression worker
        self.set_ui_busy(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(10)
        self.status_label.setText("Memulai proses kompresi PDF...")
        self.result_card.setVisible(False)

        self.worker = PdfTaskWorker(
            compress_pdf,
            self.current_file,
            target_path,
            preset=self.selected_preset,
            password=self.current_password,
        )
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_worker_progress(self, current: int, total: int, message: str):
        if total > 0:
            pct = int((current / total) * 100)
            self.progress_bar.setValue(pct)
        self.status_label.setText(message)

    def on_worker_finished(self, success: bool, message: str, result_data: Optional[Dict[str, Any]]):
        self.set_ui_busy(False)
        self.progress_bar.setVisible(False)

        if success and result_data:
            self.last_compressed_file = result_data.get("output_path")
            orig_sz = result_data.get("original_size", 0)
            comp_sz = result_data.get("compressed_size", 0)
            is_larger = result_data.get("is_larger", False)
            is_same = result_data.get("is_same", False)
            summary_txt = result_data.get("summary_text", "")

            # Display metric values
            self.orig_size_label.setText(format_file_size(orig_sz))
            self.final_size_label.setText(format_file_size(comp_sz))
            self.savings_badge.setText(summary_txt)

            if is_larger:
                self.savings_badge.setObjectName("BadgeWarning")
                self.larger_note_label.setVisible(True)
            elif is_same:
                self.savings_badge.setObjectName("BadgeNeutral")
                self.larger_note_label.setVisible(False)
            else:
                self.savings_badge.setObjectName("BadgeSuccess")
                self.larger_note_label.setVisible(False)

            self.savings_badge.style().unpolish(self.savings_badge)
            self.savings_badge.style().polish(self.savings_badge)

            self.result_card.setVisible(True)
            self.status_label.setText(f"Selesai! File tersimpan di: {self.last_compressed_file}")

            # Reload preview with compressed result
            if self.last_compressed_file and os.path.exists(self.last_compressed_file):
                self.preview_panel.load_document(self.last_compressed_file, page_num=0)
                self.preview_panel.set_summary_badge("Hasil Kompresi")

            # Check post-processing settings
            settings = get_settings_service()
            if settings.get("auto_open_folder"):
                self.open_output_folder()
            if settings.get("auto_open_file"):
                self.open_compressed_file()
        else:
            self.status_label.setText("Proses kompresi gagal.")
            QMessageBox.critical(self, "Kompresi Gagal", message)

    def open_compressed_file(self):
        if self.last_compressed_file and os.path.exists(self.last_compressed_file):
            open_file_with_default_app(self.last_compressed_file)

    def open_output_folder(self):
        if self.last_compressed_file and os.path.exists(self.last_compressed_file):
            open_in_file_manager(self.last_compressed_file)
        elif self.current_output_dir and os.path.exists(self.current_output_dir):
            open_in_file_manager(self.current_output_dir)

    def set_ui_busy(self, busy: bool):
        self.compress_btn.setEnabled(not busy)
        self.reset_btn.setEnabled(not busy)
        self.settings_card.setEnabled(not busy)
        self.info_card.setEnabled(not busy)

    def reset_form(self):
        self.current_file = None
        self.current_password = None
        self.current_page_count = 0
        self.last_compressed_file = None
        self.select_preset("balanced")

        self.info_card.setVisible(False)
        self.settings_card.setVisible(False)
        self.result_card.setVisible(False)
        self.drop_zone.setVisible(True)
        self.progress_bar.setVisible(False)
        self.compress_btn.setEnabled(False)
        self.status_label.setText("Pilih file PDF terlebih dahulu untuk memulai.")

        if hasattr(self, "preview_panel"):
            self.preview_panel.clear_preview()
            self.preview_panel.setVisible(False)
        if hasattr(self, "toggle_preview_btn"):
            self.toggle_preview_btn.setVisible(False)

