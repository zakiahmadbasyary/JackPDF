# JackPDF --- Setup dan UI Desktop

> Panduan awal untuk menyiapkan proyek JackPDF dan membangun antarmuka
> desktop modern menggunakan Python dan PySide6.

## 1. Gambaran Proyek

**JackPDF** adalah aplikasi Windows desktop untuk mengolah dokumen PDF
secara lokal. Versi awal berfokus pada UI dan navigasi; fitur pemrosesan
akan dihubungkan secara bertahap.

### Fitur utama

1.  **Merge PDF** --- menggabungkan beberapa PDF menjadi satu file.
2.  **Split PDF** --- memisahkan halaman berdasarkan rentang atau
    halaman tertentu.
3.  **Compress PDF** --- mengurangi ukuran PDF dengan preset kualitas.
4.  **Convert to PNG** --- mengekspor halaman PDF menjadi gambar PNG.
5.  **Crop PDF** --- memilih area halaman melalui preview.
6.  **Convert to Word** --- mengonversi PDF menjadi DOCX; hasil tata
    letak bergantung pada dokumen dan mesin konversi.

### Prinsip UI

-   Modern, minimalis, dan mudah dipahami.
-   Warna utama biru dengan latar putih/abu-abu muda.
-   Sidebar untuk navigasi dan area utama untuk kartu fitur atau halaman
    kerja.
-   Tooltip pada tombol dan ikon agar fungsi kontrol mudah dipahami.
-   Pemrosesan dilakukan lokal; file tidak perlu dikirim ke server.
-   UI tidak boleh membeku saat operasi PDF yang berat dijalankan.

## 2. Teknologi

  -----------------------------------------------------------------------
  Teknologi                           Peran
  ----------------------------------- -----------------------------------
  Python 3.12                         Bahasa utama

  PySide6                             UI desktop berbasis Qt

  PyMuPDF                             Membaca, merender, dan memanipulasi
                                      PDF

  pypdf                               Operasi PDF tambahan

  Pillow                              Utilitas gambar bila diperlukan

  pytest                              Pengujian

  PyInstaller                         Mengemas aplikasi menjadi
                                      executable Windows

  pdf2docx atau konverter setara      Kandidat untuk PDF ke Word; perlu
                                      diuji pada dokumen nyata
  -----------------------------------------------------------------------

> Catatan: konversi PDF ke Word lebih kompleks daripada ekspor PNG.
> Jangan menganggap tata letak, tabel, atau font selalu dapat
> dipertahankan sempurna. Periksa lisensi dan kompatibilitas pustaka
> sebelum membuat distribusi.

## 3. Persiapan Lingkungan Windows

### Prasyarat

-   Windows 10 atau Windows 11.
-   Python 3.12 terpasang.
-   Visual Studio Code (opsional, tetapi direkomendasikan).
-   Ekstensi Python untuk VS Code.

Periksa Python di terminal:

``` powershell
py --version
```

Jika Python 3.12 tersedia, buat proyek:

``` powershell
mkdir JackPDF
cd JackPDF

py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install pyside6 pymupdf pypdf pillow pytest
```

Jika PowerShell memblokir aktivasi environment, jalankan perintah ini
hanya untuk sesi terminal saat ini:

``` powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Alternatif tanpa aktivasi environment:

``` powershell
.venv\Scripts\python.exe -m pip install pyside6 pymupdf pypdf pillow pytest
```

### `requirements.txt`

Buat file `requirements.txt` dengan isi berikut:

``` text
PySide6
PyMuPDF
pypdf
Pillow
pytest
```

Setelah lingkungan siap, instal dependensi dari file:

``` powershell
pip install -r requirements.txt
```

Untuk proyek yang sudah stabil, simpan versi paket yang benar-benar
telah diuji, misalnya dengan:

``` powershell
pip freeze > requirements-lock.txt
```

## 4. Struktur Folder Awal

Buat struktur berikut. Folder `services` akan menampung logika PDF,
sedangkan folder `ui` hanya berisi antarmuka.

``` text
JackPDF/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main_window.py
│   ├── ui/
│   │   ├── __init__.py
│   │   └── home_page.py
│   ├── services/
│   │   └── __init__.py
│   ├── workers/
│   │   └── __init__.py
│   └── utils/
│       └── __init__.py
├── assets/
│   ├── icons/
│   └── styles/
│       └── light.qss
└── tests/
```

Buat file `__init__.py` kosong di setiap folder Python yang ditunjukkan.

## 5. Implementasi UI Pertama

Tahap ini membuat jendela JackPDF dengan enam kartu fitur dan tooltip.
Tombol belum menjalankan pemrosesan PDF; fungsinya saat ini untuk
membangun fondasi UI.

### `main.py`

``` python
import sys

