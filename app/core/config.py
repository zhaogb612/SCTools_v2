# -*- coding: utf-8 -*-
"""路径与配置读写：全部基于相对路径，配置存放于 resources/config/"""
import json
import os
import sys

APP_VER = "3.1"   # 与 GitHub Release tag 对应（tag 形如 v3.1 时此处写 "3.1"）

def _base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


APP_DIR = _base_dir()
ICON_DIR = os.path.join(APP_DIR, "resources", "icons")
SKIN_DIR = os.path.join(APP_DIR, "resources", "skins")


def config_dir():
    # 打包后优先 exe 同级 resources，回退 _internal/resources
    p = os.path.join(_base_dir(), "resources", "config")
    if not os.path.isdir(p) and getattr(sys, "frozen", False):
        p = os.path.join(_base_dir(), "_internal", "resources", "config")
    return p


def config_path(name):
    return os.path.join(config_dir(), name)


def load_json(name, default):
    path = config_path(name)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # 配置损坏时回退默认值并重写
    save_json(name, default)
    return default


def save_json(name, data):
    os.makedirs(config_dir(), exist_ok=True)
    with open(config_path(name), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
