@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0.."

echo [1/4] 检查主程序产物 dist\SCTools2...
if not exist "dist\SCTools2\SCTools2.exe" (
    echo 未找到主程序，请先运行 build.bat 打包主程序。
    pause & exit /b 1
)

echo [2/4] 生成载荷 payload.zip（压缩 dist\SCTools2）...
"C:\Users\Z1321\AppData\Local\Programs\Python\Python313\python.exe" installer\make_payload.py || goto :err

echo [3/4] 编译安装程序（onefile）...
cd installer
"C:\Users\Z1321\AppData\Local\Programs\Python\Python313\python.exe" -m PyInstaller --clean --noconfirm installer.spec || goto :err
cd ..

echo [4/4] 拼接载荷到安装器尾部，输出单文件安装包...
if exist "dist_installer\SC Tools安装程序.exe" del /q "dist_installer\SC Tools安装程序.exe"
copy /b "installer\dist\SC_Tools_Setup_tmp.exe" + "installer\assets\payload.zip" "dist_installer\SC Tools安装程序.exe" >nul || goto :err

echo.
echo 完成：dist_installer\SC Tools安装程序.exe（单文件，双击安装）
echo 卸载程序 uninstall.exe 由安装程序在安装时生成到安装目录。
pause
exit /b 0

:err
echo 安装程序构建失败。
pause
exit /b 1
