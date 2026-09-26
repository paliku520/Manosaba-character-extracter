/* ============================================================
 * preview.js — 实时预览（合成触发）/ 缩放 / 平移 / 放大预览查看器
 *              + 无组件角色的精灵预览模式
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * 说明：原 app.js 里 on('part_preview_ready') / on('composite_done') 的处理体
 *       依赖本模块私有状态（_lb / previewZoom / previewFit），故下沉为
 *       handlePartPreviewReady / handleCompositeDone 由 events.js 转调。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, api, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const toast = (...a) => MCE.toast(...a);
  const setStatus = (...a) => MCE.setStatus(...a);
  const clearProgress = (...a) => MCE.clearProgress(...a);
  const taskbarProgress = (...a) => MCE.taskbarProgress(...a);
  const taskbarDone = (...a) => MCE.taskbarDone(...a);
  const setTipText = (...a) => MCE.setTipText(...a);
  const sketchTextArg = (...a) => MCE.sketchTextArg(...a);
  const sketchSizeArg = (...a) => MCE.sketchSizeArg(...a);
  const sketchAlignArg = (...a) => MCE.sketchAlignArg(...a);

  // ── 无组件角色精灵预览模式 ──────────────────────────────

  function enterPreviewMode(r) {
    App.previewMode = true;
    App.previewData = [];
    App.previewThumbs = {};
    App.previewSel.clear();
    App.loading = true;   // 预览提取进行中：期间再次点击会先确认取消，避免并发提取
    // 等待精灵加载完成（preview_ready）后再切换到预览视图
    api().preview_bundle(r.name);
  }

  function updatePreviewCount() {
    const total = App.previewData.length;
    $('#preview-count').textContent = total ? t('preview.selected_count', { count: App.previewSel.size, total }) : '';
    const btnSel = $('#btn-prev-export-sel');
    if (btnSel) btnSel.disabled = App.previewSel.size === 0;
  }

  // 组件选择页面内的缩略图加载进度条
  function showSpritePreviewProgress(p) {
    const wrap = $('#sprite-preview-progress');
    if (!wrap) return;
    wrap.hidden = false;
    const pct = p && p.total > 0 ? Math.round((p.current / p.total) * 100) : 0;
    $('#sprite-preview-progress-bar').style.width = pct + '%';
    $('#sprite-preview-progress-label').textContent = t('preview.loading_thumbs') + ' ' + pct + '%';
    taskbarProgress(pct);
  }
  function hideSpritePreviewProgress() {
    const wrap = $('#sprite-preview-progress');
    if (wrap && !wrap.hidden) {
      wrap.hidden = true;
      taskbarDone();
    }
  }

  function renderPreviewGrid() {
    const grid = $('#preview-grid');
    grid.innerHTML = '';
    // 按文件名升序（自然排序，n_n.png 数字感知）
    const list = [...App.previewData].sort((a, b) =>
      a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }));
    grid.hidden = list.length === 0;
    $('#sprite-preview-empty').hidden = list.length > 0;
    updatePreviewCount();
    list.forEach((s) => {
      const item = document.createElement('div');
      item.className = 'sprite-preview-item' + (App.previewSel.has(s.name) ? ' selected' : '');
      item.dataset.name = s.name;
      const thumb = document.createElement('div');
      thumb.className = 'sprite-preview-thumb';
      const url = App.previewThumbs[s.name];
      if (url) {
        const img = document.createElement('img');
        img.src = url;
        img.alt = s.name;
        thumb.appendChild(img);
      }
      const meta = document.createElement('div');
      meta.className = 'sprite-preview-meta';
      const nameEl = document.createElement('div');
      nameEl.className = 'sprite-preview-name';
      nameEl.textContent = s.name;
      setTipText(nameEl, s.name);   // 名称被省略号截断时，悬停用统一气泡显示完整名称
      const sizeEl = document.createElement('div');
      sizeEl.className = 'sprite-preview-size';
      sizeEl.textContent = (s.size && s.size[0]) ? s.size[0] + '×' + s.size[1] : '';
      meta.appendChild(nameEl);
      meta.appendChild(sizeEl);
      item.appendChild(thumb);
      item.appendChild(meta);
      item.addEventListener('click', () => togglePreviewSel(s.name));
      // 右键精灵 → 放大预览（无组件角色没有位置数据，直接展示精灵本身）
      item.addEventListener('contextmenu', (e) => {
        if (MCE.spear.active) return;
        const url = App.previewThumbs[s.name];
        if (!url) return;
        e.preventDefault();
        e.stopPropagation();
        openLightbox({ src: url, kind: 'sprite', name: s.name });
      });
      grid.appendChild(item);
    });
  }

  function togglePreviewSel(name) {
    if (App.previewSel.has(name)) App.previewSel.delete(name);
    else App.previewSel.add(name);
    const item = document.querySelector('#preview-grid .sprite-preview-item[data-name="' + CSS.escape(name) + '"]');
    if (item) item.classList.toggle('selected', App.previewSel.has(name));
    updatePreviewCount();
  }

  function clearPreview() {
    closePreviewLightbox();   // 预览已清空：同步收起放大叠加层
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
    const pc = previewViewport();
    if (pc) { pc.classList.remove('zoomed', 'dragging'); pc.scrollLeft = 0; pc.scrollTop = 0; }
  }

  // ═════════════ 预览缩放 / 平移 ═════════════

  // 滚动/滚轮/拖拽都作用在“预览滚动容器”上：卡片本身不滚动，滚动条因而落在卡片之外
  function previewViewport() {
    return $('#preview-scroll') || $('#preview');
  }

  const ZOOM_MAX = 4;          // 最大缩放 400%
  let previewZoom = 1;         // 当前缩放（1 = 100%，最小值以总分辨率为准 = 适配）
  let previewFit = 1;          // 适配（完整显示全图）所需缩放
  let previewDragging = null;  // 拖动平移状态

  function computeFit() {
    const size = App.previewSize;
    const container = previewViewport();
    if (!size || !container) return 1;
    const cw = container.clientWidth - 2;  // 减去预览卡片左右 border
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
    const container = previewViewport();
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
    const container = previewViewport();
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
    const container = previewViewport();
    previewDragging = {
      x: e.clientX, y: e.clientY,
      sl: container.scrollLeft, st: container.scrollTop,
    };
    container.classList.add('dragging');
    e.preventDefault();
  }

  function onPreviewMouseMove(e) {
    if (!previewDragging) return;
    const container = previewViewport();
    container.scrollLeft = previewDragging.sl - (e.clientX - previewDragging.x);
    container.scrollTop = previewDragging.st - (e.clientY - previewDragging.y);
    e.preventDefault();
  }

  function onPreviewMouseUp() {
    if (!previewDragging) return;
    previewDragging = null;
    const c = previewViewport();
    if (c) c.classList.remove('dragging');
  }

  function bindPreviewZoom() {
    const container = previewViewport();
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
    // 右键预览区 → 整屏放大（叠加层 + 预览图居中）
    container.addEventListener('contextmenu', (e) => {
      if (MCE.spear.active) return;   // 长矛彩蛋锁定期间不放大
      e.preventDefault();
      openPreviewLightbox();
    });
    document.addEventListener('mousemove', onPreviewMouseMove);
    document.addEventListener('mouseup', onPreviewMouseUp);
    window.addEventListener('resize', () => {
      if (App.previewSize && $('#zoom-slider').value === '0') applyPreviewZoom();
    });
  }

  // ── 放大预览：整屏叠加层（可滚轮缩放 / 拖拽平移 + 底部操作卡片）──
  // openLightbox({ src }) 传 null 时先打开叠加层显示“生成中”（部件预览要等后端合成），
  // 拿到图片后由 lbSetImage() 填入。kind='composite' 时才提供「导出」（导出当前合成图）。
  let _lb = null;                 // 当前查看器状态（null = 未打开）
  const LB_MIN_RATIO = 0.5;       // 最小缩放 = 适配的一半
  const LB_STEP = 1.25;           // 按钮每次缩放的倍率
  const LB_MAX_SCALE = 16;        // 绝对上限（大画布适配后很小，仍能放大看细节）

  const LB_ICONS = {
    zoomIn: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M11 8v6M8 11h6"/>',
    zoomOut: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5M8 11h6"/>',
    fit: '<path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/>',
    export: '<path d="M12 3v12m0 0 4-4m-4 4-4-4M4 21h16"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
  };

  function lbIcon(name) {
    return '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" ' +
      'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' +
      (LB_ICONS[name] || '') + '</svg>';
  }

  function closePreviewLightbox() {
    const lb = _lb;
    if (!lb) return;
    _lb = null;
    document.removeEventListener('keydown', onLightboxEsc, true);
    document.removeEventListener('pointermove', lb.onMove);
    document.removeEventListener('pointerup', lb.onUp);
    lb.root.classList.remove('show');
    setTimeout(() => lb.root.remove(), 220);   // 等淡出过渡结束再移除
  }

  function onLightboxEsc(e) {
    if (!_lb || e.key !== 'Escape') return;
    e.preventDefault();
    e.stopPropagation();
    closePreviewLightbox();
  }

  // 应用缩放/平移：图片绝对定位在舞台中心，再按 (dx, dy) 平移、按 scale 缩放
  function lbApply() {
    const lb = _lb;
    if (!lb) return;
    lb.img.style.transform =
      'translate(-50%, -50%) translate(' + lb.dx + 'px, ' + lb.dy + 'px) scale(' + lb.scale + ')';
    if (lb.zoomLabel) {
      lb.zoomLabel.textContent = Math.abs(lb.scale - lb.fit) < 1e-3
        ? t('parts.zoom_fit')
        : Math.round(lb.scale / lb.fit * 100) + '%';
    }
  }

  // 适配：整图完整可见、居中不平移
  function lbFit() {
    const lb = _lb;
    if (!lb || !lb.img.naturalWidth) return;
    const sw = lb.stage.clientWidth;
    const sh = lb.stage.clientHeight;
    if (sw <= 0 || sh <= 0) return;
    lb.fit = Math.min(sw / lb.img.naturalWidth, sh / lb.img.naturalHeight);
    lb.scale = lb.fit;
    lb.dx = 0;
    lb.dy = 0;
    lbApply();
  }

  // 以舞台内 (cx, cy) 为中心缩放（默认舞台中心）：保持该点下的内容不动
  function lbZoomAt(factor, cx, cy) {
    const lb = _lb;
    if (!lb || !lb.fit) return;
    const next = Math.max(lb.fit * LB_MIN_RATIO, Math.min(LB_MAX_SCALE, lb.scale * factor));
    if (Math.abs(next - lb.scale) < 1e-6) return;
    const k = next / lb.scale;
    const ox = (cx === undefined ? lb.stage.clientWidth / 2 : cx) - lb.stage.clientWidth / 2;
    const oy = (cy === undefined ? lb.stage.clientHeight / 2 : cy) - lb.stage.clientHeight / 2;
    lb.dx += (ox - lb.dx) * (1 - k);
    lb.dy += (oy - lb.dy) * (1 - k);
    lb.scale = next;
    lbApply();
  }

  // 填入图片（同步打开时直接给 src；部件预览等后端返回后再调用）
  function lbSetImage(dataUrl) {
    const lb = _lb;
    if (!lb || !dataUrl) return;
    const loading = lb.stage.querySelector('.lightbox-loading');
    if (loading) loading.remove();
    lb.img.hidden = false;
    lb.img.addEventListener('load', lbFit, { once: true });
    lb.img.src = dataUrl;
    lb.zoomBtns.forEach((b) => { b.disabled = false; });
    if (lb.img.complete) lbFit();
  }

  function openLightbox(opts) {
    const src = (opts && opts.src) || null;
    const kind = (opts && opts.kind) || 'image';
    const name = (opts && opts.name) || null;   // 精灵预览时记录当前精灵名（供「导出当前」使用）
    closePreviewLightbox();           // 防御性：先收回上一次
    // 上一次可能仍在淡出（延迟移除）：直接清掉，保证同一时刻只有一个查看器
    document.querySelectorAll('.preview-lightbox').forEach((el) => el.remove());

    const root = document.createElement('div');
    root.className = 'preview-lightbox';

    const stage = document.createElement('div');
    stage.className = 'lightbox-stage';
    const img = document.createElement('img');
    img.className = 'lightbox-img';
    img.alt = 'preview';
    img.hidden = !src;
    stage.appendChild(img);
    if (!src) {
      const loading = document.createElement('div');
      loading.className = 'lightbox-loading';
      loading.textContent = t('parts.lightbox_loading');
      stage.appendChild(loading);
    }

    const zone = document.createElement('div');
    zone.className = 'lightbox-bottom';
    const hint = document.createElement('div');
    hint.className = 'lightbox-hint';
    hint.textContent = t('parts.lightbox_hint');
    const bar = document.createElement('div');
    bar.className = 'lightbox-bar';
    const zoomLabel = document.createElement('span');
    zoomLabel.className = 'lightbox-zoom';

    const mkBtn = (iconName, key, cls, onClick) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'btn sm' + (cls ? ' ' + cls : '');
      b.setAttribute('aria-label', t(key));
      b.innerHTML = lbIcon(iconName) + '<span></span>';
      b.querySelector('span').textContent = t(key);
      b.addEventListener('click', (e) => { e.stopPropagation(); onClick(); });
      return b;
    };
    const btnOut = mkBtn('zoomOut', 'parts.lightbox_zoom_out', 'ghost', () => lbZoomAt(1 / LB_STEP));
    const btnIn = mkBtn('zoomIn', 'parts.lightbox_zoom_in', 'ghost', () => lbZoomAt(LB_STEP));
    const btnFit = mkBtn('fit', 'parts.lightbox_fit', 'ghost', lbFit);
    bar.appendChild(zoomLabel);
    bar.appendChild(btnOut);
    bar.appendChild(btnIn);
    bar.appendChild(btnFit);
    const zoomBtns = [btnOut, btnIn, btnFit];
    // 导出：合成预览 → 保存合成图；无组件精灵预览 → 导出精灵；部件预览没有可导出对象，不提供
    if (kind === 'composite') {
      const b = mkBtn('export', 'parts.lightbox_export', 'primary', dispatchLightboxExport);
      bar.appendChild(b);
      zoomBtns.push(b);
    } else if (kind === 'sprite') {
      // 无组件预览：导出“当前正在查看的这一张”精灵
      const b = mkBtn('export', 'preview.lightbox_export_current', 'primary', dispatchLightboxExport);
      bar.appendChild(b);
      zoomBtns.push(b);
    }
    bar.appendChild(mkBtn('close', 'parts.lightbox_close', '', closePreviewLightbox));
    if (!src) zoomBtns.forEach((b) => { b.disabled = true; });   // 生成中先禁用（除关闭外）

    zone.appendChild(hint);
    zone.appendChild(bar);
    root.appendChild(stage);
    root.appendChild(zone);
    document.body.appendChild(root);

    const lb = {
      root, stage, img, kind, name, zoomLabel, zoomBtns,
      scale: 1, fit: 1, dx: 0, dy: 0, drag: null, moved: false,
      onMove: null, onUp: null,
    };
    _lb = lb;

    // 滚轮缩放：以光标位置为中心
    stage.addEventListener('wheel', (e) => {
      e.preventDefault();
      const r = stage.getBoundingClientRect();
      lbZoomAt(e.deltaY < 0 ? 1.1 : 1 / 1.1, e.clientX - r.left, e.clientY - r.top);
    }, { passive: false });
    // 拖拽平移（左键；拖拽过的这一次不触发“点击关闭”）
    stage.addEventListener('pointerdown', (e) => {
      if (e.button !== 0 || !lb.img.naturalWidth) return;
      lb.drag = { x: e.clientX, y: e.clientY, dx: lb.dx, dy: lb.dy };
      lb.moved = false;
      stage.classList.add('grabbing');
      e.preventDefault();
    });
    lb.onMove = (e) => {
      if (!lb.drag) return;
      const mx = e.clientX - lb.drag.x;
      const my = e.clientY - lb.drag.y;
      if (!lb.moved && Math.abs(mx) + Math.abs(my) > 4) lb.moved = true;
      lb.dx = lb.drag.dx + mx;
      lb.dy = lb.drag.dy + my;
      lbApply();
    };
    lb.onUp = () => {
      if (!lb.drag) return;
      lb.drag = null;
      stage.classList.remove('grabbing');
    };
    document.addEventListener('pointermove', lb.onMove);
    document.addEventListener('pointerup', lb.onUp);
    // 点击空白处关闭；点在底部操作卡片上不关闭
    root.addEventListener('click', (e) => {
      if (e.target.closest('.lightbox-bar')) return;
      if (lb.moved) { lb.moved = false; return; }   // 刚拖拽过，忽略这一次点击
      closePreviewLightbox();
    });
    root.addEventListener('contextmenu', (e) => { e.preventDefault(); closePreviewLightbox(); });
    document.addEventListener('keydown', onLightboxEsc, true);

    void root.offsetWidth;            // 强制 reflow：先渲染隐藏初始态，再加 .show 触发淡入
    root.classList.add('show');
    if (src) {
      img.src = src;
      img.addEventListener('load', lbFit, { once: true });
      if (img.complete) lbFit();
    }
    return lb;
  }

  // 打开当前合成图的放大预览（右键预览区）
  function openPreviewLightbox() {
    const img = $('#preview-img');
    const src = (img && !img.hidden) ? img.getAttribute('src') : null;
    if (!src) return;                 // 无预览图时不弹出
    openLightbox({ src, kind: 'composite' });
  }

  // 部件放大预览：后端用“合成逻辑 + 临时画布”把该部件画在它的真实位置（不在画面中央）
  function openPartLightbox(name) {
    if (MCE.spear.active || !api()) return;
    openLightbox({ src: null, kind: 'part' });   // 先开叠加层显示“生成中”
    api().preview_part(name);
  }

  // 查看器内的「导出」按来源分发：合成预览 → 保存合成图；无组件精灵预览 → 导出当前这张精灵
  function dispatchLightboxExport() {
    const lb = _lb;
    const kind = lb ? lb.kind : null;
    if (kind === 'sprite') {
      const name = lb.name;                      // 当前正在查看的精灵
      closePreviewLightbox();
      if (name && api()) api().export_preview(App.currentName, [name]);
      return;
    }
    closePreviewLightbox();
    if (kind === 'composite' && App.characterData) api().save_composite();
  }

  // ═════════════ 合成触发 ═════════════

  function schedulePreview() {
    clearTimeout(App.previewTimer);
    App.previewTimer = setTimeout(() => {
      if (!App.characterData || App.selected.size === 0) return;
      api().composite(Array.from(App.selected), sketchTextArg(), sketchSizeArg(), sketchAlignArg());
    }, 500);
  }

  function doComposite() {
    if (!App.characterData) return;
    if (App.selected.size === 0) {
      toast(t('parts.no_selection_hint'), 'warning');
      return;
    }
    // 手动“生成合成图像”：取消待执行的自动更新防抖，立即按最新选择合成（恢复正常）
    clearTimeout(App.previewTimer);
    console.log(t('log.js_composite_start', { count: App.selected.size }));
    api().composite(Array.from(App.selected), sketchTextArg(), sketchSizeArg(), sketchAlignArg());
  }

  // ═════════════ 后端事件处理体（由 events.js 转调）═════════════

  // 流式：填充某个精灵缩略图（不重建整网格），并把尺寸标签实时更新为实际显示尺寸
  function _setPreviewThumb(name, url) {
    App.previewThumbs[name] = url;
    const item = document.querySelector('#preview-grid .sprite-preview-item[data-name="' + CSS.escape(name) + '"]');
    const thumb = item && item.querySelector('.sprite-preview-thumb');
    if (thumb && !thumb.querySelector('img')) {
      const img = document.createElement('img');
      img.src = url;
      img.alt = name;
      img.onload = () => {
        if (item && img.naturalWidth) {
          const sizeEl = item.querySelector('.sprite-preview-size');
          if (sizeEl) sizeEl.textContent = img.naturalWidth + '×' + img.naturalHeight;
        }
      };
      thumb.appendChild(img);
    }
  }

  // 部件放大预览（临时画布已生成）：填入叠加层；失败则关闭并提示
  function handlePartPreviewReady(r) {
    if (!_lb || _lb.kind !== 'part') return;
    if (!r || !r.ok) {
      closePreviewLightbox();
      toast(t('dialog.composite_error_msg', { msg: (r && r.error) || '' }), 'error');
      return;
    }
    lbSetImage(r.data_url);
  }

  function handleCompositeDone(r) {
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
    // 长矛彩蛋：合成完成才允许点击预览中的人物结束
    if (MCE.spear.active) MCE.spear.previewReady = true;
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.enterPreviewMode = enterPreviewMode;
  MCE.updatePreviewCount = updatePreviewCount;
  MCE.showSpritePreviewProgress = showSpritePreviewProgress;
  MCE.hideSpritePreviewProgress = hideSpritePreviewProgress;
  MCE.renderPreviewGrid = renderPreviewGrid;
  MCE.togglePreviewSel = togglePreviewSel;
  MCE.clearPreview = clearPreview;
  MCE.previewViewport = previewViewport;
  MCE.computeFit = computeFit;
  MCE.previewMinZoom = previewMinZoom;
  MCE.applyPreviewZoom = applyPreviewZoom;
  MCE.bindPreviewZoom = bindPreviewZoom;
  MCE.openLightbox = openLightbox;
  MCE.openPreviewLightbox = openPreviewLightbox;
  MCE.openPartLightbox = openPartLightbox;
  MCE.closePreviewLightbox = closePreviewLightbox;
  MCE.lbSetImage = lbSetImage;
  MCE.schedulePreview = schedulePreview;
  MCE.doComposite = doComposite;
  MCE.setPreviewThumb = _setPreviewThumb;
  MCE.handlePartPreviewReady = handlePartPreviewReady;
  MCE.handleCompositeDone = handleCompositeDone;
})();
