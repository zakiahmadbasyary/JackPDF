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


class FeatureCard(QFrame):
    selected = Signal(str)

    def __init__(self, title: str, description: str, tooltip: str):
        super().__init__()
        self.setObjectName("FeatureCard")
        self.setMinimumHeight(140)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        icon_label = QLabel("PDF")
        icon_label.setObjectName("FeatureIcon")
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setFixedSize(42, 42)

        title_label = QLabel(title)
        title_label.setObjectName("FeatureTitle")

        description_label = QLabel(description)
        description_label.setObjectName("FeatureDescription")
        description_label.setWordWrap(True)

        action = QPushButton("Buka tool  →")
        action.setObjectName("CardAction")
        action.setToolTip(tooltip)
        action.setCursor(Qt.CursorShape.PointingHandCursor)
        action.clicked.connect(lambda: self.selected.emit(title))

        self.setToolTip(tooltip)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(description_label, 1)
        layout.addWidget(action, alignment=Qt.AlignmentFlag.AlignLeft)


class HomePage(QWidget):
    feature_selected = Signal(str)

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

        settings = QPushButton("⚙")
        settings.setObjectName("IconButton")
        settings.setToolTip("Pengaturan JackPDF.")
        settings.setFixedSize(40, 40)
        header.addWidget(settings)

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
            ("Split PDF", "Pisahkan halaman sesuai kebutuhan.", "Pisahkan PDF berdasarkan halaman."),
            ("Compress PDF", "Kurangi ukuran dokumen.", "Kompres PDF dengan pilihan kualitas."),
            ("Convert to PNG", "Ekspor halaman menjadi gambar.", "Ekspor halaman PDF menjadi PNG."),
            ("Crop PDF", "Atur area halaman yang terlihat.", "Potong area halaman PDF sesuai pilihan."),
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
        if available_width < 460:
            target_cols = 1
        elif available_width < 820:
            target_cols = 2
        elif available_width < 1200:
            target_cols = 3
        else:
            target_cols = 4

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

