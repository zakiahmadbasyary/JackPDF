# JackPDF — Fitur Convert PDF to PNG

Spesifikasi dan prompt implementasi fitur Convert PDF to PNG untuk aplikasi desktop JackPDF (Python 3.12, PySide6, PyMuPDF). Ikuti juga `JackPDF_Visual_Design_Guidelines.md`.

## 1. Tujuan

Mengubah halaman PDF yang dipilih menjadi file PNG. Setiap halaman terpilih menghasilkan satu file PNG terpisah.

Contoh:
- PDF 10 halaman, pilih semua → 10 PNG.
- PDF 10 halaman, pilih halaman 2, 5, dan 9 → 3 PNG.

Pengguna dapat memilih semua halaman atau kombinasi halaman bebas, mengatur DPI dan mode warna, menentukan folder output, memantau progres, lalu membuka folder hasil.

## 2. Teknologi

- Python 3.12
- PySide6 untuk UI
- PyMuPDF (`fitz`) untuk render PDF ke PNG
- Pillow hanya jika diperlukan
- pytest untuk pengujian

Gunakan API yang sesuai dengan versi PyMuPDF di proyek. Jangan menambah dependency tanpa kebutuhan.

## 3. Alur Pengguna

1. Buka halaman Convert to PNG.
2. Pilih satu PDF melalui Browse File atau drag-and-drop.
3. Validasi PDF dan tampilkan nama, ukuran, serta jumlah halaman.
4. Pilih halaman yang akan dikonversi.
5. Pilih DPI dan mode warna.
6. Tentukan folder output.
7. Klik Convert to PNG.
8. Render halaman di background worker.
9. Tampilkan progres dan ringkasan hasil.
10. Pengguna dapat membuka folder hasil.

## 4. Rancangan UI/UX

### A. Header dan file
- Judul: `Convert to PNG`.
- Deskripsi: `Ubah halaman PDF menjadi gambar PNG berkualitas tinggi.`
- Dropzone dengan ikon PDF, teks `Pilih file PDF`, dan tombol `Browse File`.
- Setelah file dipilih, tampilkan nama file, ukuran, jumlah halaman, tombol Ganti File dan Hapus.
- Satu file PDF per proses.

### B. Pemilihan halaman — wajib fleksibel

Pengguna harus dapat memilih semua halaman atau halaman mana pun secara bebas. Sediakan tiga cara berikut:

**1. Semua Halaman**
- Opsi `Semua Halaman`.
- Saat dipilih, seluruh halaman otomatis terpilih.

**2. Pilih Manual dengan Checkbox**
- Tampilkan daftar nomor halaman sesuai jumlah halaman PDF.
- Setiap halaman memiliki checkbox.
- Pengguna dapat memilih kombinasi tidak berurutan, misalnya halaman 1, 3, 6, dan 8.
- Sediakan tombol `Pilih Semua` dan `Hapus Pilihan`.
- Tampilkan ringkasan, misalnya `4 dari 8 halaman dipilih`.
- Daftar checkbox harus dapat di-scroll untuk PDF panjang.
- Thumbnail preview boleh menjadi peningkatan opsional. Jangan merender seluruh thumbnail resolusi tinggi sekaligus.

**3. Input Nomor atau Rentang**
- Sediakan input manual untuk mengetik nomor tunggal dan rentang.
- Contoh: `1, 3, 6-8, 12`.
- Nomor halaman dimulai dari 1.
- Dukung kombinasi nomor tunggal dan rentang.
- Spasi di sekitar angka boleh diabaikan.
- Tolak format seperti `3-1`, `1,,2`, `abc`, atau nomor di luar jumlah halaman.
- Hilangkan duplikat dan urutkan sesuai urutan halaman asli.
- Sediakan tombol `Terapkan` jika tidak memakai sinkronisasi langsung.

**Sinkronisasi wajib**
- Memilih Semua Halaman mencentang semua checkbox.
- Checkbox yang diubah memperbarui input manual dan ringkasan.
- Input manual yang diterapkan memperbarui checkbox.
- Tampilkan jumlah halaman terpilih.
- Jika tidak ada halaman terpilih, tombol Convert to PNG nonaktif.
- Jika PDF diganti, reset pilihan halaman.
- Urutan output mengikuti urutan halaman asli, bukan urutan pengguna mencentang.

Contoh: PDF 10 halaman, pengguna mencentang 2, 5, dan 9. Ringkasan menunjukkan `3 dari 10 halaman dipilih`, input menunjukkan `2, 5, 9`, dan hanya halaman itu yang dikonversi.

