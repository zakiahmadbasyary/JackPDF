# JackPDF — Fitur Compress PDF

Dokumen ini adalah spesifikasi sekaligus prompt implementasi fitur **Compress PDF** pada aplikasi desktop JackPDF (Python 3.12, PySide6, PyMuPDF). Ikuti juga `JackPDF_Visual_Design_Guidelines.md`.

## 1. Tujuan

Mengurangi ukuran file PDF agar lebih mudah disimpan, dibagikan, atau diunggah. Pengguna memilih PDF, menentukan preset kompresi, memilih lokasi output, lalu melihat perbandingan ukuran sebelum dan sesudah.

**Catatan:** kompresi tidak selalu menghasilkan file lebih kecil. Hasil bergantung pada isi PDF dan tingkat optimasi file sumber.

## 2. Alur Pengguna

1. Buka halaman **Compress PDF**.
2. Pilih atau drag-and-drop satu file PDF.
3. Tampilkan nama file, ukuran awal, dan jumlah halaman.
4. Pilih preset kompresi.
5. Tentukan nama dan lokasi file hasil.
6. Klik **Compress PDF**.
7. Proses berjalan di background agar UI tidak freeze.
8. Tampilkan ringkasan hasil dan tombol membuka file/folder.

## 3. Pilihan Kompresi

Sediakan tiga preset dengan default **Seimbang**.

| Preset | Tujuan | Perilaku |
|---|---|---|
| Kualitas Tinggi | Menjaga kualitas visual | Optimasi struktur dan stream; hindari downsampling agresif |
| Seimbang | Kompromi ukuran dan kualitas | Optimasi struktur dan kompresi gambar moderat |
| Ukuran Lebih Kecil | Memprioritaskan ukuran file | Downsampling gambar lebih agresif; beri tahu pengguna kualitas gambar dapat menurun |

Jangan menjanjikan persentase pengurangan ukuran tertentu. Nilai kualitas gambar dan resolusi target harus disimpan terpusat dalam konfigurasi preset dan ditentukan melalui pengujian.

## 4. Rancangan UI

### Header
- Judul: `Compress PDF`
- Deskripsi: `Kurangi ukuran file PDF agar lebih mudah disimpan dan dibagikan.`

### Pemilihan file
- Dropzone dengan ikon dokumen PDF.
- Teks: `Pilih file PDF` dan `atau tarik dan letakkan file di sini`.
- Tombol `Browse File`.
- Setelah file dipilih, tampilkan nama, ukuran, jumlah halaman, dan kontrol ganti/hapus file.

### Preset
Tampilkan tiga pilihan preset sebagai radio card atau segmented card. Setiap preset memiliki nama dan deskripsi singkat.

### Output
- Nama default: `{nama_file}_compressed.pdf`.
- Nama file bisa diedit.
- Folder output bisa dipilih melalui dialog.
- Jangan pernah menimpa file sumber.
- Jika nama output sudah ada, minta nama lain atau konfirmasi eksplisit sebelum mengganti.

### Aksi dan hasil
- Tombol utama: `Compress PDF`.
- Tombol sekunder: `Reset` atau `Pilih File Lain`.
- Setelah berhasil, tampilkan ukuran awal, ukuran akhir, selisih, persentase perubahan, tombol `Buka File`, dan `Buka Folder`.
- Jika hasil lebih besar, tampilkan keterangan `Ukuran bertambah`; jangan menyebutnya sebagai penghematan.

## 5. Identitas Visual

Ikuti `JackPDF_Visual_Design_Guidelines.md`:
- Light theme.
- Background `#F7F9FC`, kartu `#FFFFFF`.
- Navy `#071426` / `#0B1B33`.
- Tombol utama `#1D6FEA`, hover `#1557B0`.
- Aksen cyan `#45C7F5` secukupnya.
- Border `#DCE3EC`.
- Font Segoe UI.
- Radius kartu 12–16 px, tombol 8–10 px.
- Gunakan aset ikon Compress JackPDF: malaikat maut memangkas dokumen menggunakan sabit.
- Jangan menambahkan tulisan ke gambar ikon dan jangan memenuhi UI dengan ornamen gothic, glow, atau efek berlebihan.

## 6. Strategi Teknis Kompresi

