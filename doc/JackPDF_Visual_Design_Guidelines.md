# JackPDF — Visual Design Guidelines

Panduan ini menjadi acuan warna, tipografi, dan gaya visual antarmuka JackPDF agar konsisten dengan logo serta ikon fitur.

## 1. Arah Visual

**Karakter:** misterius, modern, minimalis, tegas, tetapi tetap nyaman digunakan.

Identitas JackPDF terinspirasi dari sosok malaikat maut bergaya siluet dengan topi, jubah, dan sabit. Unsur tersebut menjadi ciri khas visual, bukan alasan untuk membuat antarmuka terlihat seram atau terlalu ramai.

Prinsip:
- Cool and calm: dominasi biru, navy, abu-abu, dan putih.
- Minimalist: hindari ornamen gothic dan efek berlebihan pada halaman kerja.
- Consistent: gunakan bentuk, ikon, jarak, dan warna yang konsisten.
- Readable: utamakan keterbacaan dan hierarki informasi.
- Functional: visual membantu pengguna memahami fungsi.

## 2. Palet Warna

### Warna brand

| Token | HEX | Penggunaan |
|---|---|---|
| Navy 950 | `#071426` | Sidebar gelap dan branding |
| Navy 900 | `#0B1B33` | Area identitas dan panel gelap |
| Navy 800 | `#142B4D` | Panel sekunder dan hover gelap |
| Blue 700 | `#1557B0` | Tombol utama saat hover |
| Blue 600 | `#1D6FEA` | Aksen dan tombol utama |
| Blue 500 | `#278BFA` | Link, ikon aktif, highlight |
| Cyan 400 | `#45C7F5` | Aksen cahaya secukupnya |
| Blue 100 | `#DCEBFF` | Seleksi dan highlight lembut |

### Warna netral

| Token | HEX | Penggunaan |
|---|---|---|
| White | `#FFFFFF` | Kartu dan permukaan utama |
| Gray 50 | `#F7F9FC` | Latar aplikasi |
| Gray 100 | `#EEF2F7` | Latar input dan area sekunder |
| Gray 200 | `#DCE3EC` | Border dan divider |
| Gray 400 | `#98A6B8` | Placeholder dan ikon nonaktif |
| Gray 600 | `#5D6B7D` | Teks sekunder |
| Gray 800 | `#263445` | Teks utama |
| Gray 950 | `#111B29` | Teks dengan kontras tinggi |

### Warna status

| Status | HEX |
|---|---|
| Success | `#198754` |
| Warning | `#D99116` |
| Danger | `#D64545` |
| Info | `#278BFA` |

Warna status digunakan seperlunya. Merah bukan warna dominan JackPDF.

## 3. Aturan Penggunaan Warna

Gunakan **light theme sebagai tema utama**. Identitas navy dan biru hadir melalui sidebar, tombol, ikon, dan elemen branding.

- Latar aplikasi: `#F7F9FC`
- Sidebar: `#071426` atau `#0B1B33`
- Kartu dan panel kerja: `#FFFFFF`
- Judul: `#111B29`
- Teks deskripsi: `#5D6B7D`
- Tombol utama: `#1D6FEA`
- Hover tombol: `#1557B0`
- Border: `#DCE3EC`
- Fokus input: `#278BFA`
- Seleksi item: `#DCEBFF`

Gradien boleh digunakan pada logo, ilustrasi, atau highlight kecil. Hindari gradien pada semua kartu dan tombol.

## 4. Tipografi

### Font utama: Segoe UI

Gunakan **Segoe UI** karena cocok dengan lingkungan Windows, modern, dan mudah dibaca.

Fallback:
```css
font-family: "Segoe UI", "Arial", sans-serif;
```

Untuk PySide6, atur font global ke Segoe UI dan gunakan sans-serif sistem sebagai fallback.

### Skala tipografi

| Elemen | Ukuran | Weight |
|---|---:|---|
| Judul halaman | 24–28 px | Bold / 700 |
| Judul bagian | 17–20 px | Semibold / 600 |
| Judul kartu | 15–16 px | Semibold / 600 |
| Isi utama | 13–14 px | Normal / 400 |
| Label input | 12–13 px | Medium / 500 |
| Deskripsi/helper text | 11–12 px | Normal / 400 |
| Tooltip | 11–12 px | Normal / 400 |
| Tombol | 13–14 px | Semibold / 600 |

Aturan:
- Hindari penggunaan seluruh teks kapital.
- Jangan gunakan font horror, gothic, handwritten, atau decorative untuk UI.
- Gunakan bold untuk penekanan, bukan untuk semua teks.
- Pastikan teks nyaman dibaca pada skala Windows 100–150%.

## 5. Bentuk dan Komponen

| Elemen | Rekomendasi |
|---|---|
| Kartu | Radius 12–16 px |
| Tombol | Radius 8–10 px |
| Input | Radius 8 px |
| Dialog | Radius 12 px |
| Border | 1 px, abu-abu muda |
| Spacing | Kelipatan 4 atau 8 px |
| Padding kartu | 16–20 px |
| Tinggi tombol | 36–42 px |
| Tinggi input | 38–42 px |

