# Manosaba-character-extracter

[![English](https://img.shields.io/badge/English-README-blue)](/docs/README.en.md) 
[![中文(简体)](https://img.shields.io/badge/中文(简体)-README-red)](/README.md)

从游戏「魔法少女的魔女审判」(manosaba) 的 Unity bundle 中提取角色精灵：自动检测组件数据、直接导出精灵或拼接完整立绘，还可按游戏原版排版合成角色名片，并支持分类浏览导出背景与各类小素材。界面为 **Electron 无边框窗口**，核心逻辑由 **Python 后端**（子进程 + stdio JSON-RPC）承担。

## 相关项目
>- **[Manosaba-Library](https://github.com/QwQSakuya/Manosaba-Library)** —— 同为《魔法少女的魔女审判》社区的项目，是一个玩家自发的非官方资料站，收录剧情节点图谱、证物图鉴、CG画廊、语音音乐与全素材库索引，并支持在线立绘预览。

## 功能

**提取与合成**

- **智能检测** — 自动识别组件数据：无组件可预览/直接导出，有组件可导出或拼接
- **角色立绘拼接** — 按部件位置、深度与剪切蒙版合成完整立绘，支持分类、缩略图；Normal / Multiply / Screen / Overlay / Softlight 五种混合模式还原原作效果
- **精灵预览** — 无组件角色一键预览全部精灵，勾选导出
- **部件管理** — 搜索、自然排序、分组折叠、一键全选、快速勾选 ClippingMask 部件、点击复制名称
- **层级结构** — 组件树查看，每行带复制按钮
- **Anan 素描本** — 选中 anan 素描本部件时可自定义文字（多行、字号、对齐方式）
- **加载可取消** — 角色分析进行中可随时取消，立即恢复可操作状态

**背景与小素材导出**

- 独立「素材提取」页自动定位游戏素材，支持场景背景、CG、证物、人物资料、界面图标与按钮，以及演出包中的全部图片分类浏览、搜索和勾选
- 点击素材行预览，勾选框独立选择导出；支持一键预热全部、有限内存缓存、temp 磁盘缩略图缓存和取消
- 原始尺寸 PNG 按分类平铺在 `output/backgrounds/背景/`、`证物/`、`人物资料/`、`界面素材/`、`演出物件/` 等文件夹内；不创建素材包子文件夹，同名文件自动编号
- 图集 Sprite 单独列出，保留未被 Sprite 引用的独立纹理，避免重复导出整张图集；详细分类和缓存行为见 [素材提取说明](docs/backgrounds.md)

**部件组合预设**

- 内置全部主要角色的 **Default 预设**，下拉即可一键恢复勾选（随程序打包分发，缺失/损坏会自动修复）
- 也可保存自己的组合，支持以 **JSON 文件 / 代码**导入导出；内置预设受保护，不可覆盖或删除

**名片合成**

- 首页输入姓名即可按游戏原版排版渲染名片 PNG（601×289，字号层级与位置参数均解析自游戏 UI bundle；名字过长自动加宽画布、不缩字号）
- 字体固定为 TsukushiMincho / SourceHanSerifSC 两种；输出至 `output/nameplate/`
- 首次使用「一键提取素材」自动从游戏目录定位并提取底板与字体（查找可随时中止，也可手动选择 bundle）

**预览与查看**

- **实时预览** — 滚轮缩放（以鼠标为中心）、拖动平移
- **放大查看器** — 合成图 / 单个部件 / 精灵均可放大细看，可直接从放大视图导出
- **预览画质 / 导出原画** — 预览以低分辨率合成减轻负载（100 / 75 / 50 / 25 四档）；导出默认保持原始画质，可切换为与预览一致

**界面与体验**

- **拖拽导入** — 将游戏目录或 bundle 文件拖入窗口即可加载，自动记忆上次使用的游戏目录
- **多语言 / 主题** — 简体中文 / English / 日本語 / 魔女语，深浅色主题 + 17 种角色主题色可切换并持久化
- **低配 GPU 优化** — 可禁用硬件加速（软件渲染）与界面动画，提升低端设备流畅度
- **任务栏效果** — 读条期间显示进度，完成后任务栏闪烁提示
- **日志文件 / 控制台** — 控制台日志同步写入 `logs/`，可一键清理；另有独立的日志控制台窗口（按级别过滤、多行归并、导出保存）

**数据与维护**

- **缓存复用** — 已提取数据缓存到 `temp/`，重复加载无需重新解包
- **内存回收** — 即时释放资源并触发 GC，退出前强制回收
- **调试模式** — 实时监视内存/CPU/窗口分辨率（仅本次运行）
- **累计导出 / 关于页 / 自动更新检查 / 免责声明**（第三方非官方工具）

## 环境要求

- **Python 3.10+**：`pip install -r requirements.txt`
- **Node.js 18+**：`cd electron && npm install`

> 目前主要针对 **Windows** 充分测试，Linux/macOS 兼容性未知。

## 最低配置要求

| 项目 | 最低要求 | 推荐 |
|---|---|---|
| 操作系统 | Windows 10 1809（64 位） | Windows 10 / 11（64 位） |
| CPU | 双核 1.6 GHz（x64） | 四核及以上 |
| 内存 | 1 GB | 2 GB 及以上 |
| 显卡 | 支持 DirectX 11 / WebGL（核显可） | 独立显卡，显存 1 GB+ |
| 硬盘 | 约 500 MB 可用空间 | 1 GB 及以上 |

> - 打包版（绿色版 / 安装版）已内置 Python 后端与 Electron 运行时，**无需**安装 Python / Node.js，开箱即用。
> - 合成角色立绘会创建较大图像画布（不小于 2000×4000，并按部件实际跨度自动扩展），内存偏小或核显设备建议开启 **禁用硬件加速** 与 **禁用界面动画** 以提升流畅度。
> - 低端设备可降低 **预览画质**（100 / 75 / 50 / 25 四档）减轻负载；导出仍默认保持原始画质。

## 使用

### 运行（推荐：启动脚本）

Windows 下直接使用仓库根目录的 `start.bat` 启动脚本：

```bat
start.bat                  :: Electron 无边框窗口（默认，原生 Aero Snap / 拖动 / 双击最大化 / 边缘缩放）
start.bat help             :: 显示帮助
start.bat clean [目标...]  :: 清理临时文件与构建缓存（见下方「清理开发缓存」）
```

**首次运行前需安装依赖**：

```bash
pip install -r requirements.txt        # Python 依赖
cd electron && npm install             # Electron 依赖
```

> 也可手动启动：`cd electron && npm start`
>
> `electron/.npmrc` 已把 Electron 二进制下载镜像指向 `npmmirror`（与 `electron-builder.yml` 的 `electronDownload.mirror` 一致），安装时无需访问 github.com，可避免国内网络下的下载 404 / TLS 证书校验失败。npm 11 会提示 `Unknown project config "electron_mirror"`，属正常无害提醒；如需换源，设置环境变量 `npm_config_electron_mirror` 即可覆盖。

### 清理开发缓存（`start.bat clean`）

开发过程中产生的临时文件与构建缓存可按目标分开清理：

```bat
start.bat clean                  :: 默认：temp + logs + build + pycache（不含 dist）
start.bat clean temp             :: 只清提取缓存 temp/
start.bat clean logs             :: 只清日志 logs/*.log（该目录下其它文件保留）
start.bat clean build            :: 只清 PyInstaller 构建缓存 build/
start.bat clean pycache          :: 只清 __pycache__ / .pytest_cache
start.bat clean dist             :: 只清打包产物 dist/
start.bat clean all              :: 以上全部
start.bat clean temp logs build  :: 目标可空格组合
```

- 目标名大小写不敏感，未知目标会给出提示并列出用法。
- **不碰用户数据**：`data/`（设置与预设）、`output/`（导出结果）、`builtin/`（内置预设）、`electron/node_modules`。
- `__pycache__` 只扫描仓库自身的 `src/`、`scripts/`、`builtin/`、`i18n/` 与根目录，不会进入 `.venv`、`node_modules`。


### 使用步骤

1. 点击左侧角色 → 程序自动检测：
   - **无组件数据** → 预览精灵 / 直接导出全部 / 取消
   - **有组件数据** → 直接导出 / 拼接角色图像
2. 拼接模式：勾选部件（或从预设栏选择内置 / 自定义组合）→ 实时预览 → 保存合成 PNG
3. 名片：首页名片卡片输入姓名、选字体与首字颜色 → 生成预览 → 保存（首次需「一键提取素材」）
4. 素材：切换到「素材提取」→「加载素材目录」选择游戏根目录或 `backgrounds` 目录 → 选择分类并勾选素材 →「导出所选」。点击素材行即可预览，勾选框只控制导出选择；「预热全部」为所有已加载素材生成可取消、可复用的缩略图缓存。默认显示场景背景，小素材从分类下拉切换；「全选当前列表」只选择搜索/分类后可见的素材，已选素材跨分类保留，「取消全选」清除全部选择。

预览缩放到最长边 1280 像素，导出始终保留原始尺寸，不受角色画质设置影响。背景包预览首张图片并导出包内全部图片，小素材逐张预览和导出。切换到素材页后，也可将游戏目录拖入窗口加载。加载、预览、预热和导出均可取消；已完成的 PNG 和缓存会保留，失败项会单独列出。

### 设置

可配置：**输出目录**（自动记忆）、**语言**、**主题与主题色**、**显示原始文件名**、**自动查找 characters 目录**（关闭后需手动指定直接包含角色 bundle 的文件夹）、**防剧透警告**、**预览画质**（100 / 75 / 50 / 25 四档，降低预览合成分辨率以减轻负载）、**导出原始画质**（关闭后导出与预览一致）、**禁用硬件加速**（软件渲染，需重启生效）、**禁用界面动画**（低配提速，立即生效）、**显示更新内容**（默认开启，检查更新时在弹窗中展示该版本的 Release 更新说明，可在更新弹窗内关闭）、**调试模式**、**检查更新**、**清理**（`temp/` 缓存、`output/` 目录或 `logs/` 日志）。

> 设置保存在程序目录 `data/settings.json`（已设隐藏属性）。

### 数据存储路径（打包版）

打包安装后，程序在**安装目录**下读写以下数据（以 `D:\mce` 为例）：

| 路径 | 用途 |
|---|---|
| `D:\mce\data` | 设置文件 `settings.json` + 部件组合预设 `presets\` |
| `D:\mce\output` | 导出精灵 / 合成立绘 / 名片 PNG |
| `D:\mce\temp` | 提取缓存（可清理） |
| `D:\mce\logs` | 运行日志（可一键清理，跟随数据目录） |

> 数据（`data`/`output`/`temp`/`logs`）始终**优先存放在程序所在目录**（安装目录或绿色版解压目录），仅当该目录不可写（如授权失败、杀毒软件拦截、只读盘）时才回退到 `%APPDATA%\Manosaba Character Extracter` 作为兜底。
>
> 名片素材与字体的提取结果存放在**程序资源目录** `resources\webui\assets\nameplate`（与 `assets\fonts`），
> 仅当 `webui` 目录实测不可写时才回退到 `data\nameplate`。
>
> 默认安装到 `C:\Program Files\MCE` 时，安装程序已为普通用户授予该目录的写入与删除权限，因此数据仍直接生成在安装目录下。
>
> **覆盖安装 / 升级不会碰这些数据**（对齐 Inno Setup 的行为）：安装器在安装前会把 `data`/`output`/`temp`/`logs` 原样搬到安装目录同级的 `MCE-update-backup`，装完再搬回去（Rename，不复制数据）；卸载器也只删除自己写入的程序文件（`MCE.exe`、`resources`、`locales` 等白名单），安装目录里用户自己放的文件不会被删。
> 卸载时若检测到安装目录下存在数据（静默卸载除外），会弹窗询问是否一并删除：选「是」一并删除、选「否」只卸载程序保留数据、选「取消」中止卸载。

### 输出与缓存结构

```
output/
├── <角色名>/            # 无组件：精灵直接平铺
├── <角色名>/sprites/    # 有组件：导出的精灵
├── <角色名>/composite/  # 有组件：合成图（<角色名>_composite.png，重名自动加序号）
├── backgrounds/背景/  # 原有背景、CG 和演出包 PNG
├── backgrounds/<分类>/ # 证物、人物资料、界面素材、演出物件等 PNG，每类平铺
└── nameplate/           # 名片 PNG（按姓名命名，重名自动加序号）
temp/
└── <角色名>/            # 提取缓存：sprites/ + character_data.json + mask_mapping.json
data/presets/            # 部件组合预设（内置镜像 + 用户自建，清缓存不丢失）
```

## 架构

**启动链路**

- 开发态：`start.bat` → `electron/main.js` → `spawn(backend.py)` → `run.JsApi`
- 打包态：`MCE.exe` → `resources/backend/backend.exe`（PyInstaller 打包的同一后端）

**职责边界**

- **Electron 主进程**拥有全部系统原生 UI：无边框窗口控制（原生 Aero Snap / 拖动 / 双击最大化 / 边缘缩放）、目录与文件选择对话框、任务栏进度、日志控制台窗口。前端通过 `window.pywebview.api`（业务方法）与 `window.__electron`（窗口/对话框/日志控制台等原生能力）两条桥接调用。
- **Python 后端**只做业务逻辑与图像处理，不依赖任何 GUI 框架；`run.py` 无独立启动入口，唯一进程入口是 `backend.py`。

**通信协议**（stdin/stdout 单行 JSON）

- 请求 `{"id":N,"method":"...","args":[...]}` → 响应 `{"id":N,"result":...}` / `{"id":N,"error":"..."}`
- 事件 `{"event":"name","payload":{...}}`（进度、预览图、更新结果等）
- stdout 专供协议，日志一律走 stderr 并写入 `logs/`

**提取 worker 子进程**

UnityPy 提取在 `backend.py --worker` 独立子进程中执行（避免后端主进程偶发卡死）：支持随时取消（终止子进程），无输出 45 秒或总耗时 600 秒判定超时并自动重试一次。

**环境变量（开发 / 调试用）**

- `MCE_PYTHON` — 覆盖后端 Python 解释器（`start.bat` 与 `main.js` 均优先读取）
- `MCE_DATA_DIR` — 重定向全部数据目录（`data`/`output`/`temp`/`logs`）；打包态由 Electron 自动设置

## 项目结构

```
├── start.bat          # Windows 启动脚本（启动应用 / 清理临时文件与构建缓存）
├── run.py             # 业务逻辑层（JsApi：合成/预览/设置/提取/名片/更新检查；无任何 GUI 依赖）
├── backend.py         # stdio JSON-RPC 后端进程（唯一入口，复用 run.py 的 JsApi）
├── electron/          # Electron 界面壳
│   ├── main.js        #   主进程：无边框窗口 + 窗口控制 + 原生对话框 + Python 子进程桥接
│   ├── preload.js     #   桥接层：window.pywebview.api / __pywebview.events / __electron
│   ├── nsis/          #   安装器自定义脚本（升级数据保护 / 白名单卸载）
│   └── package.json
├── webui/             # 前端（index.html + css/ + js/，纯本地无 CDN；console/ 为日志控制台窗口）
├── src/               # 核心模块（bundle 加载、合成、导出、缓存、预设、名片、i18n、设置、更新检查等）
├── i18n/              # 语言包（YAML：common 通用 + games/<游戏>，4 语言键集合一致）
├── builtin/           # 内置部件组合预设（随包分发，只读）
├── scripts/           # PyInstaller 打包脚本
├── docs/              # 英文 README 等
├── output/            # 输出目录（程序生成）
└── temp/              # 提取缓存（程序生成）
```

技术栈：[UnityPy](https://github.com/K0lb3/UnityPy)（bundle 解析）、Pillow（图像处理）、[Electron](https://www.electronjs.org/)（无边框 UI 壳，Chromium 渲染 + 原生 Aero Snap）。Python 侧运行时依赖仅这 3 个，窗口聚焦等系统能力由 ctypes 标准库实现。

## 致谢与许可证

### 原作信息

本工具提取的内容来源于游戏 **「魔法少女ノ魔女裁判」(Manosaba)**
© 2024 **Re,AER LLC. / Acacia** — 原游戏所有权利归其所有。

### 本工具作者

**paliku520（云野 风云）** — 开发与维护

### 贡献者

**[Rainfrost2907](https://github.com/Rainfrost2907)** — 「素材提取」页（背景与小素材提取导出，详见 [docs/backgrounds.md](/docs/backgrounds.md)）

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

### Electron 应用
```bash
python scripts\build_electron_backend.py   # 仅打后端 → dist/backend/
python scripts\build_electron.py            # 一键：后端 + 绿色版 zip + 安装版 Setup.exe
```

- `build_electron.py` 可选参数：`--backend-only` / `--app-only` / `--zip-only` / `--installer-only` / `--no-clean` / `--clean-dist`
- 可选 `--company/--product/--description/--copyright` 透传给后端 exe 版本信息（默认用 `scripts/version_info.py` 顶部 `APP_*` 常量）
- 版本号自动取自 `src/version.py`（产物名 `MCE-Setup-<版本>.exe` / `MCE-<版本>-win.zip` 与后端 exe 版本信息均自动同步，改版本只改这一处）
- electron-builder 配置见 `electron/electron-builder.yml`（需先安装 electron 目录的 node_modules）
- 更多参数见 `--help`

> **素材版权说明**：名片底板与游戏字体为版权受限素材，**不进仓库、也不进发行包**
> （`electron-builder.yml` 已在 `extraResources` 中排除 `webui/assets/nameplate/` 与三个游戏字体）。
> 最终用户需在应用内「一键提取素材」自行提取；程序自带 UI 字体与其余页面资源照常打包。
