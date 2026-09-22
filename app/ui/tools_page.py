# -*- coding: utf-8 -*-
"""工具箱页面：卡片（应用图标/收藏星/运行绿点）+ 流式布局 + 拖拽排序 + 悬浮提示"""
import os
import subprocess

from PySide6.QtCore import QMimeData, QPoint, Qt, QThread, Signal
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel,
                               QScrollArea, QPushButton, QVBoxLayout, QWidget)

from app.core import file_icon
from app.ui import icons
from app.ui.dialogs import AppMessageBox, SquareMenu
from app.ui.flow_layout import FlowLayout
from app.ui.tool_dialog import ToolDialog

CARD_H = 46
CARD_MIN_W = 180  # 填满模式下的最小卡宽，窗口宽度据此决定每行列数
GAP = 10
ICON_SIZE = 30
MIME = "application/x-sctools-tool"


class RunningWatcher(QThread):
    """后台定期扫描进程列表（tasklist），回报运行中进程名集合"""
    refreshed = Signal(set)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False
        self._force = False

    def force_refresh(self):
        self._force = True

    def stop(self):
        self._stop = True
        self._force = True

    def run(self):
        while not self._stop:
            names = set()
            try:
                out = subprocess.run(["tasklist", "/fo", "csv", "/nh"],
                                     creationflags=0x08000000, capture_output=True)
                for line in out.stdout.decode("gbk", errors="replace").splitlines():
                    if line.startswith('"'):
                        names.add(line.split('","')[0].strip('"').lower())
            except OSError:
                pass
            self.refreshed.emit(names)
            # 5 秒一轮，可被 force_refresh 提前唤醒
            for _ in range(50):
                if self._stop or self._force:
                    break
                self.msleep(100)
            self._force = False
            if self._stop:
                break


class ToolCard(QFrame):
    def __init__(self, page, tool):
        super().__init__()
        self._page = page
        self._tool = tool
        self._press_pos = QPoint(0, 0)
        self._dragging = False
        self.setObjectName("Card")
        self.setFixedHeight(CARD_H)
        self.setMinimumWidth(120)
        self.setCursor(Qt.PointingHandCursor)
        self.setAcceptDrops(True)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 10, 6)
        lay.setSpacing(10)
        self.icon_label = None
        if page.show_icons():
            self.icon_label = QLabel()
            self.icon_label.setFixedSize(ICON_SIZE, ICON_SIZE)
            self.icon_label.setAlignment(Qt.AlignCenter)
            self._refresh_icon()
            lay.addWidget(self.icon_label)
        self.name_label = QLabel(tool["name"])
        self.name_label.setObjectName("CardName")
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.name_label, 1)
        # 收藏星标（仅收藏的应用显示）
        self.star_label = QLabel()
        self.star_label.setFixedSize(14, 14)
        self.star_label.setPixmap(icons.icon("star", "#F5B301").pixmap(14, 14))
        self.star_label.setVisible(bool(tool.get("favorite", False)))
        lay.addWidget(self.star_label)
        # 运行状态绿点
        self.run_dot = QLabel()
        self.run_dot.setFixedSize(9, 9)
        self.run_dot.setStyleSheet(
            "background:#3CB371; border-radius:4px;")
        self.run_dot.setToolTip("运行中")
        self.run_dot.setVisible(False)
        lay.addWidget(self.run_dot)

    def set_running(self, running_names):
        exe = os.path.basename(self._page._win.app_manager.resolve(self._tool.get("path", "")))
        self.run_dot.setVisible(bool(exe) and exe.lower() in running_names)

    # -- 图标 ---------------------------------------------------------------
    def _refresh_icon(self):
        if self.icon_label is None:
            return
        am = self._page._win.app_manager
        ic = file_icon.icon_for(am.resolve(self._tool.get("path", "")), ICON_SIZE)
        if ic is None:
            # 提取失败回退内置应用图标（随主题着色）
            ic = icons.icon("app", self._page._win.palette_data()["on_brand"])
        self.icon_label.setPixmap(ic.pixmap(ICON_SIZE, ICON_SIZE))

    # -- 悬浮提示 ----------------------------------------------------------
    def enterEvent(self, e):
        t = self._tool
        self._page.set_hint("{} — {}".format(t["name"], t.get("description", "")))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._page.set_hint("")
        super().leaveEvent(e)

    def set_tool(self, tool):
        self._tool = tool
        self.name_label.setText(tool["name"])
        self._refresh_icon()

    def tool(self):
        return self._tool

    # -- 点击/双击启动 / 拖拽排序 ---------------------------------------------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press_pos = e.position().toPoint()
            self._dragging = False
        elif e.button() == Qt.RightButton:
            self._page.show_card_menu(self._tool, self.mapToGlobal(e.position().toPoint()))
        super().mousePressEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._page.launch(self._tool)
        super().mouseDoubleClickEvent(e)

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton and not self._dragging:
            if (e.position().toPoint() - self._press_pos).manhattanLength() > 12:
                self._dragging = True
                drag = QDrag(self)
                mime = QMimeData()
                mime.setData(MIME, self._tool["name"].encode("utf-8"))
                drag.setMimeData(mime)
                drag.exec_(Qt.MoveAction)
        super().mouseMoveEvent(e)

    def dragEnterEvent(self, e):
        if e.source() is not self and e.mimeData().hasFormat(MIME):
            e.acceptProposedAction()

    def dropEvent(self, e):
        src = e.source()
        if isinstance(src, ToolCard) and src is not self:
            self._page.reorder(src.tool()["name"], self._tool["name"])


class ToolsPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window
        cats = parent_window.app_manager.categories
        self._category = cats[0] if cats else "全部应用"
        self._keyword = ""
        self._cards = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.title_label = QLabel(self._category)
        self.title_label.setObjectName("PageTitle")
        self.count_label = QLabel("")
        self.count_label.setObjectName("Sub")
        title_box.addWidget(self.title_label)
        title_box.addWidget(self.count_label)
        header.addLayout(title_box)
        header.addStretch()
        self.add_btn = QPushButton("添加应用")
        self.add_btn.setObjectName("Accent")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._add_tool)
        header.addWidget(self.add_btn)
        root.addLayout(header)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._grid_host = QWidget()
        self._flow = FlowLayout(self._grid_host, spacing=GAP, fill_min=CARD_MIN_W)
        self._scroll.setWidget(self._grid_host)
        root.addWidget(self._scroll, 1)

        # 运行状态监测（后台 5 秒一轮）
        self._running = set()
        self._watcher = RunningWatcher(self)
        self._watcher.refreshed.connect(self._on_running)
        self._watcher.start()

        self.rebuild()

    # -- 供卡片调用的接口 -----------------------------------------------------
    def set_hint(self, text):
        self._win.set_hint(text)

    def show_icons(self):
        return bool(self._win.skin.get("show_tool_icons", True))

    def set_category(self, category):
        self._category = category
        self.rebuild()

    def set_filter(self, keyword):
        self._keyword = keyword
        self.rebuild()

    def reorder(self, src_name, dst_name):
        self._win.app_manager.swap_order(src_name, dst_name)
        self.rebuild()

    # -- 布局 ---------------------------------------------------------------
    def rebuild(self):
        self.title_label.setText(self._category if not self._keyword
                                 else "{} - 搜索:{}".format(self._category, self._keyword))
        tools = self._win.app_manager.by_category(self._category, self._keyword)
        self.count_label.setText("共 {} 个应用（双击启动 · 拖动调整顺序 · 右键编辑/删除）".format(len(tools)))
        while self._flow.count():
            item = self._flow.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards = [ToolCard(self, t) for t in tools]
        for card in self._cards:
            self._flow.addWidget(card)
            card.set_running(self._running)

    def _on_running(self, names):
        self._running = names
        for card in self._cards:
            card.set_running(names)

    # -- 操作 ---------------------------------------------------------------
    def launch(self, tool):
        try:
            self._win.app_manager.launch(tool)
            self._watcher.force_refresh()   # 启动后尽快点亮运行状态
        except FileNotFoundError:
            AppMessageBox.warning(self, "启动失败",
                                  "程序路径不存在：\n{}\n\n右键卡片可编辑路径。".format(
                                      self._win.app_manager.resolve(tool["path"])))
        except OSError as e:
            AppMessageBox.warning(self, "启动失败", str(e))

    def show_card_menu(self, tool, global_pos):
        menu = SquareMenu(self)
        act_launch = menu.addAction(icons.icon("play"), "启动")
        act_fav = menu.addAction(icons.icon("star"),
                                 "取消收藏" if tool.get("favorite") else "收藏")
        act_reveal = menu.addAction(icons.icon("folder"), "打开所在目录")
        exe = os.path.basename(self._win.app_manager.resolve(tool.get("path", "")))
        running = bool(exe) and exe.lower() in self._running
        act_kill = menu.addAction(icons.icon("close"), "结束进程") if running else None
        menu.addSeparator()
        act_edit = menu.addAction(icons.icon("edit"), "编辑")
        act_del = menu.addAction(icons.icon("trash"), "删除")
        act = menu.exec_(global_pos)
        am = self._win.app_manager
        if act == act_launch:
            self.launch(tool)
        elif act == act_fav:
            am.toggle_favorite(tool["name"])
            self.rebuild()
        elif act == act_reveal:
            try:
                am.reveal(tool)
            except (FileNotFoundError, OSError) as e:
                AppMessageBox.warning(self, "操作失败", str(e))
        elif act == act_kill:
            if AppMessageBox.question(self, "结束进程",
                                      "确定结束「{}」（{}）吗？未保存的数据将丢失。".format(tool["name"], exe)):
                subprocess.run(["taskkill", "/f", "/im", exe],
                               creationflags=0x08000000, capture_output=True)
                self._watcher.force_refresh()
        elif act == act_edit:
            self._edit_tool(tool)
        elif act == act_del:
            self._delete_tool(tool)

    def _delete_tool(self, tool):
        if AppMessageBox.question(self, "删除应用", "确定删除「{}」吗？".format(tool["name"])):
            self._win.app_manager.remove(tool["name"])
            self._win.reload_all_pages()

    def _edit_tool(self, tool):
        am = self._win.app_manager

        def on_delete():
            if AppMessageBox.question(self, "删除应用", "确定删除「{}」吗？".format(tool["name"])):
                am.remove(tool["name"])
                self._win.reload_all_pages()
                return True
            return False

        data = ToolDialog.get_data(self, am.categories, tool, on_delete)
        if data:
            am.update(tool["name"], data)
            self._win.reload_all_pages()

    def _add_tool(self):
        am = self._win.app_manager
        data = ToolDialog.get_data(self, am.categories)
        if data:
            am.add(data["name"], data["category"], data["description"], data["path"])
            self._win.reload_all_pages()

    def refresh_theme(self):
        # 图标为系统提取的彩色位图无需换色，仅兜底内置图标随主题着色
        for card in self._cards:
            card._refresh_icon()
