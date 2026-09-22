# -*- coding: utf-8 -*-
"""配置检测页：检测电脑硬件与系统配置（系统/处理器/内存/显卡/主板/硬盘/网络），
附带应用与导航配置文件扫描"""
import json
import subprocess

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

_PS = (
    "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
    "$ErrorActionPreference = 'SilentlyContinue'; "
    "$info = [ordered]@{"
    "os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption, Version, OSArchitecture; "
    "cpu = Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, "
    "NumberOfLogicalProcessors, MaxClockSpeed; "
    "sys = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer, Model, TotalPhysicalMemory; "
    "gpu = Get-CimInstance Win32_VideoController | Select-Object Name, DriverVersion; "
    "board = Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer, Product; "
    "bios = Get-CimInstance Win32_BIOS | Select-Object Manufacturer, SMBIOSBIOSVersion; "
    "mem = Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, Capacity, ConfiguredClockSpeed, Speed; "
    "disk = Get-CimInstance Win32_LogicalDisk -Filter 'DriveType=3' | "
    "Select-Object DeviceID, VolumeName, Size, FreeSpace; "
    "net = Get-CimInstance Win32_NetworkAdapterConfiguration -Filter 'IPEnabled=true' | "
    "Select-Object Description, MACAddress, IPAddress"
    "}; $info | ConvertTo-Json -Depth 3"
)


def _gb(nbytes):
    try:
        return "{:.1f} GB".format(int(nbytes) / 1024 ** 3)
    except (TypeError, ValueError):
        return "未知"


class DetectThread(QThread):
    """后台采集硬件信息，避免阻塞界面"""
    got = Signal(dict)
    failed = Signal(str)

    def run(self):
        try:
            out = subprocess.run(["powershell", "-NoProfile", "-Command", _PS],
                                 capture_output=True, timeout=45,
                                 creationflags=0x08000000)  # CREATE_NO_WINDOW，不弹控制台窗
            self.got.emit(json.loads(out.stdout.decode("utf-8", "replace")))
        except Exception as e:
            self.failed.emit(str(e))


