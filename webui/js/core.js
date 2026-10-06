/* ============================================================
 * core.js — 全局状态（App）/ 工具函数 / 初始化入口 / 全部事件绑定
 *
 * 【加载顺序约定】本文件必须最先加载：
 *   其余模块头部会 `const { $, $$, t, api, escapeHtml, fmt, App } = window.MCE;`
 *   并把跨模块函数写成转发别名（晚绑定），因此只要求本文件先于它们执行。
 *   index.html 的 script 顺序：i18n.js → core.js → …各模块… → events.js
 *
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;

  // ── 工具 ────────────────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));
  const t = (k, p) => window.I18N.t(k, p);
  const api = () => (window.pywebview ? window.pywebview.api : null);
  const escapeHtml = (s) => String(s == null ? '' : s).replace(/[&<>"']/g,
    (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmt = (n) => (Number.isInteger(n) ? String(n) : Number(n).toFixed(1));

  // 将前端 console 输出转发到 Python 控制台（标注 [JS] 来源，与 Python 日志区分）
  (function () {
    const _levels = { log: 'info', info: 'info', warn: 'warning', error: 'error', debug: 'debug' };
    const _send = (level, args) => {
      const apiObj = window.pywebview && window.pywebview.api;
      if (!apiObj || !apiObj.log_js) return;
      let msg = '';
      try {
        msg = Array.from(args).map((a) => {
          if (typeof a === 'string') return a;
          try { return JSON.stringify(a); } catch (e) { return String(a); }
        }).join(' ');
      } catch (e) { msg = String(args); }
      try { apiObj.log_js(_levels[level] || 'info', msg); } catch (e) { /* ignore */ }
    };
    ['log', 'info', 'warn', 'error', 'debug'].forEach((m) => {
      const orig = console[m];
      console[m] = function () { _send(m, arguments); orig.apply(console, arguments); };
    });
  })();

  // 禁用原生图片拖拽：拖动 logo / 部件缩略图会拖出半透明“拖影”，观感像 bug。
  // 预览图的平移是自实现的（mousedown 拖拽），不依赖 HTML5 拖拽，因此可以全局禁用。
  document.addEventListener('dragstart', (e) => {
    if (e.target && e.target.tagName === 'IMG') e.preventDefault();
  });

  // 复制文本到剪贴板（优先 Clipboard API，回退 execCommand），成功后 toast 提示
  function copyText(text) {
    const done = () => toast(t('app.copied', { text }), 'success');
    const fallback = () => {
      try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.style.cssText = 'position:fixed;top:0;left:0;opacity:0;pointer-events:none';
        document.body.appendChild(ta);
        ta.focus(); ta.select();
        const ok = document.execCommand('copy');
        ta.remove();
        if (ok) done();
      } catch (e) { /* ignore */ }
    };
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(done, fallback);
    } else {
      fallback();
    }
  }

  const App = {
    info: null,
    bundles: {},             // {角色名: bundle路径}
    currentName: null,
    characterData: null,     // { transform_data, hierarchy }
    thumbnails: {},          // {部件名: dataURL}
    selected: new Set(),     // 已选部件名
    autoUpdate: true,
    previewTimer: null,
    lastStatus: '',
    partEls: {},             // {部件名: {cb, thumb}}
    hierarchyNav: { expand: [], collapse: [] },
    previewSize: null,       // 当前预览合成图实际尺寸 [w, h]
    exportCount: 0,          // 累计导出精灵数（来自后端 settings.json）
    showOriginalName: false,  // 是否显示原始文件名（设置中调节；默认显示本地化角色名）
    showReleaseNotes: true,   // 更新弹窗是否展示 Release 更新内容（设置中调节，默认开启）
    debugMode: false,        // 调试模式（仅本次运行，监视内存/CPU/窗口）
    windowMaximized: false,  // 窗口是否最大化（标题栏按钮图标 / 禁用手柄缩放）
    previewMode: false,      // 当前是否为无组件角色精灵预览模式
    previewData: [],         // 无组件角色的预览精灵 [{name,size}]
    previewThumbs: {},       // {精灵名: dataURL}
    previewSel: new Set(),   // 已勾选精灵名
    loading: false,          // 正在加载角色/导出（读条中禁止切换）
    backgroundBusy: false,   // 背景任务使用同一状态栏，期间禁止启动角色任务
    sketchText: '',          // Anan 素描本已应用的文字（点“应用”后生效）
    sketchSize: 56,          // Anan 素描本文字字号（已应用）
    sketchAlign: 'center',   // Anan 素描本文字对齐：left/center/right（已应用）
  };

  // 后端事件注册表
  window.__pywebview = window.__pywebview || {};
  window.__pywebview.events = window.__pywebview.events || {};
  const on = (event, fn) => { window.__pywebview.events[event] = fn; };

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  // 各模块间存在循环依赖，函数不能在加载时解构，故用转发函数保持调用点写法不变。
  const toast = (...a) => MCE.toast(...a);
  const showModal = (...a) => MCE.showModal(...a);
  const btn = (...a) => MCE.btn(...a);
  const confirmDialog = (...a) => MCE.confirmDialog(...a);
  const setStatus = (...a) => MCE.setStatus(...a);
  const refreshExportCount = (...a) => MCE.refreshExportCount(...a);
  const initTabIndicator = (...a) => MCE.initTabIndicator(...a);
  const switchTab = (...a) => MCE.switchTab(...a);
  const updateTitleBar = (...a) => MCE.updateTitleBar(...a);
  const setMaxState = (...a) => MCE.setMaxState(...a);
  const setTipText = (...a) => MCE.setTipText(...a);
  const maybeAutoStartTour = (...a) => MCE.maybeAutoStartTour(...a);
  const applyTheme = (...a) => MCE.applyTheme(...a);
  const applyAnimations = (...a) => MCE.applyAnimations(...a);
  const renderCharList = (...a) => MCE.renderCharList(...a);
  const filterCharList = (...a) => MCE.filterCharList(...a);
  const onLoadClick = (...a) => MCE.onLoadClick(...a);
  const setupDragDrop = (...a) => MCE.setupDragDrop(...a);
  const filterParts = (...a) => MCE.filterParts(...a);
  const selectAll = (...a) => MCE.selectAll(...a);
  const selectClipMaskParts = (...a) => MCE.selectClipMaskParts(...a);
  const savePreset = (...a) => MCE.savePreset(...a);
  const deletePreset = (...a) => MCE.deletePreset(...a);
  const importPreset = (...a) => MCE.importPreset(...a);
  const exportPreset = (...a) => MCE.exportPreset(...a);
  const openSketchModal = (...a) => MCE.openSketchModal(...a);
  const syncSketchSizeLabel = (...a) => MCE.syncSketchSizeLabel(...a);
  const isAnanSketchMode = (...a) => MCE.isAnanSketchMode(...a);
  const finishSpearEaster = (...a) => MCE.finishSpearEaster(...a);
  const schedulePreview = (...a) => MCE.schedulePreview(...a);
  const doComposite = (...a) => MCE.doComposite(...a);
  const clearPreview = (...a) => MCE.clearPreview(...a);
  const renderPreviewGrid = (...a) => MCE.renderPreviewGrid(...a);
  const showSpritePreviewProgress = (...a) => MCE.showSpritePreviewProgress(...a);
  const bindPreviewZoom = (...a) => MCE.bindPreviewZoom(...a);
  const buildPreviewQualityDropdown = (...a) => MCE.buildPreviewQualityDropdown(...a);
  const openSettings = (...a) => MCE.openSettings(...a);
  const renderInfoPage = (...a) => MCE.renderInfoPage(...a);
  const renderAboutPage = (...a) => MCE.renderAboutPage(...a);
  const initAboutBg = (...a) => MCE.initAboutBg(...a);
  const loadSysInfo = (...a) => MCE.loadSysInfo(...a);

  // ═════════════ 事件绑定 ═════════════

  function bindEvents() {
    // Electron 无边框窗口：自绘标题栏 + 8 个缩放手柄（窗口控制在主进程侧实现）
    // 无边框标题栏：窗口控制（拖动/双击最大化/Aero Snap 由 Electron 原生处理）
    if ($('#titlebar')) {
      $('#tb-min').addEventListener('click', () => api() && api().window_minimize());
      $('#tb-max').addEventListener('click', async () => {
        if (!api()) return;
        const r = await api().window_maximize();
        if (r && 'maximized' in r) setMaxState(r.maximized);
      });
      $('#tb-close').addEventListener('click', () => api() && api().quit_app());
      // 日志控制台按钮（原生 cmd 窗口，随时可开，不依赖调试模式）
      const tbConsole = $('#tb-console');
      if (tbConsole) {
        tbConsole.addEventListener('click', () => {
          if (window.__electron && window.__electron.openLogConsole) window.__electron.openLogConsole();
        });
      }
      // 原生最大化/还原（双击标题栏、Aero Snap）→ 同步标题栏图标与缩放手柄
      if (window.__electron && window.__electron.onMaximizedChanged) {
        window.__electron.onMaximizedChanged((maximized) => setMaxState(maximized));
      }
    }
    // 无边框窗口边缘/角落缩放
    let resizeState = null;
    $$('#resize-handles .rh').forEach((h) => {
      h.addEventListener('mousedown', (e) => {
        if (e.button !== 0 || App.windowMaximized) return;
        resizeState = { dir: h.dataset.dir, sx: e.screenX, sy: e.screenY };
        e.preventDefault();
        e.stopPropagation();
      });
    });
    document.addEventListener('mousemove', (e) => {
      if (!resizeState) return;
      const dx = e.screenX - resizeState.sx;
      const dy = e.screenY - resizeState.sy;
      resizeState.sx = e.screenX; resizeState.sy = e.screenY;
      if (api()) api().window_resize(resizeState.dir, dx, dy);
    });
    document.addEventListener('mouseup', () => { resizeState = null; });
    $('#btn-load').addEventListener('click', onLoadClick);
    // 「取消加载」（进度区内，仅加载游戏目录期间可见）：立即禁用防重复点击，
    // 复位交给 clearProgress（load_complete 到达后收起进度区）
    $('#btn-cancel-load').addEventListener('click', async (e) => {
      const btn = e.currentTarget;
      btn.disabled = true;
      try { await api().cancel_load(); }
      catch (err) { btn.disabled = false; toast(String(err), 'error'); }
    });
    MCE.initBackgrounds();
    setupDragDrop();  // 拖拽导入：把游戏目录文件夹拖入窗口即可加载
    $('#btn-open-output').addEventListener('click', () => api().open_output());
    $('#btn-settings').addEventListener('click', openSettings);
    $('#btn-clear-cache').addEventListener('click', async () => {
      if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止清缓存
      switchTab('info');  // 先返回信息页，再清理
      const okc = await confirmDialog(t('left.clear_cache_confirm_title'), t('left.clear_cache_confirm_msg'));
      if (!okc) return;
      api().clear_cache(App.previewMode);  // 无组件预览模式时保留 preview 预览缓存
    });
    $('#char-search').addEventListener('input', (e) => filterCharList(e.target.value));
    $('#parts-search').addEventListener('input', (e) => filterParts(e.target.value));

    $$('.tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));

    $('#btn-select-all').addEventListener('click', () => selectAll(true));
    $('#btn-deselect-all').addEventListener('click', () => selectAll(false));

    // 快速勾选所有 ClippingMask 部件（被裁剪进角色区域的叠加层，正确合成光影所必需）
    $('#btn-select-clip').addEventListener('click', selectClipMaskParts);

    // 无组件预览模式
    $('#btn-prev-select-all').addEventListener('click', () => {
      App.previewSel = new Set(App.previewData.map((s) => s.name));
      renderPreviewGrid();
    });
    $('#btn-prev-clear').addEventListener('click', () => {
      App.previewSel.clear();
      renderPreviewGrid();
    });
    $('#btn-prev-export-sel').addEventListener('click', () => {
      if (App.previewSel.size === 0) { toast(t('parts.no_selection_hint'), 'warning'); return; }
      api().export_preview(App.currentName, Array.from(App.previewSel));
    });
    $('#btn-prev-export-all').addEventListener('click', () => {
      api().export_preview(App.currentName, null);
    });

    $('#btn-composite').addEventListener('click', doComposite);

    // 用户预设：下拉由 parts.js 动态构建（自绘下拉），这里只绑保存 / 导入 / 导出 / 删除按钮
    const btnPresetSave = $('#btn-preset-save');
    if (btnPresetSave) btnPresetSave.addEventListener('click', savePreset);
    const btnPresetImport = $('#btn-preset-import');
    // 必须包一层：importPreset(initial) 的第一个参数是「拖入的文件内容」，
    // 直接把函数交给 addEventListener 会把 MouseEvent 当文件传进去（弹出假的"JSON 格式不正确"）
    if (btnPresetImport) btnPresetImport.addEventListener('click', () => importPreset());
    const btnPresetExport = $('#btn-preset-export');
    if (btnPresetExport) btnPresetExport.addEventListener('click', exportPreset);
    const btnPresetDelete = $('#btn-preset-delete');
    if (btnPresetDelete) btnPresetDelete.addEventListener('click', deletePreset);

    $('#btn-save').addEventListener('click', () => { if (App.characterData) api().save_composite(); });
    $('#btn-clear-preview').addEventListener('click', clearPreview);
    $('#auto-update').addEventListener('change', (e) => {
      App.autoUpdate = e.target.checked;
      if (App.autoUpdate && App.selected.size > 0) schedulePreview();
    });

    // 预览画质（部件选择页，复用设置同款自定义下拉）：合成预览用
    buildPreviewQualityDropdown($('#preview-quality-slot'), () => {
      if (App.characterData && App.selected.size > 0) doComposite();
    });
    // 无组件精灵预览也跟随预览画质（切换后按新画质流式重新生成缩略图）
    buildPreviewQualityDropdown($('#preview-quality-slot-nc'), () => {
      if (!App.previewMode) return;
      App.previewThumbs = {};
      renderPreviewGrid();
      showSpritePreviewProgress({ current: 0, total: 1 });
      api().get_preview_thumbnails();
    });

    // 导出原始画质开关（预览窗口，悬停提示）：持久化（默认开启）
    const exportCb = $('#set-export-original');
    if (exportCb) {
      exportCb.checked = App.info.export_original_quality !== false;
      exportCb.addEventListener('change', async () => {
        if (!api()) return;
        const r = await api().set_export_original_quality(exportCb.checked);
        App.info.export_original_quality = !!r.export_original_quality;
      });
    }

    // Anan 素描本自定义文字：“编辑文字”按钮 → 模态编辑（确定后即刷新预览）
    const btnSketchEdit = $('#btn-sketch-edit');
    if (btnSketchEdit) btnSketchEdit.addEventListener('click', openSketchModal);
    // 字号滑块：实时应用并刷新预览
    const sketchSize = $('#sketch-size');
    if (sketchSize) {
      sketchSize.addEventListener('input', () => {
        App.sketchSize = Number(sketchSize.value);
        syncSketchSizeLabel();
        if (isAnanSketchMode() && App.selected.size > 0) schedulePreview();
      });
    }
    // 对齐分段按钮：点击即时应用并滑动指示条
    const sketchAlignSeg = $('#sketch-align');
    if (sketchAlignSeg) {
      sketchAlignSeg.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-align]');
        if (!btn) return;
        App.sketchAlign = btn.dataset.align;
        const ind = sketchAlignSeg.querySelector('.seg-ind');
        let idx = 0;
        sketchAlignSeg.querySelectorAll('button[data-align]').forEach((b, i) => {
          b.classList.toggle('active', b === btn);
          if (b === btn) idx = i;
        });
        if (ind) ind.style.transform = 'translateX(' + (idx * 100) + '%)';
        if (isAnanSketchMode() && App.selected.size > 0) schedulePreview();
      });
    }

    bindPreviewZoom();

    // 长矛彩蛋：点击预览中的人物结束（播放音频 + 清空预览 + 取消全选 + 解除锁定）
    const spearPreviewImg = $('#preview-img');
    if (spearPreviewImg) {
      spearPreviewImg.addEventListener('click', (e) => {
        // 需等待合成完成（_spearPreviewReady）后才允许点击结束
        if (!MCE.spear.active || !MCE.spear.previewReady) return;
        e.stopPropagation();
        finishSpearEaster();
      });
    }
    // 长矛彩蛋锁定期间屏蔽右键菜单（强化"锁定"体验）
    document.addEventListener('contextmenu', (e) => {
      if (MCE.spear.active) { e.preventDefault(); e.stopPropagation(); }
    });
    // 长矛彩蛋锁定期间全局拦截点击：除标题栏窗口控件（最小化/最大化/关闭）
    // 与合成完成后预览中的人物（点击结束彩蛋）外，一律禁止（捕获阶段拦截，先于元素自身处理器）
    document.addEventListener('click', (e) => {
      if (!MCE.spear.active) return;
      if (e.target.closest('#tb-min, #tb-max, #tb-close')) return;
      if (MCE.spear.previewReady && e.target.closest('#preview-img')) return;
      e.preventDefault();
      e.stopPropagation();
    }, true);

    $('#btn-expand').addEventListener('click', () => App.hierarchyNav.expand.forEach((f) => f()));
    $('#btn-collapse').addEventListener('click', () => App.hierarchyNav.collapse.forEach((f) => f()));

    // 关于页：跳转按钮 + 检查更新（事件委托，renderAboutPage 重建后仍有效）
    document.addEventListener('click', (e) => {
      const openBtn = e.target.closest('.about-open');
      if (openBtn && openBtn.dataset.url && api()) { api().open_url(openBtn.dataset.url); return; }
      if (e.target.closest('#btn-about-update') && api()) {
        setStatus(t('app.status.checking_update'), true);
        api().check_update(false);
      }
    });
  }

  // ═════════════ 初始化 ═════════════

  // 同步窗口最大化状态：主进程会按记忆的窗口状态在页面加载前就 maximize（前端收不到那次事件），
  // 因此启动后主动查一次；之后的原生最大化/还原由 win:maximized-changed 事件推送。
  async function syncWindowMaximized() {
    if (!api()) return;
    try {
      const r = await api().window_is_maximized();
      if (r && 'maximized' in r) setMaxState(!!r.maximized);
    } catch (e) { /* ignore */ }
  }

  // 启动剧透提示（勾选"不再提示"并点"继续"后不再弹出，持久化到 settings.json）
  function showSpoilerNotice() {
    if (App.info && App.info.no_spoiler) return;
    const body = document.createElement('div');
    const msg = document.createElement('div');
    msg.className = 'desc';
    msg.textContent = t('dialog.spoiler_msg');
    body.appendChild(msg);
    const label = document.createElement('label');
    label.className = 'form-row';
    label.style.flexDirection = 'row';
    label.style.alignItems = 'center';
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    const cbText = document.createElement('span');
    cbText.textContent = t('dialog.spoiler_never');
    label.appendChild(cb);
    label.appendChild(cbText);
    body.appendChild(label);
    const footer = document.createElement('div');
    const quit = btn(t('dialog.spoiler_quit'), 'btn sm', null);
    const cont = btn(t('dialog.spoiler_continue'), 'btn sm primary', null);
    footer.appendChild(quit);
    footer.appendChild(cont);
    const { close } = showModal({ title: t('dialog.spoiler_title'), body, footer });
    quit.addEventListener('click', () => { api().quit_app(); });
    cont.addEventListener('click', () => {
      if (cb.checked) api().set_no_spoiler(true);
      close();
    });
  }

  // 启动进度条更新
  function setSplashProgress(p) {
    const fill = $('#splash-bar-fill');
    if (fill) fill.style.width = Math.min(100, Math.max(0, p)) + '%';
  }

  // 隐藏启动加载界面：进度条满后停顿一下，再缓慢淡出
  function hideSplash() {
    setSplashProgress(100);
    const sp = $('#splash');
    if (!sp) return;
    setTimeout(() => {
      sp.classList.add('hide');
      setTimeout(() => { if (sp.parentNode) sp.parentNode.removeChild(sp); }, 650);
    }, 600);
  }

  async function init() {
    if (!window.pywebview || !window.pywebview.api) {
      // 唯一启动链路：start.bat → electron/main.js → backend.py。
      // 因此走到这里只可能是直接双击 index.html 打开了页面（无 preload 桥）。
      const el = document.createElement('div');
      el.className = 'no-bridge';
      el.innerHTML =
        '<h2>' + t('app.subtitle') + '</h2>' +
        '<p>' + t('app.no_bridge_hint') + '</p>';
      document.body.appendChild(el);
      return;
    }
    try {
      setSplashProgress(15);
      const info = await window.pywebview.api.get_app_info();
      setSplashProgress(45);
      App.info = info;
      window.I18N.set(info.translations, info.current_lang, info.lang_names);
      setSplashProgress(60);
      updateTitleBar();
      const vb = $('#version-badge');
      vb.textContent = 'v' + info.version;
      setTipText(vb, 'v' + info.version);   // 完整版本号（被省略号截断时悬停可见）
      const isPrerelease = /(pre|rc|beta|alpha)/i.test(info.version || '');
      vb.classList.toggle('prerelease', isPrerelease);
      document.title = 'Manosaba Character Extracter v' + info.version;
      // 启动提示：测试版提示 + 剧透警告。
      // 首次启动（tutorial_done=false）时让位给使用引导——引导结束（或跳过）后再弹出，
      // 否则「先弹剧透框、关掉才轮到教程」会让教程显得姗姗来迟（见文件末尾 maybeAutoStartTour 调用）。
      const showStartupNotices = () => {
        if (isPrerelease) {
          const footer = document.createElement('div');
          const ok = btn(t('dialog.ok'), 'btn sm primary', null);
          footer.appendChild(ok);
          const { close } = showModal({
            title: t('dialog.prerelease_title'),
            body: '<div class="desc">' + escapeHtml(t('dialog.prerelease_msg', { version: info.version })) + '</div>',
            footer,
          });
          ok.addEventListener('click', close);
        }
        showSpoilerNotice();   // 剧透提示（首次启动，或未勾选"不再提示"时）
      };
      const tourPending = !info.tutorial_done;   // 是否将自动播放首次使用引导
      if (!tourPending) showStartupNotices();
      // 主题：settings.json（后端 get_app_info）为唯一权威，不接受 localStorage 等其他来源
      let theme = 'dark';
      if (info.theme === 'dark' || info.theme === 'light') theme = info.theme;
      const accent = info.accent || 'default';
      applyTheme(theme, accent);
      applyAnimations(!!info.disable_animations);   // 禁用界面动画（低配 GPU 提速）
      setSplashProgress(80);
      bindEvents();
      syncWindowMaximized();   // 主进程可能已按记忆状态最大化：启动后同步图标/缩放手柄
      initTabIndicator();   // tab 指示条（active 下划线滑动动画）
      renderCharList();
      renderInfoPage();
      renderAboutPage();
      initAboutBg();
      loadSysInfo();        // 启动时检查 CPU/GPU/内存配置（关于页展示）
      App.exportCount = (typeof info.export_count === 'number') ? info.export_count : 0;
      App.showOriginalName = !!info.show_original_name;
      App.showReleaseNotes = info.show_release_notes !== false;   // 默认开启
      App.debugMode = !!info.debug;
      refreshExportCount();
      window.pywebview.api.check_update(true); // 静默检查更新
      hideSplash();
      // 首次启动：使用引导优先弹出，结束后再补启动提示；否则按原顺序即时提示
      maybeAutoStartTour(tourPending ? showStartupNotices : null);
    } catch (e) {
      toast(t('app.init_failed', { msg: e }), 'error');
      hideSplash();
    }
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.App = App;
  MCE.$ = $;
  MCE.$$ = $$;
  MCE.t = t;
  MCE.api = api;
  MCE.escapeHtml = escapeHtml;
  MCE.fmt = fmt;
  MCE.copyText = copyText;
  MCE.on = on;
  MCE.init = init;
  MCE.bindEvents = bindEvents;
  MCE.showSpoilerNotice = showSpoilerNotice;
  MCE.setSplashProgress = setSplashProgress;
  MCE.hideSplash = hideSplash;

  // 启动：preload 在页面脚本之前注入 window.pywebview，因此直接等 DOM 就绪即可
  // （不再需要等待 pywebview 的 ready 事件）
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
