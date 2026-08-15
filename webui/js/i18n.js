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
