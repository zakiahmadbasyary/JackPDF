@echo off

echo ========================================================
echo   JackPDF - Windows Executable and Installer Build
echo ========================================================
echo.

:: 1. Navigate to repository root
cd /d "%~dp0"
echo [1/6] Memeriksa direktori project: %CD%

:: 2. Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv tidak ditemukan!
    echo Silakan buat venv terlebih dahulu dengan: python -m venv .venv
    exit /b 1
)
echo [2/6] Mengaktifkan virtual environment .venv...
call .venv\Scripts\activate.bat

:: 3. Check PyInstaller
where pyinstaller >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] PyInstaller tidak ditemukan dalam virtual environment!
    echo Memasang PyInstaller...
    python -m pip install pyinstaller
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Gagal memasang PyInstaller.
        exit /b 1
    )
)
echo [3/6] PyInstaller terdeteksi.

:: 4. Clean old build, dist, and installer folders safely
echo [4/6] Membersihkan folder build, dist, dan installer lama...
if exist "build" (
    rmdir /s /q "build"
)
if exist "dist\JackPDF" (
    rmdir /s /q "dist\JackPDF"
)
if not exist "installer" (
    mkdir "installer"
)

:: Ensure icon exists
if not exist "assets\icons\jackpdf.ico" (
    echo [INFO] Menghasilkan assets\icons\jackpdf.ico dari logo.png...
    python -c "from PIL import Image; img = Image.open('assets/icons/logo.png'); img.save('assets/icons/jackpdf.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])"
)

:: 5. Run PyInstaller with JackPDF.spec
echo [5/6] Menjalankan PyInstaller dengan JackPDF.spec...
pyinstaller --noconfirm --clean JackPDF.spec

if %ERRORLEVEL% neq 0 (
    echo.
    echo ========================================================
    echo [ERROR] Proses packaging PyInstaller GAGAL!
    echo ========================================================
    exit /b %ERRORLEVEL%
)

echo [INFO] JackPDF.exe berhasil dibuat di: dist\JackPDF\JackPDF.exe

:: 6. Compile Inno Setup Installer
echo [6/6] Mencari Inno Setup compiler ISCC.exe...
set "ISCC_PATH="

where iscc >nul 2>nul
if %ERRORLEVEL% equ 0 (
    for /f "delims=" %%I in ('where iscc') do set "ISCC_PATH=%%I"
)

if "%ISCC_PATH%"=="" (
    if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    ) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
        set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
    )
)

if not "%ISCC_PATH%"=="" (
    echo [INFO] Inno Setup ditemukan di: "%ISCC_PATH%"
    echo [INFO] Mengompilasi installer JackPDF_Setup.exe...
    "%ISCC_PATH%" JackPDF.iss
    if not errorlevel 1 (
        echo.
        echo ========================================================
        echo [SUKSES LENGKAP]
        echo 1. Executable: %CD%\dist\JackPDF\JackPDF.exe
        echo 2. Installer : %CD%\installer\JackPDF_Setup.exe
        echo ========================================================
    ) else (
        echo [WARNING] Pembuatan installer gagal, tetapi JackPDF.exe tersedia di dist\JackPDF
    )
) else (
    echo [WARNING] Inno Setup ISCC.exe tidak ditemukan.
    echo Hanya JackPDF.exe yang dibuat di: %CD%\dist\JackPDF\JackPDF.exe
    echo Pasang Inno Setup 6 jika ingin membuat installer secara otomatis.
)

echo.
exit /b 0
