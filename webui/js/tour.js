/* ============================================================
 * tour.js — 首次使用引导（分步高亮浮层）
 *
 * 首次启动（settings.json 的 global.tutorial_done 为 false）时由 core.js 调
 * MCE.maybeAutoStartTour() 自动弹出；完成 / 跳过 / 关闭后经 API
 * set_tutorial_done(true) 持久化，之后不再自动弹出。
 * 可在「设置 → 数据」点「重新观看教程」调用 MCE.startTour() 随时重看。
 *
 * 依赖：core.js（MCE.$ / MCE.t / MCE.api / MCE.switchTab）；步骤文案见 i18n 的 tour.*。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const t = (...a) => MCE.t(...a);
  const api = (...a) => MCE.api(...a);
  const switchTab = (...a) => MCE.switchTab(...a);

  // ── 教程注册表 ───────────────────────────────────────────
  // 每个教程由若干步骤组成；步骤字段：
  //   key   文案键（i18n 的 tour.<教程id>.<key>_title / _body）
  //   target 高亮元素选择器，或候选选择器数组（取第一个可见者）；null = 居中卡片
  //   tab    进入该步骤前切换到的标签页
  //   place  气泡优先方位（缺省自动判断）
  //   interactive 是否允许在高亮区内直接操作（缺省：有高亮目标即开启）
  // 文案里的「可操作」提示见 i18n 的 tour.try_hint。
  const TOURS = {
    // 合成立绘（主流程）：加载目录 → 选示例角色 → 拼合/导出 → 无组件角色的精灵预览
    // 示例角色固定：有组件用 ema，无组件用 creatureema（见 i18n 文案中的 {ema} / {creatureema}）
    extract: [
      { key: 'x1', target: null, tab: 'info' },
      { key: 'x2', target: '#btn-load', place: 'right' },
      // 有组件支路：点示例角色 → 在「处理方式」对话框里点「拼接角色图像」
      { key: 'x3', target: '#char-list .char-item[data-name="ema"]', place: 'right' },
      { key: 'x4', target: ['.mode-card[data-mode="composite"]', '#parts-layout'], place: 'right', tab: 'parts' },
      { key: 'x5', target: '.parts-col', place: 'right', tab: 'parts' },
      { key: 'x5b', target: '#btn-select-clip', place: 'right', tab: 'parts' },
      { key: 'x6', target: '.pv-actions', place: 'top', tab: 'parts' },
      // 无组件支路：点示例角色 → 在对话框里点「预览精灵」→ 精灵预览面板
      { key: 'x7', target: '#char-list .char-item[data-name="creatureema"]', place: 'right' },
      { key: 'x8', target: ['.mode-card[data-mode="preview"]', '#preview-panel'], place: 'right', tab: 'parts' },
      { key: 'x9', target: '.sprite-preview-toolbar', place: 'bottom', tab: 'parts' },
      { key: 'x10', target: '#preview-grid', place: 'right', tab: 'parts' },
      { key: 'x11', target: '#btn-open-output', place: 'right', tab: 'info' },
      { key: 'x12', target: null, tab: 'info' },
    ],
    // 名片合成：介绍 + 动手试做
    nameplate: [
      { key: 'n1', target: null, tab: 'info' },
      { key: 'n2', target: ['#np-body', '#np-setup', '#np-card'], place: 'right', tab: 'info' },
      { key: 'n3', target: null, tab: 'info' },
    ],
    // 素材提取：背景 / 证物 / 资料 / 界面 / 演出素材的分类浏览与批量导出
    assets: [
      { key: 'a1', target: null, tab: 'backgrounds' },
      { key: 'a2', target: '#bg-load', place: 'bottom', tab: 'backgrounds' },
      { key: 'a3', target: '.background-filters', place: 'bottom', tab: 'backgrounds' },
      { key: 'a4', target: '#bg-list', place: 'right', tab: 'backgrounds' },
      { key: 'a5', target: '.background-actions', place: 'top', tab: 'backgrounds' },
      { key: 'a6', target: null, tab: 'backgrounds' },
    ],
  };

  const TOUR_ORDER = ['extract', 'nameplate', 'assets'];   // 教程菜单展示顺序
  const DEFAULT_TOUR = 'extract';                          // 首次启动自动播放的教程

  const SPOT_PAD = 8;   // 高亮框相对目标元素的外扩像素
  const GAP = 18;       // 气泡与高亮框的间距（含外发光，留出呼吸空间）
  const MARGIN = 12;    // 气泡与视口边缘的最小间距

  let root = null;      // #tour-root
  let spot = null;      // 高亮框
  let tip = null;       // 气泡
  let tipStep = null;
  let tipTitle = null;
  let tipBody = null;
  let tipTry = null;    // 「可直接操作」提示（仅 interactive 步骤显示）
  let btnPrev = null;
  let btnNext = null;
  let btnSkip = null;
  let blockers = null;      // 可操作步骤的点击拦截层（覆盖高亮区之外的区域）
  let blockEls = [];        // 上 / 下 / 左 / 右 四块
  let activeId = null;  // 当前播放的教程 id（文案键前缀 / aria 标签）
  let steps = [];       // 当前教程的步骤列表
  let index = 0;
  let timers = [];
  let autoFinishCb = null;   // 首启自动引导结束后的回调（用于补弹启动提示）
  let modalObserver = null;  // 监听模态框：弹出时引导暂时让位（避免遮挡对话框）

  const isActive = () => !!root;

  // ── DOM 构建 ─────────────────────────────────────────────
  function buildUi() {
    root = document.createElement('div');
    root.id = 'tour-root';
    root.className = 'tour-root';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');

    spot = document.createElement('div');
    spot.className = 'tour-spot';

    // 可操作步骤：高亮区（洞）之内允许点击穿透以直接操作，四周由这些透明层拦截，避免误触其它界面
    blockers = document.createElement('div');
    blockers.className = 'tour-blockers';
    blockers.hidden = true;
    blockEls = ['top', 'bottom', 'left', 'right'].map((side) => {
      const b = document.createElement('div');
      b.className = 'tour-block tour-block-' + side;
      blockers.appendChild(b);
      return b;
    });

    tip = document.createElement('div');
    tip.className = 'tour-tip';

    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'tour-tip-close';
    close.textContent = '✕';
    close.addEventListener('click', () => finish());

    const head = document.createElement('div');
    head.className = 'tour-tip-head';
    tipStep = document.createElement('span');
    tipStep.className = 'tour-tip-step';
    head.appendChild(tipStep);

    tipTitle = document.createElement('h4');
    tipTitle.className = 'tour-tip-title';

    tipBody = document.createElement('p');
    tipBody.className = 'tour-tip-body';

    tipTry = document.createElement('p');
    tipTry.className = 'tour-tip-try';
    tipTry.hidden = true;

    const foot = document.createElement('div');
    foot.className = 'tour-tip-foot';
    const hint = document.createElement('span');
    hint.className = 'tour-tip-hint';
    hint.textContent = t('tour.hint');
    const actions = document.createElement('div');
    actions.className = 'tour-tip-actions';
    btnSkip = makeBtn('btn sm ghost', () => finish());
    btnPrev = makeBtn('btn sm', () => go(index - 1));
    btnNext = makeBtn('btn sm primary', () => go(index + 1));
    actions.appendChild(btnSkip);
    actions.appendChild(btnPrev);
    actions.appendChild(btnNext);
    foot.appendChild(hint);
    foot.appendChild(actions);

    tip.appendChild(close);
    tip.appendChild(head);
    tip.appendChild(tipTitle);
    tip.appendChild(tipBody);
    tip.appendChild(tipTry);
    tip.appendChild(foot);

    root.appendChild(blockers);   // 拦截层在最下，气泡始终可点
    root.appendChild(spot);
    root.appendChild(tip);
    document.body.appendChild(root);
  }

  function makeBtn(cls, onClick) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = cls;
    b.addEventListener('click', onClick);
    return b;
  }

  // ── 步骤渲染 ─────────────────────────────────────────────
  // 文案中的示例角色名：取翻译表里的本地化角色名（char.*），缺失时回退到原始 id
  function nameParams() {
    const pick = (id) => {
      const v = t('char.' + id);
      return (v && v !== 'char.' + id) ? v : id;
    };
    return { ema: pick('ema'), creatureema: pick('creatureema') };
  }

  function applyTexts() {
    if (!root) return;
    const step = steps[index];
    const params = nameParams();
    const key = (suffix) => t('tour.' + activeId + '.' + step.key + '_' + suffix, params);
    tipStep.textContent = t('tour.step', { cur: index + 1, total: steps.length });
    tipTitle.textContent = key('title');
    tipBody.textContent = key('body');
    btnPrev.textContent = t('tour.prev');
    btnNext.textContent = t(index === steps.length - 1 ? 'tour.done' : 'tour.next');
    btnSkip.textContent = t('tour.skip');
    tip.querySelector('.tour-tip-hint').textContent = t('tour.hint');
    tipTry.textContent = t('tour.try_hint');   // 是否显示由 layout() 决定（它才知道目标是否解析得到）
    root.setAttribute('aria-label', t('tour.' + activeId + '_title'));
    btnPrev.disabled = index === 0;
    btnSkip.hidden = index === steps.length - 1;
  }

  // 步骤是否允许在高亮区内直接操作（缺省：只要高亮了元素就允许）
  const isInteractive = (step, hasTarget) => step.interactive !== false && !!hasTarget;

  function render() {
    const step = steps[index];
    if (step.tab) switchTab(step.tab);
    applyTexts();
    // 标签页切换/滑入动画期间元素位置会变化：先测一次，再补测几次收敛
    layout();
    // 换步后重新判定「对话框是否与当前步骤相关」：不相关则让位，相关则保持高亮
    syncSuspend();
    scheduleReposition();
  }

  function go(next) {
    if (!isActive()) return;
    if (next < 0) return;
    if (next >= steps.length) { finish(); return; }
    index = next;
    render();
  }

  function clearTimers() {
    timers.forEach((id) => clearTimeout(id));
    timers = [];
  }

  function scheduleReposition() {
    clearTimers();
    [60, 180, 360].forEach((ms) => timers.push(setTimeout(layout, ms)));
  }

  // ── 布局 ─────────────────────────────────────────────────
  // 解析步骤目标：target 可为选择器或候选选择器数组（取第一个可见者）；
  // 目标不在视口内时（如首页下方的名片卡片）先滚动到可见处再测量，保证高亮框可见。
  function targetRect(step) {
    const list = Array.isArray(step.target) ? step.target
      : (step.target ? [step.target] : []);
    for (const sel of list) {
      const el = document.querySelector(sel);
      if (!el) continue;
      let r = el.getBoundingClientRect();
      if (!(r.width > 0 && r.height > 0)) continue;
      if (r.top < 0 || r.bottom > window.innerHeight) {
        el.scrollIntoView({ block: 'center', inline: 'nearest' });
        r = el.getBoundingClientRect();
      }
      if (r.width > 0 && r.height > 0) return r;
    }
    return null;
  }

  function setBox(el, left, top, width, height) {
    el.style.left = left + 'px';
    el.style.top = top + 'px';
    el.style.width = Math.max(0, width) + 'px';
    el.style.height = Math.max(0, height) + 'px';
  }

  // 可操作步骤：高亮区之外铺四块透明拦截层，使「洞」内可直接操作、其余区域仍不可点
  function layoutBlockers(rect) {
    if (!rect) return;
    const L = rect.left - SPOT_PAD;
    const T = rect.top - SPOT_PAD;
    const R = rect.right + SPOT_PAD;
    const B = rect.bottom + SPOT_PAD;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    setBox(blockEls[0], 0, 0, vw, T);            // 上
    setBox(blockEls[1], 0, B, vw, vh - B);       // 下
    setBox(blockEls[2], 0, T, L, B - T);         // 左
    setBox(blockEls[3], R, T, vw - R, B - T);    // 右
  }

  // 依次尝试 bottom / top / right / left，选第一个放得下的方位
  function autoPlace(rect, w, h) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    if (rect.bottom + GAP + h <= vh - MARGIN) return 'bottom';
    if (rect.top - GAP - h >= MARGIN) return 'top';
    if (rect.right + GAP + w <= vw - MARGIN) return 'right';
    if (rect.left - GAP - w >= MARGIN) return 'left';
    return 'bottom';
  }

  // 某方位下气泡左上角坐标
  function placeAt(place, rect, w, h) {
    if (place === 'top') return { left: rect.left + rect.width / 2 - w / 2, top: rect.top - GAP - h };
    if (place === 'left') return { left: rect.left - GAP - w, top: rect.top + rect.height / 2 - h / 2 };
    if (place === 'right') return { left: rect.right + GAP, top: rect.top + rect.height / 2 - h / 2 };
    return { left: rect.left + rect.width / 2 - w / 2, top: rect.bottom + GAP };
  }

  // 把候选位置收敛到视口内（贴边时平移，不改变方位）
  function clampToView(p, w, h) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    return {
      left: Math.max(MARGIN, Math.min(p.left, vw - w - MARGIN)),
      top: Math.max(MARGIN, Math.min(p.top, vh - h - MARGIN)),
    };
  }

  // 按 order 依次挑方位：优先「收敛后不遮挡高亮目标」，其次退回首选方位。
  // 先收敛再判定，避免因目标贴近视口边缘（如顶部工具栏按钮）而误判某方位不可用。
  function pickPlacement(rect, order, w, h) {
    let first = null;
    for (const place of order) {
      const p = clampToView(placeAt(place, rect, w, h), w, h);
      if (!first) first = p;
      const overlaps = !(p.left + w <= rect.left || p.left >= rect.right ||
                         p.top + h <= rect.top || p.top >= rect.bottom);
      if (!overlaps) return p;
    }
    return first;
  }

  function layout() {
    if (!root) return;
    const step = steps[index];
    const rect = targetRect(step);

    if (rect) {
      root.classList.remove('is-centered');
      spot.hidden = false;
      spot.style.left = (rect.left - SPOT_PAD) + 'px';
      spot.style.top = (rect.top - SPOT_PAD) + 'px';
      spot.style.width = (rect.width + SPOT_PAD * 2) + 'px';
      spot.style.height = (rect.height + SPOT_PAD * 2) + 'px';
    } else {
      root.classList.add('is-centered');
      spot.hidden = true;
    }

    // 可操作步骤：开启「洞内可点」，并用拦截层挡住其余区域
    // （提示行也在此处切换：只有真正高亮到目标、"洞"存在时，才告诉用户可以直接操作）
    const interactive = isInteractive(step, !!rect);
    tipTry.hidden = !interactive;
    root.classList.toggle('is-interactive', interactive);
    if (interactive) { blockers.hidden = false; layoutBlockers(rect); }
    else blockers.hidden = true;

    const w = tip.offsetWidth;
    const h = tip.offsetHeight;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    let left;
    let top;

    if (!rect) {
      left = (vw - w) / 2;
      top = (vh - h) / 2;
    } else {
      const pref = step.place || autoPlace(rect, w, h);
      const order = [pref].concat(['bottom', 'top', 'right', 'left'].filter((p) => p !== pref));
      ({ left, top } = pickPlacement(rect, order, w, h));
    }

    // 贴边时收敛到视口内；目标过小/过大导致气泡超界时也保证完整可见
    left = Math.max(MARGIN, Math.min(left, vw - w - MARGIN));
    top = Math.max(MARGIN, Math.min(top, vh - h - MARGIN));
    tip.style.left = left + 'px';
    tip.style.top = top + 'px';
  }

  // ── 生命周期 ─────────────────────────────────────────────
  function onKey(e) {
    if (!isActive()) return;
    // 让位中（对话框在上层且与当前步骤无关）：键盘完全交给对话框
    if (root.classList.contains('tour-suspended')) return;
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();   // 当前步骤若正高亮对话框内容，Esc 只退出引导，不连带关掉对话框
      finish();
    }
    else if (e.key === 'ArrowRight') { e.preventDefault(); go(index + 1); }
    else if (e.key === 'ArrowLeft') { e.preventDefault(); go(index - 1); }
  }

  // ── 模态框让位 / 对话框内高亮 ────────────────────────────
  // 情况一：当前步骤指向对话框内的元素（如「处理方式」里的某个选项）→ 引导保持显示，
  //         此时高亮框挖在对话框上，指引用户点哪一个；Esc/方向键仍由引导接管。
  // 情况二：对话框弹出但与当前步骤无关（如名片素材查找窗口）→ 引导淡出且不拦截点击，关闭后自动恢复。
  function stepTargetsModal() {
    const step = steps[index];
    if (!step || !step.target) return false;
    const list = Array.isArray(step.target) ? step.target : [step.target];
    return list.some((sel) => {
      const el = document.querySelector(sel);
      return !!(el && el.closest && el.closest('#modal-root'));
    });
  }

  function syncSuspend() {
    if (!root) return;
    const modalRoot = document.querySelector('#modal-root');
    const hasModal = !!(modalRoot && modalRoot.children.length);
    root.classList.toggle('tour-suspended', hasModal && !stepTargetsModal());
  }

  function watchModals() {
    const modalRoot = document.querySelector('#modal-root');
    if (!modalRoot || modalObserver) return;
    // 对话框的开合会改变目标元素：先决定是否让位，再重新测量高亮位置
    modalObserver = new MutationObserver(() => { syncSuspend(); scheduleReposition(); });
    modalObserver.observe(modalRoot, { childList: true });
    syncSuspend();
  }

  function unwatchModals() {
    if (modalObserver) { modalObserver.disconnect(); modalObserver = null; }
  }

  function startTour(id) {
    if (isActive()) return;
    activeId = TOURS[id] ? id : DEFAULT_TOUR;
    steps = TOURS[activeId];
    index = 0;
    buildUi();
    root.classList.add('show');
    document.addEventListener('keydown', onKey, true);
    window.addEventListener('resize', layout);
    window.addEventListener('scroll', layout, true);
    watchModals();
    render();
    // 首帧后淡入，避免气泡从 (0,0) 位置滑入
    layout();
  }

  // 教程菜单：列出全部教程，点击即播放（入口：首页「查看使用教程」、设置 →「重新观看教程」）
  function openTourPicker() {
    if (isActive() || !MCE.showModal) return;
    if (document.querySelector('.tour-menu')) return;   // 防重复：连续点击不叠加多层菜单
    const body = document.createElement('div');
    body.className = 'tour-menu';

    const lead = document.createElement('p');
    lead.className = 'tour-menu-lead';
    lead.textContent = t('tour.menu_desc');
    body.appendChild(lead);

    const closeRef = { fn: null };
    TOUR_ORDER.forEach((id) => {
      const item = document.createElement('button');
      item.type = 'button';
      item.className = 'tour-menu-item';
      const title = document.createElement('span');
      title.className = 'tour-menu-title';
      title.textContent = t('tour.' + id + '_title');
      const desc = document.createElement('span');
      desc.className = 'tour-menu-desc';
      desc.textContent = t('tour.' + id + '_desc');
      const play = document.createElement('span');
      play.className = 'tour-menu-play';
      play.setAttribute('aria-hidden', 'true');
      play.textContent = '▶';
      item.appendChild(title);
      item.appendChild(desc);
      item.appendChild(play);
      item.addEventListener('click', () => {
        if (closeRef.fn) closeRef.fn();   // 先关菜单再播放，避免引导层与菜单叠加
        startTour(id);
      });
      body.appendChild(item);
    });

    const footer = document.createElement('div');
    const closeBtn = MCE.btn(t('tour.menu_close'), 'btn sm', null);
    footer.appendChild(closeBtn);
    const { close } = MCE.showModal({ titleKey: 'tour.menu_title', body, footer, className: 'tour-menu-modal' });
    closeRef.fn = close;
    closeBtn.addEventListener('click', close);
  }

  function finish() {
    if (!isActive()) return;
    clearTimers();
    document.removeEventListener('keydown', onKey, true);
    window.removeEventListener('resize', layout);
    window.removeEventListener('scroll', layout, true);
    unwatchModals();
    root.remove();
    root = null;
    markDone();
    // 首启流程：引导结束后再补弹启动提示（剧透警告 / 测试版提示，见 core.js）
    const cb = autoFinishCb;
    autoFinishCb = null;
    if (cb) { try { cb(); } catch (e) { /* 提示弹出失败不应影响主流程 */ } }
  }

  // 引导结束（完成 / 跳过 / 关闭）后持久化，确保不再自动弹出
  function markDone() {
    try {
      if (MCE.App && MCE.App.info) MCE.App.info.tutorial_done = true;
      const a = api();
      if (a && typeof a.set_tutorial_done === 'function') a.set_tutorial_done(true);
    } catch (e) { /* 无后端（浏览器直开）时静默忽略 */ }
  }

  // 语言切换后若引导仍在显示，刷新文案
  function refreshTourTexts() {
    if (isActive()) { applyTexts(); scheduleReposition(); }
  }

  // 首次启动自动引导：等启动页淡出（并确保没有别的模态框在显示）后开始。
  // onFinish：引导结束（完成 / 跳过 / 关闭）后回调；不适用或引导最终未能开始时立即回调，
  // 便于调用方（core.js）统一把启动提示（剧透警告等）安排在引导之后。
  function maybeAutoStartTour(onFinish) {
    const info = MCE.App && MCE.App.info;
    const takeCb = () => { const cb = autoFinishCb; autoFinishCb = null; return cb; };
    const fireCb = () => { const cb = takeCb(); if (cb) { try { cb(); } catch (e) { /* ignore */ } } };
    if (!info || info.tutorial_done) { autoFinishCb = onFinish || null; fireCb(); return; }
    autoFinishCb = onFinish || null;
    let waited = 0;
    const attempt = () => {
      // 期间已在别处标记完成 / 久等模态框未果：放弃引导，但仍补上启动提示
      if (MCE.App.info.tutorial_done || waited >= 60000) { fireCb(); return; }
      const modalRoot = document.querySelector('#modal-root');
      if (modalRoot && modalRoot.children.length) {
        waited += 400;
        timers.push(setTimeout(attempt, 400));
        return;
      }
      timers.push(setTimeout(() => startTour(DEFAULT_TOUR), 1300));   // 等待启动页淡出后再开始引导
    };
    attempt();
  }

  MCE.startTour = startTour;
  MCE.openTourPicker = openTourPicker;
  MCE.finishTour = finish;
  MCE.maybeAutoStartTour = maybeAutoStartTour;
  MCE.refreshTourTexts = refreshTourTexts;
})();
