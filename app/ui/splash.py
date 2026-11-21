# -*- coding: utf-8 -*-
"""启动图：应用启动时居中展示动图/静图，主窗口就绪或点击后关闭。
窗口半透明无底色无边框，尺寸由设置页三档（小/中/大）控制。
默认图位于 resources/splash（随包发布），用户自添加图存放于
%LOCALAPPDATA%/SCTools/splash（安装到 Program Files 时该目录可写）。"""
import os
import random
import sys

from PySide6.QtCore import QSize, Qt, QRect, QTimer
from PySide6.QtGui import QColor, QMovie, QPainter, QPixmap
from PySide6.QtWidgets import QLabel, QApplication, QVBoxLayout, QWidget

from app.core import config

IMAGE_EXTS = (".gif", ".png", ".jpg", ".jpeg", ".webp", ".bmp")
MIN_RATIO, MAX_RATIO, DEF_RATIO = 5, 80, 40   # 图片短边占屏幕短边的百分比


def default_dir():
    p = os.path.join(config.APP_DIR, "resources", "splash")
    if not os.path.isdir(p) and getattr(sys, "frozen", False):
        p = os.path.join(config.APP_DIR, "_internal", "resources", "splash")
    return p


def user_dir():
    d = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
                     "SCTools", "splash")
    os.makedirs(d, exist_ok=True)
    return d


def list_images():
    """可用启动图池：默认图 + 用户自添加图"""
    pool = []
    for d in (default_dir(), user_dir()):
        if os.path.isdir(d):
            pool += [os.path.join(d, f) for f in sorted(os.listdir(d))
                     if f.lower().endswith(IMAGE_EXTS)]
    return pool


def user_images():
    """用户自添加的启动图（不含随包默认图），供设置页管理与删除"""
    d = user_dir()
    return [os.path.join(d, f) for f in sorted(os.listdir(d))
            if f.lower().endswith(IMAGE_EXTS)]


def resolve_path(skin):
    """按设置返回本次启动要显示的图路径；关闭返回 None；自定义文件缺失回退随机"""
    mode = skin.get("splash_mode", "random")
    if mode == "off":
        return None
    if mode == "custom":
        p = skin.get("splash_custom", "")
        if p and os.path.isfile(p):
            return p
    pool = list_images()
    return random.choice(pool) if pool else None


def _img_size(skin, base):
    """按设置的百分比等比缩放图片尺寸（占屏幕短边的百分比）"""
    ratio = skin.get("splash_ratio", DEF_RATIO)
    try:
        ratio = max(MIN_RATIO, min(MAX_RATIO, int(ratio))) / 100.0
    except (TypeError, ValueError):
        ratio = DEF_RATIO / 100.0
    scr = QApplication.primaryScreen()
    if scr is None:
        return base
    short = min(scr.availableGeometry().size().width(),
                scr.availableGeometry().size().height())
    limit_w = limit_h = int(short * ratio)
    f = limit_w / max(1, min(base.width(), base.height()))
    return QSize(max(40, int(base.width() * f)), max(25, int(base.height() * f)))


_window_size = _img_size  # 兼容旧名引用


class SplashWindow(QWidget):
    """无边框半透明启动图窗口：GIF 走 QMovie 循环播放，静图走 QPixmap，点击关闭"""

    def __init__(self, image_path, skin=None):
        super().__init__(None)
        self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint
                            | Qt.WindowStaysOnTopHint)
        # 半透明合成：窗口无底色无边框，只显示图片本身
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._movie = None

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        label = QLabel()
        label.setAlignment(Qt.AlignCenter)

        skin = skin or {}
        if image_path.lower().endswith(".gif"):
            self._movie = QMovie(image_path)
            self._movie.jumpToFrame(0)
            base = self._movie.currentPixmap().size()
            self._movie.setScaledSize(_window_size(skin, base))
            label.setMovie(self._movie)
            self._size = self._movie.scaledSize()
        else:
            pm = QPixmap(image_path)
            self._size = _window_size(skin, pm.size())
            label.setPixmap(pm.scaled(self._size, Qt.KeepAspectRatio,
                                      Qt.SmoothTransformation))
        lay.addWidget(label)

        self.resize(self._size)
        # 屏幕居中
        scr = QApplication.primaryScreen()
        if scr is not None:
            avail = scr.availableGeometry()
            self.move(avail.center() - self.rect().center())

        QTimer.singleShot(8000, self.finish)  # 兜底：主窗口迟迟未就绪也自动关闭

    def start(self):
        if self._movie is not None:
            self._movie.start()

    def finish(self):
        """主窗口就绪后调用：停止播放并关闭（可重复调用，避免兜底定时器重复触发）"""
        if getattr(self, "_done", False):
            return
        self._done = True
        if self._movie is not None:
            self._movie.stop()
            self._movie = None
        self.close()
        self.deleteLater()

    def mousePressEvent(self, e):
        self.finish()
        super().mousePressEvent(e)


