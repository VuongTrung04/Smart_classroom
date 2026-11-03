@echo off
REM Setup script for Smart Classroom
REM Tạo venv + cài dependencies

echo.
echo ======================================
echo  Smart Classroom - Setup
echo ======================================
echo.

REM Kiểm tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python không tìm thấy!
    echo Cài đặt Python 3.10, 3.11, hoặc 3.12 từ python.org
    echo ⚠️  Chọn "Add Python to PATH" khi cài
    pause
    exit /b 1
)

REM Kiểm tra version Python
for /f "tokens=2" %%i in ('python --version 2^>^&1') do (
    set PYTHON_VERSION=%%i
)
echo ✓ Python version: %PYTHON_VERSION%

REM Tạo venv
if not exist "venv" (
    echo.
    echo 📦 Tạo virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Lỗi tạo venv
        pause
        exit /b 1
    )
    echo ✓ venv tạo thành công
) else (
    echo ✓ venv đã tồn tại
)

REM Kích hoạt venv
echo.
echo 🔌 Kích hoạt venv...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ❌ Lỗi kích hoạt venv
    pause
    exit /b 1
)

REM Upgrade pip
echo.
echo 📦 Upgrade pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ⚠️  Cảnh báo: pip upgrade có lỗi, tiếp tục...
)

REM Cài dependencies
echo.
echo 📦 Cài dependencies từ requirements.txt...
echo (Điều này có thể mất 5-10 phút lần đầu...)
pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Lỗi cài dependencies!
    echo Thử chạy lại hoặc kiểm tra requirements.txt
    pause
    exit /b 1
)

REM Xong
echo.
echo ✅ Setup thành công!
echo.
echo 🚀 Để chạy ứng dụng:
echo    cd Smart_Classroom_03
echo    python main.py
echo.
echo Hoặc double-click: Smart_Classroom_03\run.bat
echo.
pause