Gunakan PyMuPDF sebagai library utama. Periksa API `Document.save()` berdasarkan versi PyMuPDF yang terpasang. Evaluasi opsi yang tersedia, seperti:
- garbage collection untuk membersihkan objek yang tidak terpakai;
- deflate untuk mengompresi stream;
- clean untuk membersihkan konten PDF bila sesuai;
- optimasi gambar berdasarkan preset.

Jangan mengasumsikan semua parameter tersedia atau memiliki perilaku identik pada setiap versi library.

### Prinsip perlindungan konten
- Jangan merasterisasi seluruh halaman PDF.
- Pertahankan teks agar tetap dapat dipilih dan dicari.
- Pertahankan grafik vektor jika memungkinkan.
- Pertahankan ukuran halaman, orientasi, urutan, dan jumlah halaman.
- Pertahankan metadata, bookmark, anotasi, form, dan lampiran sejauh didukung.
- Jangan menghapus elemen interaktif secara diam-diam.
- PDF terenkripsi harus ditangani dengan alur password yang jelas; jangan melewati proteksi.
- PDF rusak/tidak terbaca harus ditolak dengan pesan yang ramah.
- Jangan mengubah atau menghapus file sumber.
- Menyimpan ulang PDF dapat membatalkan tanda tangan digital. Deteksi bila memungkinkan dan beri peringatan sebelum proses.

## 7. Perhitungan Ukuran

Ambil ukuran sumber dan output langsung dari file aktual di disk.

```python
saved_bytes = original_size - compressed_size

if original_size > 0:
    change_percent = (saved_bytes / original_size) * 100
else:
    change_percent = 0
```

Interpretasi:
- Nilai positif: ukuran berkurang.
- Nol: ukuran tidak berubah.
- Negatif: ukuran bertambah.

Format ukuran ke B, KB, atau MB secara konsisten. Jika ukuran bertambah, gunakan label yang jelas dan jangan menampilkan angka negatif sebagai penghematan.

## 8. Background Processing

Gunakan QThread atau QThreadPool sesuai pola yang sudah ada di proyek.
- UI harus tetap responsif.
- Tampilkan indikator `Sedang memproses...`.
- Nonaktifkan kontrol yang dapat mengubah file/preset saat proses berjalan.
- Kirim progres hanya jika progres dapat dihitung secara akurat.
- Jangan membuat progress bar palsu.
- Worker tidak boleh memperbarui widget secara langsung.
- Tangani sinyal sukses/gagal dan bersihkan worker setelah selesai.

Jika progres tidak dapat diukur, gunakan spinner/indikator proses tanpa persentase.

## 9. Validasi dan Error Handling

Validasi:
- File wajib dipilih.
- Ekstensi dan isi file harus merupakan PDF yang valid.
- File tidak kosong dan dapat diakses.
- Path output tidak boleh sama dengan path sumber.
- Folder output tersedia atau dapat dibuat.
- Nama output valid untuk Windows.
- File output yang sudah ada ditangani dengan aman.

Contoh pesan:
- `Silakan pilih file PDF terlebih dahulu.`
- `File yang dipilih bukan PDF yang valid.`
- `PDF ini dilindungi password. Masukkan password atau pilih file lain.`
- `File sedang digunakan aplikasi lain. Tutup file tersebut lalu coba lagi.`
- `Folder tujuan tidak dapat diakses.`
- `Proses kompresi gagal. File asli tetap aman.`

Jangan tampilkan traceback kepada pengguna. Simpan detail teknis di log aplikasi.

## 10. Struktur File yang Disarankan

Sesuaikan dengan struktur aktual proyek; jangan menduplikasi pola yang sudah tersedia.

```text
app/
├── pages/
│   └── compress_page.py
├── services/
│   └── compress_service.py
├── workers/
│   └── compress_worker.py
└── utils/
    └── file_utils.py

tests/
├── test_compress_service.py
└── test_compress_validation.py
```

Tanggung jawab:
- `compress_page.py`: UI dan interaksi.
- `compress_service.py`: validasi dan logika kompresi.
- `compress_worker.py`: menjalankan service di background.
- `file_utils.py`: utilitas ukuran dan path jika belum tersedia.
- `tests/`: pengujian service dan validasi.

## 11. Pengujian

