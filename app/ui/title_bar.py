# -*- coding: utf-8 -*-
"""仿 Mac 风格标题栏：控制按钮位于右侧（红/黄/绿三色圆点），中部为悬浮提示区"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QApplication

from app.core import config
from app.ui import icons


def _circle_btn(name, color, hover, tooltip):
    btn = QPushButton()
    btn.setObjectName(name)
    btn.setToolTip(tooltip)
    btn.setFixedSize(11, 11)
    btn.setCursor(Qt.PointingHandCursor)
    btn.setStyleSheet(
        "QPushButton#{} {{ background:{}; border:none; border-radius:5px; }}"
        "QPushButton#{}:hover {{ background:{}; }}".format(name, color, name, hover))
    return btn


class TitleBar(QFrame):
    def __init__(self, window):
        super().__init__(window)
        self._win = window
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 0, 12, 0)
        lay.setSpacing(6)

        logo = QLabel()
        logo.setPixmap(icons.icon("app", "#1a73e8").pixmap(16, 16))
        self._logo_label = logo
        lay.addWidget(logo)

        title = QLabel("SC Tools")
        title.setObjectName("AppTitle")
        lay.addWidget(title)

        ver = QLabel("v" + config.APP_VER)
        ver.setObjectName("AppVer")
        lay.addWidget(ver)

        # 悬浮提示区（占标题栏中部空白）
        self.hint_label = QLabel("")
        self.hint_label.setObjectName("Hint")
        lay.addWidget(self.hint_label, 1)
        lay.addSpacing(8)

        # 置顶
        self.pin_btn = QPushButton()
        self.pin_btn.setToolTip("窗口置顶")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setFixedSize(24, 24)
        self.pin_btn.setCursor(Qt.PointingHandCursor)
        self.pin_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; border-radius:4px; }"
            "QPushButton:hover { background:rgba(128,128,128,60); }")
        self.pin_btn.clicked.connect(self._toggle_pin)
        lay.addWidget(self.pin_btn)

        # 日/夜模式切换（白天显示月亮=切夜间，夜间显示太阳=切白天）
        self.mode_btn = QPushButton()
        self.mode_btn.setFixedSize(24, 24)
        self.mode_btn.setCursor(Qt.PointingHandCursor)
        self.mode_btn.setStyleSheet(
            "QPushButton { background:transparent; border:none; border-radius:4px; }"
            "QPushButton:hover { background:rgba(128,128,128,60); }")
        self.mode_btn.clicked.connect(self._toggle_mode)
        lay.addWidget(self.mode_btn)
        lay.addSpacing(4)

        # 仿 Mac 三色控制按钮（右侧，缩小版）
        self.btn_close = _circle_btn("MacClose", "#ff5f57", "#e0443e", "关闭")
        self.btn_min = _circle_btn("MacMin", "#febc2e", "#e0a51f", "最小化")
        self.btn_max = _circle_btn("MacMax", "#28c840", "#1fa833", "最大化/还原")
        for b, slot in ((self.btn_close, self._win.close),
                        (self.btn_min, self._win.showMinimized),
                        (self.btn_max, self._toggle_max)):
            b.clicked.connect(slot)
            lay.addWidget(b)

        # 系统样式按钮组（SVG 图标，与 Mac 组二选一）
        self.sys_btn_min = self._sys_btn(self._win.showMinimized, "最小化")
        self.sys_btn_max = self._sys_btn(self._toggle_max, "最大化/还原")
        self.sys_btn_close = self._sys_btn(self._win.close, "关闭")
        for b in (self.sys_btn_min, self.sys_btn_max, self.sys_btn_close):
            lay.addWidget(b)

        self._style = self._win.skin.get("titlebar_style", "mac")
        self.refresh_icons()

    def _sys_btn(self, slot, tooltip):
        b = QPushButton()
        b.setToolTip(tooltip)
        b.setFixedSize(30, 22)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet(
            "QPushButton { background:transparent; border:none; border-radius:0; }"
            "QPushButton:hover { background:rgba(128,128,128,70); }")
        b.clicked.connect(slot)
        return b

    def set_style(self, style):
        """切换标题栏按钮样式：mac（三色圆点）/ system（— □ ×）"""
        self._style = style
        self.refresh_icons()

    def set_hint(self, text):
        self.hint_label.setText(text)

    def refresh_icons(self):
        p = self._win.palette_data()
        self._logo_label.setPixmap(icons.icon("app", p["on_brand"]).pixmap(16, 16))
        mac = self._style != "system"
        for b in (self.btn_close, self.btn_min, self.btn_max):
            b.setVisible(mac)
        for b in (self.sys_btn_min, self.sys_btn_max, self.sys_btn_close):
            b.setVisible(not mac)
        color = p["on_brand"]
        maximized = bool(self._win.windowState() & Qt.WindowMaximized)
        for b, name in ((self.sys_btn_min, "win_min"),
                        (self.sys_btn_max, "win_restore" if maximized else "win_max"),
                        (self.sys_btn_close, "close")):
            b.setIcon(icons.icon(name, color))
            b.setIconSize(b.size() * 0.5)
        color = p["on_brand"] if self.pin_btn.isChecked() else p["sub"]
        self.pin_btn.setIcon(icons.icon("pin", color))
        self.pin_btn.setIconSize(self.pin_btn.size() * 0.6)
        # 日/夜切换图标：当前白天显示月亮，当前夜间显示太阳
        night = p["mode"] == "night"
        self.mode_btn.setIcon(icons.icon("sun" if night else "moon", p["on_brand"]))
        self.mode_btn.setIconSize(self.mode_btn.size() * 0.6)
        self.mode_btn.setToolTip("切换到{}模式".format("白天" if night else "夜间"))

    def _toggle_mode(self):
        self._win.skin["mode"] = "day" if self._win.skin.get("mode", "day") == "night" else "night"
        self._win.apply_theme()

    def _toggle_pin(self):
        checked = self.pin_btn.isChecked()
        self._win.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self._win.show()
        self.refresh_icons()

    def _toggle_max(self):
        w = self._win
        # 双重判定（isMaximized + 状态位），修复最大化后状态丢失导致需点两次才还原
        if w.isMaximized() or (w.windowState() & Qt.WindowMaximized):
            w.setWindowState(w.windowState() & ~Qt.WindowMaximized)
            w.showNormal()
            # 无边框窗口 showNormal 偶发不还原几何，强制回到放大前尺寸
            geom = getattr(w, "_normal_geom", None)
            if geom is not None and geom.width() > 0:
                w.setGeometry(geom)
        else:
            w._normal_geom = w.geometry()
            w.showMaximized()
        self.refresh_icons()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            child = self.childAt(e.position().toPoint())
            if child is None or isinstance(child, QLabel):
                # 双击的第一次 press 不启动系统移动，否则移动模态循环会吞掉双击事件
                import time as _time
                now = _time.monotonic()
                interval = QApplication.instance().doubleClickInterval() / 1000.0
                if now - getattr(self, "_last_press", 0) > interval:
                    self.window().windowHandle().startSystemMove()
                self._last_press = now
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        self._toggle_max()
