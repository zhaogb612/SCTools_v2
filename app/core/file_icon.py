# -*- coding: utf-8 -*-
"""应用文件图标提取：QFileIconProvider 优先，取到通用默认图标时改用
ExtractIconExW 直接读 exe 图标资源；磁盘缓存加速二次启动。
缓存放 %LOCALAPPDATA%/SCTools/icon_cache（Program Files 下 resources 不可写）"""
import ctypes
import hashlib
import os
from ctypes import wintypes

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon, QImage, QPixmap
from PySide6.QtWidgets import QFileIconProvider

CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                         "SCTools", "icon_cache")
_provider = None
_generic_img = None  # 通用 exe 默认图标的基准图，用于识别"没取到真图标"

# 64 位句柄必须显式声明参数类型，否则 ctypes 默认按 32 位 int 传参溢出
_user32, _gdi32, _shell32 = ctypes.windll.user32, ctypes.windll.gdi32, ctypes.windll.shell32
_gdi32.GetObjectW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
_gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
_gdi32.SelectObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_gdi32.GetDIBits.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint,
                             ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
_gdi32.CreateCompatibleDC.argtypes = [ctypes.c_void_p]
_gdi32.DeleteDC.argtypes = [ctypes.c_void_p]
_user32.GetDC.argtypes = [ctypes.c_void_p]
_user32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_user32.DestroyIcon.argtypes = [ctypes.c_void_p]
_shell32.ExtractIconExW.argtypes = [ctypes.c_wchar_p, ctypes.c_int,
                                    ctypes.POINTER(ctypes.c_void_p),
                                    ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint]


def _generic_image():
    global _provider, _generic_img
    if _generic_img is None:
        if _provider is None:
            _provider = QFileIconProvider()
        ic = _provider.icon(QFileInfo(r"C:\__no_such_file__.exe"))
        _generic_img = ic.pixmap(32, 32).toImage()
    return _generic_img


def _hicon_to_qimage(hicon):
    """GetIconInfo+GetDIBits 读取 HICON 像素为 QImage（BGRA 原序对应 ARGB32_Premultiplied）"""

    class ICONINFO(ctypes.Structure):
        _fields_ = [("fIcon", wintypes.BOOL), ("xHotspot", wintypes.DWORD),
                    ("yHotspot", wintypes.DWORD), ("hbmMask", wintypes.HBITMAP),
                    ("hbmColor", wintypes.HBITMAP)]

    class BITMAP(ctypes.Structure):
        _fields_ = [("bmType", wintypes.LONG), ("bmWidth", wintypes.LONG),
                    ("bmHeight", wintypes.LONG), ("bmWidthBytes", wintypes.LONG),
                    ("bmPlanes", wintypes.WORD), ("bmBitsPixel", wintypes.WORD),
                    ("bmBits", ctypes.c_void_p)]

    class BMIH(ctypes.Structure):
        _fields_ = [("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
                    ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
                    ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                    ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
                    ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
                    ("biClrImportant", wintypes.DWORD)]

    user32, gdi32 = _user32, _gdi32
    user32.GetIconInfo.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    ii = ICONINFO()
    if not user32.GetIconInfo(hicon, ctypes.byref(ii)):
        return None
    try:
        if not ii.hbmColor:
            return None
        bm = BITMAP()
        if not gdi32.GetObjectW(ii.hbmColor, ctypes.sizeof(BITMAP), ctypes.byref(bm)):
            return None
        w, h = bm.bmWidth, bm.bmHeight
        if not (0 < w <= 256 and 0 < h <= 256):
            return None
        bmi = BMIH()
        bmi.biSize = ctypes.sizeof(BMIH)
        bmi.biWidth = w
        bmi.biHeight = -h          # top-down
        bmi.biPlanes = 1
        bmi.biBitCount = 32
        bmi.biCompression = 0      # BI_RGB
        buf = ctypes.create_string_buffer(w * h * 4)
        sdc = user32.GetDC(0)
        try:
            mdc = gdi32.CreateCompatibleDC(sdc)
            try:
                old = gdi32.SelectObject(mdc, ii.hbmColor)
                gdi32.GetDIBits(mdc, ii.hbmColor, 0, h, buf, ctypes.byref(bmi), 0)
                gdi32.SelectObject(mdc, old)
            finally:
                gdi32.DeleteDC(mdc)
        finally:
            user32.ReleaseDC(0, sdc)
        img = QImage(buf, w, h, w * 4, QImage.Format_ARGB32_Premultiplied)
        return img.copy()  # 脱离 buffer
    finally:
        if ii.hbmColor:
            gdi32.DeleteObject(ii.hbmColor)
        if ii.hbmMask:
            gdi32.DeleteObject(ii.hbmMask)


def _extract_resource_icon(path):
    """ExtractIconExW 提取 exe 内嵌第一个图标，成功返回 QIcon"""
    hicon = ctypes.c_void_p()
    n = _shell32.ExtractIconExW(path, 0, ctypes.byref(hicon), None, 1)
    if n <= 0 or not hicon.value:
        return None
    try:
        img = _hicon_to_qimage(hicon.value)
        if img is None or img.isNull() or img.width() < 8:
            return None
        return QIcon(QPixmap.fromImage(img))
    finally:
        _user32.DestroyIcon(hicon.value)


def _is_generic(pixmap):
    img = pixmap.toImage()
    g = _generic_image()
    return img.size() == g.size() and img == g


def icon_for(path, size=32):
    """取文件关联图标；路径无效或提取失败返回 None（调用方自行回退内置图标）"""
    global _provider
    if not path or not os.path.isfile(path):
        return None
    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return None  # 离屏模式下提取的是占位图标，不污染缓存
    try:
        mtime = int(os.path.getmtime(path))
    except OSError:
        mtime = 0
    key = hashlib.md5("{}|{}".format(
        os.path.normcase(os.path.abspath(path)), mtime).encode("utf-8")).hexdigest()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
    except OSError:
        pass
    cache_png = os.path.join(CACHE_DIR, key + ".png")
    if os.path.isfile(cache_png):
        pm = QPixmap(cache_png)
        if not pm.isNull():
            return QIcon(pm)
    if _provider is None:
        _provider = QFileIconProvider()
    ic = _provider.icon(QFileInfo(path))
    pm = ic.pixmap(size, size) if not ic.isNull() else QPixmap()
    if pm.isNull() or _is_generic(pm):
        # Provider 拿不到真图标（部分 exe/权限/清单原因），直接读内嵌图标资源
        ic2 = _extract_resource_icon(path)
        if ic2 is not None:
            ic = ic2
            pm = ic.pixmap(size, size)
    if pm.isNull():
        return None
    try:
        pm.save(cache_png, "PNG")
    except OSError:
        pass
    return QIcon(pm)
