# -*- coding: utf-8 -*-
"""SCTools2 安装/卸载程序（单文件双职能）：
- 安装模式：许可协议 -> 安装位置/附加任务 -> 解压内嵌载荷 -> 快捷方式 + 注册表卸载项 -> 生成 uninstall.exe
- 卸载模式：参数 --uninstall 或本程序被命名为 uninstall.exe 时触发；删除文件/快捷方式/注册表项
界面与主程序同风格：无边框、直角、主色标题栏 + 浅色内容区
"""
import os
import shutil
import subprocess
import sys
import time
import zipfile

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (QApplication, QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
                               QStackedWidget, QTextEdit, QVBoxLayout, QWidget)

APP_NAME = "SCTools2"
APP_VER = "3.1"
EXE_NAME = "SCTools2.exe"
UNINSTALL_NAME = "uninstall.exe"
REG_PARENT = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
REG_KEY = "SCTools2"
BRAND = "#89C2FF"          # 主色（标题栏），与主程序晴空蓝一致
BG = "#E6F7FF"             # 辅色（内容区）
DEFAULT_DIR = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), APP_NAME)
START_MENU_DIR = os.path.join(os.environ["APPDATA"],
                              r"Microsoft\Windows\Start Menu\Programs", APP_NAME)


def resolve_install_target(path):
    """把用户选定的目录规范化为真正的安装目录：自动在其下创建 APP_NAME 子目录。

    选中 C:\\Software 装到 C:\\Software\\SCTools2，避免程序文件直接铺进所选目录
    （否则卸载会清空该目录原有文件）。若所选目录本身已是 SCTools2（覆盖更新、
    或用户已选到程序目录）则原样返回，不会套成 SCTools2\\SCTools2。
    """
    p = os.path.normpath(os.path.abspath(path.strip()))
    if os.path.basename(p).lower() == APP_NAME.lower():
        return p
    return os.path.join(p, APP_NAME)

FONT = '"Microsoft YaHei UI", "Microsoft YaHei", sans-serif'


def payload_path():
    """载荷 zip 直接拼接在安装器 exe 尾部（copy /b），zipfile 能从 PE 尾部定位"""
    if getattr(sys, "frozen", False):
        return sys.executable
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "payload.zip")


def license_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "license.txt")


def icon_path():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "app.ico")


QSS = """
* {{ font-family: {font}; outline: none; }}
QWidget#Root {{ background: {bg}; }}
QFrame#Page {{ background: {bg}; }}
QFrame#TitleBar {{ background: {brand}; }}
QFrame#TitleBar QLabel {{ background: transparent; color: {on_brand}; }}
QLabel#Step {{ color: {on_brand}; font-size: 12px; }}
QPushButton#Close {{
    background: transparent; border: none; color: {on_brand};
    font-size: 14px; padding: 4px 14px;
}}
QPushButton#Close:hover {{ background: rgba(0,0,0,40); }}
/* 仿 Mac 三色圆点（与主程序标题栏一致） */
QPushButton#MacClose {{ background:#ff5f57; border:none; border-radius:5px; }}
QPushButton#MacClose:hover {{ background:#e0443e; }}
QPushButton#MacMin {{ background:#febc2e; border:none; border-radius:5px; }}
QPushButton#MacMin:hover {{ background:#e0a51f; }}
QPushButton#MacMax {{ background:#28c840; border:none; border-radius:5px; }}
QPushButton#MacMax:hover {{ background:#1fa833; }}
QLabel {{ color: #2A2F36; background: transparent; }}
QLabel#Title {{ font-size: 15px; font-weight: bold; }}
QLabel#BarName {{ font-size: 13px; font-weight: bold; }}
QTextEdit {{ background: #FFFFFF; border: 1px solid #C9D6DE; color: #2A2F36; padding: 6px; }}
QLineEdit {{
    background: #FFFFFF; border: 1px solid #C9D6DE; padding: 5px 8px; color: #2A2F36;
}}
QPushButton {{
    background: #FFFFFF; border: 1px solid #C9D6DE; color: #2A2F36;
    padding: 6px 18px; font-size: 12px;
}}
QPushButton:hover {{ border-color: {brand_dark}; color: {brand_dark}; }}
QPushButton#Accent {{ background: {brand_dark}; color: #FFFFFF; border: none; font-weight: bold; }}
QPushButton#Accent:hover {{ background: {brand_hover}; }}
QPushButton#Accent:disabled {{ background: #B9C6CE; color: #FFFFFF; }}
QProgressBar {{
    background: #FFFFFF; border: 1px solid #C9D6DE; height: 18px; text-align: center;
    color: #2A2F36; font-size: 11px;
}}
QProgressBar::chunk {{ background: {brand_dark}; }}
QCheckBox {{ color: #2A2F36; spacing: 6px; }}
""".format(font=FONT, brand=BRAND, brand_dark="#5FA8DC", brand_hover="#7CB8E8",
           on_brand="#173247", bg=BG)


