"""
国际化 / 本地化支持（i18n）

提供中英文切换功能，GUI 中所有用户可见字符串均通过 _() 函数获取。
"""

from __future__ import annotations

from typing import Dict


# ── 语言代码 ──────────────────────────────────────────────
LANG_CN = "zh_CN"       # 简体中文
LANG_EN = "en_US"       # 英语
LANG_MGL = "mgl_MG"     # 魔女语 (fiXmArge Language)(架空语言)


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
    # 按前缀分组整理（about/app/char/console/dialog/hierarchy/info/lang/left/log/parts/preview/settings/tabs）
    # log.* 键的魔女语与英文一致（便于日志阅读）。

    # ── about.* ──
    "about.app_name": {
        LANG_CN: "魔裁立绘提取工具", 
        LANG_EN: "Manosaba Sprite Tool", 
        LANG_MGL: "Manosaba - eXi' Toim", 
    },
    "about.copyright": {
        LANG_CN: "非商业用途 · 仅供学习交流", 
        LANG_EN: "Non-commercial · For learning and sharing", 
        LANG_MGL: "Non-commercial · For learning", 
    },
    "about.description": {
        LANG_CN: "从《魔法少女的魔女审判》游戏文件中提取并合成角色立绘的桌面工具。", 
        LANG_EN: "A desktop tool to extract and composite character sprites from the Manosaba game files.", 
        LANG_MGL: "Toim to eXi' and gDie JIO MEif from Manosaba.", 
    },
    "about.dev_bilibili": {
        LANG_CN: "Bilibili", 
        LANG_EN: "Bilibili", 
        LANG_MGL: "Bilibili", 
    },
    "about.dev_click": {
        LANG_CN: "点击跳转", 
        LANG_EN: "Click to open", 
        LANG_MGL: "Alte to open", 
    },
    "about.dev_github": {
        LANG_CN: "GitHub", 
        LANG_EN: "GitHub", 
        LANG_MGL: "GitHub", 
    },
    "about.dev_name": {
        LANG_CN: "云野风云 (paliku520)", 
        LANG_EN: "Yunye Fengyun (paliku520)", 
        LANG_MGL: "Yunye Fengyun (paliku520)", 
    },
    "about.dev_title": {
        LANG_CN: "开发者", 
        LANG_EN: "Developer", 
        LANG_MGL: "KeI·tion", 
    },
    "about.export_count": {
        LANG_CN: "累计导出", 
        LANG_EN: "Total Exported", 
        LANG_MGL: "Alte KeI·tion", 
    },
    "about.license_note": {
        LANG_CN: "本工具提取的内容来源于游戏「魔法少女ノ魔女裁判」(Manosaba)\n© 2024 Re,AER LLC. / Acacia — 原游戏所有权利归其所有。", 
        LANG_EN: "The content extracted by this tool is from the game \"Magical Girl Witch Trials\" (Manosaba)\n© 2024 Re,AER LLC. / Acacia — All rights reserved by the original game developer.", 
        LANG_MGL: "Toim eXi' MEif from \"Mahou Shoujo no Majo Saiban\" (Manosaba)\n© 2024 Re,AER LLC. / Acacia — Alte oF Taven", 
    },
    "about.links_issues": {
        LANG_CN: "问题反馈", 
        LANG_EN: "Issues", 
        LANG_MGL: "AnxAn Baru", 
    },
    "about.links_repo": {
        LANG_CN: "源码仓库", 
        LANG_EN: "Source Code", 
        LANG_MGL: "Taven Ge-mon", 
    },
    "about.links_title": {
        LANG_CN: "项目链接", 
        LANG_EN: "Project Links", 
        LANG_MGL: "rEcanRey oF Ge-mon", 
    },
    "about.open_btn": {
        LANG_CN: "打开", 
        LANG_EN: "Open", 
        LANG_MGL: "Owk", 
    },
    "about.thanks_text": {
        LANG_CN: "感谢所有【共犯】的支持与反馈", 
        LANG_EN: "Thanks to all players for your support and feedback", 
        LANG_MGL: "gDie to Alte KyOhan for support and feedback", 
    },
    "about.thanks_title": {
        LANG_CN: "致谢", 
        LANG_EN: "Thanks", 
        LANG_MGL: "gDie", 
    },
    "about.update_btn": {
        LANG_CN: "检查更新", 
        LANG_EN: "Check for Updates", 
        LANG_MGL: "AnxAn Toim", 
    },
    "about.version_label": {
        LANG_CN: "版本 {version}", 
        LANG_EN: "Version {version}", 
        LANG_MGL: "Toim {version}", 
    },

    # ── app.* ──
    "app.disclaimer": {
        LANG_CN: "本工具为第三方非官方工具，与游戏官方无关。",
        LANG_EN: "This tool is a third-party unofficial tool and is not affiliated with the game official.",
        LANG_MGL: "This tool is third-party, Nii oF game official.",
    },
    "app.click_to_copy": {
        LANG_CN: "点击复制", 
        LANG_EN: "Click to copy", 
        LANG_MGL: "Alte to save", 
    },
    "app.copied": {
        LANG_CN: "已复制: {text}", 
        LANG_EN: "Copied: {text}", 
        LANG_MGL: "saved: {text}", 
    },
    "app.progress.loading_bundles": {
        LANG_CN: "正在扫描并加载 bundle 文件...", 
        LANG_EN: "Scanning and loading bundle files...", 
        LANG_MGL: "Loadeh Ge-mon...", 
    },
    "app.status.analyze_failed": {
        LANG_CN: "分析失败", 
        LANG_EN: "Analysis failed", 
        LANG_MGL: "AnxAn Baru", 
    },
    "app.status.analyzing": {
        LANG_CN: "正在分析: {name} ...", 
        LANG_EN: "Analyzing: {name} ...", 
        LANG_MGL: "AnxAn: {name} ...", 
    },
    "app.status.cancelled": {
        LANG_CN: "已取消", 
        LANG_EN: "Cancelled", 
        LANG_MGL: "Ca-nay", 
    },
    "app.status.checking_update": {
        LANG_CN: "正在检查更新...", 
        LANG_EN: "Checking for updates...", 
        LANG_MGL: "AnxAn Toim...", 
    },
    "app.status.composite_done": {
        LANG_CN: "合成完成", 
        LANG_EN: "Composite complete", 
        LANG_MGL: "gDie FineNd", 
    },
    "app.status.compositing": {
        LANG_CN: "正在合成图像...", 
        LANG_EN: "Compositing image...", 
        LANG_MGL: "gDie MEif...", 
    },
    "app.status.export_done": {
        LANG_CN: "完成: {name} — 导出 {count} 个精灵", 
        LANG_EN: "Done: {name} — {count} sprites exported", 
        LANG_MGL: "FineNd: {name} — {count} KeI·tion", 
    },
    "app.status.exporting": {
        LANG_CN: "正在导出 {name} 的精灵...", 
        LANG_EN: "Exporting sprites for {name}...", 
        LANG_MGL: "KeI·tion {name}...", 
    },
    "app.status.extract_done": {
        LANG_CN: "已就绪: {name} — {count} 个部件", 
        LANG_EN: "Ready: {name} — {count} parts", 
        LANG_MGL: "DArime: {name} — {count} hA-k", 
    },
    "app.status.extracting": {
        LANG_CN: "正在提取 {name} 的角色数据...", 
        LANG_EN: "Extracting character data for {name}...", 
        LANG_MGL: "cOnzAI {name}...", 
    },
    "app.status.load_failed": {
        LANG_CN: "加载失败", 
        LANG_EN: "Load failed", 
        LANG_MGL: "Loadeh Baru", 
    },
    "app.status.loaded": {
        LANG_CN: "已加载 {count} 个角色", 
        LANG_EN: "Loaded {count} characters", 
        LANG_MGL: "Loadeh {count} JIO", 
    },
    "app.status.ready": {
        LANG_CN: "就绪", 
        LANG_EN: "Ready", 
        LANG_MGL: "DArime", 
    },
    "app.status.settings_saved": {
        LANG_CN: "设置已保存: {path}", 
        LANG_EN: "Settings saved: {path}", 
        LANG_MGL: "Co-Jundic saved: {path}", 
    },
    "app.subtitle": {
        LANG_CN: "角色立绘提取工具", 
        LANG_EN: "Character Sprite Extracter", 
        LANG_MGL: "JIO eXi' Toim", 
    },
    "app.title": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具", 
        LANG_EN: "Manosaba - Character Sprite Tool", 
        LANG_MGL: "Manosaba - eXi' Toim", 
    },

    # ── char.* ──
    "char.alisa": {
        LANG_CN: "紫藤亚里沙", 
        LANG_EN: "Shito Alisa", 
        LANG_MGL: "Shito Alisa", 
    },
    "char.anan": {
        LANG_CN: "夏目安安", 
        LANG_EN: "Natsume An-An", 
        LANG_MGL: "Natsume An-An", 
    },
    "char.coco": {
        LANG_CN: "泽渡可可", 
        LANG_EN: "Sawatari Coco", 
        LANG_MGL: "Sawatari Coco", 
    },
    "char.creaturealisa": {
        LANG_CN: "亚里沙（魔女化）", 
        LANG_EN: "alisa(creature)", 
        LANG_MGL: "alisa(creature)", 
    },
    "char.creatureanan": {
        LANG_CN: "安安（魔女化）", 
        LANG_EN: "anan(creature)", 
        LANG_MGL: "anan(creature)", 
    },
    "char.creaturecoco": {
        LANG_CN: "可可（魔女化）", 
        LANG_EN: "coco(creature)", 
        LANG_MGL: "coco(creature)", 
    },
    "char.creatureema": {
        LANG_CN: "艾玛（魔女化）", 
        LANG_EN: "ema(creature)", 
        LANG_MGL: "ema(creature)", 
    },
    "char.creaturehanna": {
        LANG_CN: "汉娜（魔女化）", 
        LANG_EN: "hanna(creature)", 
        LANG_MGL: "hanna(creature)", 
    },
    "char.creaturehiro": {
        LANG_CN: "希罗（魔女化）", 
        LANG_EN: "hiro(creature)", 
        LANG_MGL: "hiro(creature)", 
    },
    "char.creatureleia": {
        LANG_CN: "蕾雅（魔女化）", 
        LANG_EN: "leia(creature)", 
        LANG_MGL: "leia(creature)", 
    },
    "char.creaturemargo": {
        LANG_CN: "玛格（魔女化）", 
        LANG_EN: "margo(creature)", 
        LANG_MGL: "margo(creature)", 
    },
    "char.creaturemeruru": {
        LANG_CN: "梅露露（魔女化）", 
        LANG_EN: "meruru(creature)", 
        LANG_MGL: "meruru(creature)", 
    },
    "char.creaturemiria": {
        LANG_CN: "米莉亚（魔女化）", 
        LANG_EN: "miria(creature)", 
        LANG_MGL: "miria(creature)", 
    },
    "char.creaturenanoka": {
        LANG_CN: "奈叶香（魔女化）", 
        LANG_EN: "nanoka(creature)", 
        LANG_MGL: "nanoka(creature)", 
    },
    "char.creaturenoah": {
        LANG_CN: "诺亚（魔女化）", 
        LANG_EN: "noah(creature)", 
        LANG_MGL: "noah(creature)", 
    },
    "char.creaturesherry": {
        LANG_CN: "雪莉（魔女化）", 
        LANG_EN: "sherry(creature)", 
        LANG_MGL: "sherry(creature)", 
    },
    "char.ema": {
        LANG_CN: "樱羽艾玛", 
        LANG_EN: "Sakuraba Ema", 
        LANG_MGL: "Sakuraba Ema", 
    },
    "char.hanna": {
        LANG_CN: "远野汉娜", 
        LANG_EN: "Tono Hanna", 
        LANG_MGL: "Tono Hanna", 
    },
    "char.hiro": {
        LANG_CN: "二阶堂希罗", 
        LANG_EN: "Nikaido Hiro", 
        LANG_MGL: "Nikaido Hiro", 
    },
    "char.jailer": {
        LANG_CN: "看守（黑部穗乃香）", 
        LANG_EN: "jailer(Kurobe Honoka)", 
        LANG_MGL: "jailer(Kurobe Honoka)", 
    },
    "char.jailerb": {
        LANG_CN: "希罗（残骸）", 
        LANG_EN: "jailerb(Hiro)", 
        LANG_MGL: "jailerb(Hiro)", 
    },
    "char.jailerc": {
        LANG_CN: "流浪的残骸", 
        LANG_EN: "jailerc", 
        LANG_MGL: "jailerc", 
    },
    "char.leia": {
        LANG_CN: "莲见蕾雅", 
        LANG_EN: "Hasumi Leia", 
        LANG_MGL: "Hasumi Leia", 
    },
    "char.margo": {
        LANG_CN: "宝生玛格", 
        LANG_EN: "Houshou Margo", 
        LANG_MGL: "Houshou Margo", 
    },
    "char.meruru": {
        LANG_CN: "冰上梅露露", 
        LANG_EN: "Hikami Meruru", 
        LANG_MGL: "Hikami Meruru", 
    },
    "char.miria": {
        LANG_CN: "佐伯米莉亚", 
        LANG_EN: "Saeki Miria", 
        LANG_MGL: "Saeki Miria", 
    },
    "char.nanoka": {
        LANG_CN: "黑部奈叶香", 
        LANG_EN: "Kurobe Nanoka", 
        LANG_MGL: "Kurobe Nanoka", 
    },
    "char.noah": {
        LANG_CN: "城崎诺亚", 
        LANG_EN: "Jogasaki Noah", 
        LANG_MGL: "Jogasaki Noah", 
    },
    "char.sherry": {
        LANG_CN: "橘雪莉", 
        LANG_EN: "Tachibana Sherry", 
        LANG_MGL: "Tachibana Sherry", 
    },
    "char.warden": {
        LANG_CN: "典狱长", 
        LANG_EN: "warden", 
        LANG_MGL: "warden", 
    },
    "char.yuki": {
        LANG_CN: "月代雪", 
        LANG_EN: "Tsukishiro Yuki", 
        LANG_MGL: "Tsukishiro Yuki", 
    },

    # ── console.* ──
    "console.exit_msg": {
        LANG_CN: "程序已退出。\n\n提示：控制台延迟关闭是正常现象（WebView2 清理子进程通常需 1-3 秒），请等待其自动消失。后台线程为 daemon 模式，不影响退出。\n\n警告：直接关闭控制台可能中断任务或引发异常。\n\n感谢使用「魔裁立绘提取工具」！", 
        LANG_EN: "Program exited.\n\nNote: Console closing delay is normal (WebView2 cleanup usually takes 1-3 seconds). Please wait for it to disappear automatically.\n\nWARNING: Closing this console directly may interrupt tasks or cause exceptions.\n\nThank you for using the Manosaba Sprite Tool!", 
        LANG_MGL: "Program exited.\n\nNote: Console closing delay is normal (WebView2 cleanup usually takes 1-3 seconds). Please wait for it to disappear automatically.\n\nWARNING: Closing this console directly may interrupt tasks or cause exceptions.\n\nThank you for using the Manosaba Sprite Tool!", 
    },
    "console.startup_msg": {
        LANG_CN: "欢迎使用「魔裁立绘提取工具」！\n本控制台用于显示运行日志。\n\n提示：请不要轻易关闭本控制台，否则程序会立即退出。\n如需退出程序，请点击主窗口右上角的关闭按钮。", 
        LANG_EN: "Welcome to the Manosaba Sprite Tool!\nThis console shows runtime logs.\n\nTip: Do not close this console casually, or the program will exit immediately.\nTo quit, click the close button on the top-right of the main window.", 
        LANG_MGL: "Welcome to the Manosaba Sprite Tool!\nThis console shows runtime logs.\n\nTip: Do not close this console casually, or the program will exit immediately.\nTo quit, click the close button on the top-right of the main window.", 
    },
    "console.title": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具 - 控制台", 
        LANG_EN: "Manosaba - Character Sprite Tool - console", 
        LANG_MGL: "Manosaba - eXi' Toim - console", 
    },

    # ── dialog.* ──
    "dialog.prerelease_title": {
        LANG_CN: "测试版提示",
        LANG_EN: "Pre-release Notice",
        LANG_MGL: "hAquEi: Toim oF now",
    },
    "dialog.prerelease_msg": {
        LANG_CN: "您正在使用测试版 v{version}，可能存在尚未修复的问题，请谨慎使用。",
        LANG_EN: "You are using a pre-release version v{version}. It may contain unfixed issues. Use with caution.",
        LANG_MGL: "Toim oF now v{version} may have Baru. Use with hAquEi.",
    },
    "dialog.spoiler_title": {
        LANG_CN: "剧透提示",
        LANG_EN: "Spoiler Notice",
        LANG_MGL: "hAquEi: sinruits",
    },
    "dialog.spoiler_msg": {
        LANG_CN: "本工具包含大量剧透内容，强烈建议您完成全周目（三周目完结）后再使用，以免破坏您的沉浸式体验。",
        LANG_EN: "This tool contains major spoilers. It is highly recommended to complete the main story before using it, so as not to ruin your immersive experience.",
        LANG_MGL: "Toim has Alte sinruits. Finish Manosaba first for gDie.",
    },
    "dialog.spoiler_continue": {
        LANG_CN: "继续",
        LANG_EN: "Continue",
        LANG_MGL: "KaRause",
    },
    "dialog.spoiler_quit": {
        LANG_CN: "退出",
        LANG_EN: "Quit",
        LANG_MGL: "FineNd",
    },
    "dialog.spoiler_never": {
        LANG_CN: "不再提示",
        LANG_EN: "Don't show again",
        LANG_MGL: "Nii hAquEi again",
    },
    "dialog.analyze_error_msg": {
        LANG_CN: "分析角色「{name}」时出错:\n{msg}", 
        LANG_EN: "Error analyzing character '{name}':\n{msg}", 
        LANG_MGL: "AnxAn JIO '{name}' Baru:\n{msg}", 
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
    "dialog.ask_mode_msg": {
        LANG_CN: "该 bundle 包含组件数据，请选择处理方式:", 
        LANG_EN: "This bundle has component data. Choose a mode:", 
        LANG_MGL: "This has component. Alte mode:", 
    },
    "dialog.ask_mode_title": {
        LANG_CN: "处理方式 - {name}", 
        LANG_EN: "Processing Mode - {name}", 
        LANG_MGL: "KeI·tion Mode - {name}", 
    },
    "dialog.bundle_not_found": {
        LANG_CN: "路径不存在: {path}", 
        LANG_EN: "Path not found: {path}", 
        LANG_MGL: "Ge-mon not found: {path}", 
    },
    "dialog.cancel": {
        LANG_CN: "取消", 
        LANG_EN: "Cancel", 
        LANG_MGL: "Ca-nay", 
    },
    "dialog.cancel_load_msg": {
        LANG_CN: "当前正在加载角色，是否中断？中断后将清理临时数据。", 
        LANG_EN: "A character is still loading. Interrupt it? Temporary data will be cleaned up.", 
        LANG_MGL: "JIO still Toim. Ca-nay? temp will be Ca-nay.", 
    },
    "dialog.cancel_load_title": {
        LANG_CN: "中断当前加载？", 
        LANG_EN: "Interrupt current loading?", 
        LANG_MGL: "Ca-nay Toim?", 
    },
    "dialog.characters_not_found": {
        LANG_CN: "未找到 characters 目录: {path}", 
        LANG_EN: "Characters directory not found: {path}", 
        LANG_MGL: "JIO Ge-mon not found: {path}", 
    },
    "dialog.close": {
        LANG_CN: "关闭", 
        LANG_EN: "Close", 
        LANG_MGL: "FineNd", 
    },
    "dialog.composite_error_msg": {
        LANG_CN: "图像合成失败:\n{msg}", 
        LANG_EN: "Image compositing failed:\n{msg}", 
        LANG_MGL: "gDie MEif Baru:\n{msg}", 
    },
    "dialog.export_complete_msg": {
        LANG_CN: "角色「{name}」的 {count} 个精灵已导出到:\n{path}", 
        LANG_EN: "Character '{name}' — {count} sprites exported to:\n{path}", 
        LANG_MGL: "JIO '{name}' — {count} sprites KeI·tion to:\n{path}", 
    },
    "dialog.export_complete_title": {
        LANG_CN: "导出完成", 
        LANG_EN: "Export Complete", 
        LANG_MGL: "KeI·tion FineNd", 
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
    "dialog.no_component_export": {
        LANG_CN: "直接导出全部", 
        LANG_EN: "Export All Directly", 
        LANG_MGL: "KeI·tion Alte", 
    },
    "dialog.no_component_export_hint": {
        LANG_CN: "不预览，将所有精灵直接导出到输出目录", 
        LANG_EN: "Export all sprites to the output directory without preview", 
        LANG_MGL: "KeI·tion Alte to output Ge-mon, Nii Lai Nei", 
    },
    "dialog.no_component_msg": {
        LANG_CN: "此角色不含组件数据，无法拼接立绘。请选择处理方式：", 
        LANG_EN: "This character has no component data and cannot be composited. Choose how to proceed:", 
        LANG_MGL: "JIO has Nii hA-k, Nii gDie. Alte We-Ho:", 
    },
    "dialog.no_component_preview": {
        LANG_CN: "预览精灵", 
        LANG_EN: "Preview Sprites", 
        LANG_MGL: "Lai Nei", 
    },
    "dialog.no_component_preview_hint": {
        LANG_CN: "在预览页查看所有精灵，可选中后再导出",
        LANG_EN: "View all sprites on the preview page, select then export",
        LANG_MGL: "View Alte sprites, Alte then KeI·tion",
    },
    "dialog.no_component_title": {
        LANG_CN: "选择处理方式 - {name}", 
        LANG_EN: "Choose how to process - {name}", 
        LANG_MGL: "Alte We-Ho - {name}", 
    },
    "dialog.ok": {
        LANG_CN: "确定", 
        LANG_EN: "OK", 
        LANG_MGL: "gDie", 
    },
    "dialog.open_output": {
        LANG_CN: "打开输出目录", 
        LANG_EN: "Open output folder", 
        LANG_MGL: "Owk output Ge-mon", 
    },
    "dialog.open_release": {
        LANG_CN: "前往下载", 
        LANG_EN: "Open release", 
        LANG_MGL: "Alte download", 
    },
    "dialog.process_error_msg": {
        LANG_CN: "处理数据时出错:\n{msg}", 
        LANG_EN: "Error processing data:\n{msg}", 
        LANG_MGL: "KeI·tion data Baru:\n{msg}", 
    },
    "dialog.save_error_msg": {
        LANG_CN: "保存失败: {msg}", 
        LANG_EN: "Save failed: {msg}", 
        LANG_MGL: "Save Baru: {msg}", 
    },
    "dialog.save_success_msg": {
        LANG_CN: "图像已保存:\n{path}", 
        LANG_EN: "Image saved:\n{path}", 
        LANG_MGL: "MEif saved:\n{path}", 
    },
    "dialog.save_success_title": {
        LANG_CN: "成功", 
        LANG_EN: "Success", 
        LANG_MGL: "gDie", 
    },
    "dialog.update_available_msg": {
        LANG_CN: "发现新版本 v{new}！\n当前版本: v{current}\n\n是否前往下载页面？", 
        LANG_EN: "New version v{new} is available!\nCurrent version: v{current}\n\nOpen the download page?", 
        LANG_MGL: "neYO Toim v{new}!\nToim oF now: v{current}\n\nAlte download Ge-mon?", 
    },
    "dialog.update_available_title": {
        LANG_CN: "发现新版本", 
        LANG_EN: "Update Available", 
        LANG_MGL: "neYO Toim", 
    },
    "dialog.update_check_error_msg": {
        LANG_CN: "检查更新时出错:\n{msg}", 
        LANG_EN: "Failed to check for updates:\n{msg}", 
        LANG_MGL: "AnxAn Toim Baru:\n{msg}", 
    },
    "dialog.update_latest_msg": {
        LANG_CN: "当前已是最新版本 v{current}", 
        LANG_EN: "You are running the latest version v{current}", 
        LANG_MGL: "Toim oF now v{current}", 
    },

    # ── hierarchy.* ──
    "hierarchy.collapse_all": {
        LANG_CN: "全部折叠", 
        LANG_EN: "Collapse All", 
        LANG_MGL: "Alte Ca-nay", 
    },
    "hierarchy.empty_hint": {
        LANG_CN: "暂无层级数据", 
        LANG_EN: "No hierarchy data", 
        LANG_MGL: "Nii rEcanRey", 
    },
    "hierarchy.expand_all": {
        LANG_CN: "全部展开", 
        LANG_EN: "Expand All", 
        LANG_MGL: "Alte Owk", 
    },
    "hierarchy.hint": {
        LANG_CN: "组件层级结构（点击 + 展开/折叠）", 
        LANG_EN: "Component hierarchy (click + to expand/collapse)", 
        LANG_MGL: "rEcanRey oF hA-k (Alte + Owk / Ca-nay)", 
    },

    # ── info.* ──
    "info.guide_step1": {
        LANG_CN: "点击「加载游戏目录」→ 选择您的游戏安装文件夹（如 .../manosaba_game）", 
        LANG_EN: "Click 'Load Game Directory' → choose your game folder (e.g. .../manosaba_game)", 
        LANG_MGL: "Alte 'Loadeh Coa Tain' → Alte game Ge-mon (e.g. .../manosaba_game)", 
    },
    "info.guide_step2": {
        LANG_CN: "左侧列表出现角色名 → 单击选中", 
        LANG_EN: "Character names appear on the left → click to select", 
        LANG_MGL: "JIO names on left → Alte to select", 
    },
    "info.guide_step3": {
        LANG_CN: "点击「拼接角色图像」→ 等待加载完成", 
        LANG_EN: "Click 'Composite Character Image' → wait for it to load", 
        LANG_MGL: "Alte 'gDie JIO' → wait for Toim", 
    },
    "info.guide_step4": {
        LANG_CN: "在「部件选择」面板勾选需要的部件（右侧实时预览）", 
        LANG_EN: "Check the parts you need in the 'Part Selection' panel (live preview on the right)", 
        LANG_MGL: "Alte hA-k in 'hA-k Alte' panel (Toim Lai Nei on right)", 
    },
    "info.guide_step5": {
        LANG_CN: "点击「保存合成图像」→ 立绘将导出至 output/ 目录", 
        LANG_EN: "Click 'Save Composite' → the image is exported to the output/ folder", 
        LANG_MGL: "Alte 'Save gDie MEif' → MEif KeI·tion to output/ Ge-mon", 
    },
    "info.guide_title": {
        LANG_CN: "快速上手：", 
        LANG_EN: "Quick Start:", 
        LANG_MGL: "Owk:", 
    },
    "info.tab_title": {
        LANG_CN: "首页", 
        LANG_EN: "Home", 
        LANG_MGL: "Taven", 
    },
    "info.tip1": {
        LANG_CN: "首次使用建议先加载游戏目录，让工具建立缓存（位于 temp/）", 
        LANG_EN: "Load the game directory first to build the cache (stored in temp/)", 
        LANG_MGL: "Loadeh Coa Tain first to build temp (in temp/)", 
    },
    "info.tip2": {
        LANG_CN: "切换角色时缓存会自动复用，速度更快", 
        LANG_EN: "Cache is reused automatically when switching characters, for faster speed", 
        LANG_MGL: "temp auto reused when switching JIO, for faster Toim", 
    },
    "info.tip3": {
        LANG_CN: "如需导出所有部件，可选择「导出所有精灵」", 
        LANG_EN: "To export all parts, choose 'Export All Sprites'", 
        LANG_MGL: "To KeI·tion Alte hA-k, Alte 'KeI·tion Alte'", 
    },
    "info.tips_title": {
        LANG_CN: "提示：", 
        LANG_EN: "Tips:", 
        LANG_MGL: "hAquEi:", 
    },
    "info.welcome_lead": {
        LANG_CN: "本工具帮助您从《魔法少女的魔女审判》游戏文件中快速提取并合成角色立绘。", 
        LANG_EN: "This tool helps you quickly extract and composite character sprites from the Manosaba game files.", 
        LANG_MGL: "Toim helps Alte eXi' and gDie JIO MEif from Manosaba.", 
    },
    "info.welcome_title": {
        LANG_CN: "欢迎使用 魔裁立绘提取工具 v{version}", 
        LANG_EN: "Welcome to Manosaba Sprite Tool v{version}", 
        LANG_MGL: "gDie to Manosaba - eXi' Toim v{version}", 
    },

    # ── lang.* ──
    "lang.en_US": {
        LANG_CN: "English", 
        LANG_EN: "English", 
        LANG_MGL: "English", 
    },
    "lang.label": {
        LANG_CN: "语言", 
        LANG_EN: "Language", 
        LANG_MGL: "Coword", 
    },
    "lang.mgl_MG": {
        LANG_CN: "fiXmArge", 
        LANG_EN: "fiXmArge", 
        LANG_MGL: "fiXmArge", 
    },
    "lang.zh_CN": {
        LANG_CN: "简体中文", 
        LANG_EN: "简体中文", 
        LANG_MGL: "简体中文", 
    },

    # ── left.* ──
    "left.char_list_title": {
        LANG_CN: "角色列表", 
        LANG_EN: "Character List", 
        LANG_MGL: "JIO Lisuto", 
    },
    "left.char_search": {
        LANG_CN: "搜索角色…", 
        LANG_EN: "Search characters…", 
        LANG_MGL: "AnxAn JIO…", 
    },
    "left.check_update": {
        LANG_CN: "检查更新", 
        LANG_EN: "Check for Updates", 
        LANG_MGL: "AnxAn Toim", 
    },
    "left.clear_cache": {
        LANG_CN: "清除缓存文件夹", 
        LANG_EN: "Clear Cache", 
        LANG_MGL: "Ca-nay temp Ge-mon", 
    },
    "left.clear_cache_confirm_msg": {
        LANG_CN: "确定要清除所有临时缓存文件吗？\n\n下次加载角色时需要重新提取数据。", 
        LANG_EN: "Clear all temporary cache files?\n\nNext character load will need to re-extract data.", 
        LANG_MGL: "Ca-nay Alte temp Ge-mon?\n\nNext JIO Loadeh need neYO cOnzAI.", 
    },
    "left.clear_cache_confirm_title": {
        LANG_CN: "清除缓存", 
        LANG_EN: "Clear Cache", 
        LANG_MGL: "Ca-nay temp", 
    },
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
    "left.settings": {
        LANG_CN: "设置", 
        LANG_EN: "Settings", 
        LANG_MGL: "Co-Jundic", 
    },

    # ── log.* ──
    "log.analyze_failed": {
        LANG_CN: "分析 bundle 失败 {name}: {e}", 
        LANG_EN: "Bundle analysis failed: {name} ({e})", 
        LANG_MGL: "Bundle analysis failed: {name} ({e})", 
    },
    "log.analyze_has": {
        LANG_CN: "分析 {name}: 有组件", 
        LANG_EN: "Analyze {name}: has components", 
        LANG_MGL: "Analyze {name}: has components", 
    },
    "log.analyze_none": {
        LANG_CN: "分析 {name}: 无组件", 
        LANG_EN: "Analyze {name}: no components", 
        LANG_MGL: "Analyze {name}: no components", 
    },
    "log.app_exited": {
        LANG_CN: "程序正在退出", 
        LANG_EN: "App exiting", 
        LANG_MGL: "App exiting", 
    },
    "log.app_started": {
        LANG_CN: "程序启动: v{version}", 
        LANG_EN: "App started: v{version}", 
        LANG_MGL: "App started: v{version}", 
    },
    "log.bundle_files_found": {
        LANG_CN: "找到 {count} 个 bundle 文件", 
        LANG_EN: "Found {count} bundle files", 
        LANG_MGL: "Found {count} bundle files", 
    },
    "log.cache_cleared": {
        LANG_CN: "已清空缓存", 
        LANG_EN: "Cache cleared", 
        LANG_MGL: "Cache cleared", 
    },
    "log.cache_loaded": {
        LANG_CN: "从缓存加载角色数据: {name} ({count} 个部件)", 
        LANG_EN: "Loaded character data from cache: {name} ({count} parts)", 
        LANG_MGL: "Loaded character data from cache: {name} ({count} parts)", 
    },
    "log.cache_saved": {
        LANG_CN: "缓存已保存: {name} -> {path}", 
        LANG_EN: "Cache saved: {name} -> {path}", 
        LANG_MGL: "Cache saved: {name} -> {path}", 
    },
    "log.char_data_extracted": {
        LANG_CN: "角色数据已提取: {name} ({count} 个部件)", 
        LANG_EN: "Character data extracted: {name} ({count} parts)", 
        LANG_MGL: "Character data extracted: {name} ({count} parts)", 
    },
    "log.char_load_cancelled": {
        LANG_CN: "角色加载/导出已中断", 
        LANG_EN: "Character loading/export cancelled", 
        LANG_MGL: "Character loading/export cancelled", 
    },
    "log.characters_dir_found": {
        LANG_CN: "找到 characters 目录: {path}", 
        LANG_EN: "Characters directory found: {path}", 
        LANG_MGL: "Characters directory found: {path}", 
    },
    "log.original_name_off": {
        LANG_CN: "已关闭原始文件名显示", 
        LANG_EN: "Original file names off", 
        LANG_MGL: "Original file names off", 
    },
    "log.original_name_on": {
        LANG_CN: "已开启原始文件名显示", 
        LANG_EN: "Original file names on", 
        LANG_MGL: "Original file names on", 
    },
    "log.component_detect_failed": {
        LANG_CN: "检测组件数据失败 {name}: {e}", 
        LANG_EN: "Component data detection failed: {name} ({e})", 
        LANG_MGL: "Component data detection failed: {name} ({e})", 
    },
    "log.composite_done": {
        LANG_CN: "合成完成: {size}", 
        LANG_EN: "Composite done: {size}", 
        LANG_MGL: "Composite done: {size}", 
    },
    "log.composite_failed": {
        LANG_CN: "合成失败: {e}", 
        LANG_EN: "Composite failed: {e}", 
        LANG_MGL: "Composite failed: {e}", 
    },
    "log.composite_failed_part": {
        LANG_CN: "  拼接失败 {name}: {e}", 
        LANG_EN: "  Composite failed: {name} ({e})", 
        LANG_MGL: "  Composite failed: {name} ({e})", 
    },
    "log.composite_saved": {
        LANG_CN: "已保存合成图: {path}", 
        LANG_EN: "Composite saved: {path}", 
        LANG_MGL: "Composite saved: {path}", 
    },
    "log.debug_off": {
        LANG_CN: "调试模式已关闭", 
        LANG_EN: "Debug mode off", 
        LANG_MGL: "Debug mode off", 
    },
    "log.debug_on": {
        LANG_CN: "调试模式已开启（监视内存/CPU/窗口）", 
        LANG_EN: "Debug mode on (monitoring mem/CPU/window)", 
        LANG_MGL: "Debug mode on (monitoring mem/CPU/window)", 
    },
    "log.export_complete": {
        LANG_CN: "导出完成: {name} {count} 个精灵", 
        LANG_EN: "Exported: {name} ({count} sprites)", 
        LANG_MGL: "Exported: {name} ({count} sprites)", 
    },
    "log.export_done": {
        LANG_CN: "完成: 从 {file} 导出 {count} 个精灵 -> {dir}", 
        LANG_EN: "Done: exported {count} sprites from {file} -> {dir}", 
        LANG_MGL: "Done: exported {count} sprites from {file} -> {dir}", 
    },
    "log.export_failed": {
        LANG_CN: "导出 {name} 失败: {e}", 
        LANG_EN: "Export failed: {name} ({e})", 
        LANG_MGL: "Export failed: {name} ({e})", 
    },
    "log.export_start": {
        LANG_CN: "开始导出 {name} 的精灵", 
        LANG_EN: "Exporting sprites for {name}", 
        LANG_MGL: "Exporting sprites for {name}", 
    },
    "log.exported_sprite": {
        LANG_CN: "  导出精灵: {name}.png", 
        LANG_EN: "  Exported sprite: {name}.png", 
        LANG_MGL: "  Exported sprite: {name}.png", 
    },
    "log.extract_cache_hit": {
        LANG_CN: "提取 {name}: 命中缓存", 
        LANG_EN: "Extract {name}: cache hit", 
        LANG_MGL: "Extract {name}: cache hit", 
    },
    "log.extract_complete": {
        LANG_CN: "提取完成: {name} {count} 个部件", 
        LANG_EN: "Extracted: {name} ({count} parts)", 
        LANG_MGL: "Extracted: {name} ({count} parts)", 
    },
    "log.found_common": {
        LANG_CN: "通过常见路径找到: {path}", 
        LANG_EN: "Found via common path: {path}", 
        LANG_MGL: "Found via common path: {path}", 
    },
    "log.found_deep": {
        LANG_CN: "通过常见路径深层找到: {path}", 
        LANG_EN: "Found via deep common path: {path}", 
        LANG_MGL: "Found via deep common path: {path}", 
    },
    "log.found_sub": {
        LANG_CN: "通过常见路径子目录找到: {path}", 
        LANG_EN: "Found via common path subdirectory: {path}", 
        LANG_MGL: "Found via common path subdirectory: {path}", 
    },
    "log.gc_before_exit": {
        LANG_CN: "程序退出前已内存回收（释放 {count} 个对象），当前占用 {mem} MB", 
        LANG_EN: "GC done before exit ({count} objects collected), memory {mem} MB", 
        LANG_MGL: "GC done before exit ({count} objects collected), memory {mem} MB", 
    },
    "log.invalid_preview_size": {
        LANG_CN: "预览图像尺寸无效: {size}", 
        LANG_EN: "Invalid preview image size: {size}", 
        LANG_MGL: "Invalid preview image size: {size}", 
    },
    "log.js_composite_saved": {
        LANG_CN: "已保存合成图: {path}", 
        LANG_EN: "Composite saved: {path}", 
        LANG_MGL: "Composite saved: {path}", 
    },
    "log.js_composite_start": {
        LANG_CN: "开始合成: {count} 个部件", 
        LANG_EN: "Compositing: {count} parts", 
        LANG_MGL: "Compositing: {count} parts", 
    },
    "log.js_export_done": {
        LANG_CN: "导出完成: {name} {count}", 
        LANG_EN: "Exported: {name} {count}", 
        LANG_MGL: "Exported: {name} {count}", 
    },
    "log.js_extract_done": {
        LANG_CN: "提取完成: {name} {count}", 
        LANG_EN: "Extracted: {name} {count}", 
        LANG_MGL: "Extracted: {name} {count}", 
    },
    "log.js_load_dir": {
        LANG_CN: "加载目录: {path}", 
        LANG_EN: "Loading directory: {path}", 
        LANG_MGL: "Loading directory: {path}", 
    },
    "log.js_select_char": {
        LANG_CN: "选择角色: {name}", 
        LANG_EN: "Select character: {name}", 
        LANG_MGL: "Select character: {name}", 
    },
    "log.js_selected": {
        LANG_CN: "已选择组件（{count}/{total}）", 
        LANG_EN: "Selected parts ({count}/{total})", 
        LANG_MGL: "Selected parts ({count}/{total})", 
    },
    "log.lang_changed": {
        LANG_CN: "语言已切换: {code}", 
        LANG_EN: "Language switched: {code}", 
        LANG_MGL: "Language switched: {code}", 
    },
    "log.lang_detected": {
        LANG_CN: "检测到系统语言: {code}", 
        LANG_EN: "System language detected: {code}", 
        LANG_MGL: "System language detected: {code}", 
    },
    "log.lang_from_settings": {
        LANG_CN: "从设置加载语言: {code}", 
        LANG_EN: "Language loaded from settings: {code}", 
        LANG_MGL: "Language loaded from settings: {code}", 
    },
    "log.load_cancelled_dir": {
        LANG_CN: "目录 {path} 的加载已取消", 
        LANG_EN: "Loading cancelled for: {path}", 
        LANG_MGL: "Loading cancelled for: {path}", 
    },
    "log.load_complete": {
        LANG_CN: "加载完成: {count} 个角色", 
        LANG_EN: "Loaded: {count} characters", 
        LANG_MGL: "Loaded: {count} characters", 
    },
    "log.load_error": {
        LANG_CN: "加载失败: {errors}", 
        LANG_EN: "Load failed: {errors}", 
        LANG_MGL: "Load failed: {errors}", 
    },
    "log.load_failed": {
        LANG_CN: "加载失败 {name}: {e}", 
        LANG_EN: "Load failed: {name} ({e})", 
        LANG_MGL: "Load failed: {name} ({e})", 
    },
    "log.loaded_all": {
        LANG_CN: "成功加载 {count} 个角色", 
        LANG_EN: "Successfully loaded {count} characters", 
        LANG_MGL: "Successfully loaded {count} characters", 
    },
    "log.loaded_char": {
        LANG_CN: "加载角色成功: {name}", 
        LANG_EN: "Character loaded: {name}", 
        LANG_MGL: "Character loaded: {name}", 
    },
    "log.loaded_sprite": {
        LANG_CN: "  加载精灵: {name}.png", 
        LANG_EN: "  Loaded sprite: {name}.png", 
        LANG_MGL: "  Loaded sprite: {name}.png", 
    },
    "log.loading_dir": {
        LANG_CN: "开始加载游戏目录: {path}", 
        LANG_EN: "Loading game directory: {path}", 
        LANG_MGL: "Loading game directory: {path}", 
    },
    "log.log_cleared": {
        LANG_CN: "已清理 {count} 个日志文件", 
        LANG_EN: "Cleared {count} log file(s)", 
        LANG_MGL: "Cleared {count} log file(s)", 
    },
    "log.logs_cleared": {
        LANG_CN: "已清理日志文件", 
        LANG_EN: "Log files cleared", 
        LANG_MGL: "Log files cleared", 
    },
    "log.output_cleared": {
        LANG_CN: "已清空输出目录: {path}", 
        LANG_EN: "Output directory cleared: {path}", 
        LANG_MGL: "Output directory cleared: {path}", 
    },
    "log.output_dir_cleared": {
        LANG_CN: "已清空输出目录", 
        LANG_EN: "Output directory cleared", 
        LANG_MGL: "Output directory cleared", 
    },
    "log.output_dir_set": {
        LANG_CN: "输出目录已设置: {path}", 
        LANG_EN: "Output directory set: {path}", 
        LANG_MGL: "Output directory set: {path}", 
    },
    "log.preview_cleaned": {
        LANG_CN: "已清理预览临时文件: {path}", 
        LANG_EN: "Preview temp files cleaned: {path}", 
        LANG_MGL: "Preview temp files cleaned: {path}", 
    },
    "log.preview_ready": {
        LANG_CN: "预览就绪: {name} — {count} 个精灵", 
        LANG_EN: "Preview ready: {name} — {count} sprites", 
        LANG_MGL: "Preview ready: {name} — {count} sprites", 
    },
    "log.process_data_failed": {
        LANG_CN: "处理角色数据失败: {e}", 
        LANG_EN: "Character data processing failed: {e}", 
        LANG_MGL: "Character data processing failed: {e}", 
    },
    "log.recursive_search": {
        LANG_CN: "常见路径未命中，开始递归搜索 characters 目录...", 
        LANG_EN: "Common paths not found, searching recursively for characters dir...", 
        LANG_MGL: "Common paths not found, searching recursively for characters dir...", 
    },
    "log.resource_title": {
        LANG_CN: " | 内存 {mem} MB | CPU {cpu}%{win}", 
        LANG_EN: " | mem {mem} MB | CPU {cpu}%{win}", 
        LANG_MGL: " | mem {mem} MB | CPU {cpu}%{win}", 
    },
    "log.resource_usage": {
        LANG_CN: "资源占用: 内存 {mem} MB | CPU {cpu}%{win}", 
        LANG_EN: "Resource usage: mem {mem} MB | CPU {cpu}%{win}", 
        LANG_MGL: "Resource usage: mem {mem} MB | CPU {cpu}%{win}", 
    },
    "log.resource_win": {
        LANG_CN: " | 窗口 {width}x{height}", 
        LANG_EN: " | window {width}x{height}", 
        LANG_MGL: " | window {width}x{height}", 
    },
    "log.saved_path_failed": {
        LANG_CN: "保存路径记忆失败: {e}", 
        LANG_EN: "Failed to save path memory: {e}", 
        LANG_MGL: "Failed to save path memory: {e}", 
    },
    "log.settings_save_failed": {
        LANG_CN: "保存设置失败: {e}", 
        LANG_EN: "Failed to save settings: {e}", 
        LANG_MGL: "Failed to save settings: {e}", 
    },
    "log.skipped_char": {
        LANG_CN: "跳过角色: {name} (未找到精灵资源)", 
        LANG_EN: "Skipped: {name} (no sprites found)", 
        LANG_MGL: "Skipped: {name} (no sprites found)", 
    },
    "log.sprite_extract_failed": {
        LANG_CN: "  精灵提取失败 (path_id={id}): {e}", 
        LANG_EN: "  Sprite extraction failed (path_id={id}): {e}", 
        LANG_MGL: "  Sprite extraction failed (path_id={id}): {e}", 
    },
    "log.temp_cleared": {
        LANG_CN: "已清空临时缓存: {path}", 
        LANG_EN: "Temp cache cleared: {path}", 
        LANG_MGL: "Temp cache cleared: {path}", 
    },
    "log.theme_changed": {
        LANG_CN: "主题已切换: {theme}", 
        LANG_EN: "Theme switched: {theme}", 
        LANG_MGL: "Theme switched: {theme}", 
    },

    # ── parts.* ──
    "parts.auto_update": {
        LANG_CN: "自动更新", 
        LANG_EN: "Auto Update", 
        LANG_MGL: "Toim KaRause", 
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
    "parts.deselect_all": {
        LANG_CN: "取消全选", 
        LANG_EN: "Deselect All", 
        LANG_MGL: "Alte Ca-nay", 
    },
    "parts.empty_hint": {
        LANG_CN: "请先在左侧选择一个角色进入拼接模式", 
        LANG_EN: "Select a character on the left to enter composite mode", 
        LANG_MGL: "Alte JIO on left for gDie mode", 
    },
    "parts.no_preview": {
        LANG_CN: "未生成预览", 
        LANG_EN: "No preview", 
        LANG_MGL: "Lai Nei Nii", 
    },
    "parts.no_selection_hint": {
        LANG_CN: "请至少选择一个部件", 
        LANG_EN: "Please select at least one part", 
        LANG_MGL: "Alte one hA-k", 
    },
    "parts.preview_title": {
        LANG_CN: "实时预览", 
        LANG_EN: "Live Preview", 
        LANG_MGL: "Toim Lai Nei", 
    },
    "parts.save_composite": {
        LANG_CN: "保存合成图像", 
        LANG_EN: "Save Composite", 
        LANG_MGL: "Save gDie MEif", 
    },
    "parts.search_hint": {
        LANG_CN: "搜索部件…", 
        LANG_EN: "Search parts…", 
        LANG_MGL: "AnxAn hA-k…", 
    },
    "parts.select_all": {
        LANG_CN: "全选", 
        LANG_EN: "Select All", 
        LANG_MGL: "Alte", 
    },
    "parts.selected_list_title": {
        LANG_CN: "已选精灵", 
        LANG_EN: "Selected Sprites", 
        LANG_MGL: "Alte KeI·tion", 
    },
    "parts.total": {
        LANG_CN: "个部件", 
        LANG_EN: "parts", 
        LANG_MGL: "hA-k", 
    },
    "parts.zoom": {
        LANG_CN: "缩放", 
        LANG_EN: "Zoom", 
        LANG_MGL: "Sha-Rui", 
    },
    "parts.zoom_fit": {
        LANG_CN: "适配", 
        LANG_EN: "Fit", 
        LANG_MGL: "gDie MEif", 
    },

    # ── preview.* ──
    "preview.banner": {
        LANG_CN: "此角色无组件数据，已进入精灵预览模式（选中后导出）",
        LANG_EN: "This character has no component data. Sprite preview mode (select to export)",
        LANG_MGL: "JIO has Nii hA-k. Lai Nei mode (Alte then KeI·tion)",
    },
    "preview.clear": {
        LANG_CN: "取消选择", 
        LANG_EN: "Clear selection", 
        LANG_MGL: "Ca-nay Alte", 
    },
    "preview.empty": {
        LANG_CN: "未找到任何精灵", 
        LANG_EN: "No sprites found", 
        LANG_MGL: "Nii sprites", 
    },
    "preview.export_all": {
        LANG_CN: "导出全部", 
        LANG_EN: "Export All", 
        LANG_MGL: "KeI·tion Alte hA-k", 
    },
    "preview.export_selected": {
        LANG_CN: "导出选中", 
        LANG_EN: "Export Selected", 
        LANG_MGL: "KeI·tion Alte", 
    },
    "preview.select_all": {
        LANG_CN: "全选", 
        LANG_EN: "Select All", 
        LANG_MGL: "Alte", 
    },
    "preview.selected_count": {
        LANG_CN: "已选 {count}/{total}", 
        LANG_EN: "Selected {count}/{total}", 
        LANG_MGL: "Alte {count}/{total}", 
    },

    # ── settings.* ──
    "settings.browse": {
        LANG_CN: "浏览...", 
        LANG_EN: "Browse...", 
        LANG_MGL: "Owk...", 
    },
    "settings.original_name_label": {
        LANG_CN: "显示原始文件名", 
        LANG_EN: "Show Original File Names", 
        LANG_MGL: "Show Original File Names", 
    },
    "settings.clear_cache_btn": {
        LANG_CN: "清除缓存", 
        LANG_EN: "Clear Cache", 
        LANG_MGL: "Ca-nay temp", 
    },
    "settings.clear_log_btn": {
        LANG_CN: "清理日志文件", 
        LANG_EN: "Clear Log Files", 
        LANG_MGL: "Ca-nay log Ge-mon", 
    },
    "settings.clear_log_confirm_msg": {
        LANG_CN: "确定要删除 logs 目录中的所有日志文件吗？", 
        LANG_EN: "Delete all log files in the logs directory?", 
        LANG_MGL: "Ca-nay Alte log Ge-mon?", 
    },
    "settings.clear_log_confirm_title": {
        LANG_CN: "清理日志文件", 
        LANG_EN: "Clear Log Files", 
        LANG_MGL: "Ca-nay log Ge-mon", 
    },
    "settings.clear_output_btn": {
        LANG_CN: "清除输出目录", 
        LANG_EN: "Clear Output Directory", 
        LANG_MGL: "Ca-nay output Ge-mon", 
    },
    "settings.clear_output_confirm_msg": {
        LANG_CN: "确定要删除输出目录中的所有文件吗？\n{path}", 
        LANG_EN: "Delete all files in the output directory?\n{path}", 
        LANG_MGL: "Ca-nay Alte Ge-mon in output?\n{path}", 
    },
    "settings.clear_output_confirm_title": {
        LANG_CN: "清除输出目录", 
        LANG_EN: "Clear Output Directory", 
        LANG_MGL: "Ca-nay output Ge-mon", 
    },
    "settings.debug_label": {
        LANG_CN: "调试模式", 
        LANG_EN: "Debug Mode", 
        LANG_MGL: "Debug Mode", 
    },
    "settings.output_dir_label": {
        LANG_CN: "输出目录", 
        LANG_EN: "Output Directory", 
        LANG_MGL: "output Ge-mon", 
    },
    "settings.restore_default": {
        LANG_CN: "恢复默认", 
        LANG_EN: "Restore Default", 
        LANG_MGL: "rEcanRey Taven", 
    },
    "settings.theme_dark": {
        LANG_CN: "深色", 
        LANG_EN: "Dark", 
        LANG_MGL: "DaRk rai", 
    },
    "settings.theme_label": {
        LANG_CN: "界面主题", 
        LANG_EN: "Theme", 
        LANG_MGL: "MEif oF Toim", 
    },
    "settings.theme_light": {
        LANG_CN: "浅色", 
        LANG_EN: "Light", 
        LANG_MGL: "Sha-Rui", 
    },
    "settings.title": {
        LANG_CN: "设置", 
        LANG_EN: "Settings", 
        LANG_MGL: "Co-Jundic", 
    },

    # ── tabs.* ──
    "tabs.about": {
        LANG_CN: "关于", 
        LANG_EN: "About", 
        LANG_MGL: "sinruits", 
    },
    "tabs.hierarchy": {
        LANG_CN: "组件结构", 
        LANG_EN: "Hierarchy", 
        LANG_MGL: "rEcanRey", 
    },
    "tabs.parts": {
        LANG_CN: "部件选择", 
        LANG_EN: "Part Selection", 
        LANG_MGL: "hA-k Alte", 
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

LANGUAGE_CODES = [LANG_CN, LANG_EN, LANG_MGL]