### C. Resolusi

| Preset | DPI | Kegunaan |
|---|---:|---|
| Standar | 150 | Penggunaan umum, hasil lebih ringan |
| Tinggi | 200 | Keseimbangan detail dan ukuran |
| Sangat Tinggi | 300 | Detail kecil atau kebutuhan cetak |
| Custom | 72–600 | Pengaturan manual |

Default: **Tinggi (200 DPI)**.

DPI tinggi menghasilkan gambar lebih tajam dan dimensi pixel lebih besar, serta biasanya membutuhkan lebih banyak memori dan ruang penyimpanan. Validasi custom DPI dalam rentang 72–600.

### D. Mode warna

- RGB (default), cocok untuk layar dan penggunaan umum.
- Grayscale, menghasilkan gambar abu-abu.
- Jangan sediakan CMYK pada versi awal tanpa kebutuhan teknis.
- Gunakan latar putih secara default. Transparansi bukan kebutuhan versi awal.

### E. Output

- Folder default: `{nama_file}_png` di samping PDF sumber, atau ikuti pola output fitur lain.
- Sediakan tombol Browse untuk memilih folder.
- Nama file: `nama-file_page-001.png`, `nama-file_page-002.png`, dan seterusnya.
- Nomor pada nama file harus nomor halaman asli PDF.
- Gunakan padding angka berdasarkan jumlah halaman.
- Jangan mengubah atau menghapus PDF sumber.
- Jangan overwrite file output diam-diam. Minta folder lain atau konfirmasi eksplisit.

### F. Tombol dan hasil
- Tombol utama: `Convert to PNG`.
- Tombol sekunder: `Reset` atau `Pilih File Lain`.
- Tombol utama nonaktif jika file/halaman/pengaturan belum valid atau proses berjalan.
- Tampilkan tombol `Batal` saat proses jika pembatalan aman.
- Hasil menampilkan status, jumlah halaman terpilih, jumlah berhasil/gagal, DPI, mode warna, folder output, dan tombol `Buka Folder`.
- Jika sebagian halaman gagal, tampilkan nomor halaman yang gagal. Jangan menyatakan semua berhasil.

## 5. Visual

Ikuti `JackPDF_Visual_Design_Guidelines.md`:
- Light theme, background `#F7F9FC`, kartu `#FFFFFF`.
- Navy `#071426` / `#0B1B33`.
- Tombol utama `#1D6FEA`, hover `#1557B0`.
- Aksen cyan `#45C7F5` secukupnya.
- Border `#DCE3EC`.
- Font Segoe UI.
- Radius kartu 12–16 px, tombol 8–10 px.
- Gunakan aset ikon Convert to PNG JackPDF: malaikat maut mengubah dokumen menjadi gambar.
- Jangan menambahkan tulisan pada gambar ikon.
- Hindari ornamen gothic dan glow berlebihan.

## 6. Strategi Teknis

Gunakan PyMuPDF untuk membuka PDF, memvalidasi jumlah halaman, merender halaman terpilih, dan menyimpan PNG.

Contoh konsep API (sesuaikan versi PyMuPDF):

```python
import fitz

document = fitz.open(input_path)
try:
    page_number = 3          # Nomor halaman untuk pengguna (1-based)
    page_index = page_number - 1  # Indeks PyMuPDF (0-based)
    page = document[page_index]
    pixmap = page.get_pixmap(
        dpi=200,
        colorspace=fitz.csRGB,
        alpha=False
    )
    pixmap.save(output_path)
finally:
    document.close()
```

Ketentuan:
- Konversi nomor halaman pengguna (1-based) ke indeks PyMuPDF (0-based) dengan benar.
- Gunakan DPI atau matriks skala sesuai API versi terpasang.
- Gunakan colorspace grayscale yang didukung untuk mode Grayscale.
- `alpha=False` untuk hasil tanpa transparansi; pastikan latar putih.
- Tutup dokumen walaupun terjadi exception.
- Render dan simpan satu halaman pada satu waktu, jangan semua halaman sekaligus.

### Parsing halaman

Buat fungsi terpisah:

```python
def parse_page_selection(value: str, total_pages: int) -> list[int]:
    """Parse '1, 3, 6-8, 12' menjadi [1, 3, 6, 7, 8, 12]."""
```

