# -*- coding: utf-8 -*-
"""Windows 全局热键：RegisterHotKey + 原生事件过滤器拦截 WM_HOTKEY；
支持任意「修饰键+主键」组合，组合键以文本形式保存（如 Ctrl+Alt+S）"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import QAbstractNativeEventFilter
from PySide6.QtWidgets import QApplication

WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN = 0x1, 0x2, 0x4, 0x8
MOD_NOREPEAT = 0x4000

# 修饰键显示名 -> MOD 位
MOD_MAP = {"ctrl": MOD_CONTROL, "alt": MOD_ALT, "shift": MOD_SHIFT, "win": MOD_WIN}
MOD_NAMES = {MOD_CONTROL: "Ctrl", MOD_ALT: "Alt", MOD_SHIFT: "Shift", MOD_WIN: "Win"}

# 快捷预设
CHOICES = ["Ctrl+Alt+S", "Ctrl+Alt+T", "Ctrl+Alt+Space", "Ctrl+Alt+D", "Ctrl+Shift+S"]


def parse_hotkey(label):
    """'Ctrl+Alt+S' -> (mods, vk)；不合法或缺修饰键返回 None（避免劫持普通按键）"""
    parts = [p.strip() for p in (label or "").split("+") if p.strip()]
    if len(parts) < 2:
        return None
    mods = 0
    for p in parts[:-1]:
        m = MOD_MAP.get(p.lower())
        if m is None:
            return None
        mods |= m
    key = parts[-1]
    if len(key) == 1 and key.isalnum():
        vk = ord(key.upper())
    elif key.lower() == "space":
        vk = 0x20
    elif len(key) > 1 and key[0].upper() == "F" and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        vk = 0x70 + int(key[1:]) - 1
    else:
        return None
    return mods, vk


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
