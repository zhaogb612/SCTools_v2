# -*- coding: utf-8 -*-
"""应用管理对话框：添加/编辑工具（指定程序或目录），编辑模式含删除按钮"""
import os

from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton

from app.core import config
from app.ui.dialogs import AppDialog, AppMessageBox


def _ghost(text, slot):
    b = QPushButton(text)
    b.setObjectName("Ghost")
    b.clicked.connect(slot)
    return b


class ToolDialog(AppDialog):
    def __init__(self, parent, categories, tool=None, on_delete=None):
        super().__init__(parent, "编辑应用" if tool else "添加应用")
        self.setFixedWidth(440)
        self._tool = tool
        self._on_delete = on_delete
        self.result_data = None
        c = self.content_layout()

        def row(label, w):
            c.addWidget(QLabel(label))
            c.addWidget(w)
            return w

        self.ed_name = row("名称", QLineEdit(tool.get("name", "") if tool else ""))
        self.ed_cat = row("分类", QLineEdit(tool.get("category", "") if tool else ""))
        self.ed_cat.setPlaceholderText("输入或使用现有分类，如：系统工具")
        self.ed_path = row("路径", QLineEdit(tool.get("path", "") if tool else ""))
        self.ed_path.setPlaceholderText("程序或目录路径（支持相对路径）")
        self.ed_desc = row("描述", QLineEdit(tool.get("description", "") if tool else ""))

        btns = QHBoxLayout()
        btns.setSpacing(8)
        btns.addWidget(_ghost("选择程序", self._pick_file))
        btns.addWidget(_ghost("选择目录", self._pick_dir))
        btns.addWidget(_ghost("测试启动", self._test))
        btns.addStretch()
        if tool and on_delete:
            btns.addWidget(_ghost("删除此应用", self._delete))
        c.addLayout(btns)

        c.addSpacing(4)
        act = QHBoxLayout()
        act.addStretch()
        act.addWidget(_ghost("取消", self.reject))
        ok = QPushButton("保存")
        ok.setObjectName("Accent")
        ok.clicked.connect(self._accept)
        act.addWidget(ok)
        c.addLayout(act)

    def _pick_file(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择程序",
                                           os.path.dirname(self.ed_path.text()) or ".")
        if p:
            self.ed_path.setText(p)

    def _pick_dir(self):
        p = QFileDialog.getExistingDirectory(self, "选择目录",
                                             os.path.dirname(self.ed_path.text()) or ".")
        if p:
            self.ed_path.setText(p)

    def _test(self):
        path = self.ed_path.text().strip()
        full = path if os.path.isabs(path) else os.path.join(config.APP_DIR, path)
        if not path or not os.path.exists(full):
            AppMessageBox.warning(self, "测试启动", "路径不存在：\n{}".format(full))
            return
        try:
            os.startfile(full)
        except OSError as e:
            AppMessageBox.warning(self, "测试启动", "启动失败：{}".format(e))

    def _delete(self):
        if self._on_delete and self._on_delete():
            self.reject()

    def _accept(self):
        name = self.ed_name.text().strip()
        path = self.ed_path.text().strip()
        if not name or not path:
            AppMessageBox.warning(self, "提示", "名称与路径不能为空")
            return
        self.result_data = {
            "name": name,
            "category": self.ed_cat.text().strip() or "其他工具",
            "description": self.ed_desc.text().strip(),
            "path": path,
        }
        self.accept()

    @staticmethod
    def get_data(parent, categories, tool=None, on_delete=None):
        dlg = ToolDialog(parent, categories, tool, on_delete)
        return dlg.result_data if dlg.exec_() == AppDialog.Accepted else None
