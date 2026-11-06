# JackPDF — Fitur Crop PDF

Dokumen ini menjadi spesifikasi dan prompt implementasi fitur **Crop PDF** pada aplikasi desktop JackPDF menggunakan Python, PySide6, dan PyMuPDF.

Gunakan juga `JackPDF_Visual_Design_Guidelines.md` sebagai acuan warna, tipografi, komponen, dan identitas visual.

---

## 1. Tujuan Fitur

Fitur Crop PDF digunakan untuk memotong area tampilan halaman PDF agar pengguna dapat membuang margin kosong atau memusatkan bagian dokumen yang dibutuhkan.

Pengguna dapat:
- Memilih satu file PDF.
- Melihat preview halaman PDF.
- Mengatur area crop dengan menarik batas/handle pada preview.
- Mengatur nilai crop secara manual.
- Memilih halaman yang akan di-crop.
- Menerapkan area crop ke satu halaman, halaman tertentu, atau semua halaman.
- Melihat preview hasil sebelum menyimpan.
- Menentukan nama dan lokasi file output.
- Menyimpan hasil sebagai file PDF baru.

**Penting:** implementasi crop berbasis `CropBox` pada PDF umumnya mengubah area halaman yang ditampilkan, bukan menghapus permanen konten di luar area crop. Konten di luar area tersebut mungkin masih tersimpan di dalam file dan dapat dipulihkan oleh aplikasi PDF tertentu. Jangan menyebutnya sebagai penghapusan permanen atau redaksi konten.

## 2. Teknologi

Gunakan stack JackPDF:
- Python 3.12.
- PySide6 untuk UI desktop.
- PyMuPDF (`fitz`) untuk membuka PDF, membaca ukuran halaman, mengatur crop box, dan menyimpan PDF hasil.
- Pillow hanya jika diperlukan untuk membuat preview tambahan.
- pytest untuk unit testing.

Gunakan PyMuPDF sebagai library utama. Periksa API dan perilaku koordinat berdasarkan versi yang terpasang. Jangan menambahkan dependency tanpa kebutuhan yang jelas.

## 3. Alur Pengguna

1. Pengguna membuka halaman **Crop PDF**.
2. Pengguna memilih satu file PDF melalui Browse File atau drag-and-drop.
3. Aplikasi memvalidasi PDF dan membaca jumlah halaman.
4. Aplikasi menampilkan preview halaman.
5. Pengguna memilih halaman yang akan di-crop.
6. Pengguna mengatur area crop dengan:
   - Menarik handle pada preview.
   - Memasukkan nilai margin/koordinat secara manual.
7. Pengguna melihat preview hasil crop.
8. Pengguna memilih apakah area crop diterapkan ke satu halaman, halaman tertentu, atau semua halaman.
9. Pengguna menentukan nama dan lokasi output.
10. Pengguna menekan tombol **Crop PDF**.
11. Aplikasi memproses PDF di background thread.
12. Setelah selesai, aplikasi menampilkan status dan tombol membuka file/folder hasil.

---

## 4. Rancangan UI/UX

### 4.1 Header

- Judul: `Crop PDF`
- Deskripsi: `Potong area halaman PDF sesuai kebutuhan.`
- Tombol kembali jika sesuai dengan pola navigasi aplikasi.

### 4.2 Area pemilihan PDF

Sediakan dropzone:
- Ikon dokumen PDF.
- Teks `Pilih file PDF`.
- Teks pendukung `atau tarik dan letakkan file di sini`.
- Tombol `Browse File`.

Setelah file dipilih, tampilkan:
- Nama file.
- Ukuran file.
- Jumlah halaman.
- Tombol `Ganti File` dan `Hapus`.

Untuk versi awal, satu proses menerima satu file PDF.

### 4.3 Preview halaman PDF

Preview merupakan bagian utama halaman Crop PDF.

Tampilkan:
- Area preview halaman yang sedang dipilih.
- Nomor halaman aktif, misalnya `Halaman 2 dari 10`.
- Tombol halaman sebelumnya dan berikutnya.
- Kontrol zoom in, zoom out, dan fit to page.
- Overlay atau garis batas crop yang terlihat jelas.
- Handle pada empat sudut dan empat sisi untuk mengubah ukuran area crop.
- Area di luar crop diberi overlay abu-abu transparan agar batas crop mudah dipahami.

