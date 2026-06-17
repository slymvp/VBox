@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

set SERVER_IP=207.57.129.252
set SERVER_USER=root
set SERVER_PATH=/var/www/vbox
set NGINX_CONF_PATH=/etc/nginx/sites-available/vbox

echo ================================
echo VBox Full Deployment Script
echo ================================
echo.

echo 1. Checking build files...
if not exist "client\dist" (
    echo Error: client\dist not found. Run: cd client && npm run build
    pause
    exit /b 1
)

if not exist "admin\dist" (
    echo Error: admin\dist not found. Run: cd admin && npm run build
    pause
    exit /b 1
)
echo OK: Build files checked

echo.
echo 2. Creating server directories...
ssh %SERVER_USER%@%SERVER_IP% "mkdir -p %SERVER_PATH%/{client,admin}"
echo OK: Directories created

echo.
echo 3. Uploading client...
scp -r client\dist\* %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/client/
echo OK: Client uploaded

echo.
echo 4. Uploading admin...
scp -r admin\dist\* %SERVER_USER%@%SERVER_IP%:%SERVER_PATH%/admin/
echo OK: Admin uploaded

echo.
echo 5. Uploading Nginx config...
scp vbox-nginx.conf %SERVER_USER%@%SERVER_IP%:%NGINX_CONF_PATH%
echo OK: Nginx config uploaded

echo.
echo 6. Configuring Nginx...
ssh %SERVER_USER%@%SERVER_IP% "ln -sf /etc/nginx/sites-available/vbox /etc/nginx/sites-enabled/vbox && nginx -t && systemctl restart nginx"
echo OK: Nginx configured

echo.
echo ================================
echo Deployment completed!
echo ================================
echo URLs:
echo   Client: http://v-box.org
echo   Admin: http://v-box.org/admin
echo ================================
echo.
echo Note:
echo 1. Clear browser cache (Ctrl+F5)
echo 2. Check logs: tail -f /var/log/nginx/vbox-error.log
echo 3. Ensure backend is running on 207.57.129.252:8000
echo.

pause