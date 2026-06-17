@echo off
chcp 65001 >nul
echo ========================================
echo VBox Admin Startup
echo ========================================
echo.

REM ============================================
REM Step 0: Check and release port 3001
REM ============================================
echo Step 0: Checking admin port 3001...
netstat -ano | findstr ":3001 " | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo Port 3001 is available.
) else (
    echo Port 3001 is occupied, releasing...
    for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3001 " ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
    echo Port 3001 released.
)
echo.

REM ============================================
REM Step 1: Check node_modules
REM ============================================
echo Step 1: Checking dependencies...
if exist "node_modules\.bin\vite.cmd" (
    echo Dependencies found.
) else (
    echo WARNING: node_modules not found!
    echo Installing dependencies...
    call npm install
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies!
        pause
        exit /b 1
    )
)
echo.

REM ============================================
REM Step 2: Start admin dev server
REM ============================================
echo Step 2: Starting admin dev server...
echo Admin Dev: http://localhost:3001
echo.

echo ========================================
echo Admin is running!
echo Press Ctrl+C to stop
echo ========================================
echo.

npm run dev

pause
