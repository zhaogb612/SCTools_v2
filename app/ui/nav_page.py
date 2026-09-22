# -*- coding: utf-8 -*-
"""网站导航页面：分类菜单栏切换 + 网址卡片（favicon）+ 悬浮提示 + 添加/编辑/删除（右键）"""
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QFormLayout, QFrame,
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
        self.setFixedSize(CHIP_W, CHIP_H)
        self.setCursor(Qt.PointingHandCursor)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 0, 10, 0)
        lay.setSpacing(8)
        self.fav_label = QLabel()
        self.fav_label.setFixedSize(FAV_SIZE, FAV_SIZE)
        self.fav_label.setAlignment(Qt.AlignCenter)
        self.set_favicon()
        lay.addWidget(self.fav_label)
        self.name_label = QLabel(item["name"])
        self.name_label.setObjectName("CardName")
        self.name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        lay.addWidget(self.name_label, 1)

    def set_favicon(self):
        """缓存命中显示 favicon，否则用默认 globe 图标（随主题着色）"""
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
    """顶部横向分类菜单栏，点击分类直接切换下方网址列表"""

    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window

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

        # 分类菜单栏（类似导航栏，点击直接切换）
        self._tab_bar = QWidget()
        self._tab_lay = QHBoxLayout(self._tab_bar)
        self._tab_lay.setContentsMargins(0, 0, 0, 0)
        self._tab_lay.setSpacing(8)
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_group.buttonClicked.connect(self._on_tab)
        root.addWidget(self._tab_bar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self._host = QWidget()
        self._host_lay = QVBoxLayout(self._host)
        self._host_lay.setContentsMargins(0, 0, 12, 0)
        self._host_lay.setSpacing(10)
        scroll.setWidget(self._host)
        self._scroll = scroll
        root.addWidget(scroll, 1)

        self.rebuild()

    def set_hint(self, text):
        self._win.set_hint(text)

    def refresh_theme(self):
        # favicon 为彩色位图无需换色，仅默认 globe 图标随主题着色
        self._walk_chips(lambda chip: chip.set_favicon())

    def _walk_chips(self, fn):
        for i in range(self._host_lay.count()):
            host = self._host_lay.itemAt(i).widget()
            if host is None:
                continue
            lay = host.layout()
            for j in range(lay.count()):
                w = lay.itemAt(j).widget()
                if isinstance(w, NavChip):
                    fn(w)

    def rebuild(self):
        nm = self._win.nav_manager
        groups = [g for g in nm.groups() if nm.by_group(g)]
        total = sum(len(nm.by_group(g)) for g in groups)
        self.count_label.setText("共 {} 个分类、{} 个网址（点击打开 · 右键网址卡片编辑/删除）".format(
            len(groups), total))
        # 重建分类菜单栏
        while self._tab_lay.count():
            it = self._tab_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        for g in groups:
            b = QPushButton(g)
            b.setObjectName("NavTab")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            self._tab_group.addButton(b)
            self._tab_lay.addWidget(b)
        self._tab_lay.addStretch()
        if groups:
            self._tab_group.buttons()[0].setChecked(True)
            self._show_group(groups[0])
        else:
            self._show_group(None)

    def _on_tab(self, btn):
        self._show_group(btn.text())

    def _show_group(self, group):
        while self._host_lay.count():
            it = self._host_lay.takeAt(0)
            if it.widget():
                it.widget().deleteLater()
        if not group:
            return
        nm = self._win.nav_manager
        host = QWidget()
        flow = FlowLayout(host, spacing=8)
        items = nm.by_group(group)
        for item in items:
            flow.addWidget(NavChip(self, item))
        self._host_lay.addWidget(host)
        self._host_lay.addStretch()
        self._fetch_favicons(items)

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