def kill_running_app():
    subprocess.run(["taskkill", "/f", "/im", EXE_NAME],
                   creationflags=0x08000000, capture_output=True)


def _payload_span(fpath):
    """定位 exe 尾部内嵌 zip 的起始偏移，返回 (start, file_size)；找不到返回 None"""
    import struct
    size = os.path.getsize(fpath)
    with open(fpath, "rb") as f:
        f.seek(max(0, size - (65536 + 22)))
        tail = f.read()
    i = tail.rfind(b"PK\x05\x06")          # End of Central Directory
    if i < 0 or len(tail) - i < 22:
        return None
    cd_size, cd_off = struct.unpack("<II", tail[i + 12:i + 20])
    start = (size - len(tail) + i) - cd_size - cd_off
    if 0 <= start < size:
        return start, size
    return None


def make_uninstall(dest):
    """生成卸载程序：复制安装器 exe 但截掉尾部载荷 zip（卸载用不到，省 ~318MB）。
    onefile 的 bootloader+CArchive 在载荷之前，截断不影响卸载模式运行。"""
    span = _payload_span(sys.executable) if getattr(sys, "frozen", False) else None
    if not span:
        shutil.copy2(sys.executable, dest)   # 开发环境：payload 在 assets/，exe 本身就不含载荷
        return
    start, _total = span
    with open(sys.executable, "rb") as a, open(dest, "wb") as b:
        remaining = start
        while remaining > 0:
            chunk = a.read(min(1 << 20, remaining))
            if not chunk:
                break
            b.write(chunk)
            remaining -= len(chunk)


def make_shortcut(lnk_path, target, workdir, desc):
    ps = ("$ws = New-Object -ComObject WScript.Shell; "
          "$s = $ws.CreateShortcut('{lnk}'); "
          "$s.TargetPath = '{tgt}'; $s.WorkingDirectory = '{wd}'; "
          "$s.Description = '{desc}'; $s.IconLocation = '{tgt},0'; $s.Save()").format(
        lnk=lnk_path, tgt=target, wd=workdir, desc=desc)
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   creationflags=0x08000000, capture_output=True)


def desktop_dir():
    return os.path.join(os.environ["USERPROFILE"], "Desktop")


def _reg_values(install_dir):
    exe_path = os.path.join(install_dir, EXE_NAME)
    total_kb = 0
    for root, _dirs, files in os.walk(install_dir):
        for f in files:
            try:
                total_kb += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return [
        ("DisplayName", APP_NAME),
        ("DisplayVersion", APP_VER),
        ("DisplayIcon", exe_path),
        ("UninstallString", '"{}" --uninstall'.format(os.path.join(install_dir, UNINSTALL_NAME))),
        ("InstallLocation", install_dir),
        ("Publisher", "沙尘612"),
        ("NoModify", 1),
        ("NoRepair", 1),
        ("EstimatedSize", total_kb // 1024),
    ]


def write_registry(install_dir):
    """写 HKLM（安装器带管理员清单，优先全局卸载项，卸载中心必显示）；无权限时回退 HKCU。
    返回实际写入的 hive 名（"HKLM"/"HKCU"），全部失败返回 None"""
    import winreg
    key_path = REG_PARENT + "\\" + REG_KEY
    values = _reg_values(install_dir)
    for root, hive in ((winreg.HKEY_LOCAL_MACHINE, "HKLM"),
                       (winreg.HKEY_CURRENT_USER, "HKCU")):
        try:
            with winreg.CreateKey(root, key_path) as k:
                for name, val in values:
                    if name in ("NoModify", "NoRepair", "EstimatedSize"):
                        winreg.SetValueEx(k, name, 0, winreg.REG_DWORD, val)
                    else:
                        winreg.SetValueEx(k, name, 0, winreg.REG_SZ, val)
            return hive
        except OSError:
            continue
    return None


def delete_registry():
    """HKLM/HKCU 两处都尝试删除（兼容旧版只写 HKCU 的安装）"""
    import winreg
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            winreg.DeleteKey(root, REG_PARENT + "\\" + REG_KEY)
        except OSError:
            pass


def read_install_dir_from_registry():
    import winreg
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, REG_PARENT + "\\" + REG_KEY) as k:
                v, _ = winreg.QueryValueEx(k, "InstallLocation")
                if v:
                    return v
        except OSError:
            continue
    return ""


