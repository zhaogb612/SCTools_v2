# -*- coding: utf-8 -*-
"""皮肤系统：每套主题两个颜色（主色 brand + 辅色 bg），分区明确两色都可见：
  白天：标题栏 = 主色；侧边栏/内容区背景 = 辅色（向主色轻染保证可辨识）；卡片白色；输入控件取辅色加深
  夜间：全局深色底；标题栏 = 主色加深；交互色 = 主色提亮
文字颜色按背景亮度自适应。含中文字体回退链"""
from app.core import config

# 中文字体回退链
FONT_STACK = '"Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimHei", sans-serif'

# 每套主题仅两个颜色：brand（主色）+ bg（辅色，浅色）
SCHEMES = {
    "苹果青": {"brand": "#73AE52", "bg": "#FBF1D7"},
    "晴空蓝": {"brand": "#89C2FF", "bg": "#E6F7FF"},
    "白青":   {"brand": "#98B6C2", "bg": "#F5FBFE"},
    "菖蒲紫": {"brand": "#694D9F", "bg": "#FDF4DC"},
    "芍药粉": {"brand": "#F8B5D0", "bg": "#F5F5F5"},
    "极光蓝": {"brand": "#78C7D2", "bg": "#FFFEF9"},
    "薄荷绿": {"brand": "#3EB489", "bg": "#EAF7F0"},
    "蜜柑橙": {"brand": "#ED8B2D", "bg": "#FFF3E2"},
    "樱桃红": {"brand": "#E15A6B", "bg": "#FDEEF0"},
    "靛蓝":   {"brand": "#3F5AA9", "bg": "#EDF1FA"},
    "松石青": {"brand": "#2FA8A0", "bg": "#E7F7F5"},
    "琥珀金": {"brand": "#D19C2F", "bg": "#FAF3E3"},
    "石墨灰": {"brand": "#5E6A73", "bg": "#F2F4F6"},
    "落霞橘": {"brand": "#E2725B", "bg": "#FCF0EB"},
    "薰衣草": {"brand": "#9B7EDE", "bg": "#F3EFFC"},
}

CUSTOM_SCHEME = "自定义"

# 每套配色的文字描述（设置页展示）
SCHEME_DESCS = {
    "苹果青": "清新苹果绿配米黄底，温和护眼",
    "晴空蓝": "天空蓝配浅蓝底，清爽百搭（默认）",
    "白青": "低饱和青灰，极简安静",
    "菖蒲紫": "深紫主色配暖米底，古典雅致",
    "芍药粉": "樱粉主色配浅灰底，柔和轻盈",
    "极光蓝": "青蓝主色配暖白底，明快现代",
    "薄荷绿": "薄荷绿配淡绿底，清凉自然",
    "蜜柑橙": "暖橙配奶油底，活力温暖",
    "樱桃红": "玫红配淡粉底，明艳醒目",
    "靛蓝": "沉稳靛蓝配淡蓝底，商务稳重",
    "松石青": "松石青配浅青底，通透干净",
    "琥珀金": "琥珀金配米黄底，复古温暖",
    "石墨灰": "中性灰配浅灰底，冷静克制",
    "落霞橘": "落霞橘配霞光白底，热烈温暖",
    "薰衣草": "薰衣草紫配淡紫底，浪漫柔和",
    CUSTOM_SCHEME: "添加主题：自由搭配主题色、字体、背景、侧栏与内容区颜色",
}

DEFAULT_SKIN = {"scheme": "晴空蓝", "mode": "day", "bg_image": "", "opacity": 92, "blur": 30,
                "custom_brand": "", "custom_bg": "", "custom_themes": [],
                "titlebar_style": "system", "show_tool_icons": True,
                "splash_mode": "random", "splash_custom": "",
                "splash_ratio": 40}


def _lum(hexc):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _mix(hexc, other, k):
    """k=0 返回 hexc，k=1 返回 other"""
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    o = other.lstrip("#")
    r2, g2, b2 = int(o[0:2], 16), int(o[2:4], 16), int(o[4:6], 16)
    return "#{:02X}{:02X}{:02X}".format(
        int(r + (r2 - r) * k), int(g + (g2 - g) * k), int(b + (b2 - b) * k))


def _darken(hexc, k):
    return _mix(hexc, "#000000", k)


def _lighten(hexc, k):
    return _mix(hexc, "#FFFFFF", k)


def _rgba_str(hexc, alpha):
    r, g, b = int(hexc[1:3], 16), int(hexc[3:5], 16), int(hexc[5:7], 16)
    return "rgba({},{},{},{})".format(r, g, b, alpha)


def _rgba(hexc, alpha):
    if hexc.startswith("rgba"):
        return hexc
    return _rgba_str(hexc, alpha)


def scheme_names():
    return list(SCHEMES.keys())