Fungsi harus:
- Mendukung nomor tunggal, rentang, dan kombinasinya.
- Menolak token kosong, karakter nonangka, rentang terbalik, dan halaman di luar batas.
- Menghilangkan duplikat.
- Mengembalikan nomor halaman unik dalam urutan menaik.
- Tidak mengartikan input kosong sebagai semua halaman.

### Halaman besar
- Render satu per satu.
- Tangani kegagalan per halaman jika memungkinkan.
- Jika dibatalkan, pertahankan file yang sudah berhasil dan laporkan hasil parsial.
- Perkirakan dimensi pixel sebelum render jika memungkinkan untuk mengurangi risiko penggunaan memori berlebihan.

## 7. Validasi dan Error Handling

Validasi:
- File wajib dipilih, tidak kosong, dan PDF valid.
- Jumlah halaman lebih dari nol.
- Minimal satu halaman dipilih.
- Nomor/rentang halaman valid.
- DPI dalam rentang 72–600.
- Mode warna didukung.
- Folder output tersedia atau dapat dibuat.
- Nama file valid untuk Windows.
- Output tidak boleh sama dengan file sumber.
- File output yang sudah ada ditangani dengan aman.

Contoh pesan:
- `Silakan pilih file PDF terlebih dahulu.`
- `File yang dipilih bukan PDF yang valid.`
- `Pilih minimal satu halaman untuk dikonversi.`
- `Nomor halaman melebihi jumlah halaman PDF.`
- `Format halaman tidak valid. Contoh: 1, 3, 6-8, 12.`
- `DPI harus berupa angka antara 72 dan 600.`
- `Folder tujuan tidak dapat diakses.`
- `Halaman 4 gagal dikonversi. Halaman lainnya tetap diproses.`
- `Proses konversi dibatalkan.`

Untuk PDF terenkripsi, minta password melalui alur yang jelas jika didukung. Jangan melewati proteksi atau menyimpan password ke log. Jangan tampilkan traceback kepada pengguna; simpan detail teknis di log aplikasi.

## 8. Background Processing

Gunakan QThread atau QThreadPool mengikuti pola proyek:
- UI tetap responsif.
- Progres berdasarkan halaman terpilih, misalnya `Memproses halaman 3 dari 5 halaman terpilih`.
- Persentase = jumlah halaman selesai / jumlah halaman terpilih.
- Kirim sinyal progres ke UI.
- Worker tidak boleh mengakses widget secara langsung.
- Nonaktifkan kontrol yang mengubah input selama proses.
- Jika dibatalkan, hentikan dengan aman, pertahankan file yang sudah dibuat, dan laporkan hasil parsial.
- Tutup dokumen dan bersihkan worker setelah selesai/gagal.

## 9. Struktur File yang Disarankan

Sesuaikan dengan struktur aktual proyek dan jangan membuat duplikasi:

```text
app/
├── pages/
│   └── convert_png_page.py
├── services/
│   └── convert_png_service.py
├── workers/
│   └── convert_png_worker.py
└── utils/
    └── file_utils.py

tests/
├── test_convert_png_service.py
└── test_page_selection.py
```

- `convert_png_page.py`: UI, pemilihan halaman, DPI, mode warna, output.
- `convert_png_service.py`: validasi, parsing halaman, render PNG.
- `convert_png_worker.py`: background processing dan sinyal progres.
- `file_utils.py`: utilitas path/ukuran jika belum tersedia.
- `tests/`: pengujian.

## 10. Pengujian

Gunakan pytest dan PDF fixture lokal. Minimal uji:
1. PDF satu halaman berhasil dikonversi.
2. PDF multi-halaman menghasilkan PNG sesuai halaman terpilih.
3. Semua halaman menghasilkan jumlah PNG sesuai jumlah halaman PDF.
4. Pilihan manual 2, 5, 9 hanya menghasilkan tiga PNG.
5. Input `1, 3, 6-8, 12` menghasilkan `[1, 3, 6, 7, 8, 12]`.
6. Checkbox dan input manual tersinkronisasi.
7. Pilih Semua dan Hapus Pilihan berfungsi.
8. Duplikat dihilangkan.
9. Nomor di luar batas ditolak.
10. Rentang terbalik dan format salah ditolak.
11. DPI 150, 200, 300 dan custom valid bekerja.
12. DPI di luar batas ditolak.
13. RGB menghasilkan PNG RGB.
14. Grayscale menghasilkan PNG grayscale.
15. PNG dapat dibuka kembali oleh Pillow atau image viewer.
16. Dimensi pixel sesuai DPI.
17. File bukan PDF, kosong, atau rusak ditangani.
18. PDF terenkripsi mengikuti alur password.
19. Output yang sudah ada tidak ditimpa diam-diam.
20. Kegagalan satu halaman dilaporkan.
21. Pembatalan proses ditangani.
22. Dokumen selalu ditutup.

