# -*- coding: utf-8 -*-
"""网站导航管理：JSON 持久化，支持用户自定义增删改；链接已于 2026-09 逐一校验"""
from app.core import config

DEFAULT_GROUPS = ["社交媒体", "官方下载", "搜索引擎", "知识社区", "美化资源", "科技资讯",
                  "常用网站", "常用软件", "游戏工具"]

# 游戏工具分组（自旧「游戏工具」应用分类迁移）
GAME_NAV = [
    {"name": "Steam 官方下载", "url": "https://store.steampowered.com/about/", "description": "Steam 平台下载", "group": "游戏工具"},
    {"name": "Epic 官方下载", "url": "https://store.epicgames.com/zh-CN/", "description": "Epic 平台下载", "group": "游戏工具"},
    {"name": "EA App 官方下载", "url": "https://www.ea.com/ea-app", "description": "EA App 平台下载", "group": "游戏工具"},
    {"name": "战网游戏平台", "url": "https://download.battle.net/", "description": "暴雪战网下载", "group": "游戏工具"},
    {"name": "微星小飞机", "url": "https://www.msi.com/Landing/afterburner", "description": "MSI Afterburner 显卡监控/超频（下载页）", "group": "游戏工具"},
    {"name": "风灵月影", "url": "https://flingtrainer.com/", "description": "FlingTrainer 修改器官网", "group": "游戏工具"},
    {"name": "迅游加速器", "url": "https://www.xunyou.com/", "description": "迅游加速器官网", "group": "游戏工具"},
    {"name": "雷神加速器", "url": "https://www.leigod.com/", "description": "雷神加速器官网", "group": "游戏工具"},
    {"name": "UU加速器", "url": "https://uu.163.com/", "description": "网易 UU 加速器官网", "group": "游戏工具"},
    {"name": "YZ加速器", "url": "https://www.yuanzijiasu.com/", "description": "YZ 加速器官网", "group": "游戏工具"},
    {"name": "外星仔加速器", "url": "https://www.et001.com/", "description": "外星仔加速器官网", "group": "游戏工具"},
]