def palette(scheme, mode="day", custom=None):
    """custom：用户自定义主题色板，可含 brand/bg/text/sidebar/panel（均可选，
    缺省项按内置规则派生）；夜间模式仅取 brand，其余深色派生保证可读"""
    is_cust = bool(custom) and bool(custom.get("brand"))
    if is_cust:
        s = {"brand": custom["brand"], "bg": custom.get("bg") or "#E6F7FF"}
    else:
        s = SCHEMES.get(scheme, SCHEMES["晴空蓝"])
    brand, bg = s["brand"], s["bg"]
    if mode == "night":
        return {
            "mode": "night", "brand": brand, "bg": "#15181D",
            "titlebar": _darken(brand, 0.55), "on_brand": "#FFFFFF",
            "on_brand_sub": _rgba_str("#FFFFFF", 0.65),
            "sidebar": "#171A20", "sidebar_text": "#C7CDD6", "sidebar_sub": "#8A93A0",
            "sidebar_hover": _rgba_str("#FFFFFF", 0.07),
            "sidebar_selected_bg": _rgba_str(brand, 0.30),
            "sidebar_selected_text": _lighten(brand, 0.35),
            "panel": "#1F242C", "panel2": "#262C36",
            "text": "#E6EAF0", "sub": "#98A2B0",
            "accent": _lighten(brand, 0.15) if _lum(brand) < 0.55 else brand,
            "accent_hover": _lighten(brand, 0.3),
            "border": "#343B46", "hover": "#2A313B", "selected": "#33404E",
        }
    # 白天：两色都可见——主色标题栏，辅色侧边栏（轻染主色）与内容区
    on_brand = "#2E2A20" if _lum(brand) > 0.62 else "#FFFFFF"
    sidebar = _mix(bg, brand, 0.12)          # 辅色可辨识化
    panel2 = _mix(bg, brand, 0.22)           # 输入控件取辅色进一步加深
    text = "#2A2F36"
    p = {
        "mode": "day", "brand": brand, "bg": bg,
        "titlebar": brand, "on_brand": on_brand,
        "on_brand_sub": _rgba_str(on_brand, 0.7),
        "sidebar": sidebar, "sidebar_text": "#33383F", "sidebar_sub": "#6E757E",
        "sidebar_hover": _rgba_str(brand, 0.12),
        "sidebar_selected_bg": _rgba_str(brand, 0.28),
        "sidebar_selected_text": _darken(brand, 0.35),
        "panel": "#FFFFFF", "panel2": panel2,
        "text": text, "sub": "#72797F",
        "accent": _darken(brand, 0.28) if _lum(brand) > 0.45 else brand,
        "accent_hover": _darken(brand, 0.12),
        "border": _mix(bg, "#000000", 0.16), "hover": _mix(bg, "#000000", 0.05),
        "selected": _mix(brand, "#FFFFFF", 0.68),
    }
    if is_cust:
        # 用户自定义项覆盖：字体颜色、侧栏颜色、内容区（卡片）颜色
        if custom.get("text"):
            p["text"] = custom["text"]
            p["sidebar_text"] = custom["text"]
            p["sub"] = _mix(custom["text"], bg, 0.45)
        if custom.get("sidebar"):
            p["sidebar"] = custom["sidebar"]
            p["sidebar_hover"] = _rgba_str(brand, 0.12)
            p["sidebar_selected_bg"] = _rgba_str(brand, 0.28)
            p["border"] = _mix(custom["sidebar"], "#000000", 0.16)
            p["hover"] = _mix(custom["sidebar"], "#000000", 0.05)
            p["panel2"] = _mix(custom["sidebar"], "#000000", 0.08)
        if custom.get("panel"):
            p["panel"] = custom["panel"]
    return p


