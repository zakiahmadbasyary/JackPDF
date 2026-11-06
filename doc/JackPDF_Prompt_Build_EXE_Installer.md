# Prompt Implementasi Packaging JackPDF Menjadi EXE dan Installer Windows

## 1. Tujuan

Lakukan packaging aplikasi **JackPDF** yang sudah selesai dikembangkan menjadi aplikasi Windows mandiri (`JackPDF.exe`), kemudian siapkan installer (`JackPDF_Setup.exe`) agar dapat dipasang pada komputer Windows lain tanpa pengguna perlu memasang Python atau dependency secara manual.

Dokumen ini ditujukan untuk AI coding agent yang bekerja langsung pada repository JackPDF.

**Kondisi project:**
- Aplikasi: JackPDF
- Bahasa: Python 3.12
- GUI: PySide6
- Pemrosesan PDF: PyMuPDF, dengan kemungkinan penggunaan pypdf dan Pillow
- Environment: virtual environment (`venv` atau `.venv`)
- Ikon aplikasi: sudah tersedia dalam format `.ico`
- Fitur aplikasi sudah selesai dikembangkan; fokus pekerjaan adalah packaging, pengujian, dan installer.
- Target: Windows 10/11, dengan prioritas kompatibilitas Windows 11.

## 2. Instruksi utama untuk coding agent

Sebelum mengubah apa pun:

1. Periksa struktur repository dan identifikasi entry point aplikasi yang sebenarnya.
2. Periksa `requirements.txt`, `pyproject.toml`, atau berkas dependency lain.
3. Identifikasi virtual environment (`venv` atau `.venv`).
4. Temukan lokasi ikon `.ico`, assets, font, gambar, konfigurasi, dan resource runtime.
5. Periksa cara aplikasi memuat resource dan menentukan lokasi file.
6. Identifikasi modul, plugin Qt, dan dependency native yang diperlukan saat runtime.
7. Jangan mengasumsikan entry point adalah `main.py`, lokasi ikon `assets/icons/jackpdf.ico`, atau struktur folder tertentu sebelum memeriksa repository.

**Jangan mengubah atau menulis ulang fitur PDF yang sudah berfungsi.** Perubahan kode hanya boleh dilakukan jika diperlukan agar aplikasi berjalan benar setelah dipaketkan. Pertahankan arsitektur, UI, alur kerja, dan perilaku aplikasi.

## 3. Teknologi packaging

Gunakan:
- **PyInstaller** untuk mengemas aplikasi Python menjadi executable Windows.
- **Inno Setup** untuk membuat installer Windows.
- **PySide6** sebagai GUI runtime.
- Dependency PDF yang memang digunakan repository, misalnya PyMuPDF, pypdf, dan Pillow.

Gunakan versi dependency yang kompatibel dengan versi Python dan PySide6 pada project. Jangan melakukan upgrade massal tanpa alasan teknis.

## 4. Tahap A — Audit kesiapan project

Lakukan audit dan laporkan:
- Entry point aplikasi.
- Versi Python dan PySide6.
- Daftar dependency runtime.
- Lokasi ikon `.ico`.
- Lokasi assets dan resource.
- Modul internal yang perlu disertakan.
- Apakah aplikasi menggunakan Qt plugin tambahan.
- Apakah ada file yang dibaca menggunakan relative path.
- Apakah ada subprocess, worker thread, atau file sementara yang memerlukan penanganan khusus.
- Apakah ada dependency native atau binary tambahan.

Buat daftar risiko packaging sebelum menjalankan build.

## 5. Tahap B — Persiapan resource path

Periksa seluruh pemanggilan resource seperti ikon, gambar, font, stylesheet, template, dan file pendukung.

Jika aplikasi masih memakai relative path yang bergantung pada current working directory, perbaiki secara terpusat menggunakan helper resource path yang kompatibel dengan mode development dan PyInstaller.

Contoh pendekatan (sesuaikan dengan struktur project):