def read_installed_version():
    import winreg
    for root in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
        try:
            with winreg.OpenKey(root, REG_PARENT + "\\" + REG_KEY) as k:
                return winreg.QueryValueEx(k, "DisplayVersion")[0]
        except OSError:
            continue
    return ""


def detect_existing_install():
    """返回 (已安装目录, 已安装版本)；未安装返回 ("", "")"""
    d = read_install_dir_from_registry()
    if d and os.path.isfile(os.path.join(d, EXE_NAME)):
        return os.path.normpath(d), read_installed_version()
    return "", ""


class InstallThread(QThread):
    progress = Signal(int, str)   # 百分比, 当前文件
    done = Signal(bool, str)      # 成功, 消息

    def __init__(self, zip_path, target, keep_config=False):
        super().__init__()
        self._zip = zip_path
        self._target = target
        self._keep_config = keep_config   # 覆盖更新时保留用户配置（tools/nav/skin.json）

    def run(self):
        try:
            os.makedirs(self._target, exist_ok=True)
            skipped = 0
            with zipfile.ZipFile(self._zip) as z:
                names = z.namelist()
                total = len(names)
                for i, name in enumerate(names):
                    arc = name.replace("\\", "/")
                    if self._keep_config and arc.startswith("resources/config/"):
                        skipped += 1   # 不覆盖用户已生成的配置
                        continue
                    z.extract(name, self._target)
                    if i % 20 == 0:
                        self.progress.emit(int(i * 100 / max(1, total)), name)
                self.progress.emit(100, "完成")
            self.done.emit(True, "跳过用户配置 {} 项".format(skipped) if skipped else "")
        except Exception as e:
            self.done.emit(False, str(e))


class TitleBar(QFrame):
    """仿 Mac 标题栏：图标 + 名称，右侧红/黄/绿三色圆点（关闭/最小化/最大化），可拖动"""

    def __init__(self, window):
        super().__init__()
        self._win = window
        self.setObjectName("TitleBar")
        self.setFixedHeight(38)
        bl = QHBoxLayout(self)
        bl.setContentsMargins(12, 0, 12, 0)
        bl.setSpacing(6)
        icon_lbl = QLabel()
        icon_lbl.setStyleSheet("background: transparent;")
        icon = QIcon(icon_path())
        if not icon.isNull():
            icon_lbl.setPixmap(icon.pixmap(18, 18))
        bl.addWidget(icon_lbl)
        name = QLabel(APP_NAME + " 安装程序")
        name.setObjectName("BarName")
        bl.addWidget(name)
        bl.addStretch()

        def circle(name, tooltip):
            b = QPushButton()
            b.setObjectName(name)
            b.setToolTip(tooltip)
            b.setFixedSize(11, 11)
            b.setCursor(Qt.PointingHandCursor)
            return b

        self.btn_close = circle("MacClose", "关闭")
        self.btn_min = circle("MacMin", "最小化")
        self.btn_max = circle("MacMax", "最大化/还原")
        self.btn_close.clicked.connect(window.close)
        self.btn_min.clicked.connect(window.showMinimized)
        self.btn_max.clicked.connect(self._toggle_max)
        for b in (self.btn_close, self.btn_min, self.btn_max):
            bl.addWidget(b)
        self._normal_geom = None

    def _toggle_max(self):
        w = self._win
        if w.isMaximized() or (w.windowState() & Qt.WindowMaximized):
            w.setWindowState(w.windowState() & ~Qt.WindowMaximized)
            w.showNormal()
            if self._normal_geom is not None and self._normal_geom.width() > 0:
                w.setGeometry(self._normal_geom)
        else:
            self._normal_geom = w.geometry()
            w.showMaximized()

    def mouseDoubleClickEvent(self, _):
        self._toggle_max()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            child = self.childAt(e.position().toPoint())
            if child is None or isinstance(child, QLabel):
                self._win.windowHandle().startSystemMove()
        super().mousePressEvent(e)


class InstallerWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle(APP_NAME + " 安装程序")
        self.setWindowFlag(Qt.FramelessWindowHint)
        ic = QIcon(icon_path())
        if not ic.isNull():
            self.setWindowIcon(ic)
        self.setMinimumSize(560, 430)
        self.resize(560, 430)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(TitleBar(self))

        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)
        self._install_dir = ""
        self._thread = None
        self._existing_dir, self._existing_ver = detect_existing_install()

        self._build_license_page()
        self._build_option_page()
        self._build_progress_page()
        self._build_finish_page()
        self._stack.setCurrentIndex(0)

    # -- 页面构建 -----------------------------------------------------------
    def _page_frame(self):
        f = QFrame()
        f.setObjectName("Page")
        v = QVBoxLayout(f)
        v.setContentsMargins(24, 18, 24, 18)
        v.setSpacing(12)
        return f, v

    def _nav_row(self, back=None, next_text="下一步", next_slot=None, enabled=True):
        row = QHBoxLayout()
        row.addStretch()
        if back is not None:
            b = QPushButton("上一步")
            b.clicked.connect(back)
            row.addWidget(b)
        nb = QPushButton(next_text)
        nb.setObjectName("Accent")
        nb.setCursor(Qt.PointingHandCursor)
        nb.setEnabled(enabled)
        if next_slot:
            nb.clicked.connect(next_slot)
        row.addWidget(nb)
        return row, nb

    def _build_license_page(self):
        f, v = self._page_frame()
        t = QLabel("许可协议与免责声明")
        t.setObjectName("Title")
        v.addWidget(t)
        tip = QLabel("安装前请阅读以下协议。继续安装即表示您同意协议全部内容。")
        tip.setStyleSheet("color:#5A6772; font-size:11px;")
        v.addWidget(tip)
        box = QTextEdit()
        box.setReadOnly(True)
        try:
            box.setPlainText(open(license_path(), "r", encoding="utf-8").read())
        except OSError:
            box.setPlainText("（许可协议文件缺失）")
        v.addWidget(box, 1)
        self._agree = QCheckBox("我已阅读并同意本协议")
        self._agree.toggled.connect(lambda on: self._agree_btn.setEnabled(on))
        v.addWidget(self._agree)
        row, self._agree_btn = self._nav_row(
            next_slot=lambda: self._stack.setCurrentIndex(1), enabled=False)
        v.addLayout(row)
        self._stack.addWidget(f)

    def _build_option_page(self):
        f, v = self._page_frame()
        t = QLabel("选择安装位置")
        t.setObjectName("Title")
        v.addWidget(t)
        if self._existing_dir:
            d = QLabel("检测到已安装 {} v{}（{}）。\n将继续以覆盖更新方式安装：程序文件将更新，用户配置（工具/导航/主题设置）保留。"
                       .format(APP_NAME, self._existing_ver or "?", self._existing_dir))
            d.setStyleSheet("color:#1B6B34; font-size:11px;")
            self._dir_edit = QLineEdit(self._existing_dir)
        else:
            d = QLabel("默认安装到系统程序目录 {}（需管理员权限）。\n选择其他位置时，将自动在其下创建 {} 文件夹。"
                       "卸载时将删除该目录全部文件。".format(DEFAULT_DIR, APP_NAME))
            d.setStyleSheet("color:#5A6772; font-size:11px;")
            self._dir_edit = QLineEdit(DEFAULT_DIR)
        d.setWordWrap(True)
        v.addWidget(d)
        row = QHBoxLayout()
        row.addWidget(self._dir_edit, 1)
        browse = QPushButton("浏览...")
        browse.clicked.connect(self._browse)
        row.addWidget(browse)
        v.addLayout(row)

        t2 = QLabel("附加任务")
        t2.setObjectName("Title")
        v.addWidget(t2)
        self._chk_desktop = QCheckBox("创建桌面快捷方式")
        self._chk_desktop.setChecked(True)
        self._chk_menu = QCheckBox("创建开始菜单快捷方式")
        self._chk_menu.setChecked(True)
        v.addWidget(self._chk_desktop)
        v.addWidget(self._chk_menu)
        v.addStretch()

        def back():
            self._stack.setCurrentIndex(0)

        row, _ = self._nav_row(back=back, next_text="安装", next_slot=self._start_install)
        v.addLayout(row)
        self._stack.addWidget(f)

    def _build_progress_page(self):
        f, v = self._page_frame()
        t = QLabel("正在安装")
        t.setObjectName("Title")
        v.addWidget(t)
        self._prog = QProgressBar()
        v.addWidget(self._prog)
        self._prog_label = QLabel("准备中...")
        self._prog_label.setStyleSheet("color:#5A6772; font-size:11px;")
        v.addWidget(self._prog_label)
        v.addStretch()
        self._stack.addWidget(f)

    def _build_finish_page(self):
        f, v = self._page_frame()
        t = QLabel("安装完成")
        t.setObjectName("Title")
        v.addWidget(t)
        d = QLabel("{} {} 已安装到：".format(APP_NAME, APP_VER))
        v.addWidget(d)
        self._final_dir = QLabel("")
        self._final_dir.setWordWrap(True)
        self._final_dir.setStyleSheet("color:#5A6772; font-size:11px;")
        v.addWidget(self._final_dir)
        self._reg_status = QLabel("")
        self._reg_status.setWordWrap(True)
        v.addWidget(self._reg_status)
        self._chk_run = QCheckBox("立即运行 {}".format(APP_NAME))
        self._chk_run.setChecked(True)
        v.addWidget(self._chk_run)
        tip = QLabel("卸载：开始菜单搜索卸载，或运行安装目录内 uninstall.exe")
        tip.setStyleSheet("color:#5A6772; font-size:11px;")
        v.addWidget(tip)
        v.addStretch()
        row, _ = self._nav_row(next_text="完成", next_slot=self._finish)
        v.addLayout(row)
        self._stack.addWidget(f)

    # -- 动作 ---------------------------------------------------------------
    def _browse(self):
        d = QFileDialog.getExistingDirectory(self, "选择安装位置", self._dir_edit.text())
        if d:
            # 选中父目录时自动补一层 APP_NAME 子目录，安装时再自动创建该文件夹
            self._dir_edit.setText(resolve_install_target(d))

    def _start_install(self):
        raw = self._dir_edit.text().strip()
        if not raw:
            QMessageBox.warning(self, "无效路径", "请选择一个具体的安装目录。")
            return
        # 手输路径同样规范化，保证始终装在独立的 APP_NAME 目录下
        target = resolve_install_target(raw)
        self._dir_edit.setText(target)
        drive = os.path.splitdrive(target)[0]
        if drive and not os.path.exists(drive + "\\"):
            QMessageBox.warning(self, "路径无效", "磁盘 {} 不存在。".format(drive))
            return
        is_update = (self._existing_dir
                     and os.path.normpath(target).lower() == self._existing_dir.lower())
        if not is_update and os.path.isdir(target) and os.listdir(target):
            r = QMessageBox.question(
                self, "目录非空",
                "目标目录已存在且包含文件，继续安装将覆盖同名文件。\n是否继续？")
            if r != QMessageBox.Yes:
                return
        # 覆盖更新：结束正在运行的程序，否则主程序 exe 被占用无法覆盖
        kill_running_app()
        self._install_dir = target
        self._stack.setCurrentIndex(2)
        self._thread = InstallThread(payload_path(), target, keep_config=is_update)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_done)
        self._thread.start()

    def _on_progress(self, pct, name):
        self._prog.setValue(pct)
        self._prog_label.setText("解压：{}".format(name))

    def _on_done(self, ok, msg):
        if not ok:
            QMessageBox.critical(self, "安装失败", "解压失败：\n" + msg)
            self.close()
            return
        d = self._install_dir
        exe_path = os.path.join(d, EXE_NAME)
        # 生成卸载程序 + 注册表（结果明确告知用户，避免静默失败）
        hive = None
        try:
            make_uninstall(os.path.join(d, UNINSTALL_NAME))
        except OSError as e:
            QMessageBox.warning(self, "警告", "卸载程序写入失败：\n" + str(e))
        try:
            hive = write_registry(d)
        except Exception as e:
            QMessageBox.warning(self, "警告", "注册表写入失败：\n" + str(e))
        if hive == "HKLM":
            self._reg_status.setText("已注册系统级卸载信息（HKLM），可在「设置-应用」和卸载工具中看到本程序。")
            self._reg_status.setStyleSheet("color:#1B6B34; font-size:11px;")
        elif hive == "HKCU":
            self._reg_status.setText("已注册当前用户卸载信息（HKCU）。如需所有用户可见，请以管理员身份重新安装。")
            self._reg_status.setStyleSheet("color:#8A4B00; font-size:11px;")
        else:
            self._reg_status.setText("警告：卸载信息注册失败，控制面板不会显示卸载项！")
            self._reg_status.setStyleSheet("color:#B02020; font-size:11px; font-weight:bold;")
        # 快捷方式
        if self._chk_desktop.isChecked():
            make_shortcut(os.path.join(desktop_dir(), APP_NAME + ".lnk"),
                          exe_path, d, APP_NAME)
        if self._chk_menu.isChecked():
            os.makedirs(START_MENU_DIR, exist_ok=True)
            make_shortcut(os.path.join(START_MENU_DIR, APP_NAME + ".lnk"),
                          exe_path, d, APP_NAME)
            make_shortcut(os.path.join(START_MENU_DIR, "卸载 " + APP_NAME + ".lnk"),
                          os.path.join(d, UNINSTALL_NAME), d, "卸载 " + APP_NAME)
        self._final_dir.setText(d)
        self._stack.setCurrentIndex(3)

    def _finish(self):
        if self._chk_run.isChecked():
            exe = os.path.join(self._install_dir, EXE_NAME)
            if os.path.exists(exe):
                subprocess.Popen([exe], cwd=self._install_dir)
        self.close()