Perilaku interaksi:
- Pengguna dapat menarik area crop untuk memindahkan seleksi.
- Pengguna dapat menarik handle untuk mengubah lebar dan tinggi area.
- Area crop tidak boleh keluar dari batas halaman.
- Area crop tidak boleh memiliki lebar atau tinggi nol.
- Preview harus mempertahankan rasio halaman.
- Perubahan zoom tidak boleh mengubah koordinat crop sebenarnya.
- Gunakan koordinat dokumen sebagai sumber data utama; posisi layar hanya untuk visualisasi dan interaksi.

Jika PDF memiliki banyak halaman:
- Jangan merender seluruh halaman sekaligus.
- Render halaman aktif dan halaman yang diperlukan saja.
- Gunakan thumbnail ringan atau navigasi nomor halaman jika dibutuhkan.
- Hindari UI menjadi berat pada dokumen panjang.

### 4.4 Pengaturan Area Crop

Sediakan dua cara pengaturan yang saling tersinkronisasi.

**A. Drag pada Preview**
- Pengguna menarik batas crop langsung pada halaman.
- Handle dapat digunakan untuk mengubah ukuran.
- Pengguna dapat memindahkan keseluruhan kotak crop.
- Perubahan langsung memperbarui nilai pengaturan.

**B. Input Manual**

Sediakan input margin:
- Top
- Bottom
- Left
- Right

Gunakan satuan yang konsisten, rekomendasi **millimeter (mm)** pada UI. Konversikan ke satuan koordinat PDF saat diterapkan.

Aturan:
- Nilai harus numerik dan tidak negatif.
- Jumlah margin kiri dan kanan tidak boleh menghilangkan seluruh lebar halaman.
- Jumlah margin atas dan bawah tidak boleh menghilangkan seluruh tinggi halaman.
- Tampilkan ukuran halaman dan ukuran area hasil crop.
- Perubahan nilai manual memperbarui overlay preview.
- Perubahan drag preview memperbarui nilai manual.

Sediakan tombol:
- `Reset Crop` untuk mengembalikan area ke seluruh halaman.
- `Center Crop` bila pengguna ingin mengembalikan seleksi ke tengah dengan ukuran yang sedang dipilih, jika implementasi mendukungnya.

### 4.5 Pemilihan Halaman yang Di-crop

Sediakan pilihan:

| Opsi | Perilaku |
|---|---|
| Halaman Saat Ini | Hanya halaman yang sedang ditampilkan |
| Halaman Tertentu | Pengguna menentukan nomor/rentang halaman |
| Semua Halaman | Menerapkan area crop ke seluruh halaman |

Untuk `Halaman Tertentu`, sediakan input seperti:
```text
1, 3, 5-7
```

Ketentuan:
- Nomor halaman dimulai dari 1.
- Dukung nomor tunggal, rentang, dan kombinasi.
- Tolak halaman di luar jumlah halaman dokumen.
- Tolak rentang terbalik dan format yang tidak valid.
- Hilangkan duplikat.
- Urutkan berdasarkan urutan halaman asli.
- Tampilkan jumlah halaman terpilih.

**Penerapan area crop ke banyak halaman:**
- Secara default, gunakan area crop yang sama pada setiap halaman terpilih.
- Jika ukuran halaman berbeda, pertahankan margin fisik (mm) yang sama pada masing-masing halaman, lalu hitung ulang koordinat crop sesuai ukuran halaman masing-masing.
- Jika margin tersebut tidak valid untuk salah satu halaman, jangan memotong secara tidak sengaja. Tampilkan daftar halaman yang tidak valid dan minta pengguna memperbaiki pilihan atau mengecualikan halaman tersebut.
- Preview utama menampilkan halaman aktif. Beri keterangan bahwa pengaturan yang sama akan diterapkan ke halaman terpilih.

### 4.6 Pengaturan Output

- Nama default: `{nama_file}_cropped.pdf`.
- Pengguna dapat mengubah nama file.
- Folder default: folder yang sama dengan file sumber atau ikuti pola output fitur JackPDF lainnya.
- Sediakan tombol `Browse` untuk memilih folder.
- Jangan pernah mengubah file sumber.
- Jangan menimpa output yang sudah ada tanpa konfirmasi.
- Pastikan output tidak sama dengan path file sumber.

### 4.7 Tombol Aksi

- Tombol utama: `Crop PDF`.
- Tombol sekunder: `Reset Crop`.
- Tombol `Batal` saat proses berlangsung jika pembatalan aman.
- Tombol utama nonaktif jika file tidak valid, area crop tidak valid, halaman belum dipilih, atau proses sedang berjalan.

### 4.8 Hasil

Setelah berhasil, tampilkan:
- Status berhasil.
- Nama file hasil.
- Jumlah halaman yang di-crop.
- Halaman yang dilewati/gagal jika ada.
- Lokasi output.
- Tombol `Buka File`.
- Tombol `Buka Folder`.

