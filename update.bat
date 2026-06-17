@echo off
chcp 65001 >nul

set SERVER_IP=207.57.129.252
set SERVER_USER=root
set SERVER_PATH=/var/www/vbox
set SERVER_CODE_PATH=/opt/vbox/server

:: Parse numeric parameter
:: 1-Client, 2-Admin, 3-Server, 4-All
set TARGET=%1

:: If no parameter provided, show menu
if "%TARGET%"=="" goto :show_menu
goto :start_update

:show_menu
echo ================================
echo VBox Deployment Script
echo ================================
echo Please select an option:
echo   1 - Client only
echo   2 - Admin only
echo   3 - Server only
echo   4 - All
echo   0 - Exit
echo ================================
echo.
set /p TARGET="Enter option (1/2/3/4): "

if "%TARGET%"=="0" goto :exit_script
if "%TARGET%"=="" goto :show_menu
if "%TARGET%" neq "1" if "%TARGET%" neq "2" if "%TARGET%" neq "3" if "%TARGET%" neq "4" (
    echo ERROR: Invalid option!
    echo.
    goto :show_menu
)

echo.
echo Selected option: %TARGET%
echo.
pause

:start_update
echo ================================
echo Starting deployment...
echo ================================
echo.

:: Update Client (1 or 4)
if "%TARGET%"=="1" goto :client_only
if "%TARGET%"=="4" goto :update_all
goto :check_admin

:client_only
echo [Step 1] Building client...
cd client
call npm run build
if errorlevel 1 (
    echo ERROR: Client build failed!
    echo.
    goto :error_end
)
cd ..
echo OK: Client built

echo [Step 2] Uploading client...
scp -r client/dist/. %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/client/
if errorlevel 1 (
    echo ERROR: Client upload failed!
    echo.
    goto :error_end
)
echo OK: Client uploaded
echo.
goto :finish

:update_all
echo [Step 1/6] Building client...
cd client
call npm run build
if errorlevel 1 (
    echo ERROR: Client build failed!
    echo.
    goto :error_end
)
cd ..
echo OK: Client built

echo [Step 2/6] Uploading client...
scp -r client/dist/. %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/client/
if errorlevel 1 (
    echo ERROR: Client upload failed!
    echo.
    goto :error_end
)
echo OK: Client uploaded

:check_admin
:: Update Admin (2 or 4)
if "%TARGET%"=="2" goto :admin_only
if "%TARGET%"=="4" goto :update_admin
goto :update_server

:admin_only
echo [Step 1] Building admin...
cd admin
call npm run build
if errorlevel 1 (
    echo ERROR: Admin build failed!
    echo.
    goto :error_end
)
cd ..
echo OK: Admin built

echo [Step 2] Uploading admin...
scp -r admin/dist/. %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/admin/
if errorlevel 1 (
    echo ERROR: Admin upload failed!
    echo.
    goto :error_end
)
echo OK: Admin uploaded
echo.
goto :finish

:update_admin
echo [Step 3/6] Building admin...
cd admin
call npm run build
if errorlevel 1 (
    echo ERROR: Admin build failed!
    echo.
    goto :error_end
)
cd ..
echo OK: Admin built

echo [Step 4/6] Uploading admin...
scp -r admin/dist/. %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/admin/
if errorlevel 1 (
    echo ERROR: Admin upload failed!
    echo.
    goto :error_end
)
echo OK: Admin uploaded

:update_server
:: Update Server (3 or 4)
if "%TARGET%"=="3" goto :server_only
if "%TARGET%"=="4" goto :update_server_code

:server_only
echo [Step 1] Uploading server code...
goto :upload_server

:update_server_code
echo [Step 5/6] Uploading server code...

:upload_server
echo Preparing server files...

:: Create temporary directory
if exist ".temp_server_upload" rmdir /s /q ".temp_server_upload"
mkdir ".temp_server_upload"

:: Copy required directories
echo - Copying api...
xcopy "server\api" ".temp_server_upload\api" /E /I /Y >nul 2>&1

echo - Copying core...
xcopy "server\core" ".temp_server_upload\core" /E /I /Y >nul 2>&1

echo - Copying models...
xcopy "server\models" ".temp_server_upload\models" /E /I /Y >nul 2>&1

echo - Copying scripts...
xcopy "server\scripts" ".temp_server_upload\scripts" /E /I /Y >nul 2>&1

echo - Copying spiders...
xcopy "server\spiders" ".temp_server_upload\spiders" /E /I /Y >nul 2>&1

echo - Copying main files...
copy "server\main.py" ".temp_server_upload\" /Y >nul 2>&1
copy "server\requirements.txt" ".temp_server_upload\" /Y >nul 2>&1

:: Delete __pycache__ directories
for /d /r ".temp_server_upload" %%d in (__pycache__) do rmdir /s /q "%%d" 2>nul

:: Delete .pyc files
for /r ".temp_server_upload" %%f in (*.pyc) do del "%%f" 2>nul

echo Uploading server code...
scp -r ".temp_server_upload\*" %SERVER_USER%@%SERVER_IP%:%SERVER_CODE_PATH%/

:: Clean up
rmdir /s /q ".temp_server_upload" 2>nul

if errorlevel 1 (
    echo ERROR: Server upload failed!
    echo.
    goto :error_end
)
echo OK: Server uploaded

:: Restart server
echo Restarting server service...
ssh %SERVER_USER%@%SERVER_IP% "cd /opt/vbox/server && pkill -f 'python.*main.py' ; sleep 2 && nohup python main.py > logs/app.log 2>&1 &"
if errorlevel 1 (
    echo WARNING: Server restart may have failed.
) else (
    echo OK: Server restarted
)
echo.
goto :check_nginx

:check_nginx
if "%TARGET%"=="1" goto :finish
if "%TARGET%"=="2" goto :finish
if "%TARGET%"=="3" goto :finish

echo [Step 6/6] Refreshing Nginx cache...
ssh %SERVER_USER%@%SERVER_IP% "nginx -s reload"
if errorlevel 1 (
    echo WARNING: Nginx reload failed.
) else (
    echo OK: Nginx reloaded
)
echo.
goto :finish

:finish
echo ================================
echo Deployment completed!
echo ================================
echo URLs:
echo   Client: https://v-box.org
echo   Admin:  https://v-box.org/admin
echo   Server: http://207.57.129.252:8000
echo ================================
echo.
echo TIP: Press Ctrl+F5 to clear browser cache
echo.
echo ================================
echo Deployment finished successfully!
echo Press any key to exit...
echo ================================
pause >nul
goto :exit_script

:error_end
echo ================================
echo Deployment failed!
echo ================================
echo Please check the error messages above.
echo.
echo ================================
echo Press any key to exit...
echo ================================
pause >nul
goto :exit_script

:exit_script
endlocal