class UninstallThread(QThread):
    """逐文件删除安装目录（跳过自身 exe），删除进度实时回报"""
    progress = Signal(int, str)
    done = Signal(list)

    def __init__(self, target, self_path):
        super().__init__()
        self._target = target
        self._self = self_path

    def _remove(self, path, failed):
        """删文件；被占用则先结束同名进程再重试，仍失败记入 failed"""
        for attempt in range(3):
            try:
                os.remove(path)
                return
            except OSError:
                name = os.path.basename(path)
                if name.lower().endswith(".exe"):
                    subprocess.run(["taskkill", "/f", "/im", name],
                                   creationflags=0x08000000, capture_output=True)
                time.sleep(0.3 * (attempt + 1))
        failed.append(path)

    def run(self):
        target = self._target
        files = []
        for root, _dirs, fs in os.walk(target):
            for f in fs:
                files.append(os.path.join(root, f))
        total = max(1, len(files))
        failed = []
        for i, p in enumerate(files):
            if os.path.normpath(p) != os.path.normpath(self._self):
                self._remove(p, failed)
            if i % 15 == 0:
                self.progress.emit(int(i * 100 / total), os.path.basename(p))
        # 自底向上清空目录结构（删不掉的目录留给延迟批处理兜底）
        for root, dirs, _fs in os.walk(target, topdown=False):
            for d in dirs:
                try:
                    os.rmdir(os.path.join(root, d))
                except OSError:
                    pass
        try:
            os.rmdir(target)
        except OSError:
            pass
        self.progress.emit(100, "完成")
        self.done.emit(failed)


