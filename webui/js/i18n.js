/* ============================================================
 * i18n.js — 前端国际化工具
 * 翻译数据由 Python 后端通过 get_app_info() 提供（单一数据源），
 * 此处仅提供 t() 格式化函数与开发模式兜底文案。
 * ============================================================ */
(function () {
  'use strict';

  const I18N = {
    current: 'zh_CN',
    data: {},
    langNames: {},

    // 开发模式（普通浏览器打开、无后端）时的兜底文案
    fallback: {
      'app.subtitle': 'Extracter',
      'app.splash_subtitle': '立绘提取工具',
      'app.loading': '正在加载...',
      'app.init_failed': '初始化失败：{msg}',
      'app.status.ready': '就绪',
      'left.load_button': '加载游戏目录',
      'left.open_output': '打开输出目录',
      'left.settings': '设置',
      'left.cancel_load': '取消加载',
      'left.load_cancelled': '已取消加载游戏目录',
      'left.char_list_title': '角色列表',
      'left.char_search': '搜索角色…',
      'left.clear_cache': '清除缓存',
      'info.tab_title': '首页',
      // 名片合成（首页卡片；后端未就绪时的兜底文案）
      'np.title': '名片合成',
      'np.desc': '按游戏内规则合成角色名片：姓氏首字用大字号、名字首字用中字号、其余字用小字号。',
      'np.surname': '姓氏',
      'np.given': '名字',
      'np.font': '字体',
      'np.no_font': '未选择字体',
      'np.fonts_empty': '未找到游戏字体，请重新提取素材',
      'np.color_default': '跟随文字颜色',
      'np.color_input_hint': '颜色框支持 #RGB、#RRGGBB、rgb(r,g,b) 或 R,G,B 写法；也可用下方的 R/G/B 数值框精确调整。',
      'np.head_color': '首字颜色',
      'np.bundle_invalid': '所选文件不是名片素材，请选择 general-sprites*.bundle',
      'np.generate': '生成预览',
      'np.rendering': '正在生成…',
      'np.empty_preview': '填写姓名后点击「生成预览」',
      'np.save': '保存 PNG',
      'np.size': '尺寸 {w} × {h}',
      'np.saved': '名片已保存',
      'np.save_failed': '保存失败：{msg}',
      'np.render_failed': '渲染失败：{msg}',
      'np.nothing_to_save': '请先生成预览',
      'np.need_assets': '首次使用需从游戏素材中提取名片底板与字体（自动查找上次打开的游戏目录，找不到时可手动指定）',
      'np.prepare': '一键提取素材',
      'np.searching': '正在自动查找游戏素材…（起点：{path}）',
      'np.importing_bundle': '正在读取所选素材：{name}',
      'np.prepared': '名片素材已就绪',
      'np.prepared_fonts': '名片素材已就绪（顺带提取 {count} 个游戏字体）',
      'np.prepare_failed': '提取失败：{msg}',
      'np.not_found': '未在 {path} 及其上下级目录找到素材',
      'np.not_found_title': '未找到名片素材',
      'np.pick_bundle_title': '选择名片素材 bundle',
      'np.pick_manually': '手动选择…',
      'np.cancel_search': '停止查找',
      'np.search_cancelling': '正在停止查找…',
      'np.search_cancelled': '已停止查找，可重新提取',
      'np.search_path_title': '开始查找素材',
      'np.search_path_lead': '将在下面的位置查找名片素材（先查该目录及其下级，再逐级向上）：',
      'np.search_path_hint': '该位置来自上次打开的游戏目录。如需更换，可点「换一个位置…」，或使用左侧的「加载游戏目录」。',
      'np.search_use_path': '开始查找',
      'np.search_change_path': '换一个位置…',
      'np.hint_lead': '自动查找没能定位到游戏素材。你可以点「手动选择…」直接指定文件，或按下面的位置自行查找：',
      'np.hint_path_label': 'Steam 库文件夹下的位置',
      'np.hint_file_label': '需要选择的文件',
      'np.hint_start': '本次查找起点：{path}',
      'np.hint_searched': '已搜索的位置（{count} 处）',
      'np.need_desktop': '仅桌面版支持文件选择',
      // 通用对话框按钮（正常由后端翻译表的 dialog 段提供，这里兜底，避免无后端时显示键名）
      'dialog.ok': '确定',
      'dialog.cancel': '取消',
      // 首次使用引导（tour.js；无后端时兜底，避免显示键名）
      'tour.title': '使用教学',
      'tour.open': '查看使用教程',
      'tour.replay': '重新观看教程',
      'tour.replay_hint': '选择一个教程播放，逐步了解各功能。',
      'tour.menu_title': '使用教程',
      'tour.menu_desc': '选择一个教程开始播放；播放中可直接在高亮区内跟着操作。',
      'tour.menu_close': '关闭',
      'tour.step': '{cur} / {total}',
      'tour.prev': '上一步',
      'tour.next': '下一步',
      'tour.skip': '跳过',
      'tour.done': '完成',
      'tour.hint': '← → 切换步骤 · Esc 退出',
      'tour.try_hint': '这一区内可以直接操作',
      'tour.extract_title': '合成立绘（主流程）',
      'tour.extract_desc': '两条支路一次讲清：有组件的角色按部件拼合，无组件的角色用精灵预览挑选导出。示例角色：ema（有组件）、creatureema（无组件）。',
      'tour.extract.x1_title': '主流程导览',
      'tour.extract.x1_body': '合成立绘有两条支路：有组件的角色用「拼接角色图像」按部件拼合，无组件的角色用「预览精灵」挑选导出。本教程以 {ema} 和 {creatureema} 为例，高亮区内都可以直接操作。',
      'tour.extract.x2_title': '第一步：加载游戏目录',
      'tour.extract.x2_body': '点击「加载游戏目录」，选中游戏安装目录（或包含 characters 文件夹的目录）。也可以把文件夹直接拖入窗口。',
      'tour.extract.x3_title': '【有组件】选择示例角色',
      'tour.extract.x3_body': '在左侧角色列表点击 {ema} —— 它带有组件数据，是本教程的「有组件」示例。（若列表为空，请先完成上一步加载目录。）',
      'tour.extract.x4_title': '【有组件】选择「拼接角色图像」',
      'tour.extract.x4_body': '点击角色后会弹出「处理方式」对话框。这里请选「拼接角色图像」：按组件的位置与深度合成完整立绘。',
      'tour.extract.x5_title': '勾选部件',
      'tour.extract.x5_body': '进入部件选择后，在左侧列表勾选/取消部件，右侧会立即预览组合效果；也可以搜索部件，或用上方「全选」一次勾上全部部件。',
      'tour.extract.x5b_title': '快速勾选 ClippingMask 部件',
      'tour.extract.x5b_body': '点这个按钮可以一次性勾选全部 ClippingMask 部件（光效、轮廓等叠加层），不必逐个勾选；旁边的 (?) 图标有详细说明。',
      'tour.extract.x6_title': '生成预览 → 保存',
      'tour.extract.x6_body': '调整满意后点「生成合成图像」—— 它按当前勾选生成合成预览（只预览，不写文件）；确认无误再点「保存合成图像」导出 PNG。',
      'tour.extract.x7_title': '【无组件】选择示例角色',
      'tour.extract.x7_body': '回到左侧角色列表，点击 {creatureema} —— 它没有组件数据，无法拼接立绘，是本教程的「无组件」示例。',
      'tour.extract.x8_title': '【无组件】选择「预览精灵」',
      'tour.extract.x8_body': '点击后同样会弹出对话框：选「预览精灵」进入预览模式；选「直接导出全部」则不做预览、把所有精灵一次性导出。这里请点「预览精灵」。',
      'tour.extract.x9_title': '精灵预览：批量选择与导出',
      'tour.extract.x9_body': '顶部工具条中，「全选」勾选全部精灵、「取消选择」清空勾选；「导出选中」只导出勾选的精灵，「导出全部」导出全部。',
      'tour.extract.x10_title': '精灵网格：逐个勾选',
      'tour.extract.x10_body': '在下方的精灵网格里点击精灵即可选中/取消；选中的精灵会打上勾，用「导出选中」即可只导出这些。',
      'tour.extract.x11_title': '导出结果在哪',
      'tour.extract.x11_body': '所有导出的图片都保存在输出目录，点这里随时打开查看；输出目录可在「设置」中更改。',
      'tour.extract.x12_title': '主流程结束',
      'tour.extract.x12_body': '以上就是两条支路：有组件 → 拼接角色图像 → 勾选部件 → 生成/保存合成图像；无组件 → 预览精灵 → 勾选 → 导出选中/导出全部。',
      'tour.nameplate_title': '名片合成',
      'tour.nameplate_desc': '按游戏原版排版合成角色名片：输入姓名、选字体与首字颜色，导出 601×289 PNG。',
      'tour.nameplate.n1_title': '什么是名片合成',
      'tour.nameplate.n1_body': '名片合成按游戏内的排版规则生成角色名片，尺寸 601×289（名字过长会自动加宽画布）。',
      'tour.nameplate.n2_title': '动手试做名片',
      'tour.nameplate.n2_body': '首次使用先点「一键提取素材」准备底板与字体；素材就绪后填好姓名，点「生成预览」，满意再点「保存 PNG」。',
      'tour.nameplate.n3_title': '名片合成结束',
      'tour.nameplate.n3_body': '名片已导出到输出目录的 nameplate 文件夹。随时可从首页打开教程列表重看本教程。',
      'tour.assets_title': '素材提取',
      'tour.assets_desc': '批量提取背景、证物、人物资料、界面与演出图片，按分类勾选后导出原始尺寸 PNG。',
      'tour.assets.a1_title': '素材提取是什么',
      'tour.assets.a1_body': '「素材提取」页会从游戏资源加载背景、CG、证物、人物资料、界面图标与演出包图片，可按分类浏览、搜索并批量导出。',
      'tour.assets.a2_title': '加载素材目录',
      'tour.assets.a2_body': '点击「加载素材目录」，选择游戏根目录或 backgrounds 目录；也可把游戏目录直接拖入窗口。',
      'tour.assets.a3_title': '分类与筛选',
      'tour.assets.a3_body': '用分类下拉切换素材类别，搜索框按名称筛选；「全选当前列表」只选择当前筛选结果。',
      'tour.assets.a4_title': '浏览与勾选',
      'tour.assets.a4_body': '点击素材行查看预览，勾选框只控制是否导出；背景包预览首张图片、导出包内全部图片。',
      'tour.assets.a5_title': '预热与导出',
      'tour.assets.a5_body': '「预热全部」先把所有素材的缩略图缓存好；「导出所选」导出勾选的素材；「打开输出目录」查看结果。',
      'tour.assets.a6_title': '素材提取结束',
      'tour.assets.a6_body': '以上就是素材提取的用法。加载、预览、预热与导出都可以随时取消。',
      'tabs.parts': '部件选择',
      'tabs.hierarchy': '组件层级',
      'parts.select_all': '全选',
      'parts.deselect_all': '取消全选',
      'parts.select_clip': '快速勾选ClippingMask部件',
      'parts.clip_importance': 'ClippingMask 部件是被裁剪进角色区域的叠加层（光效/轮廓等），勾选后才能正确合成；缺失时相关光影效果将不显示。',
      'parts.clip_selected': '已新增 {count} 个 ClippingMask 部件',
      'parts.selected_list_title': '已选精灵',
      'parts.preview_title': '实时预览',
      'parts.auto_update': '自动更新',
      'parts.composite_btn': '生成合成图像',
      'parts.preset_placeholder': '预设…',
      'parts.preset_save': '保存预设',
      'parts.preset_delete': '删除',
      'parts.preset_select_hint': '选择预设以恢复该组合的部件勾选',
      'parts.preset_option': '{name}（{count} 个部件）',
      'parts.preset_applied': '已应用预设「{name}」：选中 {count} 个部件',
      'parts.preset_builtin_name': '「{name}」是内置预设，不能覆盖或重名保存',
      'parts.preset_builtin_readonly': '内置预设不可删除或覆盖',
      'parts.preset_builtin_suffix': '（内置）',
      'parts.preset_export': '导出',
      'parts.preset_export_code_hint': '代码（可直接分享给他人导入）',
      'parts.preset_export_copy': '复制',
      'parts.preset_export_failed': '导出失败',
      'parts.preset_export_json_hint': 'JSON 内容（可保存为文件）',
      'parts.preset_export_save': '保存为文件…',
      'parts.preset_export_saved': '已保存到 {path}',
      'parts.preset_export_title': '导出预设',
      'parts.preset_import': '导入',
      'parts.preset_import_bad_character': '角色标识缺失或未知（{name}）',
      'parts.preset_import_bad_code': '代码格式不正确，应为：游戏标识,角色标识,排序值…',
      'parts.preset_import_bad_file': 'JSON 文件格式不正确或缺少部件数据',
      'parts.preset_import_bad_game': '游戏标识缺失或未知（{name}）',
      'parts.preset_import_char_mismatch': '该预设属于角色「{name}」，请先切换到该角色再导入',
      'parts.preset_import_choose': '选择 JSON 文件…',
      'parts.preset_import_code_hint': '格式：游戏标识,角色标识,排序值…（例：manosaba,hiro,1,52,97）；排序值需与当前角色数据一致',
      'parts.preset_import_code_placeholder': 'manosaba,hiro,1,52,97,130',
      'parts.preset_import_default_name': '导入预设',
      'parts.preset_import_exists': '已存在同名预设「{name}」，确定覆盖吗？',
      'parts.preset_import_failed': '导入预设失败',
      'parts.preset_import_file_hint': '本工具导出的预设 .json 文件，也可直接拖入',
      'parts.preset_import_game_mismatch': '该预设来自其他作品（{name}），无法导入',
      'parts.preset_import_loaded': '已读取 {name}（{count} 个部件）',
      'parts.preset_import_name': '预设名',
      'parts.preset_import_need_code': '请先粘贴预设代码',
      'parts.preset_import_need_file': '请先选择预设文件',
      'parts.preset_import_need_name': '请填写预设名',
      'parts.preset_import_no_file': '尚未选择文件',
      'parts.preset_import_no_match': '代码里的排序值在当前角色数据中找不到对应部件',
      'parts.preset_import_title': '导入预设',
      'parts.preset_imported': '已导入预设「{name}」（{count} 个部件，跳过 {skipped}）',
      'parts.preset_tab_code': '代码',
      'parts.preset_tab_file': '文件',
      'parts.preset_empty': '该预设中的部件在当前角色数据里不存在',
      'parts.preset_need_selection': '请先勾选要保存的部件',
      'parts.preset_name_conflict': '预设名「{name}」与已有预设的文件名冲突，请换一个名称',
      'parts.preset_name_empty': '预设名不能为空',
      'parts.preset_name_hint': '预设名称',
      'parts.preset_name_invalid': '预设名不合法：请使用 1–40 个字符，且不要包含 < > : " / \\ | ? *',
      'parts.preset_name_title': '保存预设',
      'parts.preset_saved': '已保存预设「{name}」（{count} 个部件）',
      'parts.preset_save_failed': '保存预设失败',
      'parts.preset_overwrite_title': '覆盖预设',
      'parts.preset_overwrite_msg': '已存在同名预设「{name}」，确定覆盖吗？',
      'parts.preset_delete_title': '删除预设',
      'parts.preset_delete_msg': '确定删除预设「{name}」吗？该操作不可撤销。',
      'parts.preset_deleted': '已删除预设「{name}」',
      'parts.preset_delete_failed': '删除预设失败',
      'parts.save_composite': '保存合成图',
      'parts.clear_preview': '清空预览',
      'parts.no_preview': '尚无预览',
      'parts.lightbox_hint': '滚轮缩放 · 拖拽平移 · 点击空白处 / Esc 关闭',
      'parts.lightbox_close': '关闭',
      'parts.lightbox_zoom_in': '放大',
      'parts.lightbox_zoom_out': '缩小',
      'parts.lightbox_fit': '适应',
      'parts.lightbox_export': '导出',
      'parts.lightbox_loading': '正在生成预览…',
      'parts.loading_hint': '正在读取角色数据…',
      'preview.lightbox_export_current': '导出当前',
      'parts.empty_hint': '请先在左侧选择一个角色进入拼接模式',
      'hierarchy.hint': '角色组件层级结构',
      'hierarchy.expand_all': '全部展开',
      'hierarchy.collapse_all': '全部折叠',
      'hierarchy.empty_hint': '暂无层级数据',
      'settings.preview_quality_label': '预览画质',
      'settings.preview_quality_hint': '预览以较低分辨率合成以减轻负载；导出始终为原始画质。',
      'settings.hw_accel_label': '禁用硬件加速',
      'settings.hw_accel_hint': '改用软件渲染，显卡异常/卡顿时可尝试；需重启程序生效。',
      'settings.hw_accel_restart_title': '需要重启',
      'settings.hw_accel_restart_msg': '硬件加速设置已保存，需要重启程序后才能生效。是否立即重启？',
      'settings.hw_accel_restart_now': '立即重启',
      'settings.hw_accel_restart_later': '稍后',
      'settings.export_original_label': '导出原始画质图像',
      'settings.export_original_hint': '关闭后导出的图像与预览画质一致（体积更小、更省资源）。',
      'settings.disable_animations_label': '禁用界面动画',
      'settings.disable_animations_hint': '关闭淡入/过渡等动画，低配设备更流畅；立即生效。',
      'settings.auto_find_characters_label': '自动查找 characters 目录',
      'settings.auto_find_characters_hint': '开启后选择游戏目录即可自动定位 characters 目录；关闭时需手动选择 characters 目录（直接包含角色 .bundle 文件的文件夹）。',
      'parts.preview_quality_label': '预览画质',
      'about.contrib_title': '贡献者',
      'about.contrib_role_contributor': '贡献者',
      'about.contrib_rf_desc': '「素材提取」页：背景与小素材的提取与导出',
      'about.contrib_role_original': '技术致谢 · 原项目作者',
      'about.contrib_lk_desc': 'KabeNaki 项目作者，本项目的重构基础',
      'about.sys_title': '系统信息',
      'about.sys_loading': '正在获取系统信息...',
      'about.sys_cpu': 'CPU: {model}（{cores} 核 · {speed} GHz）',
      'about.sys_mem': '内存: {mem} GB',
      'about.sys_gpu': '显卡: {name}（显存 {vram} GB）',
      'about.sys_gpu_name': '显卡: {name}',
      'about.sys_os': '系统: {os}（{arch}）',
    },

    /**
     * 设置翻译数据并刷新页面文案
     * @param {object} data      完整翻译模板表 { key: template }
     * @param {string} lang      当前语言代码
     * @param {object} langNames { code: 显示名 }
     */
    set(data, lang, langNames) {
      if (lang) this.current = lang;
      if (langNames) this.langNames = langNames;
      if (data) this.data = data;
      // 同步 document 语言标记（供 CSS 按语言切换字体等，如日语用 TsukushiMincho）
      if (this.current) document.documentElement.lang = this.current;
      this.applyDom();
    },

    /**
     * 取翻译文本，支持 {name} 占位符
     * @param {string} key    翻译键
     * @param {object} params 格式化参数
     */
    t(key, params) {
      let tpl = (key in this.data) ? this.data[key]
        : (key in this.fallback) ? this.fallback[key] : key;
      if (params) {
        tpl = tpl.replace(/\{(\w+)\}/g, (m, k) =>
          (k in params) ? String(params[k]) : m);
      }
      return tpl;
    },

    /** 将 data-i18n 应用到整个文档（只作用于叶子元素，避免破坏 SVG 图标） */
    applyDom() {
      const isLeaf = (el) => el.querySelectorAll('*').length === 0;
      document.querySelectorAll('[data-i18n]').forEach((el) => {
        if (!isLeaf(el)) return;
        el.textContent = this.t(el.getAttribute('data-i18n'));
      });
      document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
        el.setAttribute('placeholder', this.t(el.getAttribute('data-i18n-placeholder')));
      });
      // 悬停提示统一走自定义气泡（ui.js 的全局委托监听 data-tip），因此写入 data-tip；
      // 同时移除原生 title，避免系统气泡与自定义气泡同时出现（样式不一致）
      document.querySelectorAll('[data-i18n-title], [data-i18n-tip]').forEach((el) => {
        const key = el.getAttribute('data-i18n-title') || el.getAttribute('data-i18n-tip');
        el.setAttribute('data-tip', this.t(key));
        el.removeAttribute('title');
      });
      // aria-label（无障碍）：与悬停提示同源，语言切换后一并刷新
      document.querySelectorAll('[data-i18n-aria]').forEach((el) => {
        el.setAttribute('aria-label', this.t(el.getAttribute('data-i18n-aria')));
      });
    },
  };

  window.I18N = I18N;
})();
