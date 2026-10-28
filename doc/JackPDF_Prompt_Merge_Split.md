# Prompt Implementasi Fitur Merge PDF dan Split PDF --- JackPDF

Dokumen ini berisi prompt yang dapat diberikan kepada AI coding agent
untuk mengimplementasikan fitur **Merge PDF** dan **Split PDF** pada
proyek JackPDF yang sudah memiliki setup Python dan UI PySide6.

## 1. Konteks Proyek

Nama aplikasi: **JackPDF**

Jenis aplikasi: Windows desktop, pemrosesan PDF secara lokal.

Teknologi: - Python 3.12 - PySide6 untuk UI - PyMuPDF dan/atau pypdf
untuk operasi PDF - pytest untuk pengujian

Desain UI: - Modern, sederhana, dominan putih/abu-abu muda dengan aksen
biru. - Font Segoe UI. - Sudut komponen sekitar 8--12 px. - Tooltip
untuk tombol, ikon, dan input yang membutuhkan penjelasan. - Konsisten
dengan desain yang sudah ada di proyek JackPDF. - Jangan mengubah
identitas visual atau membangun ulang aplikasi dari nol.

Fitur yang dikerjakan dalam prompt ini hanya: 1. Merge PDF. 2. Split
PDF.

Fitur lain seperti compress, convert to PNG, crop, dan convert to Word
tidak termasuk dalam lingkup implementasi ini.

## 2. Instruksi Utama untuk AI Coding Agent

Salin prompt berikut dan berikan kepada AI coding agent yang memiliki
akses ke folder proyek JackPDF.

------------------------------------------------------------------------

### PROMPT

Kamu bertindak sebagai **Python Desktop Application Engineer** yang
berpengalaman membangun aplikasi Windows dengan Python, PySide6,
PyMuPDF, dan pypdf.

Saya memiliki proyek desktop bernama **JackPDF**. Implementasikan fitur
**Merge PDF** dan **Split PDF** ke dalam proyek yang sudah ada.

Sebelum menulis atau mengubah kode:

1.  Periksa struktur folder dan seluruh file relevan yang sudah ada.
2.  Baca `main.py`, `app/main_window.py`, `app/ui/home_page.py`,
    stylesheet, dan file konfigurasi yang tersedia.
3.  Ikuti struktur, pola penamaan, komponen UI, dan gaya kode yang sudah
    digunakan.
4.  Jangan menimpa atau menghapus kode yang sudah berfungsi.
5.  Jika struktur aktual berbeda dari dokumentasi, utamakan struktur
    aktual proyek dan integrasikan perubahan dengan hati-hati.
6.  Buat rencana perubahan singkat, lalu implementasikan langsung
    seluruh file yang diperlukan. Jangan hanya memberikan contoh atau
    potongan kode.
7.  Jangan membuat backend web, API, database, login, atau
    ketergantungan cloud. Seluruh proses PDF harus dilakukan secara
    lokal.

### A. Fitur Merge PDF

Buat halaman kerja Merge PDF dengan persyaratan berikut.

#### UI dan interaksi

-   Pengguna dapat memilih beberapa file PDF melalui dialog file
    Windows.
-   Sediakan area drag-and-drop untuk menambahkan file PDF.
-   Tampilkan daftar file yang sudah ditambahkan.
-   Informasi setiap file minimal berisi nama file dan ukuran file;
    jumlah halaman boleh ditambahkan setelah metadata berhasil dibaca.
-   Sediakan tombol:
    -   `Tambah PDF`
    -   `Hapus Pilihan`
    -   `Hapus Semua`
    -   `Naikkan Urutan`
    -   `Turunkan Urutan`
    -   `Gabungkan PDF`
-   Pengguna dapat memilih satu file dalam daftar dan mengubah
    urutannya.
-   Urutan yang terlihat pada daftar harus menjadi urutan halaman dalam
    dokumen hasil.
-   Cegah file yang sama ditambahkan berulang kali tanpa sengaja; bila
    duplikasi memang diizinkan, jelaskan perilakunya secara konsisten.
