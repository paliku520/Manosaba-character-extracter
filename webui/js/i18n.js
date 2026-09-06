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
      'app.status.ready': '就绪',
      'left.load_button': '加载游戏目录',
      'left.open_output': '打开输出目录',
      'left.settings': '设置',
      'left.char_list_title': '角色列表',
      'left.char_search': '搜索角色…',
      'left.clear_cache': '清除缓存',
      'info.tab_title': '首页',
      'tabs.parts': '部件选择',
      'tabs.hierarchy': '组件层级',
      'parts.select_all': '全选',
      'parts.deselect_all': '取消全选',
      'parts.select_clip': '快速勾选ClippingMask部件',
      'parts.clip_importance': 'ClippingMask 部件是被裁剪进角色区域的叠加层（光效/轮廓等），勾选后才能正确合成；缺失时相关光影效果将不显示。',
      'parts.clip_selected': '已勾选 {count} 个 ClippingMask 部件',
      'parts.selected_list_title': '已选精灵',
      'parts.preview_title': '实时预览',
      'parts.auto_update': '自动更新',
      'parts.composite_btn': '生成合成图像',
      'parts.save_composite': '保存合成图',
      'parts.clear_preview': '清空预览',
      'parts.no_preview': '尚无预览',
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
      document.querySelectorAll('[data-i18n-title]').forEach((el) => {
        el.setAttribute('title', this.t(el.getAttribute('data-i18n-title')));
      });
    },
  };

  window.I18N = I18N;
})();
