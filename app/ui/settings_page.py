# -*- coding: utf-8 -*-
"""设置页面：配色方案（预设 + 自定义主题）、日/夜模式、标题栏、全局热键、
应用卡片图标开关、自定义背景图（含模糊度）、面板不透明度、配置导入导出与检查更新"""
import os
import re
import tempfile

from PySide6.QtCore import Qt, QUrl, QTimer, Signal
from PySide6.QtGui import QColor, QDesktopServices, QLinearGradient, QPainter
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QGridLayout,
                               QHBoxLayout, QLabel, QLineEdit, QProgressBar,
                               QPushButton, QScrollArea, QSlider, QTextEdit,
                               QVBoxLayout, QWidget)

from app.core import config, updater
from app.core.theme import (CUSTOM_SCHEME, FONT_STACK, SCHEME_DESCS, scheme_names, palette)
from app.ui.dialogs import AppDialog, AppMessageBox, SquareMenu
from app.ui.flow_layout import FlowLayout

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# 取色器预设色板（与主题友好的常用色）
PRESET_COLORS = [
    "#E74C3C", "#E15A6B", "#ED8B2D", "#D19C2F", "#8BC34A", "#3EB489",
    "#2FA8A0", "#78C7D2", "#89C2FF", "#3F5AA9", "#694D9F", "#9B7EDE",
    "#F8B5D0", "#E2725B", "#98B6C2", "#5E6A73", "#2A2F36", "#173247",
]

# 自定义主题可调项：key -> (显示名, 默认色)
THEME_KEYS = [
    ("brand", "主题色\n(标题栏)", "#89C2FF"),
    ("text", "字体颜色", "#2A2F36"),
    ("bg", "应用背景颜色", "#E6F7FF"),
    ("sidebar", "侧栏按钮颜色", "#D8ECF9"),
    ("panel", "内容区域背景颜色", "#FFFFFF"),
]


def _lum_of(hexc):
    c = QColor(hexc)
    return (0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()) / 255


