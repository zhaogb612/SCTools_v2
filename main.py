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
    sp = resolve_path(skin)
    overlay = None
    if sp or skin.get("splash_mode") != "off":
        overlay = LoadingOverlay(win, sp, skin)
    # 白色覆盖层先于主窗口 show()：首帧绘制即包含白底，
    # 从启动到淡出整个过程中应用内容都不外露（消除“先闪一下界面再跳白底”）
    if overlay is not None:
        overlay.show()
    win.show()
    if overlay is not None:
        overlay.raise_()
        overlay.start()
    # 保证首帧真正绘制出来之后，加载覆盖层已就位
    for _ in range(6):
        app.processEvents()
        time.sleep(0.02)
    app.processEvents()

    def _finish_overlay():
        if overlay is not None:
            overlay.finish()

    if overlay is not None:
        # 至少展示 MIN_SPLASH_MS 后淡出
        QTimer.singleShot(MIN_SPLASH_MS, _finish_overlay)

    # 自动检查更新（设置中开启时）：等窗口就绪后静默查询，发现新版本才弹出提示
    if skin.get("auto_check_update", False):
        from app.core import updater
        from app.ui.settings_page import UpdateDialog

        def _auto_fetch():
            try:
                return updater.fetch_latest(timeout=10)
            except Exception:
                return None

        def _auto_result(info):
            # 该槽由 QThread 信号在队列中触发，运行于主线程，可安全弹窗
            if info:
                dlg = UpdateDialog(win, info)
                dlg.exec()

        _t = updater.FnThread(_auto_fetch, win)
        _t.done.connect(_auto_result)
        QTimer.singleShot(2500, _t.start)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