DEFAULT_NAV = [
    {"name": "微信网页版", "url": "https://wx.qq.com/", "description": "微信网页版（注意：部分账号已不支持网页版登录）", "group": "社交媒体"},
    {"name": "QQ网页版", "url": "https://im.qq.com/", "description": "QQ官网", "group": "社交媒体"},
    {"name": "哔哩哔哩", "url": "https://www.bilibili.com/", "description": "国内知名的视频弹幕网站", "group": "社交媒体"},
    {"name": "小红书", "url": "https://www.xiaohongshu.com/", "description": "生活方式分享平台", "group": "社交媒体"},
    {"name": "快手", "url": "https://www.kuaishou.com/", "description": "短视频分享平台", "group": "社交媒体"},
    {"name": "抖音", "url": "https://www.douyin.com/", "description": "短视频分享平台", "group": "社交媒体"},

    {"name": "微信PC版下载", "url": "https://pc.weixin.qq.com/", "description": "微信官方下载", "group": "官方下载"},
    {"name": "QQ下载", "url": "https://im.qq.com/pcqq/", "description": "QQ官方下载", "group": "官方下载"},
    {"name": "火绒安全", "url": "https://www.huorong.cn/", "description": "火绒安全软件官方下载", "group": "官方下载"},
    {"name": "FirPE", "url": "https://www.firpe.cn/", "description": "第三方 WinPE 工具", "group": "官方下载"},
    {"name": "Everything", "url": "https://www.voidtools.com/zh-cn/", "description": "文件搜索工具官方下载", "group": "官方下载"},
    {"name": "Motrix", "url": "https://motrix.app/zh-CN/", "description": "全能下载工具官方下载", "group": "官方下载"},
    {"name": "qBittorrent", "url": "https://www.qbittorrent.org/", "description": "BT 下载工具官方下载", "group": "官方下载"},

    {"name": "百度", "url": "https://www.baidu.com/", "description": "国内最大的搜索引擎", "group": "搜索引擎"},
    {"name": "谷歌", "url": "https://www.google.com/", "description": "全球搜索引擎（需科学上网）", "group": "搜索引擎"},

    {"name": "GitHub", "url": "https://github.com/", "description": "全球最大的代码托管平台", "group": "知识社区"},
    {"name": "知乎", "url": "https://www.zhihu.com/", "description": "知识问答社区", "group": "知识社区"},

    {"name": "致美化", "url": "https://zhutix.com/", "description": "桌面美化资源平台", "group": "美化资源"},
    {"name": "枫の主题社", "url": "https://winmoes.com/", "description": "二次元技术研究社区，电脑美化资源", "group": "美化资源"},

    {"name": "IT之家", "url": "https://www.ithome.com/", "description": "科技资讯网站", "group": "科技资讯"},
    {"name": "电手", "url": "https://www.dians.net/", "description": "科技、数码和互联网资讯网站（原 4hou.com 链接有误，已修复）", "group": "科技资讯"},

    {"name": "淘宝", "url": "https://www.taobao.com/", "description": "电子商务平台", "group": "常用网站"},
    {"name": "京东", "url": "https://www.jd.com/", "description": "电子商务平台", "group": "常用网站"},
    {"name": "网易", "url": "https://www.163.com/", "description": "互联网公司门户", "group": "常用网站"},
    {"name": "新浪", "url": "https://www.sina.com.cn/", "description": "互联网公司门户", "group": "常用网站"},
    {"name": "网易云音乐", "url": "https://music.163.com/", "description": "在线音乐平台", "group": "常用网站"},
    {"name": "豆瓣", "url": "https://www.douban.com/", "description": "文化社区和评论网站", "group": "常用网站"},
    {"name": "吾爱破解", "url": "https://www.52pojie.cn/", "description": "软件技术交流论坛", "group": "常用网站"},

    # 常用软件下载（自旧版「推荐应用」完整移植）
    {"name": "格式工厂", "url": "https://www.pcgeshi.com/", "description": "多媒体格式转换工具", "group": "常用软件"},
    {"name": "PDFGear", "url": "https://www.pdfgear.com/", "description": "免费 PDF 编辑工具", "group": "常用软件"},
    {"name": "PyCharm", "url": "https://www.jetbrains.com/pycharm/download/", "description": "Python IDE", "group": "常用软件"},
    {"name": "VSCode", "url": "https://code.visualstudio.com/Download", "description": "代码编辑器", "group": "常用软件"},
    {"name": "Obsidian", "url": "https://obsidian.md/download", "description": "知识管理，笔记软件", "group": "常用软件"},
    {"name": "LocalSend", "url": "https://localsend.org/download/", "description": "跨设备文件传输工具", "group": "常用软件"},
    {"name": "LXMusic", "url": "https://lxmusic.toside.cn/", "description": "音乐播放器", "group": "常用软件"},
    {"name": "Ani", "url": "https://myani.org/", "description": "追番/动画播放软件", "group": "常用软件"},
    {"name": "Kazumi", "url": "https://kazumi.cn/", "description": "动漫软件", "group": "常用软件"},
    {"name": "PotPlayer", "url": "https://potplayer.info/download/", "description": "视频播放器", "group": "常用软件"},
    {"name": "TranslucentTB", "url": "https://translucenttb.net/", "description": "任务栏美化工具", "group": "常用软件"},
    {"name": "Steam", "url": "https://store.steampowered.com/download/", "description": "游戏平台", "group": "常用软件"},
    {"name": "Epic", "url": "https://www.epicgames.com/store/en-US/download", "description": "游戏平台", "group": "常用软件"},
    {"name": "Steam++", "url": "https://steampp.net/download", "description": "Steam 辅助工具（Watt Toolkit）", "group": "常用软件"},
    {"name": "V2RayN", "url": "https://github.com/2dust/v2rayN/releases", "description": "网络工具", "group": "常用软件"},
    {"name": "Blender", "url": "https://www.blender.org/download/", "description": "3D 建模和动画软件", "group": "常用软件"},
    {"name": "OBS", "url": "https://obsproject.com/download", "description": "开源直播和录屏软件", "group": "常用软件"},
    {"name": "Chrome", "url": "https://www.google.com/chrome/downloads/", "description": "谷歌浏览器（需科学上网）", "group": "常用软件"},
    {"name": "彩虹工具箱", "url": "https://rainbowbyte.com/", "description": "多功能工具集合", "group": "常用软件"},
    {"name": "贴汁", "url": "https://tiez.name666.top/zh/", "description": "第三方剪贴板工具（原链接笔误已修复）", "group": "常用软件"},
    {"name": "小智桌面", "url": "https://xzdesktop.cqttech.com/", "description": "桌面整理工具", "group": "常用软件"},
    {"name": "MTools", "url": "https://github.com/HG-ha/MTools", "description": "媒体多功能工具集合", "group": "常用软件"},
    {"name": "Waifu2x", "url": "https://gitee.com/aaronfeng0711/Waifu2x-Extension-GUI", "description": "图像放大和降噪工具", "group": "常用软件"},
    {"name": "Uotan Toolbox", "url": "https://toolbox.uotan.cn/", "description": "刷机工具箱", "group": "常用软件"},
    {"name": "网易有道翻译", "url": "https://fanyi.youdao.com/", "description": "在线翻译工具", "group": "常用软件"},
]

DEFAULT_NAV.extend(GAME_NAV)  # 并入游戏工具分组，缺失项启动时自动补进配置


class NavManager:
    def __init__(self):
        data = config.load_json("nav.json", {"items": DEFAULT_NAV})
        self.items = data.get("items", list(DEFAULT_NAV))
        # 默认清单更新后一次性合并进已有配置（按 名称+分组 去重，不动用户删除项）
        existing = {(it.get("name"), it.get("group")) for it in self.items}
        missing = [d for d in DEFAULT_NAV if (d["name"], d.get("group")) not in existing]
        if missing:
            self.items.extend(missing)
            self.save()

    def save(self):
        config.save_json("nav.json", {"items": self.items})

    def reload(self):
        """重新读取配置文件（配置导入后调用）"""
        data = config.load_json("nav.json", {"items": DEFAULT_NAV})
        self.items = data.get("items", list(DEFAULT_NAV))
        existing = {(it.get("name"), it.get("group")) for it in self.items}
        missing = [d for d in DEFAULT_NAV if (d["name"], d.get("group")) not in existing]
        if missing:
            self.items.extend(missing)
            self.save()

    def groups(self):
        """内置分组顺序在前，用户自建分组按出现顺序追加"""
        out = list(DEFAULT_GROUPS)
        for it in self.items:
            g = it.get("group", "")
            if g and g not in out:
                out.append(g)
        return out

    def by_group(self, group, keyword=""):
        kw = keyword.strip().lower()
        return [it for it in self.items
                if it.get("group") == group
                and (not kw or kw in it["name"].lower() or kw in it.get("description", "").lower())]

    def add(self, name, url, description, group):
        self.items.append({"name": name, "url": url, "description": description, "group": group})
        self.save()

    def update(self, old_name, data):
        for it in self.items:
            if it["name"] == old_name:
                it.update(data)
                self.save()
                return
        raise KeyError(old_name)

    def remove(self, name):
        self.items = [it for it in self.items if it["name"] != name]
        self.save()
