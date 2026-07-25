# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

从游戏「魔法少女的魔女审判」(manosaba) 的 Unity bundle 文件中提取角色精灵，支持自动检测组件数据、直接导出精灵或拼接完整立绘。

## 功能

- **自动检测** — 分析 bundle 是否包含 `SpriteRenderer` + `Transform` 组件数据
- **两种模式**：
  - 无组件数据 → 直接导出所有精灵 PNG
  - 有组件数据 → 可选择直接导出或拼接角色图像
- **已选精灵列表** — 右侧面板实时显示已勾选的精灵文件名，一目了然
- **实时预览** — 勾选/取消部件时自动合成预览（500ms 防抖）
- **部件选择** — 按分类分组显示部件，带缩略图预览，支持全选/取消
- **角色立绘拼接** — 按组件位置和排序深度合成完整角色图像
- **层级结构查看** — TreeView 树状展示角色组件层级
- **进度条显示** — 所有耗时操作（加载、导出、合成）显示实际进度百分比
- **多语言支持** — 内置简体中文/English/fiXmArge（架空语），自动跟随系统语言
- **缓存复用** — 已提取的角色数据缓存到 `temp/` 目录，重复加载无需重新解包
- **清除缓存按钮** — 一键清空缓存，释放磁盘空间
- **自适应布局** — 窗口缩小时各面板仍保持可用，滚动条始终可见
- **路径记忆** — 自动记住上次选择的游戏目录
- **自定义输出路径** — 支持命令行参数指定输出目录，灵活整合到工作流中

## 环境要求

- Python 3.10+
- 依赖见 [`requirements.txt`](requirements.txt)
### 依赖安装
```bash
pip install -r requirements.txt
```
### 新增语言

如需添加新语言，编辑 `src/i18n.py`：
1. 定义语言常量（如 `LANG_JP = "ja_JP"`）
2. 加入 `LANGUAGE_CODES` 列表
3. 为每个翻译键补充该语言的条目
4. 添加 `lang.ja_JP` 显示名称

> 下拉框自动根据 `LANGUAGE_CODES` 动态生成，无需修改 `run.py`。

## 平台兼容性

本项目主要针对 **Windows** 平台开发和测试，目前**尚未在其他操作系统上进行充分测试**。

- **Windows 10/11**：为主要开发和测试平台，功能正常。
- **Linux**：兼容性未知，Tkinter 和 UnityPy 在 Linux 下可能存在表现差异。
- **macOS**：兼容性未知，界面和文件路径处理可能存在问题。

如果你在非 Windows 平台上成功运行或遇到问题，欢迎提交 Issue 或 Pull Request 分享你的经验。

## 使用

### 基础运行
```bash
python run.py
```
### 命令行参数（exe程序仍然可以正常使用）

```bash
python run.py --help
```

| 参数 | 说明 |
|------|------|
| `-h`, `--help` | 显示帮助信息 |
| `-c`, `--clean` | 启动前清空输出目录（默认或自定义路径） |
| `-o <路径>`, `--output <路径>` | 指定输出目录（支持绝对/相对路径，相对路径基于程序根目录） |
| `--clear-cache` | 仅清除缓存文件夹后退出（不启动 GUI） |
| `--git-clean` | 清除 output 和 temp 目录后退出（用于 git 提交前清理） |

**示例：**
```bash
# 查看帮助
python run.py --help

# 清空默认输出目录后启动
python run.py --clean

# 指定自定义输出路径
python run.py --output D:/game_exports

# 仅清除缓存，不启动 GUI
python run.py --clear-cache

# 组合使用
python run.py -c -o E:/exports
```
### 工作流程

1. 点击 **加载游戏目录** → 选择游戏根目录或 `characters` 目录
2. 在左侧角色列表中点击要处理的角色
3. 程序自动检测 bundle 类型：
   - **无组件数据** → 弹窗确认后直接导出所有精灵
   - **有组件数据** → 弹窗询问处理方式
4. 选择 **拼接角色图像** 后：
   - 在「部件选择」页勾选/取消要包含的部件
   - 右侧「已选精灵」面板实时列出已勾选的部件文件名
   - 开启 **自动更新** 可实时预览合成效果
   - 点击 **生成合成图像** 手动合成
   - 点击 **保存合成图像** 导出 PNG

### 目录结构

output/ 目录结构根据角色类型自动区分：

```
程序根目录/
├── output/                ← 最终输出目录
│   ├── <角色名>/          ← 无组件角色：精灵直接平铺
│   │   ├── ArmL01.png
│   │   ├── Body.png
│   │   └── ...
│   └── <角色名>/          ← 有组件角色：按类型分子目录
│       ├── sprites/       ← 导出的精灵
│       │   ├── ArmL01.png
│       │   ├── Body.png
│       │   └── ...
│       └── composite/     ← 合成图
│           ├── <角色名>_composite.png
│           └── ...
├── temp/                  ← 精灵缓存目录（可手动清除，重复角色时加速加载）
│   └── <角色名>/
│       ├── character_data.json   ← 层级 + 部件数据
│       └── sprites/
│           ├── ArmL01.png
│           ├── Body.png
│           └── ...
├── src/                   ← 源码目录
├── run.py                 ← 主程序入口
└── ...
```

