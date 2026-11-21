# -*- coding: utf-8 -*-
"""统一弹窗：方角、自定义标题栏（可拖动/关闭）、纯文字，风格与主程序一致"""
import sys

from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import (QDialog, QFrame, QHBoxLayout, QLabel, QMenu,
                               QPushButton, QVBoxLayout, QWidget)

from app.ui import icons


class SquareMenu(QMenu):
    """方角菜单：QSS 只能去掉 QSS 层圆角，Win11 的系统级弹窗圆角需 DWM 关闭。
    背景一律实心（内联主题色覆盖全局带透明度的 QSS）：
    半透明会让菜单走 LAYERED 合成路径，部分环境渲染异常导致
    “右键收藏弹出后一闪而过/看不清”，实心后任何机器都稳定可读。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        if sys.platform == "win32":
            # 注意：不启用 WA_TranslucentBackground（会变 LAYERED，QSS 渲染不稳）
            self.setWindowFlags(self.windowFlags()
                                | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)

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
            self._apply_solid_style()

    def _apply_solid_style(self):
        """实心背景：沿父链取当前主题面板色/文字色，内联覆盖全局
        （带面板不透明度 alpha 的）QSS，保证菜单任何时候都不透明、不闪现"""
        p = None
        cur = self.parent()
        while cur is not None:
            d = getattr(cur, "_palette_data", None)
            if isinstance(d, dict) and d.get("panel"):
                p = d
                break
            cur = cur.parentWidget() if hasattr(cur, "parentWidget") else None
        if not p:
            return
        panel = p.get("panel", "#FFFFFF")
        text = p.get("text", "#2A2F36")
        selected = p.get("selected", "#D8ECF9")
        accent = p.get("accent", "#3F5AA9")
        border = p.get("border", "#C9D6DE")
        self.setStyleSheet(
            "QMenu {{ background: {panel}; color: {text}; border: 1px solid {border};"
            " padding: 3px 0; margin: 0; }}"
            "QMenu::item {{ padding: 6px 24px 6px 10px; font-size: 12px;"
            " background: transparent; }}"
            "QMenu::icon {{ margin-left: 10px; margin-right: 8px; padding: 0; }}"
            "QMenu::item:selected {{ background: {selected}; color: {accent}; }}"
            "QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}"
            .format(panel=panel, text=text, selected=selected,
                    accent=accent, border=border))


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
        close_btn.setIcon(icons.icon("close", self._on_brand()))
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

    def _on_brand(self):
        """标题栏关闭按钮颜色：沿父级链找 _palette_data 里的 titlebar/on_brand。
        弹窗标题栏背景为不透明主题色，直接按该色亮度选深/浅前景，保证任何主题下可见"""
        try:
            from app.core.theme import on_brand_for
        except Exception:
            on_brand_for = None
        cur = self.parent()
        while cur is not None:
            p = getattr(cur, "_palette_data", None)
            if isinstance(p, dict) and p.get("titlebar"):
                if on_brand_for:
                    return on_brand_for(p["titlebar"])
                return p.get("on_brand") or "#FFFFFF"
            cur = cur.parent()
        p = getattr(self, "_palette_data", None)
        if isinstance(p, dict) and p.get("titlebar") and on_brand_for:
            return on_brand_for(p["titlebar"])
        return "#888888"

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
