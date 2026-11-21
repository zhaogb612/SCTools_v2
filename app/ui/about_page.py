# -*- coding: utf-8 -*-
"""关于页：当前版本、应用简介、项目地址、作者、开源协议，
以及检查更新与打开缓存文件夹（配置导入导出/恢复默认/清除缓存位于设置页）"""
import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QVBoxLayout, QWidget)

from app.core import config


def _cache_dir():
    """图标缓存目录（与 favicon/file_icon 保持一致）"""
    try:
        from app.core import favicon
        return favicon.CACHE_DIR
    except Exception:
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, "SCTools", "cache")


def _label(text, obj):
    lbl = QLabel(text)
    lbl.setObjectName(obj)
    return lbl


def _btn(text, obj_name, slot):
    b = QPushButton(text)
    b.setObjectName(obj_name)
    b.setCursor(Qt.PointingHandCursor)
    b.clicked.connect(slot)
    return b


class AboutPage(QScrollArea):
    """「关于」侧栏页：应用信息展示 + 检查更新 / 打开缓存文件夹
    （配置导出导入、恢复默认与清除缓存位于设置页「配置与维护」区块）"""

    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window
        self.setWidgetResizable(True)
        self.setFrameShape(QScrollArea.NoFrame)

        body = QWidget()
        body.setObjectName("AboutBody")
        root = QVBoxLayout(body)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(12)
        self.setWidget(body)

        # 头部：应用名 + 版本
        head = QHBoxLayout()
        head.setSpacing(10)
        head.addWidget(_label("SCTools2", "AboutTitle"))
        self.ver_label = QLabel("v" + config.APP_VER)
        self.ver_label.setObjectName("AboutVersion")
        head.addWidget(self.ver_label)
        head.addStretch()
        root.addLayout(head)

        # 简介（详细）
        intro = QLabel(
            "SCTools2 是一款基于 PySide6（Qt6）开发的 Windows 工具箱，"
            "将常用系统工具、磁盘工具、硬件检测、系统优化与网络工具集中到一个界面，"
            "支持自定义应用清单、收藏、快捷启动、右键菜单与网站导航。\n\n"
            "项目特性：\n"
            "· 全部工具分类展示，双击启动、拖动排序、右键管理；\n"
            "· 多套配色方案、日夜模式、背景图与面板透明度自由搭配；\n"
            "· 我的收藏视图与应用搜索，快速直达常用工具；\n"
            "· 网站导航分组管理与 favicon 自动抓取；\n"
            "· 配置一键导出/导入，便于换机迁移；内置在线检查更新。")
        intro.setObjectName("Sub")
        intro.setWordWrap(True)
        root.addWidget(intro)
        root.addSpacing(4)

        # 信息行：项目地址 / 作者
        proj = QHBoxLayout()
        proj.setSpacing(8)
        proj.addWidget(_label("项目地址", "AboutField"))
        link = QLabel('<a href="https://github.com/zhaogb612/SCTools_v2" '
                      'style="color:%s;">%s</a>' % (
                          self._link_color(), "github.com/zhaogb612/SCTools_v2"))
        link.setOpenExternalLinks(True)
        link.setCursor(Qt.PointingHandCursor)
        proj.addWidget(link)
        proj.addStretch()
        root.addLayout(proj)

        author = QHBoxLayout()
        author.setSpacing(8)
        author.addWidget(_label("作者", "AboutField"))
        author.addWidget(_label("沙尘612（zhaogb612）", "Sub"))
        author.addStretch()
        root.addLayout(author)

        lic = QHBoxLayout()
        lic.setSpacing(8)
        lic.addWidget(_label("开源协议", "AboutField"))
        lic.addWidget(_label("MIT License", "Sub"))
        lic.addStretch()
        root.addLayout(lic)

        # 分隔 + 操作按钮
        sep = QFrame()
        sep.setObjectName("AboutSep")
        sep.setFixedHeight(1)
        root.addWidget(sep)
        root.addSpacing(2)

        self.btn_check = _btn("检查更新", "Accent", self._check_update)
        root.addWidget(self.btn_check)

        ops = QHBoxLayout()
        ops.setSpacing(8)
        btn_cache_dir = _btn("打开缓存文件夹", "Ghost", self._open_cache_dir)
        ops.addWidget(btn_cache_dir)
        ops.addStretch()
        root.addLayout(ops)

        tip = QLabel("配置导出/导入、恢复默认配置与清除缓存请在「设置与皮肤」页中操作；"
                     "缓存位于 %LOCALAPPDATA%\\SCTools\\cache，清理后图标会在下次启动时重新生成。")
        tip.setObjectName("AboutTip")
        tip.setWordWrap(True)
        root.addWidget(tip)

        root.addStretch()

    # -- 操作 --------------------------------------------------------------
    def _link_color(self):
        p = getattr(self._win, "_palette_data", None)
        if isinstance(p, dict) and p.get("accent"):
            return p["accent"]
        return "#3F5AA9"

    def _check_update(self):
        from app.core import updater
        from app.ui.settings_page import UpdateDialog
        from app.ui.dialogs import AppMessageBox
        self.btn_check.setEnabled(False)
        self.btn_check.setText("检查中...")
        self._upd_thread = updater.FnThread(updater.fetch_latest, self)
        self._upd_thread.done.connect(
            lambda info: self._on_update_info(info, UpdateDialog, AppMessageBox))
        self._upd_thread.fail.connect(
            lambda msg: self._on_update_fail(msg, AppMessageBox))
        self._upd_thread.start()

    def _on_update_info(self, info, UpdateDialog, AppMessageBox):
        self.btn_check.setEnabled(True)
        self.btn_check.setText("检查更新")
        if info is None:
            AppMessageBox.info(self, "检查更新", "当前已是最新版本。")
            return
        dlg = UpdateDialog(self, info)
        dlg.exec()

    def _on_update_fail(self, msg, AppMessageBox):
        self.btn_check.setEnabled(True)
        self.btn_check.setText("检查更新")
        AppMessageBox.warning(self, "检查更新失败",
                              msg + "\n\nGitHub 在部分网络环境下可能无法直连，"
                                    "可稍后重试或到项目发布页手动下载。")

    def _open_cache_dir(self):
        d = _cache_dir()
        if os.path.isdir(d):
            QDesktopServices.openUrl(QUrl.fromLocalFile(d))
        else:
            from app.ui.dialogs import AppMessageBox
            AppMessageBox.info(self, "打开缓存文件夹",
                               "缓存目录尚未创建：\n" + d + "\n\n首次抓取图标后会自动生成。")