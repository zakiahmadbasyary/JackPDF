# Prompt Pengembangan Fitur: Convert Images to PDF -- JackPDF

## 1. Konteks Proyek

Saya sedang mengembangkan **JackPDF**, aplikasi desktop Windows untuk
pengelolaan PDF menggunakan Python 3.11.9 (64-bit), PySide6, PyMuPDF,
pypdf, dan Pillow. Aplikasi sudah memiliki fitur Merge PDF, Split PDF,
Compress PDF, Convert PDF to PNG, dan Crop PDF. Aplikasi dikemas
menggunakan PyInstaller mode `onedir` dan Inno Setup.

Tagline: **Your PDF. Your Control.**

## 2. Tujuan Fitur

Tambahkan fitur **Convert Images to PDF** yang memungkinkan pengguna
memilih satu atau beberapa gambar sekaligus, mengatur urutannya, lalu
menggabungkannya menjadi satu dokumen PDF. Setiap gambar menjadi satu
halaman PDF.

Contoh: pengguna memilih `foto_1.jpg`, `foto_2.png`, dan `scan_3.jpeg`.
Hasilnya adalah satu PDF dengan tiga halaman sesuai urutan gambar yang
ditentukan.

## 3. Format Gambar

Dukung JPG, JPEG, PNG, BMP, TIFF/TIF, dan WEBP. Validasi setiap file
sebelum konversi. Jika file rusak atau tidak didukung, tampilkan nama
file dan alasan kegagalannya. Jangan mengubah atau menghapus file
sumber.

## 4. UI/UX

Sebelum coding, pelajari struktur project, halaman fitur yang sudah ada,
komponen UI, stylesheet, navigasi, helper, dan pola service. Ikuti
desain JackPDF yang sudah ada; jangan melakukan redesign seluruh
aplikasi.

Buat halaman dengan: - Judul: **Convert Images to PDF** - Deskripsi:
`Combine multiple images into a single PDF document.` - Tombol **Add
Images** dengan file dialog yang mendukung multi-selection. - Tombol
**Add Folder** sebagai fitur opsional. - Drag and drop file jika dapat
diterapkan konsisten dengan arsitektur aplikasi. - Daftar gambar
terpilih yang menampilkan nomor urut, thumbnail, nama file, resolusi
(lebar × tinggi), dan tombol hapus. - Kontrol **Move Up**, **Move
Down**, **Remove Selected**, dan **Clear All**. - Urutan dalam daftar
harus sama dengan urutan halaman PDF. - Cegah duplikasi berdasarkan path
file, tetapi jangan menghapus daftar lama ketika pengguna menambahkan
gambar baru.

### Pengaturan output

Sediakan: - Nama file default: `Converted_Images.pdf`. - Tombol
**Browse** untuk memilih lokasi penyimpanan. - Pilihan ukuran
halaman: 1. **Fit to Image** (default): ukuran halaman mengikuti dimensi
dan orientasi masing-masing gambar. 2. **A4 Portrait**. 3. **A4
Landscape**. - Margin sederhana (opsional).

Pada mode A4, gambar harus menyesuaikan area halaman tanpa mengubah
rasio aspek atau terdistorsi. Pada Fit to Image, setiap halaman
mengikuti ukuran gambar masing-masing.

Tombol **Convert to PDF** harus nonaktif jika belum ada gambar. Saat
proses berlangsung, tampilkan status/progress dan cegah klik ganda.
Setelah berhasil, tampilkan notifikasi
`Images successfully converted to PDF.` serta aksi **Open PDF** dan
**Open Folder** jika sesuai pola aplikasi.

## 5. Logika Konversi

-   Proses gambar sesuai urutan yang terlihat di daftar.
-   Pastikan gambar dapat dibuka dan didekode sebelum diproses.
-   Pertahankan rasio aspek dan orientasi gambar.
-   Terapkan metadata EXIF orientation jika tersedia.
-   Tangani transparansi PNG/WEBP dengan background putih.
-   Hindari penurunan kualitas yang tidak perlu.
-   Perhatikan penggunaan memori untuk gambar beresolusi besar atau
    jumlah gambar banyak.
