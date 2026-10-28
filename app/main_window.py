from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.ui.home_page import HomePage
from app.ui.pages.merge_page import MergePage
from app.ui.pages.split_page import SplitPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JackPDF")
        self.resize(1100, 720)
        self.setMinimumSize(680, 480)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar Frame
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 20, 16, 16)
        sidebar_layout.setSpacing(8)

        brand = QLabel("▣  JackPDF")
        brand.setObjectName("Brand")
        sidebar_layout.addWidget(brand)

        tagline = QLabel("Your everyday PDF toolkit")
        tagline.setObjectName("SidebarHint")
        tagline.setWordWrap(True)
        sidebar_layout.addWidget(tagline)
        sidebar_layout.addSpacing(16)

        self.home_button = QPushButton("⌂   Beranda")
        self.home_button.setObjectName("NavButton")
        self.home_button.setProperty("active", "true")
        self.home_button.setToolTip("Kembali ke halaman utama JackPDF.")
        self.home_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.home_button.clicked.connect(self.show_home)
        sidebar_layout.addWidget(self.home_button)

        tools_label = QLabel("PDF TOOLS")
        tools_label.setObjectName("SectionLabel")
        sidebar_layout.addWidget(tools_label)

        self.nav_buttons: dict[str, QPushButton] = {}
        nav_items = [
            ("Merge PDF", "Gabungkan beberapa PDF menjadi satu file.", True),
            ("Split PDF", "Pisahkan PDF berdasarkan halaman.", True),
            ("Compress PDF", "Kurangi ukuran file PDF.", False),
            ("Convert to PNG", "Ekspor halaman PDF menjadi gambar PNG.", False),
            ("Crop PDF", "Pilih area halaman PDF yang ingin dipotong.", False),
        ]

        for label, tooltip, is_active in nav_items:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor if is_active else Qt.CursorShape.ArrowCursor)
            button.setEnabled(is_active)

            if label == "Merge PDF":
                button.clicked.connect(self.show_merge)
            elif label == "Split PDF":
                button.clicked.connect(self.show_split)

            self.nav_buttons[label] = button
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        local_note = QLabel("●  File diproses secara lokal")
        local_note.setObjectName("LocalNote")
        local_note.setWordWrap(True)
        sidebar_layout.addWidget(local_note)

        # Content Pages Stack
        self.content = QStackedWidget()

        self.home_page = HomePage()
        self.merge_page = MergePage()
        self.split_page = SplitPage()

        # Connect Navigation
        self.home_page.feature_selected.connect(self.on_feature_selected)
        self.merge_page.go_back.connect(self.show_home)
        self.split_page.go_back.connect(self.show_home)

        self.content.addWidget(self.home_page)   # index 0
        self.content.addWidget(self.merge_page)  # index 1
        self.content.addWidget(self.split_page)  # index 2

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.content, 1)
        self.setCentralWidget(root)

    def _set_active_nav(self, active_name: str):
        # Update active properties for styling
        self.home_button.setProperty("active", "true" if active_name == "Beranda" else "false")
        self.home_button.style().unpolish(self.home_button)
        self.home_button.style().polish(self.home_button)

        for name, btn in self.nav_buttons.items():
            btn.setProperty("active", "true" if name == active_name else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def show_home(self):
        self.content.setCurrentWidget(self.home_page)
        self._set_active_nav("Beranda")

    def show_merge(self):
        self.content.setCurrentWidget(self.merge_page)
        self._set_active_nav("Merge PDF")

    def show_split(self):
        self.content.setCurrentWidget(self.split_page)
        self._set_active_nav("Split PDF")

    def on_feature_selected(self, feature_name: str):
        if feature_name == "Merge PDF":
            self.show_merge()
        elif feature_name == "Split PDF":
            self.show_split()
        else:
            print(f"Fitur '{feature_name}' akan segera hadir.")
