/* ============================================================
 * charlist.js — 角色列表（渲染 / 搜索 / 点击）+ 游戏目录加载（选择 / 拖拽导入）
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, $$, t, api, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const toast = (...a) => MCE.toast(...a);
  const setStatus = (...a) => MCE.setStatus(...a);
  const confirmDialog = (...a) => MCE.confirmDialog(...a);
  const clearPartsUI = (...a) => MCE.clearPartsUI(...a);
  const clearPreview = (...a) => MCE.clearPreview(...a);
  const spearEasterAvailable = (...a) => MCE.spearEasterAvailable(...a);
  const startSpearEaster = (...a) => MCE.startSpearEaster(...a);

  // ═════════════ 侧边栏 ═════════════

  // 角色类型：常规(0) < 看守/典狱长(1) < 魔女化(2) < 残骸(3)；同类型内按英文 A-Z（bundle 文件名）
  function charTypeRank(name) {
    if (name === 'jailer' || name === 'warden') return 1;   // 看守/典狱长
    if (name.indexOf('creature') === 0) return 2;           // 魔女化
    if (name === 'jailerb' || name === 'jailerc') return 3; // 残骸
    return 0;                                               // 常规角色
  }
  function charDisplayName(name) {
    // 默认显示当前语言的本地化角色名（char.* 翻译键）；勾选“显示原始文件名”时显示原始文件名
    if (App.showOriginalName) return name;
    const key = 'char.' + name;
    const data = window.I18N.data || {};
    return (key in data) ? data[key] : name;        // 键缺失时回退原始文件名
  }
  function renderCharList() {
    const ul = $('#char-list');
    ul.innerHTML = '';
    const names = Object.keys(App.bundles).sort((a, b) => {
      const ra = charTypeRank(a), rb = charTypeRank(b);
      if (ra !== rb) return ra - rb;
      return a < b ? -1 : a > b ? 1 : 0;
    });
    if (names.length === 0) {
      const li = document.createElement('li');
      li.className = 'char-empty';
      li.style.cssText = 'color:var(--text-faint);font-size:12px;padding:10px;text-align:center';
      li.textContent = t('left.char_search');
      ul.appendChild(li);
      return;
    }
    names.forEach((name, i) => {
      const li = document.createElement('li');
      li.className = 'char-item' + (name === App.currentName ? ' active' : '');
      li.dataset.name = name;   // 原始 bundle 名，供搜索与选择
      li.innerHTML = '<span class="char-avatar"></span><span class="char-name"></span>';
      li.querySelector('.char-avatar').textContent = i + 1;
      li.querySelector('.char-name').textContent = charDisplayName(name);
      li.addEventListener('click', () => onCharClick(name));
      // 彩蛋：noah 组件选择界面右键 leia → 长矛彩蛋
      li.addEventListener('contextmenu', (e) => {
        if (name !== 'leia') return;
        if (!spearEasterAvailable()) return;
        e.preventDefault();
        e.stopPropagation();
        startSpearEaster();
      });
      ul.appendChild(li);
    });
    // 重新渲染后重新应用搜索过滤：点击角色等操作会重建列表，需保持搜索框当前的过滤状态
    const searchInput = $('#char-search');
    if (searchInput && searchInput.value) filterCharList(searchInput.value);
  }

  // 刷新所有显示角色名的地方（侧边栏 / 部件页 / 预览页），切换中文名或语言时调用
  function refreshNameDisplay() {
    renderCharList();
    if (!App.currentName) return;
    const dn = charDisplayName(App.currentName);
    const pn = $('#preview-name');
    if (pn) pn.textContent = dn;
    const partsName = $('#parts-name');
    if (partsName) partsName.textContent = dn;
  }

  function filterCharList(query) {
    const q = (query || '').trim().toLowerCase();
    $$('#char-list .char-item').forEach((li) => {
      const orig = (li.dataset.name || '').toLowerCase();
      const shown = li.querySelector('.char-name').textContent.toLowerCase();
      li.style.display = (!q || orig.includes(q) || shown.includes(q)) ? '' : 'none';
    });
  }

  function loadDir(path) {
    console.log(t('log.js_load_dir', { path }));
    setStatus(t('app.progress.loading_bundles'), true);
    api().load_directory(path);
  }

  // ── 拖拽导入：把游戏目录文件夹拖入窗口即可加载 ──
  function setupDragDrop() {
    const overlay = $('#drop-overlay');
    const overlayText = $('#drop-overlay-text');
    let depth = 0;  // dragenter/dragleave 成对计数，避免子元素进出误隐藏
    const hasFiles = (e) => !!(e.dataTransfer && Array.from(e.dataTransfer.types || []).includes('Files'));
    const show = () => {
      if (overlay) {
        if (overlayText) overlayText.textContent = t('left.drop_overlay');
        overlay.hidden = false;
      }
    };
    const hide = () => { if (overlay) overlay.hidden = true; };

    window.addEventListener('dragenter', (e) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth++;
      show();
    });
    window.addEventListener('dragover', (e) => {
      if (!hasFiles(e)) return;
      e.preventDefault();  // 阻止浏览器打开文件
      if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    });
    window.addEventListener('dragleave', (e) => {
      if (!hasFiles(e)) return;
      depth = Math.max(0, depth - 1);
      if (depth === 0) hide();
    });
    window.addEventListener('drop', (e) => {
      if (!hasFiles(e)) return;
      e.preventDefault();
      depth = 0;
      hide();
      handleDrop(e);
    });
  }

  function handleDrop(e) {
    const item = e.dataTransfer.items && e.dataTransfer.items[0];
    const file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (!file) return;
    // 只接受文件夹
    let isDir = false;
    if (item && item.webkitGetAsEntry) {
      const entry = item.webkitGetAsEntry();
      isDir = !!(entry && entry.isDirectory);
    }
    if (!isDir) {
      toast(t('left.drop_not_folder'), 'warning');
      return;
    }
    // 获取绝对路径：Electron 用 webUtils.getPathForFile，旧版 Electron 回退 file.path
    let path = null;
    if (window.__electron && window.__electron.getPathForFile) {
      try { path = window.__electron.getPathForFile(file); } catch (err) { path = null; }
    }
    if (!path && typeof file.path === 'string') path = file.path;
    if (!path) {
      toast(t('left.drop_unsupported'), 'warning');
      return;
    }
    loadDir(path);
  }

  async function onCharClick(name) {
    if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止切换角色
    if (App.loading) {
      const ok = await confirmDialog(t('dialog.cancel_load_title'), t('dialog.cancel_load_msg'));
      if (!ok) return;
      api().cancel_character_load();
    }
    console.log(t('log.js_select_char', { name }));
    App.currentName = name;
    App.characterData = null;
    App.selected.clear();
    App.thumbnails = {};
    App.partEls = {};
    App.previewMode = false;
    App.previewData = [];
    App.previewThumbs = {};
    App.previewSel.clear();
    App.sketchText = '';   // 切换角色时清空素描本自定义文字
    clearPartsUI();
    clearPreview();
    renderCharList();
    setStatus(t('app.status.analyzing', { name }), true);
    App.loading = true;   // 分析/提取进行中：期间再次点击会先确认取消，避免并发加载
    api().select_character(name);
  }

  // ── 扩展：从游戏目录选择（无边框标题栏「加载游戏目录」按钮）──
  async function onLoadClick() {
    if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止加载游戏目录
    const path = await api().select_directory();
    if (path) loadDir(path);
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.charTypeRank = charTypeRank;
  MCE.charDisplayName = charDisplayName;
  MCE.renderCharList = renderCharList;
  MCE.refreshNameDisplay = refreshNameDisplay;
  MCE.filterCharList = filterCharList;
  MCE.loadDir = loadDir;
  MCE.setupDragDrop = setupDragDrop;
  MCE.handleDrop = handleDrop;
  MCE.onCharClick = onCharClick;
  MCE.onLoadClick = onLoadClick;
})();