```python
import sys
from pathlib import Path

def resource_path(relative_path: str) -> str:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent

    return str(base_path / relative_path)
```

Ketentuan:
- Jangan menyalin contoh secara membabi buta; sesuaikan lokasi helper dan root project.
- Jangan mengubah path file input/output PDF menjadi lokasi internal bundle.
- File hasil pengguna harus disimpan ke lokasi yang dipilih pengguna atau direktori pengguna yang sesuai.
- Pastikan resource dapat dibaca saat aplikasi dijalankan dari source maupun hasil packaging.
- Hindari duplikasi helper jika project sudah memiliki mekanisme resource path yang benar.

## 6. Tahap C — Konfigurasi PyInstaller

Buat konfigurasi packaging yang dapat diulang, dengan prioritas menggunakan file **`JackPDF.spec`** agar pengaturan lebih mudah dipelihara.

Konfigurasi harus:
- Menggunakan entry point yang benar.
- Memasukkan ikon `.ico` aplikasi.
- Memasukkan hanya assets/resource yang diperlukan.
- Menyertakan dependency dan modul internal yang diperlukan.
- Menangani hidden imports yang benar-benar dibutuhkan berdasarkan hasil audit.
- Memastikan plugin Qt yang diperlukan tersedia.
- Tidak memasukkan folder virtual environment.
- Tidak memasukkan cache, test artifacts, file sementara, atau file development yang tidak dibutuhkan.
- Menghindari penambahan seluruh hidden imports secara membabi buta.
- Menghindari duplikasi binary atau resource yang memperbesar paket tanpa kebutuhan.
- Menggunakan mode GUI/windowed untuk build rilis.

### Mode build awal: onedir

Mulai dengan mode `onedir`, bukan `onefile`.

Alasan:
- Lebih mudah didiagnosis jika ada dependency atau resource yang hilang.
- Lebih mudah memeriksa hasil packaging.
- Startup umumnya lebih sederhana daripada ekstraksi bundle onefile.
- Cocok untuk aplikasi desktop dengan dependency Qt.

Output yang diharapkan:

```text
dist/
└── JackPDF/
    ├── JackPDF.exe
    └── _internal/
        └── ...
```

Nama folder internal dapat mengikuti versi PyInstaller yang digunakan.

## 7. Tahap D — Build otomatis

Buat script build Windows, misalnya `build.bat`, yang:

1. Berjalan dari direktori repository.
2. Mengaktifkan virtual environment yang benar (`venv` atau `.venv` berdasarkan hasil audit).
3. Memastikan PyInstaller tersedia.
4. Menghapus output `build` dan `dist` lama dengan aman.
5. Menjalankan PyInstaller menggunakan `JackPDF.spec`.
6. Memeriksa exit code.
7. Menampilkan lokasi output jika build berhasil.
8. Menampilkan pesan error yang jelas jika build gagal.

Jangan menghapus folder source, assets, data pengguna, atau file project lain.

Sediakan instruksi build manual untuk debugging.

## 8. Tahap E — Pengujian hasil EXE

Jalankan pengujian terhadap hasil build, bukan hanya source code.

### Pengujian startup dan UI
- EXE dapat dibuka.
- Tidak muncul console window pada build rilis.
- Ikon aplikasi benar.
- Semua halaman dan navigasi tampil normal.
- Font, gambar, stylesheet, dan ikon komponen termuat.
- Dialog Open/Save bekerja.
- Aplikasi dapat ditutup dengan normal.

### Pengujian fitur PDF
Uji semua fitur yang tersedia di repository:
- Merge PDF.
- Split PDF.
- Compress PDF.
- Convert PDF to PNG.
- Crop PDF.

Pastikan:
- Input PDF dapat dibuka.
- Output tersimpan di lokasi yang dipilih.
- Nama output benar.
- File sumber tidak ditimpa tanpa persetujuan.
- File output dapat dibuka kembali.
- Progress dan worker thread berjalan normal.
- UI tidak freeze selama operasi.
- Error PDF rusak, terenkripsi, atau tidak valid ditangani dengan baik.

