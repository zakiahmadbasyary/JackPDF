# Prompt Pengembangan Fitur: Background Changer -- JackPDF

## 1. Konteks Proyek

Saya sedang mengembangkan **JackPDF**, aplikasi desktop Windows untuk
pengelolaan dokumen dan gambar. Aplikasi dibuat menggunakan:

-   Python 3.11.9 (64-bit)
-   PySide6 untuk antarmuka desktop
-   Pillow untuk pemrosesan gambar
-   PyMuPDF dan pypdf untuk fitur PDF
-   PyInstaller mode `onedir` untuk packaging
-   Inno Setup untuk membuat installer Windows

Fitur yang sudah tersedia: 1. Merge PDF 2. Split PDF 3. Compress PDF 4.
Convert PDF to PNG 5. Crop PDF 6. Convert Images to PDF

Identitas visual JackPDF menggunakan maskot Malaikat Maut bertopi tinggi
dengan mata biru bercahaya, sabit, serta palet navy, biru, dan cyan.
Tagline: **Your PDF. Your Control.**

## 2. Tujuan Fitur

Tambahkan fitur baru bernama **Background Changer**.

Fitur ini memungkinkan pengguna menghapus background asli dari foto
secara otomatis menggunakan model AI, lalu menggantinya dengan salah
satu dari lima warna background yang telah ditentukan.

Fitur harus mendukung dua jenis penggunaan: - **Foto Formal / Pas
Foto:** foto orang untuk dokumen, administrasi, lamaran kerja, dan
kebutuhan formal. - **Foto Bebas:** foto orang dengan berbagai pose atau
komposisi, bukan hanya foto kepala dan bahu.

Pemrosesan harus dapat dilakukan secara lokal/offline setelah model dan
dependensinya tersedia. Jangan mengunggah foto pengguna ke server atau
layanan eksternal.

## 3. Pilihan Warna Background

Sediakan tepat lima pilihan warna. Jangan menambahkan custom color
picker.

Gunakan kode warna awal berikut dan letakkan dalam satu
konfigurasi/konstanta terpusat agar mudah disesuaikan:

  Nama     HEX         Penggunaan
  -------- ----------- ----------------------------------
  Merah    `#D9001B`   Background pas foto formal merah
  Biru     `#0056A6`   Background pas foto formal biru
  Putih    `#FFFFFF`   Background putih
  Kuning   `#FFD700`   Background kuning
  Hijau    `#00843D`   Background hijau

Catatan: - Warna merah dan biru harus terlihat formal, tidak neon atau
terlalu terang. - Tampilkan swatch warna dan nama warna pada UI. - Warna
putih harus tetap terlihat jelas pada panel UI, misalnya menggunakan
border. - Jangan mengklaim bahwa kode warna tersebut berlaku untuk semua
instansi. Pengguna bertanggung jawab memilih warna sesuai ketentuan
dokumen yang dibutuhkan.

## 4. Teknologi yang Direkomendasikan

Pelajari dependency yang sudah tersedia sebelum menambahkan library
baru.

Rekomendasi: - **rembg:** background removal berbasis model AI. - **ONNX
Runtime:** menjalankan model AI secara lokal. - **Pillow:** membaca,
mengolah alpha mask, mengganti background, dan menyimpan gambar. -
**OpenCV (opsional):** membantu proses perbaikan tepi atau pemrosesan
mask jika memang dibutuhkan.

Ketentuan: 1. Utamakan model yang sesuai untuk foto manusia dan
menghasilkan foreground mask yang baik. 2. Evaluasi pilihan model rembg
yang tersedia berdasarkan kualitas hasil, ukuran model, kebutuhan RAM,
dan performa CPU. 3. Jangan mengunduh model setiap kali aplikasi
dijalankan. 4. Model harus tersedia secara lokal setelah proses
instalasi atau pada penggunaan pertama melalui mekanisme yang
transparan. 5. Jika model perlu diunduh saat pertama kali, tampilkan
informasi ukuran unduhan, progress, lokasi penyimpanan, dan pesan error
jika gagal. Jangan mengunduh secara diam-diam. 6. Pastikan lisensi
library dan model sesuai untuk distribusi aplikasi. 7. Jangan
menambahkan dependency yang tidak diperlukan.

