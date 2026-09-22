# -*- coding: utf-8 -*-
"""主窗口：自绘背景（支持模糊）+ 侧边导航 + 页面栈，皮肤/主题热切换；
无边框窗口支持边缘拖拽缩放；使用 resources/app.ico 作为程序图标"""
import os

from PySide6.QtCore import QPoint, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsBlurEffect,
                               QGraphicsScene, QHBoxLayout, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow,
                               QStackedWidget, QVBoxLayout, QWidget)

from app.core import config
from app.core.app_manager import AppManager
from app.core.hotkey import HotkeyManager, parse_hotkey
from app.core.nav_manager import NavManager
from app.core.theme import DEFAULT_SKIN, SCHEMES, build_qss, palette
from app.ui import icons
from app.ui.check_page import CheckPage
from app.ui.nav_page import NavPage
from app.ui.settings_page import SettingsPage
from app.ui.title_bar import TitleBar
from app.ui.tools_page import ToolsPage

CATEGORY_ICON = {"系统工具": "system", "磁盘工具": "disk", "硬件检测": "chip",
                 "系统优化": "spark", "其他工具": "layers", "网络工具": "globe"}

FAV_VIEW_NAME = "我的收藏"

NAV_PAGE_NAME = "网站导航"
SET_PAGE_NAME = "设置与皮肤"
CHECK_PAGE_NAME = "配置检测"