## 11. Kriteria Penerimaan

Fitur selesai jika:
- Pengguna dapat memilih satu PDF dan melihat informasinya.
- Pengguna dapat memilih semua halaman.
- Pengguna dapat memilih kombinasi halaman bebas melalui checkbox.
- Pengguna dapat mengetik nomor dan rentang halaman.
- Checkbox, input manual, dan ringkasan pilihan tersinkronisasi.
- Pengguna dapat memilih DPI dan mode warna.
- Pengguna dapat menentukan folder output.
- Setiap halaman terpilih menghasilkan satu PNG.
- Nama file memakai nomor halaman asli dan urut.
- Proses tidak membekukan UI.
- Progres sesuai jumlah halaman terpilih.
- File sumber aman.
- PNG dapat dibuka dan dimensinya sesuai DPI.
- Error dan halaman gagal dilaporkan dengan jelas.
- UI konsisten dengan design guidelines.
- Unit test utama lulus.

---

# 12. Prompt Implementasi untuk AI Coding Agent

Kamu adalah Python Desktop Application Engineer yang berpengalaman menggunakan PySide6 dan PyMuPDF. Implementasikan fitur **Convert PDF to PNG** pada repository JackPDF berdasarkan spesifikasi ini dan `JackPDF_Visual_Design_Guidelines.md`.

## Aturan kerja
1. Inspeksi struktur proyek terlebih dahulu.
2. Pelajari pola navigasi, halaman, komponen UI, stylesheet, worker, service, dan error handling.
3. Gunakan kembali pola/komponen yang ada; jangan membuat sistem duplikat.
4. Jangan menimpa atau menghapus fitur lain yang sudah berjalan.
5. Implementasikan langsung pada file proyek, bukan hanya memberi snippet.
6. Gunakan PyMuPDF dan periksa API sesuai versi terpasang.
7. Pisahkan UI, service, dan background worker.
8. Render satu halaman per satu waktu.
9. Jangan mengubah/menghapus PDF sumber.
10. Jangan overwrite output tanpa konfirmasi.
11. Hindari refactor besar yang tidak diperlukan.

## Implementasi wajib
- Halaman Convert to PNG dengan Browse File dan drag-and-drop.
- Informasi nama, ukuran, dan jumlah halaman.
- Opsi Semua Halaman.
- Checkbox untuk memilih halaman satu per satu secara bebas.
- Tombol Pilih Semua dan Hapus Pilihan.
- Input manual nomor/rentang seperti `1, 3, 6-8, 12`.
- Sinkronisasi checkbox, input manual, dan ringkasan pilihan.
- Validasi halaman dan rentang.
- DPI 150, 200, 300, serta custom 72–600.
- Mode RGB dan Grayscale.
- Pemilihan folder output.
- Nama file berisi nomor halaman asli, misalnya `dokumen_page-009.png`.
- Background worker dengan progres berdasarkan halaman terpilih.
- Penanganan pembatalan dan halaman gagal.
- Ringkasan hasil dan tombol Buka Folder.
- Unit test konversi, parsing halaman, sinkronisasi, dan validasi.
- Integrasi ke Home/navigasi mengikuti pola proyek.

## Visual
Gunakan light theme JackPDF, warna navy/biru/cyan/abu-abu/putih, font Segoe UI, kartu putih, border tipis, radius konsisten, dan tombol utama biru. Gunakan aset ikon Convert to PNG yang sudah disediakan. Jangan menambahkan tulisan ke gambar ikon. Jaga tampilan sederhana.

## Setelah implementasi
- Jalankan unit test dan perbaiki error.
- Pastikan halaman dapat dibuka dari Home/navigasi.
- Pastikan pemilihan bebas melalui checkbox dan input manual benar-benar berfungsi.
- Pastikan fitur lain tetap berjalan.
- Laporkan file yang dibuat/diubah, dependency, hasil test, dan keterbatasan.

Mulai dengan inspeksi repository, lalu implementasikan fitur secara menyeluruh. Jangan berhenti setelah membuat rencana.

---

**Kesimpulan:** pengguna harus bisa mengonversi semua halaman atau memilih kombinasi halaman mana pun. Hasil PNG harus memiliki nama sesuai nomor halaman asli, kualitas sesuai DPI, dan proses yang tetap responsif.
