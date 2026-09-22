# -*- coding: utf-8 -*-
"""流式布局：卡片/链接按行自动换行"""
from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtWidgets import QLayout, QSizePolicy, QWidgetItem


class FlowLayout(QLayout):
    def __init__(self, parent=None, spacing=10, fill_min=0):
        """fill_min>0 时启用填满模式：按可用宽度和最小卡宽算列数，每行卡片均分宽度不留空隙"""
        super().__init__(parent)
        self.setContentsMargins(0, 0, 0, 0)
        self._spacing = spacing
        self._fill_min = fill_min
        self._items = []

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, i):
        return self._items[i] if 0 <= i < len(self._items) else None

    def takeAt(self, i):
        return self._items.pop(i) if 0 <= i < len(self._items) else None

    def remove(self, widget):
        """按 widget 移除对应条目"""
        for i, item in enumerate(self._items):
            if item.widget() is widget:
                self._items.pop(i)
                return

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return QSize(m.left() + m.right() + size.width(), m.top() + m.bottom() + size.height())

    def _do_layout(self, rect, test_only):
        m = self.contentsMargins()
        x, y = rect.x() + m.left(), rect.y() + m.top()
        right = rect.right() - m.right()
        # 填满模式：列数 = 可用宽度能容纳的最少卡数，卡片均分行宽
        if self._fill_min > 0:
            avail = right - x + 1
            cols = max(1, int((avail + self._spacing) // (self._fill_min + self._spacing)))
            item_w = (avail - (cols - 1) * self._spacing) / cols
            row_h = 0
            for i, item in enumerate(self._items):
                col = i % cols
                h = item.sizeHint().height()
                if col == 0 and i > 0:
                    y += row_h + self._spacing
                    row_h = 0
                if not test_only:
                    item.setGeometry(QRect(QPoint(int(x + col * (item_w + self._spacing)), y),
                                           QSize(int(item_w), h)))
                row_h = max(row_h, h)
            return y + row_h - rect.y() + m.bottom()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self._spacing
            if next_x - self._spacing > right and line_height > 0:
                x = rect.x() + m.left()
                y = y + line_height + self._spacing
                next_x = x + hint.width() + self._spacing
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + m.bottom()


def widget_item(w):
    return QWidgetItem(w)