class HueBar(QWidget):
    """色相条：水平 0-359 度渐变，点击/拖动选色相"""
    hueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(14)
        self._hue = 210
        self.setCursor(Qt.PointingHandCursor)

    def set_hue(self, h):
        self._hue = h % 360
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        for i in range(7):
            grad.setColorAt(i / 6.0, QColor.fromHsv((i * 60) % 360, 255, 255))
        p.fillRect(self.rect(), grad)
        x = self._hue / 359.0 * self.width()
        p.setPen(QColor("#FFFFFF"))
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(Qt.NoBrush)
        p.drawRect(int(x) - 2, 0, 4, self.height())
        p.end()

    def _pick(self, e):
        h = int(e.position().x() / max(1, self.width()) * 359)
        self._hue = max(0, min(359, h))
        self.update()
        self.hueChanged.emit(self._hue)

    def mousePressEvent(self, e):
        self._pick(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._pick(e)


class SVCanvas(QWidget):
    """饱和度-亮度二维取色板"""
    svChanged = Signal(float, float)   # s, v (0-1)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hue = 210
        self._s, self._v = 0.45, 1.0
        self.setMinimumSize(220, 140)
        self.setCursor(Qt.CrossCursor)

    def set_hue(self, h):
        self._hue = h % 360
        self.update()

    def set_sv(self, s, v):
        self._s, self._v = s, v
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        base = QColor.fromHsv(self._hue, 255, 255)
        w, h = self.width(), self.height()
        g1 = QLinearGradient(0, 0, w, 0)
        g1.setColorAt(0, QColor("#FFFFFF"))
        g1.setColorAt(1, base)
        p.fillRect(self.rect(), g1)
        g2 = QLinearGradient(0, 0, 0, h)
        g2.setColorAt(0, QColor(0, 0, 0, 0))
        g2.setColorAt(1, QColor(0, 0, 0, 255))
        p.fillRect(self.rect(), g2)
        # 指示圈
        cx, cy = self._s * w, (1 - self._v) * h
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QColor("#FFFFFF"))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(int(cx) - 5, int(cy) - 5, 10, 10)
        p.setPen(QColor("#333333"))
        p.drawEllipse(int(cx) - 6, int(cy) - 6, 12, 12)
        p.end()

    def _pick(self, e):
        s = e.position().x() / max(1, self.width())
        v = 1 - e.position().y() / max(1, self.height())
        self._s = max(0.0, min(1.0, s))
        self._v = max(0.0, min(1.0, v))
        self.update()
        self.svChanged.emit(self._s, self._v)

    def mousePressEvent(self, e):
        self._pick(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._pick(e)


class ColorPickerDialog(AppDialog):
    """方形取色器：SV 色板 + 色相条自由取色，附 HEX 输入与预设色板"""

    def __init__(self, parent, title, current):
        super().__init__(parent, title)
        self.setFixedWidth(400)
        self._syncing = False
        self.color = current if _HEX_RE.match(current or "") else "#89C2FF"
        c = self.content_layout()

        # SV 色板 + 色相条
        pick_row = QHBoxLayout()
        pick_row.setSpacing(10)
        self._sv = SVCanvas()
        self._sv.svChanged.connect(self._on_sv)
        pick_row.addWidget(self._sv, 1)
        self._hue_bar = HueBar()
        self._hue_bar.setFixedWidth(16)
        self._hue_bar.hueChanged.connect(self._on_hue)
        pick_row.addWidget(self._hue_bar)
        c.addLayout(pick_row)

        # 预览 + HEX
        prev_row = QHBoxLayout()
        prev_row.setSpacing(8)
        self._preview = QLabel()
        self._preview.setFixedHeight(36)
        self._preview.setAlignment(Qt.AlignCenter)
        prev_row.addWidget(self._preview, 1)
        prev_row.addWidget(QLabel("HEX"))
        self._hex_edit = QLineEdit(self.color)
        self._hex_edit.setFixedWidth(90)
        self._hex_edit.textChanged.connect(self._on_hex)
        prev_row.addWidget(self._hex_edit)
        c.addLayout(prev_row)

        # 预设色板
        g = QGridLayout()
        g.setSpacing(6)
        for i, col in enumerate(PRESET_COLORS):
            b = QPushButton()
            b.setFixedSize(36, 36)
            b.setCursor(Qt.PointingHandCursor)
            b.setStyleSheet(
                "QPushButton {{ background:{}; border:1px solid #99A6AE; }}"
                "QPushButton:hover {{ border:2px solid {}; }}".format(col, "#2A2F36"))
            b.clicked.connect(lambda _=False, cc=col: self._hex_edit.setText(cc))
            g.addWidget(b, i // 6, i % 6)
        c.addLayout(g)

        # 确定/取消
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("确定")
        ok.setObjectName("Accent")
        ok.clicked.connect(self.accept)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        c.addLayout(btn_row)

        self._load_color(self.color)

    # -- 颜色同步 -----------------------------------------------------------
    def _load_color(self, hexc):
        """从 HEX 反推 hue/s/v 并刷新全部控件"""
        qc = QColor(hexc)
        h, s, _v = qc.hsvHue(), qc.hsvSaturationF(), qc.valueF()
        h = 210 if h < 0 else h
        self._syncing = True
        self._sv.set_hue(h)
        self._sv.set_sv(s, _v)
        self._hue_bar.set_hue(h)
        self._hex_edit.setText(hexc.upper())
        self._syncing = False
        self._update_preview()

    def _on_sv(self, s, v):
        if self._syncing:
            return
        qc = QColor.fromHsv(self._hue_bar._hue, int(s * 255), int(v * 255))
        self.color = qc.name().upper()
        self._syncing = True
        self._hex_edit.setText(self.color)
        self._syncing = False
        self._update_preview()

    def _on_hue(self, h):
        if self._syncing:
            return
        self._sv.set_hue(h)
        self._on_sv(self._sv._s, self._sv._v)

    def _on_hex(self, text):
        if self._syncing:
            return
        t = text.strip()
        if t and not t.startswith("#"):
            t = "#" + t
        if _HEX_RE.match(t):
            self._load_color(t.upper())

    def _update_preview(self):
        fg = "#2A2F36" if _lum_of(self.color) > 0.6 else "#FFFFFF"
        self._preview.setStyleSheet(
            "background:{}; border:1px solid #99A6AE; color:{};"
            "font-size:13px; font-weight:bold;".format(self.color, fg))
        self._preview.setText(self.color)

    @staticmethod
    def get_color(parent, title, current):
        dlg = ColorPickerDialog(parent, title, current)
        if dlg.exec():
            return dlg.color
        return None


class UpdateDialog(AppDialog):
    """发现新版本：展示更新日志，下载资产，完成后运行安装包"""

    def __init__(self, parent, info):
        super().__init__(parent, "发现新版本")
        self._info = info
        self._dest = ""
        self.setFixedWidth(430)
        c = self.content_layout()

        head = QLabel("最新版本 {}，当前 v{}{}".format(
            info["version"], config.APP_VER,
            "" if info["asset_url"] else "（发布页未附安装包，请到发布页手动下载）"))
        head.setWordWrap(True)
        c.addWidget(head)

        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setPlainText(info["notes"] or "（无更新说明）")
        notes.setFixedHeight(150)
        c.addWidget(notes)

        self._prog = QProgressBar()
        self._prog.setValue(0)
        self._prog.hide()
        c.addWidget(self._prog)
        self._status = QLabel("")
        self._status.setStyleSheet("color:#5A6772; font-size:11px;")
        self._status.hide()
        c.addWidget(self._status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        page_btn = QPushButton("打开发布页")
        page_btn.setObjectName("Ghost")
        page_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(info["page"])))
        btn_row.addWidget(page_btn)
        self._dl_btn = QPushButton("下载并安装")
        self._dl_btn.setObjectName("Accent")
        self._dl_btn.setCursor(Qt.PointingHandCursor)
        self._dl_btn.setEnabled(bool(info["asset_url"]))
        self._dl_btn.clicked.connect(self._download)
        btn_row.addWidget(self._dl_btn)
        c.addLayout(btn_row)

    def _download(self):
        self._dl_btn.setEnabled(False)
        self._prog.show()
        self._prog.setValue(0)
        self._status.show()
        self._status.setText("下载中...")
        self._dest = os.path.join(tempfile.gettempdir(),
                                  self._info["asset_name"] or "SC_Tools_Setup.exe")
        self._thread = _DownloadThread(self._info["asset_url"], self._dest, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.done.connect(self._on_downloaded)
        self._thread.fail.connect(self._on_download_fail)
        self._thread.start()

    def _on_progress(self, got, total):
        if total > 0:
            self._prog.setValue(int(got * 100 / total))
            self._status.setText("下载中... {:.1f} / {:.1f} MB".format(
                got / 1048576, total / 1048576))

    def _on_download_fail(self, msg):
        self._status.setText("下载失败：" + msg)
        self._dl_btn.setEnabled(True)

    def _on_downloaded(self, _dest):
        self._prog.setValue(100)
        self._status.setText("下载完成，正在启动安装程序（将自动覆盖安装）...")
        try:
            os.startfile(self._dest)
        except OSError as e:
            self._status.setText("安装包位置：{}\n（{}）".format(self._dest, e))


class _DownloadThread(updater.FnThread):
    progress = Signal(int, int)

    def __init__(self, url, dest, parent=None):
        super().__init__(None, parent)
        self._url, self._dest = url, dest

    def run(self):
        try:
            updater.download(self._url, self._dest,
                             lambda g, t: self.progress.emit(g, t))
            self.done.emit(self._dest)
        except Exception as e:
            self.fail.emit(str(e))


class ThemeDialog(AppDialog):
    """添加/编辑自定义主题：命名 + 主题色/字体/背景/侧栏/内容区 五项颜色自由搭配"""

    def __init__(self, parent, win, theme=None):
        super().__init__(parent, "添加主题" if not theme else "编辑主题")
        self._win = win
        self._theme = dict(theme) if theme else {}
        self.setFixedWidth(440)
        c = self.content_layout()

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("主题名称"))
        self._name_edit = QLineEdit((theme or {}).get("name", "我的主题"))
        name_row.addWidget(self._name_edit, 1)
        c.addLayout(name_row)

        # 五项颜色色块（横排，块下小字名称）
        color_row = QHBoxLayout()
        color_row.setSpacing(12)
        self._color_btns = {}
        for key, label, default in THEME_KEYS:
            cell = QVBoxLayout()
            cell.setSpacing(4)
            b = QPushButton()
            b.setFixedSize(64, 48)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, k=key: self._pick(k))
            self._color_btns[key] = b
            cell.addWidget(b, 0, Qt.AlignHCenter)
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignHCenter)
            lbl.setStyleSheet("font-size:10px; color:#72797F;")
            cell.addWidget(lbl)
            color_row.addLayout(cell)
        c.addLayout(color_row)

        # 实时预览条
        self._preview = QLabel()
        self._preview.setFixedHeight(40)
        c.addWidget(self._preview)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setObjectName("Accent")
        ok.clicked.connect(self._save)
        btn_row.addWidget(cancel)
        btn_row.addWidget(ok)
        c.addLayout(btn_row)

        for key, _label, default in THEME_KEYS:
            self._refresh_btn(key, self._theme.get(key) or default)
        self._name_edit.textChanged.connect(lambda _: self._refresh_preview())

    def _refresh_btn(self, key, col):
        b = self._color_btns[key]
        b.setStyleSheet(
            "QPushButton {{ background:{}; border:1px solid #99A6AE; }}"
            "QPushButton:hover {{ border:2px solid #2A2F36; }}".format(col))
        b.setToolTip(col)
        self._theme[key] = col
        self._refresh_preview()

    def _pick(self, key):
        defaults = {k: d for k, _l, d in THEME_KEYS}
        labels = {k: l for k, l, _d in THEME_KEYS}
        cur = self._theme.get(key) or defaults[key]
        c = ColorPickerDialog.get_color(self, labels[key].replace("\n", ""), cur)
        if c:
            self._refresh_btn(key, c)

    def _refresh_preview(self):
        t = self._theme
        self._preview.setStyleSheet(
            "background:{}; border:1px solid #99A6AE; color:{};"
            "font-size:12px; font-weight:bold;".format(t.get("bg") or "#E6F7FF",
                                                       t.get("text") or "#2A2F36"))
        self._preview.setText("  {}  —  预览（标题栏 {}）".format(
            self._name_edit.text() or "未命名", t.get("brand") or "#89C2FF"))

    def _save(self):
        name = self._name_edit.text().strip() or "我的主题"
        self._theme["name"] = name
        themes = self._win.skin.setdefault("custom_themes", [])
        for i, t in enumerate(themes):
            if t.get("name") == name:
                themes[i] = self._theme
                break
        else:
            themes.append(self._theme)
        self.accept()


