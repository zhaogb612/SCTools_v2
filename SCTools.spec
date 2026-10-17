# -*- mode: python ; coding: utf-8 -*-
# 平铺式 onedir：contents_directory='.' 使运行库/资源全部与 exe 同层（无 _internal）
from PyInstaller.building.datastruct import TOC

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources'), ('tools', 'tools')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter',
              # 未使用的 Qt 模块（网络走 urllib，无 QML/多媒体/PDF）
              'PySide6.QtNetwork', 'PySide6.QtQuick', 'PySide6.QtQml', 'PySide6.QtOpenGL',
              'PySide6.QtOpenGLWidgets', 'PySide6.QtMultimedia', 'PySide6.QtMultimediaWidgets',
              'PySide6.QtPdf', 'PySide6.QtPdfWidgets', 'PySide6.QtTest', 'PySide6.QtSql',
              'PySide6.QtHelp', 'PySide6.QtDesigner', 'PySide6.QtUiTools', 'PySide6.QtBluetooth',
              'PySide6.QtNfc', 'PySide6.QtSerialPort', 'PySide6.QtPositioning', 'PySide6.QtLocation',
              'PySide6.QtSensors', 'PySide6.QtWebSockets', 'PySide6.QtWebChannel',
              'PySide6.QtTextToSpeech', 'PySide6.QtCharts', 'PySide6.QtStateMachine',
              'PySide6.QtScxml', 'PySide6.QtRemoteObjects'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

# 丢弃无用的大体积二进制（binaries/datas 双通道过滤，tools/ 内的同名文件不受影响）：
# 软件 OpenGL 光栅器、Qt 多媒体自带 ffmpeg/SDL、以及未使用模块的 Qt 库
_DROP = ('opengl32sw', 'avcodec', 'avformat', 'avfilter', 'avutil',
         'swscale', 'swresample', 'sdl2',
         'pySide6/qt6quick', 'pySide6/qt6qml', 'pySide6/qt6network',
         'pySide6/qt6opengl', 'pySide6/qt6pdf', 'pySide6/qt6virtualkeyboard')


def _keep(toc):
    return TOC([b for b in toc
                if not any(d in b[0].lower().replace("\\", "/") for d in _DROP)])


a.binaries = _keep(a.binaries)
a.datas = _keep(a.datas)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SCTools2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/app.ico',
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SCTools2',
    contents_directory='.',
)