## 5. Alur Penggunaan

Alur utama yang diharapkan:

1.  Pengguna membuka halaman **Background Changer**.
2.  Pengguna memilih atau menyeret foto ke area upload.
3.  Aplikasi menampilkan preview foto asli.
4.  Pengguna memilih mode **Foto Formal** atau **Foto Bebas**.
5.  Pengguna menekan tombol **Remove Background**.
6.  Aplikasi menjalankan AI background removal secara lokal.
7.  Setelah mask selesai dibuat, pengguna memilih warna merah, biru,
    putih, kuning, atau hijau.
8.  Preview hasil diperbarui tanpa perlu menjalankan background removal
    lagi.
9.  Pengguna dapat membandingkan foto asli dan hasil.
10. Pengguna menyimpan hasil sebagai JPG atau PNG.

Penting: proses penghapusan background hanya dijalankan ketika
diperlukan. Mengganti warna harus menggunakan alpha mask yang sudah
dibuat, bukan mengulang inferensi AI.

## 6. Rancangan UI/UX

Sebelum membuat UI, pelajari halaman fitur JackPDF yang sudah ada.
Gunakan komponen, stylesheet, pola navigasi, tombol, dialog, notifikasi,
dan tema yang sudah tersedia.

### A. Header

-   Judul: **Background Changer**
-   Deskripsi: `Remove and replace photo backgrounds with ease.`
-   Ikon fitur mengikuti identitas visual JackPDF.
-   Pertahankan sidebar/header dan navigasi yang sudah ada.

### B. Area upload

Sediakan: - Tombol **Upload Photo**. - Area drag and drop jika konsisten
dengan pola aplikasi. - Format input minimal JPG, JPEG, PNG, dan WEBP. -
Tampilkan nama file dan resolusi gambar. - Tombol **Change Photo** atau
**Remove Photo**. - Jangan mengubah file asli.

Batasi ukuran file dan dimensi gambar secara wajar untuk mencegah
penggunaan memori berlebihan. Jika file terlalu besar, berikan pesan
yang jelas dan jangan crash.

### C. Pemilihan mode

Sediakan dua pilihan: - **Foto Formal** - **Foto Bebas**

Mode Foto Formal dapat menampilkan panduan sederhana agar pengguna
mengunggah foto orang dengan posisi yang sesuai untuk pas foto. Jangan
mengubah bentuk tubuh, wajah, pakaian, atau identitas subjek.

Mode Foto Bebas digunakan untuk berbagai pose dan komposisi. Keduanya
menggunakan mesin background removal yang sama kecuali ada alasan teknis
yang jelas untuk membedakannya.

### D. Area preview

Tampilkan: - Preview foto asli. - Preview hasil background removal dan
penggantian warna. - Opsi **Before / After** atau tampilan
berdampingan. - Zoom in/out jika mudah diterapkan. - Indikator loading
saat proses AI berjalan.

Gunakan pola preview yang konsisten dan jangan membuat UI terlalu padat.

### E. Pilihan warna

Tampilkan lima swatch: - Merah `#D9001B` - Biru `#0056A6` - Putih
`#FFFFFF` - Kuning `#FFD700` - Hijau `#00843D`

Ketentuan: - Satu warna aktif pada satu waktu. - Berikan indikator
pilihan yang jelas. - Default warna dapat berupa putih atau merah,
tetapi jangan mengasumsikan warna yang diwajibkan untuk kebutuhan
pengguna. - Saat pengguna memilih warna lain, preview langsung berubah
menggunakan mask yang sama.

### F. Tombol aksi

Sediakan: - **Remove Background** - **Reset** - **Save as JPG** - **Save
as PNG**