class Swatch(QFrame):
    """主题色块预览卡：主色（标题栏）+ 侧栏条 + 内容区卡片"""

    def __init__(self, page, name, custom=None):
        super().__init__()
        self._page = page
        self._name = name
        self._custom = custom          # 自定义主题 dict（None=预设）
        self.setObjectName("Swatch")
        self.setFixedSize(104, 64)
        self.setCursor(Qt.PointingHandCursor)
        inner = QVBoxLayout(self)
        inner.setContentsMargins(8, 8, 8, 6)
        inner.setSpacing(4)
        self._bar = QLabel()
        self._bar.setFixedHeight(6)
        self._card = QLabel()
        self._card.setFixedHeight(18)
        inner.addWidget(self._bar)
        inner.addWidget(self._card)
        inner.addStretch()
        self._text = QLabel(name)
        self._text.setStyleSheet("border:none; font-size:11px; font-family:{};".format(FONT_STACK))
        inner.addWidget(self._text)
        self.refresh()

    def refresh(self):
        if self._custom:
            p = palette(CUSTOM_SCHEME, "day", self._custom)
        else:
            p = palette(self._name)
        self.setStyleSheet(
            "QFrame#Swatch {{ background:{}; border:2px solid #66808080; }}"
            "QFrame#Swatch[selected=\"true\"] {{ border:2px solid {}; }}".format(p["titlebar"], p["accent"]))
        self._bar.setStyleSheet("background:{}; border:none;".format(p["sidebar"]))
        self._card.setStyleSheet("background:{}; border:1px solid {};".format(p["panel"], p["border"]))
        self._text.setStyleSheet("color:{}; border:none; font-size:11px; font-family:{};".format(
            p["text"], FONT_STACK))

    def mousePressEvent(self, e):
        if e.button() == Qt.RightButton and self._custom:
            m = SquareMenu(self)
            act_del = m.addAction("删除主题")
            act_edit = m.addAction("编辑主题")
            chosen = m.exec(e.globalPosition().toPoint())
            if chosen is act_del:
                self._page.delete_custom_theme(self._name)
            elif chosen is act_edit:
                self._page.edit_custom_theme(self._name)
            return
        self._page.select_scheme(self._name)


