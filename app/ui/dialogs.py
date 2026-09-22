# -*- coding: utf-8 -*-
"""统一弹窗：方角、自定义标题栏（可拖动/关闭）、纯文字，风格与主程序一致"""
import sys

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QVBoxLayout, QWidget)

from app.ui import icons


class SquareMenu(QMenu):
    """方角菜单：QSS 只能去掉 QSS 层圆角，Win11 的系统级弹窗圆角需 DWM 关闭"""

    def __init__(self, parent=None):
        super().__init__(parent)
        if sys.platform == "win32":
            # 开启半透明：QSS 中的 rgba 背景才能生效，面板不透明度设置对菜单可见
            self.setAttribute(Qt.WA_TranslucentBackground, True)

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = int(self.winId())
                pref = ctypes.c_int(1)  # DWMWCP_DONOTROUND
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 33, ctypes.byref(pref), 4)  # DWMWA_WINDOW_CORNER_PREFERENCE
            except Exception:
                pass


class AppDialog(QDialog):
    """无系统边框的自定义弹窗基类；子类通过 content_layout() 添加内容"""

    def __init__(self, parent, title):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setModal(True)
        self._drag = False
        self._drag_pos = QPoint()

        root = QVBoxLayout(self)
        root.setContentsMargins(1, 1, 1, 1)
        root.setSpacing(0)

        # 自定义标题栏
        bar = QFrame()
        bar.setObjectName("DlgBar")
        bar.setFixedHeight(36)
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(14, 0, 8, 0)
        t = QLabel(title)
        t.setObjectName("DlgTitle")
        bl.addWidget(t)
        bl.addStretch()
        close_btn = QPushButton()
        close_btn.setObjectName("DlgClose")
        close_btn.setFixedSize(22, 22)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setToolTip("关闭")
        close_btn.clicked.connect(self.reject)
        bl.addWidget(close_btn)
        root.addWidget(bar)

        # 内容区
        self._body = QFrame()
        self._body.setObjectName("DlgBody")
        self._content = QVBoxLayout(self._body)
        self._content.setContentsMargins(20, 16, 20, 16)
        self._content.setSpacing(10)
        root.addWidget(self._body)

    def content_layout(self):
        return self._content

    def paintEvent(self, e):
        from PySide6.QtGui import QPainter, QColor
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(self.palette().color(self.backgroundRole())))
        p.setPen(QColor(128, 128, 128, 120))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        super().paintEvent(e)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag = True
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
        super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._drag and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._drag = False
        super().mouseReleaseEvent(e)


def _btn(text, obj_name, slot):
    b = QPushButton(text)
    b.setObjectName(obj_name)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(slot)
    return b


class AppMessageBox(AppDialog):
    """纯文字消息框：info/warning 仅确定，question 返回 bool；无系统图标"""

    def __init__(self, parent, title, text, question=False):
        super().__init__(parent, title)
        self.setFixedWidth(360)
        msg = QLabel(text)
        msg.setWordWrap(True)
        self.content_layout().addWidget(msg)
        self.content_layout().addSpacing(6)
        row = QHBoxLayout()
        row.addStretch()
        if question:
            row.addWidget(_btn("取消", "Ghost", self.reject))
            row.addWidget(_btn("确定", "Accent", self.accept))
        else:
            row.addWidget(_btn("确定", "Accent", self.accept))
        self.content_layout().addLayout(row)

    @staticmethod
    def info(parent, title, text):
        AppMessageBox(parent, title, text).exec_()

    warning = info

    @staticmethod
    def question(parent, title, text):
        return AppMessageBox(parent, title, text, question=True).exec_() == QDialog.Accepted