Ketentuan: - Remove Background nonaktif jika belum ada foto. - Tombol
simpan nonaktif sebelum hasil tersedia. - Reset mengembalikan preview ke
kondisi awal tanpa menghapus file sumber. - Jangan membuat tombol dummy.

## 7. Logika Background Removal dan Kualitas Hasil

Kualitas pemisahan subjek adalah bagian paling penting dari fitur ini.

Implementasikan: 1. Baca gambar dengan aman dan perhatikan metadata EXIF
orientation. 2. Jalankan model AI untuk menghasilkan foreground/alpha
mask. 3. Pastikan ukuran mask sama dengan dimensi gambar yang diproses.
4. Pertahankan detail rambut, tepi pakaian, dan bagian tubuh. 5. Hindari
halo atau sisa warna background lama pada tepi subjek. 6. Hindari
menghapus bagian tubuh, rambut, atau pakaian. 7. Jangan mengubah wajah,
warna kulit, bentuk tubuh, pakaian, atau karakteristik subjek. 8.
Terapkan alpha compositing dengan benar pada warna background pilihan.
9. Jangan melakukan blur berlebihan yang membuat tepi subjek terlihat
tidak natural. 10. Jika model menghasilkan mask yang buruk atau gagal,
tampilkan error dan jangan menyimpan hasil yang rusak.

Jika dibutuhkan, sediakan pemrosesan mask ringan seperti smoothing atau
edge refinement. Pastikan perbaikan tidak menghilangkan detail halus.
Jangan menerapkan teknik yang terlalu agresif.

### Mode output

-   **PNG:** dapat menyimpan hasil dengan background terpilih. Jika
    suatu saat ingin menyediakan PNG transparan, jadikan opsi terpisah
    dan jangan mengubah perilaku default.
-   **JPG:** selalu gunakan background solid yang dipilih, karena JPG
    tidak mendukung transparansi.

## 8. Ukuran Pas Foto (Pengembangan Terintegrasi)

Sediakan ukuran pas foto sebagai fitur pendukung, dengan prioritas
setelah background replacement dasar berfungsi stabil.

Pilihan ukuran: - 2 × 3 cm - 3 × 4 cm - 4 × 6 cm - Original Size

Ketentuan: 1. Sediakan pilihan ukuran setelah pengguna memilih mode Foto
Formal. 2. Gunakan DPI yang dapat dikonfigurasi, dengan default 300 DPI.
3. Hitung dimensi piksel dari ukuran fisik dan DPI secara benar. 4.
Terapkan crop dengan menjaga proporsi dan posisi subjek. 5. Jangan
melakukan stretch atau distorsi. 6. Berikan preview crop sebelum
menyimpan. 7. Jangan memotong kepala atau bagian penting subjek secara
otomatis tanpa preview/konfirmasi pengguna. 8. Jangan memaksakan ukuran
pas foto pada mode Foto Bebas.

Jika implementasi ukuran pas foto membuat scope terlalu besar,
selesaikan terlebih dahulu background removal, pilihan warna, preview,
dan export. Laporkan ukuran pas foto sebagai tahap lanjutan, bukan
membuat fitur inti tertunda.

## 9. Performa dan Responsivitas

-   Proses inferensi AI tidak boleh membuat UI freeze.
-   Gunakan QThread, QRunnable, atau pola worker yang sudah digunakan
    project.
-   Kirim progress/status melalui signal-slot PySide6.
-   Tampilkan status seperti `Loading model`, `Removing background`, dan
    `Preparing preview`.
-   Cegah proses ganda akibat klik berulang.
-   Tangani pembatalan jika memungkinkan dan aman.
-   Pastikan worker, model session, image object, dan file handle
    dikelola dengan benar.
-   Perhatikan konsumsi RAM, khususnya pada foto beresolusi tinggi.
-   Hindari membuat banyak salinan gambar berukuran besar di memori.
-   Jika model hanya berjalan di CPU, pastikan UI tetap responsif.

## 10. Error Handling dan Validasi