### Pengujian lingkungan bersih

Jika memungkinkan, uji pada Windows VM atau komputer lain yang tidak memiliki Python maupun dependency project.

Jangan menyatakan aplikasi portable atau mandiri sebelum pengujian ini berhasil.

## 9. Tahap F — Debugging packaging

Jika EXE gagal dibuka:

1. Buat build diagnostik dengan console aktif (`console=True` atau opsi PyInstaller yang sesuai).
2. Jalankan EXE dari PowerShell.
3. Catat traceback lengkap.
4. Identifikasi modul, resource, atau plugin yang hilang.
5. Perbaiki konfigurasi spec secara minimal.
6. Build ulang dan ulangi tes.

Periksa secara khusus:
- Qt platform plugin `windows`.
- Qt image format plugins bila diperlukan.
- Hidden imports yang benar-benar digunakan.
- Resource path.
- DLL/native dependency.
- Perbedaan current working directory.
- File sementara dan permission.

Jangan menyembunyikan error dengan menangkap semua exception tanpa logging.

## 10. Tahap G — Membuat installer menggunakan Inno Setup

Setelah folder `dist/JackPDF` lolos pengujian, siapkan installer menggunakan Inno Setup.

Installer harus:
- Memasang seluruh isi folder hasil build ke direktori instalasi.
- Membuat shortcut Start Menu.
- Menawarkan shortcut Desktop secara opsional.
- Menampilkan nama dan versi aplikasi.
- Menggunakan ikon JackPDF.
- Menyediakan proses uninstall.
- Tidak menghapus dokumen atau PDF milik pengguna saat uninstall.
- Tidak membutuhkan hak Administrator jika instalasi per-user sudah mencukupi.
- Memiliki konfigurasi upgrade yang konsisten untuk versi berikutnya.

Buat file konfigurasi installer, misalnya `JackPDF.iss`, dan sesuaikan seluruh path dengan struktur repository yang benar.

Contoh kerangka Inno Setup (wajib disesuaikan setelah audit):

```ini
#define MyAppName "JackPDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "JackPDF"
#define MyAppExeName "JackPDF.exe"

[Setup]
AppId={{A7C54C81-4D9A-4E8F-9B12-8A1C5D7F9012}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\JackPDF
DefaultGroupName=JackPDF
UninstallDisplayIcon={app}\JackPDF.exe
OutputDir=installer
OutputBaseFilename=JackPDF_Setup
SetupIconFile=assets\icons\jackpdf.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\JackPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\JackPDF"; Filename: "{app}\JackPDF.exe"
Name: "{autodesktop}\JackPDF"; Filename: "{app}\JackPDF.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut Desktop"; GroupDescription: "Shortcut tambahan:"

[Run]
Filename: "{app}\JackPDF.exe"; Description: "Jalankan JackPDF"; Flags: postinstall nowait skipifsilent
```

Catatan:
- Jangan menggunakan `AppId` contoh sebagai identitas final tanpa memastikan belum dipakai aplikasi lain.
- Pastikan format `AppId` valid.
- Pastikan `SetupIconFile` mengarah ke file yang benar.
- Pertimbangkan instalasi per-user agar tidak selalu meminta elevasi Administrator.
- Uji instalasi, launch, upgrade, dan uninstall.

## 11. Tahap H — Keamanan dan kualitas rilis

- Jangan memasukkan `.env`, password, token, credential, atau file rahasia ke bundle.
- Jangan menyimpan data pengguna di folder instalasi Program Files.
- Jangan menjalankan installer atau aplikasi dengan hak Administrator tanpa kebutuhan.
- Pastikan file output tidak tertimpa diam-diam.
- Pertimbangkan code signing jika aplikasi akan didistribusikan secara luas; jangan mengklaim signed jika belum ditandatangani.
- Dokumentasikan bahwa Windows SmartScreen dapat menampilkan peringatan untuk executable yang belum memiliki reputasi atau tanda tangan digital.
- Jangan menonaktifkan antivirus atau menyarankan pengguna mengabaikan peringatan keamanan.

