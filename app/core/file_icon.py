# -*- coding: utf-8 -*-
"""应用文件图标提取：QFileIconProvider 取 exe 关联图标，磁盘缓存加速二次启动。
缓存放 %LOCALAPPDATA%/SCTools/icon_cache（Program Files 下 resources 不可写）"""
import hashlib
import os

from PySide6.QtCore import QFileInfo
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QFileIconProvider

CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                         "SCTools", "icon_cache")
_provider = None


def icon_for(path, size=32):
    """取文件关联图标；路径无效或提取失败返回 None"""
    global _provider
    if not path or not os.path.isfile(path):
        return None
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
    if ic.isNull():
        return None
    pm = ic.pixmap(size, size)
    if pm.isNull():
        return None
    try:
        pm.save(cache_png, "PNG")
    except OSError:
        pass
    return QIcon(pm)
