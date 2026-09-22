#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SCTools 工具箱 v3.0 (PySide6) 入口"""
import os
import sys

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from app.ui import icons
from app.core.theme import FONT_STACK
from app.ui.main_window import MainWindow, APP_ICON


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("SC Tools")
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
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