APP_ICON = os.path.join(config.ICON_DIR, "..", "app.ico")
_EDGE = 6  # 边缘拖拽缩放热区宽度


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SC Tools")
        self.setWindowFlag(Qt.FramelessWindowHint)
        if os.path.exists(APP_ICON):
            self.setWindowIcon(QIcon(APP_ICON))
        self.resize(1060, 680)
        self.setMinimumSize(920, 600)

        self.app_manager = AppManager()
        self.app_manager.builtin_handler = self._open_builtin  # 内置功能（坏点检测等）
        self.nav_manager = NavManager()
        self.skin = config.load_json("skin.json", dict(DEFAULT_SKIN))
        self._palette_data = palette(self.skin.get("scheme", "晴空蓝"), self.skin.get("mode", "day"))
        self._bg_pixmap = None
        self._blur_cache = None  # ((size, blur, path), pixmap)
        # 无边框窗口：全局事件过滤器实现边缘拖拽缩放
        QApplication.instance().installEventFilter(self)

        central = QWidget()
        central.setObjectName("Root")
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self.title_bar = TitleBar(self)
        outer.addWidget(self.title_bar)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        outer.addLayout(body, 1)

        # 侧边栏
        side = QFrame()
        side.setObjectName("Sidebar")
        side.setFixedWidth(192)
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(10, 12, 10, 12)
        side_lay.setSpacing(10)

        self.search = QLineEdit()
        self.search.setObjectName("SearchBox")
        self.search.setPlaceholderText("搜索应用...")
        self.search.textChanged.connect(self._on_search)
        side_lay.addWidget(self.search)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("NavList")
        self.nav_list.setFrameShape(QListWidget.NoFrame)
        self.nav_list.setSpacing(2)
        self.nav_list.setMouseTracking(True)  # 侧边项悬浮提示
        self.nav_list.itemEntered.connect(self._on_nav_hover)
        side_lay.addWidget(self.nav_list, 1)
        body.addWidget(side)

        # 页面栈
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.tools_page = ToolsPage(self)
        self.nav_page = NavPage(self)
        self.settings_page = SettingsPage(self)
        self.check_page = CheckPage(self)
        self.stack.addWidget(self.tools_page)
        self.stack.addWidget(self.nav_page)
        self.stack.addWidget(self.settings_page)
        self.stack.addWidget(self.check_page)

        self._fill_sidebar()
        self.nav_list.currentRowChanged.connect(self._on_nav)
        self.nav_list.setCurrentRow(0)
        self.apply_theme(initial=True)
        # 全局热键呼出主窗口
        self.hotkey = HotkeyManager(self._hotkey_raise)
        self.apply_hotkey()

    # -- 全局热键 -----------------------------------------------------------
    def apply_hotkey(self):
        if self.skin.get("global_hotkey", True):
            parsed = parse_hotkey(self.skin.get("hotkey_label", "Ctrl+Alt+S"))
            if parsed is None:  # 配置损坏时回退默认
                parsed = parse_hotkey("Ctrl+Alt+S")
            ok = self.hotkey.register(*parsed)
            self.skin["hotkey_ok"] = bool(ok)
        else:
            self.hotkey.unregister()
        config.save_json("skin.json", self.skin)

    def _hotkey_raise(self):
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()

    def _open_builtin(self, name):
        """内置功能入口（builtin://name），目前：屏幕坏点/漏光测试"""
        if name == "screen_test":
            from app.ui.screen_test import ScreenTestDialog
            dlg = ScreenTestDialog(self)
            dlg.setWindowFlag(Qt.Window)
            dlg.show()

    def closeEvent(self, event):
        # 停掉后台线程，避免退出时 QThread 仍在运行
        self.tools_page._watcher.stop()
        self.tools_page._watcher.wait(3000)
        self.tools_page.stop_workers()
        self.nav_page.stop_workers()
        self.hotkey.unregister()
        super().closeEvent(event)

    # -- 边缘拖拽缩放 -------------------------------------------------------
    def eventFilter(self, obj, event):
        # 应用级过滤器：本窗口边缘 6px 内按下即开始系统级缩放
        et = event.type()
        if et == event.Type.MouseButtonPress and not self.isMaximized() and self.isActiveWindow():
            edges = self._edge_at(event.globalPosition().toPoint())
            if edges:
                self.windowHandle().startSystemResize(edges)
                return True
        return super().eventFilter(obj, event)

    def _edge_at(self, global_pos):
        """返回光标所在窗口边缘方向（Qt.Edges），不在热区返回空"""
        if self.isMaximized():
            return Qt.Edges()
        top_left = self.mapToGlobal(QPoint(0, 0))
        rect = QRect(top_left, self.size())
        if not rect.adjusted(-_EDGE, -_EDGE, _EDGE, _EDGE).contains(global_pos):
            return Qt.Edges()
        edges = Qt.Edges()
        if global_pos.x() <= top_left.x() + _EDGE:
            edges |= Qt.LeftEdge
        if global_pos.x() >= top_left.x() + self.width() - _EDGE:
            edges |= Qt.RightEdge
        if global_pos.y() <= top_left.y() + _EDGE:
            edges |= Qt.TopEdge
        if global_pos.y() >= top_left.y() + self.height() - _EDGE:
            edges |= Qt.BottomEdge
        return edges

    # -- 悬浮提示 ----------------------------------------------------------
    def set_hint(self, text):
        if not text:
            text = self._default_hint()
        self.title_bar.set_hint(text)

    def _default_hint(self):
        w = self.stack.currentWidget()
        if w is self.nav_page:
            return "网站导航：点击分类标签切换，右键网址卡片可编辑/删除"
        if w is self.settings_page:
            return "设置：配色方案、日/夜模式、背景图与透明度"
        if w is self.check_page:
            return "配置检测：查看本机硬件与系统配置（CPU/内存/显卡/硬盘等）"
        return "SC Tools"

    def _on_nav_hover(self, item):
        name = item.text()
        if name == NAV_PAGE_NAME:
            hint = "常用网站与推荐应用下载入口"
        elif name == SET_PAGE_NAME:
            hint = "主题、背景与日/夜模式设置"
        elif name == CHECK_PAGE_NAME:
            hint = "检测本机硬件与系统配置，附带配置文件扫描"
        elif name == FAV_VIEW_NAME:
            hint = "我的收藏：收藏的应用集中显示，右键卡片可取消收藏"
        else:
            n = len(self.app_manager.by_category(name))
            hint = "{}：包含 {} 个应用".format(name, n)
        self.title_bar.set_hint(hint)

    # -- 侧边栏 ------------------------------------------------------------
    def _fill_sidebar(self):
        self.nav_list.blockSignals(True)
        self.nav_list.clear()
        entries = [(CHECK_PAGE_NAME, "info"), (FAV_VIEW_NAME, "star")] + \
                  [(c, CATEGORY_ICON.get(c, "all")) for c in self.app_manager.categories] + \
                  [(NAV_PAGE_NAME, "globe"), (SET_PAGE_NAME, "settings")]
        for name, icon_name in entries:
            item = QListWidgetItem(icons.icon(icon_name, self._palette_data["sidebar_sub"]), name)
            self.nav_list.addItem(item)
        self.nav_list.blockSignals(False)

    def _on_nav(self, row):
        name = self.nav_list.item(row).text() if row >= 0 else ""
        if name == NAV_PAGE_NAME:
            self.stack.setCurrentWidget(self.nav_page)
        elif name == SET_PAGE_NAME:
            self.stack.setCurrentWidget(self.settings_page)
        elif name == CHECK_PAGE_NAME:
            self.stack.setCurrentWidget(self.check_page)
        else:
            self.tools_page.set_category(name or "全部应用")
            self.stack.setCurrentWidget(self.tools_page)
        self.set_hint("")

    def _on_search(self, text):
        if self.stack.currentWidget() is not self.tools_page:
            # 跳到第一个工具分类（行 0 是配置检测页）
            self.nav_list.setCurrentRow(1 if self.nav_list.count() > 1 else 0)
        self.tools_page.set_filter(text)

    # -- 皮肤 --------------------------------------------------------------
    def palette_data(self):
        return self._palette_data

    def apply_theme(self, initial=False):
        scheme = self.skin.get("scheme", "晴空蓝")
        custom = None
        if scheme == "自定义" or scheme not in SCHEMES:
            for t in self.skin.get("custom_themes", []):
                if t.get("name") == scheme:
                    custom = t
                    break
            if custom is None:
                custom = {"brand": self.skin.get("custom_brand", ""),
                          "bg": self.skin.get("custom_bg", "")}
        self._palette_data = palette(scheme, self.skin.get("mode", "day"), custom)
        bg = self.skin.get("bg_image", "")
        if bg and os.path.exists(bg):
            self._bg_pixmap = QPixmap(bg)
        else:
            self._bg_pixmap = None
            self.skin["bg_image"] = ""
        self._blur_cache = None
        self._win_qss = build_qss(self._palette_data, self.skin.get("opacity", 92))
        self.window().setStyleSheet(self._win_qss)
        config.save_json("skin.json", self.skin)
        # 侧边栏图标随主题适配色（白天深灰、夜间浅灰）
        ic_color = self._palette_data["sidebar_sub"]
        for row in range(self.nav_list.count()):
            item = self.nav_list.item(row)
            name = item.text()
            if name == NAV_PAGE_NAME:
                ic = "globe"
            elif name == SET_PAGE_NAME:
                ic = "settings"
            elif name == CHECK_PAGE_NAME:
                ic = "info"
            elif name == FAV_VIEW_NAME:
                ic = "star"
            elif name == "全部应用":
                ic = "all"
            else:
                ic = CATEGORY_ICON.get(name, "all")
            item.setIcon(icons.icon(ic, ic_color))
        self.title_bar.refresh_icons()
        self.title_bar.set_style(self.skin.get("titlebar_style", "mac"))
        # 设置页日夜按钮与标题栏切换联动
        self.settings_page.sync_mode(self.skin.get("mode", "day"))
        # 工具/导航卡片内图标随主题刷新
        self.tools_page.refresh_theme()
        self.nav_page.refresh_theme()
        if not initial:
            self.update()

    def reload_config(self):
        """配置导入后整体重载：管理器重新读文件、重建设置页、全部页面刷新"""
        self.app_manager.reload()
        self.nav_manager.reload()
        self.skin = config.load_json("skin.json", dict(DEFAULT_SKIN))
        self.apply_theme(initial=True)
        self._fill_sidebar()
        row = max(0, self.nav_list.currentRow())
        self.nav_list.setCurrentRow(row)
        self.tools_page.rebuild()
        self.check_page.reset()
        self.nav_page.rebuild()
        idx = self.stack.indexOf(self.settings_page)
        self.settings_page.deleteLater()
        self.settings_page = SettingsPage(self)
        self.stack.insertWidget(idx, self.settings_page)
        self.stack.setCurrentWidget(self.settings_page)

    def reload_all_pages(self):
        self._fill_sidebar()
        row = max(0, self.nav_list.currentRow())
        self.nav_list.setCurrentRow(row)
        self.tools_page.rebuild()
        self.check_page.reset()

    # -- 背景绘制（含模糊） ---------------------------------------------------
    def _blurred_bg(self):
        blur = int(self.skin.get("blur", 0))
        if blur <= 0 or self._bg_pixmap is None:
            return self._bg_pixmap
        key = (self._bg_pixmap.cacheKey(), blur)
        if self._blur_cache and self._blur_cache[0] == key:
            return self._blur_cache[1]
        pm = self._bg_pixmap
        # 降采样-升采样近似高斯模糊；非线性曲线保证 100% 时背景完全不可辨
        factor = 2 + 38 * (blur / 100.0) ** 1.5
        small = pm.scaled(max(1, int(pm.width() / factor)), max(1, int(pm.height() / factor)),
                          Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        out = small.scaled(pm.width(), pm.height(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        self._blur_cache = (key, out)
        return out

    def paintEvent(self, event):
        painter = QPainter(self)
        bg = self._blurred_bg()
        if bg is not None and not bg.isNull():
            scaled = bg.scaled(self.size(), Qt.KeepAspectRatioByExpanding,
                               Qt.SmoothTransformation)
            x = (self.width() - scaled.width()) // 2
            y = (self.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
        else:
            painter.fillRect(self.rect(), QColor(self._palette_data["bg"]))
        super().paintEvent(event)