class AutoHideScroll(QScrollArea):
    """隐藏滚动条的滚动区：滚动时显示，停 1.2 秒后自动隐藏"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sb = self.verticalScrollBar()
        sb.setStyleSheet(
            "QScrollBar:vertical { background:transparent; width:6px; margin:0; }"
            "QScrollBar::handle:vertical { background:#66808A93; min-height:30px; }"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }"
            "QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background:transparent; }")
        sb.setVisible(False)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(lambda: sb.setVisible(False))
        sb.valueChanged.connect(self._flash)

    def _flash(self, _):
        sb = self.verticalScrollBar()
        sb.setVisible(True)
        self._timer.start(1200)


class SettingsPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window
        skin = self._win.skin

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = AutoHideScroll()
        outer.addWidget(scroll)

        body = QWidget()
        root = QVBoxLayout(body)
        root.setContentsMargins(24, 18, 24, 16)
        root.setSpacing(14)
        scroll.setWidget(body)

        title = QLabel("设置")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        # 配色方案 + 日/夜模式
        sec1 = QFrame()
        sec1.setObjectName("Section")
        v1 = QVBoxLayout(sec1)
        v1.setContentsMargins(16, 14, 16, 14)
        v1.setSpacing(12)
        l1 = QLabel("配色方案（主色 = 标题栏，辅色 = 侧边栏与背景）")
        l1.setObjectName("GroupTitle")
        v1.addWidget(l1)
        sw_host = QWidget()
        self._sw_flow = FlowLayout(sw_host, spacing=10, fill_min=104)
        self._swatches = []
        for name in scheme_names():
            self._sw_flow.addWidget(Swatch(self, name))
        self._rebuild_custom_swatches()
        v1.addWidget(sw_host)
        # 当前方案描述
        self._desc_label = QLabel("")
        self._desc_label.setObjectName("Sub")
        self._desc_label.setWordWrap(True)
        v1.addWidget(self._desc_label)
        # 日/夜模式 + 标题栏按钮 + 应用卡片图标（同一行三组互斥选项）
        opt_row = QHBoxLayout()
        opt_row.setSpacing(8)
        l_mode = QLabel("日/夜模式")
        l_mode.setObjectName("GroupTitle")
        opt_row.addWidget(l_mode)
        self.btn_day = QPushButton("白天")
        self.btn_night = QPushButton("夜间")
        for b in (self.btn_day, self.btn_night):
            b.setObjectName("Ghost")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
        self._mode_group = QButtonGroup(self)
        self._mode_group.addButton(self.btn_day)
        self._mode_group.addButton(self.btn_night)
        self._mode_group.setExclusive(True)
        self.btn_day.clicked.connect(lambda: self.select_mode("day"))
        self.btn_night.clicked.connect(lambda: self.select_mode("night"))
        opt_row.addWidget(self.btn_day)
        opt_row.addWidget(self.btn_night)
        opt_row.addSpacing(24)
        l_tb = QLabel("标题栏按钮")
        l_tb.setObjectName("GroupTitle")
        opt_row.addWidget(l_tb)
        self.btn_tb_mac = QPushButton("Mac")
        self.btn_tb_sys = QPushButton("系统")
        for b in (self.btn_tb_mac, self.btn_tb_sys):
            b.setObjectName("Ghost")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
        self._tb_group = QButtonGroup(self)
        self._tb_group.addButton(self.btn_tb_mac)
        self._tb_group.addButton(self.btn_tb_sys)
        self._tb_group.setExclusive(True)
        self.btn_tb_mac.clicked.connect(lambda: self.select_titlebar_style("mac"))
        self.btn_tb_sys.clicked.connect(lambda: self.select_titlebar_style("system"))
        opt_row.addWidget(self.btn_tb_mac)
        opt_row.addWidget(self.btn_tb_sys)
        opt_row.addSpacing(24)
        l_icon = QLabel("应用卡片图标")
        l_icon.setObjectName("GroupTitle")
        opt_row.addWidget(l_icon)
        self.btn_icon_on = QPushButton("显示")
        self.btn_icon_off = QPushButton("隐藏")
        for b in (self.btn_icon_on, self.btn_icon_off):
            b.setObjectName("Ghost")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
        self._icon_group = QButtonGroup(self)
        self._icon_group.addButton(self.btn_icon_on)
        self._icon_group.addButton(self.btn_icon_off)
        self._icon_group.setExclusive(True)
        self.btn_icon_on.clicked.connect(lambda: self.select_tool_icons(True))
        self.btn_icon_off.clicked.connect(lambda: self.select_tool_icons(False))
        (self.btn_icon_on if skin.get("show_tool_icons", True) else self.btn_icon_off).setChecked(True)
        opt_row.addWidget(self.btn_icon_on)
        opt_row.addWidget(self.btn_icon_off)
        opt_row.addStretch()
        v1.addLayout(opt_row)
        # 全局热键开关
        hk_row = QHBoxLayout()
        hk_row.setSpacing(8)
        l_hk = QLabel("全局热键")
        l_hk.setObjectName("GroupTitle")
        hk_row.addWidget(l_hk)
        tip_hk = QLabel("Ctrl+Alt+S 呼出主窗口")
        tip_hk.setObjectName("Sub")
        hk_row.addWidget(tip_hk)
        hk_row.addStretch()
        self.btn_hk_on = QPushButton("开启")
        self.btn_hk_off = QPushButton("关闭")
        for b in (self.btn_hk_on, self.btn_hk_off):
            b.setObjectName("Ghost")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
        self._hk_group = QButtonGroup(self)
        self._hk_group.addButton(self.btn_hk_on)
        self._hk_group.addButton(self.btn_hk_off)
        self._hk_group.setExclusive(True)
        self.btn_hk_on.clicked.connect(lambda: self.select_hotkey(True))
        self.btn_hk_off.clicked.connect(lambda: self.select_hotkey(False))
        (self.btn_hk_on if skin.get("global_hotkey", True) else self.btn_hk_off).setChecked(True)
        hk_row.addWidget(self.btn_hk_on)
        hk_row.addWidget(self.btn_hk_off)
        v1.addLayout(hk_row)
        root.addWidget(sec1)

        # 背景图
        sec2 = QFrame()
        sec2.setObjectName("Section")
        v2 = QVBoxLayout(sec2)
        v2.setContentsMargins(16, 14, 16, 14)
        v2.setSpacing(10)
        l2 = QLabel("自定义背景（支持将图片放入 resources/skins 后选择）")
        l2.setObjectName("GroupTitle")
        v2.addWidget(l2)
        bg_row = QHBoxLayout()
        bg_row.setSpacing(8)
        self.ed_bg = QLineEdit(skin.get("bg_image", ""))
        self.ed_bg.setReadOnly(True)
        bg_row.addWidget(self.ed_bg, 1)
        btn_pick = QPushButton("选择图片")
        btn_clear = QPushButton("清除")
        for b in (btn_pick, btn_clear):
            b.setObjectName("Ghost")
        btn_pick.clicked.connect(self._pick_bg)
        btn_clear.clicked.connect(self._clear_bg)
        bg_row.addWidget(btn_pick)
        bg_row.addWidget(btn_clear)
        v2.addLayout(bg_row)

        blur_row = QHBoxLayout()
        l_blur = QLabel("背景模糊程度（设置背景图后生效）")
        l_blur.setObjectName("GroupTitle")
        blur_row.addWidget(l_blur)
        self.blur_label = QLabel("{}%".format(skin.get("blur", 30)))
        self.blur_label.setObjectName("Sub")
        blur_row.addStretch()
        blur_row.addWidget(self.blur_label)
        v2.addLayout(blur_row)
        self.blur_slider = QSlider(Qt.Horizontal)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(int(skin.get("blur", 30)))
        self.blur_slider.valueChanged.connect(self._on_blur)
        v2.addWidget(self.blur_slider)
        root.addWidget(sec2)

        # 不透明度
        sec3 = QFrame()
        sec3.setObjectName("Section")
        v3 = QVBoxLayout(sec3)
        v3.setContentsMargins(16, 14, 16, 14)
        v3.setSpacing(10)
        l3 = QLabel("面板不透明度（设置背景图后，作用于侧边栏与全部面板）")
        l3.setObjectName("GroupTitle")
        v3.addWidget(l3)
        op_row = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(50, 100)
        self.slider.setValue(int(skin.get("opacity", 92)))
        self.slider.valueChanged.connect(self._on_opacity)
        self.op_label = QLabel("{}%".format(self.slider.value()))
        self.op_label.setObjectName("Sub")
        op_row.addWidget(self.slider, 1)
        op_row.addWidget(self.op_label)
        v3.addLayout(op_row)
        root.addWidget(sec3)

        # 关于 + 版本/更新 + 配置导入导出
        sec4 = QFrame()
        sec4.setObjectName("Section")
        v4 = QVBoxLayout(sec4)
        v4.setContentsMargins(16, 14, 16, 14)
        v4.setSpacing(10)
        ver_row = QHBoxLayout()
        ver_row.setSpacing(8)
        about = QLabel("SC Tools v{} (PySide6)    作者：沙尘612".format(config.APP_VER))
        about.setObjectName("Sub")
        ver_row.addWidget(about)
        ver_row.addStretch()
        self.btn_check = QPushButton("检查更新")
        self.btn_check.setObjectName("Ghost")
        self.btn_check.setCursor(Qt.PointingHandCursor)
        self.btn_check.clicked.connect(self._check_update)
        ver_row.addWidget(self.btn_check)
        v4.addLayout(ver_row)
        cfg_row = QHBoxLayout()
        cfg_row.setSpacing(8)
        tip = QLabel("配置文件位于 resources/config/；支持打包导出/导入，便于换机迁移。")
        tip.setObjectName("Sub")
        tip.setWordWrap(True)
        cfg_row.addWidget(tip, 1)
        btn_export = QPushButton("导出配置")
        btn_import = QPushButton("导入配置")
        for b in (btn_export, btn_import):
            b.setObjectName("Ghost")
            b.setCursor(Qt.PointingHandCursor)
        btn_export.clicked.connect(self._export_config)
        btn_import.clicked.connect(self._import_config)
        cfg_row.addWidget(btn_export)
        cfg_row.addWidget(btn_import)
        v4.addLayout(cfg_row)
        root.addWidget(sec4)

        root.addStretch()
        self.select_scheme(skin.get("scheme", "晴空蓝"), apply=False)
        mode = skin.get("mode", "day")
        (self.btn_day if mode == "day" else self.btn_night).setChecked(True)
        (self.btn_tb_mac if skin.get("titlebar_style", "mac") != "system" else self.btn_tb_sys).setChecked(True)

    # -- 色块行管理 ---------------------------------------------------------
    def _custom_theme(self, name):
        for t in self._win.skin.get("custom_themes", []):
            if t.get("name") == name:
                return t
        return None

    def _custom_palette_data(self, name):
        """main_window.apply_theme 用：scheme 名对应自定义主题 dict（无则 None）"""
        return self._custom_theme(name)

    def _rebuild_custom_swatches(self):
        # 移除旧的自定义色块与添加按钮（保留 15 个预设在前）
        while self._sw_flow.count() > len(scheme_names()):
            item = self._sw_flow.takeAt(self._sw_flow.count() - 1)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._swatches = [self._sw_flow.itemAt(i).widget() for i in range(self._sw_flow.count())]
        # 兼容旧版单套自定义配色：一次性迁移进 custom_themes（迁移后删除旧字段，不再复活）
        if self._win.skin.get("custom_brand"):
            cb = self._win.skin.pop("custom_brand")
            cbg = self._win.skin.pop("custom_bg", "") or "#E6F7FF"
            themes = self._win.skin.setdefault("custom_themes", [])
            if not any(t.get("name") == "自定义" for t in themes):
                themes.insert(0, {"name": "自定义", "brand": cb, "bg": cbg,
                                  "text": "", "sidebar": "", "panel": ""})
        for t in self._win.skin.get("custom_themes", []):
            sw = Swatch(self, t.get("name", "未命名"), custom=t)
            self._sw_flow.addWidget(sw)
        # ＋ 添加主题按钮
        add = QPushButton("＋")
        add.setFixedSize(104, 64)
        add.setCursor(Qt.PointingHandCursor)
        add.setToolTip("添加自定义主题")
        add.setStyleSheet(
            "QPushButton { background:transparent; border:2px dashed #66808080;"
            " font-size:22px; color:#72797F; }"
            "QPushButton:hover { border-color:#2A2F36; color:#2A2F36; }")
        add.clicked.connect(self._add_theme)
        self._sw_flow.addWidget(add)
        self._add_btn = add
        self._sync_selected_property()

    def _sync_selected_property(self):
        cur = self._win.skin.get("scheme", "晴空蓝")
        for sw in self._swatches:
            sw.setProperty("selected", "true" if sw._name == cur else "false")
            sw.style().unpolish(sw)
            sw.style().polish(sw)

    def _add_theme(self):
        dlg = ThemeDialog(self, self._win)
        if dlg.exec():
            self._win.skin["scheme"] = dlg._theme["name"]
            self._rebuild_custom_swatches()
            self.select_scheme(dlg._theme["name"])

    def edit_custom_theme(self, name):
        t = self._custom_theme(name)
        if not t:
            return
        dlg = ThemeDialog(self, self._win, theme=t)
        if dlg.exec():
            self._rebuild_custom_swatches()
            self.select_scheme(t["name"])

    def delete_custom_theme(self, name):
        themes = self._win.skin.get("custom_themes", [])
        self._win.skin["custom_themes"] = [t for t in themes if t.get("name") != name]
        if name == "自定义":
            # 删除旧版迁移主题时同步清掉遗留字段，避免再次出现
            self._win.skin.pop("custom_brand", None)
            self._win.skin.pop("custom_bg", None)
        if self._win.skin.get("scheme") == name:
            self._win.skin["scheme"] = "晴空蓝"
        self._rebuild_custom_swatches()
        self.select_scheme(self._win.skin.get("scheme", "晴空蓝"))

    # -- 动作 -------------------------------------------------------------
    def select_scheme(self, name, apply=True):
        self._sync_selected_property()
        for sw in self._swatches:
            if sw._name == name:
                self._desc_label.setText(SCHEME_DESCS.get(name, ""))
                break
        else:
            self._desc_label.setText("自定义主题：颜色由用户自由搭配" if name else "")
        if apply:
            self._win.skin["scheme"] = name
            self._win.apply_theme()

    def select_mode(self, mode):
        self._win.skin["mode"] = mode
        self._win.apply_theme()

    def select_titlebar_style(self, style):
        self._win.skin["titlebar_style"] = style
        self._win.apply_theme()

    def select_tool_icons(self, on):
        self._win.skin["show_tool_icons"] = bool(on)
        self._win.tools_page.rebuild()
        self._win.apply_theme()

    def select_hotkey(self, on):
        self._win.skin["global_hotkey"] = bool(on)
        self._win.apply_hotkey()
        self._win.apply_theme()

    # -- 配置导入导出 ---------------------------------------------------------
    def _export_config(self):
        import zipfile
        path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", os.path.join(os.path.expanduser("~"), "Desktop", "sctools_config.zip"),
            "配置包 (*.zip)")
        if not path:
            return
        try:
            with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
                for name in ("tools.json", "skin.json", "nav.json"):
                    p = config.config_path(name)
                    if os.path.exists(p):
                        z.write(p, name)
            AppMessageBox.info(self, "导出成功", "配置已导出到：\n" + path)
        except OSError as e:
            AppMessageBox.warning(self, "导出失败", str(e))

    def _import_config(self):
        import zipfile
        path, _ = QFileDialog.getOpenFileName(self, "导入配置", "", "配置包 (*.zip)")
        if not path:
            return
        if not AppMessageBox.question(self, "导入配置",
                                      "导入将覆盖当前应用清单、皮肤与导航配置，确定继续？"):
            return
        try:
            with zipfile.ZipFile(path) as z:
                for name in ("tools.json", "skin.json", "nav.json"):
                    if name in z.namelist():
                        z.extract(name, config.config_dir())
        except (OSError, zipfile.BadZipFile) as e:
            AppMessageBox.warning(self, "导入失败", str(e))
            return
        self._win.reload_config()
        AppMessageBox.info(self, "导入成功", "配置已应用。")

    # -- 检查更新 -------------------------------------------------------------
    def _check_update(self):
        from app.core import updater
        self.btn_check.setEnabled(False)
        self.btn_check.setText("检查中...")
        self._upd_thread = updater.FnThread(updater.fetch_latest, self)
        self._upd_thread.done.connect(self._on_update_info)
        self._upd_thread.fail.connect(self._on_update_fail)
        self._upd_thread.start()

    def _on_update_fail(self, msg):
        self.btn_check.setEnabled(True)
        self.btn_check.setText("检查更新")
        AppMessageBox.warning(self, "检查更新失败",
                              msg + "\n\nGitHub 在部分网络环境下可能无法直连，"
                                    "可稍后重试或到项目发布页手动下载。")

    def _on_update_info(self, info):
        self.btn_check.setEnabled(True)
        self.btn_check.setText("检查更新")
        if info is None:
            AppMessageBox.info(self, "检查更新", "当前已是最新版本。")
            return
        dlg = UpdateDialog(self, info)
        dlg.exec()

    def sync_titlebar_style(self, style):
        """外部切换后同步按钮选中态"""
        (self.btn_tb_mac if style != "system" else self.btn_tb_sys).setChecked(True)

    def sync_mode(self, mode):
        """标题栏切换日夜模式后同步按钮选中态（不触发点击信号）"""
        (self.btn_day if mode == "day" else self.btn_night).setChecked(True)

    def _pick_bg(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择背景图片", config.SKIN_DIR,
                                           "图片 (*.png *.jpg *.jpeg *.bmp *.webp)")
        if p:
            self._win.skin["bg_image"] = p
            self.ed_bg.setText(p)
            self._win.apply_theme()

    def _clear_bg(self):
        self._win.skin["bg_image"] = ""
        self.ed_bg.setText("")
        self._win.apply_theme()

    def _on_blur(self, v):
        self.blur_label.setText("{}%".format(v))
        self._win.skin["blur"] = v
        self._win.apply_theme()

    def _on_opacity(self, v):
        self.op_label.setText("{}%".format(v))
        self._win.skin["opacity"] = v
        self._win.apply_theme()
