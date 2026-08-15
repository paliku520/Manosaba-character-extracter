"""
国际化 / 本地化支持（i18n）

提供中英文切换功能，GUI 中所有用户可见字符串均通过 _() 函数获取。
"""

from __future__ import annotations

from typing import Dict


# ── 语言代码 ──────────────────────────────────────────────
LANG_CN = "zh_CN"       # 简体中文
LANG_EN = "en_US"       # 英语
LANG_JA = "ja_JP"       # 日本語
LANG_MGL = "mgl_MG"     # 魔女语 (fiXmArge Language or Magical girl language)(架空语言)


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
        LANG_CN: "魔法少女的魔女审判立绘提取工具", 
        LANG_EN: "Magical Girl Witch Trials Sprite Tool", 
        LANG_JA: "魔法少女ノ魔女裁判 立ち絵抽出ツール", 
        LANG_MGL: "Manosaba - eXi' Toim", 
    },
    "about.copyright": {
        LANG_CN: "非商业用途 · 仅供学习交流", 
        LANG_EN: "Non-commercial · For learning and sharing", 
        LANG_JA: "非商用 · 学習・交流用", 
        LANG_MGL: "Non-commercial · For learning", 
    },
    "about.description": {
        LANG_CN: "从《魔法少女的魔女审判》游戏文件中提取并合成角色立绘的桌面工具。", 
        LANG_EN: "A desktop tool to extract and composite character sprites from the Magical Girl Witch Trials game files.", 
        LANG_JA: "『魔法少女ノ魔女裁判』のゲームファイルからキャラクターの立ち絵を抽出・合成するデスクトップツール。", 
        LANG_MGL: "Toim to eXi' and gDie JIO MEif from Manosaba.", 
    },
    "about.dev_bilibili": {
        LANG_CN: "Bilibili", 
        LANG_EN: "Bilibili", 
        LANG_JA: "Bilibili", 
        LANG_MGL: "Bilibili", 
    },
    "about.dev_click": {
        LANG_CN: "点击跳转", 
        LANG_EN: "Click to open", 
        LANG_JA: "クリックして開く", 
        LANG_MGL: "Alte to open", 
    },
    "about.dev_github": {
        LANG_CN: "GitHub", 
        LANG_EN: "GitHub", 
        LANG_JA: "GitHub", 
        LANG_MGL: "GitHub", 
    },
    "about.dev_name": {
        LANG_CN: "云野风云 (paliku520)", 
        LANG_EN: "Yunye Fengyun (paliku520)", 
        LANG_JA: "云野风云 (paliku520)", 
        LANG_MGL: "Yunye Fengyun (paliku520)", 
    },
    "about.dev_title": {
        LANG_CN: "开发者", 
        LANG_EN: "Developer", 
        LANG_JA: "開発者", 
        LANG_MGL: "KeI·tion", 
    },
    "about.export_count": {
        LANG_CN: "累计导出", 
        LANG_EN: "Total Exported", 
        LANG_JA: "累計エクスポート", 
        LANG_MGL: "Alte KeI·tion", 
    },
    "about.license_note": {
        LANG_CN: "本工具提取的内容来源于游戏【魔法少女的魔女审判】(Manosaba)\n© 2024 Re,AER LLC. / Acacia — 原游戏所有权利归其所有。", 
        LANG_EN: "The content extracted by this tool is from the game \"Magical Girl Witch Trials\" (Manosaba)\n© 2024 Re,AER LLC. / Acacia — All rights reserved by the original game developer.", 
        LANG_JA: "本ツールが抽出する内容はゲーム『魔法少女ノ魔女裁判』(Manosaba) に由来します\n© 2024 Re,AER LLC. / Acacia — 原作のすべての権利は原作者に帰属します。", 
        LANG_MGL: "Toim eXi' MEif from \"Mahou Shoujo no Majo Saiban\" (Manosaba)\n© 2024 Re,AER LLC. / Acacia — Alte oF Taven", 
    },
    "about.links_issues": {
        LANG_CN: "问题反馈", 
        LANG_EN: "Issues", 
        LANG_JA: "問題報告", 
        LANG_MGL: "AnxAn Baru", 
    },
    "about.links_repo": {
        LANG_CN: "源码仓库", 
        LANG_EN: "Source Code", 
        LANG_JA: "ソースコード", 
        LANG_MGL: "Taven Ge-mon", 
    },
    "about.links_title": {
        LANG_CN: "项目链接", 
        LANG_EN: "Project Links", 
        LANG_JA: "プロジェクトリンク", 
        LANG_MGL: "rEcanRey oF Ge-mon", 
    },
    "about.open_btn": {
        LANG_CN: "打开", 
        LANG_EN: "Open", 
        LANG_JA: "開く", 
        LANG_MGL: "Owk", 
    },
    "about.thanks_text": {
        LANG_CN: "感谢所有【共犯】的支持与反馈", 
        LANG_EN: "Thanks to all players for your support and feedback", 
        LANG_JA: "すべての【共犯者】の皆様のご支援とフィードバックに感謝します", 
        LANG_MGL: "gDie to Alte KyOhan for support and feedback", 
    },
    "about.thanks_title": {
        LANG_CN: "致谢", 
        LANG_EN: "Thanks", 
        LANG_JA: "謝辞", 
        LANG_MGL: "gDie", 
    },
    "about.update_btn": {
        LANG_CN: "检查更新", 
        LANG_EN: "Check for Updates", 
        LANG_JA: "更新を確認", 
        LANG_MGL: "AnxAn Toim", 
    },
    "about.version_label": {
        LANG_CN: "版本 {version}", 
        LANG_EN: "Version {version}", 
        LANG_JA: "バージョン {version}", 
        LANG_MGL: "Toim {version}", 
    },

    # ── app.* ──
    "app.disclaimer": {
        LANG_CN: "本工具为第三方非官方工具，与游戏官方无关。",
        LANG_EN: "This tool is a third-party unofficial tool and is not affiliated with the game official.",
        LANG_JA: "本ツールはサードパーティ製の非公式ツールであり、ゲーム公式とは無関係です。",
        LANG_MGL: "This tool is third-party, Nii oF game official.",
    },
    "app.click_to_copy": {
        LANG_CN: "点击复制", 
        LANG_EN: "Click to copy", 
        LANG_JA: "クリックでコピー", 
        LANG_MGL: "Alte to save", 
    },
    "app.copied": {
        LANG_CN: "已复制: {text}", 
        LANG_EN: "Copied: {text}", 
        LANG_JA: "コピーしました: {text}", 
        LANG_MGL: "saved: {text}", 
    },
    "app.progress.loading_bundles": {
        LANG_CN: "正在扫描并加载 bundle 文件...", 
        LANG_EN: "Scanning and loading bundle files...", 
        LANG_JA: "バンドルファイルをスキャンして読み込み中...", 
        LANG_MGL: "Loadeh Ge-mon...", 
    },
    "app.status.analyze_failed": {
        LANG_CN: "分析失败", 
        LANG_EN: "Analysis failed", 
        LANG_JA: "分析に失敗しました", 
        LANG_MGL: "AnxAn Baru", 
    },
    "app.status.analyzing": {
        LANG_CN: "正在分析: {name} ...", 
        LANG_EN: "Analyzing: {name} ...", 
        LANG_JA: "分析中: {name} ...", 
        LANG_MGL: "AnxAn: {name} ...", 
    },
    "app.status.analyze_done": {
        LANG_CN: "已分析: {name}", 
        LANG_EN: "Analyzed: {name}", 
        LANG_JA: "分析完了: {name}", 
        # 魔女语由用户自行补充
    },
    "app.status.cancelled": {
        LANG_CN: "已取消", 
        LANG_EN: "Cancelled", 
        LANG_JA: "キャンセルしました", 
        LANG_MGL: "Ca-nay", 
    },
    "app.status.checking_update": {
        LANG_CN: "正在检查更新...", 
        LANG_EN: "Checking for updates...", 
        LANG_JA: "更新を確認中...", 
        LANG_MGL: "AnxAn Toim...", 
    },
    "app.status.composite_done": {
        LANG_CN: "合成完成", 
        LANG_EN: "Composite complete", 
        LANG_JA: "合成が完了しました", 
        LANG_MGL: "gDie FineNd", 
    },
    "app.status.compositing": {
        LANG_CN: "正在合成图像...", 
        LANG_EN: "Compositing image...", 
        LANG_JA: "画像を合成中...", 
        LANG_MGL: "gDie MEif...", 
    },
    "app.status.export_done": {
        LANG_CN: "完成: {name} — 导出 {count} 个精灵", 
        LANG_EN: "Done: {name} — {count} sprites exported", 
        LANG_JA: "完了: {name} — {count} 枚のスプライトをエクスポートしました", 
        LANG_MGL: "FineNd: {name} — {count} KeI·tion", 
    },
    "app.status.exporting": {
        LANG_CN: "正在导出 {name} 的精灵...", 
        LANG_EN: "Exporting sprites for {name}...", 
        LANG_JA: "{name} のスプライトをエクスポート中...", 
        LANG_MGL: "KeI·tion {name}...", 
    },
    "app.status.extract_done": {
        LANG_CN: "已就绪: {name} — {count} 个部件", 
        LANG_EN: "Ready: {name} — {count} parts", 
        LANG_JA: "準備完了: {name} — {count} 個のパーツ", 
        LANG_MGL: "DArime: {name} — {count} hA-k", 
    },
    "app.status.extracting": {
        LANG_CN: "正在提取 {name} 的角色数据...", 
        LANG_EN: "Extracting character data for {name}...", 
        LANG_JA: "{name} のキャラクターデータを抽出中...", 
        LANG_MGL: "cOnzAI {name}...", 
    },
    "app.status.load_failed": {
        LANG_CN: "加载失败", 
        LANG_EN: "Load failed", 
        LANG_JA: "読み込みに失敗しました", 
        LANG_MGL: "Loadeh Baru", 
    },
    "app.status.loaded": {
        LANG_CN: "已加载 {count} 个角色", 
        LANG_EN: "Loaded {count} characters", 
        LANG_JA: "{count} 人のキャラクターを読み込みました", 
        LANG_MGL: "Loadeh {count} JIO", 
    },
    "app.status.ready": {
        LANG_CN: "就绪", 
        LANG_EN: "Ready", 
        LANG_JA: "準備完了", 
        LANG_MGL: "DArime", 
    },
    "app.status.settings_saved": {
        LANG_CN: "设置已保存: {path}", 
        LANG_EN: "Settings saved: {path}", 
        LANG_JA: "設定を保存しました: {path}", 
        LANG_MGL: "Co-Jundic saved: {path}", 
    },
    "app.subtitle": {
        LANG_CN: "角色立绘提取工具", 
        LANG_EN: "Character Sprite Extracter", 
        LANG_JA: "キャラクター立ち絵抽出ツール", 
        LANG_MGL: "JIO eXi' Toim", 
    },
    "app.title": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具", 
        LANG_EN: "Magical Girl Witch Trials - Character Sprite Tool", 
        LANG_JA: "魔法少女ノ魔女裁判 - キャラクター立ち絵抽出ツール", 
        LANG_MGL: "Manosaba - eXi' Toim", 
    },
    "app.loading": {
        LANG_CN: "正在加载...",
        LANG_EN: "Loading...",
        LANG_JA: "読み込み中...",
        LANG_MGL: "Toim...",
    },

    # ── char.* ──
    "char.alisa": {
        LANG_CN: "紫藤亚里沙", 
        LANG_EN: "Shito Alisa", 
        LANG_JA: "紫藤アリサ", 
        LANG_MGL: "Shito Alisa", 
    },
    "char.anan": {
        LANG_CN: "夏目安安", 
        LANG_EN: "Natsume An-An", 
        LANG_JA: "夏目アンアン", 
        LANG_MGL: "Natsume An-An", 
    },
    "char.coco": {
        LANG_CN: "泽渡可可", 
        LANG_EN: "Sawatari Coco", 
        LANG_JA: "沢渡ココ", 
        LANG_MGL: "Sawatari Coco", 
    },
    "char.creaturealisa": {
        LANG_CN: "亚里沙（魔女化）", 
        LANG_EN: "alisa(creature)", 
        LANG_JA: "アリサ（魔女化）", 
        LANG_MGL: "alisa(creature)", 
    },
    "char.creatureanan": {
        LANG_CN: "安安（魔女化）", 
        LANG_EN: "anan(creature)", 
        LANG_JA: "アンアン（魔女化）", 
        LANG_MGL: "anan(creature)", 
    },
    "char.creaturecoco": {
        LANG_CN: "可可（魔女化）", 
        LANG_EN: "coco(creature)", 
        LANG_JA: "ココ（魔女化）", 
        LANG_MGL: "coco(creature)", 
    },
    "char.creatureema": {
        LANG_CN: "艾玛（魔女化）", 
        LANG_EN: "ema(creature)", 
        LANG_JA: "エマ（魔女化）", 
        LANG_MGL: "ema(creature)", 
    },
    "char.creaturehanna": {
        LANG_CN: "汉娜（魔女化）", 
        LANG_EN: "hanna(creature)", 
        LANG_JA: "ハンナ（魔女化）", 
        LANG_MGL: "hanna(creature)", 
    },
    "char.creaturehiro": {
        LANG_CN: "希罗（魔女化）", 
        LANG_EN: "hiro(creature)", 
        LANG_JA: "ヒロ（魔女化）", 
        LANG_MGL: "hiro(creature)", 
    },
    "char.creatureleia": {
        LANG_CN: "蕾雅（魔女化）", 
        LANG_EN: "leia(creature)", 
        LANG_JA: "レイア（魔女化）", 
        LANG_MGL: "leia(creature)", 
    },
    "char.creaturemargo": {
        LANG_CN: "玛格（魔女化）", 
        LANG_EN: "margo(creature)", 
        LANG_JA: "マーゴ（魔女化）", 
        LANG_MGL: "margo(creature)", 
    },
    "char.creaturemeruru": {
        LANG_CN: "梅露露（魔女化）", 
        LANG_EN: "meruru(creature)", 
        LANG_JA: "メルル（魔女化）", 
        LANG_MGL: "meruru(creature)", 
    },
    "char.creaturemiria": {
        LANG_CN: "米莉亚（魔女化）", 
        LANG_EN: "miria(creature)", 
        LANG_JA: "ミリア（魔女化）", 
        LANG_MGL: "miria(creature)", 
    },
    "char.creaturenanoka": {
        LANG_CN: "奈叶香（魔女化）", 
        LANG_EN: "nanoka(creature)", 
        LANG_JA: "ナノカ（魔女化）", 
        LANG_MGL: "nanoka(creature)", 
    },
    "char.creaturenoah": {
        LANG_CN: "诺亚（魔女化）", 
        LANG_EN: "noah(creature)", 
        LANG_JA: "ノア（魔女化）", 
        LANG_MGL: "noah(creature)", 
    },
    "char.creaturesherry": {
        LANG_CN: "雪莉（魔女化）", 
        LANG_EN: "sherry(creature)", 
        LANG_JA: "シェリー（魔女化）", 
        LANG_MGL: "sherry(creature)", 
    },
    "char.ema": {
        LANG_CN: "樱羽艾玛", 
        LANG_EN: "Sakuraba Ema", 
        LANG_JA: "桜羽エマ", 
        LANG_MGL: "Sakuraba Ema", 
    },
    "char.hanna": {
        LANG_CN: "远野汉娜", 
        LANG_EN: "Tono Hanna", 
        LANG_JA: "遠野ハンナ", 
        LANG_MGL: "Tono Hanna", 
    },
    "char.hiro": {
        LANG_CN: "二阶堂希罗", 
        LANG_EN: "Nikaido Hiro", 
        LANG_JA: "二階堂ヒロ", 
        LANG_MGL: "Nikaido Hiro", 
    },
    "char.jailer": {
        LANG_CN: "看守（黑部穗乃香）", 
        LANG_EN: "jailer(Kurobe Honoka)", 
        LANG_JA: "看守(黒部ホノカ)", 
        LANG_MGL: "jailer(Kurobe Honoka)", 
    },
    "char.jailerb": {
        LANG_CN: "希罗（残骸）", 
        LANG_EN: "jailerb(Hiro)", 
        LANG_JA: "ヒロ（なれはて）", 
        LANG_MGL: "jailerb(Hiro)", 
    },
    "char.jailerc": {
        LANG_CN: "流浪的残骸", 
        LANG_EN: "jailerc", 
        LANG_JA: "野良のなれはく", 
        LANG_MGL: "jailerc", 
    },
    "char.leia": {
        LANG_CN: "莲见蕾雅", 
        LANG_EN: "Hasumi Leia", 
        LANG_JA: "蓮見レイア", 
        LANG_MGL: "Hasumi Leia", 
    },
    "char.margo": {
        LANG_CN: "宝生玛格", 
        LANG_EN: "Houshou Margo", 
        LANG_JA: "宝生マーゴ", 
        LANG_MGL: "Houshou Margo", 
    },
    "char.meruru": {
        LANG_CN: "冰上梅露露", 
        LANG_EN: "Hikami Meruru", 
        LANG_JA: "氷上メルル", 
        LANG_MGL: "Hikami Meruru", 
    },
    "char.miria": {
        LANG_CN: "佐伯米莉亚", 
        LANG_EN: "Saeki Miria", 
        LANG_JA: "佐伯ミリア", 
        LANG_MGL: "Saeki Miria", 
    },
    "char.nanoka": {
        LANG_CN: "黑部奈叶香", 
        LANG_EN: "Kurobe Nanoka", 
        LANG_JA: "黒部ナノカ", 
        LANG_MGL: "Kurobe Nanoka", 
    },
    "char.noah": {
        LANG_CN: "城崎诺亚", 
        LANG_EN: "Jogasaki Noah", 
        LANG_JA: "城ケ崎ノア", 
        LANG_MGL: "Jogasaki Noah", 
    },
    "char.sherry": {
        LANG_CN: "橘雪莉", 
        LANG_EN: "Tachibana Sherry", 
        LANG_JA: "橘シェリー", 
        LANG_MGL: "Tachibana Sherry", 
    },
    "char.warden": {
        LANG_CN: "典狱长", 
        LANG_EN: "warden", 
        LANG_JA: "ゴクチョー", 
        LANG_MGL: "warden", 
    },
    "char.yuki": {
        LANG_CN: "月代雪", 
        LANG_EN: "Tsukishiro Yuki", 
        LANG_JA: "月代ユキ", 
        LANG_MGL: "Tsukishiro Yuki", 
    },

    # ── console.* ──
    "console.exit_msg": {
        LANG_CN: "程序已退出。\n\n提示：控制台延迟关闭是正常现象（WebView2 清理子进程通常需 1-3 秒），请等待其自动消失。后台线程为 daemon 模式，不影响退出。\n\n警告：直接关闭控制台可能中断任务或引发异常。\n\n感谢使用【魔法少女的魔女审判立绘提取工具】！", 
        LANG_EN: "Program exited.\n\nNote: Console closing delay is normal (WebView2 cleanup usually takes 1-3 seconds). Please wait for it to disappear automatically.\n\nWARNING: Closing this console directly may interrupt tasks or cause exceptions.\n\nThank you for using the Magical Girl Witch Trials Sprite Tool!", 
        LANG_JA: "プログラムを終了しました。\n\nヒント：コンソールの終了遅延は正常です（WebView2 が子プロセスをクリーンアップするのに通常 1〜3 秒かかります）。自動的に消えるまでお待ちください。バックグラウンドスレッドはデーモンモードのため、終了には影響しません。\n\n警告：コンソールを直接閉じると、タスクが中断されたり例外が発生する可能性があります。\n\n【魔法少女ノ魔女裁判 立ち絵抽出ツール】をご利用いただきありがとうございます！", 
        LANG_MGL: "Program exited.\n\nNote: Console closing delay is normal (WebView2 cleanup usually takes 1-3 seconds). Please wait for it to disappear automatically.\n\nWARNING: Closing this console directly may interrupt tasks or cause exceptions.\n\nThank you for using the Manosaba Sprite Tool!", 
    },
    "console.exit_msg_electron": {
        LANG_CN: "应用已安全退出。\n\n提示：如果后端服务（Python）未完全关闭，\n系统会在几秒内自动清理。",
        LANG_EN: "Application exited safely.\n\nNote: If the backend service (Python) has not fully closed,\nthe system will clean it up automatically within a few seconds.",
        LANG_JA: "アプリケーションは安全に終了しました。\n\nヒント：バックエンドサービス（Python）が完全に終了していない場合、\n数秒後にシステムが自動的にクリーンアップします。",
        LANG_MGL: "Application exited safely.\n\nNote: If the backend service (Python) has not fully closed,\nthe system will clean it up automatically within a few seconds.",
    },
    "console.startup_msg": {
        LANG_CN: "欢迎使用【魔法少女的魔女审判立绘提取工具】！\n本控制台用于显示运行日志。\n\n提示：请不要轻易关闭本控制台，否则程序会立即退出。\n如需退出程序，请点击主窗口右上角的关闭按钮。", 
        LANG_EN: "Welcome to the Magical Girl Witch Trials Sprite Tool!\nThis console shows runtime logs.\n\nTip: Do not close this console casually, or the program will exit immediately.\nTo quit, click the close button on the top-right of the main window.", 
        LANG_JA: "【魔法少女ノ魔女裁判 立ち絵抽出ツール】へようこそ！\nこのコンソールは実行ログを表示します。\n\nヒント：このコンソールを軽率に閉じないでください。閉じるとプログラムは即座に終了します。\nプログラムを終了するには、メインウィンドウ右上の閉じるボタンをクリックしてください。", 
        LANG_MGL: "Welcome to the Manosaba Sprite Tool!\nThis console shows runtime logs.\n\nTip: Do not close this console casually, or the program will exit immediately.\nTo quit, click the close button on the top-right of the main window.", 
    },
    "console.startup_msg_electron": {
        LANG_CN: "欢迎使用【魔法少女的魔女审判立绘提取工具】！\n本窗口为日志控制台，仅用于显示运行日志。\n\n提示：关闭此窗口不会退出程序。\n如需退出程序，请点击主窗口右上角的关闭按钮。", 
        LANG_EN: "Welcome to the Magical Girl Witch Trials Sprite Tool!\nThis window is the log console, used to show runtime logs.\n\nTip: Closing this window will not exit the program.\nTo quit, click the close button on the top-right of the main window.", 
        LANG_JA: "【魔法少女ノ魔女裁判 立ち絵抽出ツール】へようこそ！\nこのウィンドウはログコンソールで、実行ログの表示専用です。\n\nヒント：このウィンドウを閉じてもプログラムは終了しません。\nプログラムを終了するには、メインウィンドウ右上の閉じるボタンをクリックしてください。", 
        LANG_MGL: "Welcome to the Manosaba Sprite Tool!\nThis window is the log console, used to show runtime logs.\n\nTip: Closing this window will not exit the program.\nTo quit, click the close button on the top-right of the main window.", 
    },
    "console.title": {
        LANG_CN: "魔法少女的魔女审判 - 角色立绘提取工具 - 控制台", 
        LANG_EN: "Magical Girl Witch Trials - Character Sprite Tool - console", 
        LANG_JA: "魔法少女ノ魔女裁判 - キャラクター立ち絵抽出ツール - コンソール", 
        LANG_MGL: "Manosaba - eXi' Toim - console", 
    },

    # ── dialog.* ──
    "dialog.prerelease_title": {
        LANG_CN: "测试版提示",
        LANG_EN: "Pre-release Notice",
        LANG_JA: "プレリリース版のお知らせ",
        LANG_MGL: "hAquEi: Toim oF now",
    },
    "dialog.prerelease_msg": {
        LANG_CN: "您正在使用测试版 v{version}，可能存在尚未修复的问题，请谨慎使用。",
        LANG_EN: "You are using a pre-release version v{version}. It may contain unfixed issues. Use with caution.",
        LANG_JA: "プレリリース版 v{version} を使用しています。未修正の問題が含まれる可能性があるため、ご注意ください。",
        LANG_MGL: "Toim oF now v{version} may have Baru. Use with hAquEi.",
    },
    "dialog.spoiler_title": {
        LANG_CN: "剧透提示",
        LANG_EN: "Spoiler Notice",
        LANG_JA: "ネタバレ注意",
        LANG_MGL: "hAquEi: sinruits",
    },
    "dialog.spoiler_msg": {
        LANG_CN: "本工具包含大量剧透内容，强烈建议您完成全周目（三周目完结）后再使用，以免破坏您的沉浸式体验。",
        LANG_EN: "This tool contains major spoilers. It is highly recommended to complete the main story before using it, so as not to ruin your immersive experience.",
        LANG_JA: "本ツールには大量のネタバレが含まれています。没入体験を損なわないよう、全周回（三周目クリア）を終えてから使用することを強くお勧めします。",
        LANG_MGL: "Toim has Alte sinruits. Finish Manosaba first for gDie.",
    },
    "dialog.spoiler_continue": {
        LANG_CN: "继续",
        LANG_EN: "Continue",
        LANG_JA: "続ける",
        LANG_MGL: "KaRause",
    },
    "dialog.spoiler_quit": {
        LANG_CN: "退出",
        LANG_EN: "Quit",
        LANG_JA: "終了",
        LANG_MGL: "FineNd",
    },
    "dialog.spoiler_never": {
        LANG_CN: "不再提示",
        LANG_EN: "Don't show again",
        LANG_JA: "今後表示しない",
        LANG_MGL: "Nii hAquEi again",
    },
    "dialog.analyze_error_msg": {
        LANG_CN: "分析角色【{name}】时出错:\n{msg}", 
        LANG_EN: "Error analyzing character '{name}':\n{msg}", 
        LANG_JA: "キャラクター【{name}】の分析中にエラーが発生しました:\n{msg}", 
        LANG_MGL: "AnxAn JIO '{name}' Baru:\n{msg}", 
    },
    "dialog.ask_mode_composite": {
        LANG_CN: "拼接角色图像", 
        LANG_EN: "Composite Character", 
        LANG_JA: "キャラクター画像を合成", 
        LANG_MGL: "gDie JIO", 
    },
    "dialog.ask_mode_composite_hint": {
        LANG_CN: "按组件的位置和深度信息合成完整立绘", 
        LANG_EN: "Assemble full character by position & depth", 
        LANG_JA: "パーツの位置と深度情報に基づいて完全な立ち絵を合成します", 
        LANG_MGL: "gDie full JIO by pos & depth", 
    },
    "dialog.ask_mode_export": {
        LANG_CN: "直接导出所有精灵文件", 
        LANG_EN: "Export All Sprites", 
        LANG_JA: "すべてのスプライトファイルを直接エクスポート", 
        LANG_MGL: "KeI·tion Alte", 
    },
    "dialog.ask_mode_export_hint": {
        LANG_CN: "将所有精灵图片保存到文件夹，不做任何拼接处理", 
        LANG_EN: "Save all sprite images without compositing", 
        LANG_JA: "合成処理を行わず、すべてのスプライト画像をフォルダに保存します", 
        LANG_MGL: "Save Alte sprites, Nii gDie", 
    },
    "dialog.ask_mode_msg": {
        LANG_CN: "该 bundle 包含组件数据，请选择处理方式:", 
        LANG_EN: "This bundle has component data. Choose a mode:", 
        LANG_JA: "このバンドルにはパーツデータが含まれています。処理方法を選択してください:", 
        LANG_MGL: "This has component. Alte mode:", 
    },
    "dialog.ask_mode_title": {
        LANG_CN: "处理方式 - {name}", 
        LANG_EN: "Processing Mode - {name}", 
        LANG_JA: "処理方法 - {name}", 
        LANG_MGL: "KeI·tion Mode - {name}", 
    },
    "dialog.bundle_not_found": {
        LANG_CN: "路径不存在: {path}", 
        LANG_EN: "Path not found: {path}", 
        LANG_JA: "パスが存在しません: {path}", 
        LANG_MGL: "Ge-mon not found: {path}", 
    },
    "dialog.cancel": {
        LANG_CN: "取消", 
        LANG_EN: "Cancel", 
        LANG_JA: "キャンセル", 
        LANG_MGL: "Ca-nay", 
    },
    "dialog.cancel_load_msg": {
        LANG_CN: "当前正在加载角色，是否中断？中断后将清理临时数据。", 
        LANG_EN: "A character is still loading. Interrupt it? Temporary data will be cleaned up.", 
        LANG_JA: "現在キャラクターを読み込み中です。中断しますか？中断後、一時データはクリーンアップされます。", 
        LANG_MGL: "JIO still Toim. Ca-nay? temp will be Ca-nay.", 
    },
    "dialog.cancel_load_title": {
        LANG_CN: "中断当前加载？", 
        LANG_EN: "Interrupt current loading?", 
        LANG_JA: "読み込みを中断しますか？", 
        LANG_MGL: "Ca-nay Toim?", 
    },
    "dialog.characters_not_found": {
        LANG_CN: "未找到 characters 目录: {path}", 
        LANG_EN: "Characters directory not found: {path}", 
        LANG_JA: "characters ディレクトリが見つかりません: {path}", 
        LANG_MGL: "JIO Ge-mon not found: {path}", 
    },
    "dialog.close": {
        LANG_CN: "关闭", 
        LANG_EN: "Close", 
        LANG_JA: "閉じる", 
        LANG_MGL: "FineNd", 
    },
    "dialog.composite_error_msg": {
        LANG_CN: "图像合成失败:\n{msg}", 
        LANG_EN: "Image compositing failed:\n{msg}", 
        LANG_JA: "画像の合成に失敗しました:\n{msg}", 
        LANG_MGL: "gDie MEif Baru:\n{msg}", 
    },
    "dialog.export_complete_msg": {
        LANG_CN: "角色【{name}】的 {count} 个精灵已导出到:\n{path}", 
        LANG_EN: "Character '{name}' — {count} sprites exported to:\n{path}", 
        LANG_JA: "キャラクター【{name}】の {count} 枚のスプライトをエクスポートしました:\n{path}", 
        LANG_MGL: "JIO '{name}' — {count} sprites KeI·tion to:\n{path}", 
    },
    "dialog.export_complete_title": {
        LANG_CN: "导出完成", 
        LANG_EN: "Export Complete", 
        LANG_JA: "エクスポート完了", 
        LANG_MGL: "KeI·tion FineNd", 
    },
    "dialog.no_bundle_files": {
        LANG_CN: "未找到 bundle 文件: {path}", 
        LANG_EN: "No bundle files found in: {path}", 
        LANG_JA: "バンドルファイルが見つかりません: {path}", 
        LANG_MGL: "Nii Ge-mon in: {path}", 
    },
    "dialog.no_bundle_loaded": {
        LANG_CN: "没有成功加载任何 bundle", 
        LANG_EN: "No bundles were loaded successfully", 
        LANG_JA: "バンドルが正常に読み込まれませんでした", 
        LANG_MGL: "Nii Ge-mon loaded", 
    },
    "dialog.no_component_export": {
        LANG_CN: "直接导出全部", 
        LANG_EN: "Export All Directly", 
        LANG_JA: "すべて直接エクスポート", 
        LANG_MGL: "KeI·tion Alte", 
    },
    "dialog.no_component_export_hint": {
        LANG_CN: "不预览，将所有精灵直接导出到输出目录", 
        LANG_EN: "Export all sprites to the output directory without preview", 
        LANG_JA: "プレビューせず、すべてのスプライトを出力ディレクトリに直接エクスポートします", 
        LANG_MGL: "KeI·tion Alte to output Ge-mon, Nii Lai Nei", 
    },
    "dialog.no_component_msg": {
        LANG_CN: "此角色不含组件数据，无法拼接立绘\n（这意味着这个文件不需要拼装）。\n请选择处理方式：",
        LANG_EN: "This character has no component data and cannot be composited\n (this file does not need assembling).\nPlease choose how to proceed:",
        LANG_JA: "このキャラクターにはパーツデータが含まれていないため、立ち絵を合成できません\n（つまり、このファイルは組み立てる必要がありません）。\n処理方法を選択してください：",
        LANG_MGL: "JIO has Nii hA-k, Nii gDie\n (Nii need assemble).\nAlte We-Ho:",
    },
    "dialog.no_component_preview": {
        LANG_CN: "预览精灵", 
        LANG_EN: "Preview Sprites", 
        LANG_JA: "スプライトをプレビュー", 
        LANG_MGL: "Lai Nei", 
    },
    "dialog.no_component_preview_hint": {
        LANG_CN: "在预览页查看所有精灵，可选中后再导出",
        LANG_EN: "View all sprites on the preview page, select then export",
        LANG_JA: "プレビューページで全スプライトを確認し、選択後にエクスポートできます",
        LANG_MGL: "View Alte sprites, Alte then KeI·tion",
    },
    "dialog.no_component_title": {
        LANG_CN: "选择处理方式 - {name}", 
        LANG_EN: "Choose how to process - {name}", 
        LANG_JA: "処理方法の選択 - {name}", 
        LANG_MGL: "Alte We-Ho - {name}", 
    },
    "dialog.ok": {
        LANG_CN: "确定", 
        LANG_EN: "OK", 
        LANG_JA: "OK", 
        LANG_MGL: "gDie", 
    },
    "dialog.open_output": {
        LANG_CN: "打开输出目录", 
        LANG_EN: "Open output folder", 
        LANG_JA: "出力ディレクトリを開く", 
        LANG_MGL: "Owk output Ge-mon", 
    },
    "dialog.open_release": {
        LANG_CN: "前往下载", 
        LANG_EN: "Open release", 
        LANG_JA: "ダウンロードページへ", 
        LANG_MGL: "Alte download", 
    },
    "dialog.process_error_msg": {
        LANG_CN: "处理数据时出错:\n{msg}", 
        LANG_EN: "Error processing data:\n{msg}", 
        LANG_JA: "データ処理中にエラーが発生しました:\n{msg}", 
        LANG_MGL: "KeI·tion data Baru:\n{msg}", 
    },
    "dialog.save_error_msg": {
        LANG_CN: "保存失败: {msg}", 
        LANG_EN: "Save failed: {msg}", 
        LANG_JA: "保存に失敗しました: {msg}", 
        LANG_MGL: "Save Baru: {msg}", 
    },
    "dialog.save_success_msg": {
        LANG_CN: "图像已保存:\n{path}", 
        LANG_EN: "Image saved:\n{path}", 
        LANG_JA: "画像を保存しました:\n{path}", 
        LANG_MGL: "MEif saved:\n{path}", 
    },
    "dialog.save_success_title": {
        LANG_CN: "成功", 
        LANG_EN: "Success", 
        LANG_JA: "成功", 
        LANG_MGL: "gDie", 
    },
    "dialog.update_available_msg": {
        LANG_CN: "发现新版本 v{new}！\n当前版本: v{current}\n\n是否前往下载页面？", 
        LANG_EN: "New version v{new} is available!\nCurrent version: v{current}\n\nOpen the download page?", 
        LANG_JA: "新しいバージョン v{new} が見つかりました！\n現在のバージョン: v{current}\n\nダウンロードページを開きますか？", 
        LANG_MGL: "neYO Toim v{new}!\nToim oF now: v{current}\n\nAlte download Ge-mon?", 
    },
    "dialog.update_available_title": {
        LANG_CN: "发现新版本", 
        LANG_EN: "Update Available", 
        LANG_JA: "新しいバージョンがあります", 
        LANG_MGL: "neYO Toim", 
    },
    "dialog.update_check_error_msg": {
        LANG_CN: "检查更新时出错:\n{msg}", 
        LANG_EN: "Failed to check for updates:\n{msg}", 
        LANG_JA: "更新の確認中にエラーが発生しました:\n{msg}", 
        LANG_MGL: "AnxAn Toim Baru:\n{msg}", 
    },
    "dialog.update_latest_msg": {
        LANG_CN: "当前已是最新版本 v{current}", 
        LANG_EN: "You are running the latest version v{current}", 
        LANG_JA: "現在、最新バージョン v{current} を使用しています", 
        LANG_MGL: "Toim oF now v{current}", 
    },

    # ── hierarchy.* ──
    "hierarchy.collapse_all": {
        LANG_CN: "全部折叠", 
        LANG_EN: "Collapse All", 
        LANG_JA: "すべて折りたたむ", 
        LANG_MGL: "Alte Ca-nay", 
    },
    "hierarchy.empty_hint": {
        LANG_CN: "暂无层级数据", 
        LANG_EN: "No hierarchy data", 
        LANG_JA: "階層データがありません", 
        LANG_MGL: "Nii rEcanRey", 
    },
    "hierarchy.expand_all": {
        LANG_CN: "全部展开", 
        LANG_EN: "Expand All", 
        LANG_JA: "すべて展開", 
        LANG_MGL: "Alte Owk", 
    },
    "hierarchy.hint": {
        LANG_CN: "组件层级结构（点击 + 展开/折叠）", 
        LANG_EN: "Component hierarchy (click + to expand/collapse)", 
        LANG_JA: "パーツ階層構造（+ をクリックで展開/折りたたみ）", 
        LANG_MGL: "rEcanRey oF hA-k (Alte + Owk / Ca-nay)", 
    },

    # ── info.* ──
    "info.guide_step1": {
        LANG_CN: "点击【加载游戏目录】→ 选择您的游戏安装文件夹（如 .../manosaba_game）", 
        LANG_EN: "Click 'Load Game Directory' → choose your game folder (e.g. .../manosaba_game)", 
        LANG_JA: "【ゲームディレクトリを読み込む】をクリック → ゲームのインストールフォルダを選択（例: .../manosaba_game）", 
        LANG_MGL: "Alte 'Loadeh Coa Tain' → Alte game Ge-mon (e.g. .../manosaba_game)", 
    },
    "info.guide_step2": {
        LANG_CN: "左侧列表出现角色名 → 单击选中", 
        LANG_EN: "Character names appear on the left → click to select", 
        LANG_JA: "左側のリストにキャラクター名が表示されたら → クリックして選択", 
        LANG_MGL: "JIO names on left → Alte to select", 
    },
    "info.guide_step3": {
        LANG_CN: "点击【拼接角色图像】→ 等待加载完成", 
        LANG_EN: "Click 'Composite Character Image' → wait for it to load", 
        LANG_JA: "【キャラクター画像を合成】をクリック → 読み込み完了を待つ", 
        LANG_MGL: "Alte 'gDie JIO' → wait for Toim", 
    },
    "info.guide_step4": {
        LANG_CN: "在【部件选择】面板勾选需要的部件（右侧实时预览）", 
        LANG_EN: "Check the parts you need in the 'Part Selection' panel (live preview on the right)", 
        LANG_JA: "【パーツ選択】パネルで必要なパーツをチェック（右側にリアルタイムプレビュー）", 
        LANG_MGL: "Alte hA-k in 'hA-k Alte' panel (Toim Lai Nei on right)", 
    },
    "info.guide_step5": {
        LANG_CN: "点击【保存合成图像】→ 立绘将导出至 output/ 目录", 
        LANG_EN: "Click 'Save Composite' → the image is exported to the output/ folder", 
        LANG_JA: "【合成画像を保存】をクリック → 立ち絵が output/ ディレクトリにエクスポートされます", 
        LANG_MGL: "Alte 'Save gDie MEif' → MEif KeI·tion to output/ Ge-mon", 
    },
    "info.guide_title": {
        LANG_CN: "快速上手：", 
        LANG_EN: "Quick Start:", 
        LANG_JA: "クイックスタート：", 
        LANG_MGL: "Owk:", 
    },
    "info.tab_title": {
        LANG_CN: "首页", 
        LANG_EN: "Home", 
        LANG_JA: "ホーム", 
        LANG_MGL: "Taven", 
    },
    "info.tip1": {
        LANG_CN: "首次使用建议先加载游戏目录，让工具建立缓存（位于 temp/）", 
        LANG_EN: "Load the game directory first to build the cache (stored in temp/)", 
        LANG_JA: "初回使用時はまずゲームディレクトリを読み込み、ツールにキャッシュを作成させることをお勧めします（temp/ に保存されます）", 
        LANG_MGL: "Loadeh Coa Tain first to build temp (in temp/)", 
    },
    "info.tip2": {
        LANG_CN: "切换角色时缓存会自动复用，速度更快", 
        LANG_EN: "Cache is reused automatically when switching characters, for faster speed", 
        LANG_JA: "キャラクターを切り替えるとキャッシュが自動的に再利用され、高速になります", 
        LANG_MGL: "temp auto reused when switching JIO, for faster Toim", 
    },
    "info.tip3": {
        LANG_CN: "如需导出所有部件，可选择【导出所有精灵】", 
        LANG_EN: "To export all parts, choose 'Export All Sprites'", 
        LANG_JA: "すべてのパーツをエクスポートする場合は、【すべてのスプライトをエクスポート】を選択できます", 
        LANG_MGL: "To KeI·tion Alte hA-k, Alte 'KeI·tion Alte'", 
    },
    "info.tips_title": {
        LANG_CN: "提示：", 
        LANG_EN: "Tips:", 
        LANG_JA: "ヒント：", 
        LANG_MGL: "hAquEi:", 
    },
    "info.welcome_lead": {
        LANG_CN: "本工具帮助您从《魔法少女的魔女审判》游戏文件中快速提取并合成角色立绘。", 
        LANG_EN: "This tool helps you quickly extract and composite character sprites from the Magical Girl Witch Trials game files.", 
        LANG_JA: "本ツールは『魔法少女ノ魔女裁判』のゲームファイルからキャラクターの立ち絵を素早く抽出・合成するのに役立ちます。", 
        LANG_MGL: "Toim helps Alte eXi' and gDie JIO MEif from Manosaba.", 
    },
    "info.welcome_title": {
        LANG_CN: "欢迎使用 魔法少女的魔女审判立绘提取工具 v{version}", 
        LANG_EN: "Welcome to Magical Girl Witch Trials Sprite Tool v{version}", 
        LANG_JA: "魔法少女ノ魔女裁判 立ち絵抽出ツール v{version} へようこそ", 
        LANG_MGL: "gDie to Manosaba - eXi' Toim v{version}", 
    },

    # ── lang.* ──
    "lang.en_US": {
        LANG_CN: "English", 
        LANG_EN: "English", 
        LANG_JA: "English", 
        LANG_MGL: "English", 
    },
    "lang.ja_JP": {
        LANG_CN: "日本語", 
        LANG_EN: "日本語", 
        LANG_JA: "日本語", 
        LANG_MGL: "日本語", 
    },
    "lang.label": {
        LANG_CN: "语言", 
        LANG_EN: "Language", 
        LANG_JA: "言語", 
        LANG_MGL: "Coword", 
    },
    "lang.mgl_MG": {
        LANG_CN: "fiXmArge", 
        LANG_EN: "fiXmArge", 
        LANG_JA: "fiXmArge", 
        LANG_MGL: "fiXmArge", 
    },
    "lang.zh_CN": {
        LANG_CN: "简体中文", 
        LANG_EN: "简体中文", 
        LANG_JA: "简体中文", 
        LANG_MGL: "简体中文", 
    },

    # ── left.* ──
    "left.char_list_title": {
        LANG_CN: "角色列表", 
        LANG_EN: "Character List", 
        LANG_JA: "キャラクターリスト", 
        LANG_MGL: "JIO Lisuto", 
    },
    "left.char_search": {
        LANG_CN: "搜索角色…", 
        LANG_EN: "Search characters…", 
        LANG_JA: "キャラクターを検索…", 
        LANG_MGL: "AnxAn JIO…", 
    },
    "left.check_update": {
        LANG_CN: "检查更新", 
        LANG_EN: "Check for Updates", 
        LANG_JA: "更新を確認", 
        LANG_MGL: "AnxAn Toim", 
    },
    "left.clear_cache": {
        LANG_CN: "清除缓存文件夹", 
        LANG_EN: "Clear Cache", 
        LANG_JA: "キャッシュフォルダをクリア", 
        LANG_MGL: "Ca-nay temp Ge-mon", 
    },
    "left.clear_cache_confirm_msg": {
        LANG_CN: "确定要清除所有临时缓存文件吗？\n\n下次加载角色时需要重新提取数据。", 
        LANG_EN: "Clear all temporary cache files?\n\nNext character load will need to re-extract data.", 
        LANG_JA: "すべての一時キャッシュファイルを削除しますか？\n\n次回キャラクターを読み込む際にデータを再抽出する必要があります。", 
        LANG_MGL: "Ca-nay Alte temp Ge-mon?\n\nNext JIO Loadeh need neYO cOnzAI.", 
    },
    "left.clear_cache_confirm_title": {
        LANG_CN: "清除缓存", 
        LANG_EN: "Clear Cache", 
        LANG_JA: "キャッシュをクリア", 
        LANG_MGL: "Ca-nay temp", 
    },
    "left.load_button": {
        LANG_CN: "加载游戏目录", 
        LANG_EN: "Load Game Directory", 
        LANG_JA: "ゲームディレクトリを読み込む", 
        LANG_MGL: "Loadeh Coa Tain", 
    },
    "left.open_output": {
        LANG_CN: "打开输出文件夹", 
        LANG_EN: "Open Output Folder", 
        LANG_JA: "出力フォルダを開く", 
        LANG_MGL: "Owk GE-mon", 
    },
    "left.settings": {
        LANG_CN: "设置", 
        LANG_EN: "Settings", 
        LANG_JA: "設定", 
        LANG_MGL: "Co-Jundic", 
    },
    "left.drop_overlay": {
        LANG_CN: "松开鼠标以加载此目录",
        LANG_EN: "Drop to load this directory",
        LANG_JA: "マウスを離してこのディレクトリを読み込み",
        LANG_MGL: "Alte to Loadeh Ge-mon",
    },
    "left.drop_not_folder": {
        LANG_CN: "请拖入文件夹（游戏目录）",
        LANG_EN: "Please drop a folder (game directory)",
        LANG_JA: "フォルダ（ゲームディレクトリ）をドラッグしてください",
        LANG_MGL: "Alte Ge-mon (Coa Tain)",
    },
    "left.drop_unsupported": {
        LANG_CN: "当前模式不支持拖拽导入，请点击【加载游戏目录】选择",
        LANG_EN: "Drag & drop is not supported here, please click \"Load Game Directory\"",
        LANG_JA: "現在のモードではドラッグ＆ドロップに対応していません。【ゲームディレクトリを読み込む】をクリックして選択してください",
        LANG_MGL: "Drag & drop Nii here, Alte 'Loadeh Coa Tain'",
    },

    # ── log.* ──
    "log.analyze_failed": {
        LANG_CN: "分析 bundle 失败 {name}: {e}", 
        LANG_EN: "Bundle analysis failed: {name} ({e})", 
        LANG_JA: "バンドル分析に失敗しました {name}: {e}", 
        LANG_MGL: "Bundle analysis failed: {name} ({e})", 
    },
    "log.analyze_has": {
        LANG_CN: "分析 {name}: 有组件", 
        LANG_EN: "Analyze {name}: has components", 
        LANG_JA: "分析 {name}: パーツあり", 
        LANG_MGL: "Analyze {name}: has components", 
    },
    "log.analyze_none": {
        LANG_CN: "分析 {name}: 无组件", 
        LANG_EN: "Analyze {name}: no components", 
        LANG_JA: "分析 {name}: パーツなし", 
        LANG_MGL: "Analyze {name}: no components", 
    },
    "log.app_exited": {
        LANG_CN: "程序正在退出", 
        LANG_EN: "App exiting", 
        LANG_JA: "プログラムを終了しています", 
        LANG_MGL: "App exiting", 
    },
    "log.app_started": {
        LANG_CN: "程序启动: v{version}", 
        LANG_EN: "App started: v{version}", 
        LANG_JA: "プログラム起動: v{version}", 
        LANG_MGL: "App started: v{version}", 
    },
    "log.bundle_files_found": {
        LANG_CN: "找到 {count} 个 bundle 文件", 
        LANG_EN: "Found {count} bundle files", 
        LANG_JA: "{count} 個のバンドルファイルが見つかりました", 
        LANG_MGL: "Found {count} bundle files", 
    },
    "log.cache_cleared": {
        LANG_CN: "已清空缓存", 
        LANG_EN: "Cache cleared", 
        LANG_JA: "キャッシュをクリアしました", 
        LANG_MGL: "Cache cleared", 
    },
    "log.cache_loaded": {
        LANG_CN: "从缓存加载角色数据: {name} ({count} 个部件)", 
        LANG_EN: "Loaded character data from cache: {name} ({count} parts)", 
        LANG_JA: "キャッシュからキャラクターデータを読み込みました: {name} ({count} 個のパーツ)", 
        LANG_MGL: "Loaded character data from cache: {name} ({count} parts)", 
    },
    "log.cache_saved": {
        LANG_CN: "缓存已保存: {name} -> {path}", 
        LANG_EN: "Cache saved: {name} -> {path}", 
        LANG_JA: "キャッシュを保存しました: {name} -> {path}", 
        LANG_MGL: "Cache saved: {name} -> {path}", 
    },
    "log.char_data_extracted": {
        LANG_CN: "角色数据已提取: {name} ({count} 个部件)", 
        LANG_EN: "Character data extracted: {name} ({count} parts)", 
        LANG_JA: "キャラクターデータを抽出しました: {name} ({count} 個のパーツ)", 
        LANG_MGL: "Character data extracted: {name} ({count} parts)", 
    },
    "log.char_load_cancelled": {
        LANG_CN: "角色加载/导出已中断", 
        LANG_EN: "Character loading/export cancelled", 
        LANG_JA: "キャラクターの読み込み/エクスポートを中断しました", 
        LANG_MGL: "Character loading/export cancelled", 
    },
    "log.characters_dir_found": {
        LANG_CN: "找到 characters 目录: {path}", 
        LANG_EN: "Characters directory found: {path}", 
        LANG_JA: "characters ディレクトリが見つかりました: {path}", 
        LANG_MGL: "Characters directory found: {path}", 
    },
    "log.original_name_off": {
        LANG_CN: "已关闭原始文件名显示", 
        LANG_EN: "Original file names off", 
        LANG_JA: "元のファイル名の表示をオフにしました", 
        LANG_MGL: "Original file names off", 
    },
    "log.original_name_on": {
        LANG_CN: "已开启原始文件名显示", 
        LANG_EN: "Original file names on", 
        LANG_JA: "元のファイル名の表示をオンにしました", 
        LANG_MGL: "Original file names on", 
    },
    "log.component_detect_failed": {
        LANG_CN: "检测组件数据失败 {name}: {e}", 
        LANG_EN: "Component data detection failed: {name} ({e})", 
        LANG_JA: "パーツデータの検出に失敗しました {name}: {e}", 
        LANG_MGL: "Component data detection failed: {name} ({e})", 
    },
    "log.composite_done": {
        LANG_CN: "合成完成: {size}", 
        LANG_EN: "Composite done: {size}", 
        LANG_JA: "合成完了: {size}", 
        LANG_MGL: "Composite done: {size}", 
    },
    "log.composite_failed": {
        LANG_CN: "合成失败: {e}", 
        LANG_EN: "Composite failed: {e}", 
        LANG_JA: "合成に失敗しました: {e}", 
        LANG_MGL: "Composite failed: {e}", 
    },
    "log.composite_failed_part": {
        LANG_CN: "  拼接失败 {name}: {e}", 
        LANG_EN: "  Composite failed: {name} ({e})", 
        LANG_JA: "  パーツ合成に失敗しました {name}: {e}", 
        LANG_MGL: "  Composite failed: {name} ({e})", 
    },
    "log.composite_saved": {
        LANG_CN: "已保存合成图: {path}", 
        LANG_EN: "Composite saved: {path}", 
        LANG_JA: "合成画像を保存しました: {path}", 
        LANG_MGL: "Composite saved: {path}", 
    },
    "log.debug_off": {
        LANG_CN: "调试模式已关闭", 
        LANG_EN: "Debug mode off", 
        LANG_JA: "デバッグモードをオフにしました", 
        LANG_MGL: "Debug mode off", 
    },
    "log.debug_on": {
        LANG_CN: "调试模式已开启（监视内存/CPU/窗口）", 
        LANG_EN: "Debug mode on (monitoring mem/CPU/window)", 
        LANG_JA: "デバッグモードをオンにしました（メモリ/CPU/ウィンドウを監視）", 
        LANG_MGL: "Debug mode on (monitoring mem/CPU/window)", 
    },
    "log.export_complete": {
        LANG_CN: "导出完成: {name} {count} 个精灵", 
        LANG_EN: "Exported: {name} ({count} sprites)", 
        LANG_JA: "エクスポート完了: {name} {count} 枚のスプライト", 
        LANG_MGL: "Exported: {name} ({count} sprites)", 
    },
    "log.export_done": {
        LANG_CN: "完成: 从 {file} 导出 {count} 个精灵 -> {dir}", 
        LANG_EN: "Done: exported {count} sprites from {file} -> {dir}", 
        LANG_JA: "完了: {file} から {count} 枚のスプライトをエクスポート -> {dir}", 
        LANG_MGL: "Done: exported {count} sprites from {file} -> {dir}", 
    },
    "log.export_failed": {
        LANG_CN: "导出 {name} 失败: {e}", 
        LANG_EN: "Export failed: {name} ({e})", 
        LANG_JA: "{name} のエクスポートに失敗しました: {e}", 
        LANG_MGL: "Export failed: {name} ({e})", 
    },
    "log.export_start": {
        LANG_CN: "开始导出 {name} 的精灵", 
        LANG_EN: "Exporting sprites for {name}", 
        LANG_JA: "{name} のスプライトのエクスポートを開始", 
        LANG_MGL: "Exporting sprites for {name}", 
    },
    "log.exported_sprite": {
        LANG_CN: "  导出精灵: {name}.png", 
        LANG_EN: "  Exported sprite: {name}.png", 
        LANG_JA: "  スプライトをエクスポート: {name}.png", 
        LANG_MGL: "  Exported sprite: {name}.png", 
    },
    "log.extract_cache_hit": {
        LANG_CN: "提取 {name}: 命中缓存", 
        LANG_EN: "Extract {name}: cache hit", 
        LANG_JA: "抽出 {name}: キャッシュにヒット", 
        LANG_MGL: "Extract {name}: cache hit", 
    },
    "log.extract_complete": {
        LANG_CN: "提取完成: {name} {count} 个部件", 
        LANG_EN: "Extracted: {name} ({count} parts)", 
        LANG_JA: "抽出完了: {name} {count} 個のパーツ", 
        LANG_MGL: "Extracted: {name} ({count} parts)", 
    },
    "log.found_common": {
        LANG_CN: "通过常见路径找到: {path}", 
        LANG_EN: "Found via common path: {path}", 
        LANG_JA: "一般的なパスで見つかりました: {path}", 
        LANG_MGL: "Found via common path: {path}", 
    },
    "log.found_deep": {
        LANG_CN: "通过常见路径深层找到: {path}", 
        LANG_EN: "Found via deep common path: {path}", 
        LANG_JA: "一般的なパスの深層で見つかりました: {path}", 
        LANG_MGL: "Found via deep common path: {path}", 
    },
    "log.found_sub": {
        LANG_CN: "通过常见路径子目录找到: {path}", 
        LANG_EN: "Found via common path subdirectory: {path}", 
        LANG_JA: "一般的なパスのサブディレクトリで見つかりました: {path}", 
        LANG_MGL: "Found via common path subdirectory: {path}", 
    },
    "log.gc_before_exit": {
        LANG_CN: "程序退出前已内存回收（释放 {count} 个对象），当前占用 {mem} MB", 
        LANG_EN: "GC done before exit ({count} objects collected), memory {mem} MB", 
        LANG_JA: "プログラム終了前にメモリを回収しました（{count} 個のオブジェクトを解放）、現在の使用量 {mem} MB", 
        LANG_MGL: "GC done before exit ({count} objects collected), memory {mem} MB", 
    },
    "log.invalid_preview_size": {
        LANG_CN: "预览图像尺寸无效: {size}", 
        LANG_EN: "Invalid preview image size: {size}", 
        LANG_JA: "プレビュー画像のサイズが無効です: {size}", 
        LANG_MGL: "Invalid preview image size: {size}", 
    },
    "log.js_composite_saved": {
        LANG_CN: "已保存合成图: {path}", 
        LANG_EN: "Composite saved: {path}", 
        LANG_JA: "合成画像を保存しました: {path}", 
        LANG_MGL: "Composite saved: {path}", 
    },
    "log.js_composite_start": {
        LANG_CN: "开始合成: {count} 个部件", 
        LANG_EN: "Compositing: {count} parts", 
        LANG_JA: "合成開始: {count} 個のパーツ", 
        LANG_MGL: "Compositing: {count} parts", 
    },
    "log.js_export_done": {
        LANG_CN: "导出完成: {name} {count}", 
        LANG_EN: "Exported: {name} {count}", 
        LANG_JA: "エクスポート完了: {name} {count}", 
        LANG_MGL: "Exported: {name} {count}", 
    },
    "log.js_extract_done": {
        LANG_CN: "提取完成: {name} {count}", 
        LANG_EN: "Extracted: {name} {count}", 
        LANG_JA: "抽出完了: {name} {count}", 
        LANG_MGL: "Extracted: {name} {count}", 
    },
    "log.js_load_dir": {
        LANG_CN: "加载目录: {path}", 
        LANG_EN: "Loading directory: {path}", 
        LANG_JA: "ディレクトリを読み込み: {path}", 
        LANG_MGL: "Loading directory: {path}", 
    },
    "log.js_select_char": {
        LANG_CN: "选择角色: {name}", 
        LANG_EN: "Select character: {name}", 
        LANG_JA: "キャラクターを選択: {name}", 
        LANG_MGL: "Select character: {name}", 
    },
    "log.js_selected": {
        LANG_CN: "已选择组件（{count}/{total}）", 
        LANG_EN: "Selected parts ({count}/{total})", 
        LANG_JA: "パーツを選択しました（{count}/{total}）", 
        LANG_MGL: "Selected parts ({count}/{total})", 
    },
    "log.lang_changed": {
        LANG_CN: "语言已切换: {code}", 
        LANG_EN: "Language switched: {code}", 
        LANG_JA: "言語を切り替えました: {code}", 
        LANG_MGL: "Language switched: {code}", 
    },
    "log.lang_detected": {
        LANG_CN: "检测到系统语言: {code}", 
        LANG_EN: "System language detected: {code}", 
        LANG_JA: "システム言語を検出しました: {code}", 
        LANG_MGL: "System language detected: {code}", 
    },
    "log.lang_from_settings": {
        LANG_CN: "从设置加载语言: {code}", 
        LANG_EN: "Language loaded from settings: {code}", 
        LANG_JA: "設定から言語を読み込みました: {code}", 
        LANG_MGL: "Language loaded from settings: {code}", 
    },
    "log.load_cancelled_dir": {
        LANG_CN: "目录 {path} 的加载已取消", 
        LANG_EN: "Loading cancelled for: {path}", 
        LANG_JA: "ディレクトリ {path} の読み込みをキャンセルしました", 
        LANG_MGL: "Loading cancelled for: {path}", 
    },
    "log.load_complete": {
        LANG_CN: "加载完成: {count} 个角色", 
        LANG_EN: "Loaded: {count} characters", 
        LANG_JA: "読み込み完了: {count} 人のキャラクター", 
        LANG_MGL: "Loaded: {count} characters", 
    },
    "log.load_error": {
        LANG_CN: "加载失败: {errors}", 
        LANG_EN: "Load failed: {errors}", 
        LANG_JA: "読み込みに失敗しました: {errors}", 
        LANG_MGL: "Load failed: {errors}", 
    },
    "log.load_failed": {
        LANG_CN: "加载失败 {name}: {e}", 
        LANG_EN: "Load failed: {name} ({e})", 
        LANG_JA: "読み込みに失敗しました {name}: {e}", 
        LANG_MGL: "Load failed: {name} ({e})", 
    },
    "log.loaded_all": {
        LANG_CN: "成功加载 {count} 个角色", 
        LANG_EN: "Successfully loaded {count} characters", 
        LANG_JA: "{count} 人のキャラクターの読み込みに成功しました", 
        LANG_MGL: "Successfully loaded {count} characters", 
    },
    "log.loaded_char": {
        LANG_CN: "加载角色成功: {name}", 
        LANG_EN: "Character loaded: {name}", 
        LANG_JA: "キャラクターの読み込みに成功しました: {name}", 
        LANG_MGL: "Character loaded: {name}", 
    },
    "log.loaded_sprite": {
        LANG_CN: "  加载精灵: {name}.png", 
        LANG_EN: "  Loaded sprite: {name}.png", 
        LANG_JA: "  スプライトを読み込み: {name}.png", 
        LANG_MGL: "  Loaded sprite: {name}.png", 
    },
    "log.loading_dir": {
        LANG_CN: "开始加载游戏目录: {path}", 
        LANG_EN: "Loading game directory: {path}", 
        LANG_JA: "ゲームディレクトリの読み込みを開始: {path}", 
        LANG_MGL: "Loading game directory: {path}", 
    },
    "log.log_cleared": {
        LANG_CN: "已清理 {count} 个日志文件", 
        LANG_EN: "Cleared {count} log file(s)", 
        LANG_JA: "{count} 個のログファイルを削除しました", 
        LANG_MGL: "Cleared {count} log file(s)", 
    },
    "log.logs_cleared": {
        LANG_CN: "已清理日志文件", 
        LANG_EN: "Log files cleared", 
        LANG_JA: "ログファイルを削除しました", 
        LANG_MGL: "Log files cleared", 
    },
    "log.output_cleared": {
        LANG_CN: "已清空输出目录: {path}", 
        LANG_EN: "Output directory cleared: {path}", 
        LANG_JA: "出力ディレクトリを空にしました: {path}", 
        LANG_MGL: "Output directory cleared: {path}", 
    },
    "log.output_dir_cleared": {
        LANG_CN: "已清空输出目录", 
        LANG_EN: "Output directory cleared", 
        LANG_JA: "出力ディレクトリを空にしました", 
        LANG_MGL: "Output directory cleared", 
    },
    "log.output_dir_set": {
        LANG_CN: "输出目录已设置: {path}", 
        LANG_EN: "Output directory set: {path}", 
        LANG_JA: "出力ディレクトリを設定しました: {path}", 
        LANG_MGL: "Output directory set: {path}", 
    },
    "log.preview_cleaned": {
        LANG_CN: "已清理预览临时文件: {path}", 
        LANG_EN: "Preview temp files cleaned: {path}", 
        LANG_JA: "プレビュー用一時ファイルを削除しました: {path}", 
        LANG_MGL: "Preview temp files cleaned: {path}", 
    },
    "log.preview_ready": {
        LANG_CN: "预览就绪: {name} — {count} 个精灵", 
        LANG_EN: "Preview ready: {name} — {count} sprites", 
        LANG_JA: "プレビュー準備完了: {name} — {count} 枚のスプライト", 
        LANG_MGL: "Preview ready: {name} — {count} sprites", 
    },
    "log.process_data_failed": {
        LANG_CN: "处理角色数据失败: {e}", 
        LANG_EN: "Character data processing failed: {e}", 
        LANG_JA: "キャラクターデータの処理に失敗しました: {e}", 
        LANG_MGL: "Character data processing failed: {e}", 
    },
    "log.recursive_search": {
        LANG_CN: "常见路径未命中，开始递归搜索 characters 目录...", 
        LANG_EN: "Common paths not found, searching recursively for characters dir...", 
        LANG_JA: "一般的なパスが見つからず、characters ディレクトリを再帰的に検索中...", 
        LANG_MGL: "Common paths not found, searching recursively for characters dir...", 
    },
    "log.resource_title": {
        LANG_CN: " | 内存 {mem} MB | CPU {cpu}%{win}", 
        LANG_EN: " | mem {mem} MB | CPU {cpu}%{win}", 
        LANG_JA: " | メモリ {mem} MB | CPU {cpu}%{win}", 
        LANG_MGL: " | mem {mem} MB | CPU {cpu}%{win}", 
    },
    "log.resource_usage": {
        LANG_CN: "资源占用: 内存 {mem} MB | CPU {cpu}%{win}", 
        LANG_EN: "Resource usage: mem {mem} MB | CPU {cpu}%{win}", 
        LANG_JA: "リソース使用量: メモリ {mem} MB | CPU {cpu}%{win}", 
        LANG_MGL: "Resource usage: mem {mem} MB | CPU {cpu}%{win}", 
    },
    "log.resource_win": {
        LANG_CN: " | 窗口 {width}x{height}", 
        LANG_EN: " | window {width}x{height}", 
        LANG_JA: " | ウィンドウ {width}x{height}", 
        LANG_MGL: " | window {width}x{height}", 
    },
    "log.saved_path_failed": {
        LANG_CN: "保存路径记忆失败: {e}", 
        LANG_EN: "Failed to save path memory: {e}", 
        LANG_JA: "パス記憶の保存に失敗しました: {e}", 
        LANG_MGL: "Failed to save path memory: {e}", 
    },
    "log.settings_save_failed": {
        LANG_CN: "保存设置失败: {e}", 
        LANG_EN: "Failed to save settings: {e}", 
        LANG_JA: "設定の保存に失敗しました: {e}", 
        LANG_MGL: "Failed to save settings: {e}", 
    },
    "log.settings_repaired": {
        LANG_CN: "设置文件已损坏，已自动修复（原文件备份到 {path}）", 
        LANG_EN: "Settings file was corrupted and auto-repaired (backup: {path})", 
        LANG_JA: "設定ファイルが破損していたため自動修復しました（元ファイルは {path} にバックアップ）", 
        LANG_MGL: "Settings file was corrupted and auto-repaired (backup: {path})", 
    },
    "log.skipped_char": {
        LANG_CN: "跳过角色: {name} (未找到精灵资源)", 
        LANG_EN: "Skipped: {name} (no sprites found)", 
        LANG_JA: "キャラクターをスキップ: {name}（スプライトが見つかりません）", 
        LANG_MGL: "Skipped: {name} (no sprites found)", 
    },
    "log.sprite_extract_failed": {
        LANG_CN: "  精灵提取失败 (path_id={id}): {e}", 
        LANG_EN: "  Sprite extraction failed (path_id={id}): {e}", 
        LANG_JA: "  スプライト抽出に失敗しました (path_id={id}): {e}", 
        LANG_MGL: "  Sprite extraction failed (path_id={id}): {e}", 
    },
    "log.temp_cleared": {
        LANG_CN: "已清空临时缓存: {path}", 
        LANG_EN: "Temp cache cleared: {path}", 
        LANG_JA: "一時キャッシュを空にしました: {path}", 
        LANG_MGL: "Temp cache cleared: {path}", 
    },
    "log.theme_changed": {
        LANG_CN: "主题已切换: {theme}", 
        LANG_EN: "Theme switched: {theme}", 
        LANG_JA: "テーマを切り替えました: {theme}", 
        LANG_MGL: "Theme switched: {theme}", 
    },
    "log.accent_changed": {
        LANG_CN: "主题色已切换: {accent}", 
        LANG_EN: "Accent switched: {accent}", 
        LANG_JA: "テーマカラーを切り替えました: {accent}", 
        LANG_MGL: "Accent switched: {accent}", 
    },

    # ── parts.* ──
    "parts.auto_update": {
        LANG_CN: "自动更新", 
        LANG_EN: "Auto Update", 
        LANG_JA: "自動更新", 
        LANG_MGL: "Toim KaRause", 
    },
    "parts.clear_preview": {
        LANG_CN: "清空预览", 
        LANG_EN: "Clear Preview", 
        LANG_JA: "プレビューをクリア", 
        LANG_MGL: "Ca-nay Lai Nei", 
    },
    "parts.composite_btn": {
        LANG_CN: "生成合成图像", 
        LANG_EN: "Generate Composite", 
        LANG_JA: "合成画像を生成", 
        LANG_MGL: "gDie MEif", 
    },
    "parts.deselect_all": {
        LANG_CN: "取消全选", 
        LANG_EN: "Deselect All", 
        LANG_JA: "すべて選択解除", 
        LANG_MGL: "Alte Ca-nay", 
    },
    "parts.deselect_group": {
        LANG_CN: "取消选择",
        LANG_EN: "Deselect",
        LANG_JA: "選択解除",
        LANG_MGL: "Ca-nay Alte",
    },
    "parts.empty_hint": {
        LANG_CN: "请先在左侧选择一个角色进入拼接模式", 
        LANG_EN: "Select a character on the left to enter composite mode", 
        LANG_JA: "先に左側でキャラクターを選択して合成モードに入ってください", 
        LANG_MGL: "Alte JIO on left for gDie mode", 
    },
    "parts.no_preview": {
        LANG_CN: "未生成预览", 
        LANG_EN: "No preview", 
        LANG_JA: "プレビューが生成されていません", 
        LANG_MGL: "Lai Nei Nii", 
    },
    "parts.no_selection_hint": {
        LANG_CN: "请至少选择一个部件", 
        LANG_EN: "Please select at least one part", 
        LANG_JA: "少なくとも 1 つのパーツを選択してください", 
        LANG_MGL: "Alte one hA-k", 
    },
    "parts.preview_title": {
        LANG_CN: "实时预览", 
        LANG_EN: "Live Preview", 
        LANG_JA: "リアルタイムプレビュー", 
        LANG_MGL: "Toim Lai Nei", 
    },
    "parts.save_composite": {
        LANG_CN: "保存合成图像", 
        LANG_EN: "Save Composite", 
        LANG_JA: "合成画像を保存", 
        LANG_MGL: "Save gDie MEif", 
    },
    "parts.search_hint": {
        LANG_CN: "搜索部件…", 
        LANG_EN: "Search parts…", 
        LANG_JA: "パーツを検索…", 
        LANG_MGL: "AnxAn hA-k…", 
    },
    "parts.select_all": {
        LANG_CN: "全选", 
        LANG_EN: "Select All", 
        LANG_JA: "すべて選択", 
        LANG_MGL: "Alte", 
    },
    "parts.selected_list_title": {
        LANG_CN: "已选精灵", 
        LANG_EN: "Selected Sprites", 
        LANG_JA: "選択済みスプライト", 
        LANG_MGL: "Alte KeI·tion", 
    },
    "parts.sketch_label": {
        LANG_CN: "素描本文字",
        LANG_EN: "Sketchbook Text",
        LANG_JA: "スケッチブックの文字",
        LANG_MGL: "hA-k oF FuWana",
    },
    "parts.sketch_placeholder": {
        LANG_CN: "输入显示在素描本上的文字…",
        LANG_EN: "Enter text shown on the sketchbook…",
        LANG_JA: "スケッチブックに表示する文字を入力…",
        LANG_MGL: "Coword iN FuWana…",
    },
    "parts.sketch_size": {
        LANG_CN: "字号",
        LANG_EN: "Font Size",
        LANG_JA: "文字サイズ",
        LANG_MGL: "Sha-Rui",
    },
    "parts.sketch_apply": {
        LANG_CN: "应用",
        LANG_EN: "Apply",
        LANG_JA: "適用",
        LANG_MGL: "gDie",
    },
    "parts.sketch_edit": {
        LANG_CN: "编辑文字",
        LANG_EN: "Edit Text",
        LANG_JA: "文字を編集",
        LANG_MGL: "KeI·tion Coword",
    },
    "parts.sketch_align": {
        LANG_CN: "对齐",
        LANG_EN: "Align",
        LANG_JA: "配置",
        LANG_MGL: "rEcanRey",
    },
    "parts.align_left": {
        LANG_CN: "左",
        LANG_EN: "Left",
        LANG_JA: "左",
        LANG_MGL: "mu·Yon",
    },
    "parts.align_center": {
        LANG_CN: "中",
        LANG_EN: "Center",
        LANG_JA: "中央",
        LANG_MGL: "Alte",
    },
    "parts.align_right": {
        LANG_CN: "右",
        LANG_EN: "Right",
        LANG_JA: "右",
        LANG_MGL: "Taven",
    },
    "parts.total": {
        LANG_CN: "个部件", 
        LANG_EN: "parts", 
        LANG_JA: "個のパーツ", 
        LANG_MGL: "hA-k", 
    },
    "parts.zoom": {
        LANG_CN: "缩放", 
        LANG_EN: "Zoom", 
        LANG_JA: "ズーム", 
        LANG_MGL: "Sha-Rui", 
    },
    "parts.zoom_fit": {
        LANG_CN: "适配", 
        LANG_EN: "Fit", 
        LANG_JA: "フィット", 
        LANG_MGL: "gDie MEif", 
    },

    # ── preview.* ──
    "preview.banner": {
        LANG_CN: "此角色无组件数据，已进入精灵预览模式（选中后导出）",
        LANG_EN: "This character has no component data. Sprite preview mode (select to export)",
        LANG_JA: "このキャラクターにはパーツデータがありません。スプライトプレビューモードに入りました（選択後にエクスポート）",
        LANG_MGL: "JIO has Nii hA-k. Lai Nei mode (Alte then KeI·tion)",
    },
    "preview.loading_thumbs": {
        LANG_CN: "正在加载精灵预览...",
        LANG_EN: "Loading sprite preview...",
        LANG_JA: "スプライトプレビューを読み込み中...",
        LANG_MGL: "Toim Lai Nei...",
    },
    "preview.clear": {
        LANG_CN: "取消选择", 
        LANG_EN: "Clear selection", 
        LANG_JA: "選択解除", 
        LANG_MGL: "Ca-nay Alte", 
    },
    "preview.empty": {
        LANG_CN: "未找到任何精灵", 
        LANG_EN: "No sprites found", 
        LANG_JA: "スプライトが見つかりません", 
        LANG_MGL: "Nii sprites", 
    },
    "preview.export_all": {
        LANG_CN: "导出全部", 
        LANG_EN: "Export All", 
        LANG_JA: "すべてエクスポート", 
        LANG_MGL: "KeI·tion Alte hA-k", 
    },
    "preview.export_selected": {
        LANG_CN: "导出选中", 
        LANG_EN: "Export Selected", 
        LANG_JA: "選択したものをエクスポート", 
        LANG_MGL: "KeI·tion Alte", 
    },
    "preview.select_all": {
        LANG_CN: "全选", 
        LANG_EN: "Select All", 
        LANG_JA: "すべて選択", 
        LANG_MGL: "Alte", 
    },
    "preview.selected_count": {
        LANG_CN: "已选 {count}/{total}", 
        LANG_EN: "Selected {count}/{total}", 
        LANG_JA: "選択済み {count}/{total}", 
        LANG_MGL: "Alte {count}/{total}", 
    },

    # ── settings.* ──
    "settings.browse": {
        LANG_CN: "浏览...", 
        LANG_EN: "Browse...", 
        LANG_JA: "参照...", 
        LANG_MGL: "Owk...", 
    },
    "settings.original_name_label": {
        LANG_CN: "显示原始文件名", 
        LANG_EN: "Show Original File Names", 
        LANG_JA: "元のファイル名を表示", 
        LANG_MGL: "Show Original File Names", 
    },
    "settings.clear_cache_btn": {
        LANG_CN: "清除缓存", 
        LANG_EN: "Clear Cache", 
        LANG_JA: "キャッシュをクリア", 
        LANG_MGL: "Ca-nay temp", 
    },
    "settings.clear_log_btn": {
        LANG_CN: "清理日志文件", 
        LANG_EN: "Clear Log Files", 
        LANG_JA: "ログファイルを削除", 
        LANG_MGL: "Ca-nay log Ge-mon", 
    },
    "settings.clear_log_confirm_msg": {
        LANG_CN: "确定要删除 logs 目录中的所有日志文件吗？", 
        LANG_EN: "Delete all log files in the logs directory?", 
        LANG_JA: "logs ディレクトリ内のすべてのログファイルを削除しますか？", 
        LANG_MGL: "Ca-nay Alte log Ge-mon?", 
    },
    "settings.clear_log_confirm_title": {
        LANG_CN: "清理日志文件", 
        LANG_EN: "Clear Log Files", 
        LANG_JA: "ログファイルを削除", 
        LANG_MGL: "Ca-nay log Ge-mon", 
    },
    "settings.clear_output_btn": {
        LANG_CN: "清除输出目录", 
        LANG_EN: "Clear Output Directory", 
        LANG_JA: "出力ディレクトリをクリア", 
        LANG_MGL: "Ca-nay output Ge-mon", 
    },
    "settings.clear_output_confirm_msg": {
        LANG_CN: "确定要删除输出目录中的所有文件吗？\n{path}", 
        LANG_EN: "Delete all files in the output directory?\n{path}", 
        LANG_JA: "出力ディレクトリ内のすべてのファイルを削除しますか？\n{path}", 
        LANG_MGL: "Ca-nay Alte Ge-mon in output?\n{path}", 
    },
    "settings.clear_output_confirm_title": {
        LANG_CN: "清除输出目录", 
        LANG_EN: "Clear Output Directory", 
        LANG_JA: "出力ディレクトリをクリア", 
        LANG_MGL: "Ca-nay output Ge-mon", 
    },
    "settings.debug_label": {
        LANG_CN: "调试模式", 
        LANG_EN: "Debug Mode", 
        LANG_JA: "デバッグモード", 
        LANG_MGL: "Debug Mode", 
    },
    "settings.output_dir_label": {
        LANG_CN: "输出目录", 
        LANG_EN: "Output Directory", 
        LANG_JA: "出力ディレクトリ", 
        LANG_MGL: "output Ge-mon", 
    },
    "settings.restore_default": {
        LANG_CN: "恢复默认", 
        LANG_EN: "Restore Default", 
        LANG_JA: "デフォルトに戻す", 
        LANG_MGL: "rEcanRey Taven", 
    },
    "settings.theme_dark": {
        LANG_CN: "深色", 
        LANG_EN: "Dark", 
        LANG_JA: "ダーク", 
        LANG_MGL: "DaRk rai", 
    },
    "settings.theme_label": {
        LANG_CN: "界面主题", 
        LANG_EN: "Theme", 
        LANG_JA: "テーマ", 
        LANG_MGL: "MEif oF Toim", 
    },
    "settings.theme_light": {
        LANG_CN: "浅色", 
        LANG_EN: "Light", 
        LANG_JA: "ライト", 
        LANG_MGL: "Sha-Rui", 
    },
    "settings.accent_label": {
        LANG_CN: "主题色",
        LANG_EN: "Accent Color",
        LANG_JA: "テーマカラー",
        LANG_MGL: "MEif oF Toim",
    },
    "settings.accent_default": {
        LANG_CN: "默认（绿）",
        LANG_EN: "Default (Green)",
        LANG_JA: "デフォルト（緑）",
        LANG_MGL: "Taven (Green)",
    },
    "settings.accent_alisa": {
        LANG_CN: "紫藤亚里沙（红）",
        LANG_EN: "Alisa (Red)",
        LANG_JA: "紫藤アリサ（赤）",
        LANG_MGL: "Alisa (Red)",
    },
    "settings.accent_anan": {
        LANG_CN: "夏目安安（紫）",
        LANG_EN: "Anan (Violet)",
        LANG_JA: "夏目アンアン（紫）",
        LANG_MGL: "Anan (Violet)",
    },
    "settings.accent_coco": {
        LANG_CN: "泽渡可可（橙）",
        LANG_EN: "Coco (Orange)",
        LANG_JA: "沢渡ココ（オレンジ）",
        LANG_MGL: "Coco (Orange)",
    },
    "settings.accent_ema": {
        LANG_CN: "樱羽艾玛（粉）",
        LANG_EN: "Ema (Pink)",
        LANG_JA: "桜羽エマ（ピンク）",
        LANG_MGL: "Ema (Pink)",
    },
    "settings.accent_hanna": {
        LANG_CN: "远野汉娜（黄绿）",
        LANG_EN: "Hanna (Lime)",
        LANG_JA: "遠野ハンナ（黄緑）",
        LANG_MGL: "Hanna (Lime)",
    },
    "settings.accent_hiro": {
        LANG_CN: "二阶堂希罗（红）",
        LANG_EN: "Hiro (Red)",
        LANG_JA: "二階堂ヒロ（赤）",
        LANG_MGL: "Hiro (Red)",
    },
    "settings.accent_jailer": {
        LANG_CN: "看守（银灰）",
        LANG_EN: "Jailer (Silver)",
        LANG_JA: "看守（シルバー）",
        LANG_MGL: "Jailer (Silver)",
    },
    "settings.accent_leia": {
        LANG_CN: "莲见蕾雅（琥珀）",
        LANG_EN: "Leia (Amber)",
        LANG_JA: "蓮見レイア（琥珀）",
        LANG_MGL: "Leia (Amber)",
    },
    "settings.accent_margo": {
        LANG_CN: "宝生玛格（紫）",
        LANG_EN: "Margo (Violet)",
        LANG_JA: "宝生マーゴ（紫）",
        LANG_MGL: "Margo (Violet)",
    },
    "settings.accent_meruru": {
        LANG_CN: "冰上梅露露（粉）",
        LANG_EN: "Meruru (Pink)",
        LANG_JA: "氷上メルル（ピンク）",
        LANG_MGL: "Meruru (Pink)",
    },
    "settings.accent_miria": {
        LANG_CN: "佐伯米莉亚（黄）",
        LANG_EN: "Miria (Yellow)",
        LANG_JA: "佐伯ミリア（黄）",
        LANG_MGL: "Miria (Yellow)",
    },
    "settings.accent_nanoka": {
        LANG_CN: "黑部奈叶香（灰）",
        LANG_EN: "Nanoka (Gray)",
        LANG_JA: "黒部ナノカ（グレー）",
        LANG_MGL: "Nanoka (Gray)",
    },
    "settings.accent_noah": {
        LANG_CN: "城崎诺亚（青）",
        LANG_EN: "Noah (Cyan)",
        LANG_JA: "城ケ崎ノア（シアン）",
        LANG_MGL: "Noah (Cyan)",
    },
    "settings.accent_sherry": {
        LANG_CN: "橘雪莉（蓝）",
        LANG_EN: "Sherry (Blue)",
        LANG_JA: "橘シェリー（ブルー）",
        LANG_MGL: "Sherry (Blue)",
    },
    "settings.accent_warden": {
        LANG_CN: "典狱长（雾紫）",
        LANG_EN: "Warden (Mist)",
        LANG_JA: "ゴクチョー（霧紫）",
        LANG_MGL: "Warden (Mist)",
    },
    "settings.accent_yuki": {
        LANG_CN: "月代雪（淡蓝）",
        LANG_EN: "Yuki (Ice)",
        LANG_JA: "月代ユキ（水色）",
        LANG_MGL: "Yuki (Ice)",
    },
    "settings.section_appearance": {
        LANG_CN: "外观",
        LANG_EN: "Appearance",
        LANG_JA: "外観",
        LANG_MGL: "Sha-Rui",
    },
    "settings.section_display": {
        LANG_CN: "显示",
        LANG_EN: "Display",
        LANG_JA: "表示",
        LANG_MGL: "Lai Nei",
    },
    "settings.section_data": {
        LANG_CN: "数据",
        LANG_EN: "Data",
        LANG_JA: "データ",
        LANG_MGL: "data",
    },
    "settings.lang_ai_note": {
        LANG_CN: "※语言翻译由AI生成，不保证完全准确，仅供辅助参考。",
        LANG_EN: "※ Translations are AI-generated and may not be fully accurate. For reference only.",
        LANG_JA: "※ 翻訳はAI生成であり、完全に正確とは限りません。参考用です。",
        LANG_MGL: "※ Coword from AI, Nii fully correct. For reference.",
    },
    "settings.title": {
        LANG_CN: "设置", 
        LANG_EN: "Settings", 
        LANG_JA: "設定", 
        LANG_MGL: "Co-Jundic", 
    },

    # ── tabs.* ──
    "tabs.about": {
        LANG_CN: "关于", 
        LANG_EN: "About", 
        LANG_JA: "情報", 
        LANG_MGL: "sinruits", 
    },
    "tabs.hierarchy": {
        LANG_CN: "组件结构", 
        LANG_EN: "Hierarchy", 
        LANG_JA: "階層構造", 
        LANG_MGL: "rEcanRey", 
    },
    "tabs.parts": {
        LANG_CN: "部件选择", 
        LANG_EN: "Part Selection", 
        LANG_JA: "パーツ選択", 
        LANG_MGL: "hA-k Alte", 
    },

    # ── titlebar.* ──
    "titlebar.minimize": {
        LANG_CN: "最小化",
        LANG_EN: "Minimize",
        LANG_JA: "最小化",
        LANG_MGL: "Sha-Rui",
    },
    "titlebar.maximize": {
        LANG_CN: "最大化",
        LANG_EN: "Maximize",
        LANG_JA: "最大化",
        LANG_MGL: "gDie",
    },
    "titlebar.close": {
        LANG_CN: "关闭 (Alt + F4)",
        LANG_EN: "Close (Alt + F4)",
        LANG_JA: "閉じる (Alt + F4)",
        LANG_MGL: "FineNd (Alt + F4)",
    },
    "titlebar.console": {
        LANG_CN: "日志控制台 (Ctrl+Shift+L)",
        LANG_EN: "Log Console (Ctrl+Shift+L)",
        LANG_JA: "ログコンソール (Ctrl+Shift+L)",
        LANG_MGL: "Log Console (Ctrl+Shift+L)",
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

LANGUAGE_CODES = [LANG_CN, LANG_EN, LANG_JA, LANG_MGL]
