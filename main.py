#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCTools2 工具箱入口（PySide6）"""
import os
import sys
import time

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.ui import icons
from app.core.theme import FONT_STACK
from app.ui.main_window import MainWindow, APP_ICON


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SCTools2")
    if os.path.exists(APP_ICON):
        app.setWindowIcon(QIcon(APP_ICON))

    # 中文字体回退链，保证不同系统下显示正常
    font = QFont()
    font.setFamilies(["Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC",
                      "Noto Sans CJK SC", "SimHei", "sans-serif"])
    font.setPointSize(10)
    app.setFont(font)
    _ = FONT_STACK  # QSS 内同步使用回退链

    icons.ensure_icon_files()

    # 启动加载：主窗口先行，加载覆盖层（启动图 + “正在加载中…”）在窗口内展示。
    # 主窗口就绪即淡出，但保证至少可见 MIN_SPLASH_MS，避免一闪而过
    MIN_SPLASH_MS = 1500
    from app.core import config
    from app.core.theme import DEFAULT_SKIN
    app.setApplicationVersion(config.APP_VER)
    from app.ui.splash import LoadingOverlay, resolve_path
    skin = config.load_json("skin.json", dict(DEFAULT_SKIN))

    win = MainWindow()
    win.show()
    # 保证首帧真正绘制出来，再叠加加载覆盖层
    for _ in range(6):
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()

    overlay = None
    sp = resolve_path(skin)
    if sp or skin.get("splash_mode") != "off":
        overlay = LoadingOverlay(win, sp, skin)
        overlay.show()
        overlay.start()
        app.processEvents()

    t0 = time.monotonic()

    def _finish_overlay():
        if overlay is not None:
            overlay.finish()

    if overlay is not None:
        # 至少展示 MIN_SPLASH_MS 后淡出
        QTimer.singleShot(MIN_SPLASH_MS, _finish_overlay)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
