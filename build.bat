@echo off
setlocal
cd /d "%~dp0"

set "PY=python"
where python >nul 2>nul
if errorlevel 1 (
    if exist "C:\Users\Z1321\AppData\Local\Programs\Python\Python313\python.exe" (
        set "PY=C:\Users\Z1321\AppData\Local\Programs\Python\Python313\python.exe"
    )
)

echo ============================================
echo  SCTools2 (PySide6, 平铺布局) 打包
echo ============================================
"%PY%" -m PyInstaller --noconfirm SCTools.spec
if errorlevel 1 goto :err

echo.
echo 完成：dist\SCTools2\SCTools2.exe
echo 结构：exe 与运行库/资源/tools 全部同层（无 _internal），可整体搬移
pause
exit /b 0

:err
echo.
echo 打包失败，请检查 PySide6 / pyinstaller 是否已安装。
pause
exit /b 1