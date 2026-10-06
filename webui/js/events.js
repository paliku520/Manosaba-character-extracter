/* ============================================================
 * events.js — 后端事件监听（window.__pywebview.events）+ 调试资源监视
 *
 * 依赖：core.js（必须已加载）；其余模块由脚本顺序保证已解析
 *       （回调均在运行时触发，函数用转发别名晚绑定）。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * 说明：
 *   - on('part_preview_ready') / on('composite_done') 的处理体依赖 preview.js
 *     私有状态（_lb / previewZoom / previewFit），已下沉到该模块，这里转调。
 *   - _setPreviewThumb 属预览缩略图逻辑，已下沉到 preview.js。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, api, App } = MCE;

  // 后端事件注册表（preload 已创建，这里兜底，保证本模块可独立于 core 加载）
  window.__pywebview = window.__pywebview || {};
  window.__pywebview.events = window.__pywebview.events || {};
  const on = (event, fn) => { window.__pywebview.events[event] = fn; };

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const toast = (...a) => MCE.toast(...a);
  const setStatus = (...a) => MCE.setStatus(...a);
  const setErrorStatus = (...a) => MCE.setErrorStatus(...a);
  const showProgress = (...a) => MCE.showProgress(...a);
  const clearProgress = (...a) => MCE.clearProgress(...a);
  const switchTab = (...a) => MCE.switchTab(...a);
  const renderCharList = (...a) => MCE.renderCharList(...a);
  const charDisplayName = (...a) => MCE.charDisplayName(...a);
  const renderInfoPage = (...a) => MCE.renderInfoPage(...a);
  const showModeDialog = (...a) => MCE.showModeDialog(...a);
  const showNoComponentDialog = (...a) => MCE.showNoComponentDialog(...a);
  const offerOpen = (...a) => MCE.offerOpen(...a);
  const sortParts = (...a) => MCE.sortParts(...a);
  const renderParts = (...a) => MCE.renderParts(...a);
  const updateSelUI = (...a) => MCE.updateSelUI(...a);
  const clearPartsUI = (...a) => MCE.clearPartsUI(...a);
  const setPartsPlaceholder = (...a) => MCE.setPartsPlaceholder(...a);
  const renderHierarchy = (...a) => MCE.renderHierarchy(...a);
  const renderPreviewGrid = (...a) => MCE.renderPreviewGrid(...a);
  const showSpritePreviewProgress = (...a) => MCE.showSpritePreviewProgress(...a);
  const hideSpritePreviewProgress = (...a) => MCE.hideSpritePreviewProgress(...a);
  const setPreviewThumb = (...a) => MCE.setPreviewThumb(...a);
  const clearPreview = (...a) => MCE.clearPreview(...a);
  const handlePartPreviewReady = (...a) => MCE.handlePartPreviewReady(...a);
  const handleCompositeDone = (...a) => MCE.handleCompositeDone(...a);
  const refreshExportCount = (...a) => MCE.refreshExportCount(...a);
  const showUpdateDialog = (...a) => MCE.showUpdateDialog(...a);

  // ═════════════ 后端事件 ═════════════

  on('status', (s) => setStatus(s.text, true));
  on('progress', (p) => {
    // 缩略图生成阶段 → 组件选择页面内进度条；其余 → 侧边栏底部进度条
    if (p && p.phase === 'preview_thumbs') showSpritePreviewProgress(p);
    else showProgress(p);
  });

  // ═════════════ 调试资源监视（内存/CPU + FPS；GPU 无法实时监视，故不在此显示）══
  App._res = { mem: 0, cpu: 0, fps: 0, win: '' };

  function _updateResTitle() {
    const el = $('#tb-res');
    if (!el) return;
    if (!App.debugMode) { el.hidden = true; return; }
    const r = App._res;
    const parts = [];
    parts.push(t('log.resource_mem', { mem: r.mem }));
    parts.push(t('log.resource_cpu', { cpu: r.cpu }));
    if (r.fps > 0) parts.push(t('log.resource_fps', { fps: r.fps }));
    if (r.win) parts.push(r.win);
    el.textContent = parts.join(' | ');
    el.hidden = false;
  }

  // 调试模式：后端内存/CPU → 标题栏（窗口分辨率与 FPS 由前端自行采集）
  on('res_monitor', (p) => {
    App._res.mem = p.mem_mb;
    App._res.cpu = p.cpu;
    _updateResTitle();
  });

  // FPS + 窗口分辨率：前端 requestAnimationFrame 实时帧率（轻量，始终运行；非调试时隐藏显示）
  // 窗口尺寸直接读 window.outerWidth/outerHeight（CSS 像素，与主进程 DIP 口径一致），
  // 无需经后端获取窗口句柄。
  let _fpsAccum = 0, _fpsLast = performance.now();
  (function _fpsLoop() {
    _fpsAccum++;
    const now = performance.now();
    if (now - _fpsLast >= 1000) {
      App._res.fps = Math.round((_fpsAccum * 1000) / (now - _fpsLast));
      _fpsAccum = 0;
      _fpsLast = now;
      const w = window.outerWidth || window.innerWidth;
      const h = window.outerHeight || window.innerHeight;
      App._res.win = t('log.resource_win', { width: w, height: h });
      _updateResTitle();
    }
    requestAnimationFrame(_fpsLoop);
  })();

  // GPU 无法实时监视显存占用，故不加入资源监视；GPU 型号仅在启动系统信息中显示（见 _loadSysInfo）

  on('load_complete', (r) => {
    clearProgress();
    if (r.cancelled) {
      // 用户点击「取消加载」→ 提示已中止；被新的加载请求打断则只复位状态（新加载随即刷新状态栏）
      setStatus(t('app.status.cancelled'), false);
      if (r.cancelled_reason === 'user') toast(t('left.load_cancelled'), 'info');
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
    // 恢复状态栏：询问对话框（含点叉号关闭）期间不再显示"正在分析"
    setStatus(t('app.status.ready'), false);
    toast(t('app.status.analyze_done', { name: r.name }), 'success');
    if (r.has_components) showModeDialog(r.name);
    else showNoComponentDialog(r.name);
  });

  on('analyze_error', (r) => {
    clearProgress();
    setErrorStatus();
    setStatus(t('app.status.analyze_failed'));
    toast(t('dialog.analyze_error_msg', { name: r.name, msg: r.message }), 'error');
  });

  on('preview_ready', (d) => {
    clearProgress();
    console.log(t('log.preview_ready', { name: d.name, count: d.count }));
    App.previewData = d.sprites || [];
    App.previewThumbs = {};
    setStatus(t('app.status.extract_done', { name: d.name, count: d.count }));
    toast(t('app.status.extract_done', { name: d.name, count: d.count }), 'success');
    // 加载完成后再进入预览视图：隐藏组件选中板块，预览占满，再切到部件 tab
    $('#preview-panel').hidden = false;
    const pl = $('#parts-layout');
    if (pl) pl.hidden = true;
    $('#preview-name').textContent = charDisplayName(d.name);
    $('#preview-count').textContent = '';
    $('#sprite-preview-empty').hidden = true;
    switchTab('parts');
    // 流式加载：先渲染占位网格，缩略图随后逐张填充
    renderPreviewGrid();
    showSpritePreviewProgress({ current: 0, total: 1 });
    api().get_preview_thumbnails();
  });

  // 流式：每收到一张立即填充对应格子（形参勿用 t，避免遮蔽 i18n 的 t）
  on('preview_thumb', (d) => {
    if (d && d.name && d.data_url) setPreviewThumb(d.name, d.data_url);
  });

  on('preview_thumbs_ready', (map) => {
    clearProgress();
    hideSpritePreviewProgress();
    // 缩略图已流式填充完成；恢复状态栏、提示加载完毕（无需整网格重建，保留已加载图）
    const pn = $('#preview-name');
    setStatus(t('app.status.extract_done', { name: pn ? pn.textContent : '', count: App.previewData.length }), false);
    toast(t('log.preview_ready', { name: pn ? pn.textContent : '', count: App.previewData.length }), 'success');
  });

  on('export_complete', (r) => {
    clearProgress();
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
    App.characterData = d;
    App.selected.clear();
    App.thumbnails = {};
    App.previewMode = false;
    App.previewData = [];
    App.previewThumbs = {};
    App.previewSel.clear();
    $('#preview-panel').hidden = true;
    const pl = $('#parts-layout');
    if (pl) pl.hidden = false;
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
    setPartsPlaceholder('select');   // 加载失败：退回“请选择角色”提示（此时无可展示数据）
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

  // 部件放大预览（临时画布已生成）：交给 preview.js（需访问其私有查看器状态）
  on('part_preview_ready', (r) => handlePartPreviewReady(r));

  // 合成完成：交给 preview.js（需写入其私有缩放状态）
  on('composite_done', (r) => handleCompositeDone(r));

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
    // 打开输出目录：打开文件所在目录并在资源管理器中定位该文件（后端 open_path 对文件走 reveal）
    offerOpen(t('dialog.save_success_title'), t('dialog.save_success_msg', { path: r.path }), r.path || r.dir);
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
      showUpdateDialog(r);
      setStatus(t('app.status.ready'));
    } else if (!r.silent && r.status === 'latest') {
      setStatus(t('app.status.ready'));
      toast(t('dialog.update_latest_msg', { current: r.current }), 'success');
    } else if (!r.silent && r.status === 'error') {
      setStatus(t('app.status.ready'));
      toast(t('dialog.update_check_error_msg', { msg: r.message }), 'error');
    }
  });

  // 名片合成（首页卡片；处理体在 nameplate.js，与 part_preview_ready 同模式）
  on('nameplate_assets', (d) => MCE.npOnAssets(d));
  on('nameplate_rendered', (d) => MCE.npOnRendered(d));
  on('nameplate_saved', (d) => MCE.npOnSaved(d));
})();
