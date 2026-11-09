# JackPDF

> **Your everyday PDF toolkit — Your PDF. Your Control.**

Aplikasi desktop Windows modern, cepat, dan elegan untuk pengelolaan dokumen PDF dan foto secara lokal tanpa perlu koneksi internet atau mengunggah data ke server luar. Dibuat menggunakan Python 3.11, PySide6 (Qt for Python), PyMuPDF, Pillow, dan model AI lokal ONNX Runtime.

---

## Fitur Utama

JackPDF menyediakan 7 alat utama yang siap pakai:

1. **Merge PDF**
   - Menggabungkan beberapa berkas PDF menjadi satu dokumen utuh.
   - Dilengkapi *drag-and-drop* pengurutan baris langsung pada tabel, tombol Naik/Turun, dan sorting otomatis (nama, ukuran, halaman).
   - Pratinjau dokumen interaktif dengan navigasi halaman.

2. **Split PDF**
   - Memisahkan dokumen PDF berdasarkan rentang halaman (misal: `1-3, 5, 8-10`) atau mengekstrak setiap halaman menjadi file individual.
   - Pratinjau visual halaman dokumen sebelum proses pemisahan.

3. **Compress PDF**
   - Mengurangi ukuran file PDF dengan pilihan preset: Ekstrem (kualitas dasar), Rekomendasi (seimbang), atau Ringan (kualitas tinggi).
   - Menampilkan metrik perbandingan ukuran sebelum vs sesudah serta persentase penghematan.

4. **Convert to PNG**
   - Mengekspor halaman PDF menjadi berkas gambar PNG beresolusi tinggi (DPI dapat dikonfigurasi).
   - Mendukung pilihan konversi seluruh halaman atau rentang halaman tertentu.

5. **Crop PDF**
   - Memotong area margin halaman dokumen PDF melalui kanvas pratinjau interaktif.
   - Mendukung pemotongan per halaman atau diterapkan ke seluruh halaman dokumen.

6. **Image to PDF (Convert Images to PDF)**
   - Menggabungkan berbagai format gambar (JPG, JPEG, PNG, WEBP, BMP, TIFF) menjadi satu dokumen PDF rapi.
   - Pilihan ukuran halaman fleksibel: **A4**, **Letter**, atau **Ukuran Asli Gambar**.
   - Pilihan orientasi: Otomatis, Portrait, atau Landscape.
   - Pengaturan margin halaman: Tanpa Margin, Kecil (5 mm), atau Standar (12 mm).

7. **Background Changer**
   - Menghapus latar belakang foto secara otomatis menggunakan model AI lokal (`rembg` / ONNX Runtime) tanpa mengirim data ke internet (100% pemrosesan lokal).
   - Menyediakan **5 warna latar belakang formal terstandarisasi**:
     - **Merah** (`#D9001B`) — Pas foto formal tahun kelahiran ganjil.
     - **Biru** (`#0056A6`) — Pas foto formal tahun kelahiran genap.
     - **Putih** (`#FFFFFF`) — Dokumen visa, paspor, kedutaan.
     - **Kuning** (`#FFD700`) — Kebutuhan administrasi khusus.
     - **Hijau** (`#00843D`) — Kebutuhan dokumen instansi tertentu.
   - Dua mode penggunaan:
     - **Foto Formal / Pas Foto**: Pemotongan rasio pas foto otomatis (**2×3 cm**, **3×4 cm**, **4×6 cm** pada 300 DPI, atau **Asli**).
     - **Foto Bebas**: Untuk foto non-formal atau portrait bebas.
   - Inferensi AI efisien (dijalankan satu kali untuk ekstraksi mask; penggantian warna dan crop dilakukan instan di memori).
   - Pratinjau pembanding *Before/After* (Foto Asli vs Hasil AI).
   - Ekspor berkualitas tinggi ke format **JPG** (quality 95) atau **PNG**.

---

## Privasi & Keamanan

- **100% Pemrosesan Lokal**: Semua dokumen dan foto diproses langsung di perangkat Anda.
- **Tidak Memerlukan Akun**: Langsung pakai tanpa registrasi atau login.
- **Tanpa Pengunggahan Cloud**: Tidak ada data yang dikirim ke server luar atau API pihak ketiga.

---

## Persyaratan Sistem

- **Sistem Operasi**: Windows 10 atau Windows 11 (64-bit)
- **Python**: Versi 3.11.x (direkomendasikan 3.11.9 64-bit)

---

## Panduan Instalasi & Menjalankan (Development)

1. **Buka folder project**:
   ```powershell
   cd E:\proyek\JackPDF
   ```

2. **Buat dan aktifkan Virtual Environment**:
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

3. **Pasang Dependensi**:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Jalankan Aplikasi**:
   ```powershell
   python main.py
   ```

---

## Menjalankan Pengujian (Testing)

JackPDF dilengkapi pengujian otomatis unit test dan UI test menyeluruh menggunakan `pytest`:

```powershell
.\.venv\Scripts\pytest
```

---

## Build Executable & Installer

Proyek ini telah dikonfigurasi untuk pembuatan file executable mandiri (PyInstaller mode `onedir`) dan installer Windows (Inno Setup):

1. **Jalankan script build otomatis**:
   ```powershell
   .\build.bat
   ```
   Script ini akan:
   - Mengumpulkan seluruh aset (ikon, stylesheet, model AI ONNX).
   - Membangun executable mandiri di direktori `dist\JackPDF\JackPDF.exe`.
   - Menghasilkan installer `installer\JackPDF_Setup.exe` jika Inno Setup (`ISCC.exe`) terpasang.

2. **Atau compile installer secara manual via Inno Setup**:
   Buka file [`JackPDF.iss`](JackPDF.iss) di Inno Setup Compiler dan klik **Compile**.

---

## Lisensi

Dikembangkan untuk kebutuhan manajemen dokumen dan produktivitas harian yang aman, cepat, dan berorientasi privasi.
