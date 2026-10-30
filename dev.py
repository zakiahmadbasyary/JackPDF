"""
JackPDF Development Auto-Reload Runner
Menjalankan JackPDF dan otomatis me-restart aplikasi setiap kali ada file .py atau .qss yang disimpan.

Cara menjalankan:
    .venv\\Scripts\\python dev.py
"""
import os
import sys
import time
import subprocess

WATCH_DIRS = ["app", "assets"]
WATCH_EXTS = {".py", ".qss"}


def get_file_mtimes() -> dict:
    """Mengambil timestamp modifikasi terakhir dari seluruh file yang dipantau."""
    mtimes = {}
    for folder in WATCH_DIRS:
        if not os.path.exists(folder):
            continue
        for root, _, files in os.walk(folder):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in WATCH_EXTS:
                    full_path = os.path.join(root, file)
                    try:
                        mtimes[full_path] = os.path.getmtime(full_path)
                    except OSError:
                        pass
    if os.path.exists("main.py"):
        try:
            mtimes["main.py"] = os.path.getmtime("main.py")
        except OSError:
            pass
    return mtimes


def main():
    python_exe = sys.executable
    print("=" * 60)
    print("  JackPDF Auto-Reload Dev Server")
    print(f"  Python: {python_exe}")
    print(f"  Memantau folder: {', '.join(WATCH_DIRS)} dan main.py")
    print("  Tekan Ctrl+C di terminal ini untuk berhenti.")
    print("=" * 60)

    # Jalankan instance pertama main.py
    process = subprocess.Popen([python_exe, "main.py"])
    last_mtimes = get_file_mtimes()

    try:
        while True:
            time.sleep(0.5)

            # Jika aplikasi ditutup manual oleh user (klik tombol X jendela)
            if process.poll() is not None:
                print("\n[JackPDF Dev] Jendela aplikasi ditutup.")
                break

            current_mtimes = get_file_mtimes()
            changed_file = None

            for path, mtime in current_mtimes.items():
                if path not in last_mtimes or mtime > last_mtimes[path]:
                    changed_file = path
                    break

            if not changed_file and len(current_mtimes) != len(last_mtimes):
                changed_file = "struktur file/folder"

            if changed_file:
                fname = os.path.basename(changed_file) if changed_file != "struktur file/folder" else changed_file
                print(f"\n[JackPDF Dev] Perubahan terdeteksi pada '{fname}'. Me-restart aplikasi...")
                last_mtimes = current_mtimes

                # Tutup proses lama
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()

                time.sleep(0.2)
                # Mulai proses baru
                process = subprocess.Popen([python_exe, "main.py"])

    except KeyboardInterrupt:
        print("\n[JackPDF Dev] Auto-reload dihentikan.")
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()


if __name__ == "__main__":
    main()