-   Tombol proses dinonaktifkan jika belum ada minimal dua file valid.
-   Tampilkan lokasi output atau dialog Save As sebelum menyimpan hasil.
-   Default nama hasil: `JackPDF_Merged.pdf`.
-   Jangan pernah menimpa file input secara diam-diam. Jika lokasi
    output sama dengan salah satu file input, tolak operasi dan
    tampilkan pesan yang jelas.
-   Setelah berhasil, tampilkan notifikasi dan sediakan tindakan untuk
    membuka folder output jika mudah diintegrasikan.

#### Logika pemrosesan

-   Implementasikan logika di `app/services/merge_service.py`.
-   UI tidak boleh memuat logika manipulasi PDF secara langsung.
-   Gunakan PyMuPDF atau pypdf secara konsisten, pilih pustaka yang
    paling sesuai dengan kode proyek yang sudah ada.
-   Pastikan semua dokumen input ditutup dengan benar meskipun terjadi
    error.
-   Validasi bahwa file ada, berekstensi `.pdf`, dapat dibuka, dan
    memiliki halaman.
-   Tangani PDF terenkripsi yang tidak dapat dibuka tanpa password
    dengan pesan yang dapat dipahami pengguna.
-   Tangani file rusak, file tidak valid, izin akses ditolak, dan
    kegagalan menulis output.
-   Pertahankan urutan dokumen dan urutan halaman dari masing-masing
    file.
-   Jangan merasterisasi halaman hanya untuk menggabungkannya;
    pertahankan konten PDF semaksimal mungkin.
-   Jika proses gagal, hapus file output parsial yang dibuat oleh
    operasi tersebut bila aman dilakukan.
-   Jangan memodifikasi atau menghapus file sumber.

### B. Fitur Split PDF

Buat halaman kerja Split PDF dengan persyaratan berikut.

#### UI dan interaksi

-   Pengguna memilih satu file PDF melalui dialog atau drag-and-drop.
-   Tampilkan nama file, ukuran, dan jumlah halaman setelah file
    berhasil dibaca.
-   Sediakan pilihan mode pemisahan:
    1.  **Rentang halaman** --- contoh `1-3, 5, 8-10`.
    2.  **Satu file per halaman** --- setiap halaman menjadi file PDF
        terpisah.
    3.  **Rentang berukuran tetap** --- pengguna menentukan jumlah
        halaman per file, misalnya 3 halaman per file.
-   Pengguna memilih folder output.
-   Berikan contoh format input rentang halaman di dekat kolom input.
-   Nomor halaman yang digunakan UI harus dimulai dari 1, bukan indeks
    internal 0.
-   Validasi rentang halaman sebelum proses dijalankan.
-   Tampilkan jumlah halaman yang akan diekspor atau jumlah file yang
    akan dibuat bila bisa dihitung.
-   Sediakan tombol `Split PDF` dan `Reset`.
-   Tombol proses dinonaktifkan bila input belum valid.
-   Tampilkan progres atau status proses. Jika progres rinci sulit
    diterapkan, tampilkan status seperti `Memproses...` dan `Selesai`.
-   Setelah sukses, tampilkan lokasi folder output dan jumlah file yang
    dibuat.

#### Logika pemrosesan

-   Implementasikan logika di `app/services/split_service.py`.
-   Pisahkan UI dari service pemrosesan.
-   Pastikan indeks halaman yang diproses benar: UI 1-based, API PDF
    biasanya 0-based.
-   Untuk mode rentang halaman, parsing harus mendukung format seperti:
    -   `1-3`
    -   `1,3,5`
    -   `1-3, 5, 8-10`
-   Tolak input seperti:
    -   `0`
    -   rentang terbalik seperti `5-2`
    -   halaman melebihi jumlah halaman PDF
    -   format yang tidak valid seperti `1--3`, `a-b`, atau koma tanpa
        angka
    -   rentang kosong
