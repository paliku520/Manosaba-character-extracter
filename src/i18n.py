"""
国际化 / 本地化支持（i18n）

提供中英文切换功能，GUI 中所有用户可见字符串均通过 _() 函数获取。
"""

from __future__ import annotations

from typing import Dict


# ── 语言代码 ──────────────────────────────────────────────
LANG_CN = "zh_CN"       # 简体中文
LANG_EN = "en_US"       # 英语
LANG_MGL = "mgl_MG"     # 魔女语 (fiXmArge Language)


# ── 当前语言（默认简体中文） ──────────────────────────────
_current_lang: str = LANG_CN


def current_lang() -> str:
    return _current_lang


def set_lang(code: str) -> None:
    global _current_lang
    _current_lang = code


# ── 翻译表 ────────────────────────────────────────────────
# 每组的 key 为语义标识，三个语言各一个值

T: Dict[str, Dict[str, str]] = {
    # ── 窗口／全局 ──
    "app.title": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具",
        LANG_EN: "Manosaba - Character Sprite Tool",
        LANG_MGL: "Manosaba - eXi' Toim",
    },
    "app.status.ready": {
        LANG_CN: "就绪",
        LANG_EN: "Ready",
        LANG_MGL: "DArime",
    },
    "app.status.loading": {
        LANG_CN: "加载中...",
        LANG_EN: "Loading...",
        LANG_MGL: "Toim...",
    },
    "app.status.loaded": {
        LANG_CN: "已加载 {count} 个角色",
        LANG_EN: "Loaded {count} characters",
        LANG_MGL: "Loadeh {count} JIO",
    },
    "app.status.load_failed": {
        LANG_CN: "加载失败",
        LANG_EN: "Load failed",
        LANG_MGL: "Loadeh Baru",
    },
    "app.status.cancelled": {
        LANG_CN: "已取消",
        LANG_EN: "Cancelled",
        LANG_MGL: "Ca-nay",
    },
    "app.status.analyzing": {
        LANG_CN: "正在分析: {name} ...",
        LANG_EN: "Analyzing: {name} ...",
        LANG_MGL: "AnxAn: {name} ...",
    },
    "app.status.analyze_failed": {
        LANG_CN: "分析失败",
        LANG_EN: "Analysis failed",
        LANG_MGL: "AnxAn Baru",
    },
    "app.status.exporting": {
        LANG_CN: "正在导出 {name} 的精灵...",
        LANG_EN: "Exporting sprites for {name}...",
        LANG_MGL: "KeI·tion {name}...",
    },
    "app.status.export_done": {
        LANG_CN: "完成: {name} — 导出 {count} 个精灵",
        LANG_EN: "Done: {name} — {count} sprites exported",
        LANG_MGL: "FineNd: {name} — {count} KeI·tion",
    },
    "app.status.extracting": {
        LANG_CN: "正在提取 {name} 的角色数据...",
        LANG_EN: "Extracting character data for {name}...",
        LANG_MGL: "cOnzAI {name}...",
    },
    "app.status.extract_done": {
        LANG_CN: "已就绪: {name} — {count} 个部件",
        LANG_EN: "Ready: {name} — {count} parts",
        LANG_MGL: "DArime: {name} — {count} hA-k",
    },
    "app.status.compositing": {
        LANG_CN: "正在合成图像...",
        LANG_EN: "Compositing image...",
        LANG_MGL: "gDie MEif...",
    },
    "app.status.composite_done": {
        LANG_CN: "合成完成",
        LANG_EN: "Composite complete",
        LANG_MGL: "gDie FineNd",
    },
    "app.status.composite_failed": {
        LANG_CN: "合成失败",
        LANG_EN: "Composite failed",
        LANG_MGL: "gDie Baru",
    },
    "app.status.preview_cleared": {
        LANG_CN: "预览已清除",
        LANG_EN: "Preview cleared",
        LANG_MGL: "Lai Nei Ca-nay",
    },
    "app.progress.loading_bundles": {
        LANG_CN: "正在扫描并加载 bundle 文件...",
        LANG_EN: "Scanning and loading bundle files...",
        LANG_MGL: "Loadeh Ge-mon...",
    },

    # ── 左侧面板 ──
    "left.load_button": {
        LANG_CN: "加载游戏目录",
        LANG_EN: "Load Game Directory",
        LANG_MGL: "Loadeh Coa Tain",
    },
    "left.open_output": {
        LANG_CN: "打开输出文件夹",
        LANG_EN: "Open Output Folder",
        LANG_MGL: "Owk GE-mon",
    },
    "left.char_list_title": {
        LANG_CN: "角色列表",
        LANG_EN: "Character List",
        LANG_MGL: "JIO Lisuto",
    },
    "left.clear_cache": {
        LANG_CN: "清除缓存文件夹",
        LANG_EN: "Clear Cache",
        LANG_MGL: "Ca-nay temp Ge-mon",
    },
    "left.clear_cache_confirm_title": {
        LANG_CN: "清除缓存",
        LANG_EN: "Clear Cache",
        LANG_MGL: "Ca-nay temp",
    },
    "left.clear_cache_confirm_msg": {
        LANG_CN: "确定要清除所有临时缓存文件吗？\n\n下次加载角色时需要重新提取数据。",
        LANG_EN: "Clear all temporary cache files?\n\nNext character load will need to re-extract data.",
        LANG_MGL: "Ca-nay Alte temp Ge-mon?\n\nNext JIO Loadeh need neYO cOnzAI.",
    },
    "log.cache_loaded": {
        LANG_CN: "从缓存加载角色数据: {name} ({count} 个部件)",
        LANG_EN: "Loaded character data from cache: {name} ({count} parts)",
        LANG_MGL: "Loadeh JIO data from temp: {name} ({count} hA-k)",
    },

    # ── 部件选择页 ──
    "parts.select_all": {
        LANG_CN: "全选",
        LANG_EN: "Select All",
        LANG_MGL: "Alte",
    },
    "parts.deselect_all": {
        LANG_CN: "取消全选",
        LANG_EN: "Deselect All",
        LANG_MGL: "Alte Ca-nay",
    },
    "parts.selected_count": {
        LANG_CN: "已选择: {count} 个部件",
        LANG_EN: "Selected: {count} parts",
        LANG_MGL: "Alte: {count} hA-k",
    },
    "parts.save_composite": {
        LANG_CN: "保存合成图像",
        LANG_EN: "Save Composite",
        LANG_MGL: "Save gDie MEif",
    },
    "parts.clear_preview": {
        LANG_CN: "清空预览",
        LANG_EN: "Clear Preview",
        LANG_MGL: "Ca-nay Lai Nei",
    },
    "parts.composite_btn": {
        LANG_CN: "生成合成图像",
        LANG_EN: "Generate Composite",
        LANG_MGL: "gDie MEif",
    },
    "parts.auto_update": {
        LANG_CN: "自动更新",
        LANG_EN: "Auto Update",
        LANG_MGL: "Toim KaRause",
    },
    "parts.no_preview": {
        LANG_CN: "未生成预览",
        LANG_EN: "No preview",
        LANG_MGL: "Lai Nei Nii",
    },
    "parts.generating": {
        LANG_CN: "正在生成合成图像...",
        LANG_EN: "Generating composite image...",
        LANG_MGL: "gDie MEif...",
    },
    "parts.composite_done_fmt": {
        LANG_CN: "合成完成 ({w}x{h})",
        LANG_EN: "Composite done ({w}x{h})",
        LANG_MGL: "gDie FineNd ({w}x{h})",
    },
    "parts.no_selection_hint": {
        LANG_CN: "请至少选择一个部件",
        LANG_EN: "Please select at least one part",
        LANG_MGL: "Alte one hA-k",
    },
    "parts.selected_list_title": {
        LANG_CN: "已选精灵",
        LANG_EN: "Selected Sprites",
        LANG_MGL: "Alte KeI·tion",
    },
    "parts.no_img": {
        LANG_CN: "[无图]",
        LANG_EN: "[NoImg]",
        LANG_MGL: "[Nii]",
    },
    "parts.scale_hint": {
        LANG_CN: "预览已缩放 ({scale:.0%})，保存的为原始大小",
        LANG_EN: "Preview scaled ({scale:.0%}), saved at original size",
        LANG_MGL: "Lai Nei scaled ({scale:.0%}), Save Taven",
    },

    # ── 信息页 ──
    "info.tab_title": {
        LANG_CN: "信息",
        LANG_EN: "Info",
        LANG_MGL: "sinruits",
    },
    "info.char_list_header": {
        LANG_CN: "已加载 {count} 个角色:\n\n",
        LANG_EN: "Loaded {count} characters:\n\n",
        LANG_MGL: "Loadeh {count} JIO:\n\n",
    },
    "info.char_list_footer": {
        LANG_CN: "\n请在左侧列表中点击角色名称开始处理。",
        LANG_EN: "\nClick a character name in the left list to start.",
        LANG_MGL: "\nAlte JIO in left list.",
    },
    "info.welcome": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具\n\n",
        LANG_EN: "Manosaba - Character Sprite Tool\n\n",
        LANG_MGL: "Manosaba - eXi' Toim\n\n",
    },
    "info.usage_title": {
        LANG_CN: "使用说明:\n",
        LANG_EN: "Instructions:\n",
        LANG_MGL: "We-Ho:\n",
    },
    "info.usage_1": {
        LANG_CN: "1. 点击左侧「加载游戏目录」按钮，选择游戏安装目录\n",
        LANG_EN: "1. Click 'Load Game Directory' and select the game folder\n",
        LANG_MGL: "1. Alte 'Loadeh Coa Tain' Ga-mon\n",
    },
    "info.usage_2": {
        LANG_CN: "2. 程序自动扫描 characters 目录并加载所有角色\n",
        LANG_EN: "2. The tool scans the characters directory automatically\n",
        LANG_MGL: "2. Toim scans characters GE-mon oF Alte JIO\n",
    },
    "info.usage_3": {
        LANG_CN: "3. 在角色列表中点击要处理的角色\n",
        LANG_EN: "3. Click a character in the list to process\n",
        LANG_MGL: "3. Alte JIO in lisuto\n",
    },
    "info.usage_4": {
        LANG_CN: "4. 程序将自动检测 bundle 类型并执行相应操作\n\n",
        LANG_EN: "4. The tool detects bundle type and acts accordingly\n\n",
        LANG_MGL: "4. Toim oF KeI·tion\n\n",
    },
    "info.logic_title": {
        LANG_CN: "处理逻辑:\n",
        LANG_EN: "Processing Logic:\n",
        LANG_MGL: "KeI·tion sinruits:\n",
    },
    "info.logic_no_component": {
        LANG_CN: "• 无组件数据的 bundle → 直接导出所有精灵\n",
        LANG_EN: "• No component data → export all sprites directly\n",
        LANG_MGL: "• Nii component → KeI·tion Alte\n",
    },
    "info.logic_has_component": {
        LANG_CN: "• 有组件数据的 bundle → 询问处理方式:\n",
        LANG_EN: "• Has component data → ask user for mode:\n",
        LANG_MGL: "• Has component → ask:\n",
    },
    "info.logic_export": {
        LANG_CN: "   - 「直接导出所有精灵」导出原始精灵图片\n",
        LANG_EN: "   - 'Export All' → export raw sprite images\n",
        LANG_MGL: "   - 'KeI·tion Alte' → export raw sprites\n",
    },
    "info.logic_composite": {
        LANG_CN: "   - 「拼接角色图像」按位置和深度合成完整立绘\n\n",
        LANG_EN: "   - 'Composite' → assemble full character image\n\n",
        LANG_MGL: "   - 'gDie MEif' → assemble full JIO image\n\n",
    },
    "info.cache_warning": {
        LANG_CN: "注意： temp/ 目录为自动生成的缓存。切换角色时不会自动删除，点击左侧「清除缓存文件夹」按钮可手动释放空间。请勿存放个人文件！\n",
        LANG_EN: "Note: temp/ is an auto-generated cache folder. It is NOT automatically deleted when switching characters. Click 'Clear Cache' on the left to manually free up space. Do not store personal files here!\n",
        LANG_MGL: "hAquEi: temp/ is auto-cache Ge-mon. Nii auto Ca-nay when switching JIO. Alte left 'Ca-nay temp Ge-mon' to free space. Nii store personal Ge-mon!\n",
    },

    # ── 层级结构页 ──
    "hierarchy.tab_title": {
        LANG_CN: "组件结构",
        LANG_EN: "Hierarchy",
        LANG_MGL: "rEcanRey",
    },
    "hierarchy.hint": {
        LANG_CN: "组件层级结构（点击 + 展开/折叠）",
        LANG_EN: "Component hierarchy (click + to expand/collapse)",
        LANG_MGL: "rEcanRey oF hA-k (Alte + Owk / Ca-nay)",
    },
    "hierarchy.expand_all": {
        LANG_CN: "全部展开",
        LANG_EN: "Expand All",
        LANG_MGL: "Alte Owk",
    },
    "hierarchy.collapse_all": {
        LANG_CN: "全部折叠",
        LANG_EN: "Collapse All",
        LANG_MGL: "Alte Ca-nay",
    },
    "hierarchy.level_fmt": {
        LANG_CN: "层级 {level}:  {name}  —  [{count} 个子项]",
        LANG_EN: "Level {level}:  {name}  —  [{count} children]",
        LANG_MGL: "Level {level}: {name} — [{count} children]",
    },
    "hierarchy.item_sprite": {
        LANG_CN: "{name}  —  [位置: {pos}]  [排序: {order}]  [A: {alpha}]",
        LANG_EN: "{name}  —  [pos: {pos}]  [order: {order}]  [A: {alpha}]",
        LANG_MGL: "{name} — [pos: {pos}] [order: {order}] [A: {alpha}]",
    },
    "hierarchy.item_children": {
        LANG_CN: "{name}  —  [{count} 个子项]",
        LANG_EN: "{name}  —  [{count} children]",
        LANG_MGL: "{name} — [{count} children]",
    },
    "hierarchy.item_empty": {
        LANG_CN: "{name}  —  (位置: {pos})",
        LANG_EN: "{name}  —  (pos: {pos})",
        LANG_MGL: "{name} — (pos: {pos})",
    },
    "parts.json_hint": {
        LANG_CN: "组件的 RGBA 详细值可前往 character_data.json 中查看",
        LANG_EN: "Full RGBA values can be found in character_data.json",
        LANG_MGL: "RGBA oF hA-k iN character_data.json",
    },

    # ── 部件选择标签页标题 ──
    "tabs.parts": {
        LANG_CN: "部件选择",
        LANG_EN: "Part Selection",
        LANG_MGL: "hA-k Alte",
    },
    "tabs.hierarchy": {
        LANG_CN: "组件结构",
        LANG_EN: "Hierarchy",
        LANG_MGL: "rEcanRey",
    },

    # ── 对话框 ──
    "dialog.export_confirm_title": {
        LANG_CN: "确认导出",
        LANG_EN: "Confirm Export",
        LANG_MGL: "KeI·tion?",
    },
    "dialog.export_confirm_msg": {
        LANG_CN: "角色「{name}」的 bundle 不包含组件数据。\n\n将直接导出所有精灵文件到 output 目录。\n\n是否继续？",
        LANG_EN: "Character '{name}' bundle has no component data.\n\nAll sprites will be exported to the output directory.\n\nContinue?",
        LANG_MGL: "JIO '{name}' has Nii component.\n\nAlte KeI·tion to output.\n\nKaRause?",
    },
    "dialog.ask_mode_title": {
        LANG_CN: "处理方式 - {name}",
        LANG_EN: "Processing Mode - {name}",
        LANG_MGL: "KeI·tion Mode - {name}",
    },
    "dialog.ask_mode_msg": {
        LANG_CN: "该 bundle 包含组件数据，请选择处理方式:",
        LANG_EN: "This bundle has component data. Choose a mode:",
        LANG_MGL: "This has component. Alte mode:",
    },
    "dialog.ask_mode_export": {
        LANG_CN: "直接导出所有精灵文件",
        LANG_EN: "Export All Sprites",
        LANG_MGL: "KeI·tion Alte",
    },
    "dialog.ask_mode_export_hint": {
        LANG_CN: "将所有精灵图片保存到文件夹，不做任何拼接处理",
        LANG_EN: "Save all sprite images without compositing",
        LANG_MGL: "Save Alte sprites, Nii gDie",
    },
    "dialog.ask_mode_composite": {
        LANG_CN: "拼接角色图像",
        LANG_EN: "Composite Character",
        LANG_MGL: "gDie JIO",
    },
    "dialog.ask_mode_composite_hint": {
        LANG_CN: "按组件的位置和深度信息合成完整立绘",
        LANG_EN: "Assemble full character by position & depth",
        LANG_MGL: "gDie full JIO by pos & depth",
    },
    "dialog.export_complete_title": {
        LANG_CN: "导出完成",
        LANG_EN: "Export Complete",
        LANG_MGL: "KeI·tion FineNd",
    },
    "dialog.export_complete_msg": {
        LANG_CN: "角色「{name}」的 {count} 个精灵已导出到:\n{path}",
        LANG_EN: "Character '{name}' — {count} sprites exported to:\n{path}",
        LANG_MGL: "JIO '{name}' — {count} sprites KeI·tion to:\n{path}",
    },
    "dialog.warning_no_parts": {
        LANG_CN: "警告",
        LANG_EN: "Warning",
        LANG_MGL: "hAquEi",
    },
    "dialog.warning_no_parts_msg": {
        LANG_CN: "角色「{name}」未提取到有效的部件数据",
        LANG_EN: "No valid part data found for character '{name}'",
        LANG_MGL: "Nii valid part found for JIO '{name}'",
    },
    "dialog.composite_error_title": {
        LANG_CN: "合成错误",
        LANG_EN: "Composite Error",
        LANG_MGL: "gDie Baru",
    },
    "dialog.composite_error_msg": {
        LANG_CN: "图像合成失败:\n{msg}",
        LANG_EN: "Image compositing failed:\n{msg}",
        LANG_MGL: "gDie MEif Baru:\n{msg}",
    },
    "dialog.save_warning_title": {
        LANG_CN: "警告",
        LANG_EN: "Warning",
        LANG_MGL: "hAquEi",
    },
    "dialog.save_warning_msg": {
        LANG_CN: "请先生成合成图像",
        LANG_EN: "Please generate a composite image first",
        LANG_MGL: "gDie MEif first",
    },
    "dialog.save_success_title": {
        LANG_CN: "成功",
        LANG_EN: "Success",
        LANG_MGL: "gDie",
    },
    "dialog.save_success_msg": {
        LANG_CN: "图像已保存:\n{path}",
        LANG_EN: "Image saved:\n{path}",
        LANG_MGL: "MEif saved:\n{path}",
    },
    "dialog.save_error_title": {
        LANG_CN: "错误",
        LANG_EN: "Error",
        LANG_MGL: "Baru",
    },
    "dialog.save_error_msg": {
        LANG_CN: "保存失败: {msg}",
        LANG_EN: "Save failed: {msg}",
        LANG_MGL: "Save Baru: {msg}",
    },
    "dialog.analyze_error_title": {
        LANG_CN: "分析失败",
        LANG_EN: "Analysis Failed",
        LANG_MGL: "AnxAn Baru",
    },
    "dialog.analyze_error_msg": {
        LANG_CN: "分析角色「{name}」时出错:\n{msg}",
        LANG_EN: "Error analyzing character '{name}':\n{msg}",
        LANG_MGL: "AnxAn JIO '{name}' Baru:\n{msg}",
    },
    "dialog.process_error_msg": {
        LANG_CN: "处理数据时出错:\n{msg}",
        LANG_EN: "Error processing data:\n{msg}",
        LANG_MGL: "KeI·tion data Baru:\n{msg}",
    },
    "dialog.bundle_not_found": {
        LANG_CN: "路径不存在: {path}",
        LANG_EN: "Path not found: {path}",
        LANG_MGL: "Ge-mon not found: {path}",
    },
    "dialog.no_bundle_files": {
        LANG_CN: "未找到 bundle 文件: {path}",
        LANG_EN: "No bundle files found in: {path}",
        LANG_MGL: "Nii Ge-mon in: {path}",
    },
    "dialog.no_bundle_loaded": {
        LANG_CN: "没有成功加载任何 bundle",
        LANG_EN: "No bundles were loaded successfully",
        LANG_MGL: "Nii Ge-mon loaded",
    },
    "dialog.characters_not_found": {
        LANG_CN: "未找到 characters 目录: {path}",
        LANG_EN: "Characters directory not found: {path}",
        LANG_MGL: "JIO Ge-mon not found: {path}",
    },
    "dialog.user_cancelled": {
        LANG_CN: "用户取消",
        LANG_EN: "User cancelled",
        LANG_MGL: "User Ca-nay",
    },

    # ── 部件分类 ──
    "parts.category_header": {
        LANG_CN: "【{cat}】({count})",
        LANG_EN: "[{cat}] ({count})",
        LANG_MGL: "[{cat}] ({count})",
    },
    "parts.item_info": {
        LANG_CN: "{name:28s}  位置:({x:6.1f}, {y:6.1f})  排序:{order:3d}  A:{alpha:.2f}  大小:{size}",
        LANG_EN: "{name:28s}  pos:({x:6.1f}, {y:6.1f})  order:{order:3d}  A:{alpha:.2f}  size:{size}",
        LANG_MGL: "{name:28s} pos:({x:6.1f}, {y:6.1f}) order:{order:3d} A:{alpha:.2f} size:{size}",
    },

    # ── 预览 ──
    "parts.preview_failed": {
        LANG_CN: "预览失败: 图像尺寸无效",
        LANG_EN: "Preview failed: invalid image size",
        LANG_MGL: "Lai Nei Baru: invalid size",
    },

    # ── 进度默认文字 ──
    "app.progress.default": {
        LANG_CN: "处理中...",
        LANG_EN: "Processing...",
        LANG_MGL: "KeI·tion...",
    },

    # ── CLI ──
    "cli.description": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具",
        LANG_EN: "Manosaba - Character Sprite Tool",
        LANG_MGL: "Manosaba - eXi' Toim",
    },
    "cli.help.clean": {
        LANG_CN: "启动前清空输出文件夹",
        LANG_EN: "Clear the output folder before startup",
        LANG_MGL: "Ca-nay output before startup",
    },
    "cli.help.output": {
        LANG_CN: "指定输出目录（默认: 程序根目录下的 output 文件夹）",
        LANG_EN: "Specify output directory (default: output/ under the script folder)",
        LANG_MGL: "Set output Ge-mon (default: output/)",
    },
    "cli.help.clear_cache": {
        LANG_CN: "仅清除缓存文件夹后退出（不启动 GUI）",
        LANG_EN: "Clear cache folder and exit (without launching GUI)",
        LANG_MGL: "",
    },
    "cli.help.git_clean": {
        LANG_CN: "清除 output 和 temp 目录后退出（用于 git 提交前清理）",
        LANG_EN: "Remove output and temp directories and exit (for git commit cleanup)",
        LANG_MGL: "Ca-nay output & temp Ge-mon, then FineNd (for git commit cleanup)",
    },
    "dialog.load_error_title": {
        LANG_CN: "加载失败",
        LANG_EN: "Load Failed",
        LANG_MGL: "Loadeh Baru",
    },

    # ── 语言切换 ──
    "lang.label": {
        LANG_CN: "语言",
        LANG_EN: "Language",
        LANG_MGL: "Coword",
    },
    "lang.zh_CN": {
        LANG_CN: "简体中文",
        LANG_EN: "简体中文",
        LANG_MGL: "简体中文",
    },
    "lang.en_US": {
        LANG_CN: "English",
        LANG_EN: "English",
        LANG_MGL: "English",
    },
    "lang.mgl_MG": {
        LANG_CN: "fiXmArge",
        LANG_EN: "fiXmArge",
        LANG_MGL: "fiXmArge",
    },

    # ── 选择目录对话框 ──
    "dir.select_title": {
        LANG_CN: "选择游戏根目录或 characters 目录",
        LANG_EN: "Select game root or characters directory",
        LANG_MGL: "Alte game root or JIO Ge-mon",
    },

    # ── 文件保存对话框 ──
    "save.file_title": {
        LANG_CN: "保存合成图像",
        LANG_EN: "Save Composite Image",
        LANG_MGL: "Save gDie MEif",
    },
    "save.png_filter": {
        LANG_CN: "PNG 文件",
        LANG_EN: "PNG Files",
        LANG_MGL: "PNG Ge-mon",
    },

    # ── 日志消息 ──
    "log.saved_path_failed": {
        LANG_CN: "保存路径记忆失败: {e}",
        LANG_EN: "Failed to save path memory: {e}",
        LANG_MGL: "Save Ge-mon Baru: {e}",
    },
    "log.recursive_search": {
        LANG_CN: "常见路径未命中，开始递归搜索 characters 目录...",
        LANG_EN: "Common paths not found, searching recursively for characters dir...",
        LANG_MGL: "Common Ge-mon Nii, searching JIO Ge-mon...",
    },
    "log.found_common": {
        LANG_CN: "通过常见路径找到: {path}",
        LANG_EN: "Found via common path: {path}",
        LANG_MGL: "Found via common Ge-mon: {path}",
    },
    "log.found_sub": {
        LANG_CN: "通过常见路径子目录找到: {path}",
        LANG_EN: "Found via common path subdirectory: {path}",
        LANG_MGL: "Found via sub-Ge-mon: {path}",
    },
    "log.found_deep": {
        LANG_CN: "通过常见路径深层找到: {path}",
        LANG_EN: "Found via deep common path: {path}",
        LANG_MGL: "Found via deep Ge-mon: {path}",
    },
    "log.load_failed": {
        LANG_CN: "加载失败 {name}: {e}",
        LANG_EN: "Load failed: {name} ({e})",
        LANG_MGL: "Loadeh Baru: {name} ({e})",
    },
    "log.characters_dir_found": {
        LANG_CN: "找到 characters 目录: {path}",
        LANG_EN: "Characters directory found: {path}",
        LANG_MGL: "JIO Ge-mon found: {path}",
    },
    "log.bundle_files_found": {
        LANG_CN: "找到 {count} 个 bundle 文件",
        LANG_EN: "Found {count} bundle files",
        LANG_MGL: "Found {count} Ge-mon",
    },
    "log.loaded_char": {
        LANG_CN: "加载角色成功: {name}",
        LANG_EN: "Character loaded: {name}",
        LANG_MGL: "JIO Loadeh: {name}",
    },
    "log.skipped_char": {
        LANG_CN: "跳过角色: {name} (未找到精灵资源)",
        LANG_EN: "Skipped: {name} (no sprites found)",
        LANG_MGL: "Ca-nay: {name} (Nii sprites)",
    },
    "log.loaded_all": {
        LANG_CN: "成功加载 {count} 个角色",
        LANG_EN: "Successfully loaded {count} characters",
        LANG_MGL: "Loadeh {count} JIO",
    },
    "log.user_cancelled": {
        LANG_CN: "用户取消了选择",
        LANG_EN: "User cancelled selection",
        LANG_MGL: "User Ca-nay",
    },
    "log.component_detect_failed": {
        LANG_CN: "检测组件数据失败 {name}: {e}",
        LANG_EN: "Component data detection failed: {name} ({e})",
        LANG_MGL: "Component detect Baru: {name} ({e})",
    },
    "log.exported_sprite": {
        LANG_CN: "  导出精灵: {name}.png",
        LANG_EN: "  Exported sprite: {name}.png",
        LANG_MGL: "  KeI·tion: {name}.png",
    },
    "log.sprite_extract_failed": {
        LANG_CN: "  精灵提取失败 (path_id={id}): {e}",
        LANG_EN: "  Sprite extraction failed (path_id={id}): {e}",
        LANG_MGL: "  Sprite extract Baru (path_id={id}): {e}",
    },
    "log.export_done": {
        LANG_CN: "完成: 从 {file} 导出 {count} 个精灵 -> {dir}",
        LANG_EN: "Done: exported {count} sprites from {file} -> {dir}",
        LANG_MGL: "FineNd: {count} sprites from {file} -> {dir}",
    },
    "log.char_data_extracted": {
        LANG_CN: "角色数据已提取: {name} ({count} 个部件)",
        LANG_EN: "Character data extracted: {name} ({count} parts)",
        LANG_MGL: "JIO data extracted: {name} ({count} hA-k)",
    },
    "log.composite_failed_part": {
        LANG_CN: "  拼接失败 {name}: {e}",
        LANG_EN: "  Composite failed: {name} ({e})",
        LANG_MGL: "  gDie Baru: {name} ({e})",
    },
    "log.analyze_failed": {
        LANG_CN: "分析 bundle 失败 {name}: {e}",
        LANG_EN: "Bundle analysis failed: {name} ({e})",
        LANG_MGL: "AnxAn Baru: {name} ({e})",
    },
    "log.no_component_exporting": {
        LANG_CN: "{name}: 无组件数据，直接导出精灵",
        LANG_EN: "{name}: no component data, exporting sprites directly",
        LANG_MGL: "{name}: Nii component, KeI·tion sprites",
    },
    "log.component_detected": {
        LANG_CN: "{name}: 检测到组件数据",
        LANG_EN: "{name}: component data detected",
        LANG_MGL: "{name}: component found",
    },
    "log.parts_loaded": {
        LANG_CN: "{count} 个部件已加载，勾选后点击合成",
        LANG_EN: "{count} parts loaded, select and click composite",
        LANG_MGL: "{count} hA-k loaded, Alte and gDie",
    },
    "log.no_parts_selected": {
        LANG_CN: "没有选中任何部件，跳过合成",
        LANG_EN: "No parts selected, skipping composite",
        LANG_MGL: "Nii hA-k, Ca-nay gDie",
    },
    "log.compositing": {
        LANG_CN: "开始合成: {selected}/{total} 个部件",
        LANG_EN: "Compositing: {selected}/{total} parts",
        LANG_MGL: "gDie: {selected}/{total} hA-k",
    },
    "log.composite_failed": {
        LANG_CN: "合成失败: {e}",
        LANG_EN: "Composite failed: {e}",
        LANG_MGL: "gDie Baru: {e}",
    },
    "log.invalid_preview_size": {
        LANG_CN: "预览图像尺寸无效: {size}",
        LANG_EN: "Invalid preview image size: {size}",
        LANG_MGL: "Lai Nei size Baru: {size}",
    },
    "log.process_data_failed": {
        LANG_CN: "处理角色数据失败: {e}",
        LANG_EN: "Character data processing failed: {e}",
        LANG_MGL: "JIO data KeI·tion Baru: {e}",
    },
    "log.temp_cleared": {
        LANG_CN: "已清空临时缓存: {path}",
        LANG_EN: "Temp cache cleared: {path}",
        LANG_MGL: "Temp Ca-nay: {path}",
    },
    "log.output_cleared": {
        LANG_CN: "已清空输出目录: {path}",
        LANG_EN: "Output directory cleared: {path}",
        LANG_MGL: "Output Ge-mon Ca-nay: {path}",
    },
}


# ── 翻译函数 ──────────────────────────────────────────────

def _(key: str, **kwargs) -> str:
    """
    获取当前语言的翻译文本。

    Args:
        key: 翻译键
        **kwargs: 格式化参数，例如 _("app.status.loaded", count=5)

    Returns:
        翻译后的字符串，若 key 不存在则返回 key 本身
    """
    entry = T.get(key)
    if entry is None:
        return key
    text = entry.get(_current_lang, entry.get(LANG_CN, key))
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


# ── 语言列表（供 GUI 下拉框使用） ──────────────────────

def get_language_options() -> list[tuple[str, str]]:
    """返回 [(代码, 显示名), ...]"""
    return [
        (LANG_CN, _(f"lang.{LANG_CN}")),
        (LANG_EN, _(f"lang.{LANG_EN}")),
        (LANG_MGL, _(f"lang.{LANG_MGL}")),
    ]


LANGUAGE_CODES = [LANG_CN, LANG_EN, LANG_MGL]