>`temp/` 目录为自动生成的缓存。切换角色时不会自动删除，点击左侧「清除缓存文件夹」按钮可手动释放空间。
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
项目根目录/
├── run.py                       # ★ 主程序入口（GUI + 事件处理）
├── requirements.txt             # Python 依赖
│
├── src/                         # ── 核心模块 ──
│   ├── __init__.py
│   ├── bundleloader.py          # Bundle 文件搜索与加载
│   ├── compositor.py            # 精灵提取 / 组件检测 / 图像合成
│   ├── export_manager.py        # 精灵导出 & 合成图保存（目录路由）
│   ├── cache_manager.py         # 缓存读写与完整性验证
│   ├── i18n.py                  # 国际化（中/英/架空语）
│   ├── logtools.py              # 日志工具
│   └── version.py               # 配置当前软件版本
│
├── src/                         # ── UI 模块 ──
│   ├── ui_builder.py            # 界面构造（主布局、各标签页）
│   └── ui_helpers.py            # UI 工具（进度条、预览、层级树等）
│
├── scripts/                     # ── 构建脚本 ──
│   └── build_exe.py             # PyInstaller 打包脚本
│
├── output/                      # ★ 最终输出（由程序生成）
├── temp/                        # ★ 精灵缓存（由程序生成）
│
├── .gitignore
├── LICENSE
└── README.md
```

## 技术栈

- **[UnityPy](https://github.com/K0lb3/UnityPy)** — Unity bundle 解析
- **[Pillow](https://python-pillow.org/)** — 图像处理与合成
- **tkinter** — GUI 界面

## 致谢与许可证

### 原作信息

本工具提取的内容来源于游戏 **「魔法少女の魔女审判」(Manosaba)**  
© 2024 **Re,AER LLC. / Acacia** — 原游戏所有权利归其所有。

### 本工具作者

**paliku520（云野 风云）** — 开发与维护

### 技术致谢

本项目是 [KabeNaki](https://github.com/lingk7/KabeNaki) 项目的**深度重构与性能优化版本**，感谢原项目作者 [lingk7](https://github.com/lingk7) 的杰出工作。

**重构与优化工作包括：**
- **架构重构**：将原单体文件拆分为模块化设计（`bundleloader`, `compositor`, `tools` 等），提升代码可维护性。
- **性能优化**：优化 UI 响应与数据处理流程，消除原项目中不必要的全量 UI 重建。
- **功能增强**：新增多角色管理、批量目录扫描、路径记忆、层级结构树（TreeView）、多语言支持及缓存复用等。

---

## 打包为 EXE

项目提供了打包脚本，使用 [PyInstaller](https://pyinstaller.org/) 将程序封装为 Windows 可执行文件。

### 前置条件

```bash
pip install pyinstaller
```

### 打包脚本

打包脚本位于 `scripts/` 目录下：

```bash
python scripts\build_exe.py --help
```

### 命令行参数

| 参数 | 说明 |
|------|------|
| `--onefile` | 打包为单个 exe（启动较慢，适合分发） |
| `--name <名称>` | 自定义输出文件名（默认: `SpriteTool`） |
| `--icon <路径>` | 自定义图标（.ico 格式） |
| _(自动清理)_ | 打包前自动清除 `dist/` 和 `build/`（需确认） |
| `-h`, `--help` | 显示帮助信息 |

### 使用示例

```bash
# 默认打包（onedir 模式，启动快）
python scripts\build_exe.py

# 打包为单个 exe（onefile 模式）
python scripts\build_exe.py --onefile

# 自定义名称和图标
python scripts\build_exe.py --name MyApp --icon icon.ico
```

### 打包模式说明

| 模式 | 启动速度 | 输出结构 |
|------|----------|----------|
| `--onedir`（默认） | **快**（无需解压） | `dist\名称\名称.exe` + `_internal\` 文件夹 |
| `--onefile` | 较慢（每次运行需解压） | `dist\名称.exe`（单个文件） |

### 注意事项

- **图标文件**需为 `.ico` 格式。可用 `Pillow` 从 PNG 转换：
  ```bash
  python -c "from PIL import Image; Image.open('icon.png').save('icon.ico', format='ICO', sizes=[(256,256)])"
  ```
- **UnityPy** 等依赖通过 `--collect-all` 确保完整打包，避免运行时报 `ModuleNotFoundError`。

### 常见问题

| 问题 | 解决方案 |
|------|----------|
| 启动时提示 `No module named 'UnityPy.resources'` | 使用 `--collect-all UnityPy` 重新打包（脚本已内置） |
| 启动时提示 `fmod.dll` 或 `archspec` 相关错误 | 使用 `--collect-all fmod_toolkit` / `--collect-all archspec`（脚本已内置） |
| `output/` 或 `temp/` 目录出现在临时文件夹中 | 已修复：打包后路径自动定位到 exe 所在目录 |

## .gitignore

项目已配置 `.gitignore`，自动过滤以下目录和文件：

| 规则 | 说明 |
|------|------|
| `dist/`, `build/` | PyInstaller 构建输出 |
| `*.spec` | PyInstaller 配置文件 |
| `output/`, `temp/` | 应用运行时生成的目录 |
| `*.log` | 日志文件 |
| `__pycache__/`, `*.py[cod]` | Python 缓存 |
| `venv/`, `.venv/`, `.env` | 虚拟环境和环境变量 |
| `.vscode/`, `.idea/` | 编辑器配置 |
| `.*_config.json` | 用户路径记忆配置 |

### 许可证

本项目采用 **GPL-3.0 许可证**，详见 [LICENSE](LICENSE) 文件。

---

**免责声明**：本工具仅供学习和个人研究使用。使用本工具提取的内容，其版权归原游戏开发者所有。