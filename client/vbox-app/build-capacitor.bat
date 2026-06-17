@echo off
echo 构建VBox TV Capacitor应用...

rem 构建Vue应用
echo 构建Vue应用...
cd ..\..
call npm run build
cd vbox-app

rem 同步到原生项目
echo 同步到原生项目...
call npm run sync

rem 打开Android项目
echo 打开Android项目...
call npm run android:open

echo 构建准备完成！请使用Android Studio完成最终构建。
pause
