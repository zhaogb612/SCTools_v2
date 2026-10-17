#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCTools2 工具箱入口（PySide6）"""
import os
import sys
import time

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

    # 启动图：MainWindow 构建期间展示，主窗口首帧绘出后立即撤下
    from app.core import config
    from app.core.theme import DEFAULT_SKIN
    app.setApplicationVersion(config.APP_VER)
    from app.ui.splash import SplashWindow, resolve_path
    splash = None
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
        splash.finish()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
