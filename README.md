# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

从游戏「魔法少女的魔女审判」(manosaba) 的 Unity bundle 中提取角色精灵：自动检测组件数据、直接导出精灵或拼接完整立绘。界面为 **Electron 无边框窗口**，核心逻辑由 **Python 后端**（子进程 + stdio JSON-RPC）承担。

## 功能

- **智能检测** — 自动识别组件数据：无组件可预览/直接导出，有组件可导出或拼接
- **角色立绘拼接** — 按部件位置与深度合成完整立绘，支持分类、缩略图与实时预览
- **部件管理** — 搜索、自然排序、分组折叠、一键全选、点击复制名称
- **实时预览** — 滚轮缩放（以鼠标为中心）、拖动平移
- **精灵预览** — 无组件角色一键预览全部精灵，勾选导出
- **层级结构** — 组件树查看，每行带复制按钮
- **缓存复用** — 已提取数据缓存到 `temp/`，重复加载无需重新解包
- **内存回收** — 即时释放资源并触发 GC，退出前强制回收
- **调试模式** — 实时监视内存/CPU/窗口分辨率（仅本次运行）
- **日志文件** — 控制台日志同步写入 `logs/`，可一键清理
- **多语言 / 主题** — 简体中文 / English / fiXmArge，深浅色主题可切换并持久化
- **累计导出 / 关于页 / 自动更新检查 / 免责声明**（第三方非官方工具）

## 环境要求

- **Python 3.10+**：`pip install -r requirements.txt`
- **Node.js 18+**：`cd electron && npm install`

> 目前主要针对 **Windows** 充分测试，Linux/macOS 兼容性未知。

## 使用

### 运行

**推荐：Electron 无边框窗口**（原生 Aero Snap / 拖动 / 双击最大化 / 边缘缩放）
```bash
cd electron
npm install        # 首次安装依赖
npm start          # 启动（等价 npx electron .）
```

**备选：PyWebView / WebView2 模式**
```bash
python run.py
```

### 使用步骤

1. 点击左侧角色 → 程序自动检测：
   - **无组件数据** → 预览精灵 / 直接导出全部 / 取消
   - **有组件数据** → 直接导出 / 拼接角色图像
2. 拼接模式：勾选部件 → 实时预览 → 保存合成 PNG

### 设置

可配置：**输出目录**（自动记忆）、**语言**、**主题**、**调试模式**、**检查更新**、**清理**（`temp/` 缓存、`output/` 目录或 `logs/` 日志）。

> 设置保存在程序目录 `data/settings.json`（已设隐藏属性）。

### 数据存储路径（打包版）

打包安装后，程序在**安装目录**下读写以下数据（以 `D:\mce` 为例）：

| 路径 | 用途 |
|---|---|
| `D:\mce\data` | 设置文件 `settings.json` |
| `D:\mce\output` | 导出精灵 / 合成立绘 PNG |
| `D:\mce\temp` | 精灵缓存（可清理） |
| `D:\mce\resources\backend\logs` | 运行日志（可一键清理） |

> 绿色版解压到任意目录后数据同样生成在解压目录下；`data/` 可用环境变量 `MCE_DATA_DIR` 重定向。

### 输出结构

```
output/
├── <角色名>/            # 无组件：精灵直接平铺
└── <角色名>/            # 有组件：sprites/（精灵）+ composite/（合成图）
temp/                    # 精灵缓存（可清除，重复角色加速加载）
```

## 已知问题

### 立绘合成图层顺序/遮罩处理不完整

**问题描述**
当前版本无法完全还原游戏原作的立绘图层效果，部分部件（眼睛、头发、脸部遮罩等）合成后与游戏内显示存在差异。

**具体表现**
- 部分图层叠加顺序与游戏原作不一致
- ClippingMask（剪切蒙版）被当作普通精灵渲染，而非不可见的裁剪区域

**对比效果**

![立绘合成对比](./docs/images/comparison.png)

**原因分析（可能有误）**
- 游戏立绘使用 Unity 的 `SpriteRenderer` + `ClippingMask` 实现图层裁剪，当前合成器仅根据 `sorting_order` 简单叠加，未实现：

1. **剪切蒙版（Clipping Mask）**：`ClippingMask` 精灵用于裁剪目标图层的显示区域
2. **遮罩作用范围**：每个蒙版仅影响特定部件（如 `ClippingMask_Eyes` 只影响眼部区域），而非全局
3. **半透明遮罩**：蒙版带 `color.a < 1.0` 的半透明属性

**临时解决方案**
1. 直接导出所有精灵文件，用 Photoshop 等软件手动编辑
2. 使用 B站 [雪莉苹果汁](https://space.bilibili.com/3546949672241842) 的 [Manosaba mod](http://manosabamoddoc.fuyumi.xyz/) 在游戏本体内编辑（工具提供组件结构信息）
3. 等待后续修复


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

**重构与优化工作包括：**
- **架构重构**：将原单体文件拆分为模块化设计（`bundleloader`, `compositor`, `tools` 等），提升代码可维护性。
- **性能优化**：优化 UI 响应与数据处理流程，消除原项目中不必要的全量 UI 重建。
- **功能增强**：新增多角色管理、批量目录扫描、路径记忆、层级结构树（TreeView）、多语言支持及缓存复用等。

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

- 自动注入版本信息（文件版本 / 产品名称等，降低杀软误报）；可选 `--company/--product/--description/--copyright`（默认用脚本顶部 `APP_*` 常量）、`--console false`
- 图标需 `.ico` 格式；`--onefile` 启动较慢；更多参数见 `--help`

### Electron 应用
```bash
python scripts\build_electron_backend.py   # 仅打后端 → dist/backend/
python scripts\build_electron.py            # 一键：后端 + 绿色版 zip + 安装版 Setup.exe
```

- `build_electron.py` 可选参数：`--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- electron-builder 配置见 `electron/electron-builder.yml`（需先安装 electron 目录的 node_modules）
- 更多参数见 `--help`