Jelaskan bahwa crop berbasis CropBox mengubah area tampilan halaman dan belum tentu menghapus konten di luar area secara permanen.

---

## 5. Gaya Visual

Ikuti `JackPDF_Visual_Design_Guidelines.md`:
- Light theme.
- Background `#F7F9FC`.
- Kartu putih `#FFFFFF`.
- Navy `#071426` dan `#0B1B33`.
- Tombol utama `#1D6FEA`.
- Hover tombol `#1557B0`.
- Aksen cyan `#45C7F5` secukupnya.
- Border `#DCE3EC`.
- Font Segoe UI.
- Radius kartu 12–16 px dan tombol 8–10 px.
- Gunakan aset ikon Crop JackPDF yang sudah disiapkan: malaikat maut memotong sisi kertas menggunakan sabit.
- Jangan menambahkan tulisan pada gambar ikon.
- Gunakan garis crop dan handle dengan kontras jelas.
- Pertahankan UI sederhana, hindari ornamen gothic dan glow berlebihan.

---

## 6. Strategi Teknis Crop PDF

### 6.1 CropBox dan MediaBox

PDF memiliki beberapa konsep batas halaman. Untuk fitur versi awal:
- Gunakan `CropBox` untuk menentukan area halaman yang terlihat.
- Jangan mengubah `MediaBox` tanpa alasan teknis yang kuat.
- Jangan mengklaim konten di luar CropBox telah dihapus permanen.
- Pertahankan rotasi, orientasi, dan struktur halaman sejauh didukung.

PyMuPDF menyediakan properti/metode untuk membaca dan mengatur crop box. Periksa dokumentasi sesuai versi terpasang, termasuk aturan koordinat dan pembatasan bahwa crop box harus berada di dalam media box.

### 6.2 Koordinat dan Satuan

Koordinat PDF/PyMuPDF tidak sama dengan posisi pixel pada preview.

Implementasikan fungsi konversi terpisah untuk:
- Koordinat widget/layar ke koordinat halaman PDF.
- Koordinat halaman PDF ke posisi preview.
- Millimeter ke point PDF.
- Penyesuaian zoom dan offset preview.

Konversi satuan:
- 1 inch = 25.4 mm.
- 1 inch = 72 PDF points.
- 1 mm = 72 / 25.4 PDF points.

Jangan menggunakan posisi mouse langsung sebagai koordinat CropBox.

Pastikan implementasi memperhitungkan:
- Skala preview.
- Posisi halaman di dalam widget.
- Margin/padding widget.
- Zoom.
- Rotasi halaman.
- Ukuran halaman yang berbeda.

### 6.3 Penerapan CropBox

Alur service:
1. Buka PDF sumber.
2. Validasi halaman yang akan diubah.
3. Ambil ukuran dan batas halaman.
4. Konversi margin/seleksi menjadi koordinat halaman.
5. Pastikan crop rectangle valid dan berada dalam batas halaman.
6. Terapkan CropBox pada halaman terpilih.
7. Simpan ke file output baru.
8. Validasi file hasil dapat dibuka kembali.

Gunakan API PyMuPDF yang sesuai versi terpasang. Jangan menulis ulang PDF dengan pendekatan yang menghilangkan konten atau fitur dokumen tanpa persetujuan pengguna.

### 6.4 Perbedaan Ukuran Halaman

Jika semua halaman memiliki ukuran yang sama, area crop yang sama dapat digunakan.

Jika ukuran halaman berbeda:
- Gunakan margin fisik yang sama (mm) sebagai default untuk setiap halaman.
- Hitung ulang koordinat crop berdasarkan dimensi masing-masing halaman.
- Validasi tiap halaman.
- Laporkan halaman yang tidak dapat menerima margin tersebut.
- Jangan memaksakan crop rectangle yang berada di luar batas halaman.

---

## 7. Validasi dan Error Handling

Validasi minimal:
- File wajib dipilih.
- File harus PDF valid dan dapat dibuka.
- File tidak kosong.
- Jumlah halaman lebih dari nol.
- Minimal satu halaman dipilih.
- Nomor/rentang halaman valid.
- Crop rectangle memiliki lebar dan tinggi positif.
- Crop rectangle berada di dalam batas halaman.
- Margin tidak negatif.
- Area hasil crop tidak terlalu kecil atau kosong.
- Folder output tersedia atau dapat dibuat.
- Nama file output valid untuk Windows.
- Output tidak boleh sama dengan file sumber.
- Output yang sudah ada ditangani dengan aman.