from PySide6.QtWidgets import QApplication
from app.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JackPDF")
    app.setOrganizationName("JackPDF")

    with open("assets/styles/light.qss", "r", encoding="utf-8") as style_file:
        app.setStyleSheet(style_file.read())

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

### `app/main_window.py`

``` python
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("JackPDF")
        self.resize(1100, 720)
        self.setMinimumSize(900, 600)

        root = QWidget()
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 18)
        sidebar_layout.setSpacing(10)

        brand = QLabel("▣  JackPDF")
        brand.setObjectName("Brand")
        sidebar_layout.addWidget(brand)

        tagline = QLabel("Your everyday PDF toolkit")
        tagline.setObjectName("SidebarHint")
        tagline.setWordWrap(True)
        sidebar_layout.addWidget(tagline)
        sidebar_layout.addSpacing(24)

        home_button = QPushButton("⌂   Beranda")
        home_button.setObjectName("NavButton")
        home_button.setToolTip("Kembali ke halaman utama JackPDF.")
        sidebar_layout.addWidget(home_button)

        tools_label = QLabel("PDF TOOLS")
        tools_label.setObjectName("SectionLabel")
        sidebar_layout.addWidget(tools_label)

        nav_items = [
            ("Merge PDF", "Gabungkan beberapa PDF menjadi satu file."),
            ("Split PDF", "Pisahkan PDF berdasarkan halaman."),
            ("Compress PDF", "Kurangi ukuran file PDF."),
            ("Convert to PNG", "Ekspor halaman PDF menjadi gambar PNG."),
            ("Crop PDF", "Pilih area halaman PDF yang ingin dipotong."),
            ("Convert to Word", "Konversi PDF menjadi dokumen DOCX."),
        ]

        for label, tooltip in nav_items:
            button = QPushButton(label)
            button.setObjectName("NavButton")
            button.setToolTip(tooltip)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setEnabled(False)  # Aktifkan setelah halaman fitur dibuat.
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        local_note = QLabel("●  File diproses secara lokal")
        local_note.setObjectName("LocalNote")
        local_note.setWordWrap(True)
        sidebar_layout.addWidget(local_note)

        content = QStackedWidget()
        content.addWidget(HomePage())

        root_layout.addWidget(sidebar)
        root_layout.addWidget(content, 1)
        self.setCentralWidget(root)
```

### `app/ui/home_page.py`

``` python
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class FeatureCard(QFrame):
    selected = Signal(str)

    def __init__(self, title: str, description: str, tooltip: str):
        super().__init__()
        self.setObjectName("FeatureCard")
        self.setMinimumHeight(150)

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
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(34, 30, 34, 28)
        layout.setSpacing(18)

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

        layout.addLayout(header)

        drop_zone = QFrame()
        drop_zone.setObjectName("DropZone")
        drop_layout = QVBoxLayout(drop_zone)

        drop_title = QLabel("Mulai dengan dokumen PDF")
        drop_title.setObjectName("DropTitle")
        drop_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_hint = QLabel("Pilih fitur di bawah untuk mulai mengolah file.")
        drop_hint.setObjectName("DropHint")
        drop_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        drop_layout.addWidget(drop_title)
        drop_layout.addWidget(drop_hint)
        layout.addWidget(drop_zone)

        section = QLabel("Semua tools")
        section.setObjectName("SectionTitle")
        layout.addWidget(section)

        grid = QGridLayout()
        grid.setSpacing(14)

        features = [
            ("Merge PDF", "Gabungkan beberapa file PDF.", "Gabungkan beberapa PDF menjadi satu file."),
            ("Split PDF", "Pisahkan halaman sesuai kebutuhan.", "Pisahkan PDF berdasarkan halaman."),
            ("Compress PDF", "Kurangi ukuran dokumen.", "Kompres PDF dengan pilihan kualitas."),
            ("Convert to PNG", "Ekspor halaman menjadi gambar.", "Ekspor halaman PDF menjadi PNG."),
            ("Crop PDF", "Atur area halaman yang terlihat.", "Potong area halaman PDF sesuai pilihan."),
            ("Convert to Word", "Buat dokumen Word yang dapat diedit.", "Konversi PDF ke DOCX."),
        ]

        for index, (name, description, tooltip) in enumerate(features):
            card = FeatureCard(name, description, tooltip)
            card.selected.connect(self.on_feature_selected)
            grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(grid)
        layout.addStretch()

        footer = QLabel("JackPDF  •  Pemrosesan lokal  •  Tidak perlu akun")
        footer.setObjectName("Footer")
        layout.addWidget(footer)

    def on_feature_selected(self, feature_name: str):
        # Placeholder: navigasi dan operasi PDF akan ditambahkan pada tahap berikutnya.
        print(f"Fitur dipilih: {feature_name}")
```

