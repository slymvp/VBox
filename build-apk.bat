@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ============================================================
rem  VBox APK Build Script
rem  支持移动端和TV端打包
rem ============================================================

set "PROJECT_ROOT=%~dp0"
set "CLIENT_DIR=%PROJECT_ROOT%client"
set "CAP_DIR=%CLIENT_DIR%\vbox-app"
set "ANDROID_DIR=%CAP_DIR%\android"
set "APK_SRC=%ANDROID_DIR%\app\build\outputs\apk\debug\app-debug.apk"
set "DESKTOP=%USERPROFILE%\Desktop"

rem ============================================================
rem  显示菜单
rem ============================================================
:show_menu
echo.
echo  ========================================
echo    VBox APK Build Script
echo  ========================================
echo.
echo  请选择要打包的版本:
echo    1 - 移动端 (Mobile)
echo    2 - TV端 (TV)
echo    3 - 全部 (All)
echo    0 - 退出
echo.
echo  ========================================
echo.
set /p CHOICE="请输入选项 (1/2/3/0): "

if "%CHOICE%"=="0" goto :exit
if "%CHOICE%"=="1" goto :build_mobile
if "%CHOICE%"=="2" goto :build_tv
if "%CHOICE%"=="3" goto :build_all

echo.
echo  [ERROR] 无效的选项，请重新选择！
echo.
goto :show_menu

rem ============================================================
rem  构建移动端
rem ============================================================
:build_mobile
echo.
echo  ========================================
echo    开始构建移动端 APK...
echo  ========================================
echo.

rem 配置移动端参数
set "APP_ID=com.vbox.mobile"
set "APP_NAME=VBox"

rem 更新 Capacitor 配置
echo [1/5] 更新 Capacitor 配置...
call :update_capacitor_config "%APP_ID%" "%APP_NAME%" "mobile"
if %errorlevel% neq 0 (
    echo [ERROR] 配置更新失败！
    goto :fail
)

rem 构建前端（使用移动端生产环境变量）
echo [2/5] 构建前端代码...
cd /d "%CLIENT_DIR%"
call npm run build:mobile
if %errorlevel% neq 0 (
    echo [ERROR] 前端构建失败！
    goto :fail
)

rem 复制构建产物到 Capacitor 目录
echo [3/5] 复制构建产物到 Capacitor 目录...
if exist "%CAP_DIR%\dist" rmdir /s /q "%CAP_DIR%\dist"
xcopy "%CLIENT_DIR%\dist" "%CAP_DIR%\dist" /E /I /Y
if %errorlevel% neq 0 (
    echo [ERROR] 复制构建产物失败！
    goto :fail
)

rem 同步到 Capacitor
echo [4/5] 同步到 Capacitor...
cd /d "%CAP_DIR%"
call npx cap sync android
if %errorlevel% neq 0 (
    echo [ERROR] 同步失败！
    goto :fail
)

rem 构建 APK
echo [5/5] 构建 Android APK...
cd /d "%ANDROID_DIR%"
call gradlew.bat --stop >nul 2>&1
call gradlew.bat clean assembleDebug
if %errorlevel% neq 0 (
    echo [ERROR] APK 构建失败！
    goto :fail
)

rem 复制 APK
echo [5/5] 复制 APK 到桌面...
call :copy_apk "VBoxMobile"
if %errorlevel% neq 0 (
    echo [ERROR] APK 复制失败！
    goto :fail
)

echo.
echo  ========================================
echo    移动端 APK 构建成功！
echo  ========================================
echo.
goto :finish

rem ============================================================
rem  构建 TV 端
rem ============================================================
:build_tv
echo.
echo  ========================================
echo    开始构建 TV 端 APK...
echo  ========================================
echo.

rem 配置 TV 端参数
set "APP_ID=com.vbox.tv"
set "APP_NAME=VBox"

rem 更新 Capacitor 配置
echo [1/5] 更新 Capacitor 配置...
call :update_capacitor_config "%APP_ID%" "%APP_NAME%" "tv"
if %errorlevel% neq 0 (
    echo [ERROR] 配置更新失败！
    goto :fail
)

rem 构建前端（使用TV端生产环境变量）
echo [2/5] 构建前端代码...
cd /d "%CLIENT_DIR%"
call npm run build:tv
if %errorlevel% neq 0 (
    echo [ERROR] 前端构建失败！
    goto :fail
)

rem 复制构建产物到 Capacitor 目录
echo [3/5] 复制构建产物到 Capacitor 目录...
if exist "%CAP_DIR%\dist" rmdir /s /q "%CAP_DIR%\dist"
xcopy "%CLIENT_DIR%\dist" "%CAP_DIR%\dist" /E /I /Y
if %errorlevel% neq 0 (
    echo [ERROR] 复制构建产物失败！
    goto :fail
)

rem 同步到 Capacitor
echo [4/5] 同步到 Capacitor...
cd /d "%CAP_DIR%"
call npx cap sync android
if %errorlevel% neq 0 (
    echo [ERROR] 同步失败！
    goto :fail
)

