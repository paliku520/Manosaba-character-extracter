# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

从游戏「魔法少女的魔女审判」(manosaba) 的 Unity bundle 文件中提取角色精灵，支持自动检测组件数据、直接导出精灵或拼接完整立绘。采用 **PyWebView 现代图形界面**（WebView2 渲染）。

## 功能

- **智能检测** — 自动识别 bundle 组件数据：无组件直接导出精灵，有组件可导出或拼接
- **角色立绘拼接** — 按组件位置与深度合成完整立绘，支持部件分类、缩略图预览、实时合成预览
- **部件管理** — 部件搜索、自然排序（前缀字母+数字）、分组折叠、一键全选；已选精灵可点击复制名称
- **实时预览** — 合成预览支持滚轮缩放（以鼠标为中心）、拖动平移，最小缩放适配完整分辨率
- **层级结构** — 组件树查看，每行带复制按钮
- **缓存复用** — 已提取数据缓存到 `temp/`，重复加载无需重新解包
- **内存回收** — 加载/提取/合成过程即时释放资源并触发 GC，切换角色清理上一角色数据，退出前强制回收并输出资源检测日志
- **调试模式** — 设置中开启后实时监视内存/CPU/窗口分辨率（显示于窗口标题栏，仅本次运行有效）
- **日志文件** — 控制台日志同步写入 `logs/`（按启动时间命名），可一键清理
- **多语言** — 简体中文 / English / fiXmArge（架空语言），自动跟随系统，可在设置中切换
- **主题切换** — 深色 / 浅色主题，持久化到设置
- **累计导出** — 统计成功使用导出功能的次数（关于页展示）
- **关于页** — 开发者信息、项目链接、背景轮播、检查更新
- **自动更新检查** — 启动时静默检查 GitHub 新版本

## 环境要求

- Python 3.10+
- `pip install -r requirements.txt`

> 目前主要针对 **Windows** 充分测试，Linux/macOS 兼容性未知。

## 使用

### 运行
```bash
python run.py
```

1. 点击 **加载游戏目录** → 选择游戏根目录或 `characters` 目录
2. 点击左侧角色 → 程序自动检测：
   - **无组件数据** → 确认后直接导出所有精灵
   - **有组件数据** → 选择「直接导出」或「拼接角色图像」
3. 拼接模式：勾选部件 → 实时预览 → 保存合成 PNG

### 设置

点击左侧 **设置** 可配置：**输出目录**（自定义导出位置，自动记忆）、**语言**、**主题**（深色/浅色）、**显示中文名**（仅中文界面可选）、**调试模式**（监视内存/CPU/窗口，默认关闭且仅本次运行）、**检查更新**、**清理**（`temp/` 缓存、`output/` 目录或 `logs/` 日志文件）。

> 设置保存在程序根目录的 `settings.json`。

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
- 当前版本的立绘合成功能无法完全还原游戏原作的立绘图层效果。部分角色的部件（如眼睛、头发、脸部遮罩等）合成后与游戏内实际显示存在差异。

**具体表现**
- 部分图层叠加顺序与游戏原作不一致
- ClippingMask（剪切蒙版/遮罩图层）未被正确处理，遮罩图层被当作普通精灵渲染，而不是作为不可见的裁剪区域
- 受此影响的角色部件包括但不限于：眼睛、头发、脸部表情部件等

**对比效果**

下图为游戏原作（右）与当前合成器输出（左）的对比：

![立绘合成对比](./docs/images/comparison.png)

**原因分析**
- 游戏角色立绘使用了 Unity 的 `SpriteRenderer` + `ClippingMask` 机制来实现复杂的图层裁剪效果。当前合成器仅根据 `sorting_order` 进行简单的图层叠加，未实现以下功能：

1. **剪切蒙版（Clipping Mask）**：`ClippingMask` 类型的精灵用于裁剪目标图层的显示区域
2. **遮罩作用范围**：每个 `ClippingMask` 仅影响特定范围内的部件（如 `ClippingMask_Eyes` 遮罩只影响眼部区域），而非全局
3. **半透明遮罩**：遮罩带有 `color.a < 1.0` 的半透明属性，需要正确处理

**临时解决方案**
1. 直接导出所有精灵文件，使用`Adobe Photoshop`等图片软件手动编辑。
2. 使用 B站：[雪莉苹果汁](https://space.bilibili.com/3546949672241842) 的 [Manosaba mod](http://manosabamoddoc.fuyumi.xyz/)，直接在游戏本体内编辑（工具提供了`组件结构`的信息）
3. 等待后续修复。


## 项目结构

```
├── run.py             # 主程序入口（PyWebView 后端 + JsApi 桥接）
├── webui/             # 前端（index.html + css/ + js/，纯本地无 CDN）
├── src/               # 核心模块（加载、合成、导出、缓存、i18n、设置等）
├── scripts/           # PyInstaller 打包脚本
├── output/            # 输出目录（程序生成）
└── temp/              # 精灵缓存（程序生成）
```

技术栈：[UnityPy](https://github.com/K0lb3/UnityPy)（bundle 解析）、Pillow（图像处理）、[pywebview](https://github.com/r0x0r/pywebview)（现代 GUI，WebView2 渲染）。

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

## 打包为 EXE

```bash
pip install pyinstaller
python scripts\build_exe.py                          # 默认 onedir（启动快）
python scripts\build_exe.py --onefile                # 单文件 exe（适合分发）
python scripts\build_exe.py --name MyApp --icon icon.ico
```

- **版本信息自动注入**（文件版本 / 产品名称 / 产品版本等，降低杀软误报）
- 可选参数：`--company "名称"`（公司/开发者）、`--product`、`--description`、`--copyright`（默认用脚本顶部 `APP_*` 常量）、`--console false`（无控制台 GUI 模式）

> 图标需为 `.ico` 格式。`--onefile` 每次运行需解压、启动较慢。更多参数见 `python scripts\build_exe.py --help`。