## 12. Struktur output yang diharapkan

Sesuaikan nama file dengan repository, tetapi hasil akhir minimal:

```text
JackPDF/
├── source files...
├── assets/
├── requirements.txt
├── JackPDF.spec
├── JackPDF.iss
├── build.bat
├── build/
├── dist/
│   └── JackPDF/
│       ├── JackPDF.exe
│       └── _internal/
└── installer/
    └── JackPDF_Setup.exe
```

Jangan menyimpan hasil build di dalam source package yang nantinya ikut dibundel kembali.

## 13. Kriteria keberhasilan

Pekerjaan dianggap selesai jika:

- [ ] Source project tetap dapat dijalankan melalui virtual environment.
- [ ] `JackPDF.spec` tersedia dan dapat digunakan untuk build berulang.
- [ ] Build `onedir` berhasil.
- [ ] `JackPDF.exe` dapat dijalankan.
- [ ] Ikon dan seluruh resource tampil.
- [ ] Semua fitur PDF yang sudah ada lolos smoke test.
- [ ] Tidak ada dependency runtime yang hilang.
- [ ] Installer `JackPDF_Setup.exe` berhasil dibuat.
- [ ] Installer dapat memasang aplikasi dan membuat shortcut.
- [ ] Aplikasi dapat dijalankan setelah instalasi.
- [ ] Uninstaller dapat menghapus aplikasi tanpa menghapus dokumen pengguna.
- [ ] Pengujian pada lingkungan Windows tanpa Python dilakukan jika tersedia dan hasilnya dicatat.

## 14. Format laporan akhir coding agent

Setelah implementasi, berikan laporan:
1. Struktur project dan entry point yang ditemukan.
2. Dependency dan resource yang dimasukkan.
3. File yang dibuat atau diubah.
4. Perintah build yang berhasil digunakan.
5. Lokasi hasil `JackPDF.exe`.
6. Lokasi hasil `JackPDF_Setup.exe` jika berhasil dibuat.
7. Hasil pengujian per fitur.
8. Error atau batasan yang masih ada.
9. Langkah menjalankan build berikutnya.

**Jangan mengklaim build atau testing berhasil jika belum benar-benar dijalankan.** Jika Inno Setup belum terpasang atau environment tidak mendukung pembuatan installer, siapkan file `.iss` dan jelaskan langkah yang masih perlu dilakukan pengguna.

---

# PROMPT EKSEKUSI UNTUK AI CODING AGENT

Saya ingin kamu melakukan packaging aplikasi JackPDF yang sudah selesai dikembangkan menjadi aplikasi Windows `.exe` dan menyiapkan installer `JackPDF_Setup.exe`.

Gunakan spesifikasi lengkap pada dokumen ini. Mulailah dengan mengaudit repository aktual. Temukan entry point, virtual environment, ikon `.ico`, assets, dependency, dan seluruh resource yang digunakan. Jangan mengasumsikan nama file atau struktur folder sebelum memeriksanya.

Prioritaskan build PyInstaller mode `onedir` menggunakan `JackPDF.spec`. Pastikan resource path, plugin PySide6, dependency PyMuPDF, dan seluruh modul runtime terkemas dengan benar. Buat script build otomatis Windows dan konfigurasi Inno Setup yang sesuai dengan repository aktual.

Jangan mengubah fitur Merge, Split, Compress, Convert to PNG, atau Crop yang sudah berjalan kecuali ada perbaikan teknis yang benar-benar diperlukan untuk kompatibilitas packaging. Jangan menghapus atau menimpa source code maupun data pengguna.

Setelah build, uji aplikasi hasil packaging dan buat installer jika memungkinkan. Laporkan file yang dibuat, perintah yang dijalankan, hasil pengujian, lokasi output yang benar-benar tersedia, serta masalah yang belum terselesaikan. Kerjakan langsung pada repository; jangan hanya memberikan contoh kode atau instruksi tanpa implementasi.