Contoh pesan:
- `Silakan pilih file PDF terlebih dahulu.`
- `File yang dipilih bukan PDF yang valid.`
- `Pilih minimal satu halaman untuk di-crop.`
- `Area crop berada di luar batas halaman.`
- `Margin terlalu besar. Periksa kembali nilai Top, Bottom, Left, dan Right.`
- `Rentang halaman tidak valid.`
- `Ukuran halaman berbeda. Periksa halaman yang tidak dapat menggunakan margin ini.`
- `Folder tujuan tidak dapat diakses.`
- `Proses crop gagal. File asli tetap aman.`

PDF terenkripsi:
- Jika PDF membutuhkan password, tampilkan alur input password jika didukung.
- Jangan mencoba melewati proteksi.
- Jangan menyimpan password ke log.

Tanda tangan digital:
- Menyimpan ulang PDF dapat membatalkan validitas tanda tangan digital.
- Deteksi bila memungkinkan dan beri peringatan sebelum proses dilanjutkan.

Jangan tampilkan traceback mentah kepada pengguna. Simpan detail teknis pada log aplikasi.

---

## 8. Background Processing

Gunakan QThread atau QThreadPool mengikuti pola proyek.

Kebutuhan:
- UI tetap responsif.
- Tampilkan indikator proses.
- Jika beberapa halaman diproses, tampilkan progres berdasarkan jumlah halaman selesai.
- Contoh: `Memproses halaman 3 dari 8`.
- Jangan membuat progres palsu.
- Worker mengirim sinyal progres ke UI.
- Worker tidak boleh mengakses widget UI secara langsung.
- Nonaktifkan kontrol yang dapat mengubah input selama proses.
- Tangani pembatalan secara aman jika didukung.
- Tutup dokumen dan bersihkan worker setelah selesai/gagal.

Untuk operasi CropBox yang sangat cepat, indikator proses sederhana mungkin cukup. Namun, tetap gunakan worker jika dokumen besar atau banyak halaman.

---

## 9. Struktur File yang Disarankan

Sesuaikan dengan struktur aktual proyek. Jangan membuat folder atau service duplikat jika pola tersebut sudah tersedia.

```text
app/
├── pages/
│   └── crop_page.py
├── services/
│   └── crop_service.py
├── workers/
│   └── crop_worker.py
└── utils/
    └── pdf_geometry.py

tests/
├── test_crop_service.py
├── test_crop_geometry.py
└── test_page_selection.py
```

Tanggung jawab:
- `crop_page.py`: UI, preview, drag handle, input margin, pemilihan halaman, dan output.
- `crop_service.py`: validasi PDF dan penerapan CropBox.
- `crop_worker.py`: background processing dan sinyal progres.
- `pdf_geometry.py`: konversi koordinat, mm/point, zoom, dan geometri preview.
- `tests/`: pengujian service, geometri, dan validasi.

---

## 10. Pengujian

Gunakan pytest dan PDF fixture lokal.

Skenario minimum:
1. PDF satu halaman berhasil di-crop.
2. PDF multi-halaman dapat di-crop pada semua halaman.
3. Halaman tertentu saja yang dipilih dan diproses.
4. Input nomor/rentang halaman diparsing dengan benar.
5. Rentang halaman tidak valid ditolak.
6. CropBox hasil sesuai dengan area yang dipilih.
7. Crop rectangle tidak boleh keluar dari batas halaman.
8. Margin negatif ditolak.
9. Margin yang terlalu besar ditolak.
10. Halaman dengan ukuran berbeda dihitung dengan benar.
11. Rotasi halaman ditangani dengan benar.
12. Perubahan zoom tidak mengubah koordinat crop sebenarnya.
13. Konversi mm ke point dan sebaliknya akurat.
14. File sumber tidak berubah.
15. Output tidak menimpa sumber.
16. Output yang sudah ada ditangani dengan aman.
17. PDF rusak dan terenkripsi ditangani sesuai aturan.
18. PDF hasil dapat dibuka kembali.
19. Jumlah halaman dan urutan halaman tetap sama.
20. Kegagalan penyimpanan tidak membuat output parsial dianggap berhasil.

Uji bahwa area yang terlihat setelah CropBox diterapkan sesuai preview. Jangan menguji dengan asumsi konten di luar CropBox telah terhapus permanen.

---

## 11. Kriteria Penerimaan