Gunakan shadow yang sangat halus. Hindari bevel, efek 3D berlebihan, outline tebal, dan glow pada komponen UI biasa.

## 6. Gaya Ikon dan Ilustrasi

Ikon fitur mengikuti identitas logo JackPDF:
- Karakter malaikat maut berupa siluet gelap, dengan topi dan jubah.
- Sabit menjadi elemen khas sesuai konteks fitur.
- Latar menggunakan gradasi navy dan biru dengan cahaya bulan atau cyan yang lembut.
- Dokumen berwarna putih atau abu-abu terang agar kontras.
- Komposisi sederhana dan mudah dikenali pada ukuran kecil.
- Tidak ada tulisan di dalam gambar ikon fitur.
- Hindari darah, gore, tengkorak realistis, atau detail horor berlebihan.

### Konsep visual tiap fitur

| Fitur | Konsep |
|---|---|
| Merge PDF | Malaikat maut menarik beberapa lembar dokumen dan menyatukannya menjadi satu |
| Split PDF | Malaikat maut membelah satu lembar dokumen menggunakan sabit |
| Compress PDF | Malaikat maut memangkas atau mengurangi bagian dokumen dengan sabit hingga lebih ringkas |
| Convert to PNG | Malaikat maut mengubah dokumen menjadi gambar |
| Crop PDF | Malaikat maut memotong sisi dokumen menggunakan sabit |

Tampilkan ilustrasi dengan ukuran konsisten. Nama fitur dan deskripsi diletakkan sebagai teks UI terpisah, bukan bagian dari gambar.

## 7. Gaya Layout

- Sidebar sederhana dengan logo JackPDF di bagian atas.
- Home menampilkan kartu fitur berisi ikon, nama, dan deskripsi singkat.
- Halaman kerja memiliki judul, area pemilihan file, pengaturan, dan tombol aksi utama.
- Berikan ruang kosong yang cukup agar tampilan tidak padat.
- Gunakan satu tombol utama yang paling menonjol pada setiap halaman.
- Tambahkan tooltip pada tombol ikon, kontrol, dan elemen yang membutuhkan penjelasan.
- Gunakan dialog konfirmasi untuk tindakan yang berpotensi mengganti atau menghapus file.

## 8. Design Tokens

```css
:root {
  --color-navy-950: #071426;
  --color-navy-900: #0B1B33;
  --color-navy-800: #142B4D;
  --color-blue-700: #1557B0;
  --color-blue-600: #1D6FEA;
  --color-blue-500: #278BFA;
  --color-cyan-400: #45C7F5;
  --color-blue-100: #DCEBFF;

  --color-white: #FFFFFF;
  --color-gray-50: #F7F9FC;
  --color-gray-100: #EEF2F7;
  --color-gray-200: #DCE3EC;
  --color-gray-400: #98A6B8;
  --color-gray-600: #5D6B7D;
  --color-gray-800: #263445;
  --color-gray-950: #111B29;

  --color-success: #198754;
  --color-warning: #D99116;
  --color-danger: #D64545;
  --color-info: #278BFA;

  --font-family: "Segoe UI", Arial, sans-serif;
  --font-size-body: 14px;
  --font-size-small: 12px;
  --font-size-page-title: 26px;

  --radius-card: 14px;
  --radius-button: 9px;
  --radius-input: 8px;
  --border-width: 1px;
}
```

## 9. Hal yang Harus Dihindari

- Merah sebagai warna utama seluruh aplikasi.
- Font horror atau gothic untuk teks antarmuka.
- Semua panel berwarna gelap sehingga aplikasi terasa berat.
- Terlalu banyak efek glow, gradient, tekstur, atau ornamen.
- Ilustrasi fitur dengan gaya yang berbeda-beda.
- Tulisan di dalam ikon fitur.
- Ikon terlalu detail sehingga tidak terbaca pada ukuran kecil.
- Mengorbankan kontras teks demi tampilan visual.

## 10. Prompt Acuan Pengembangan UI

> Rancang antarmuka desktop JackPDF menggunakan PySide6 dengan gaya modern, minimalis, dan elegan. Jadikan logo serta ikon fitur JackPDF sebagai referensi identitas visual. Gunakan palet navy, biru, cyan, abu-abu, dan putih dengan light theme sebagai tema utama. Gunakan Segoe UI, kartu putih dengan rounded corner, border abu-abu tipis, shadow halus, dan tombol utama berwarna biru. Pertahankan karakter Jack sebagai siluet misterius pada logo dan ilustrasi fitur, tetapi jangan memenuhi seluruh UI dengan ornamen gothic atau efek horor. Prioritaskan keterbacaan, konsistensi, kemudahan penggunaan, dan tampilan native yang nyaman di Windows. Jangan mengubah fungsi aplikasi ketika hanya diminta memperbaiki UI.

---

**Kesimpulan:** JackPDF harus terasa seperti aplikasi produktivitas Windows yang modern dan profesional, dengan identitas misterius Jack sebagai aksen visual yang khas—bukan aplikasi horor.