Tangani kondisi berikut: - Belum ada foto. - Format file tidak
didukung. - File rusak atau gagal dibaca. - Resolusi atau ukuran file
terlalu besar. - Model AI belum tersedia. - Model gagal dimuat. -
Dependency ONNX Runtime bermasalah. - Proses background removal gagal. -
Memori tidak mencukupi. - Folder output tidak dapat ditulis. - File
output sudah ada. - Pengguna membatalkan proses.

Gunakan pesan yang ramah dan mudah dipahami. Jangan menampilkan
traceback mentah kepada pengguna. Simpan detail teknis melalui logging
aplikasi jika tersedia.

## 11. Privasi dan Keamanan

-   Foto pengguna diproses secara lokal.
-   Jangan mengunggah foto atau hasil mask ke server.
-   Jangan mengirim foto ke API eksternal.
-   Jangan menyimpan salinan foto pengguna secara permanen di folder
    aplikasi.
-   Bersihkan temporary file setelah proses selesai atau gagal.
-   Jelaskan jika model AI perlu diunduh pada penggunaan pertama; yang
    diunduh adalah model, bukan foto pengguna.
-   Jangan mengubah atau menghapus foto sumber.

## 12. Integrasi ke JackPDF

1.  Tambahkan kartu/menu **Background Changer** di Home.
2.  Tambahkan ikon fitur yang konsisten dengan maskot Malaikat Maut
    JackPDF.
3.  Integrasikan navigasi ke halaman fitur.
4.  Pastikan tombol Back/Home bekerja.
5.  Gunakan warna, tipografi, spacing, radius, border, hover state, dan
    komponen yang konsisten.
6.  Jangan melakukan redesign seluruh aplikasi.
7.  Jangan mengubah fitur lama yang tidak berkaitan.

## 13. Kompatibilitas PyInstaller dan Installer

JackPDF menggunakan PyInstaller mode `onedir` dan Inno Setup.

Pastikan: - Fitur berjalan dari source code di `.venv`. - Fitur berjalan
dari hasil build PyInstaller. - Model AI dan resource ONNX yang
diperlukan ikut tersedia atau dapat diunduh melalui mekanisme first-run
yang jelas. - Konfigurasi PyInstaller mengumpulkan package data, model,
dan binary yang benar-benar diperlukan. - Jangan mengandalkan path
absolut komputer developer. - Gunakan resource resolver
`resource_utils.py` yang sudah ada jika sesuai. - Perhatikan lokasi
penyimpanan model di luar folder instalasi jika pengguna tidak memiliki
izin menulis ke folder tersebut. - Installer tidak merusak fitur yang
sudah ada. - Dokumentasikan tambahan ukuran installer dan kebutuhan
storage. - Uji pada Windows 10/11 64-bit.

Jangan mengasumsikan bahwa model ONNX otomatis ikut ter-bundle hanya
karena package Python berhasil di-import. Verifikasi file model dan
runtime pada hasil build.

## 14. Pengujian

Tambahkan pengujian minimal:

1.  Input JPG, JPEG, PNG, dan WEBP.
2.  Foto formal dengan background sederhana.
3.  Foto bebas dengan background kompleks.
4.  Foto dengan rambut atau detail tepi halus.
5.  Foto dengan metadata EXIF orientation.
6.  Lima pilihan warna menghasilkan warna sesuai HEX.
7.  Mengganti warna tidak menjalankan ulang inferensi AI.
8.  Preview Before/After.
9.  Export JPG.
10. Export PNG.
11. File rusak atau format tidak didukung.
12. Model tidak tersedia atau gagal dimuat.
13. Foto resolusi tinggi.
14. UI tetap responsif saat inferensi berjalan.
15. Temporary file dibersihkan.
16. Foto sumber tidak berubah.
17. Aplikasi berjalan setelah packaging PyInstaller.

Gunakan test fixture dan temporary directory. Jangan menggunakan atau
mengubah foto pribadi pengguna untuk pengujian otomatis.