def build_qss(p, alpha=100):
    """alpha 为面板不透明度（%），始终作用于标题栏/侧边栏/搜索框/卡片等全部面板；
    独立弹窗（QDialog）保持不透明，避免透明叠加变暗"""
    a = max(1, min(100, int(alpha)))

    def s(color):
        return _rgba(color, int(255 * a / 100))

    bg_solid = p["bg"]

    return """
* {{
    font-family: {font};
    outline: none;
}}
QWidget#Root {{ background: transparent; }}
QFrame#TitleBar {{
    background: {titlebar};
    border-bottom: 1px solid {border};
}}
QFrame#TitleBar QLabel {{ background: transparent; color: {on_brand}; }}
QLabel#AppTitle {{ font-size: 14px; font-weight: bold; }}
QLabel#AppVer {{ font-size: 11px; color: {on_brand_sub}; }}
QLabel#Hint {{ color: {on_brand_sub}; font-size: 12px; }}

QFrame#Sidebar {{
    background: {sidebar};
    border-right: 1px solid {border};
}}
QListWidget#NavList {{
    background: transparent; border: none;
    color: {sidebar_text}; font-size: 13px;
}}
QListWidget#NavList::item {{
    height: 34px; padding-left: 6px;
    color: {sidebar_sub}; border: none; background: transparent;
}}
QListWidget#NavList::item:hover {{ background: {sidebar_hover}; color: {sidebar_text}; }}
QListWidget#NavList::item:selected {{ background: {sidebar_selected_bg}; color: {sidebar_selected_text}; font-weight: bold; }}

QLineEdit#SearchBox {{
    background: {panel2}; border: 1px solid {border};
    padding: 6px 10px; color: {text}; font-size: 13px; border-radius: 0;
}}
QLineEdit#SearchBox:focus {{ border-color: {accent}; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border}; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {sub}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}

QLabel {{ color: {text}; background: transparent; }}
QLabel#PageTitle {{ font-size: 16px; font-weight: bold; }}
QLabel#Sub {{ color: {sub}; font-size: 11px; }}
QLabel#CardName {{ font-size: 13px; font-weight: bold; }}
QLabel#GroupTitle {{ color: {sub}; font-size: 12px; font-weight: bold; }}

QFrame#Card {{
    background: {card}; border: 1px solid {border};
}}
QFrame#Card:hover {{ border: 1px solid {accent}; }}

QFrame#Chip {{
    background: {card}; border: 1px solid {border};
}}
QFrame#Chip:hover {{ border: 1px solid {accent}; }}

QPushButton#NavTab {{
    background: {card}; border: 1px solid {border};
    color: {text}; padding: 5px 16px; border-radius: 0; font-size: 12px;
}}
QPushButton#NavTab:hover {{ border-color: {accent}; color: {accent}; }}
QPushButton#NavTab:checked {{ background: {accent}; color: #ffffff; border-color: {accent}; font-weight: bold; }}

QPushButton#Ghost {{
    background: transparent; border: 1px solid {border};
    color: {text}; padding: 5px 14px; border-radius: 0; font-size: 12px;
}}
QPushButton#Ghost:hover {{ border-color: {accent}; color: {accent}; }}
QPushButton#Ghost:checked {{ background: {accent}; color: #ffffff; border-color: {accent}; }}
QPushButton#Accent {{
    background: {accent}; color: #ffffff; border: none;
    padding: 5px 16px; border-radius: 0; font-size: 12px; font-weight: bold;
}}
QPushButton#Accent:hover {{ background: {accent_hover}; }}

QMenu {{
    background: {card}; border: 1px solid {border}; color: {text};
    border-radius: 0; padding: 3px 0; margin: 0;
}}
QMenu::item {{
    padding: 6px 24px 6px 10px; font-size: 12px; border-radius: 0;
    background: transparent;
}}
QMenu::icon {{ margin-left: 10px; margin-right: 8px; padding: 0; }}
QMenu::item:selected {{ background: {selected}; color: {accent}; }}
QMenu::separator {{ height: 1px; background: {border}; margin: 4px 0; }}

QDialog {{ background: {bg_solid}; color: {text}; }}
QDialog QLabel {{ color: {text}; }}
QFrame#DlgBar {{
    background: {bg_solid_title};
    border-bottom: 1px solid {border};
}}
QFrame#DlgBar QLabel {{ background: transparent; color: {on_brand}; }}
QLabel#DlgTitle {{ font-size: 13px; font-weight: bold; }}
QPushButton#DlgClose {{
    background: transparent; border: none; border-radius: 0;
    image: url({close_icon});
}}
QPushButton#DlgClose:hover {{ background: {sidebar_selected_bg}; }}
QFrame#DlgBody {{ background: {bg}; }}
QLineEdit, QComboBox, QSpinBox {{
    background: {card}; border: 1px solid {border};
    padding: 5px 8px; color: {text}; border-radius: 0; font-size: 12px;
}}
QLineEdit:focus, QComboBox:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView {{
    background: {card}; color: {text};
    selection-background-color: {selected}; selection-color: {accent};
    border: 1px solid {border};
}}
QSlider::groove:horizontal {{ height: 4px; background: {border}; }}
QSlider::sub-page:horizontal {{ background: {accent}; }}
QSlider::handle:horizontal {{
    width: 14px; height: 14px; margin: -5px 0;
    background: {accent}; border-radius: 7px;
}}
QFrame#Swatch {{ border: 2px solid {border}; }}
QFrame#Section {{ background: {card}; border: 1px solid {border}; }}
""".format(
        font=FONT_STACK,
        titlebar=s(p["titlebar"]), bg=s(p["bg"]), bg_solid=p["bg"],
        bg_solid_title=p["titlebar"], on_brand=p["on_brand"],
        on_brand_sub=p["on_brand_sub"],
        sidebar=s(p["sidebar"]), sidebar_text=p["sidebar_text"], sidebar_sub=p["sidebar_sub"],
        sidebar_hover=p["sidebar_hover"], sidebar_selected_bg=s(p["sidebar_selected_bg"]),
        sidebar_selected_text=p["sidebar_selected_text"],
        panel2=s(p["panel2"]), card=s(p["panel"]),
        text=p["text"], sub=p["sub"], accent=p["accent"], accent_hover=p["accent_hover"],
        border=p["border"], hover=s(p["hover"]), selected=s(p["selected"]),
        close_icon=config.ICON_DIR.replace("\\", "/") + "/close.svg",
    )