Fitur dianggap selesai jika:
- Pengguna dapat memilih satu file PDF.
- Preview halaman dapat ditampilkan.
- Pengguna dapat berpindah halaman.
- Pengguna dapat mengatur crop dengan drag handle.
- Pengguna dapat memasukkan margin secara manual.
- Drag preview dan input manual saling tersinkronisasi.
- Pengguna dapat memilih halaman saat ini, halaman tertentu, atau semua halaman.
- Area crop divalidasi terhadap ukuran halaman.
- Pengguna dapat menentukan nama dan lokasi output.
- Proses tidak membekukan UI.
- File sumber tetap aman.
- PDF hasil dapat dibuka dan area tampilan sesuai preview.
- Keterbatasan CropBox dijelaskan dengan jujur.
- Error ditampilkan dengan bahasa yang mudah dipahami.
- UI konsisten dengan design guidelines JackPDF.
- Unit test utama lulus.

---

# 12. Prompt Implementasi untuk AI Coding Agent

Kamu bertugas sebagai Python Desktop Application Engineer yang berpengalaman menggunakan PySide6 dan PyMuPDF.

Implementasikan fitur **Crop PDF** pada repository JackPDF berdasarkan spesifikasi dokumen ini dan `JackPDF_Visual_Design_Guidelines.md`.

## Aturan Kerja

1. Inspeksi struktur proyek dan file terkait terlebih dahulu.
2. Pelajari pola navigasi, halaman, komponen UI, stylesheet, worker thread, service, dan error handling yang sudah digunakan.
3. Gunakan kembali pola dan komponen yang ada. Jangan membuat sistem duplikat.
4. Jangan menimpa atau menghapus fitur lain yang sudah berjalan.
5. Implementasikan langsung pada file proyek, bukan hanya memberikan snippet.
6. Gunakan PyMuPDF dan periksa API sesuai versi terpasang.
7. Pisahkan UI, geometri preview, service crop, dan background worker.
8. Pastikan konversi koordinat preview ke koordinat PDF akurat pada berbagai ukuran dan zoom.
9. Gunakan CropBox untuk versi awal dan jelaskan bahwa konten di luar area crop belum tentu terhapus permanen.
10. Jangan mengubah atau menghapus file sumber.
11. Jangan overwrite output tanpa konfirmasi.
12. Hindari refactor besar yang tidak diperlukan.

## Implementasi Wajib

- Halaman Crop PDF dengan Browse File dan drag-and-drop.
- Informasi nama file, ukuran, dan jumlah halaman.
- Preview halaman PDF.
- Navigasi halaman sebelumnya/berikutnya.
- Zoom in, zoom out, dan fit to page.
- Crop rectangle dengan handle pada sudut dan sisi.
- Drag untuk memindahkan area crop.
- Input margin Top, Bottom, Left, Right dalam mm.
- Sinkronisasi preview dan input manual.
- Tombol Reset Crop.
- Pilihan halaman saat ini, halaman tertentu/rentang, dan semua halaman.
- Penerapan margin yang sama secara fisik pada halaman dengan ukuran berbeda, disertai validasi.
- Nama dan lokasi output.
- Background processing dan progres.
- Penanganan error, pembatalan, dan perlindungan file sumber.
- Ringkasan hasil dan tombol membuka file/folder.
- Unit test untuk crop, geometri, koordinat, dan pemilihan halaman.
- Integrasi ke Home/navigasi mengikuti pola proyek.

## Visual

Gunakan light theme JackPDF dengan warna navy, biru, cyan, abu-abu, dan putih; font Segoe UI; kartu putih; border tipis; radius konsisten; dan tombol utama biru.

Gunakan aset ikon Crop JackPDF yang sudah disediakan: malaikat maut memotong sisi kertas menggunakan sabit. Jangan menambahkan tulisan ke gambar ikon. Buat garis crop dan handle pada preview jelas, tetapi tetap minimalis.

## Setelah Implementasi

- Jalankan unit test dan perbaiki error.
- Pastikan preview dan koordinat crop akurat.
- Uji halaman portrait, landscape, ukuran berbeda, dan rotasi.
- Pastikan halaman dapat dibuka dari Home/navigasi.
- Pastikan fitur lain tetap berjalan.
- Laporkan file yang dibuat/diubah, dependency, hasil test, dan keterbatasan CropBox.

Mulai dengan inspeksi repository, lalu implementasikan fitur secara menyeluruh. Jangan berhenti setelah membuat rencana.

---

**Kesimpulan:** Crop PDF JackPDF harus memberi pengguna kontrol visual untuk menentukan area potong, mendukung halaman tunggal maupun banyak halaman, menjaga file sumber tetap aman, dan menjelaskan perbedaan antara mengubah area tampilan (CropBox) dengan menghapus konten secara permanen.