# 加载指示点动画
_DOT_FRAMES = ("", ".", "..", "...")


class LoadingOverlay(QWidget):
    """窗口内加载覆盖层：主窗口显示后叠加其上，深色遮罩 + 居中启动图（可选）
    + “正在加载中…”动画文字；点击立即关闭，超时自动淡出。
    取代独立启动窗口——主窗口先行，加载状态在窗口内部展示。"""

    def __init__(self, parent, image_path=None, skin=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._skin = skin or {}
        self._movie = None
        self._done = False
        self._dot = 0

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setAlignment(Qt.AlignCenter)
        lay.setSpacing(14)

        if image_path:
            img_box = QLabel()
            img_box.setAlignment(Qt.AlignCenter)
            if image_path.lower().endswith(".gif"):
                self._movie = QMovie(image_path)
                self._movie.jumpToFrame(0)
                base = self._movie.currentPixmap().size()
                self._movie.setScaledSize(_img_size(self._skin, base))
                img_box.setMovie(self._movie)
            else:
                pm = QPixmap(image_path)
                sz = _img_size(self._skin, pm.size())
                img_box.setPixmap(pm.scaled(sz, Qt.KeepAspectRatio,
                                            Qt.SmoothTransformation))
            lay.addWidget(img_box)

        self._tip = QLabel("正在加载中")
        self._tip.setAlignment(Qt.AlignCenter)
        self._tip.setStyleSheet(
            "color: rgba(60,60,60,235); font-size: 15px; letter-spacing: 2px;")
        lay.addWidget(self._tip)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(350)
        self._tick_timer.timeout.connect(self._tick)
        QTimer.singleShot(8000, self.finish)  # 兜底：8 秒仍未就绪也自动关闭

        if parent is not None:
            parent.installEventFilter(self)
            self._sync_geometry()

    def _tick(self):
        """“正在加载中” 后的点号循环动画"""
        self._dot = (self._dot + 1) % len(_DOT_FRAMES)
        self._tip.setText("正在加载中" + _DOT_FRAMES[self._dot])

    def _sync_geometry(self):
        if self.parentWidget() is not None:
            self.setGeometry(self.parentWidget().rect())
            self.raise_()

    def eventFilter(self, obj, event):
        if obj is self.parentWidget() and event.type() == event.Type.Resize:
            self._sync_geometry()
            return False
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        # 纯不透明白底：加载期间完全遮住主窗口内容（用户视角是“模糊/被盖住”），
        # 就绪淡出后才露出应用界面；避免半透明遮罩透出后续内容。
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255, 255))
        super().paintEvent(event)

    def start(self):
        if self._movie is not None:
            self._movie.start()
        self._tick_timer.start()

    def finish(self):
        """就绪后调用：淡出并销毁（可重复调用）"""
        if getattr(self, "_done", False):
            return
        self._done = True
        if self._movie is not None:
            self._movie.stop()
            self._movie = None
        self._tick_timer.stop()
        from PySide6.QtWidgets import QGraphicsOpacityEffect
        eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(eff)
        from PySide6.QtCore import QPropertyAnimation
        anim = QPropertyAnimation(eff, b"opacity", self)
        anim.setDuration(260)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.finished.connect(self.close)
        anim.finished.connect(self.deleteLater)
        anim.start(QPropertyAnimation.DeleteWhenStopped)

    def mousePressEvent(self, e):
        self.finish()
        super().mousePressEvent(e)
