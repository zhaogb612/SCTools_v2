# -*- coding: utf-8 -*-
"""网站导航页面：分类菜单栏切换 + 网址卡片（favicon）+ 悬浮提示 + 添加/编辑/删除（右键）"""
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QComboBox, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from app.core import favicon
from app.ui import icons
from app.ui.dialogs import AppDialog, AppMessageBox, SquareMenu
from app.ui.flow_layout import FlowLayout

CHIP_W, CHIP_H = 168, 34
FAV_SIZE = 16


class NavChip(QFrame):
    def __init__(self, page, item):
        super().__init__()
        self._page = page
        self._item = item
        self.setObjectName("Chip")
        self.setFixedHeight(CHIP_H)
        self.setMinimumWidth(140)  # 宽度由填满式布局按行均分
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(8)
        self.fav_label = None  # favicon 标签，随图标显示设置动态创建/隐藏
        self.apply_icon_setting()
        self.name_label = QLabel(item["name"])
        self.name_label.setObjectName("CardName")
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.name_label, 1)

    def apply_icon_setting(self):
        """同步应用卡片图标设置：开启时创建/显示 favicon，关闭时隐藏"""
        on = self._page.show_icons()
        if on and self.fav_label is None:
            self.fav_label = QLabel()
            self.fav_label.setFixedSize(FAV_SIZE, FAV_SIZE)
            self.fav_label.setAlignment(Qt.AlignCenter)
            self.layout().insertWidget(0, self.fav_label)  # 图标固定在名称左侧
            self.set_favicon()
        if self.fav_label is not None:
            self.fav_label.setVisible(on)

    def set_favicon(self):
        """缓存命中显示 favicon，否则用默认 globe 图标（随主题着色）"""
        if self.fav_label is None:
            return
        ic = favicon.load_cached(self._item["url"])
        if ic is None:
            ic = icons.icon("globe", self._page._win.palette_data()["sub"])
        self.fav_label.setPixmap(ic.pixmap(FAV_SIZE, FAV_SIZE))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            QDesktopServices.openUrl(QUrl(self._item["url"]))
        elif e.button() == Qt.RightButton:
            self._page.show_chip_menu(self._item, self.mapToGlobal(e.position().toPoint()))
        super().mousePressEvent(e)

    def enterEvent(self, e):
        it = self._item
        desc = it.get("description") or it["url"]
        self._page.set_hint("{} — {}（{}）".format(it["name"], desc, it["url"]))
        super().enterEvent(e)

    def leaveEvent(self, e):
        self._page.set_hint("")
        super().leaveEvent(e)


class NavDialog(AppDialog):
    def __init__(self, parent, groups, item=None):
        super().__init__(parent, "编辑网址" if item else "添加网址")
        self.setFixedWidth(400)
        self.result_data = None
        c = self.content_layout()
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(10)

        self.ed_name = QLineEdit(item.get("name", "") if item else "")
        self.cb_group = QComboBox()
        self.cb_group.setEditable(True)
        self.cb_group.addItems(groups)
        if item:
            self.cb_group.setCurrentText(item.get("group", ""))
        self.ed_url = QLineEdit(item.get("url", "") if item else "")
        self.ed_url.setPlaceholderText("https://...")
        self.ed_desc = QLineEdit(item.get("description", "") if item else "")

        form.addRow("名称", self.ed_name)
        form.addRow("分组", self.cb_group)
        form.addRow("网址", self.ed_url)
        form.addRow("描述", self.ed_desc)
        c.addLayout(form)

        c.addSpacing(6)
        row = QHBoxLayout()
        row.addStretch()
        cancel = QPushButton("取消")
        cancel.setObjectName("Ghost")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setObjectName("Accent")
        ok.clicked.connect(self._accept)
        row.addWidget(cancel)
        row.addWidget(ok)
        c.addLayout(row)

    def _accept(self):
        name = self.ed_name.text().strip()
        url = self.ed_url.text().strip()
        if not name or not url:
            AppMessageBox.warning(self, "提示", "名称与网址不能为空")
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.result_data = {"name": name, "url": url,
                            "description": self.ed_desc.text().strip(),
                            "group": self.cb_group.currentText().strip() or "常用网站"}
        self.accept()

    @staticmethod
    def get_data(parent, groups, item=None):
        dlg = NavDialog(parent, groups, item)
        return dlg.result_data if dlg.exec_() == AppDialog.Accepted else None


