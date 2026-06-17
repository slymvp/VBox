@echo off
chcp 65001 >nul
echo ========================================
echo VBox Server Startup
echo ========================================
echo.

REM ============================================
REM Find Python
REM ============================================
set PYTHON_PATH=

if exist "D:\python\Python314\python.exe" (
    set PYTHON_PATH=D:\python\Python314\python.exe
    goto :found_python
)
if exist "C:\Python314\python.exe" (
    set PYTHON_PATH=C:\Python314\python.exe
    goto :found_python
)
if exist "C:\Python313\python.exe" (
    set PYTHON_PATH=C:\Python313\python.exe
    goto :found_python
)
if exist "C:\Python312\python.exe" (
    set PYTHON_PATH=C:\Python312\python.exe
    goto :found_python
)
if exist "C:\Python311\python.exe" (
    set PYTHON_PATH=C:\Python311\python.exe
    goto :found_python
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_PATH=py
    goto :found_python
)

python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_PATH=python
    goto :found_python
)

python3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_PATH=python3
    goto :found_python
)

echo ERROR: Python not found!
echo Please install Python 3.12+ and add it to PATH
echo Download: https://www.python.org/downloads/
pause
exit /b 1

:found_python
echo Using Python: %PYTHON_PATH%
%PYTHON_PATH% --version
echo.

REM ============================================
REM Step 0a: Check and release port 8000 (Backend)
REM ============================================
echo Step 0a: Checking backend port 8000...
netstat -ano | findstr ":8000 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo Port 8000 is available.
) else (
    echo Port 8000 is occupied, releasing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
    echo Port 8000 released.
)
echo.

REM ============================================
REM Step 0c: Check admin port 3001
REM ============================================
echo Step 0c: Checking admin port 3001...
set ADMIN_RUNNING=0
netstat -ano | findstr ":3001 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo Admin is not running.
) else (
    set ADMIN_RUNNING=1
    echo Admin is already running on port 3001.
)
echo.

REM ============================================
REM Step 1: Check database
REM ============================================
echo Step 1: Checking database...
if exist "vbox.db" (
    echo Database exists
) else if exist "..\vbox.db" (
    echo Database exists
) else (
    echo WARNING: Database not found
    echo The database will be created automatically when the server starts.
)
echo.

REM ============================================
REM Step 2: Start admin if not running
REM ============================================
if "%ADMIN_RUNNING%"=="0" (
    echo Step 2: Starting admin dev server...
    if exist "..\admin\node_modules\.bin\vite.cmd" (
        start "VBox Admin" cmd /c "cd /d ..\admin && npm run dev"
        echo Admin starting on http://localhost:3001
        timeout /t 2 /nobreak >nul
    ) else (
        echo WARNING: Admin node_modules not found.
        echo Run 'cd admin ^&^& npm install' first.
    )
) else (
    echo Step 2: Admin already running, skipping.
)
echo.

REM ============================================
REM Step 3: Start backend API server
REM ============================================
echo Step 3: Starting backend API server...
echo Backend API:  http://localhost:8000
echo Admin Dev:    http://localhost:3001
echo.

echo ========================================
echo Server is running!
echo Press Ctrl+C to stop backend
echo (Close admin window separately)
echo ========================================
echo.

%PYTHON_PATH% api/app.py

pause