## 15. Batasan Perubahan

-   Jangan melakukan redesign seluruh aplikasi.
-   Jangan mengubah fitur Merge, Split, Compress, Convert PDF to PNG,
    Crop, dan Convert Images to PDF kecuali diperlukan untuk integrasi.
-   Jangan menghapus konfigurasi yang sudah berfungsi.
-   Jangan menambah dependency tanpa alasan.
-   Jangan menambahkan custom color picker; hanya lima warna yang
    ditentukan.
-   Jangan mengunggah foto pengguna ke layanan eksternal.
-   Jangan mengubah identitas visual JackPDF.
-   Jangan membuat tombol atau UI yang belum memiliki fungsi.

## 16. Acceptance Criteria

Fitur dinyatakan selesai jika: - Pengguna dapat mengunggah foto. - Mode
Foto Formal dan Foto Bebas tersedia. - Background dapat dihapus otomatis
menggunakan AI lokal. - Pengguna dapat memilih merah, biru, putih,
kuning, dan hijau. - Preview berubah saat warna dipilih tanpa mengulang
inferensi. - Detail subjek dan rasio gambar dipertahankan. - Hasil dapat
disimpan sebagai JPG dan PNG. - Foto sumber tidak berubah. - UI tidak
freeze selama proses. - Error ditangani dengan jelas. - Fitur
terintegrasi ke Home dan navigasi JackPDF. - Model dan dependency
bekerja pada hasil packaging. - Fitur lama tetap berjalan.

Ukuran pas foto 2×3, 3×4, dan 4×6 dapat menjadi bagian fitur jika
berhasil diimplementasikan tanpa mengorbankan stabilitas fitur utama.

## 17. Instruksi untuk AI Coding Agent

Kerjakan bertahap:

### Tahap 1 -- Analisis

-   Periksa struktur project.
-   Pelajari pola halaman fitur dan service yang sudah ada.
-   Periksa dependency Pillow, rembg, ONNX Runtime, serta konfigurasi
    PyInstaller.
-   Evaluasi ukuran model, kebutuhan RAM, lisensi, dan cara distribusi
    model.
-   Laporkan file yang akan dibuat/diubah dan rencana packaging sebelum
    implementasi.

### Tahap 2 -- Implementasi inti

-   Buat service background removal.
-   Buat proses compositing untuk lima warna.
-   Buat halaman UI dan preview.
-   Integrasikan worker/background thread.
-   Tambahkan validasi dan error handling.

### Tahap 3 -- Integrasi

-   Tambahkan menu Home, ikon, dan navigasi.
-   Pertahankan desain JackPDF.
-   Pastikan fitur lain tidak berubah.

### Tahap 4 -- Pengujian

-   Jalankan seluruh test yang ada.
-   Tambahkan test fitur baru.
-   Uji foto formal dan foto bebas.
-   Uji performa dan penggunaan memori.
-   Uji seluruh lima warna serta export.

### Tahap 5 -- Packaging

-   Perbarui konfigurasi PyInstaller jika diperlukan.
-   Verifikasi model, ONNX Runtime, dan package data pada hasil build.
-   Build aplikasi dan uji pada Windows.
-   Perbarui installer Inno Setup jika diperlukan.

### Tahap 6 -- Laporan

Laporkan: - File yang dibuat dan diubah. - Model AI dan library yang
digunakan. - Apakah model dibundel atau diunduh saat pertama kali. -
Perkiraan tambahan ukuran installer dan kebutuhan RAM. - Hasil
pengujian. - Status kompatibilitas PyInstaller. - Keterbatasan yang
masih ada.

**Penting:** Jangan hanya membuat tampilan UI atau tombol dummy.
Implementasikan alur lengkap dari upload foto, background removal,
pemilihan warna, preview, hingga export. Prioritaskan kualitas hasil,
privasi foto, stabilitas aplikasi, dan kompatibilitas installer.
Pertahankan semua fitur JackPDF yang sudah berjalan.
