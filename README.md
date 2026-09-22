# SCTools 工具箱 v3.0 (PySide6 重构版)

原 PyQt5 版 SCTools 的重构，界面参考图吧工具箱。所有第三方工具本体不在本项目中，本程序是一个可扩展的启动器。

## 相比旧版的改进

1. **可扩展应用管理**：内置工具管理器，可在界面内添加/编辑/删除应用（可指定程序或目录），分类支持自定义，配置存于 `resources/config/tools.json`
2. **皮肤系统**：4 套内置主题（拂晓蓝/曜石黑/青竹绿/樱语粉），支持自定义背景图片与面板不透明度
3. **界面优化**：仿 Mac 风格标题栏（红黄绿控制按钮位于右侧）、直角卡片、窗口可缩放、流式卡片布局
4. **导航菜单**：保留常用网站与推荐应用下载地址；链接已于 2026-09 逐一校验——「电手」原 4hou.com 链接有误已修复为 www.dians.net，微信网页版已标注部分账号不可登录；支持界面内自定义添加/编辑（右键网址卡片）
5. **打包结构**：主程序位于根目录，图标/皮肤/配置均在同级 `resources/` 资源文件夹，全部相对路径引用
6. **中文字体**：字体回退链 `Microsoft YaHei UI → Microsoft YaHei → PingFang SC → Noto Sans CJK SC → SimHei`，QSS 与 QFont 双重生效
7. **图标规范**：全程无 emoji，界面图标全部为 feather 风格线性 SVG（源码内置定义，首次运行释放到 `resources/icons/`）

## 运行

```bash
pip install -r requirements.txt
python main.py
```

## 打包

```bash
build.bat        # 产物在 dist/SCTools2/，资源目录自动复制到 exe 同级
```

## 目录结构

```
SCTools2/
├── main.py                  # 入口
├── tools/                   # 第三方绿色工具（自包含，整体复制自旧项目）
├── app/
│   ├── core/
│   │   ├── config.py        # 路径与 JSON 配置读写
│   │   ├── app_manager.py   # 应用管理（增删改查/启动/路径迁移）
│   │   ├── nav_manager.py   # 导航管理（含已校验的默认链接）
│   │   └── theme.py         # 双色主题调色板 + 全局 QSS + 字体回退链
│   └── ui/
│       ├── icons.py         # SVG 图标定义与着色加载
│       ├── dialogs.py       # 统一弹窗基类（方角自定义标题栏）+ 消息框
│       ├── flow_layout.py   # 流式布局
│       ├── title_bar.py     # 仿 Mac 标题栏（控制按钮右侧）
│       ├── main_window.py   # 主窗口（自绘背景/侧边导航/页面栈）
│       ├── tools_page.py    # 工具箱页（纯文字卡片/自适应网格/拖拽排序）
│       ├── tool_dialog.py   # 添加/编辑应用对话框（含删除按钮）
│       ├── nav_page.py      # 网站导航页（NavDialog 内置）
│       └── settings_page.py # 设置页（双色主题/日夜/背景/透明度）
└── resources/
    ├── config/              # tools.json / nav.json / skin.json（运行时生成）
    ├── icons/               # SVG 图标（运行时释放）
    └── skins/               # 建议存放自定义背景图
```

## 配置文件说明

- `resources/config/tools.json`：分类与应用清单（name/category/description/path）
- `resources/config/nav.json`：导航项（name/url/description/group）
- `resources/config/skin.json`：theme（主题名）/ bg_image（背景图路径）/ opacity（面板不透明度 50-100）

可直接备份整个 `resources/` 迁移配置。