-   Satu gambar valid menghasilkan tepat satu halaman PDF.
-   Pastikan hasil dapat dibuka oleh pembaca PDF umum.
-   Jangan menimpa file yang sudah ada tanpa konfirmasi.

### Rekomendasi teknis

Gunakan Pillow untuk membaca, memvalidasi, mengolah orientasi, dan
menyiapkan gambar. Gunakan PyMuPDF atau library PDF yang sudah digunakan
project untuk membuat PDF. Utamakan library yang sudah tersedia; jangan
menambah dependency tanpa alasan.

Jika diperlukan file perantara, gunakan temporary file yang dikelola
dengan aman dan hapus setelah proses selesai, termasuk saat terjadi
error. Jangan menyimpan file perantara secara permanen di folder
aplikasi. Tutup resource/file handle dengan benar.

## 6. Validasi dan Error Handling

Tangani setidaknya: - Belum ada gambar: tombol Convert nonaktif. -
Format tidak didukung. - Gambar rusak atau tidak dapat dibaca. - Lokasi
output belum dipilih. - Nama file kosong atau tidak valid. - File output
sudah ada: minta konfirmasi. - Folder tujuan tidak dapat ditulis. -
Konversi gagal atau dibatalkan.

Jangan diam-diam melewati gambar yang gagal. Jika sebagian gambar tidak
valid, tampilkan daftar file yang gagal dan minta keputusan pengguna
untuk membatalkan atau melanjutkan hanya dengan file valid. Default yang
disarankan adalah membatalkan sampai pengguna memilih.

Jangan tampilkan traceback mentah kepada pengguna. Gunakan pesan yang
mudah dipahami dan logging internal jika tersedia.

## 7. Arsitektur dan Struktur Kode

Sebelum implementasi: 1. Periksa struktur folder dan konvensi penamaan.
2. Pelajari implementasi Merge, Split, Compress, Convert PDF to PNG, dan
Crop. 3. Identifikasi pola navigasi, komponen, dialog, notifikasi, ikon,
tema, dan service. 4. Gunakan kembali komponen yang sudah ada. 5.
Pisahkan UI dan proses konversi sesuai pola arsitektur project.

Nama konseptual yang dapat digunakan jika cocok dengan struktur
project: - `convert_images_to_pdf_page.py` -
`convert_images_to_pdf_service.py`

Jangan memaksakan nama tersebut jika project memiliki konvensi lain.
Proses konversi tidak boleh membuat UI freeze. Gunakan QThread,
QRunnable, atau pola worker yang sudah digunakan. Perbarui UI melalui
signal-slot PySide6, bukan langsung dari background thread.

## 8. Integrasi JackPDF

-   Tambahkan kartu/menu fitur baru di Home.
-   Tambahkan ikon yang konsisten dengan identitas visual JackPDF.
-   Integrasikan navigasi menuju halaman fitur.
-   Pastikan tombol Back/Home bekerja.
-   Pertahankan warna, tipografi, spacing, radius, border, hover state,
    dan gaya tombol.
-   Jangan mengubah fitur lama yang tidak berkaitan.
-   Jika ikon khusus belum tersedia, gunakan ikon sementara yang sesuai
    dan mudah diganti.

## 9. Kompatibilitas Packaging

Pastikan fitur: - Berjalan dari source code dalam `.venv`. - Berjalan
pada hasil build PyInstaller `onedir`. - Tidak bergantung pada path
absolut komputer developer. - Tidak menyimpan output ke folder internal
aplikasi. - Tidak membutuhkan instalasi Python pada komputer pengguna. -
Mengikuti mekanisme resource resolver `resource_utils.py` yang sudah
ada. - Tidak merusak `JackPDF.spec`, `build.bat`, dan `JackPDF.iss`.

