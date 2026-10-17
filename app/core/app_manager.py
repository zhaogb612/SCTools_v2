# -*- coding: utf-8 -*-
"""应用（工具）管理：JSON 持久化 + 插件式增删改，路径支持相对路径"""
import os
import subprocess

from app.core import config

DEFAULT_CATEGORIES = ["系统工具", "磁盘工具", "硬件检测", "系统优化", "其他工具", "网络工具"]

FAV_VIEW = "我的收藏"  # 伪分类：侧边栏收藏视图

# 默认工具清单：与随包 resources/config/tools.json 保持一致（含用户删除过的条目非此清单，恢复默认不会再冒出旧条目）
DEFAULT_TOOLS = [
    {"name": "Win11轻松设置", "category": "系统工具", "description": "Windows 11设置工具", "path": "tools\\system_tools\\Windows11轻松设置_1.09_Portable\\Windows11轻松设置.exe", "order": 34},
    {"name": "WinNTSetup", "category": "系统工具", "description": "Windows安装工具", "path": "tools\\system_tools\\WinNTSetup_5.4.1.0_64bit_Portable\\WinNTSetup_x64.exe", "order": 2},
    {"name": "EasyRC", "category": "系统工具", "description": "系统安装工具", "path": "tools\\system_tools\\EasyRC\\EasyRCV3.exe", "order": 3},
    {"name": "HEU KMS激活", "category": "系统工具", "description": "系统激活工具", "path": "tools\\system_tools\\HEU_KMS_Activator_HorseEdition.exe", "order": 4},
    {"name": "ResHacker", "category": "其他工具", "description": "资源工具", "path": "tools\\other_tools\\ResHacker\\ResHacker4.exe", "order": 1},
    {"name": "CrystalDiskInfo", "category": "磁盘工具", "description": "硬盘信息检测工具", "path": "tools\\disk_tools\\CrystalDiskInfo\\CrystalDiskInfoPortable.exe", "order": 6},
    {"name": "CrystalDiskMark", "category": "磁盘工具", "description": "硬盘性能测试工具", "path": "tools\\disk_tools\\CrystalDiskMark\\CrystalDiskMarkPortable.exe", "order": 7},
    {"name": "DiskGenius", "category": "磁盘工具", "description": "磁盘分区和数据恢复工具", "path": "tools\\disk_tools\\DiskGenius Pro\\DiskGenius.exe", "order": 8},
    {"name": "WizTree", "category": "磁盘工具", "description": "磁盘空间分析工具", "path": "tools\\disk_tools\\WizTree_4.23_Portable\\WizTree64.exe", "order": 9},
    {"name": "分区助手", "category": "磁盘工具", "description": "分区助手工具", "path": "tools\\disk_tools\\PartAssist.exe", "order": 10},
    {"name": "Recuva", "category": "磁盘工具", "description": "文件恢复工具", "path": "tools\\disk_tools\\Recuva64.exe", "order": 11},
    {"name": "AIDA64", "category": "硬件检测", "description": "系统信息和硬件检测工具", "path": "tools\\hardware_detection\\AIDA64.exe", "order": 13},
    {"name": "ChipGenius", "category": "硬件检测", "description": "USB设备信息检测工具", "path": "tools\\hardware_detection\\ChipGenius.exe", "order": 15},
    {"name": "Monitorinfo", "category": "硬件检测", "description": "显示器信息检测工具", "path": "tools\\hardware_detection\\monitorinfo.exe", "order": 16},
    {"name": "鼠标测试", "category": "硬件检测", "description": "鼠标测试工具", "path": "tools\\hardware_detection\\鼠标测试软件AresonMouseTestProgram.exe", "order": 17},
    {"name": "MOUSERATE", "category": "硬件检测", "description": "鼠标回报率测试工具", "path": "tools\\hardware_detection\\MOUSERATE.EXE", "order": 18},
    {"name": "键盘测试", "category": "硬件检测", "description": "键盘测试工具", "path": "tools\\hardware_detection\\Keyboard Test Utility.exe", "order": 19},
    {"name": "BIOSBackup", "category": "硬件检测", "description": "BIOS备份工具", "path": "tools\\hardware_detection\\BIOSBackup.exe", "order": 20},
    {"name": "HiBit卸载器", "category": "系统优化", "description": "软件卸载工具", "path": "tools\\system_optimization\\HiBit_Uninstaller_3.2.55_Single.exe", "order": 22},
    {"name": "Dism++", "category": "系统优化", "description": "Windows系统维护工具", "path": "tools\\system_optimization\\Dism++_10.1.1002.1_Portable\\Dism++x64.exe", "order": 23},
    {"name": "ContextMenuManager", "category": "系统优化", "description": "右键菜单管理工具", "path": "tools\\system_optimization\\ContextMenuManager.exe", "order": 24},
    {"name": "CrystalMark Retro", "category": "硬件检测", "description": "系统性能测试工具", "path": "tools\\hardware_detection\\CrystalMark Retro\\CrystalMarkRetroPortable.exe", "order": 25},
    {"name": "NDM", "category": "其他工具", "description": "多线程下载器", "path": "tools\\other_tools\\Neat Download Manager\\NeatDM.exe", "order": 26},
    {"name": "QBittorrent", "category": "其他工具", "description": "种子下载器", "path": "tools\\other_tools\\qBittorrent\\qbittorrent.exe", "order": 28},
    {"name": "Windows超级管理器", "category": "其他工具", "description": "Windows系统设置和监管工具", "path": "tools\\other_tools\\Windowscjglq.exe", "order": 29},
    {"name": "Everything", "category": "其他工具", "description": "文件快速搜索工具", "path": "tools\\other_tools\\Everything\\EverythingPortable.exe", "order": 33},
    {"name": "TCPing", "category": "网络工具", "description": "TCP 端口延迟测试（双击按提示输入目标）", "path": "tools\\network_tools\\tcping\\TCPing命令行.bat", "order": 35},
    {"name": "WinMTR", "category": "网络工具", "description": "路由跟踪与丢包分析工具", "path": "tools\\network_tools\\WinMTR\\WinMTR.exe", "order": 36},
    {"name": "Advanced IP Scanner", "category": "网络工具", "description": "局域网 IP 扫描工具", "path": "tools\\network_tools\\Advanced IP Scanner\\Advanced IP Scanner.exe", "order": 37},
    {"name": "CPU-Z", "category": "硬件检测", "description": "CPU / 主板 / 内存信息检测", "path": "tools\\hardware_detection\\CPU-Z.exe", "order": 38},
    {"name": "HWiNFO64", "category": "硬件检测", "description": "硬件信息与传感器监控", "path": "tools\\hardware_detection\\HWiNFO64.exe", "order": 39},
    {"name": "FurMark", "category": "硬件检测", "description": "显卡压力测试 / 烤机（内置 GPU-Z 2.54）", "path": "tools\\hardware_detection\\FurMark\\FurMark.exe", "order": 40},
    {"name": "FastCopy", "category": "其他工具", "description": "高速文件拷贝工具", "path": "tools\\other_tools\\FastCopy  5.12.0.exe", "order": 41},
    {"name": "软媒清理大师", "category": "系统优化", "description": "系统垃圾清理", "path": "tools\\system_tools\\魔方工具箱\\cleanmaster.exe", "order": 42},
    {"name": "软媒设置大师", "category": "系统优化", "description": "系统设置优化，提升工作与游戏效率", "path": "tools\\system_tools\\魔方工具箱\\winmaster.exe", "order": 43},
    {"name": "软媒磁盘大师", "category": "磁盘工具", "description": "磁盘（含 SSD）性能与健康度测试", "path": "tools\\system_tools\\魔方工具箱\\diskmaster.exe", "order": 44},
    {"name": "软媒蓝屏助手", "category": "系统工具", "description": "记录蓝屏并分析原因与解决方案", "path": "tools\\system_tools\\魔方工具箱\\bsodhelper.exe", "order": 45},
    {"name": "软媒文件大师", "category": "系统工具", "description": "文件校验/解锁/粉碎/分割/图片种子合成", "path": "tools\\system_tools\\魔方工具箱\\filemaster.exe", "order": 46},
    {"name": "软媒图标大师", "category": "系统工具", "description": "从 exe/dll 提取图标，png 与 ico 互转", "path": "tools\\system_tools\\魔方工具箱\\iconmaster.exe", "order": 47},
    {"name": "软媒美化大师", "category": "系统优化", "description": "系统外观美化定制", "path": "tools\\system_tools\\魔方工具箱\\visualmaster.exe", "order": 48},
    {"name": "DirectX Repair", "category": "其他工具", "description": "DirectX 修复工具（C++ 运行库一键修复）", "path": "tools\\other_tools\\DirectX_Repair\\DirectX Repair.exe", "order": 49},
    {"name": "Rufus", "category": "系统工具", "description": "U 盘启动盘制作工具", "path": "tools\\system_tools\\Rufus\\rufus.exe", "order": 50},
    {"name": "Ventoy2Disk", "category": "其他工具", "description": "U 盘多系统启动盘工具", "path": "tools\\other_tools\\Ventoy\\Ventoy2Disk.exe", "order": 51},
    {"name": "procexp(64位)", "category": "系统工具", "description": "Process Explorer 进程管理器（64 位）", "path": "tools\\system_tools\\ProcessExplorer\\procexp64.exe", "order": 52},
    {"name": "procexp(32位)", "category": "系统工具", "description": "Process Explorer 进程管理器（32 位）", "path": "tools\\system_tools\\ProcessExplorer\\procexp.exe", "order": 53},
    {"name": "FanControl", "category": "其他工具", "description": "风扇转速智能控制", "path": "tools\\other_tools\\FanControl\\FanControl.exe", "order": 54},
    {"name": "屏幕坏点漏光测试", "category": "硬件检测", "description": "内置全屏纯色检测（坏点/漏光，自动轮播）", "path": "builtin://screen_test", "order": 55},
    {"name": "定时关机", "category": "其他工具", "description": "定时关机工具", "path": "tools\\other_tools\\定时关机.exe", "order": 64},
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
