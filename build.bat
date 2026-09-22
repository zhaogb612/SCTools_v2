@echo off
chcp 65001 >nul
echo 打包 SCTools2 (PySide6, 平铺布局)...
pyinstaller --noconfirm SCTools.spec
if errorlevel 1 goto :err

echo.
echo 完成：dist\SCTools2\SCTools2.exe
echo 结构：exe 与运行库/资源/tools 全部同层（无 _internal），可整体搬移
pause
exit /b 0

:err
echo 打包失败，请检查 PySide6 / pyinstaller 是否已安装。
pause