-   Tentukan dengan jelas apakah halaman duplikat dari input seperti
    `1,1,2` ditolak atau dihilangkan. Pilih satu perilaku yang konsisten
    dan beri pesan validasi.
-   Mode satu file per halaman menghasilkan nama file yang berurutan,
    misalnya `dokumen_page_001.pdf`.
-   Mode rentang berukuran tetap menghasilkan nama file seperti
    `dokumen_part_001.pdf`.
-   Mode rentang halaman menghasilkan satu file berisi halaman yang
    dipilih sesuai urutan input.
-   Jika hasil terdiri dari beberapa file, hindari menimpa file yang
    sudah ada. Gunakan dialog konfirmasi atau nama alternatif yang aman.
-   Tangani PDF kosong, rusak, terenkripsi, dan kegagalan akses.
-   Pastikan dokumen ditutup dan file output parsial ditangani dengan
    aman jika proses gagal.
-   Jangan memodifikasi atau menghapus file sumber.

### C. Navigasi dan integrasi UI

-   Hubungkan kartu Merge PDF dan Split PDF pada Home ke halaman fitur
    yang benar.
-   Hubungkan item Merge PDF dan Split PDF di sidebar ke halaman yang
    sama.
-   Gunakan `QStackedWidget` atau mekanisme navigasi yang sudah ada
    dalam proyek.
-   Jangan membuat dua instance halaman berbeda untuk satu fitur jika
    tidak diperlukan.
-   Berikan judul halaman, deskripsi singkat, tombol kembali atau
    navigasi yang konsisten.
-   Terapkan tooltip menggunakan `setToolTip()` untuk semua tombol dan
    input yang memerlukan penjelasan.
-   Pastikan tooltip singkat, dalam Bahasa Indonesia, dan sesuai
    tindakan.
-   Gunakan `QFileDialog` untuk memilih file/folder dan menyimpan
    output.
-   Gunakan `QMessageBox` untuk validasi, konfirmasi, error, dan
    keberhasilan.
-   Pertahankan desain minimalis dan konsisten dengan stylesheet
    JackPDF.

### D. Responsivitas dan keamanan file

-   Operasi PDF yang berpotensi lama tidak boleh membekukan UI.
-   Jika sesuai dengan arsitektur proyek, jalankan operasi melalui
    worker berbasis `QThread` atau `QThreadPool`.
-   Perbarui progres melalui signal Qt dengan aman; jangan mengubah
    widget langsung dari thread pekerja.
-   Nonaktifkan tombol proses saat pekerjaan sedang berlangsung untuk
    mencegah eksekusi ganda.
-   Validasi ekstensi file saja tidak cukup; coba buka dokumen
    menggunakan pustaka PDF dan tangani exception.
-   Hindari logging isi dokumen atau data sensitif.
-   Jangan menjalankan file eksternal atau perintah shell dari nama file
    pengguna.
-   Pastikan pesan error tidak menampilkan traceback teknis kepada
    pengguna umum; detail teknis boleh dicatat secara lokal untuk
    debugging tanpa membocorkan isi dokumen.

### E. Pengujian

Tambahkan unit test menggunakan pytest. Gunakan PDF fixture kecil yang
dibuat saat pengujian agar tidak membutuhkan dokumen pribadi.

Minimal uji kasus berikut:

**Merge** - Menggabungkan dua PDF menjadi satu. - Memastikan jumlah
halaman hasil benar. - Memastikan urutan halaman hasil sesuai urutan
input. - Menolak kurang dari dua input jika aturan UI mensyaratkannya. -
Menolak file tidak valid. - Menangani file output yang sama dengan file
input. - Memastikan dokumen dapat dibuka setelah proses selesai.

**Split** - Mengekspor rentang `1-3`. - Mengekspor halaman `1,3,5`. -
Menghasilkan satu file per halaman dengan jumlah file benar. - Membagi
dokumen ke ukuran grup tetap dengan benar. - Menolak halaman 0, rentang
terbalik, format tidak valid, dan halaman di luar batas. - Memastikan
halaman hasil sama dengan halaman sumber yang diminta. - Menangani
output yang sudah ada tanpa menimpanya diam-diam.