class UninstallWindow(QWidget):
    """卸载程序：与安装器同风格（无边框、主色标题栏 + Mac 圆点、直角按钮）"""

    def __init__(self):
        super().__init__()
        self.setObjectName("Root")
        self.setWindowTitle("卸载 " + APP_NAME)
        self.setWindowFlag(Qt.FramelessWindowHint)
        ic = QIcon(icon_path())
        if not ic.isNull():
            self.setWindowIcon(ic)
        self.setFixedSize(460, 280)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(TitleBar(self))

        self._target = read_install_dir_from_registry() or \
            os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                            else __file__))
        # 注册表指向的目录若已失效（旧版残留），回退到卸载程序所在目录
        here = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False)
                                               else __file__))
        if not os.path.isfile(os.path.join(self._target, EXE_NAME)):
            self._target = here

        f = QFrame()
        f.setObjectName("Page")
        v = QVBoxLayout(f)
        v.setContentsMargins(24, 18, 24, 18)
        v.setSpacing(12)
        self._stack = QStackedWidget()
        root.addWidget(self._stack, 1)

        # 确认页
        t = QLabel("卸载 " + APP_NAME)
        t.setObjectName("Title")
        v.addWidget(t)
        d = QLabel("{} {} 已安装到：".format(APP_NAME, APP_VER))
        v.addWidget(d)
        loc = QLabel(self._target)
        loc.setWordWrap(True)
        loc.setStyleSheet("color:#5A6772; font-size:11px;")
        v.addWidget(loc)
        warn = QLabel("卸载将删除安装目录内的全部文件、快捷方式与注册表信息。\n"
                      "目录内的个人配置与文件也将一并删除，请先备份。")
        warn.setWordWrap(True)
        warn.setStyleSheet("color:#8A4B00; font-size:11px;")
        v.addWidget(warn)
        v.addStretch()
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.close)
        row.addWidget(cancel)
        self._go = QPushButton("卸载")
        self._go.setObjectName("Accent")
        self._go.setCursor(Qt.PointingHandCursor)
        self._go.clicked.connect(self._do_uninstall)
        row.addWidget(self._go)
        v.addLayout(row)
        self._stack.addWidget(f)

        # 进行中页
        f2 = QFrame()
        f2.setObjectName("Page")
        v2 = QVBoxLayout(f2)
        v2.setContentsMargins(24, 18, 24, 18)
        v2.setSpacing(12)
        t2 = QLabel("正在卸载")
        t2.setObjectName("Title")
        v2.addWidget(t2)
        self._prog = QProgressBar()
        self._prog.setRange(0, 0)
        v2.addWidget(self._prog)
        self._prog_label = QLabel("正在移除文件与注册表信息...")
        self._prog_label.setStyleSheet("color:#5A6772; font-size:11px;")
        v2.addWidget(self._prog_label)
        v2.addStretch()
        self._stack.addWidget(f2)

        # 完成页
        f3 = QFrame()
        f3.setObjectName("Page")
        v3 = QVBoxLayout(f3)
        v3.setContentsMargins(24, 18, 24, 18)
        v3.setSpacing(12)
        t3 = QLabel("卸载完成")
        t3.setObjectName("Title")
        v3.addWidget(t3)
        d3 = QLabel("{} 已从本机移除。".format(APP_NAME))
        v3.addWidget(d3)
        v3.addStretch()
        row3 = QHBoxLayout()
        row3.addStretch()
        done = QPushButton("完成")
        done.setObjectName("Accent")
        done.setCursor(Qt.PointingHandCursor)
        done.clicked.connect(self.close)
        row3.addWidget(done)
        v3.addLayout(row3)
        self._stack.addWidget(f3)

        self._stack.setCurrentIndex(0)

    def _do_uninstall(self):
        self._go.setEnabled(False)
        self._stack.setCurrentIndex(1)
        target = self._target
        kill_running_app()
        delete_registry()
        # 快捷方式 + 开始菜单目录
        for lnk in (os.path.join(desktop_dir(), APP_NAME + ".lnk"),
                    os.path.join(START_MENU_DIR, APP_NAME + ".lnk"),
                    os.path.join(START_MENU_DIR, "卸载 " + APP_NAME + ".lnk")):
            try:
                os.remove(lnk)
            except OSError:
                pass
        shutil.rmtree(START_MENU_DIR, ignore_errors=True)
        # 后台线程删文件；自身 exe 被占用，退出后由延迟命令补删
        self_exe = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
        self._thread = UninstallThread(target, self_exe)
        self._thread.progress.connect(self._on_uninstall_progress)
        self._thread.done.connect(self._on_uninstall_done)
        self._thread.start()

    def _on_uninstall_progress(self, pct, name):
        self._prog_label.setText("删除：{}".format(name))
        self._prog.setValue(pct)

    def _on_uninstall_done(self, failed):
        target = self._target
        self_exe = os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__)
        # 兜底改为 TEMP 下的批处理（绕开 cmd /c 引号嵌套解析坑）：等本进程退出后
        # 强删残留文件与整个安装目录，最后批处理自删。cwd 设 TEMP 避免占住目标目录。
        try:
            bat = os.path.join(os.environ.get("TEMP", "."), "sctools_uninstall_cleanup.bat")
            with open(bat, "w", encoding="mbcs", errors="replace") as f:
                f.write("@echo off\n")
                f.write("ping -n 5 127.0.0.1 >nul\n")
                for p in failed:
                    f.write('del /f /q "{}"\n'.format(p))
                f.write('del /f /q "{}"\n'.format(self_exe))
                f.write('rd /s /q "{}"\n'.format(target))
                f.write('del /f /q "%~f0"\n')
            subprocess.Popen(["cmd", "/c", bat],
                             cwd=os.environ.get("TEMP", "."),
                             creationflags=0x08000000 | subprocess.CREATE_NEW_PROCESS_GROUP,
                             close_fds=True)
        except OSError:
            pass
        # 残留诊断日志
        try:
            log = os.path.join(os.environ.get("TEMP", "."), "sctools_uninstall.log")
            with open(log, "w", encoding="utf-8") as f:
                f.write("target={}\nfailed={}:\n".format(target, len(failed)))
                for p in failed:
                    f.write(p + "\n")
        except OSError:
            pass
        if failed:
            self._prog_label.setText("部分文件被占用，将在退出后自动清除")
        self._stack.setCurrentIndex(2)


