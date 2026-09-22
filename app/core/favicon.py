# -*- coding: utf-8 -*-
"""网站 favicon 抓取：后台线程批量下载 域名/favicon.ico，缓存 %LOCALAPPDATA%/SCTools/icon_cache"""
import hashlib
import os
import urllib.parse
import urllib.request

from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QIcon, QImage, QPixmap

CACHE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                         "SCTools", "icon_cache")


def _cache_path(url):
    domain = urllib.parse.urlparse(url).netloc or url
    name = "fav_" + hashlib.md5(domain.encode("utf-8")).hexdigest() + ".png"
    return os.path.join(CACHE_DIR, name), domain


def load_cached(url):
    """命中缓存返回 QIcon，否则 None"""
    p, _ = _cache_path(url)
    if os.path.isfile(p):
        pm = QPixmap(p)
        if not pm.isNull():
            return QIcon(pm)
    return None


class FaviconWorker(QThread):
    """逐站点抓取 favicon（超时 4s，失败静默跳过用默认图标）"""
    one_done = Signal(str)   # 完成抓取的 url

    def __init__(self, urls, parent=None):
        super().__init__(parent)
        self._urls = [u for u in urls if not load_cached(u)]
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        for url in self._urls:
            if self._stop:
                break
            p, domain = _cache_path(url)
            try:
                os.makedirs(CACHE_DIR, exist_ok=True)
                req = urllib.request.Request(
                    "https://" + domain + "/favicon.ico",
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                data = urllib.request.urlopen(req, timeout=4).read()
                img = QImage.fromData(data)
                if not img.isNull() and img.width() >= 8:
                    img.scaled(32, 32).save(p, "PNG")
                    self.one_done.emit(url)
            except Exception:
                pass  # 网络不通/无 favicon，保持默认图标
