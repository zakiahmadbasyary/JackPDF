from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


from app.utils.icon_utils import get_feature_icon


class FeatureCard(QFrame):
    selected = Signal(str)

    def __init__(self, title: str, description: str = "", tooltip: str = ""):
        super().__init__()
        self.title = title
        self.setObjectName("FeatureCard")
        self.setMinimumHeight(84)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 18, 14)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        icon_label = QLabel()
        icon_label.setObjectName("FeatureIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(54, 54)

        feat_pix = get_feature_icon(title, size=54)
        if not feat_pix.isNull():
            icon_label.setPixmap(feat_pix)
        else:
            icon_label.setText("PDF")

        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_label = QLabel(title)
        title_label.setObjectName("FeatureTitle")

        text_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("FeatureDescription")
            desc_label.setWordWrap(True)
            text_layout.addWidget(desc_label)

        arrow_label = QLabel("→")
        arrow_label.setObjectName("FeatureArrow")

        tip_text = tooltip or description or title
        self.setToolTip(tip_text)

        layout.addWidget(icon_label)
        layout.addLayout(text_layout, 1)
        layout.addWidget(arrow_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.title)
        super().mousePressEvent(event)


class HomePage(QWidget):
    feature_selected = Signal(str)
    settings_clicked = Signal()

    def __init__(self):
        super().__init__()

        # Main wrapper layout holding the scroll area
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Responsive Scroll Area for all screen resolutions
        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("ContentScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Content Widget inside Scroll Area
        self.content_widget = QWidget()
        self.content_widget.setObjectName("ContentWidget")
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setContentsMargins(32, 28, 32, 28)
        self.layout.setSpacing(18)

        # Header Section
        header = QHBoxLayout()
        heading = QVBoxLayout()

        title = QLabel("PDF Tools")
        title.setObjectName("PageTitle")

        subtitle = QLabel("Pilih alat yang ingin kamu gunakan.")
        subtitle.setObjectName("PageSubtitle")

        heading.addWidget(title)
        heading.addWidget(subtitle)
        header.addLayout(heading)
        header.addStretch()

        self.settings_btn = QPushButton("⚙")
        self.settings_btn.setObjectName("IconButton")
        self.settings_btn.setToolTip("Pengaturan JackPDF.")
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self.settings_clicked.emit)
        header.addWidget(self.settings_btn)

        self.layout.addLayout(header)

        # Drop Zone Section
        drop_zone = QFrame()
        drop_zone.setObjectName("DropZone")
        drop_layout = QVBoxLayout(drop_zone)
        drop_layout.setContentsMargins(16, 20, 16, 20)

        drop_title = QLabel("Mulai dengan dokumen PDF")
        drop_title.setObjectName("DropTitle")
        drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_hint = QLabel("Pilih fitur di bawah untuk mulai mengolah file.")
        drop_hint.setObjectName("DropHint")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        self.layout.addWidget(drop_zone)

        # Section Title
        section = QLabel("Semua tools")
        section.setObjectName("SectionTitle")
        self.layout.addWidget(section)

        # Adaptive Grid
        self.grid = QGridLayout()
        self.grid.setSpacing(14)
        self.layout.addLayout(self.grid)

        features = [
            ("Merge PDF", "Gabungkan beberapa file PDF.", "Gabungkan beberapa PDF menjadi satu file."),
            ("Split PDF", "Pisahkan halaman dokumen PDF.", "Pisahkan PDF berdasarkan halaman."),
            ("Compress PDF", "Kurangi ukuran file dokumen.", "Kompres PDF dengan pilihan kualitas."),
            ("Convert to PNG", "Ekspor halaman menjadi gambar.", "Ekspor halaman PDF menjadi PNG."),
            ("Crop PDF", "Potong area margin halaman.", "Potong area halaman PDF sesuai pilihan."),
        ]

        self.cards: list[FeatureCard] = []
        for name, description, tooltip in features:
            card = FeatureCard(name, description, tooltip)
            card.selected.connect(self.on_feature_selected)
            self.cards.append(card)

        self.current_cols = 0
        self.rearrange_grid(cols=2)

        self.layout.addStretch()

        # Footer
        footer = QLabel("JackPDF  •  Pemrosesan lokal  •  Tidak perlu akun")
        footer.setObjectName("Footer")
        self.layout.addWidget(footer)

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        available_width = event.size().width() - 64  # minus margins
        target_cols = 1 if available_width < 540 else 2
        self.rearrange_grid(target_cols)

    def rearrange_grid(self, cols: int):
        if cols == self.current_cols:
            return
        self.current_cols = cols

        # Remove cards from current grid layout
        for card in self.cards:
            self.grid.removeWidget(card)

        # Clear existing column stretches
        for c in range(6):
            self.grid.setColumnStretch(c, 0)

        # Re-add cards with new column arrangement
        for index, card in enumerate(self.cards):
            row = index // cols
            col = index % cols
            self.grid.addWidget(card, row, col)

        # Ensure active columns expand evenly
        for c in range(cols):
            self.grid.setColumnStretch(c, 1)

    def on_feature_selected(self, feature_name: str):
        self.feature_selected.emit(feature_name)

