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

    # 启动图：MainWindow 构建期间展示；就绪即撤下，但保证至少可见 MIN_SPLASH_MS，
    # 避免启动过快时启动图一闪而过（等于没显示）
    MIN_SPLASH_MS = 1500
    from app.core import config
    from app.core.theme import DEFAULT_SKIN
    app.setApplicationVersion(config.APP_VER)
    from app.ui.splash import SplashWindow, resolve_path
    splash = None
    t0 = time.monotonic()
    skin = config.load_json("skin.json", dict(DEFAULT_SKIN))
    sp = resolve_path(skin)
    if sp:
        splash = SplashWindow(sp, skin)
        splash.show()
        splash.start()  # 启动 GIF 播放
        # 多轮 processEvents 确保首帧真正绘制出来，再进入耗时初始化
        for _ in range(6):
            app.processEvents()
            time.sleep(0.02)
        app.processEvents()

    win = MainWindow()
    win.show()
    app.processEvents()
    if splash is not None:
        # 剩余可见时长：主窗口就绪得早则补足最短时长后再撤下，就绪得晚则立刻撤下
        remain = int(MIN_SPLASH_MS - (time.monotonic() - t0) * 1000)
        if remain > 0:
            QTimer.singleShot(remain, splash.finish)
        else:
            splash.finish()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