rem 构建 APK
echo [5/5] 构建 Android APK...
cd /d "%ANDROID_DIR%"
call gradlew.bat --stop >nul 2>&1
call gradlew.bat clean assembleDebug
if %errorlevel% neq 0 (
    echo [ERROR] APK 构建失败！
    goto :fail
)

rem 复制 APK
echo [5/5] 复制 APK 到桌面...
call :copy_apk "VBoxTV"
if %errorlevel% neq 0 (
    echo [ERROR] APK 复制失败！
    goto :fail
)

echo.
echo  ========================================
echo    TV 端 APK 构建成功！
echo  ========================================
echo.
goto :finish

rem ============================================================
rem  构建全部
rem ============================================================
:build_all
echo.
echo  ========================================
echo    开始构建全部版本...
echo  ========================================
echo.

rem 构建移动端
echo.
echo  [步骤 1/2] 构建移动端...
call :build_mobile_internal
if %errorlevel% neq 0 (
    echo [ERROR] 移动端构建失败！
    goto :fail
)

rem 构建 TV 端
echo.
echo  [步骤 2/2] 构建 TV 端...
call :build_tv_internal
if %errorlevel% neq 0 (
    echo [ERROR] TV 端构建失败！
    goto :fail
)

echo.
echo  ========================================
echo    全部版本构建成功！
echo  ========================================
echo.
goto :finish

rem ============================================================
rem  内部构建函数
rem ============================================================
:build_mobile_internal
set "APP_ID=com.vbox.mobile"
set "APP_NAME=VBox"
call :update_capacitor_config "%APP_ID%" "%APP_NAME%" "mobile"
if %errorlevel% neq 0 exit /b 1

cd /d "%CLIENT_DIR%"
call npm run build:mobile
if %errorlevel% neq 0 exit /b 1

cd /d "%CAP_DIR%"
call npx cap sync android
if %errorlevel% neq 0 exit /b 1

cd /d "%ANDROID_DIR%"
call gradlew.bat --stop >nul 2>&1
call gradlew.bat clean assembleDebug
if %errorlevel% neq 0 exit /b 1

call :copy_apk "VBoxMobile"
exit /b 0

:build_tv_internal
set "APP_ID=com.vbox.tv"
set "APP_NAME=VBox"
call :update_capacitor_config "%APP_ID%" "%APP_NAME%" "tv"
if %errorlevel% neq 0 exit /b 1

cd /d "%CLIENT_DIR%"
call npm run build:tv
if %errorlevel% neq 0 exit /b 1

cd /d "%CAP_DIR%"
call npx cap sync android
if %errorlevel% neq 0 exit /b 1

cd /d "%ANDROID_DIR%"
call gradlew.bat --stop >nul 2>&1
call gradlew.bat clean assembleDebug
if %errorlevel% neq 0 exit /b 1

call :copy_apk "VBoxTV"
exit /b 0

rem ============================================================
rem  更新 Capacitor 配置
rem ============================================================
:update_capacitor_config
set "APP_ID=%~1"
set "APP_NAME=%~2"
set "PLATFORM=%~3"

rem 创建临时配置文件
set "CONFIG_FILE=%CAP_DIR%\capacitor.config.ts"

echo import type { CapacitorConfig } from '@capacitor/cli'; > "%CONFIG_FILE%"
echo. >> "%CONFIG_FILE%"
echo const config: CapacitorConfig = { >> "%CONFIG_FILE%"
echo   appId: '%APP_ID%', >> "%CONFIG_FILE%"
echo   appName: '%APP_NAME%', >> "%CONFIG_FILE%"
echo   webDir: 'dist' >> "%CONFIG_FILE%"
echo }; >> "%CONFIG_FILE%"
echo. >> "%CONFIG_FILE%"
echo export default config; >> "%CONFIG_FILE%"

rem 注意：不再覆盖 .env 文件，使用已配置好的 .env.*.production 文件
rem 构建命令会自动使用对应的 production 环境配置

exit /b 0

rem ============================================================
rem  复制 APK
rem ============================================================
:copy_apk
set "PREFIX=%~1"

if not exist "%APK_SRC%" (
    echo [ERROR] APK 文件不存在: %APK_SRC%
    exit /b 1
)

rem 生成日期字符串
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value') do set "dt=%%i"
set "DATE_STR=!dt:~4,4!!dt:~8,2!!dt:~10,2!"

rem 复制 APK
set "APK_DEST=%DESKTOP%\%PREFIX%-debug-!DATE_STR!.apk"
copy /Y "%APK_SRC%" "!APK_DEST!" >nul
if %errorlevel% neq 0 (
    echo [ERROR] APK 复制失败！
    exit /b 1
)

echo APK 已复制到: !APK_DEST!
exit /b 0

rem ============================================================
rem  结束
rem ============================================================
:finish
echo.
echo  ========================================
echo    构建完成！
echo  ========================================
echo.
pause
exit /b 0

:fail
echo.
echo  ========================================
echo    构建失败！请检查上面的错误信息。
echo  ========================================
echo.
pause
exit /b 1

:exit
echo.
echo  退出构建脚本。
echo.
pause
exit /b 0