Jika ada perubahan data/dependency yang diperlukan untuk packaging,
sesuaikan konfigurasi seperlunya dan jelaskan alasannya.

## 10. Pengujian

Tambahkan dan jalankan pengujian minimal untuk: 1. Satu gambar JPG. 2.
Beberapa gambar JPG. 3. Campuran JPG dan PNG. 4. BMP, TIFF, dan WEBP. 5.
Urutan halaman sesuai daftar. 6. Move Up dan Move Down. 7. Remove
Selected dan Clear All. 8. Orientasi portrait dan landscape. 9. Metadata
EXIF orientation. 10. Gambar transparan. 11. Gambar rusak/tidak valid.
12. Fit to Image, A4 Portrait, dan A4 Landscape. 13. Konfirmasi
overwrite. 14. Banyak gambar tanpa UI freeze. 15. PDF dapat dibuka dan
jumlah halaman sesuai. 16. Fitur berjalan pada hasil build PyInstaller.

Gunakan temporary directory untuk test. Jangan mengubah atau menghapus
file pengguna.

## 11. Batasan Perubahan

-   Jangan melakukan redesign seluruh aplikasi.
-   Jangan merusak fitur Merge, Split, Compress, Convert PDF to PNG, dan
    Crop.
-   Jangan menghapus konfigurasi yang sudah berfungsi.
-   Jangan menambah dependency jika library yang tersedia cukup.
-   Jangan mengubah identitas visual JackPDF.
-   Jangan mengubah packaging yang sudah stabil kecuali diperlukan.

## 12. Acceptance Criteria

Fitur dinyatakan selesai jika: - Pengguna dapat memilih banyak gambar
sekaligus dan menambahkan gambar secara bertahap. - Thumbnail, nama,
resolusi, dan urutan gambar terlihat. - Pengguna dapat mengubah urutan,
menghapus item, dan mengosongkan daftar. - Pengguna dapat menentukan
nama serta lokasi output. - Pengguna dapat memilih Fit to Image, A4
Portrait, atau A4 Landscape. - Setiap gambar valid menjadi satu halaman
PDF. - Rasio aspek dan orientasi dipertahankan. - File sumber tidak
berubah. - UI tetap responsif. - Error ditangani dengan jelas. - Fitur
terintegrasi dengan navigasi dan desain JackPDF. - Pengujian relevan
lulus dan fitur bekerja pada hasil packaging Windows.

## 13. Instruksi untuk AI Coding Agent

Kerjakan secara bertahap:

**Tahap 1 -- Analisis** - Periksa struktur project dan pola implementasi
fitur lama. - Identifikasi komponen yang dapat digunakan kembali. -
Laporkan file yang akan dibuat/diubah sebelum implementasi.

**Tahap 2 -- Implementasi** - Buat service konversi gambar ke PDF. -
Buat halaman UI mengikuti desain JackPDF. - Integrasikan navigasi dan
Home. - Terapkan validasi, error handling, dan background processing.

**Tahap 3 -- Pengujian** - Jalankan seluruh test yang sudah ada. -
Tambahkan dan jalankan test fitur baru. - Pastikan tidak ada regresi
pada fitur lama. - Uji dari source code.

**Tahap 4 -- Packaging** - Periksa kompatibilitas PyInstaller. - Build
ulang dan uji fitur pada aplikasi hasil build. - Perbarui installer
hanya jika diperlukan.

**Tahap 5 -- Laporan** Laporkan file yang dibuat/diubah, cara kerja
fitur, library yang digunakan, hasil pengujian, status packaging, serta
keterbatasan yang masih ada.

**Penting:** Jangan hanya membuat UI atau tombol dummy. Implementasikan
seluruh alur sampai file PDF benar-benar berhasil dibuat dan dapat
dibuka. Pertahankan seluruh fitur JackPDF yang sudah berjalan.