Gunakan pytest. Skenario minimum:
1. PDF teks sederhana berhasil diproses.
2. PDF berisi gambar berhasil diproses.
3. PDF multi-halaman mempertahankan jumlah halaman.
4. Teks hasil tetap dapat diekstrak.
5. Ukuran halaman dan orientasi tetap sama.
6. File bukan PDF dan file kosong ditolak.
7. PDF rusak ditangani dengan aman.
8. PDF terenkripsi mengikuti alur password.
9. File sumber tidak berubah.
10. Output tidak menimpa sumber.
11. Nama output yang sudah ada ditangani.
12. Ketiga preset dapat dijalankan.
13. Hasil yang lebih besar ditampilkan dengan benar.
14. Kegagalan penyimpanan tidak meninggalkan output parsial yang dianggap berhasil.

Jangan membuat test yang mengharuskan semua PDF menjadi lebih kecil.

## 12. Kriteria Penerimaan

Fitur selesai jika:
- Pengguna dapat memilih satu PDF dan melihat informasinya.
- Tiga preset dapat dipilih.
- Nama dan lokasi output dapat ditentukan.
- Proses berjalan tanpa membekukan UI.
- File sumber tetap aman.
- File hasil dapat dibuka.
- Teks dan struktur halaman dipertahankan sejauh didukung metode.
- Perbandingan ukuran dihitung dari file aktual.
- Kondisi ukuran bertambah ditangani secara jujur.
- Error ditampilkan dengan bahasa yang mudah dipahami.
- UI konsisten dengan design guidelines JackPDF.
- Unit test utama lulus.

---

# Prompt Implementasi untuk AI Coding Agent

Kamu adalah Python Desktop Application Engineer yang berpengalaman menggunakan PySide6 dan PyMuPDF. Implementasikan fitur **Compress PDF** pada repository JackPDF berdasarkan spesifikasi di atas dan `JackPDF_Visual_Design_Guidelines.md`.

## Aturan kerja
1. Inspeksi struktur proyek terlebih dahulu.
2. Pelajari pola navigasi, halaman, stylesheet, service, worker thread, dan error handling yang sudah ada.
3. Gunakan kembali komponen/pola yang tersedia; jangan membuat sistem duplikat.
4. Jangan menimpa atau menghapus kode fitur lain yang sudah berjalan.
5. Implementasikan langsung ke file proyek, bukan hanya memberikan snippet.
6. Gunakan PyMuPDF dan periksa API sesuai versi terpasang.
7. Pisahkan UI, service kompresi, dan background worker.
8. Pastikan UI tidak freeze.
9. Lindungi file sumber dan hindari overwrite tanpa konfirmasi.
10. Jangan merasterisasi seluruh halaman PDF.
11. Jangan menjanjikan semua PDF akan menjadi lebih kecil.
12. Hindari refactor besar yang tidak diperlukan.

## Implementasi wajib
- Halaman Compress PDF dengan browse dan drag-and-drop.
- Informasi nama, ukuran, dan jumlah halaman.
- Preset Kualitas Tinggi, Seimbang, dan Ukuran Lebih Kecil.
- Input nama file dan pemilihan folder output.
- Tombol proses, indikator berjalan, dan error handling.
- Ringkasan ukuran sebelum/sesudah.
- Tombol membuka file dan folder hasil.
- Validasi PDF, penanganan file terenkripsi/rusak, dan perlindungan file sumber.
- Unit test untuk service dan validasi.
- Integrasikan halaman ke navigasi/Home mengikuti pola proyek.

## Visual
Gunakan light theme JackPDF dengan navy, biru, cyan, abu-abu, dan putih; font Segoe UI; kartu putih; border tipis; radius konsisten; dan tombol utama biru. Gunakan aset ikon Compress yang sudah disediakan tanpa menambahkan teks pada gambar. Jaga tampilan tetap sederhana dan tidak terlalu dekoratif.

## Setelah implementasi
- Jalankan unit test dan perbaiki error.
- Pastikan halaman dapat dibuka dari navigasi/Home.
- Pastikan fitur lain tetap berjalan.
- Laporkan file yang dibuat/diubah, dependency yang diperlukan, hasil test, serta keterbatasan kompresi yang masih ada.

Mulai dengan inspeksi repository, lalu implementasikan fitur secara menyeluruh. Jangan berhenti setelah membuat rencana.
