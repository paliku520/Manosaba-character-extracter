/* ============================================================
 * settings.js — 设置面板（外观 / 显示 / 数据）、主题、预览画质、语言切换
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * 说明：主题色下拉与通用下拉的互斥注册表已下沉到 ui.js（MCE.dropdown）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, api, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const toast = (...a) => MCE.toast(...a);
  const btn = (...a) => MCE.btn(...a);
  const showModal = (...a) => MCE.showModal(...a);
  const confirmDialog = (...a) => MCE.confirmDialog(...a);
  const setStatus = (...a) => MCE.setStatus(...a);
  const refreshExportCount = (...a) => MCE.refreshExportCount(...a);
  const createDropdown = (...a) => MCE.createDropdown(...a);
  const tipIcon = (...a) => MCE.tipIcon(...a);
  const moveTabIndicator = (...a) => MCE.moveTabIndicator(...a);
  const updateTitleBar = (...a) => MCE.updateTitleBar(...a);
  const renderCharList = (...a) => MCE.renderCharList(...a);
  const refreshNameDisplay = (...a) => MCE.refreshNameDisplay(...a);
  const renderParts = (...a) => MCE.renderParts(...a);
  const updateSelUI = (...a) => MCE.updateSelUI(...a);
  const refreshPartsHeader = (...a) => MCE.refreshPartsHeader(...a);
  const renderHierarchy = (...a) => MCE.renderHierarchy(...a);
  const renderPreviewGrid = (...a) => MCE.renderPreviewGrid(...a);
  const applyPreviewZoom = (...a) => MCE.applyPreviewZoom(...a);
  const renderInfoPage = (...a) => MCE.renderInfoPage(...a);
  const renderAboutPage = (...a) => MCE.renderAboutPage(...a);

  // ═════════════ 主题 ═════════════

  // 主题：底色（dark/light）+ 主题色（accent，default=默认绿）。
  // settings.json 为唯一权威（后端 get_app_info 读取），不写/不读 localStorage。
  function applyTheme(theme, accent) {
    if (theme) document.documentElement.dataset.theme = theme;
    const acc = accent || 'default';
    document.documentElement.dataset.accent = acc;
  }

  // 禁用/启用界面动画（低配 GPU 提速；纯前端 CSS，立即生效）
  function applyAnimations(disable) {
    document.body.classList.toggle('no-anim', !!disable);
  }

  // ═════════════ 设置窗口 ═════════════

  // 主题色选项（值 + i18n 键）与色值映射
  const ACCENTS = [
    ['default', 'settings.accent_default'],
    ['alisa', 'settings.accent_alisa'],
    ['anan', 'settings.accent_anan'],
    ['coco', 'settings.accent_coco'],
    ['ema', 'settings.accent_ema'],
    ['hanna', 'settings.accent_hanna'],
    ['hiro', 'settings.accent_hiro'],
    ['jailer', 'settings.accent_jailer'],
    ['leia', 'settings.accent_leia'],
    ['margo', 'settings.accent_margo'],
    ['meruru', 'settings.accent_meruru'],
    ['miria', 'settings.accent_miria'],
    ['nanoka', 'settings.accent_nanoka'],
    ['noah', 'settings.accent_noah'],
    ['sherry', 'settings.accent_sherry'],
    ['warden', 'settings.accent_warden'],
    ['yuki', 'settings.accent_yuki'],
  ];
  const ACCENT_COLORS = {
    default: '#35d07f',
    alisa: '#EA4D3E', anan: '#9D97F9', coco: '#F77449', ema: '#FF8FB4',
    hanna: '#A7CB1E', hiro: '#F84F5A', jailer: '#C5C9D4', leia: '#FDB95B',
    margo: '#B87BF0', meruru: '#E2BFB8', miria: '#EFD28D', nanoka: '#84909A',
    noah: '#65E4EB', sherry: '#89B5FA', warden: '#B3B1C5', yuki: '#C3D4ED',
  };

  let settingsLangDropdown = null;    // 设置弹窗语言下拉引用（语言切换后刷新）
  let settingsThemeDropdown = null;   // 设置弹窗主题下拉引用

  // 主题色自定义下拉：选项左侧带颜色小方块
  function createAccentPicker({ value }) {
    const wrap = document.createElement('div');
    wrap.className = 'color-picker';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'color-picker-btn';
    const swatch = document.createElement('span');
    swatch.className = 'cp-swatch';
    const label = document.createElement('span');
    label.className = 'cp-label';
    const caret = document.createElement('span');
    caret.className = 'cp-caret';
    caret.innerHTML =
      '<svg viewBox="0 0 16 16" width="12" height="12"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
    btn.appendChild(swatch); btn.appendChild(label); btn.appendChild(caret);
    wrap.appendChild(btn);

    const list = document.createElement('div');
    list.className = 'color-picker-list';
    const items = {};
    ACCENTS.forEach(([v, key]) => {
      const it = document.createElement('button');
      it.type = 'button';
      it.className = 'color-picker-item';
      it.dataset.value = v;
      const sw = document.createElement('span');
      sw.className = 'cp-swatch';
      sw.style.background = ACCENT_COLORS[v] || '#888';
      const nm = document.createElement('span');
      nm.className = 'cp-name';
      nm.setAttribute('data-i18n', key);
      nm.textContent = t(key);
      it.appendChild(sw); it.appendChild(nm);
      it.addEventListener('click', () => {
        api.value = v;
        api.closeList();
        wrap.focus();
      });
      list.appendChild(it);
      items[v] = it;
    });
    wrap.appendChild(list);

    let current = value;
    // 打开时让下拉以视口为准 fixed 定位，避免被 .sn-panels 等带 overflow 的父级裁剪
    const onScroll = () => api.positionList();
    const onResize = () => api.positionList();
    const api = {
      el: wrap,
      get value() { return current; },
      set value(v) {
        if (!(v in items)) return;
        current = v;
        const key = (ACCENTS.find((o) => o[0] === v) || [])[1] || '';
        swatch.style.background = ACCENT_COLORS[v] || '#888';
        label.setAttribute('data-i18n', key);
        label.textContent = t(key);
        Object.keys(items).forEach((k) => items[k].classList.toggle('selected', k === v));
        if (api.onChange) api.onChange(v);
      },
      onChange: null,
      positionList() {
        const rect = btn.getBoundingClientRect();
        const gap = 4;
        const listH = list.offsetHeight || 0;
        const spaceBelow = window.innerHeight - rect.bottom - gap;
        let top = rect.bottom + gap;
        if (spaceBelow < listH && rect.top - gap > spaceBelow) {
          top = Math.max(gap, rect.top - listH - gap); // 底部空间不足时向上展开
        }
        list.style.position = 'fixed';
        list.style.left = rect.left + 'px';
        list.style.top = top + 'px';
        list.style.right = 'auto';
        list.style.width = rect.width + 'px';
        list.style.maxHeight = Math.min(220, window.innerHeight - 2 * gap) + 'px';
      },
      openList() {
        MCE.dropdown.setActive(api);
        document.body.appendChild(list);   // portal 到 body，脱离所有 overflow/transform 裁剪
        list.style.zIndex = '1000';        // 高于 modal-root(100)/toast(200)/彩蛋(300)，避免被弹窗盖住
        api.positionList();
        // 强制 reflow：先渲染隐藏初始态，加 .open 才有过渡起始帧（否则同帧移动+改态无动画）
        void list.offsetWidth;
        list.classList.add('open');
        // 面板滚动 / 窗口尺寸变化时保持下拉与按钮对齐（capture 捕获内部滚动）
        document.addEventListener('scroll', onScroll, true);
        window.addEventListener('resize', onResize);
      },
      closeList() {
        list.classList.remove('open');
        if (list.parentNode !== wrap) wrap.appendChild(list);  // 移回原位
        document.removeEventListener('scroll', onScroll, true);
        window.removeEventListener('resize', onResize);
      },
    };
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      if (list.classList.contains('open')) api.closeList();
      else api.openList();
    });
    wrap.addEventListener('keydown', (e) => { if (e.key === 'Escape') api.closeList(); });
    api.value = value; // 初始化显示
    return api;
  }

  function openSettings() {
    const body = document.createElement('div');
    // 设置分区：外观 / 显示 / 数据
    const settingsSection = (titleKey) => {
      const sec = document.createElement('div');
      sec.className = 'settings-section';
      const h = document.createElement('div');
      h.className = 'settings-section-title';
      h.setAttribute('data-i18n', titleKey);
      h.textContent = t(titleKey);
      sec.appendChild(h);
      return sec;
    };
    const secAppearance = settingsSection('settings.section_appearance');
    const secDisplay = settingsSection('settings.section_display');
    const secData = settingsSection('settings.section_data');

    const outRow = document.createElement('div');
    outRow.className = 'form-row';
    const outLabel = document.createElement('label');
    outLabel.setAttribute('data-i18n', 'settings.output_dir_label');
    outLabel.textContent = t('settings.output_dir_label');
    outRow.appendChild(outLabel);
    const outField = document.createElement('div');
    outField.className = 'field-row';
    outField.innerHTML =
      '<input type="text" id="set-output">' +
      '<button class="btn sm" id="set-browse" data-i18n="settings.browse"></button>' +
      '<button class="btn sm ghost" id="set-restore" data-i18n="settings.restore_default"></button>';
    outField.querySelector('#set-output').value = App.info.output_dir || '';
    outField.querySelector('#set-browse').textContent = t('settings.browse');
    outField.querySelector('#set-restore').textContent = t('settings.restore_default');
    outRow.appendChild(outField);

    const langRow = document.createElement('div');
    langRow.className = 'form-row';
    const langLabel = document.createElement('label');
    const langLabelText = document.createElement('span');
    langLabelText.setAttribute('data-i18n', 'lang.label');
    langLabelText.textContent = t('lang.label');
    langLabel.appendChild(langLabelText);
    // AI 翻译免责声明改为悬停图标提示（不再整段铺开）
    langLabel.appendChild(tipIcon('settings.lang_ai_note'));
    langRow.appendChild(langLabel);
    const langDropdown = createDropdown({
      options: (App.info.langs || []).map((code) => ({
        value: code,
        label: (App.info.lang_names && App.info.lang_names[code]) || code,
      })),
      value: App.info.current_lang,
    });
    settingsLangDropdown = langDropdown;
    langRow.appendChild(langDropdown.el);

    const themeRow = document.createElement('div');
    themeRow.className = 'form-row';
    const themeLabel = document.createElement('label');
    themeLabel.setAttribute('data-i18n', 'settings.theme_label');
    themeLabel.textContent = t('settings.theme_label');
    themeRow.appendChild(themeLabel);
    const themeDropdown = createDropdown({
      options: [
        { value: 'dark', label: t('settings.theme_dark') },
        { value: 'light', label: t('settings.theme_light') },
      ],
      value: document.documentElement.dataset.theme || 'dark',
    });
    settingsThemeDropdown = themeDropdown;
    themeRow.appendChild(themeDropdown.el);

    const accentRow = document.createElement('div');
    accentRow.className = 'form-row';
    const accentLabel = document.createElement('label');
    accentLabel.setAttribute('data-i18n', 'settings.accent_label');
    accentLabel.textContent = t('settings.accent_label');
    accentRow.appendChild(accentLabel);
    const accentPicker = createAccentPicker({ value: document.documentElement.dataset.accent || App.info.accent || 'default' });
    accentRow.appendChild(accentPicker.el);

    const nameRow = document.createElement('div');
    nameRow.className = 'form-row';
    nameRow.id = 'original-name-row';
    const nameSwitch = document.createElement('label');
    nameSwitch.className = 'switch';
    const nameCb = document.createElement('input');
    nameCb.type = 'checkbox';
    nameCb.id = 'set-show-original';
    const slider = document.createElement('span');
    slider.className = 'slider';
    const nameText = document.createElement('span');
    nameText.setAttribute('data-i18n', 'settings.original_name_label');
    nameText.textContent = t('settings.original_name_label');
    nameSwitch.appendChild(nameCb);
    nameSwitch.appendChild(slider);
    nameSwitch.appendChild(nameText);
    nameRow.appendChild(nameSwitch);

    const debugRow = document.createElement('div');
    debugRow.className = 'form-row';
    debugRow.id = 'debug-monitor-row';
    const debugSwitch = document.createElement('label');
    debugSwitch.className = 'switch';
    const debugCb = document.createElement('input');
    debugCb.type = 'checkbox';
    debugCb.id = 'set-debug-monitor';
    const debugSlider = document.createElement('span');
    debugSlider.className = 'slider';
    const debugText = document.createElement('span');
    debugText.setAttribute('data-i18n', 'settings.debug_label');
    debugText.textContent = t('settings.debug_label');
    debugSwitch.appendChild(debugCb);
    debugSwitch.appendChild(debugSlider);
    debugSwitch.appendChild(debugText);
    debugRow.appendChild(debugSwitch);

    // 禁用硬件加速（UI 渲染，需重启生效）
    const hwRow = document.createElement('div');
    hwRow.className = 'form-row';
    hwRow.id = 'hw-accel-row';
    const hwSwitch = document.createElement('label');
    hwSwitch.className = 'switch';
    const hwCb = document.createElement('input');
    hwCb.type = 'checkbox';
    hwCb.id = 'set-hw-accel';
    const hwSlider = document.createElement('span');
    hwSlider.className = 'slider';
    const hwText = document.createElement('span');
    hwText.setAttribute('data-i18n', 'settings.hw_accel_label');
    hwText.textContent = t('settings.hw_accel_label');
    hwSwitch.appendChild(hwCb);
    hwSwitch.appendChild(hwSlider);
    hwSwitch.appendChild(hwText);
    hwSwitch.appendChild(tipIcon('settings.hw_accel_hint'));
    hwRow.appendChild(hwSwitch);

    // 禁用界面动画（低配 GPU 提速；纯前端 CSS，立即生效，无需重启）
    const animRow = document.createElement('div');
    animRow.className = 'form-row';
    animRow.id = 'anim-row';
    const animSwitch = document.createElement('label');
    animSwitch.className = 'switch';
    const animCb = document.createElement('input');
    animCb.type = 'checkbox';
    animCb.id = 'set-anim';
    const animSlider = document.createElement('span');
    animSlider.className = 'slider';
    const animText = document.createElement('span');
    animText.setAttribute('data-i18n', 'settings.disable_animations_label');
    animText.textContent = t('settings.disable_animations_label');
    animSwitch.appendChild(animCb);
    animSwitch.appendChild(animSlider);
    animSwitch.appendChild(animText);
    animSwitch.appendChild(tipIcon('settings.disable_animations_hint'));
    animRow.appendChild(animSwitch);

    // 显示更新内容（更新弹窗中的 Release 说明；默认开启，可在弹窗内关闭）
    const relNotesRow = document.createElement('div');
    relNotesRow.className = 'form-row';
    relNotesRow.id = 'release-notes-row';
    const relNotesSwitch = document.createElement('label');
    relNotesSwitch.className = 'switch';
    const relNotesCb = document.createElement('input');
    relNotesCb.type = 'checkbox';
    relNotesCb.id = 'set-release-notes';
    const relNotesSlider = document.createElement('span');
    relNotesSlider.className = 'slider';
    const relNotesText = document.createElement('span');
    relNotesText.setAttribute('data-i18n', 'settings.release_notes_label');
    relNotesText.textContent = t('settings.release_notes_label');
    relNotesSwitch.appendChild(relNotesCb);
    relNotesSwitch.appendChild(relNotesSlider);
    relNotesSwitch.appendChild(relNotesText);
    relNotesSwitch.appendChild(tipIcon('settings.release_notes_hint'));
    relNotesRow.appendChild(relNotesSwitch);

    // 自动查找 characters 目录（关闭后需手动指定 characters 目录）
    const autoFindRow = document.createElement('div');
    autoFindRow.className = 'form-row';
    autoFindRow.id = 'auto-find-row';
    const autoFindSwitch = document.createElement('label');
    autoFindSwitch.className = 'switch';
    const autoFindCb = document.createElement('input');
    autoFindCb.type = 'checkbox';
    autoFindCb.id = 'set-auto-find';
    const autoFindSlider = document.createElement('span');
    autoFindSlider.className = 'slider';
    const autoFindText = document.createElement('span');
    autoFindText.setAttribute('data-i18n', 'settings.auto_find_characters_label');
    autoFindText.textContent = t('settings.auto_find_characters_label');
    autoFindSwitch.appendChild(autoFindCb);
    autoFindSwitch.appendChild(autoFindSlider);
    autoFindSwitch.appendChild(autoFindText);
    autoFindSwitch.appendChild(tipIcon('settings.auto_find_characters_hint'));
    autoFindRow.appendChild(autoFindSwitch);

    const actionRow = document.createElement('div');
    actionRow.className = 'form-row';
    actionRow.style.flexDirection = 'row';
    actionRow.style.flexWrap = 'wrap';
    actionRow.innerHTML =
      '<button class="btn sm" id="set-check-update" data-i18n="left.check_update"></button>' +
      '<button class="btn sm ghost" id="set-clear-cache" data-i18n="settings.clear_cache_btn"></button>' +
      '<button class="btn sm ghost" id="set-clear-output" data-i18n="settings.clear_output_btn"></button>' +
      '<button class="btn sm ghost" id="set-clear-log" data-i18n="settings.clear_log_btn"></button>';
    actionRow.querySelector('#set-check-update').textContent = t('left.check_update');
    actionRow.querySelector('#set-clear-cache').textContent = t('settings.clear_cache_btn');
    actionRow.querySelector('#set-clear-output').textContent = t('settings.clear_output_btn');
    actionRow.querySelector('#set-clear-log').textContent = t('settings.clear_log_btn');

    // 外观：主题（深/浅）/ 主题色 / 语言
    secAppearance.appendChild(themeRow);
    secAppearance.appendChild(accentRow);
    secAppearance.appendChild(langRow);
    // 显示：显示原始文件名 / 调试模式 / 禁用硬件加速 / 禁用界面动画 / 显示更新内容
    secDisplay.appendChild(nameRow);
    secDisplay.appendChild(debugRow);
    secDisplay.appendChild(hwRow);
    secDisplay.appendChild(animRow);
    secDisplay.appendChild(relNotesRow);
    // 数据：输出目录 / 自动查找 characters / 维护操作
    secData.appendChild(outRow);
    secData.appendChild(autoFindRow);
    secData.appendChild(actionRow);

    // 设置分区用 notebook（页签）划分：外观 / 显示 / 数据，竖版排版（一次只显示一个分区）
    const notebook = document.createElement('div');
    notebook.className = 'settings-notebook';
    const snTabs = document.createElement('div');
    snTabs.className = 'sn-tabs';
    const snPanels = document.createElement('div');
    snPanels.className = 'sn-panels';

    const sections = [
      { title: 'settings.section_appearance', el: secAppearance },
      { title: 'settings.section_display', el: secDisplay },
      { title: 'settings.section_data', el: secData },
    ];
    function setSnTab(idx) {
      snTabs.querySelectorAll('.sn-tab').forEach((b, i) => b.classList.toggle('active', i === idx));
      snPanels.querySelectorAll('.sn-panel').forEach((p, i) => p.classList.toggle('active', i === idx));
    }
    sections.forEach((s, i) => {
      const tb = document.createElement('button');
      tb.type = 'button';
      tb.className = 'sn-tab' + (i === 0 ? ' active' : '');
      tb.setAttribute('data-i18n', s.title);
      tb.textContent = t(s.title);
      tb.addEventListener('click', () => setSnTab(i));
      snTabs.appendChild(tb);
      const panel = document.createElement('div');
      panel.className = 'sn-panel' + (i === 0 ? ' active' : '');
      panel.appendChild(s.el);
      snPanels.appendChild(panel);
    });
    notebook.appendChild(snTabs);
    notebook.appendChild(snPanels);
    body.appendChild(notebook);

    const footer = document.createElement('div');
    const closeBtn = btn('', 'btn sm', null);
    closeBtn.setAttribute('data-i18n', 'dialog.close');
    closeBtn.textContent = t('dialog.close');
    footer.appendChild(closeBtn);
    // settings-modal：固定高度 + 页签常驻（内容在分区面板内滚动）
    const { close } = showModal({ titleKey: 'settings.title', body, footer, className: 'settings-modal' });
    closeBtn.addEventListener('click', close);

    themeDropdown.onChange = (v) => {
      applyTheme(v, accentPicker.value);
      if (api()) api().set_theme(v); // 持久化到 settings.json
    };

    accentPicker.onChange = (v) => {
      applyTheme(themeDropdown.value, v);
      App.info.accent = v;              // 同步记忆，重新打开设置时正确回显
      if (api()) api().set_accent(v);   // 持久化到 settings.json
    };

    // 默认显示本地化角色名，勾选“显示原始文件名”后显示原始文件名
    nameCb.checked = App.showOriginalName;
    nameCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_show_original_name(nameCb.checked);
      App.showOriginalName = !!r.show_original_name;
      refreshNameDisplay();
    });

    debugCb.checked = App.debugMode;
    debugCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_debug(debugCb.checked);
      App.debugMode = !!r.debug;
      // 关闭调试时隐藏标题栏资源信息
      if (!App.debugMode) {
        const el = $('#tb-res');
        if (el) el.hidden = true;
      }
      // Electron 模式：开启调试时弹出 cmd 风格日志控制台窗口
      if (App.debugMode && window.__electron && window.__electron.openLogConsole) {
        window.__electron.openLogConsole();
      }
    });

    // 禁用硬件加速（需重启生效）：改动后弹窗询问是否立即重启
    hwCb.checked = !!App.info.disable_hardware_accel;
    hwCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_disable_hardware_accel(hwCb.checked);
      App.info.disable_hardware_accel = !!r.disable_hardware_accel;
      const yes = await confirmDialog(
        t('settings.hw_accel_restart_title'),
        t('settings.hw_accel_restart_msg'),
        t('settings.hw_accel_restart_now'),
        t('settings.hw_accel_restart_later')
      );
      if (yes && window.__electron && window.__electron.restart) {
        window.__electron.restart();
      }
    });

    // 禁用界面动画（立即生效，无需重启）
    animCb.checked = !!App.info.disable_animations;
    animCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_disable_animations(animCb.checked);
      App.info.disable_animations = !!r.disable_animations;
      applyAnimations(!!r.disable_animations);
    });

    // 显示更新内容（检查更新发现新版本时，在弹窗中展示 Release 更新说明；默认开启）
    relNotesCb.checked = App.info.show_release_notes !== false;
    relNotesCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_show_release_notes(relNotesCb.checked);
      App.info.show_release_notes = !!r.show_release_notes;
      App.showReleaseNotes = App.info.show_release_notes;
    });

    // 自动查找 characters 目录（下次加载生效）
    autoFindCb.checked = !!App.info.auto_find_characters;
    autoFindCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_auto_find_characters(autoFindCb.checked);
      App.info.auto_find_characters = !!r.auto_find_characters;
    });

    outField.querySelector('#set-browse').addEventListener('click', async () => {
      const p = await api().select_output_dir();
      if (!p) return;
      const r = await api().set_output_dir(p);
      outField.querySelector('#set-output').value = r.output_dir;
      App.info.output_dir = r.output_dir;
      toast(t('app.status.settings_saved', { path: r.output_dir }), 'success');
    });
    outField.querySelector('#set-restore').addEventListener('click', async () => {
      const r = await api().set_output_dir('');
      outField.querySelector('#set-output').value = r.output_dir;
      App.info.output_dir = r.output_dir;
      toast(t('app.status.settings_saved', { path: r.output_dir }), 'success');
    });
    outField.querySelector('#set-output').addEventListener('change', async (e) => {
      const r = await api().set_output_dir(e.target.value.trim());
      App.info.output_dir = r.output_dir;
      toast(t('app.status.settings_saved', { path: r.output_dir }), 'success');
    });

    langDropdown.onChange = async (v) => {
      try {
        const r = await api().set_lang(v);
        window.I18N.set(r.translations, r.current_lang, r.lang_names);
        App.info.current_lang = r.current_lang;
        App.info.lang_names = r.lang_names;
        // 各界面独立刷新（某一步异常不中断其余），错误经 log_js 输出到日志便于定位
        const steps = [
          ['refreshSettingsModal', refreshSettingsModal],
          ['renderInfoPage', renderInfoPage],
          ['renderAboutPage', renderAboutPage],
          ['renderCharList', renderCharList],
          ['renderParts', () => { if (App.characterData) renderParts(App.characterData); }],
          ['renderHierarchy', () => { if (App.characterData) renderHierarchy(App.characterData.hierarchy); }],
          ['renderPreviewGrid', () => { if (App.previewData && App.previewData.length) renderPreviewGrid(); }],
          ['updateSelUI', updateSelUI],
          ['refreshPartsHeader', refreshPartsHeader],
          ['refreshNameDisplay', refreshNameDisplay],
          ['moveTabIndicator', moveTabIndicator],
          ['updateTitleBar', updateTitleBar],
          ['refreshExportCount', refreshExportCount],
          ['applyPreviewZoom', () => { if (App.previewSize) applyPreviewZoom(); }],
        ];
        steps.forEach(([name, fn]) => {
          try { fn(); } catch (e) {
            console.error('[lang] step "' + name + '" failed: ' + (e && e.message ? e.message : e));
          }
        });
        setStatus(t('app.status.ready'), false);
        toast(t('app.status.ready'), 'success');
      } catch (e) {
        console.error('[lang] set_lang failed: ' + (e && e.message ? e.message : e));
      }
    };

    actionRow.querySelector('#set-check-update').addEventListener('click', () => {
      setStatus(t('app.status.checking_update'), true);
      api().check_update(false);
    });
    actionRow.querySelector('#set-clear-cache').addEventListener('click', async () => {
      const okc = await confirmDialog(
        t('left.clear_cache_confirm_title'), t('left.clear_cache_confirm_msg'));
      if (okc) api().clear_cache();
    });
    actionRow.querySelector('#set-clear-output').addEventListener('click', async () => {
      const okc = await confirmDialog(
        t('settings.clear_output_confirm_title'),
        t('settings.clear_output_confirm_msg', { path: App.info.output_dir }));
      if (okc) api().clear_output();
    });
    actionRow.querySelector('#set-clear-log').addEventListener('click', async () => {
      const okc = await confirmDialog(
        t('settings.clear_log_confirm_title'), t('settings.clear_log_confirm_msg'));
      if (okc) api().clear_log();
    });
  }

  // 语言切换后刷新已打开的设置模态框文本
  function refreshSettingsModal() {
    // 语言下拉选项使用最新的 lang_names（动态语言名，非固定翻译键）
    if (settingsLangDropdown) {
      settingsLangDropdown.refreshLabels((code) =>
        (App.info.lang_names && App.info.lang_names[code]) || code);
    }
    // 主题下拉文本随语言刷新
    if (settingsThemeDropdown) {
      settingsThemeDropdown.refreshLabels((v) =>
        v === 'light' ? t('settings.theme_light') : t('settings.theme_dark'));
    }
    // 其余带 data-i18n 的文本（标题/标签/按钮/主题选项）统一刷新
    window.I18N.applyDom();
  }

  // 构建预览画质下拉（与设置同款 createDropdown）；onApply 在切换后回调
  function _buildPreviewQualityDropdown(slot, onApply) {
    if (!slot) return null;
    const dd = createDropdown({
      options: [100, 75, 50, 25].map((v) => ({ value: String(v), label: v + '%' })),
      value: String(App.info.preview_quality != null ? App.info.preview_quality : 100),
    });
    slot.appendChild(dd.el);
    dd.onChange = async (v) => {
      if (!api()) return;
      const r = await api().set_preview_quality(parseInt(v, 10) || 100);
      App.info.preview_quality = r.preview_quality;
      if (onApply) onApply(r.preview_quality);
    };
    return dd;
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.applyTheme = applyTheme;
  MCE.applyAnimations = applyAnimations;
  MCE.createAccentPicker = createAccentPicker;
  MCE.openSettings = openSettings;
  MCE.refreshSettingsModal = refreshSettingsModal;
  MCE.buildPreviewQualityDropdown = _buildPreviewQualityDropdown;
})();
