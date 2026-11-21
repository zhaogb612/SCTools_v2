# -*- coding: utf-8 -*-
"""自动更新：GitHub Releases 检查新版本 + 下载资产。
资产分两类——安装版（.exe，交给安装器静默覆盖）与绿色版（.zip，解压覆盖当前目录）；
下载默认多连接 Range 分块加速，服务端不支持分块时自动回退单连接流式下载。"""
import json
import os
import sys
import threading
import urllib.request

from PySide6.QtCore import QThread, Signal

from app.core import config

REPO = "zhaogb612/SCTools_v2"   # GitHub 仓库 owner/name，与 Release tag（形如 v3.2）对应
API = "https://api.github.com/repos/{}/releases/latest".format(REPO)
RELEASES_PAGE = "https://github.com/{}/releases/latest".format(REPO)
_UA = {"User-Agent": "SC-Tools-Updater"}

CONNS = 6             # 分块下载连接数
_CHUNK = 1 << 20      # 单连接读取块（1MB，降低磁盘与小文件下载开销）
_MIN_PART = 8 << 20   # 小于 8MB 的文件不值得分块
UNINST_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\SCTools2"

# GitHub 下载镜像（直连失败时依次回退；前缀式代理，如 gh-proxy.com/https://github.com/…）
MIRRORS = ("https://gh-proxy.com/", "https://ghfast.top/",
           "https://github.moeyy.xyz/")

LABELS = {
    "installer": "安装版（自动覆盖安装并重启）",
    "portable": "绿色版（免安装，自动解压覆盖）",
    "portable7z": "绿色版 7z 压缩包（下载后手动解压）",
}


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


def _asset_kind(name):
    n = (name or "").lower()
    if n.endswith(".exe"):
        return "installer"
    if n.endswith(".zip"):
        return "portable"
    if n.endswith(".7z"):
        return "portable7z"
    return ""


def fetch_latest(timeout=12):
    """查询最新 Release。有新版本返回 dict（含候选资产列表），已是最新返回 None，网络错误抛 UpdateError"""
    try:
        req = urllib.request.Request(API, headers=_UA)
        data = json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))
    except Exception as e:
        raise UpdateError("无法连接更新服务器：{}".format(e))
    tag = data.get("tag_name", "")
    if not tag or not compare_ver(tag, config.APP_VER):
        return None
    raw = data.get("assets", [])
    has_zip = any((a.get("name") or "").lower().endswith(".zip") for a in raw)
    assets = []
    for a in raw:
        name = a.get("name") or ""
        kind = _asset_kind(name)
        if not kind or (kind == "portable7z" and has_zip):
            continue      # 同时提供了 zip 时不再重复列出 7z
        assets.append({"name": name, "url": a.get("browser_download_url", ""),
                       "size": a.get("size", 0), "kind": kind, "label": LABELS[kind]})
    assets.sort(key=lambda x: 0 if x["kind"] == "installer" else 1)
    return {"version": tag, "notes": data.get("body") or "",
            "page": RELEASES_PAGE, "assets": assets}


def running_is_installed():
    """当前是否运行于「安装版」目录：注册表 InstallLocation 与本程序所在目录一致"""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return False
    try:
        import winreg
    except ImportError:
        return False
    here = os.path.normcase(os.path.dirname(os.path.abspath(sys.executable)))
    for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(hive, UNINST_KEY) as k:
                d = winreg.QueryValueEx(k, "InstallLocation")[0]
        except OSError:
            continue
        if d and os.path.normcase(os.path.normpath(d)) == here:
            return True
    return False


def _open(url, headers=None, timeout=60):
    h = dict(_UA)
    if headers:
        h.update(headers)
    return urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=timeout)


def _probe(url, timeout=60):
    """探测服务端是否支持 Range 分块，返回 (总字节, 可分块)"""
    try:
        with _open(url, {"Range": "bytes=0-0"}, timeout) as r:
            cr = r.headers.get("Content-Range") or ""
            total = int(cr.rsplit("/", 1)[-1]) if "/" in cr else 0
            return total, (r.status == 206 and total > 0)
    except Exception:
        return 0, False


def _part_paths(dest, n):
    return ["{}.part{}".format(dest, i) for i in range(n)]


def _drop_parts(dest, n=CONNS):
    for p in _part_paths(dest, n) + [dest]:
        try:
            os.remove(p)
        except OSError:
            pass


def _mirror_url(url, mirror):
    """镜像前缀式代理拼接：仅对 github.com 资源生效，其它源原样返回"""
    for p in ("https://github.com/", "http://github.com/"):
        if url.startswith(p):
            rest = url[len(p):]
            return mirror + "https://github.com/" + rest
    return None


def download(url, dest, progress_cb=None, timeout=60, conns=CONNS):
    """下载 url 到 dest；progress_cb(已下载字节, 总字节)。
    直连失败时自动依次回退 GitHub 镜像；所有源都失败才抛 UpdateError"""
    candidates = [url]
    for m in MIRRORS:
        u = _mirror_url(url, m)
        if u:
            candidates.append(u)
    last = None
    for u in candidates:
        try:
            return _download_one(u, dest, progress_cb, timeout, conns)
        except Exception as e:
            last = e
            _drop_parts(dest, conns)   # 清理残留 part 文件再试下一源
    raise UpdateError("所有下载源均失败：{}".format(last))


def _download_one(url, dest, progress_cb, timeout, conns):
    """单源下载：可分块时多连接加速，否则单连接"""
    total, multi = _probe(url, timeout)
    if multi and total >= _MIN_PART:
        try:
            return _download_parts(url, dest, total, conns, progress_cb, timeout)
        except Exception:
            _drop_parts(dest, conns)      # 分块失败清残留，改单连接重来
    return _download_single(url, dest, progress_cb, timeout)


def _download_single(url, dest, progress_cb=None, timeout=60):
    with _open(url, timeout=timeout) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(_CHUNK)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if progress_cb:
                progress_cb(got, total)
    return dest


def _download_parts(url, dest, total, conns, progress_cb, timeout):
    """各连接写独立 part 文件，全部完成后按序合并为完整文件"""
    step = total // conns + 1
    parts = _part_paths(dest, conns)
    lock = threading.Lock()
    state = {"got": 0}
    errors = []

    def worker(i):
        start = i * step
        if start >= total:            # 该段为空，占位即可
            open(parts[i], "wb").close()
            return
        end = min(start + step - 1, total - 1)
        try:
            with _open(url, {"Range": "bytes={}-{}".format(start, end)}, timeout) as r, \
                    open(parts[i], "wb") as f:
                while True:
                    chunk = r.read(_CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    with lock:
                        state["got"] += len(chunk)
                        got = state["got"]
                    if progress_cb:
                        progress_cb(got, total)
        except Exception as e:
            with lock:
                errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,), daemon=True) for i in range(conns)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    if errors:
        raise UpdateError(errors[0])
    with open(dest, "wb") as out:
        for p in parts:
            with open(p, "rb") as f:
                while True:
                    chunk = f.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
    for p in parts:
        try:
            os.remove(p)
        except OSError:
            pass
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
