# -*- coding: utf-8 -*-
"""Windows 全局热键：RegisterHotKey + 原生事件过滤器拦截 WM_HOTKEY"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication

WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT = 0x1, 0x2, 0x4
MOD_NOREPEAT = 0x4000

# 可选组合：(显示名, modifiers, 虚拟键码)
CHOICES = [
    ("Ctrl+Alt+S", MOD_CONTROL | MOD_ALT, 0x53),
    ("Ctrl+Alt+T", MOD_CONTROL | MOD_ALT, 0x54),
    ("Ctrl+Alt+Space", MOD_CONTROL | MOD_ALT, 0x20),
]


class HotkeyManager(QAbstractNativeEventFilter):
    def __init__(self, callback):
        super().__init__()
        self._cb = callback
        self._id = 0xB00B
        self._registered = False
        QApplication.instance().installNativeEventFilter(self)

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == self._id:
                self._cb()
                return True, 0
        return False, 0

    def register(self, mods, vk):
        self.unregister()
        self._registered = bool(ctypes.windll.user32.RegisterHotKey(
            None, self._id, mods | MOD_NOREPEAT, vk))
        return self._registered

    def unregister(self):
        if self._registered:
            ctypes.windll.user32.UnregisterHotKey(None, self._id)
            self._registered = False

    @property
    def active(self):
        return self._registered