Jalankan seluruh test yang relevan dan perbaiki kegagalan yang
disebabkan oleh implementasi.

### F. Kriteria Selesai

Pekerjaan dianggap selesai apabila:

1.  Halaman Merge PDF dan Split PDF terhubung dari Home dan sidebar.
2.  Seluruh alur pilih file, validasi, proses, dan simpan hasil
    berjalan.
3.  Urutan halaman dan penomoran halaman benar.
4.  Tooltip tampil dan informatif.
5.  Error umum ditangani dengan pesan yang jelas.
6.  UI tidak membeku saat operasi PDF berjalan.
7.  Unit test utama berhasil.
8.  Tidak ada fitur lain yang rusak.
9.  Tidak ada file proyek penting yang dihapus atau ditimpa tanpa
    alasan.
10. Berikan ringkasan file yang dibuat/diubah, cara menjalankan
    aplikasi, cara menjalankan test, dan keterbatasan yang masih ada.

Implementasikan fitur pada proyek yang tersedia. Jangan berhenti setelah
membuat rencana. Jika ada ketidakpastian kecil, pilih solusi aman yang
konsisten dengan arsitektur proyek dan jelaskan keputusan tersebut pada
ringkasan akhir.

------------------------------------------------------------------------

## 3. Rekomendasi struktur file setelah fitur dibuat

Struktur ini adalah target, bukan alasan untuk memindahkan file yang
sudah ada jika tidak diperlukan.

``` text
JackPDF/
├── main.py
├── requirements.txt
├── app/
│   ├── main_window.py
│   ├── ui/
│   │   ├── home_page.py
│   │   └── pages/
│   │       ├── merge_page.py
│   │       └── split_page.py
│   ├── services/
│   │   ├── merge_service.py
│   │   └── split_service.py
│   ├── workers/
│   │   └── pdf_worker.py
│   └── utils/
│       ├── file_utils.py
│       └── validators.py
└── tests/
    ├── test_merge.py
    └── test_split.py
```

## 4. Dependensi

Jika belum terpasang, gunakan virtual environment proyek JackPDF lalu
jalankan:

``` powershell
pip install pyside6 pymupdf pypdf pytest
```

Perbarui `requirements.txt` sesuai dependensi yang benar-benar
digunakan. Jangan menambah pustaka yang tidak diperlukan.

## 5. Cara verifikasi manual

Setelah implementasi:

1.  Jalankan `python main.py`.
2.  Buka Merge PDF, pilih dua atau lebih PDF, ubah urutannya, lalu
    gabungkan.
3.  Periksa file hasil dan pastikan urutan halaman benar.
4.  Buka Split PDF, pilih PDF multi-halaman.
5.  Coba mode rentang, satu file per halaman, dan rentang berukuran
    tetap.
6.  Coba input tidak valid dan pastikan pesan error dapat dipahami.
7.  Coba simpan ke lokasi yang sudah berisi file bernama sama.
8.  Pastikan aplikasi tetap responsif selama pemrosesan.
9.  Jalankan test dengan:

``` powershell
pytest -q
```

## 6. Catatan Implementasi

-   Gunakan satu pustaka utama untuk setiap operasi jika memungkinkan,
    agar kode lebih sederhana.
-   Perhatikan bahwa PDF dapat memiliki password, tanda tangan digital,
    formulir, anotasi, bookmark, dan metadata. Operasi penyusunan ulang
    halaman dapat memengaruhi sebagian struktur tersebut.
-   Jangan mengklaim semua metadata atau tanda tangan digital selalu
    dipertahankan; dokumentasikan keterbatasan yang ditemukan.
-   Jangan menambahkan fitur Compress, Convert to PNG, Crop, atau
    Convert to Word dalam pekerjaan ini.
-   Pertahankan nama produk **JackPDF** dan desain UI modern sederhana.
