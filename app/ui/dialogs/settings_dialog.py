"""
settings_dialog.py - Settings dialog for JackPDF.

Provides persistent configuration for default storage locations,
feature defaults (PNG, Compress, Crop), and application maintenance.
"""

import os
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.services.settings_service import get_settings_service
from app.utils.icon_utils import get_app_icon, get_app_logo


class SettingsDialog(QDialog):
    """Modal settings dialog for JackPDF."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pengaturan — JackPDF")
        self.setWindowIcon(get_app_icon())
        self.resize(620, 560)
        self.setMinimumSize(560, 480)

        self.service = get_settings_service()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Section
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        logo_label = QLabel()
        logo_label.setPixmap(get_app_logo(36))
        logo_label.setFixedSize(36, 36)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)

        title = QLabel("Pengaturan JackPDF")
        title.setObjectName("PageTitle")
        title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #111B29;")

        subtitle = QLabel("Kelola lokasi penyimpanan, nilai bawaan alat, dan pemeliharaan.")
        subtitle.setObjectName("PageSubtitle")
        subtitle.setStyleSheet("font-size: 8.5pt; color: #697586;")

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addWidget(logo_label)
        header_layout.addLayout(title_box)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Tabs Widget
        self.tabs = QTabWidget()
        self.tabs.setObjectName("SettingsTabs")
        self.tabs.setUsesScrollButtons(False)

        # 1. Tab Penyimpanan & Output
        self.tab_storage = QWidget()
        self._init_storage_tab(self.tab_storage)
        self.tabs.addTab(self.tab_storage, "Penyimpanan")

        # 2. Tab Preferensi Alat
        self.tab_features = QWidget()
        self._init_features_tab(self.tab_features)
        self.tabs.addTab(self.tab_features, "Preferensi Alat")

        # 3. Tab Tentang & Pemeliharaan
        self.tab_about = QWidget()
        self._init_about_tab(self.tab_about)
        self.tabs.addTab(self.tab_about, "Tentang JackPDF")

        layout.addWidget(self.tabs, 1)

        # Bottom Action Bar
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        self.reset_btn = QPushButton("Reset ke Bawaan")
        self.reset_btn.setObjectName("SecondaryButton")
        self.reset_btn.setToolTip("Kembalikan seluruh pengaturan ke konfigurasi default.")
        self.reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset_clicked)

        self.cancel_btn = QPushButton("Batal")
        self.cancel_btn.setObjectName("SecondaryButton")
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Simpan Pengaturan")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save_clicked)

        bottom_row.addWidget(self.reset_btn)
        bottom_row.addStretch()
        bottom_row.addWidget(self.cancel_btn)
        bottom_row.addWidget(self.save_btn)
        layout.addLayout(bottom_row)

        # Load stored settings into controls
        self.load_values()

    def _init_storage_tab(self, tab: QWidget):
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(16)

        # Group 1: Output Directory
        sec1_title = QLabel("Folder Penyimpanan Hasil")
        sec1_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29;")
        vbox.addWidget(sec1_title)

        self.radio_out_source = QRadioButton("Simpan di folder yang sama dengan file sumber (Bawaan)")
        self.radio_out_source.setObjectName("RadioChoice")
        self.radio_out_source.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_out_custom = QRadioButton("Simpan ke folder khusus:")
        self.radio_out_custom.setObjectName("RadioChoice")
        self.radio_out_custom.setCursor(Qt.CursorShape.PointingHandCursor)

        self.out_group = QButtonGroup(self)
        self.out_group.addButton(self.radio_out_source)
        self.out_group.addButton(self.radio_out_custom)

        custom_row = QHBoxLayout()
        custom_row.setContentsMargins(24, 0, 0, 0)
        custom_row.setSpacing(8)

        self.custom_dir_edit = QLineEdit()
        self.custom_dir_edit.setObjectName("StyledInput")
        self.custom_dir_edit.setPlaceholderText("Pilih folder penyimpanan tetap...")

        self.browse_dir_btn = QPushButton("Pilih Folder...")
        self.browse_dir_btn.setObjectName("SecondaryButton")
        self.browse_dir_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_dir_btn.clicked.connect(self._browse_custom_dir)

        self.radio_out_custom.toggled.connect(self.custom_dir_edit.setEnabled)
        self.radio_out_custom.toggled.connect(self.browse_dir_btn.setEnabled)

        custom_row.addWidget(self.custom_dir_edit, 1)
        custom_row.addWidget(self.browse_dir_btn)

        vbox.addWidget(self.radio_out_source)
        vbox.addWidget(self.radio_out_custom)
        vbox.addLayout(custom_row)
        vbox.addSpacing(6)

        # Group 2: Conflict resolution
        sec2_title = QLabel("Penanganan File Duplikat")
        sec2_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29;")
        vbox.addWidget(sec2_title)

        self.radio_conflict_confirm = QRadioButton("Tanyakan konfirmasi sebelum menimpa file yang sudah ada (Bawaan)")
        self.radio_conflict_confirm.setObjectName("RadioChoice")
        self.radio_conflict_confirm.setCursor(Qt.CursorShape.PointingHandCursor)

        self.radio_conflict_auto = QRadioButton("Otomatis tambahkan nomor urut unik (contoh: file_001.pdf)")
        self.radio_conflict_auto.setObjectName("RadioChoice")
        self.radio_conflict_auto.setCursor(Qt.CursorShape.PointingHandCursor)

        self.conflict_group = QButtonGroup(self)
        self.conflict_group.addButton(self.radio_conflict_confirm)
        self.conflict_group.addButton(self.radio_conflict_auto)

        vbox.addWidget(self.radio_conflict_confirm)
        vbox.addWidget(self.radio_conflict_auto)
        vbox.addSpacing(6)

        # Group 3: Post-process actions
        sec3_title = QLabel("Tindakan Setelah Selesai")
        sec3_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29;")
        vbox.addWidget(sec3_title)

        self.cb_auto_folder = QCheckBox("Otomatis buka folder hasil di Windows Explorer setelah proses selesai")
        self.cb_auto_folder.setObjectName("StyledCheckBox")
        self.cb_auto_folder.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cb_auto_file = QCheckBox("Otomatis buka file hasil dengan aplikasi pembaca PDF default")
        self.cb_auto_file.setObjectName("StyledCheckBox")
        self.cb_auto_file.setCursor(Qt.CursorShape.PointingHandCursor)

        vbox.addWidget(self.cb_auto_folder)
        vbox.addWidget(self.cb_auto_file)
        vbox.addStretch()

    def _init_features_tab(self, tab: QWidget):
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(16)

        grid = QGridLayout()
        grid.setSpacing(12)

        # 1. Convert to PNG
        png_title = QLabel("Convert to PNG")
        png_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29;")
        grid.addWidget(png_title, 0, 0, 1, 2)

        dpi_lbl = QLabel("Resolusi Gambar Bawaan:")
        dpi_lbl.setStyleSheet("color: #263445; font-size: 9pt;")
        self.combo_dpi = QComboBox()
        self.combo_dpi.setObjectName("StyledComboBox")
        self.combo_dpi.addItem("Standar (150 DPI)", 150)
        self.combo_dpi.addItem("Tinggi (200 DPI) - Rekomendasi", 200)
        self.combo_dpi.addItem("Sangat Tinggi (300 DPI)", 300)

        grid.addWidget(dpi_lbl, 1, 0)
        grid.addWidget(self.combo_dpi, 1, 1)

        color_lbl = QLabel("Mode Warna Bawaan:")
        color_lbl.setStyleSheet("color: #263445; font-size: 9pt;")
        self.combo_color = QComboBox()
        self.combo_color.setObjectName("StyledComboBox")
        self.combo_color.addItem("RGB (Warna Penuh)", "rgb")
        self.combo_color.addItem("Grayscale (Hitam & Putih)", "grayscale")

        grid.addWidget(color_lbl, 2, 0)
        grid.addWidget(self.combo_color, 2, 1)

        # 2. Compress PDF
        compress_title = QLabel("Compress PDF")
        compress_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29; margin-top: 6px;")
        grid.addWidget(compress_title, 3, 0, 1, 2)

        comp_lbl = QLabel("Preset Kompresi Bawaan:")
        comp_lbl.setStyleSheet("color: #263445; font-size: 9pt;")
        self.combo_compress = QComboBox()
        self.combo_compress.setObjectName("StyledComboBox")
        self.combo_compress.addItem("Rendah (Hasil Cepat)", "low")
        self.combo_compress.addItem("Rekomendasi (Keseimbangan Terbaik)", "recommended")
        self.combo_compress.addItem("Tinggi (Ukuran Minimum)", "high")

        grid.addWidget(comp_lbl, 4, 0)
        grid.addWidget(self.combo_compress, 4, 1)

        # 3. Crop PDF
        crop_title = QLabel("Crop PDF")
        crop_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29; margin-top: 6px;")
        grid.addWidget(crop_title, 5, 0, 1, 2)

        crop_lbl = QLabel("Satuan Ukuran Margin:")
        crop_lbl.setStyleSheet("color: #263445; font-size: 9pt;")
        self.combo_crop_unit = QComboBox()
        self.combo_crop_unit.setObjectName("StyledComboBox")
        self.combo_crop_unit.addItem("Milimeter (mm) - Bawaan", "mm")
        self.combo_crop_unit.addItem("Inci (inch)", "inch")

        grid.addWidget(crop_lbl, 6, 0)
        grid.addWidget(self.combo_crop_unit, 6, 1)

        vbox.addLayout(grid)
        vbox.addStretch()

    def _init_about_tab(self, tab: QWidget):
        vbox = QVBoxLayout(tab)
        vbox.setContentsMargins(16, 16, 16, 16)
        vbox.setSpacing(14)

        # App Info Card
        info_frame = QFrame()
        info_frame.setStyleSheet(
            "background: #F7F9FC; border: 1px solid #DCE3EC; border-radius: 10px; padding: 12px;"
        )
        info_vbox = QVBoxLayout(info_frame)
        info_vbox.setSpacing(6)

        app_name = QLabel("JackPDF — Versi 1.0.0")
        app_name.setStyleSheet("font-size: 11pt; font-weight: 700; color: #071426;")

        tagline = QLabel("Your everyday PDF toolkit.")
        tagline.setStyleSheet("font-size: 9pt; color: #1D6FEA; font-weight: 600;")

        desc = QLabel(
            "Aplikasi desktop modern untuk memproses, menggabungkan, memisahkan, "
            "mengompres, dan memotong dokumen PDF secara lokal, cepat, dan aman tanpa memerlukan koneksi internet."
        )
        desc.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        desc.setWordWrap(True)

        tech = QLabel("Runtime: Python 3.12  •  PySide6 (Qt)  •  PyMuPDF (fitz)")
        tech.setStyleSheet("color: #8C9BAE; font-size: 8pt; font-weight: 500;")

        info_vbox.addWidget(app_name)
        info_vbox.addWidget(tagline)
        info_vbox.addWidget(desc)
        info_vbox.addWidget(tech)
        vbox.addWidget(info_frame)

        # Maintenance Card
        maint_title = QLabel("Pemeliharaan & Cache")
        maint_title.setStyleSheet("font-size: 9.5pt; font-weight: 700; color: #111B29;")
        vbox.addWidget(maint_title)

        maint_desc = QLabel(
            "Bersihkan file sementara dan cache pratinjau thumbnail jika ingin menghemat ruang penyimpanan komputer."
        )
        maint_desc.setStyleSheet("color: #5D6B7D; font-size: 8.5pt;")
        maint_desc.setWordWrap(True)
        vbox.addWidget(maint_desc)

        clear_btn = QPushButton("Bersihkan File Sementara & Cache")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._on_clear_cache_clicked)
        vbox.addWidget(clear_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        vbox.addStretch()

    def _browse_custom_dir(self):
        start = self.custom_dir_edit.text().strip() or os.path.expanduser("~")
        chosen = QFileDialog.getExistingDirectory(self, "Pilih Folder Penyimpanan Default", start)
        if chosen:
            self.custom_dir_edit.setText(os.path.abspath(chosen))

    def load_values(self):
        """Load stored values into UI controls."""
        settings = self.service.get_all()

        # Storage
        if settings.get("output_mode") == "custom":
            self.radio_out_custom.setChecked(True)
        else:
            self.radio_out_source.setChecked(True)

        custom_dir = settings.get("custom_output_dir", "")
        self.custom_dir_edit.setText(custom_dir)
        self.custom_dir_edit.setEnabled(self.radio_out_custom.isChecked())
        self.browse_dir_btn.setEnabled(self.radio_out_custom.isChecked())

        if settings.get("conflict_action") == "auto_number":
            self.radio_conflict_auto.setChecked(True)
        else:
            self.radio_conflict_confirm.setChecked(True)

        self.cb_auto_folder.setChecked(bool(settings.get("auto_open_folder", False)))
        self.cb_auto_file.setChecked(bool(settings.get("auto_open_file", False)))

        # Feature defaults
        dpi = settings.get("default_png_dpi", 200)
        idx_dpi = self.combo_dpi.findData(dpi)
        if idx_dpi != -1:
            self.combo_dpi.setCurrentIndex(idx_dpi)

        color = settings.get("default_png_color", "rgb")
        idx_col = self.combo_color.findData(color)
        if idx_col != -1:
            self.combo_color.setCurrentIndex(idx_col)

        compress = settings.get("default_compress_preset", "recommended")
        idx_comp = self.combo_compress.findData(compress)
        if idx_comp != -1:
            self.combo_compress.setCurrentIndex(idx_comp)

        crop_unit = settings.get("default_crop_unit", "mm")
        idx_crop = self.combo_crop_unit.findData(crop_unit)
        if idx_crop != -1:
            self.combo_crop_unit.setCurrentIndex(idx_crop)

    def _on_save_clicked(self):
        """Gather values and save to persistent storage."""
        if self.radio_out_custom.isChecked():
            path = self.custom_dir_edit.text().strip()
            if not path or not os.path.isdir(path):
                QMessageBox.warning(
                    self,
                    "Folder Tidak Valid",
                    "Folder khusus yang Anda pilih tidak valid atau belum ditentukan. Silakan tentukan folder yang ada.",
                )
                self.tabs.setCurrentIndex(0)
                return

        new_settings = {
            "output_mode": "custom" if self.radio_out_custom.isChecked() else "source",
            "custom_output_dir": self.custom_dir_edit.text().strip(),
            "conflict_action": "auto_number" if self.radio_conflict_auto.isChecked() else "confirm",
            "auto_open_folder": self.cb_auto_folder.isChecked(),
            "auto_open_file": self.cb_auto_file.isChecked(),
            "default_png_dpi": self.combo_dpi.currentData(),
            "default_png_color": self.combo_color.currentData(),
            "default_compress_preset": self.combo_compress.currentData(),
            "default_crop_unit": self.combo_crop_unit.currentData(),
        }

        self.service.save_all(new_settings)
        self.accept()

    def _on_reset_clicked(self):
        confirm = QMessageBox.question(
            self,
            "Reset Pengaturan",
            "Apakah Anda yakin ingin mengembalikan seluruh pengaturan ke konfigurasi default?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.service.reset_to_defaults()
            self.load_values()

    def _on_clear_cache_clicked(self):
        deleted = self.service.clear_cache()
        QMessageBox.information(
            self,
            "Pembersihan Cache",
            f"Pembersihan selesai. {deleted} file sementara berhasil dibersihkan.",
        )
