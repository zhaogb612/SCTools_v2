# -*- coding: utf-8 -*-
"""屏幕坏点/漏光检测：选择纯色全屏显示，逐色检查坏点；自动轮播辅助漏光检查。
F11 进入/退出全屏，Esc 返回选择页或关闭。"""
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QPushButton, QVBoxLayout, QWidget)

COLORS = [
    ("纯白", "#FFFFFF"), ("纯黑", "#000000"),
    ("红色", "#FF0000"), ("绿色", "#00FF00"), ("蓝色", "#0000FF"),
    ("黄色", "#FFFF00"), ("青色", "#00FFFF"), ("品红", "#FF00FF"),
]
# 自动轮播间隔（毫秒）：漏光检查时眼睛适应固定亮度更易分辨边缘泛光
CYCLE_MS = 2000


class ScreenTestDialog(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("屏幕坏点 / 漏光检测 — SC Tools")
        self._full = None        # 全屏纯色窗口
        self._cycle_timer = None
        self._cycle_colors = []
        self._cycle_idx = 0

        self.resize(560, 320)
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 16)
        root.setSpacing(12)

        tip = QLabel("逐色检查坏点：全屏纯色下，不发光的异色小点即坏点；\n"
                     "黑色下检查漏光：屏幕边缘/四角出现泛光即漏光。\n"
                     "全屏中按 F11 退出全屏，Esc 返回本页。")
        tip.setObjectName("Sub")
        tip.setWordWrap(True)
        root.addWidget(tip)

        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (name, hexc) in enumerate(COLORS):
            btn = QPushButton(name)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(
                "QPushButton { background:%s; color:%s; border:none; }"
                "QPushButton:hover { border:2px solid #173247; }"
                % (hexc, "#000000" if QColor(hexc).lightness() > 128 else "#FFFFFF"))
            btn.clicked.connect(lambda _=False, c=hexc: self._show_color(c))
            grid.addWidget(btn, i // 4, i % 4)
        root.addLayout(grid)

        bottom = QHBoxLayout()
        self.btn_cycle = QPushButton("自动轮播（漏光检查）")
        self.btn_cycle.setObjectName("Accent")
        self.btn_cycle.setCursor(Qt.PointingHandCursor)
        self.btn_cycle.clicked.connect(self._toggle_cycle)
        bottom.addWidget(self.btn_cycle)
        bottom.addStretch()
        btn_close = QPushButton("关闭")
        btn_close.setObjectName("Ghost")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        bottom.addWidget(btn_close)
        root.addLayout(bottom)

    # -- 全屏纯色 -------------------------------------------------------------
    def _show_color(self, hexc):
        self._stop_cycle()
        self._launch_full(QColor(hexc))

    def _launch_full(self, color):
        if self._full is None:
            self._full = QWidget(None)  # 独立顶层窗口，可占满整个屏幕
            self._full.setWindowFlag(Qt.WindowStaysOnTopHint, True)
            self._full.setWindowFlag(Qt.FramelessWindowHint, True)
            self._full.setCursor(Qt.BlankCursor)  # 检测时光标隐藏不干扰
            QShortcut(QKeySequence(Qt.Key_F11), self._full, activated=self._exit_full)
            QShortcut(QKeySequence(Qt.Key_Escape), self._full, activated=self._exit_full)
        self._full.setStyleSheet("background:%s;" % color.name())
        self._full.showFullScreen()

    def _exit_full(self):
        self._stop_cycle()
        if self._full is not None:
            self._full.close()
            self._full = None

    # -- 自动轮播 -------------------------------------------------------------
    def _toggle_cycle(self):
        if self._cycle_timer is not None:
            self._stop_cycle()
            return
        self._cycle_colors = [c for _n, c in COLORS]
        self._cycle_idx = 0
        self._launch_full(QColor(self._cycle_colors[0]))
        self._cycle_timer = QTimer(self)
        self._cycle_timer.timeout.connect(self._next_cycle)
        self._cycle_timer.start(CYCLE_MS)
        self.btn_cycle.setText("停止轮播")

    def _next_cycle(self):
        self._cycle_idx = (self._cycle_idx + 1) % len(self._cycle_colors)
        if self._full is not None:
            self._full.setStyleSheet("background:%s;" % self._cycle_colors[self._cycle_idx])

    def _stop_cycle(self):
        if self._cycle_timer is not None:
            self._cycle_timer.stop()
            self._cycle_timer = None
            self.btn_cycle.setText("自动轮播（漏光检查）")

    def closeEvent(self, e):
        self._stop_cycle()
        if self._full is not None:
            self._full.close()
        super().closeEvent(e)