def run_uninstall():
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = UninstallWindow()
    w.show()
    sys.exit(app.exec())


def run_silent():
    """静默安装/覆盖更新（--silent 或 /S）：无界面，自动定位已装目录，
    结束运行中的程序、保留用户配置，完成后启动新版本。供自动更新链调用。
    退出码：0 成功 / 1 解压等 IO 失败 / 2 卸载信息注册失败"""
    target = read_install_dir_from_registry()
    if not target or not os.path.isfile(os.path.join(target, EXE_NAME)):
        target = DEFAULT_DIR
    target = os.path.normpath(target)
    try:
        kill_running_app()
        os.makedirs(target, exist_ok=True)
        keep = os.path.isfile(os.path.join(target, "resources", "config", "tools.json"))
        with zipfile.ZipFile(payload_path()) as z:
            for name in z.namelist():
                if keep and name.replace("\\", "/").startswith("resources/config/"):
                    continue
                z.extract(name, target)
        make_uninstall(os.path.join(target, UNINSTALL_NAME))
    except Exception:
        sys.exit(1)
    hive = write_registry(target)
    exe_path = os.path.join(target, EXE_NAME)
    if os.path.isdir(desktop_dir()):
        make_shortcut(os.path.join(desktop_dir(), APP_NAME + ".lnk"),
                      exe_path, target, APP_NAME)
    os.makedirs(START_MENU_DIR, exist_ok=True)
    make_shortcut(os.path.join(START_MENU_DIR, APP_NAME + ".lnk"),
                  exe_path, target, APP_NAME)
    make_shortcut(os.path.join(START_MENU_DIR, "卸载 " + APP_NAME + ".lnk"),
                  os.path.join(target, UNINSTALL_NAME), target, "卸载 " + APP_NAME)
    time.sleep(0.5)
    if os.path.isfile(exe_path):
        subprocess.Popen([exe_path], cwd=target)
    sys.exit(0 if hive else 2)


def main():
    argv = [a for a in sys.argv[1:]]
    is_uninstall = "--uninstall" in argv or \
        os.path.basename(sys.argv[0] if getattr(sys, "frozen", False) else __file__).lower() \
        == UNINSTALL_NAME
    if is_uninstall:
        run_uninstall()
        return
    if "--silent" in argv or "/S" in argv or "/s" in argv:
        run_silent()
        return
    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    w = InstallerWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
