/* ============================================================
 * ui.js — 通用 UI 原语
 *   Toast 提示 / Modal / 按钮 / 确认框 / 状态栏 / 进度条（含任务栏）
 *   标签页切换 / 自绘下拉 / 悬停说明气泡 / 通用对话框 / 标题栏
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, $$, t, api, escapeHtml, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const enterPreviewMode = (...a) => MCE.enterPreviewMode(...a);

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

  function showModal({ title, titleKey, body, footer, className }) {
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    const modal = document.createElement('div');
    modal.className = 'modal' + (className ? ' ' + className : '');

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
    // 点击模态外部不关闭，需通过按钮 / ✕ / Esc 显式操作
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
    App.loading = true;
    App._progressPhase = (p && p.phase) || '';
    const wrap = $('#progress-wrap');
    wrap.hidden = false;
    const pct = p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;
    $('#progress-bar').style.width = pct + '%';
    // 进度条只显示百分比，避免与状态栏文本重复
    $('#progress-label').textContent = pct + '%';
    // 合成（composite）不反映到任务栏
    if (App._progressPhase !== 'composite') taskbarProgress(pct);
  }
  function clearProgress() {
    const wasVisible = !$('#progress-wrap').hidden;
    const phase = App._progressPhase || '';
    App.loading = false;
    App._progressPhase = '';
    $('#progress-wrap').hidden = true;
    // 读条完成后任务栏黄色闪烁吸引注意（无读条时仅防御性调用，不闪烁；合成不闪烁）
    if (wasVisible && phase !== 'composite') taskbarDone();
  }

  // 任务栏（仅 Electron / Windows 原生；非 Electron 环境静默跳过）
  // 读条期间在任务栏图标显示进度；读条完成后任务栏黄色闪烁（启动 splash 走 setSplashProgress，不触发）
  // 注意：Electron setProgressBar 接收 0~1 小数，这里把 0~100 的百分比换算后传入
  function taskbarProgress(pct) {
    const tb = window.__electron && window.__electron.taskbar;
    if (tb && tb.progress) tb.progress(pct / 100);
  }
  function taskbarDone() {
    const tb = window.__electron && window.__electron.taskbar;
    if (tb && tb.flash) tb.flash();
  }

  // 标签页
  const TAB_ORDER = ['info', 'parts', 'hierarchy', 'about'];

  // active 指示条移动到当前 tab（左右滑动动画由 CSS transition 驱动）
  function moveTabIndicator() {
    const tabs = $('.tabs');
    const active = tabs && tabs.querySelector('.tab.active');
    const ind = tabs && tabs.querySelector('.tab-indicator');
    if (!tabs || !active || !ind) return;
    ind.style.left = active.offsetLeft + 'px';
    ind.style.width = active.offsetWidth + 'px';
  }

  // 初始化 tab 指示条
  function initTabIndicator() {
    const tabs = $('.tabs');
    if (!tabs || tabs.querySelector('.tab-indicator')) return;
    const ind = document.createElement('span');
    ind.className = 'tab-indicator';
    tabs.appendChild(ind);
    moveTabIndicator();
    window.addEventListener('resize', moveTabIndicator);
  }

  function switchTab(name) {
    const prev = App._activeTab || null;
    // 重复点击当前 tab：直接返回，避免删除 data-dir 触发动画切换（fadeIn 重放）导致面板闪烁
    if (prev === name) return;
    // 长矛彩蛋锁定期间：只能停留在组件选择界面（允许回到 parts，禁止离开）
    if (MCE.spear.active && name !== 'parts') return;
    App._activeTab = name;
    $$('.tab').forEach((b) => b.classList.toggle('active', b.dataset.tab === name));
    $$('.tab-panel').forEach((p) => {
      const active = p.id === 'tab-' + name;
      if (active) {
        // 滑动方向：新 tab 在旧 tab 右侧 → 从右滑入；左侧 → 从左滑入；首次无方向
        let dir = '';
        if (prev && prev !== name) {
          const iOld = TAB_ORDER.indexOf(prev);
          const iNew = TAB_ORDER.indexOf(name);
          dir = (iNew > iOld) ? 'right' : 'left';
        }
        if (dir) p.dataset.dir = dir;
        else delete p.dataset.dir;
      }
      p.classList.toggle('active', active);
    });
    moveTabIndicator();
  }

  // ═════════════ 自绘下拉 ═════════════

  // 主题色 / 通用下拉互斥：同一时刻只允许一个下拉展开
  // （ui.js 的 createDropdown 与 settings.js 的 createAccentPicker 共用本注册表）
  let activeColorPicker = null;

  function closeActiveDropdown() {
    if (activeColorPicker) activeColorPicker.closeList();
  }

  document.addEventListener('click', () => {
    closeActiveDropdown();
  });

  // 通用自绘下拉（软件风格，替代原生 <select>；复用 color-picker 样式与互斥逻辑）
  function createDropdown({ options, value }) {
    const wrap = document.createElement('div');
    wrap.className = 'color-picker';
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'color-picker-btn';
    const label = document.createElement('span');
    label.className = 'cp-label';
    const caret = document.createElement('span');
    caret.className = 'cp-caret';
    caret.innerHTML =
      '<svg viewBox="0 0 16 16" width="12" height="12"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
    btn.appendChild(label); btn.appendChild(caret);
    wrap.appendChild(btn);

    const list = document.createElement('div');
    list.className = 'color-picker-list';
    const items = {};
    options.forEach((o) => {
      const it = document.createElement('button');
      it.type = 'button';
      it.className = 'color-picker-item';
      it.dataset.value = o.value;
      const nm = document.createElement('span');
      nm.className = 'cp-name';
      nm.textContent = o.label;
      it.appendChild(nm);
      it.addEventListener('click', () => {
        api.value = o.value;
        api.closeList();
        wrap.focus();
      });
      list.appendChild(it);
      items[o.value] = it;
    });
    wrap.appendChild(list);

    let current = value;
    // 当前语言下取选项 label 的函数；语言切换后由 refreshLabels 更新，
    // 保证赋值器（set value）始终用最新语言的标签，而非创建时缓存的 options
    let labelFor = (v) => {
      const o = options.find((x) => x.value === v);
      return o ? o.label : v;
    };
    // 打开时让下拉以视口为准 fixed 定位，避免被 .sn-panels 等带 overflow 的父级裁剪
    const onScroll = () => api.positionList();
    const onResize = () => api.positionList();
    const api = {
      el: wrap,
      get value() { return current; },
      set value(v) {
        if (!(v in items)) return;
        current = v;
        label.textContent = labelFor(v);
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
        if (activeColorPicker && activeColorPicker !== api) activeColorPicker.closeList();
        activeColorPicker = api;
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
      refreshLabels(getLabel) {
        // 语言/主题切换后刷新选项文本（选项集合不变，仅 label 变化）
        labelFor = getLabel;
        Object.keys(items).forEach((k) => {
          const nm = items[k].querySelector('.cp-name');
          if (nm) nm.textContent = getLabel(k);
        });
        label.textContent = getLabel(current);
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

  // ═════════════ 悬停说明气泡 ═════════════

  // ── 悬停说明气泡（共享单例；portal 到 body + fixed 定位，规避弹窗滚动容器裁剪）──
  let _uiTipEl = null;
  let _uiTipAnchor = null;   // 当前气泡锚点（同一元素内部移动时不重建气泡）

  function _ensureUiTip() {
    if (_uiTipEl && _uiTipEl.isConnected) return _uiTipEl;
    const el = document.createElement('div');
    el.className = 'ui-tip';
    document.body.appendChild(el);
    _uiTipEl = el;
    return el;
  }

  // 在锚点附近显示气泡：优先下方，放不下自动改上方；水平方向夹紧到视口内
  function _showUiTip(anchor, text) {
    const tip = _ensureUiTip();
    tip.textContent = text;
    _uiTipAnchor = anchor;
    tip.classList.remove('show');
    // visibility:hidden 时仍有布局，可先测量尺寸再定位
    const r = anchor.getBoundingClientRect();
    const gap = 8;
    const tw = tip.offsetWidth;
    const th = tip.offsetHeight;
    let left = Math.round(r.left + r.width / 2 - tw / 2);
    left = Math.max(gap, Math.min(left, window.innerWidth - tw - gap));
    let top = r.bottom + gap;
    if (top + th > window.innerHeight - gap) {
      top = r.top - th - gap;                    // 下方放不下 → 改到上方
    }
    top = Math.max(gap, top);
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
    void tip.offsetWidth;                        // 强制 reflow：保证有淡入过渡起始帧
    tip.classList.add('show');
  }

  function _hideUiTip() {
    _uiTipAnchor = null;
    if (_uiTipEl) _uiTipEl.classList.remove('show');
  }

  // 统一提示入口：把提示文本写进 data-tip（同时移除原生 title，避免系统气泡与自定义气泡重叠显示）；
  // 传空文本则清除提示。所有带 data-tip 的元素由下方全局委托统一弹出同一套 .ui-tip 气泡。
  function setTipText(el, text) {
    if (!el) return;
    el.removeAttribute('title');
    if (text) el.setAttribute('data-tip', text);
    else el.removeAttribute('data-tip');
  }

  // 全局委托：[data-tip] 元素悬停 / 键盘聚焦时统一弹出 .ui-tip 气泡（全项目提示样式唯一）
  const _tipTarget = (node) => (node && node.closest) ? node.closest('[data-tip]') : null;
  let _uiTipMuted = null;   // 刚被点击的锚点：指针离开前不再弹出，避免点击后气泡残留
  document.addEventListener('pointerover', (e) => {
    const el = _tipTarget(e.target);
    if (!el || el === _uiTipAnchor || el === _uiTipMuted) return;
    _showUiTip(el, el.getAttribute('data-tip') || '');
  });
  document.addEventListener('pointerout', (e) => {
    const el = _tipTarget(e.target);
    if (!el) return;
    const to = e.relatedTarget;
    if (to && el.contains(to)) return;            // 仍在同一提示元素内部，不收起
    if (el === _uiTipMuted) _uiTipMuted = null;   // 指针离开后恢复提示
    if (el === _uiTipAnchor) _hideUiTip();
  });
  document.addEventListener('focusin', (e) => {
    const el = _tipTarget(e.target);
    // 鼠标点击获得的焦点不弹气泡（:focus-visible 仅键盘聚焦命中），避免点击后气泡残留
    if (!el || !el.matches(':focus-visible')) return;
    _showUiTip(el, el.getAttribute('data-tip') || '');
  });
  document.addEventListener('focusout', (e) => {
    const el = _tipTarget(e.target);
    if (el && el === _uiTipAnchor) _hideUiTip();
  });

  // 点击任意处（含关闭弹窗）时收起气泡；被点的提示元素在被移出前保持静默
  document.addEventListener('pointerdown', (e) => {
    _uiTipMuted = _tipTarget(e.target);
    _hideUiTip();
  }, true);

  // 设置行内悬停说明：触发按钮复用「部件选择页」的 .clip-hint 外观（圆形 ? + 悬停高亮）；
  // 说明文字写入 data-tip，由上面的全局委托统一弹出 .ui-tip 气泡。
  // 同时挂上 data-i18n-title / data-i18n-aria：语言切换时 applyDom 会把提示与 aria-label 一并刷新
  // （否则弹窗内这些提示会停留在创建时的旧语言）。
  function tipIcon(titleKey) {
    const el = document.createElement('span');
    el.className = 'clip-hint';
    el.setAttribute('role', 'note');
    el.setAttribute('tabindex', '0');
    el.setAttribute('data-i18n-title', titleKey);
    el.setAttribute('data-i18n-aria', titleKey);
    el.setAttribute('aria-label', t(titleKey));
    const q = document.createElement('span');
    q.className = 'ch-q';
    q.setAttribute('aria-hidden', 'true');
    q.textContent = '?';
    el.appendChild(q);
    setTipText(el, t(titleKey));
    // 嵌在 .switch 的 <label> 内：点击不应触发开关切换（仅用于悬停/聚焦查看）
    el.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); });
    return el;
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

  function showNoComponentDialog(name) {
    const body = document.createElement('div');
    const desc = document.createElement('div');
    desc.className = 'desc';
    desc.textContent = t('dialog.no_component_msg');
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

    const previewCard = mkCard('preview',
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
      t('dialog.no_component_preview'), t('dialog.no_component_preview_hint'));
    const exportCard = mkCard('export',
      '<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M12 11v5m0 0 2-2m-2 2-2-2"/></svg>',
      t('dialog.no_component_export'), t('dialog.no_component_export_hint'));
    body.appendChild(previewCard);
    body.appendChild(exportCard);

    const footer = document.createElement('div');
    const cancel = btn(t('dialog.cancel'), 'btn sm', null);
    footer.appendChild(cancel);
    const { close } = showModal({ title: t('dialog.no_component_title', { name }), body, footer });
    cancel.addEventListener('click', () => { close(); setStatus(t('app.status.ready'), false); });

    previewCard.addEventListener('click', () => {
      close();
      enterPreviewMode({ name });
    });
    exportCard.addEventListener('click', () => {
      close();
      api().export_sprites(name, false);
    });
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

  // ═════════════ 标题栏 ═════════════

  // 标题栏：应用名 + 版本（随语言切换）
  function updateTitleBar() {
    const el = $('#tb-title');
    if (el) el.textContent = t('app.title') + ' v' + (App.info ? App.info.version : '');
  }

  // 窗口最大化状态：切换标题栏按钮图标 + 控制缩放手柄显隐
  function setMaxState(maximized) {
    App.windowMaximized = !!maximized;
    const btn = $('#tb-max');
    if (btn) {
      btn.innerHTML = App.windowMaximized
        ? '<svg viewBox="0 0 10 10" width="10" height="10"><path d="M2.5 2.5h5v5h-5z" fill="none" stroke="currentColor" stroke-width="1.2"/><path d="M1.5 3.5V1.5h5" stroke="currentColor" stroke-width="1.2" fill="none"/></svg>'
        : '<svg viewBox="0 0 10 10" width="10" height="10"><rect x="1.5" y="1.5" width="7" height="7" fill="none" stroke="currentColor" stroke-width="1.2"/></svg>';
    }
    const rh = $('#resize-handles');
    if (rh) rh.style.display = App.windowMaximized ? 'none' : '';
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.toast = toast;
  MCE.showModal = showModal;
  MCE.btn = btn;
  MCE.confirmDialog = confirmDialog;
  MCE.setStatus = setStatus;
  MCE.setErrorStatus = setErrorStatus;
  MCE.refreshExportCount = refreshExportCount;
  MCE.showProgress = showProgress;
  MCE.clearProgress = clearProgress;
  MCE.taskbarProgress = taskbarProgress;
  MCE.taskbarDone = taskbarDone;
  MCE.moveTabIndicator = moveTabIndicator;
  MCE.initTabIndicator = initTabIndicator;
  MCE.switchTab = switchTab;
  MCE.createDropdown = createDropdown;
  MCE.setTipText = setTipText;
  MCE.tipIcon = tipIcon;
  MCE.showModeDialog = showModeDialog;
  MCE.showNoComponentDialog = showNoComponentDialog;
  MCE.offerOpen = offerOpen;
  MCE.updateTitleBar = updateTitleBar;
  MCE.setMaxState = setMaxState;
  // 下拉互斥注册表（settings.js 的 createAccentPicker 共用）
  MCE.dropdown = {
    setActive(dd) {
      if (activeColorPicker && activeColorPicker !== dd) activeColorPicker.closeList();
      activeColorPicker = dd;
    },
    closeActive: closeActiveDropdown,
  };
})();
