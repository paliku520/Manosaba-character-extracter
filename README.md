# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

从游戏「魔法少女的魔女审判」(manosaba) 的 Unity bundle 中提取角色精灵：自动检测组件数据、直接导出精灵或拼接完整立绘。界面为 **Electron 无边框窗口**，核心逻辑由 **Python 后端**（子进程 + stdio JSON-RPC）承担。

## 相关项目
>- **[Manosaba-Library](https://github.com/QwQSakuya/Manosaba-Library)** —— 同为《魔法少女的魔女审判》社区的项目，是一个玩家自发的非官方资料站，收录剧情节点图谱、证物图鉴、CG画廊、语音音乐与全素材库索引，并支持在线立绘预览。

## 功能

- **智能检测** — 自动识别组件数据：无组件可预览/直接导出，有组件可导出或拼接
- **角色立绘拼接** — 按部件位置、深度与剪切蒙版合成完整立绘，支持分类、缩略图，Multiply / Overlay / Softlight 混合模式还原原作效果
- **Anan 素描本** — 选中 anan 素描本部件时可自定义文字（字号 / 对齐 / 自动换行）
- **部件管理** — 搜索、自然排序、分组折叠、一键全选、点击复制名称
- **实时预览** — 滚轮缩放（以鼠标为中心）、拖动平移
- **精灵预览** — 无组件角色一键预览全部精灵，勾选导出
- **层级结构** — 组件树查看，每行带复制按钮
- **拖拽导入** — 将游戏目录或 bundle 文件拖入窗口即可加载，自动记忆上次使用的游戏目录
- **缓存复用** — 已提取数据缓存到 `temp/`，重复加载无需重新解包
- **内存回收** — 即时释放资源并触发 GC，退出前强制回收
- **任务栏效果** — Electron 模式读条期间显示进度，完成后任务栏闪烁提示
- **调试模式** — 实时监视内存/CPU/窗口分辨率（仅本次运行）
- **日志文件** — 控制台日志同步写入 `logs/`，可一键清理
- **多语言 / 主题** — 简体中文 / English / 日本語 / 魔女语，深浅色主题 + 角色主题色可切换并持久化
- **累计导出 / 关于页 / 自动更新检查 / 免责声明**（第三方非官方工具）

## 环境要求

- **Python 3.10+**：`pip install -r requirements.txt`
- **Node.js 18+**：`cd electron && npm install`

> 目前主要针对 **Windows** 充分测试，Linux/macOS 兼容性未知。

## 使用

### 运行（推荐：启动脚本）

Windows 下直接使用仓库根目录的 `start.bat` 启动脚本：

```bat
start.bat            :: Electron 无边框窗口（默认，原生 Aero Snap / 拖动 / 双击最大化 / 边缘缩放）
start.bat py         :: PyWebView / WebView2 模式（原生窗口）
start.bat help       :: 显示帮助
```

**首次运行前需安装依赖**：

```bash
pip install -r requirements.txt        # Python 依赖
cd electron && npm install             # Electron 依赖
```

> 也可手动启动：`cd electron && npm start`（Electron 模式）或 `python run.py`（PyWebView 模式）


### 使用步骤

1. 点击左侧角色 → 程序自动检测：
   - **无组件数据** → 预览精灵 / 直接导出全部 / 取消
   - **有组件数据** → 直接导出 / 拼接角色图像
2. 拼接模式：勾选部件 → 实时预览 → 保存合成 PNG

### 设置

可配置：**输出目录**（自动记忆）、**语言**、**主题与主题色**、**显示原始文件名**、**防剧透警告**、**调试模式**、**检查更新**、**清理**（`temp/` 缓存、`output/` 目录或 `logs/` 日志）。

> 设置保存在程序目录 `data/settings.json`（已设隐藏属性）。

### 数据存储路径（打包版）

打包安装后，程序在**安装目录**下读写以下数据（以 `D:\mce` 为例）：

| 路径 | 用途 |
|---|---|
| `D:\mce\data` | 设置文件 `settings.json` |
| `D:\mce\output` | 导出精灵 / 合成立绘 PNG |
| `D:\mce\temp` | 精灵缓存（可清理） |
| `D:\mce\resources\backend\logs` | 运行日志（可一键清理） |

> 数据（`data`/`output`/`temp`/`logs`）始终**优先存放在程序所在目录**（安装目录或绿色版解压目录），仅当该目录不可写（如授权失败、杀毒软件拦截、只读盘）时才回退到 `%APPDATA%\Manosaba Character Extracter` 作为兜底。
>
> 默认安装到 `C:\Program Files\MCE` 时，安装程序已为普通用户授予该目录的写入与删除权限，因此数据仍直接生成在安装目录下。卸载时若检测到安装目录下存在数据（静默卸载除外），会弹窗提示将清除全部数据，选择「否」将中止卸载。

### 输出结构

```
output/
├── <角色名>/            # 无组件：精灵直接平铺
└── <角色名>/            # 有组件：sprites/（精灵）+ composite/（合成图）
    ├── character_data.json  # 部件 / 层级数据
    └── mask_mapping.json    # 遮罩与混合方式映射
temp/                    # 精灵缓存（可清除，重复角色加速加载）
```

## 项目结构

```
├── run.py             # PyWebView 模式入口（WebView2，备用）
├── backend.py         # Electron 模式 Python 后端子进程（stdio JSON-RPC）
├── electron/          # Electron 界面壳
│   ├── main.js        #   主进程：无边框窗口 + Python 子进程桥接 + 窗口控制
│   ├── preload.js     #   桥接层：模拟 pywebview API，前端零改动
│   └── package.json
├── webui/             # 前端（index.html + css/ + js/，纯本地无 CDN，两模式共用）
├── src/               # 核心模块（加载、合成、导出、缓存、i18n、设置等）
├── scripts/           # PyInstaller 打包脚本
├── output/            # 输出目录（程序生成）
└── temp/              # 精灵缓存（程序生成）
```

技术栈：[UnityPy](https://github.com/K0lb3/UnityPy)（bundle 解析）、Pillow（图像处理）、[Electron](https://www.electronjs.org/)（无边框 UI 壳，Chromium 渲染 + 原生 Aero Snap）、[pywebview](https://github.com/r0x0r/pywebview)（备用 WebView2 模式）。

## 致谢与许可证

### 原作信息

本工具提取的内容来源于游戏 **「魔法少女ノ魔女裁判」(Manosaba)**
© 2024 **Re,AER LLC. / Acacia** — 原游戏所有权利归其所有。

### 本工具作者

**paliku520（云野 风云）** — 开发与维护

### 技术致谢

本项目是 [KabeNaki](https://github.com/lingk7/KabeNaki) 项目的**深度重构与性能优化版本**，感谢原项目作者 [lingk7](https://github.com/lingk7) 的杰出工作。

在此基础上，本项目进行了全面的技术升级：
- **GUI 框架迁移**：从 `tkinter` 完全迁移至 `Electron`，带来了更现代、流畅的用户界面和更好的平台兼容性。
- **架构与打包重构**：将项目拆分为 Python 后端与 Electron 前端，并提供了一键打包的安装程序，提升了分发与安装体验。
- **功能与体验增强**：在原有精灵提取基础上，实现了更精准的 `ClippingMask` 遮罩处理、角色主题色、实时预览缩放、多语言扩展及大量细节优化。

### 许可证

本项目采用 **GPL-3.0 许可证**，详见 [LICENSE](LICENSE) 文件。

**免责声明**：本工具仅供学习和个人研究使用。使用本工具提取的内容，其版权归原游戏开发者所有。

> 本工具为**第三方非官方工具**，与游戏官方无关。

## 打包为 EXE

### PyWebView 独立版
```bash
pip install pyinstaller
python scripts\build_pywebview.py                          # 默认 onedir（启动快）
python scripts\build_pywebview.py --onefile                # 单文件 exe
python scripts\build_pywebview.py --name MyApp --icon icon.ico
```

- 自动注入版本信息（文件版本 / 产品名称等，降低杀软误报）；版本号自动取自 `src/version.py`；可选 `--company/--product/--description/--copyright`（默认用脚本顶部 `APP_*` 常量）、`--console false`
- 图标需 `.ico` 格式；`--onefile` 启动较慢；更多参数见 `--help`

### Electron 应用
```bash
python scripts\build_electron_backend.py   # 仅打后端 → dist/backend/
python scripts\build_electron.py            # 一键：后端 + 绿色版 zip + 安装版 Setup.exe
```

- `build_electron.py` 可选参数：`--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- 可选 `--company/--product/--description/--copyright` 透传给后端 exe 版本信息（默认用脚本顶部 `APP_*` 常量）
- 版本号自动取自 `src/version.py`（产物名 `MCE-Setup-<版本>.exe` / `MCE-<版本>-win.zip` 与后端 exe 版本信息均自动同步，改版本只改这一处）
- electron-builder 配置见 `electron/electron-builder.yml`（需先安装 electron 目录的 node_modules）
- 更多参数见 `--help`