class NavPage(QWidget):
    """网站导航：全部网址按分组平铺在一个滚动区内，顶部横向快捷跳转栏定位到对应分组"""

    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window
        self._group_hosts = {}      # 分组名 -> 分组容器（用于快速跳转）
        self._chips = []            # 当前所有卡片（顺序与布局一致）

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        title = QLabel("网站导航")
        title.setObjectName("PageTitle")
        self.count_label = QLabel("")
        self.count_label.setObjectName("Sub")
        title_box.addWidget(title)
        title_box.addWidget(self.count_label)
        header.addLayout(title_box)
        header.addStretch()
        add_btn = QPushButton("添加网址")
        add_btn.setObjectName("Accent")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)
        header.addWidget(add_btn)
        root.addLayout(header)

        # 分组快速跳转栏（点击滚动到对应分组）；分组少于 2 个时隐藏
        self._jump_bar = QWidget()
        self._jump_lay = QHBoxLayout(self._jump_bar)
        self._jump_lay.setContentsMargins(0, 0, 0, 0)
        self._jump_lay.setSpacing(8)
        self._jump_buttons = {}
        root.addWidget(self._jump_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._host = QWidget()
        self._host_lay = QVBoxLayout(self._host)
        self._host_lay.setContentsMargins(0, 0, 12, 0)
        self._host_lay.setSpacing(14)
        scroll.setWidget(self._host)
        self._scroll = scroll
        root.addWidget(scroll, 1)

        self.rebuild()

    def set_hint(self, text):
        self._win.set_hint(text)

    def show_icons(self):
        return bool(self._win.skin.get("show_tool_icons", True))

    def refresh_icons(self):
        """应用卡片图标设置变化时，同步导航卡片的 favicon 显隐"""
        self._walk_chips(lambda chip: chip.apply_icon_setting())

    def refresh_theme(self):
        # favicon 为彩色位图无需换色，仅默认 globe 图标随主题着色
        self._walk_chips(lambda chip: chip.set_favicon())

    def _walk_chips(self, fn):
        for chip in list(self._chips):
            fn(chip)

    def _clear_host(self):
        while self._host_lay.count():
            it = self._host_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._group_hosts = {}
        self._chips = []

    def _clear_jump(self):
        while self._jump_lay.count():
            it = self._jump_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        self._jump_buttons = {}

    def rebuild(self):
        nm = self._win.nav_manager
        groups = [g for g in nm.groups() if nm.by_group(g)]
        total = sum(len(nm.by_group(g)) for g in groups)
        self.count_label.setText("共 {} 个分类、{} 个网址（点击打开 · 右键网址卡片编辑/删除）".format(
            len(groups), total))
        self._clear_jump()
        for g in groups:
            b = QPushButton(g)
            b.setObjectName("NavTab")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, name=g: self._jump_to(name))
            self._jump_buttons[g] = b
            self._jump_lay.addWidget(b)
        self._jump_lay.addStretch()
        self._jump_bar.setVisible(len(groups) > 1)

        self._clear_host()
        if not groups:
            empty = QLabel("暂无网址，点击右上角「添加网址」开始添加")
            empty.setObjectName("Sub")
            empty.setAlignment(Qt.AlignCenter)
            self._host_lay.addWidget(empty)
            return

        all_items = []
        for g in groups:
            items = nm.by_group(g)
            all_items.extend(items)
            group_host = QWidget()
            gh_lay = QVBoxLayout(group_host)
            gh_lay.setContentsMargins(0, 0, 0, 0)
            gh_lay.setSpacing(8)
            gtitle = QLabel("{} · {} 个".format(g, len(items)))
            gtitle.setObjectName("GroupTitle")
            gh_lay.addWidget(gtitle)
            flow_host = QWidget()
            flow = FlowLayout(flow_host, spacing=8, fill_min=CHIP_W,
                              stretch_last=True)
            for item in items:
                chip = NavChip(self, item)
                flow.addWidget(chip)
                self._chips.append(chip)
            gh_lay.addWidget(flow_host)
            self._group_hosts[g] = group_host
            self._host_lay.addWidget(group_host)
        self._host_lay.addStretch()
        self._fetch_favicons(all_items)

    def _jump_to(self, name):
        """滚动到指定分组：点击跳转栏按钮后高亮该按钮并定位分组标题"""
        btns = self._jump_buttons
        for g, b in btns.items():
            b.setChecked(g == name)
        host = self._group_hosts.get(name)
        if host is None:
            return
        # 标题顶部与滚动区顶部对齐（留 4px 呼吸空间）
        top = host.mapTo(self._host, host.rect().topLeft()).y()
        self._scroll.verticalScrollBar().setValue(max(0, top - 4))

    def _fetch_favicons(self, items):
        """后台批量抓取当前分组缺缓存的 favicon，完成后刷新对应卡片"""
        worker = favicon.FaviconWorker([it["url"] for it in items], self)
        worker.one_done.connect(self._on_favicon)
        worker.finished.connect(lambda: self._fav_workers.discard(worker))
        if not hasattr(self, "_fav_workers"):
            self._fav_workers = set()
        self._fav_workers.add(worker)
        worker.start()

    def stop_workers(self):
        """退出前停掉全部抓取线程（主窗口 closeEvent 调用）"""
        if getattr(self, "_fav_workers", None):
            for w in list(self._fav_workers):
                w.stop()
            for w in list(self._fav_workers):
                w.wait(6000)
            self._fav_workers.clear()

    def _on_favicon(self, url):
        self._walk_chips(lambda chip: chip.set_favicon()
                         if chip._item["url"] == url else None)

    def show_chip_menu(self, item, global_pos):
        menu = SquareMenu(self)
        act_open = menu.addAction(icons.icon("external"), "打开")
        menu.addSeparator()
        act_edit = menu.addAction(icons.icon("edit"), "编辑")
        act_del = menu.addAction(icons.icon("trash"), "删除")
        act = menu.exec_(global_pos)
        nm = self._win.nav_manager
        if act == act_open:
            QDesktopServices.openUrl(QUrl(item["url"]))
        elif act == act_edit:
            data = NavDialog.get_data(self, nm.groups(), item)
            if data:
                nm.update(item["name"], data)
                self.rebuild()
        elif act == act_del:
            if AppMessageBox.question(self, "删除网址", "确定删除「{}」吗？".format(item["name"])):
                nm.remove(item["name"])
                self.rebuild()

    def _add(self):
        nm = self._win.nav_manager
        data = NavDialog.get_data(self, nm.groups())
        if data:
            nm.add(data["name"], data["url"], data["description"], data["group"])
            self.rebuild()
