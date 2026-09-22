# -*- coding: utf-8 -*-
"""应用（工具）管理：JSON 持久化 + 插件式增删改，路径支持相对路径"""
import os
import subprocess

from app.core import config

DEFAULT_CATEGORIES = ["系统工具", "磁盘工具", "硬件检测", "系统优化",
                      "网络工具", "其他工具"]

FAV_VIEW = "我的收藏"  # 伪分类：侧边栏收藏视图

# 默认工具指向旧项目 src/tools（相对路径）；路径缺失时可在应用内编辑修正
def _t(*p):
    return os.path.join("..", "SCTools", "src", "tools", *p)

DEFAULT_TOOLS = [
    {"name": "PCMaster", "category": "系统工具", "description": "系统维护和优化工具集", "path": _t("system_tools", "PCMaster_6.25_Portable", "pcmaster.exe"), "order": 0},
    {"name": "Win11轻松设置", "category": "系统工具", "description": "Windows 11设置工具", "path": _t("system_tools", "Windows11轻松设置_1.09_Portable", "Windows11轻松设置.exe"), "order": 1},
    {"name": "WinNTSetup", "category": "系统工具", "description": "Windows安装工具", "path": _t("system_tools", "WinNTSetup_5.4.1.0_64bit_Portable", "WinNTSetup_x64.exe"), "order": 2},
    {"name": "EasyRC", "category": "系统工具", "description": "系统安装工具", "path": _t("system_tools", "EasyRC", "EasyRCV3.exe"), "order": 3},
    {"name": "HEU KMS激活", "category": "系统工具", "description": "系统激活工具", "path": _t("system_tools", "HEU_KMS_Activator_HorseEdition.exe"), "order": 4},
    {"name": "ResHacker", "category": "其他工具", "description": "资源工具", "path": _t("system_tools", "ResHacker", "ResHacker4.exe"), "order": 5},

    {"name": "CrystalDiskInfo", "category": "磁盘工具", "description": "硬盘信息检测工具", "path": _t("disk_tools", "CrystalDiskInfo", "CrystalDiskInfoPortable.exe"), "order": 6},
    {"name": "CrystalDiskMark", "category": "磁盘工具", "description": "硬盘性能测试工具", "path": _t("disk_tools", "CrystalDiskMark", "CrystalDiskMarkPortable.exe"), "order": 7},
    {"name": "DiskGenius", "category": "磁盘工具", "description": "磁盘分区和数据恢复工具", "path": _t("disk_tools", "DiskGenius Pro", "DiskGenius.exe"), "order": 8},
    {"name": "WizTree", "category": "磁盘工具", "description": "磁盘空间分析工具", "path": _t("disk_tools", "WizTree_4.23_Portable", "WizTree64.exe"), "order": 9},
    {"name": "分区助手", "category": "磁盘工具", "description": "分区助手工具", "path": _t("disk_tools", "PartAssist.exe"), "order": 10},
    {"name": "Recuva", "category": "磁盘工具", "description": "文件恢复工具", "path": _t("disk_tools", "Recuva64.exe"), "order": 11},

    {"name": "图拉丁硬件检测", "category": "硬件检测", "description": "硬件信息检测工具", "path": _t("hardware_detection", "图拉丁硬件检测", "图拉丁硬件检测.exe"), "order": 12},
    {"name": "AIDA64", "category": "硬件检测", "description": "系统信息和硬件检测工具", "path": _t("hardware_detection", "AIDA64.exe"), "order": 13},
    {"name": "GPU-Z", "category": "硬件检测", "description": "GPU信息检测工具", "path": _t("hardware_detection", "GPU-Z.exe"), "order": 14},
    {"name": "ChipGenius", "category": "硬件检测", "description": "USB设备信息检测工具", "path": _t("hardware_detection", "ChipGenius.exe"), "order": 15},
    {"name": "Monitorinfo", "category": "硬件检测", "description": "显示器信息检测工具", "path": _t("hardware_detection", "monitorinfo.exe"), "order": 16},
    {"name": "鼠标测试", "category": "硬件检测", "description": "鼠标测试工具", "path": _t("hardware_detection", "鼠标测试软件AresonMouseTestProgram.exe"), "order": 17},
    {"name": "MOUSERATE", "category": "硬件检测", "description": "鼠标回报率测试工具", "path": _t("hardware_detection", "MOUSERATE.EXE"), "order": 18},
    {"name": "键盘测试", "category": "硬件检测", "description": "键盘测试工具", "path": _t("hardware_detection", "Keyboard Test Utility.exe"), "order": 19},
    {"name": "BIOSBackup", "category": "硬件检测", "description": "BIOS备份工具", "path": _t("hardware_detection", "BIOSBackup.exe"), "order": 20},

    {"name": "CCleaner", "category": "系统优化", "description": "系统清理和优化工具", "path": _t("system_optimization", "CCleaner pro 6.15.10623 绿色版", "CCleaner64.exe"), "order": 21},
    {"name": "HiBit卸载器", "category": "系统优化", "description": "软件卸载工具", "path": _t("system_optimization", "HiBit_Uninstaller_3.2.55_Single.exe"), "order": 22},
    {"name": "Dism++", "category": "系统优化", "description": "Windows系统维护工具", "path": _t("system_optimization", "Dism++_10.1.1002.1_Portable", "Dism++x64.exe"), "order": 23},
    {"name": "ContextMenuManager", "category": "系统优化", "description": "右键菜单管理工具", "path": _t("system_optimization", "ContextMenuManager.exe"), "order": 24},
    {"name": "CrystalMark Retro", "category": "系统优化", "description": "系统性能测试工具", "path": _t("system_optimization", "CrystalMark Retro", "CrystalMarkRetroPortable.exe"), "order": 25},

    {"name": "NDM", "category": "其他工具", "description": "多线程下载器", "path": _t("other_tools", "Neat Download Manager", "NeatDM.exe"), "order": 26},
    {"name": "QBittorrent", "category": "其他工具", "description": "种子下载器", "path": _t("other_tools", "qBittorrent", "qbittorrent.exe"), "order": 27},
    {"name": "Windows超级管理器", "category": "其他工具", "description": "Windows系统设置和监管工具", "path": _t("other_tools", "Windowscjglq.exe"), "order": 28},
    {"name": "定时关机", "category": "其他工具", "description": "定时关机工具", "path": _t("other_tools", "定时关机.exe"), "order": 29},
    {"name": "定时闹钟", "category": "其他工具", "description": "定时闹钟工具", "path": _t("other_tools", "定时闹钟.exe"), "order": 30},
    {"name": "图片爬取", "category": "其他工具", "description": "图片爬取工具", "path": _t("other_tools", "图片爬取.exe"), "order": 31},
    {"name": "Everything", "category": "其他工具", "description": "文件快速搜索工具", "path": _t("other_tools", "Everything", "EverythingPortable.exe"), "order": 32},
]


