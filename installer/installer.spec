# -*- mode: python ; coding: utf-8 -*-
# 安装程序 spec：onefile，仅内嵌许可协议（载荷 zip 由 build 脚本拼接到 exe 尾部）
a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[('assets/license.txt', 'assets'), ('../resources/app.ico', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SC_Tools_Setup_tmp',
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
    icon='../resources/app.ico',
    uac_admin=True,
)
