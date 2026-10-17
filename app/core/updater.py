# -*- coding: utf-8 -*-
"""自动更新：GitHub Releases 检查新版本 + 下载资产。
REPO 为 GitHub 仓库 owner/name；Release 资产上传安装包 exe（名字含"安装"或"Setup"）。"""
import json
import urllib.request

from PySide6.QtCore import QThread, Signal

from app.core import config

REPO = "zhaogb612/SCTools_v2"   # GitHub 仓库 owner/name，与 Release tag（形如 v3.0）对应
API = "https://api.github.com/repos/{}/releases/latest".format(REPO)
RELEASES_PAGE = "https://github.com/{}/releases/latest".format(REPO)
_UA = {"User-Agent": "SC-Tools-Updater"}


class UpdateError(OSError):
    pass


def _ver_parts(v):
    out = []
    for p in v.lstrip("vV").split("."):
        n = "".join(ch for ch in p if ch.isdigit())
        out.append(int(n) if n else 0)
    return out


def compare_ver(a, b):
    """a > b 返回 True；位数不齐按补零比较"""
    pa, pb = _ver_parts(a), _ver_parts(b)
    n = max(len(pa), len(pb))
    pa += [0] * (n - len(pa))
    pb += [0] * (n - len(pb))
    return pa > pb


def fetch_latest(timeout=8):
    """查询最新 Release。有新版本返回 dict，已是最新返回 None，网络错误抛 UpdateError"""
    try:
        req = urllib.request.Request(API, headers=_UA)
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    except Exception as e:
        raise UpdateError("无法连接更新服务器：{}".format(e))
    tag = data.get("tag_name", "")
    if not tag or not compare_ver(tag, config.APP_VER):
        return None
    asset = None
    for a in data.get("assets", []):
        name = a.get("name", "")
        if name.endswith(".exe") and ("安装" in name or "Setup" in name or "setup" in name):
            asset = a
            break
    return {
        "version": tag,
        "notes": data.get("body") or "",
        "asset_name": asset["name"] if asset else "",
        "asset_url": asset["browser_download_url"] if asset else "",
        "asset_size": asset.get("size", 0) if asset else 0,
        "page": RELEASES_PAGE,
    }


def download(url, dest, progress_cb=None, timeout=15):
    """流式下载到 dest，progress_cb(已下载字节, 总字节)"""
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if progress_cb:
                progress_cb(got, total)
    return dest


class FnThread(QThread):
    """通用后台任务线程：done 结果 / fail 错误信息"""
    done = Signal(object)
    fail = Signal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn())
        except Exception as e:
            self.fail.emit(str(e))
