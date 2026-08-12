/* ============================================================
 * app.js — Manosaba Extracter 前端主逻辑 (PyWebView)
 * 通过 window.pywebview.api 调用 Python 后端，
 * 后端通过 window.__pywebview.events.<事件> 推送结果。
 * ============================================================ */
(function () {
  'use strict';

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
    useChineseNames: false,  // 是否显示角色中文名（设置中调节）
  };

  // 后端事件注册表
  window.__pywebview = window.__pywebview || {};
  window.__pywebview.events = window.__pywebview.events || {};
  const on = (event, fn) => { window.__pywebview.events[event] = fn; };

  // ═════════════ 基础 UI ═════════════

  // ── Toast 提示框（参考「窝-home-team」风格：堆叠 + 关闭 + 进度条 + 滑入） ──
  const TOAST_DURATION = 3500;
  const MAX_TOASTS = 4;
  const TOAST_GAP = 12;
  const TOAST_BOTTOM = 24;
  const TOAST_COLORS = {
    info: '#58a6ff',
    success: '#35d07f',
    warning: '#fbbf24',
    error: '#f85149',
  };
  const _toasts = []; // 当前存活的 toast（最早在前，最新在后）

  function _layoutToasts() {
    // 最新加入的在最底部，旧的往上堆叠；通过 CSS transition:bottom 平滑上移
    let bottom = TOAST_BOTTOM;
    for (let i = _toasts.length - 1; i >= 0; i--) {
      const el = _toasts[i];
      el.style.bottom = bottom + 'px';
      bottom += el.offsetHeight + TOAST_GAP;
    }
  }

  function _dismissToast(el) {
    if (!el.isConnected) return;
    const idx = _toasts.indexOf(el);
    if (idx > -1) _toasts.splice(idx, 1);
    if (el.dataset.timer) clearTimeout(Number(el.dataset.timer));
    el.classList.add('hide');
    setTimeout(() => {
      if (el.isConnected) el.remove();
      _layoutToasts();
    }, 350);
  }

  function toast(msg, type) {
    type = type || 'info';
    const color = TOAST_COLORS[type] || TOAST_COLORS.info;

    // 超出最大数量时移除最旧的
    while (_toasts.length >= MAX_TOASTS) {
      const oldest = _toasts.shift();
      if (oldest && oldest.dataset.timer) clearTimeout(Number(oldest.dataset.timer));
      if (oldest && oldest.isConnected) _dismissToast(oldest);
    }

    const el = document.createElement('div');
    el.className = 'toast';
    el.style.borderColor = color;
    el.innerHTML =
      '<span class="toast-msg"></span>' +
      '<button class="toast-close" type="button" aria-label="close">✕</button>' +
      '<div class="toast-progress"></div>';
    el.querySelector('.toast-msg').textContent = msg;
    el.querySelector('.toast-progress').style.background = color;
    $('#toast-root').appendChild(el);

    const dismiss = () => _dismissToast(el);
    el.querySelector('.toast-close').addEventListener('click', dismiss);

    _toasts.push(el);
    _layoutToasts(); // 设置初始 bottom（新 toast 在最底部）

    // 淡入（双 rAF 确保初始样式渲染后触发过渡）
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.add('show')));

    const timer = setTimeout(dismiss, TOAST_DURATION);
    el.dataset.timer = timer;
  }

  function showModal({ title, titleKey, body, footer }) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    const modal = document.createElement('div');
    modal.className = 'modal';

    const head = document.createElement('div');
    head.className = 'modal-header';
    const h3 = document.createElement('h3');
    if (titleKey) {
      // 使用翻译键：语言切换后 applyDom 可自动刷新标题
      h3.setAttribute('data-i18n', titleKey);
      h3.textContent = window.I18N.t(titleKey);
    } else {
      h3.textContent = title || '';
    }
    const x = document.createElement('button');
    x.className = 'modal-close';
    x.textContent = '✕';
    head.appendChild(h3); head.appendChild(x);

    const bodyEl = document.createElement('div');
    bodyEl.className = 'modal-body';
    if (typeof body === 'string') bodyEl.innerHTML = body;
    else if (body) bodyEl.appendChild(body);

    const footerEl = document.createElement('div');
    footerEl.className = 'modal-footer';
    if (footer) footerEl.appendChild(footer);
    else footerEl.style.display = 'none';

    modal.appendChild(head); modal.appendChild(bodyEl); modal.appendChild(footerEl);
    backdrop.appendChild(modal);
    $('#modal-root').appendChild(backdrop);

    const onKey = (e) => { if (e.key === 'Escape') close(); };
    const close = () => { backdrop.remove(); document.removeEventListener('keydown', onKey); };
    document.addEventListener('keydown', onKey);
    backdrop.addEventListener('click', (e) => { if (e.target === backdrop) close(); });
    x.addEventListener('click', close);
    return { close, bodyEl, footerEl };
  }

  function btn(text, cls, onClick) {
    const b = document.createElement('button');
    b.className = cls || 'btn sm';
    b.textContent = text;
    if (onClick) b.addEventListener('click', onClick);
    return b;
  }

  function confirmDialog(title, message, okLabel, cancelLabel) {
    return new Promise((resolve) => {
      const footer = document.createElement('div');
      const no = btn(cancelLabel || t('dialog.cancel'), 'btn sm', () => { close(); resolve(false); });
      const yes = btn(okLabel || t('dialog.ok'), 'btn sm primary', () => { close(); resolve(true); });
      footer.appendChild(no); footer.appendChild(yes);
      const { close } = showModal({
        title,
        body: '<div class="desc">' + escapeHtml(message) + '</div>',
        footer,
      });
    });
  }

  // 状态栏 / 进度
  function setStatus(text, busy) {
    App.lastStatus = text || '';
    $('#status-text').textContent = App.lastStatus;
    $('#status').classList.toggle('busy', !!busy);
    $('#status').classList.remove('error');
  }
  function setErrorStatus() { $('#status').classList.add('error'); }

  // 累计导出计数显示（关于页）
  function refreshExportCount() {
    const el = $('#about-export-count');
    if (el) el.textContent = String(App.exportCount);
  }
  function showProgress(p) {
    const wrap = $('#progress-wrap');
    wrap.hidden = false;
    const pct = p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;
    $('#progress-bar').style.width = pct + '%';
    $('#progress-label').textContent = (App.lastStatus ? App.lastStatus + ' ' : '') + pct + '%';
  }
  function clearProgress() { $('#progress-wrap').hidden = true; }

  // 标签页
  function switchTab(name) {
    $$('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === 'tab-' + name));
  }

  // 主题
  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('msx-theme', theme); } catch (e) { /* ignore */ }
  }

  // ═════════════ 侧边栏 ═════════════

  // 角色类型：常规(0) < 看守/典狱长(1) < 魔女化(2) < 残骸(3)；同类型内按英文 A-Z（bundle 文件名）
  function charTypeRank(name) {
    if (name === 'jailer' || name === 'warden') return 1;   // 看守/典狱长
    if (name.indexOf('creature') === 0) return 2;           // 魔女化
    if (name === 'jailerb' || name === 'jailerc') return 3; // 残骸
    return 0;                                               // 常规角色
  }
  function charDisplayName(name) {
    // 仅当「设置开启中文名」且「当前语言为中文」时才显示中文角色名
    if (!App.useChineseNames) return name;
    if (window.I18N.current !== 'zh_CN') return name;
    const key = 'char.' + name;
    const data = window.I18N.data || {};
    return (key in data) ? data[key] : name;        // 键缺失时回退原名
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
      ul.appendChild(li);
    });
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

  function onCharClick(name) {
    console.log(t('log.js_select_char', { name }));
    App.currentName = name;
    App.characterData = null;
    App.selected.clear();
    App.thumbnails = {};
    App.partEls = {};
    clearPartsUI();
    clearPreview();
    renderCharList();
    setStatus(t('app.status.analyzing', { name }), true);
    api().select_character(name);
  }

  function clearPartsUI() {
    $('#parts-list').innerHTML = '';
    $('#parts-empty').hidden = false;
    $('#parts-name').textContent = '—';
    $('#parts-count').textContent = '';
    $('#sel-count').textContent = '0';
    $('#selected-list').innerHTML = '';
    $('#hierarchy-tree').innerHTML = '';
    $('#hierarchy-empty').hidden = false;
  }

  function clearPreview() {
    const img = $('#preview-img');
    img.hidden = true;
    img.removeAttribute('src');
    img.style.width = '';
    img.style.maxWidth = '';
    img.style.height = '';
    $('#preview-empty').hidden = false;
    $('#preview-info').hidden = true;
    // 重置缩放状态
    App.previewSize = null;
    previewDragging = null;
    const zoomEl = $('#zoom-slider');
    if (zoomEl) { zoomEl.disabled = true; zoomEl.value = 0; }
    const zv = $('#zoom-value');
    if (zv) zv.textContent = t('parts.zoom_fit');
    const pc = $('#preview');
    if (pc) pc.classList.remove('zoomed', 'dragging');
  }

  // ═════════════ 预览缩放 / 平移 ═════════════

  const ZOOM_MAX = 4;          // 最大缩放 400%
  let previewZoom = 1;         // 当前缩放（1 = 100%，最小值以总分辨率为准 = 适配）
  let previewFit = 1;          // 适配（完整显示全图）所需缩放
  let previewDragging = null;  // 拖动平移状态

  function computeFit() {
    const size = App.previewSize;
    const container = $('#preview');
    if (!size || !container) return 1;
    const cw = container.clientWidth - 2;  // 减去 border
    const ch = container.clientHeight - 2;
    if (cw <= 0 || ch <= 0) return 1;
    return Math.min(cw / size[0], ch / size[1]);
  }

  // 最小缩放以当前预览的总分辨率为准：完整显示全图（若图像小于容器则为 100%）
  function previewMinZoom() {
    return Math.min(1, previewFit);
  }

  function sliderToZoom(v) {
    const min = previewMinZoom();
    return min + (ZOOM_MAX - min) * (Number(v) / 100);
  }

  function zoomToSlider(zoom) {
    const min = previewMinZoom();
    const v = (zoom - min) / (ZOOM_MAX - min) * 100;
    return zoom > min + 0.001 ? Math.max(1, Math.ceil(v)) : 0;
  }

  function applyPreviewZoom() {
    const size = App.previewSize;
    const container = $('#preview');
    const img = $('#preview-img');
    const slider = $('#zoom-slider');
    if (!size || !container || !img || !slider) return;
    previewFit = computeFit();
    previewZoom = Math.max(previewMinZoom(), Math.min(ZOOM_MAX, previewZoom));
    slider.value = zoomToSlider(previewZoom);
    img.style.maxWidth = 'none';
    img.style.width = Math.round(size[0] * previewZoom) + 'px';
    img.style.height = Math.round(size[1] * previewZoom) + 'px';
    container.classList.toggle('zoomed', previewZoom > previewFit + 0.001);
    $('#zoom-value').textContent =
      slider.value <= 0 ? t('parts.zoom_fit') : Math.round(previewZoom * 100) + '%';
  }

  function onPreviewWheel(e) {
    const size = App.previewSize;
    const container = $('#preview');
    if (!size || !container) return;
    e.preventDefault();
    const oldZ = previewZoom;
    const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
    const newZ = Math.max(Math.min(1, previewFit), Math.min(ZOOM_MAX, oldZ * factor));
    if (Math.abs(newZ - oldZ) < 0.001) return;
    // 以鼠标位置为中心缩放：保持光标下的内容点不动
    const rect = container.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    previewZoom = newZ;
    applyPreviewZoom();
    const ratio = newZ / oldZ;
    container.scrollLeft = container.scrollLeft * ratio + mx * (ratio - 1);
    container.scrollTop = container.scrollTop * ratio + my * (ratio - 1);
  }

  function onPreviewMouseDown(e) {
    if (e.button !== 0) return;
    const container = $('#preview');
    previewDragging = {
      x: e.clientX, y: e.clientY,
      sl: container.scrollLeft, st: container.scrollTop,
    };
    container.classList.add('dragging');
    e.preventDefault();
  }

  function onPreviewMouseMove(e) {
    if (!previewDragging) return;
    const container = $('#preview');
    container.scrollLeft = previewDragging.sl - (e.clientX - previewDragging.x);
    container.scrollTop = previewDragging.st - (e.clientY - previewDragging.y);
    e.preventDefault();
  }

  function onPreviewMouseUp() {
    if (!previewDragging) return;
    previewDragging = null;
    const c = $('#preview');
    if (c) c.classList.remove('dragging');
  }

  function bindPreviewZoom() {
    const container = $('#preview');
    const slider = $('#zoom-slider');
    $('#btn-zoom-fit').addEventListener('click', () => {
      slider.value = 0;
      previewZoom = previewMinZoom();
      applyPreviewZoom();
    });
    slider.addEventListener('input', (e) => {
      previewZoom = sliderToZoom(e.target.value);
      applyPreviewZoom();
    });
    container.addEventListener('wheel', onPreviewWheel, { passive: false });
    container.addEventListener('mousedown', onPreviewMouseDown);
    document.addEventListener('mousemove', onPreviewMouseMove);
    document.addEventListener('mouseup', onPreviewMouseUp);
    window.addEventListener('resize', () => {
      if (App.previewSize && $('#zoom-slider').value === '0') applyPreviewZoom();
    });
  }

  // ═════════════ 部件选择 / 预览 ═════════════

  // 自然排序：字母段按字典序，数字段按数值比较（如 ArmL02 < ArmL10）
  function naturalCmp(a, b) {
    const pa = (a.match(/\d+|\D+/g) || []);
    const pb = (b.match(/\d+|\D+/g) || []);
    const n = Math.max(pa.length, pb.length);
    for (let i = 0; i < n; i++) {
      const x = pa[i];
      const y = pb[i];
      if (x === undefined) return -1;
      if (y === undefined) return 1;
      const xIsNum = /^\d+$/.test(x);
      const yIsNum = /^\d+$/.test(y);
      if (xIsNum && yIsNum) {
        const diff = parseInt(x, 10) - parseInt(y, 10);
        if (diff !== 0) return diff;
      } else if (x !== y) {
        return x < y ? -1 : 1;
      }
    }
    return 0;
  }

  // 排序键：第一个下划线之前的字符串（如 Eyes01_Normal_Open -> Eyes01）
  function partPrefix(name) {
    const i = name.indexOf('_');
    return i === -1 ? name : name.slice(0, i);
  }

  // 部件排序：先按前缀（首字母+数字）排序，同前缀再按完整名自然排序
  function sortParts(data) {
    data.transform_data.sort((p1, p2) => {
      const c = naturalCmp(partPrefix(p1.name), partPrefix(p2.name));
      return c !== 0 ? c : naturalCmp(p1.name, p2.name);
    });
  }

  // 部件搜索过滤（按名称，匹配时隐藏不相关的卡片与分组）
  function filterParts(q) {
    const query = (q || '').trim().toLowerCase();
    $$('#parts-list .part-group').forEach((group) => {
      let visible = 0;
      group.querySelectorAll('.part-item').forEach((item) => {
        const name = item.querySelector('.part-name').textContent.toLowerCase();
        const show = !query || name.includes(query);
        item.style.display = show ? '' : 'none';
        if (show) visible++;
      });
      group.style.display = visible > 0 ? '' : 'none';
      // 搜索时自动展开匹配到的分组，保证结果可见
      if (query && visible > 0) group.classList.remove('collapsed');
    });
  }

  function renderParts(data) {
    App.partEls = {};
    const list = $('#parts-list');
    list.innerHTML = '';
    $('#parts-name').textContent = data.name;
    $('#parts-count').textContent = data.count + ' ' + t('parts.total');
    $('#parts-empty').hidden = true;

    const groups = {};
    data.transform_data.forEach((p) => {
      (groups[p.category] = groups[p.category] || []).push(p);
    });

    Object.keys(groups).sort().forEach((cat) => {
      const parts = groups[cat];
      const g = document.createElement('div');
      g.className = 'part-group';
      const h = document.createElement('div');
      h.className = 'part-group-header';
      h.title = cat;
      const caret = document.createElement('span');
      caret.className = 'part-caret';
      caret.innerHTML =
        '<svg viewBox="0 0 16 16" width="12" height="12"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
      const nameSpan = document.createElement('span');
      nameSpan.textContent = cat;
      const cnt = document.createElement('span');
      cnt.className = 'g-count';
      cnt.textContent = parts.length;
      h.appendChild(caret); h.appendChild(nameSpan); h.appendChild(cnt);
      // 点击分组标题折叠/展开
      h.addEventListener('click', () => g.classList.toggle('collapsed'));
      g.appendChild(h);

      parts.forEach((p) => {
        const pos = p.position || { x: 0, y: 0 };
        const sz = p.sprite_size || [0, 0];
        const alpha = (p.color && typeof p.color.a === 'number') ? p.color.a : 1;

        const item = document.createElement('div');
        item.className = 'part-item';
        item.innerHTML =
          '<input type="checkbox">' +
          '<span class="part-thumb"><span class="noimg">…</span></span>' +
          '<span class="part-info">' +
          '  <span class="part-name"></span>' +
          '  <span class="part-meta"></span>' +
          '</span>' +
          '<span class="part-alpha"></span>';

        item.querySelector('.part-name').textContent = p.name;
        item.querySelector('.part-meta').textContent =
          'x:' + fmt(pos.x) + '  y:' + fmt(pos.y) + '  order:' + p.sorting_order +
          '  ' + sz[0] + '×' + sz[1];
        item.querySelector('.part-alpha').textContent = 'α ' + Number(alpha).toFixed(2);

        const cb = item.querySelector('input[type=checkbox]');
        // 仅点击复选框切换勾选；点击卡片其他区域不触发选择/合成
        cb.addEventListener('change', () => onPartToggle(p.name, cb.checked));

        App.partEls[p.name] = { cb, thumb: item.querySelector('.part-thumb') };
        g.appendChild(item);
      });
      list.appendChild(g);
    });
  }

  function onPartToggle(name, checked) {
    if (checked) App.selected.add(name);
    else App.selected.delete(name);
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    if (App.autoUpdate) schedulePreview();
  }

  function updateSelUI() {
    $('#sel-count').textContent = App.selected.size;
    const ul = $('#selected-list');
    ul.innerHTML = '';
    if (!App.characterData || App.selected.size === 0) {
      const li = document.createElement('li');
      li.className = 'selected-empty';
      li.textContent = t('parts.no_selection_hint');
      ul.appendChild(li);
      return;
    }
    App.characterData.transform_data.forEach((p) => {
      if (App.selected.has(p.name)) {
        const li = document.createElement('li');
        li.textContent = p.name;
        li.title = t('app.click_to_copy');
        li.addEventListener('click', () => copyText(p.name));
        ul.appendChild(li);
      }
    });
  }

  function selectAll(checked) {
    if (!App.characterData) return;
    App.selected.clear();
    App.characterData.transform_data.forEach((p) => {
      if (checked) App.selected.add(p.name);
    });
    Object.values(App.partEls).forEach((e) => { e.cb.checked = checked; });
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    if (App.autoUpdate && checked) schedulePreview();
  }

  function schedulePreview() {
    clearTimeout(App.previewTimer);
    App.previewTimer = setTimeout(() => {
      if (!App.characterData || App.selected.size === 0) return;
      api().composite(Array.from(App.selected));
    }, 500);
  }

  function doComposite() {
    if (!App.characterData) return;
    if (App.selected.size === 0) {
      toast(t('parts.no_selection_hint'), 'warning');
      return;
    }
    console.log(t('log.js_composite_start', { count: App.selected.size }));
    api().composite(Array.from(App.selected));
  }

  // ═════════════ 层级树 ═════════════

  function renderHierarchy(nodes) {
    App.hierarchyNav = { expand: [], collapse: [] };
    const root = $('#hierarchy-tree');
    root.innerHTML = '';
    const wrap = document.createElement('div');
    wrap.className = 'tree-root';
    nodes.forEach((n) => wrap.appendChild(buildNode(n, App.hierarchyNav)));
    root.appendChild(wrap);
    $('#hierarchy-empty').hidden = nodes.length > 0;
  }

  function buildNode(node, nav) {
    const hasChildren = node.children && node.children.length > 0;
    const wrap = document.createElement('div');
    wrap.className = 'tree-node';

    const row = document.createElement('div');
    row.className = 'tree-row open';
    if (node.level === 0) row.classList.add('tree-node-root');

    const caret = document.createElement('span');
    caret.className = 'tree-caret';
    caret.textContent = hasChildren ? '▶' : '';

    const label = document.createElement('span');
    const pos = node.position || {};
    const posStr = '(' + fmt(pos.x) + ', ' + fmt(pos.y) + ')';
    if (node.has_sprite) {
      label.classList.add('tree-sprite');
      label.textContent = node.name + ' — ' + posStr + ' · order ' + node.sorting_order;
    } else if (hasChildren) {
      label.textContent = node.name + ' (' + node.children.length + ')';
    } else {
      label.textContent = node.name + ' — ' + posStr;
    }

    row.appendChild(caret);
    row.appendChild(label);
    wrap.appendChild(row);

    let childBox = null;
    if (hasChildren) {
      childBox = document.createElement('div');
      node.children.forEach((c) => childBox.appendChild(buildNode(c, nav)));
      wrap.appendChild(childBox);
      nav.expand.push(() => { row.classList.add('open'); childBox.hidden = false; });
      nav.collapse.push(() => { row.classList.remove('open'); childBox.hidden = true; });
    }
    // 行点击：展开/折叠（无子节点时无操作）
    row.addEventListener('click', () => {
      if (childBox) {
        const open = row.classList.toggle('open');
        childBox.hidden = !open;
      }
    });
    // 复制按钮：每个组件单独复制，不触发行点击
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'tree-copy';
    copyBtn.title = t('app.click_to_copy');
    copyBtn.innerHTML =
      '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '<rect x="9" y="9" width="11" height="11" rx="2"/><path d="M5 15V5a2 2 0 0 1 2-2h10"/></svg>';
    copyBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      copyText(node.name);
    });
    row.insertBefore(copyBtn, label);
    return wrap;
  }

  // ═════════════ 设置窗口 ═════════════

  function openSettings() {
    const body = document.createElement('div');

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
    langLabel.setAttribute('data-i18n', 'lang.label');
    langLabel.textContent = t('lang.label');
    langRow.appendChild(langLabel);
    const langSel = document.createElement('select');
    langSel.className = 'input';
    langSel.id = 'set-lang';
    (App.info.langs || []).forEach((code) => {
      const opt = document.createElement('option');
      opt.value = code;
      opt.textContent = (App.info.lang_names && App.info.lang_names[code]) || code;
      if (code === App.info.current_lang) opt.selected = true;
      langSel.appendChild(opt);
    });
    langRow.appendChild(langSel);

    const themeRow = document.createElement('div');
    themeRow.className = 'form-row';
    const themeLabel = document.createElement('label');
    themeLabel.setAttribute('data-i18n', 'settings.theme_label');
    themeLabel.textContent = t('settings.theme_label');
    themeRow.appendChild(themeLabel);
    const themeSel = document.createElement('select');
    themeSel.className = 'input';
    themeSel.id = 'set-theme';
    themeSel.innerHTML =
      '<option value="dark" data-i18n="settings.theme_dark">' + t('settings.theme_dark') + '</option>' +
      '<option value="light" data-i18n="settings.theme_light">' + t('settings.theme_light') + '</option>';
    themeRow.appendChild(themeSel);

    const nameRow = document.createElement('div');
    nameRow.className = 'form-row';
    nameRow.id = 'chinese-names-row';
    const nameSwitch = document.createElement('label');
    nameSwitch.className = 'switch';
    const nameCb = document.createElement('input');
    nameCb.type = 'checkbox';
    nameCb.id = 'set-chinese-names';
    const slider = document.createElement('span');
    slider.className = 'slider';
    const nameText = document.createElement('span');
    nameText.setAttribute('data-i18n', 'settings.chinese_names_label');
    nameText.textContent = t('settings.chinese_names_label');
    nameSwitch.appendChild(nameCb);
    nameSwitch.appendChild(slider);
    nameSwitch.appendChild(nameText);
    nameRow.appendChild(nameSwitch);

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

    body.appendChild(outRow);
    body.appendChild(langRow);
    body.appendChild(themeRow);
    body.appendChild(nameRow);
    body.appendChild(actionRow);

    const footer = document.createElement('div');
    const closeBtn = btn('', 'btn sm', null);
    closeBtn.setAttribute('data-i18n', 'dialog.close');
    closeBtn.textContent = t('dialog.close');
    footer.appendChild(closeBtn);
    const { close } = showModal({ titleKey: 'settings.title', body, footer });
    closeBtn.addEventListener('click', close);

    themeSel.value = document.documentElement.dataset.theme || 'dark';
    themeSel.addEventListener('change', () => {
      applyTheme(themeSel.value);
      if (api()) api().set_theme(themeSel.value); // 持久化到 settings.json
    });

    // 仅当语言为中文时显示“显示中文名”选项
    nameRow.style.display = (window.I18N.current === 'zh_CN') ? '' : 'none';
    nameCb.checked = App.useChineseNames;
    nameCb.addEventListener('change', async () => {
      if (!api()) return;
      const r = await api().set_use_chinese_names(nameCb.checked);
      App.useChineseNames = !!r.use_chinese_names;
      renderCharList();
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

    langSel.addEventListener('change', async (e) => {
      const r = await api().set_lang(e.target.value);
      window.I18N.set(r.translations, r.current_lang, r.lang_names);
      App.info.current_lang = r.current_lang;
      App.info.lang_names = r.lang_names;
      refreshSettingsModal();
      renderInfoPage();       // 重建主信息页（其文本是动态渲染的）
      renderAboutPage();      // 重建关于页
      refreshPartsHeader();   // 如有已加载角色，刷新部件页头部计数
      renderCharList();       // 角色名（开启中文名时随语言变化）
      refreshExportCount();   // 累计导出计数文本
      if (App.previewSize) applyPreviewZoom(); // 刷新缩放标签（适配/百分比）
      setStatus(t('app.status.ready'), false);
      toast(t('app.status.ready'), 'success');
    });

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
    const langSel = document.querySelector('#set-lang');
    if (langSel) {
      const current = langSel.value;
      langSel.innerHTML = '';
      (App.info.langs || []).forEach((code) => {
        const opt = document.createElement('option');
        opt.value = code;
        opt.textContent = (App.info.lang_names && App.info.lang_names[code]) || code;
        if (code === current) opt.selected = true;
        langSel.appendChild(opt);
      });
    }
    // 其余带 data-i18n 的文本（标题/标签/按钮/主题选项）统一刷新
    window.I18N.applyDom();
    // “显示中文名”选项仅在中文界面显示
    const cnRow = document.querySelector('#chinese-names-row');
    if (cnRow) cnRow.style.display = (window.I18N.current === 'zh_CN') ? '' : 'none';
  }

  // 语言切换后刷新部件页头部（角色名 + 计数）
  function refreshPartsHeader() {
    if (!App.characterData) return;
    $('#parts-name').textContent = App.characterData.name;
    $('#parts-count').textContent = App.characterData.count + ' ' + t('parts.total');
  }

  // ═════════════ 对话框（模式选择 / 导出确认 / 打开目录） ═════════════

  function showModeDialog(name) {
    const body = document.createElement('div');
    const desc = document.createElement('div');
    desc.className = 'desc';
    desc.textContent = t('dialog.ask_mode_msg');
    body.appendChild(desc);

    const mkCard = (mode, iconSvg, title, hint) => {
      const card = document.createElement('div');
      card.className = 'mode-card';
      card.dataset.mode = mode;
      const ic = document.createElement('span');
      ic.className = 'mc-icon';
      ic.innerHTML = iconSvg;
      const box = document.createElement('div');
      const t1 = document.createElement('div');
      t1.className = 'mc-title';
      t1.textContent = title;
      const t2 = document.createElement('div');
      t2.className = 'mc-desc';
      t2.textContent = hint;
      box.appendChild(t1); box.appendChild(t2);
      card.appendChild(ic); card.appendChild(box);
      return card;
    };

    const exportCard = mkCard('export',
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M12 11v5m0 0 2-2m-2 2-2-2"/></svg>',
      t('dialog.ask_mode_export'), t('dialog.ask_mode_export_hint'));
    const compositeCard = mkCard('composite',
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 18 9 5 9-5"/></svg>',
      t('dialog.ask_mode_composite'), t('dialog.ask_mode_composite_hint'));
    body.appendChild(exportCard);
    body.appendChild(compositeCard);

    const footer = document.createElement('div');
    const cancel = btn(t('dialog.cancel'), 'btn sm', null);
    footer.appendChild(cancel);
    const { close } = showModal({ title: t('dialog.ask_mode_title', { name }), body, footer });
    cancel.addEventListener('click', close);

    exportCard.addEventListener('click', () => {
      close();
      api().export_sprites(name, true);
    });
    compositeCard.addEventListener('click', () => {
      close();
      api().start_composite_mode(name);
    });
  }

  function confirmExport(name) {
    const footer = document.createElement('div');
    const cancel = btn(t('dialog.cancel'), 'btn sm', null);
    const ok = btn(t('dialog.ok'), 'btn sm primary', null);
    footer.appendChild(cancel); footer.appendChild(ok);
    const { close } = showModal({
      title: t('dialog.export_confirm_title'),
      body: '<div class="desc">' + escapeHtml(t('dialog.export_confirm_msg', { name })) + '</div>',
      footer,
    });
    cancel.addEventListener('click', close);
    ok.addEventListener('click', () => { close(); api().export_sprites(name, false); });
  }

  function offerOpen(title, message, path) {
    const footer = document.createElement('div');
    const closeBtn = btn(t('dialog.close'), 'btn sm', null);
    const open = btn(t('dialog.open_output'), 'btn sm primary', null);
    footer.appendChild(closeBtn); footer.appendChild(open);
    const { close } = showModal({
      title,
      body: '<div class="desc">' + escapeHtml(message) + '</div>',
      footer,
    });
    closeBtn.addEventListener('click', close);
    open.addEventListener('click', () => { api().open_path(path); close(); });
  }

  // ═════════════ 后端事件 ═════════════

  on('status', (s) => setStatus(s.text, true));
  on('progress', showProgress);

  on('load_complete', (r) => {
    clearProgress();
    if (r.cancelled) {
      // 本次查找被新的加载请求打断
      setStatus(t('app.status.cancelled'), false);
      return;
    }
    if (r.success) {
      App.bundles = r.bundles || {};
      renderCharList();
      setStatus(t('app.status.loaded', { count: r.count }));
      toast(t('app.status.loaded', { count: r.count }), 'success');
      switchTab('info');
      renderInfoPage();
    } else {
      setErrorStatus();
      setStatus(t('app.status.load_failed'));
      toast((r.errors || []).join('\n'), 'error');
    }
  });

  on('analyze_complete', (r) => {
    clearProgress();
    if (r.error) { setErrorStatus(); setStatus(t('app.status.analyze_failed')); toast(r.error, 'error'); return; }
    if (r.has_components) showModeDialog(r.name);
    else confirmExport(r.name);
  });

  on('analyze_error', (r) => {
    clearProgress();
    setErrorStatus();
    setStatus(t('app.status.analyze_failed'));
    toast(t('dialog.analyze_error_msg', { name: r.name, msg: r.message }), 'error');
  });

  on('export_complete', (r) => {
    clearProgress();
    console.log(t('log.js_export_done', { name: r.name, count: r.count }));
    setStatus(t('app.status.export_done', { name: r.name, count: r.count }));
    toast(t('app.status.export_done', { name: r.name, count: r.count }), 'success');
    if (typeof r.export_count === 'number') {
      App.exportCount = r.export_count; // 后端累计值（权威）
      refreshExportCount();
    }
    offerOpen(
      t('dialog.export_complete_title'),
      t('dialog.export_complete_msg', { name: r.name, count: r.count, path: r.output_dir }),
      r.output_dir);
  });

  on('export_error', (r) => {
    clearProgress();
    setErrorStatus();
    setStatus(t('app.status.export_done', { name: r.name, count: 0 }));
    toast(t('dialog.export_complete_msg', { name: r.name, count: 0, path: '' }) + '\n' + r.message, 'error');
  });

  on('data_ready', (d) => {
    clearProgress();
    console.log(t('log.js_extract_done', { name: d.name, count: d.count }));
    App.characterData = d;
    App.selected.clear();
    App.thumbnails = {};
    sortParts(d); // 部件按前缀（首字母+数字）排序
    const ps = $('#parts-search');
    if (ps) ps.value = ''; // 切换角色后重置部件搜索
    renderParts(d);
    renderHierarchy(d.hierarchy);
    updateSelUI();
    switchTab('parts');
    setStatus(t('app.status.extract_done', { name: d.name, count: d.count }));
    toast(t('app.status.extract_done', { name: d.name, count: d.count }), 'success');
    api().get_thumbnails();
  });

  on('data_error', (r) => {
    clearProgress();
    setErrorStatus();
    setStatus(t('app.status.analyze_failed'));
    toast(t('dialog.process_error_msg', { msg: r.message }), 'error');
  });

  on('thumbnails_ready', (map) => {
    App.thumbnails = map || {};
    Object.keys(App.thumbnails).forEach((name) => {
      const el = App.partEls[name];
      if (!el) return;
      const img = document.createElement('img');
      img.src = App.thumbnails[name];
      el.thumb.innerHTML = '';
      el.thumb.appendChild(img);
    });
  });

  on('composite_done', (r) => {
    clearProgress();
    if (!r.ok) {
      if (r.error && r.error !== 'no_data' && r.error !== 'empty') {
        toast(t('dialog.composite_error_msg', { msg: r.error }), 'error');
      }
      return;
    }
    const img = $('#preview-img');
    img.src = r.data_url;
    img.hidden = false;
    $('#preview-empty').hidden = true;
    $('#preview-info').textContent = r.size[0] + ' × ' + r.size[1] + ' px';
    $('#preview-info').hidden = false;
    setStatus(t('app.status.composite_done'));
    // 缩放：首次合成适配（完整显示全图），后续合成保持当前缩放级别
    const firstPreview = !App.previewSize;
    App.previewSize = r.size;
    previewFit = computeFit();
    const zoomSlider = $('#zoom-slider');
    zoomSlider.disabled = false;
    if (firstPreview) {
      zoomSlider.value = 0;
      previewZoom = previewMinZoom();
    }
    applyPreviewZoom();
  });

  on('save_complete', (r) => {
    clearProgress();
    if (!r.ok) {
      toast(t('dialog.save_error_msg', { msg: r.error }), 'error');
      return;
    }
    setStatus(t('app.status.ready'));
    console.log(t('log.js_composite_saved', { path: r.path }));
    toast(t('dialog.save_success_msg', { path: r.path }), 'success');
    if (typeof r.export_count === 'number') {
      App.exportCount = r.export_count; // 保存合成图也计入累计导出
      refreshExportCount();
    }
    // 打开输出目录：打开文件所在目录（而非文件本身）
    offerOpen(t('dialog.save_success_title'), t('dialog.save_success_msg', { path: r.path }), r.dir || r.path);
  });

  on('cache_cleared', (r) => {
    clearProgress();
    App.characterData = null;
    App.selected.clear();
    clearPartsUI();
    clearPreview();
    switchTab('info');
    toast(t('log.temp_cleared', { path: r.temp_dir }), 'success');
  });

  on('output_cleared', (r) => {
    clearProgress();
    toast(t('log.output_cleared', { path: r.output_dir }), 'success');
  });

  on('log_cleared', (r) => {
    clearProgress();
    toast(t('log.log_cleared', { count: r.count }), 'success');
  });

  on('update_result', (r) => {
    clearProgress();
    if (r.status === 'available') {
      const footer = document.createElement('div');
      const closeBtn = btn(t('dialog.close'), 'btn sm', null);
      const go = btn(t('dialog.open_release'), 'btn sm primary', null);
      footer.appendChild(closeBtn); footer.appendChild(go);
      const { close } = showModal({
        title: t('dialog.update_available_title'),
        body: '<div class="desc">' + escapeHtml(t('dialog.update_available_msg', { new: r.latest, current: r.current })) + '</div>',
        footer,
      });
      closeBtn.addEventListener('click', close);
      go.addEventListener('click', () => { api().open_url(r.url); close(); });
      setStatus(t('app.status.ready'));
    } else if (!r.silent && r.status === 'latest') {
      setStatus(t('app.status.ready'));
      toast(t('dialog.update_latest_msg', { current: r.current }), 'success');
    } else if (!r.silent && r.status === 'error') {
      setStatus(t('app.status.ready'));
      toast(t('dialog.update_check_error_msg', { msg: r.message }), 'error');
    }
  });

  // ═════════════ 信息页 ═════════════

  // 信息板块：始终显示欢迎/指南（加载角色后不改变）
  function renderInfoPage() {
    const el = $('#info-content');
    const ver = App.info && App.info.version ? App.info.version : '';
    el.innerHTML =
      '<div class="info-hero">' +
      '<div class="hero-icon">' +
      '  <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '    <circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>' +
      '    <path d="M8.2 8.2 20 20M8.2 15.8 20 4"/>' +
      '  </svg>' +
      '</div>' +
      '<h2>' + t('info.welcome_title', { version: ver }) + '</h2>' +
      '<p class="lead">' + t('info.welcome_lead') + '</p>' +
      '<div class="guide-card">' +
      '  <h3>' + t('info.guide_title') + '</h3>' +
      '  <ol>' +
      '    <li><span class="step">1</span>' + t('info.guide_step1') + '</li>' +
      '    <li><span class="step">2</span>' + t('info.guide_step2') + '</li>' +
      '    <li><span class="step">3</span>' + t('info.guide_step3') + '</li>' +
      '    <li><span class="step">4</span>' + t('info.guide_step4') + '</li>' +
      '    <li><span class="step">5</span>' + t('info.guide_step5') + '</li>' +
      '  </ol>' +
      '</div>' +
      '<div class="guide-card">' +
      '  <h3>' + t('info.tips_title') + '</h3>' +
      '  <ul>' +
      '    <li>' + t('info.tip1') + '</li>' +
      '    <li>' + t('info.tip2') + '</li>' +
      '    <li>' + t('info.tip3') + '</li>' +
      '  </ul>' +
      '</div>' +
      '</div>';
  }

  // ═════════════ 关于页 ═════════════

  const _aboutIcons = {
    scissors: '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.2 8.2 20 20M8.2 15.8 20 4"/></svg>',
    tag: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r=".5"/></svg>',
    download: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6"/></svg>',
    user: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    play: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    branch: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>',
    code: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    repo: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="1"/><circle cx="16" cy="12" r="1"/><circle cx="8" cy="18" r="1"/></svg>',
    bug: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"/></svg>',
    heart: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8Z"/></svg>',
    external: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"/></svg>',
  };
  const _aI = (k) => _aboutIcons[k] || '';

  function renderAboutPage() {
    const el = $('#about-content');
    if (!el) return;
    const ver = App.info && App.info.version ? 'v' + App.info.version : '';
    el.innerHTML =
      '<div class="about-hero">' +
      '<div class="about-icon"><img src="assets/logo.ico" alt="logo"></div>' +
      '<h2>' + t('about.app_name') + '</h2>' +
      '<p class="about-version-line">' +
      '  <span class="about-ver">' + _aI('tag') + t('about.version_label', { version: ver }) + '</span>' +
      '</p>' +
      '<div class="about-export-badge">' +
      '  <span class="about-export-icon">' + _aI('download') + '</span>' +
      '  <div class="about-export-body">' +
      '    <span class="about-export-label">' + t('about.export_count') + '</span>' +
      '    <span class="about-export-num" id="about-export-count">' + App.exportCount + '</span>' +
      '  </div>' +
      '</div>' +
      '<button id="btn-about-update" class="btn sm ghost">' + _aI('refresh') + t('about.update_btn') + '</button>' +
      '</div>' +
      '<p class="about-desc">' + t('about.description') + '</p>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('user') + t('about.dev_title') + '</h3>' +
      '  <div class="about-row">' + t('about.dev_name') + '</div>' +
      '  <div class="about-link">' + _aI('play') + '<span class="about-link-label">' + t('about.dev_bilibili') + ': ' + t('about.dev_click') + ' →</span><button type="button" class="about-open bili" data-url="https://space.bilibili.com/511874938" title="' + t('about.dev_click') + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '  <div class="about-link">' + _aI('branch') + '<span class="about-link-label">' + t('about.dev_github') + ': ' + t('about.dev_click') + ' →</span><button type="button" class="about-open gh" data-url="https://github.com/paliku520" title="' + t('about.dev_click') + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '</div>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('code') + t('about.links_title') + '</h3>' +
      '  <div class="about-link">' + _aI('repo') + '<span class="about-link-label">' + t('about.links_repo') + '</span><button type="button" class="about-open" data-url="https://github.com/paliku520/Manosaba-character-extracter" title="' + t('about.dev_click') + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '  <div class="about-link">' + _aI('bug') + '<span class="about-link-label">' + t('about.links_issues') + '</span><button type="button" class="about-open" data-url="https://github.com/paliku520/Manosaba-character-extracter/issues" title="' + t('about.dev_click') + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '</div>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('heart') + t('about.thanks_title') + '</h3>' +
      '  <p class="about-thanks">' + t('about.thanks_text') + '</p>' +
      '</div>' +
      '<p class="about-copy">' + t('about.copyright') + '</p>' +
      '<p class="about-note">' + t('about.license_note') + '</p>';
  }

  // 关于页背景轮播（参考站 images/bg/01~45.webp，随机起始、定时切换）
  const ABOUT_BG_COUNT = 45;
  function aboutBgUrl(i) {
    return 'assets/bg/' + String(i + 1).padStart(2, '0') + '.webp';
  }
  function initAboutBg() {
    const layer = $('#about-bg-layer');
    if (!layer) return;
    let idx = Math.floor(Math.random() * ABOUT_BG_COUNT);
    layer.style.backgroundImage = 'url("' + aboutBgUrl(idx) + '")';
    setInterval(() => {
      idx = (idx + 1) % ABOUT_BG_COUNT;
      layer.style.opacity = 0;
      setTimeout(() => {
        layer.style.backgroundImage = 'url("' + aboutBgUrl(idx) + '")';
        layer.style.opacity = 1;
      }, 500);
    }, 8000);
  }

  async function onLoadClick() {
    const path = await api().select_directory();
    if (path) loadDir(path);
  }

  // ═════════════ 事件绑定 ═════════════

  function bindEvents() {
    $('#btn-load').addEventListener('click', onLoadClick);
    $('#btn-open-output').addEventListener('click', () => api().open_output());
    $('#btn-settings').addEventListener('click', openSettings);
    $('#btn-clear-cache').addEventListener('click', async () => {
      const okc = await confirmDialog(t('left.clear_cache_confirm_title'), t('left.clear_cache_confirm_msg'));
      if (okc) api().clear_cache();
    });
    $('#char-search').addEventListener('input', (e) => filterCharList(e.target.value));
    $('#parts-search').addEventListener('input', (e) => filterParts(e.target.value));

    $$('.tab').forEach((b) => b.addEventListener('click', () => switchTab(b.dataset.tab)));

    $('#btn-select-all').addEventListener('click', () => selectAll(true));
    $('#btn-deselect-all').addEventListener('click', () => selectAll(false));
    $('#btn-composite').addEventListener('click', doComposite);
    $('#btn-save').addEventListener('click', () => { if (App.characterData) api().save_composite(); });
    $('#btn-clear-preview').addEventListener('click', clearPreview);
    $('#auto-update').addEventListener('change', (e) => {
      App.autoUpdate = e.target.checked;
      if (App.autoUpdate && App.selected.size > 0) schedulePreview();
    });

    bindPreviewZoom();

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

  async function init() {
    if (!window.pywebview || !window.pywebview.api) {
      const el = document.createElement('div');
      el.className = 'no-bridge';
      el.innerHTML =
        '<h2>' + t('app.subtitle') + '</h2>' +
        '<p>本界面需要 PyWebView 环境。请通过 <code>python run.py</code> 启动应用（将使用系统 WebView2 渲染）。' +
        '在普通浏览器中打开时无法访问 Python 后端。</p>';
      document.body.appendChild(el);
      return;
    }
    try {
      const info = await window.pywebview.api.get_app_info();
      App.info = info;
      window.I18N.set(info.translations, info.current_lang, info.lang_names);
      $('#version-badge').textContent = 'v' + info.version;
      document.title = 'Manosaba Extracter v' + info.version;
      // 主题：以 settings.json（后端）为权威，localStorage 仅作旧版兜底
      let theme = 'dark';
      try { theme = localStorage.getItem('msx-theme') || theme; } catch (e) { /* ignore */ }
      if (info.theme === 'dark' || info.theme === 'light') theme = info.theme;
      applyTheme(theme);
      bindEvents();
      renderCharList();
      renderInfoPage();
      renderAboutPage();
      initAboutBg();
      App.exportCount = (typeof info.export_count === 'number') ? info.export_count : 0;
      App.useChineseNames = !!info.use_chinese_names;
      refreshExportCount();
      window.pywebview.api.check_update(true); // 静默检查更新
    } catch (e) {
      toast('初始化失败: ' + e, 'error');
    }
  }

  if (window.pywebview) {
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
  } else {
    window.addEventListener('pywebviewready', init);
  }
})();
