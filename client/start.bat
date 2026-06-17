@echo off
chcp 65001 >nul
cls

echo.
echo ===============================================
echo         VBox Client Launcher v1.0
echo ===============================================
echo.
echo Please select launch mode:
echo.
echo    1. PC Development
echo    2. Mobile Development  
echo    3. TV Development
echo.
echo ===============================================
echo.

set /p choice=Enter your choice (1/2/3): 

if "%choice%"=="1" (
    echo.
    echo Starting PC Development Mode...
    echo.
    npm run dev
) else if "%choice%"=="2" (
    echo.
    echo Starting Mobile Development Mode...
    echo.
    npm run dev:mobile
) else if "%choice%"=="3" (
    echo.
    echo Starting TV Development Mode...
    echo.
    npm run dev:tv
) else (
    echo.
    echo Invalid choice! Please enter 1, 2 or 3
    echo.
    pause
    goto :eof
)