### `assets/styles/light.qss`

``` css
QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #172033;
    background: #F7F8FC;
}

QFrame#Sidebar {
    background: #FFFFFF;
    border-right: 1px solid #E7EAF0;
}

QLabel#Brand {
    font-size: 19pt;
    font-weight: 700;
    color: #2563EB;
    padding: 4px 0;
}

QLabel#SidebarHint,
QLabel#PageSubtitle,
QLabel#FeatureDescription,
QLabel#DropHint,
QLabel#Footer {
    color: #697586;
}

QLabel#SectionLabel {
    color: #8A94A6;
    font-size: 8pt;
    font-weight: 700;
    padding-top: 8px;
}

QPushButton#NavButton {
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: #475467;
}

QPushButton#NavButton:hover {
    background: #EFF6FF;
    color: #1D4ED8;
}

QPushButton#NavButton:disabled {
    color: #98A2B3;
}

QLabel#LocalNote {
    color: #16803D;
    background: #ECFDF3;
    border-radius: 8px;
    padding: 10px;
    font-size: 9pt;
}

QLabel#PageTitle {
    font-size: 24pt;
    font-weight: 700;
    color: #172033;
}

QLabel#SectionTitle {
    font-size: 13pt;
    font-weight: 700;
}

QFrame#DropZone {
    background: #FFFFFF;
    border: 1px dashed #B9C8E5;
    border-radius: 12px;
    padding: 14px;
    min-height: 75px;
}

QLabel#DropTitle {
    font-size: 12pt;
    font-weight: 600;
}

QFrame#FeatureCard {
    background: #FFFFFF;
    border: 1px solid #E6EAF2;
    border-radius: 12px;
}

QFrame#FeatureCard:hover {
    border: 1px solid #93B4F8;
    background: #FCFDFF;
}

QLabel#FeatureIcon {
    color: #2563EB;
    background: #EFF6FF;
    border-radius: 9px;
    font-weight: 700;
}

QLabel#FeatureTitle {
    font-size: 11pt;
    font-weight: 700;
}

QPushButton#CardAction {
    color: #2563EB;
    background: transparent;
    border: none;
    padding: 4px 0;
    font-weight: 600;
}

QPushButton#CardAction:hover {
    color: #1D4ED8;
}

QPushButton#IconButton {
    background: #FFFFFF;
    border: 1px solid #E3E8F0;
    border-radius: 9px;
    font-size: 15pt;
}

QPushButton#IconButton:hover {
    background: #EFF6FF;
    border-color: #BFDBFE;
}

QToolTip {
    color: #FFFFFF;
    background: #202938;
    border: 1px solid #202938;
    padding: 7px 9px;
    border-radius: 5px;
}
```

## 6. Menjalankan JackPDF

Pastikan struktur file sudah sesuai, lalu jalankan:

``` powershell
python main.py
```

Jendela JackPDF akan menampilkan sidebar, kartu enam fitur, informasi
pemrosesan lokal, dan tooltip. Tombol fitur masih berupa kerangka UI;
fungsi pemrosesan dan navigasi halaman fitur belum diimplementasikan.

### Checklist hasil tahap awal

-   [ ] Python dan virtual environment sudah siap.
-   [ ] Dependensi berhasil dipasang.
-   [ ] Struktur folder sudah dibuat.
-   [ ] Jendela JackPDF dapat dibuka.
-   [ ] Enam kartu fitur tampil.
-   [ ] Tooltip muncul saat kursor diarahkan ke tombol.
-   [ ] Tidak ada error saat aplikasi ditutup.


**Prinsip pengembangan:** pisahkan UI dari service PDF, simpan hasil
sebagai file baru secara default, dan jangan biarkan proses yang lama
membekukan jendela aplikasi.