class AppManager:
    def __init__(self):
        self.builtin_handler = None  # 由主窗口注入：处理 builtin:// 内置功能
        data = config.load_json("tools.json", {"categories": DEFAULT_CATEGORIES, "tools": DEFAULT_TOOLS})
        self.categories = data.get("categories", list(DEFAULT_CATEGORIES))
        self.tools = data.get("tools", list(DEFAULT_TOOLS))
        # 兼容旧配置：缺失 order 字段时按现有顺序补齐
        for i, t in enumerate(self.tools):
            t.setdefault("order", i)
        self._migrate_paths()

    def _migrate_paths(self):
        """旧版默认路径 ../SCTools/src/tools/* 迁移到本目录 tools/*；迁移后重写配置"""
        old_marks = (os.path.join("..", "SCTools", "src", "tools"),
                     os.path.join("..", "src", "tools"))
        changed = False
        norm_low = config.APP_DIR.lower()
        for t in self.tools:
            p = t.get("path", "")
            pl = p.lower()
            if p.startswith(old_marks):
                rel = p[len(old_marks[0]):].lstrip("\\/") if p.startswith(old_marks[0]) \
                    else p[len(old_marks[1]):].lstrip("\\/")
                t["path"] = os.path.join("tools", rel)
                changed = True
            elif "sctools\\src\\tools" in pl or "sctools/src/tools" in pl:
                # 绝对形式的旧路径
                idx = pl.find("src\\tools") if "src\\tools" in pl else pl.find("src/tools")
                t["path"] = os.path.join("tools", p[idx + 9:].lstrip("\\/"))
                changed = True
        # 任何解析后落在本目录外且目录不存在的 tools/ 相对路径不动，交由用户编辑
        if changed:
            self.save()

    def save(self):
        config.save_json("tools.json", {"categories": self.categories, "tools": self.tools})

    def reload(self):
        """重新读取配置文件（配置导入后调用）"""
        data = config.load_json("tools.json", {"categories": DEFAULT_CATEGORIES, "tools": DEFAULT_TOOLS})
        self.categories = data.get("categories", list(DEFAULT_CATEGORIES))
        self.tools = data.get("tools", list(DEFAULT_TOOLS))
        for i, t in enumerate(self.tools):
            t.setdefault("order", i)
        self._migrate_paths()

    def is_url(self, tool):
        return str(tool.get("path", "")).lower().startswith(("http://", "https://"))

    def is_builtin(self, tool):
        return str(tool.get("path", "")).startswith("builtin://")

    def resolve(self, path):
        if os.path.isabs(path):
            return os.path.normpath(path)
        return os.path.normpath(os.path.join(config.APP_DIR, path))

    def exists(self, tool):
        if self.is_url(tool) or self.is_builtin(tool):
            return True
        return os.path.exists(self.resolve(tool.get("path", "")))

    def launch(self, tool):
        p = tool.get("path", "")
        if self.is_builtin(tool):
            if self.builtin_handler:
                self.builtin_handler(p.split("://", 1)[1])
            return
        if self.is_url(tool):
            os.startfile(p)  # 网址类卡片：直接打开浏览器
            return
        full = self.resolve(p)
        if not os.path.exists(full):
            raise FileNotFoundError(full)
        os.startfile(full)

    def reveal(self, tool):
        if self.is_url(tool) or self.is_builtin(tool):
            raise OSError("网址/内置功能类应用没有所在目录")
        p = self.resolve(tool["path"])
        if not os.path.exists(p):
            raise FileNotFoundError(p)
        subprocess.Popen(["explorer", "/select,", p])

    def ensure_category(self, cat):
        if cat and cat not in self.categories:
            self.categories.append(cat)
            self.save()

    def add(self, name, category, description, path):
        order = max((t.get("order", 0) for t in self.tools), default=-1) + 1
        self.tools.append({"name": name, "category": category, "description": description,
                           "path": path, "order": order})
        self.ensure_category(category)
        self.save()

    def update(self, old_name, data):
        for t in self.tools:
            if t["name"] == old_name:
                t.update(data)
                self.ensure_category(t["category"])
                self.save()
                return
        raise KeyError(old_name)

    def remove(self, name):
        self.tools = [t for t in self.tools if t["name"] != name]
        self.save()

    def by_category(self, category, keyword=""):
        kw = keyword.strip().lower()
        if category == FAV_VIEW:
            source = [t for t in self.tools if t.get("favorite", False)]
        else:
            source = self.tools
        out = []
        for t in source:
            if category not in ("全部应用", FAV_VIEW) and t.get("category") != category:
                continue
            if kw and kw not in t["name"].lower() and kw not in t.get("description", "").lower():
                continue
            out.append(t)
        # 收藏置顶，其余按手动顺序
        out.sort(key=lambda t: (not t.get("favorite", False), t.get("order", 0)))
        return out

    def favorites(self):
        return [t for t in self.tools if t.get("favorite", False)]

    def toggle_favorite(self, name):
        t = next((t for t in self.tools if t["name"] == name), None)
        if t:
            t["favorite"] = not t.get("favorite", False)
            self.save()

    def swap_order(self, name_a, name_b):
        """拖拽排序：交换两个应用的次序"""
        a = next((t for t in self.tools if t["name"] == name_a), None)
        b = next((t for t in self.tools if t["name"] == name_b), None)
        if a and b:
            a["order"], b["order"] = b.get("order", 0), a.get("order", 0)
            self.save()