class CheckPage(QWidget):
    def __init__(self, parent_window):
        super().__init__()
        self._win = parent_window
        self._thread = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 16)
        root.setSpacing(12)

        header = QHBoxLayout()
        box = QVBoxLayout()
        box.setSpacing(2)
        title = QLabel("配置检测")
        title.setObjectName("PageTitle")
        self.sub = QLabel("检测本机硬件与系统配置；附带应用/导航配置文件扫描")
        self.sub.setObjectName("Sub")
        box.addWidget(title)
        box.addWidget(self.sub)
        header.addLayout(box)
        header.addStretch()
        self.check_btn = QPushButton("开始检测")
        self.check_btn.setObjectName("Accent")
        self.check_btn.setCursor(Qt.PointingHandCursor)
        self.check_btn.clicked.connect(self._start_detect)
        header.addWidget(self.check_btn)
        root.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self._col = QVBoxLayout(host)
        self._col.setContentsMargins(0, 0, 12, 0)
        self._col.setSpacing(12)
        scroll.setWidget(host)
        root.addWidget(scroll, 1)

        # 硬件信息区（检测后填充）
        self._info_frame, self._info_col = self._make_section("硬件信息")
        self._info_label = QLabel("尚未检测。点击右上角「开始检测」采集本机硬件配置。")
        self._info_label.setWordWrap(True)
        self._info_col.addWidget(self._info_label)

        # 配置文件扫描区（原功能保留）
        self._cfg_frame, self._cfg_col = self._make_section("应用配置扫描")
        row = QHBoxLayout()
        self.result_label = QLabel("扫描 tools.json 应用路径与 nav.json 导航配置。")
        self.result_label.setWordWrap(True)
        row.addWidget(self.result_label, 1)
        cfg_btn = QPushButton("扫描配置")
        cfg_btn.setObjectName("Ghost")
        cfg_btn.setCursor(Qt.PointingHandCursor)
        cfg_btn.clicked.connect(self._run_check)
        row.addWidget(cfg_btn)
        self._cfg_col.addLayout(row)

    def _make_section(self, title):
        frame = QFrame()
        frame.setObjectName("Section")
        v = QVBoxLayout(frame)
        v.setContentsMargins(16, 14, 16, 14)
        v.setSpacing(6)
        label = QLabel(title)
        label.setObjectName("GroupTitle")
        v.addWidget(label)
        self._col.addWidget(frame)
        return frame, v

    # -- 硬件检测 ----------------------------------------------------------
    def _start_detect(self):
        if self._thread and self._thread.isRunning():
            return
        self._info_label.setText("正在采集硬件信息，请稍候（约 2~5 秒）...")
        self.check_btn.setEnabled(False)
        self._thread = DetectThread()
        self._thread.got.connect(self._fill)
        self._thread.failed.connect(self._on_fail)
        self._thread.finished.connect(lambda: self.check_btn.setEnabled(True))
        self._thread.start()

    def _clear_info(self):
        while self._info_col.count():
            item = self._info_col.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            elif item.layout():
                item.layout().deleteLater()

    def _row(self, key, value):
        h = QHBoxLayout()
        h.setSpacing(12)
        k = QLabel(key)
        k.setObjectName("Sub")
        k.setFixedWidth(96)
        k.setAlignment(Qt.AlignTop)
        val = QLabel(str(value))
        val.setWordWrap(True)
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)
        h.addWidget(k)
        h.addWidget(val, 1)
        self._info_col.addLayout(h)

    def _fill(self, d):
        self._clear_info()
        os_ = d.get("os") or {}
        self._row("操作系统", "{}（版本 {}，{}）".format(
            os_.get("Caption", "未知"), os_.get("Version", "?"),
            os_.get("OSArchitecture", "?")))
        cpu = d.get("cpu") or {}
        self._row("处理器", "{}（{} 核 {} 线程，基准频率 {:.2f} GHz）".format(
            cpu.get("Name", "未知").strip(), cpu.get("NumberOfCores", "?"),
            cpu.get("NumberOfLogicalProcessors", "?"),
            (cpu.get("MaxClockSpeed") or 0) / 1000.0))
        sys_ = d.get("sys") or {}
        self._row("机型", "{} {}".format(sys_.get("Manufacturer", ""), sys_.get("Model", "")))
        self._row("内存容量", _gb(sys_.get("TotalPhysicalMemory")))
        sticks = d.get("mem") or []
        if isinstance(sticks, dict):
            sticks = [sticks]
        for i, m in enumerate(sticks, 1):
            self._row("内存条 {}".format(i), "{}  {}MHz".format(
                m.get("Manufacturer") or "未知", m.get("ConfiguredClockSpeed") or m.get("Speed") or "?"))
        gpu = d.get("gpu") or []
        if isinstance(gpu, dict):
            gpu = [gpu]
        for g in gpu:
            self._row("显卡", "{}（驱动 {}）".format(g.get("Name", "未知"),
                                                g.get("DriverVersion", "?")))
        board = d.get("board") or {}
        self._row("主板", "{} {}".format(board.get("Manufacturer", ""),
                                       board.get("Product", "")))
        bios = d.get("bios") or {}
        self._row("BIOS", "{} {}".format(bios.get("Manufacturer", ""),
                                       bios.get("SMBIOSBIOSVersion", "")))
        disks = d.get("disk") or []
        if isinstance(disks, dict):
            disks = [disks]
        for dk in disks:
            size, free = int(dk.get("Size") or 0), int(dk.get("FreeSpace") or 0)
            used_pct = 100 - free * 100 // size if size else 0
            self._row("分区 {}".format(dk.get("DeviceID", "?")), "共 {}，可用 {}（已用 {}%）".format(
                _gb(size), _gb(free), used_pct))
        nets = d.get("net") or []
        if isinstance(nets, dict):
            nets = [nets]
        for n in nets:
            ips = n.get("IPAddress") or []
            ip = ips[0] if isinstance(ips, list) and ips else "?"
            self._row("网卡", "{}（IP {}）".format(n.get("Description", "未知"), ip))

    def _on_fail(self, msg):
        self._info_label.setText("检测失败：{}".format(msg))

    # -- 配置文件扫描（附带功能） ---------------------------------------------
    def reset(self):
        self.result_label.setText("配置已变更，建议重新扫描。")

    def _run_check(self):
        am = self._win.app_manager
        missing = [t["name"] for t in am.tools if not am.exists(t)]
        names = [t["name"] for t in am.tools]
        dups = sorted({n for n in names if names.count(n) > 1})
        nm = self._win.nav_manager
        bad_nav = [i["name"] for i in nm.items if not str(i.get("url", "")).strip()]

        lines = ["应用配置 tools.json：共 {} 个，路径失效 {} 个{}".format(
            len(am.tools), len(missing), self._fmt(missing)),
            "导航配置 nav.json：共 {} 项，网址缺失 {} 个{}".format(
                len(nm.items), len(bad_nav), self._fmt(bad_nav))]
        if dups:
            lines.append("警告：重名应用 {} 个{}".format(len(dups), self._fmt(dups)))
        lines.append("扫描结果：" + ("全部正常。" if not (missing or dups or bad_nav)
                     else "失效应用请在工具页右键卡片 → 编辑修正。"))
        self.result_label.setText("\n".join(lines))

    @staticmethod
    def _fmt(items):
        return "（{}）".format("、".join(items[:8]) + ("..." if len(items) > 8 else "")) if items else ""
