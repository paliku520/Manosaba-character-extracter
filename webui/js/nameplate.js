/* ============================================================
 * nameplate.js — 首页「名片合成」卡片
 *
 * 依赖：core.js（必须已加载）、ui.js（createDropdown / toast）。
 * 后端：run.py 的 JsApi.get_nameplate_info / prepare_nameplate /
 *       render_nameplate / save_nameplate / import_nameplate_font。
 * 后端事件：nameplate_assets / nameplate_rendered / nameplate_saved
 *          （由 events.js 转发到本模块的 npOn* 处理函数）。
 *
 * 排版规则（与游戏内一致，由后端按解析出的 UI 节点参数绘制）：
 *   姓氏首字 = 大字号   名字首字 = 中字号   其余字 = 小字号
 *
 * 交互约定：
 *   - **不自动合成**：只有点「生成预览」才请求渲染（改文字/字体/颜色都不会自动渲染）
 *   - 素材提取：主按钮「一键提取素材」自动查找（起点 = settings.json 的 last_directory，
 *     优先 StandaloneWindows64 再逐级向上），**查找中可点「停止查找」中止**；
 *     旁边的「手动选择…」可直接跳过自动查找；找不到时弹**模态窗口**给出
 *     `steamapps\common\manosaba_game\manosaba_Data\StreamingAssets\aa\StandaloneWindows64`
 *     的具体位置指引与目标文件名
 *   - 输出固定为底板尺寸 601×289（不提供背景图/字号缩放/位置偏移）
 *   - 字体固定用游戏内的两种明朝体（NAME_PLATE_FONTS）；首字颜色支持色板 + 自定义
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, api, App } = MCE;

  // 跨模块调用统一走转发别名（晚绑定，避免加载顺序问题）
  const toast = (...a) => MCE.toast(...a);
  const createDropdown = (...a) => MCE.createDropdown(...a);
  const showModal = (...a) => MCE.showModal(...a);
  const modalBtn = (...a) => MCE.btn(...a);
  const refreshExportCount = (...a) => MCE.refreshExportCount && MCE.refreshExportCount(...a);

  // 模块私有状态：语言切换会重建首页 DOM，靠它回填（输入/预览不丢）
  const S = {
    info: null, ready: false,
    surname: '', given: '',
    font: '', fontDrop: null,
    headColor: '',                 // '' = 跟随文字颜色（白）
    preview: '', fullSize: null,
    busy: false, busyAt: 0, picking: false,
    searching: false,              // 正在自动查找素材（按钮变「停止查找」）
  };

  // 字体固定为游戏内的两种明朝体（不提供导入）
  const NAME_PLATE_FONTS = ['TsukushiMincho', 'SourceHanSerifSC'];

  // 未找到素材时的位置指引兜底（与 src/nameplate.py 的 GAME_REL_HINT / BUNDLE_HINT_FILE 一致）
  const DEFAULT_HINT_REL = 'steamapps\\common\\manosaba_game\\manosaba_Data\\StreamingAssets\\aa\\StandaloneWindows64';
  const DEFAULT_HINT_FILE = 'general-sprites_assets_all.bundle';

  // 色板：与 webui/css/theme.css 的 html[data-accent="…"] 保持一致（游戏角色主题色）
  const NP_PALETTE = [
    { id: '', color: '#FFFFFF' },
    { id: 'alisa', color: '#EA4D3E' },
    { id: 'anan', color: '#9D97F9' },
    { id: 'coco', color: '#F77449' },
    { id: 'ema', color: '#FF8FB4' },
    { id: 'hanna', color: '#A7CB1E' },
    { id: 'hiro', color: '#F84F5A' },
    { id: 'leia', color: '#FDB95B' },
    { id: 'margo', color: '#B87BF0' },
    { id: 'meruru', color: '#E2BFB8' },
    { id: 'miria', color: '#EFD28D' },
    { id: 'nanoka', color: '#84909A' },
    { id: 'noah', color: '#65E4EB' },
    { id: 'sherry', color: '#89B5FA' },
    { id: 'jailer', color: '#C5C9D4' },
    { id: 'warden', color: '#B3B1C5' },
    { id: 'yuki', color: '#C3D4ED' },
  ];

  // 字体固定为游戏内的两种明朝体（日文筑紫明朝 / 中文思源宋体），不提供字体导入
  const PREFER_FONTS = ['TsukushiMincho', 'SourceHanSerifSC'];

  /** 只保留白名单内的两种字体 */
  function usableFonts(fonts) {
    return (fonts || []).filter((f) => PREFER_FONTS.indexOf(f.name) >= 0);
  }

  function defaultFont(fonts) {
    const list = usableFonts(fonts);
    for (const name of PREFER_FONTS) {
      const hit = list.find((f) => f.name === name);
      if (hit) return hit.path;
    }
    return list.length ? list[0].path : '';
  }

  /** 规范化 hex 颜色（#RGB / #RRGGBB，可省略 #）→ #RRGGBB 大写；无效返回 null */
  function normalizeHex(text) {
    const s = String(text || '').trim().replace(/^#/, '');
    if (/^[0-9a-fA-F]{3}$/.test(s)) {
      return ('#' + s.split('').map((c) => c + c).join('')).toUpperCase();
    }
    if (/^[0-9a-fA-F]{6}$/.test(s)) {
      return ('#' + s).toUpperCase();
    }
    return null;
  }

  function fileBaseName(p) {
    return String(p || '').split(/[\\/]/).pop() || '';
  }

  function colorLabel(id) {
    return id || t('np.color_default');
  }

  // ═════════════ 首字颜色（模态窗口）═════════════

  /** 打开首字颜色模态：角色主题色 + 坐标取色板 + hex 输入。
   *
   * 用项目的 showModal（**点击外部不会关闭**），因此可以放心点击 / 编辑 hex 输入框
   * （之前的下拉面板会被 document 上的外部点击逻辑关掉，「一点击就关闭」）。
   */
  function openColorModal() {
    const draft = S.headColor || '#FFFFFF';

    const body = document.createElement('div');
    body.className = 'np-color-modal';
    body.innerHTML =
      '<div class="np-color-top">' +
      '  <span class="np-color-preview" id="npm-preview"></span>' +
      '  <input type="text" class="np-input np-color-hex" id="npm-hex" maxlength="7"' +
      '         placeholder="#FFFFFF" spellcheck="false" autocomplete="off">' +
      '</div>' +
      '<div class="np-color-grid" id="npm-roles">' +
      NP_PALETTE.map((c) => colorItemHtml(c.color, colorLabel(c.id), c.id)).join('') +
      '</div>' +
      '<div class="np-color-plane np-color-plane-lg" id="npm-plane">' +
      '  <span class="np-color-cursor" id="npm-cursor"></span>' +
      '</div>';

    let current = draft;
    let closeFn = () => { /* 由 showModal 赋值 */ };

    const footer = document.createElement('div');
    footer.appendChild(modalBtn(t('dialog.cancel'), 'btn sm', () => closeFn()));
    footer.appendChild(modalBtn(t('dialog.ok'), 'btn sm primary', () => {
      S.headColor = current;
      syncColor();
      closeFn();
    }));

    const pv = body.querySelector('#npm-preview');
    const hx = body.querySelector('#npm-hex');
    const cursor = body.querySelector('#npm-cursor');
    const plane = body.querySelector('#npm-plane');
    const roles = body.querySelector('#npm-roles');
    plane.style.backgroundImage = planeBackgroundCss();

    const clamp01 = (v) => Math.min(1, Math.max(0, v));

    // 光标定位：拖动取色时直接用**指针原始坐标**（xy），只有颜色由外部改变（选角色色 / 输 hex /
    // 打开模态）才从颜色反推。否则纯黑/纯白（色相丢失）或色相 0≡360、拖出边界被 clamp 时，
    // 反推出的色相会坍缩成 0，光标会横跳到最左。
    const moveCursor = (xy) => {
      let x;
      let y;
      if (xy) {
        x = clamp01(xy.x);
        y = clamp01(xy.y);
      } else {
        const hsl = hexToHsl(current);
        x = clamp01(hsl.h / 360);
        y = hsl.l >= 50 ? (100 - hsl.l) / 100 : 1 - hsl.l / 100;
      }
      cursor.style.left = (x * 100).toFixed(2) + '%';
      cursor.style.top = (y * 100).toFixed(2) + '%';
    };

    const apply = (color, keepHex, xy) => {
      current = color;
      pv.style.background = color;
      if (!keepHex) hx.value = color;
      roles.querySelectorAll('.np-color-item').forEach((b) => {
        b.classList.toggle('selected', b.dataset.color.toUpperCase() === color.toUpperCase());
      });
      moveCursor(xy);
    };

    roles.addEventListener('click', (e) => {
      const item = e.target.closest('.np-color-item');
      if (item) apply(item.dataset.color);
    });

    // 取色板：按下并拖动连续取色（坐标超界时颜色贴到端色、光标停在边缘，不会跳回另一端）
    const pick = (e) => {
      const r = plane.getBoundingClientRect();
      const w = plane.clientWidth;
      const h = plane.clientHeight;
      if (!w || !h) return;
      // clientLeft/clientTop/clientWidth/Height 不含边框，与背景渐变的绘制区一致
      const x = (e.clientX - r.left - plane.clientLeft) / w;
      const y = (e.clientY - r.top - plane.clientTop) / h;
      apply(planeColorAt(x, y), false, { x, y });
    };
    plane.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      try { plane.setPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      pick(e);
    });
    plane.addEventListener('pointermove', (e) => {
      let captured = false;
      try { captured = plane.hasPointerCapture(e.pointerId); } catch (err) { /* ignore */ }
      if (captured) pick(e);
    });

    hx.addEventListener('input', () => {
      const v = normalizeHex(hx.value);
      if (v) apply(v, true);   // 输入中不回写输入框，避免光标跳动
    });

    const modal = showModal({
      title: t('np.head_color'),
      body,
      footer,
      className: 'np-color-modal-wrap',
    });
    closeFn = modal.close;
    apply(draft);
    setTimeout(() => hx.focus(), 30);
  }

  // ═════════════ 卡片结构 ═════════════

  // 坐标取色板：横向 = 色相（12 个停靠点，CSS 线性插值），纵向 = 明度（白 → 纯色 → 黑）
  const NP_SAT = 70;                                        // 取色板饱和度（%）
  const NP_HUE_STOPS = [0, 22, 45, 68, 100, 160, 190, 210, 232, 262, 290, 330];

  /** HSL → #RRGGBB */
  function hslToHex(h, s, l) {
    const S = s / 100;
    const L = l / 100;
    const k = (n) => (n + h / 30) % 12;
    const a = S * Math.min(L, 1 - L);
    const f = (n) => L - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)));
    return ('#' + [f(0), f(8), f(4)]
      .map((v) => Math.round(255 * v).toString(16).padStart(2, '0')).join('')).toUpperCase();
  }

  /** #RRGGBB → {h, s, l}（用于把当前颜色反推到取色板坐标） */
  function hexToHsl(hex) {
    const s = String(hex || '').replace('#', '');
    const r = parseInt(s.slice(0, 2), 16) / 255;
    const g = parseInt(s.slice(2, 4), 16) / 255;
    const b = parseInt(s.slice(4, 6), 16) / 255;
    const max = Math.max(r, g, b);
    const min = Math.min(r, g, b);
    const l = (max + min) / 2;
    const d = max - min;
    let h = 0;
    let sat = 0;
    if (d) {
      sat = d / (1 - Math.abs(2 * l - 1));
      if (max === r) h = ((g - b) / d) % 6;
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h *= 60;
      if (h < 0) h += 360;
    }
    return { h, s: sat * 100, l: l * 100 };
  }

  /** 取色板坐标（x/y ∈ 0..1）→ 颜色；与 CSS 背景渐变保持一致 */
  function planeColorAt(x, y) {
    const hue = Math.round(Math.min(1, Math.max(0, x)) * 360);
    const yy = Math.min(1, Math.max(0, y));
    const l = yy <= 0.5 ? 100 - yy * 100 : (1 - yy) * 100;   // 0→白 0.5→纯色 1→黑
    return hslToHex(hue, NP_SAT, l);
  }

  function colorItemHtml(color, label, id) {
    return '' +
      '<button type="button" class="np-color-item" data-color="' + color + '"' +
      (id !== undefined ? ' data-id="' + id + '"' : '') +
      ' data-tip="' + (label || color) + '">' +
      '<span class="np-swatch" style="background:' + color + '"></span>' +
      '</button>';
  }

  /** 取色板背景：横向色相渐变（停靠点位置 = hue/360，与 planeColorAt 一致）+ 纵向明度 */
  function planeBackgroundCss() {
    const stops = NP_HUE_STOPS.map((h) => 'hsl(' + h + ', ' + NP_SAT + '%, 50%) ' + (h / 360 * 100).toFixed(2) + '%');
    stops.push('hsl(360, ' + NP_SAT + '%, 50%) 100%');
    const hue = 'linear-gradient(to right, ' + stops.join(', ') + ')';
    const light = 'linear-gradient(to bottom, #FFFFFF 0%, rgba(255,255,255,0) 50%, #000000 100%)';
    return light + ', ' + hue;
  }

  function cardHtml() {
    return '' +
      '<div class="guide-card np-card" id="np-card">' +
      '  <h3>' + t('np.title') + '</h3>' +
      '  <p class="np-desc">' + t('np.desc') + '</p>' +

      // 素材未就绪：自动查找（可中止） + 手动选择；失败时弹模态给出查找位置指引
      '  <div class="np-setup" id="np-setup" hidden>' +
      '    <div class="np-setup-hint">' + t('np.need_assets') + '</div>' +
      '    <div class="np-setup-actions">' +
      '      <button type="button" class="btn sm primary" id="np-btn-prepare">' + t('np.prepare') + '</button>' +
      '      <button type="button" class="btn sm" id="np-btn-pick-bundle">' + t('np.pick_manually') + '</button>' +
      '    </div>' +
      '    <div class="np-setup-status" id="np-setup-status" hidden></div>' +
      '  </div>' +

      // 主体
      '  <div class="np-body" id="np-body" hidden>' +
      '    <div class="np-form">' +
      '      <div class="np-row">' +
      '        <label class="np-field"><span class="np-label">' + t('np.surname') + '</span>' +
      '          <input type="text" id="np-surname" class="np-input" maxlength="16" autocomplete="off" spellcheck="false">' +
      '        </label>' +
      '        <label class="np-field"><span class="np-label">' + t('np.given') + '</span>' +
      '          <input type="text" id="np-given" class="np-input" maxlength="16" autocomplete="off" spellcheck="false">' +
      '        </label>' +
      '      </div>' +
      '      <div class="np-row">' +
      '        <span class="np-label">' + t('np.font') + '</span>' +
      '        <span class="np-slot" id="np-font-slot"></span>' +
      '      </div>' +
      '      <div class="np-row">' +
      '        <span class="np-label">' + t('np.head_color') + '</span>' +
      '        <button type="button" class="np-color-btn" id="np-color-btn">' +
      '          <span class="np-swatch" id="np-color-swatch"></span>' +
      '          <span class="np-color-name" id="np-color-name"></span>' +
      '          <span class="cp-caret">' +
      '            <svg viewBox="0 0 16 16" width="12" height="12"><path d="M11.5 1.5l3 3L5.5 13.5 2 14l.5-3.5L11.5 1.5zM9.5 3.5l3 3" stroke="currentColor" stroke-width="1.4" fill="none" stroke-linejoin="round" stroke-linecap="round"/></svg>' +
      '          </span>' +
      '        </button>' +
      '      </div>' +
      '    </div>' +

      '    <div class="np-preview">' +
      '      <div class="np-stage">' +
      '        <div class="np-stage-empty" id="np-stage-empty">' + t('np.empty_preview') + '</div>' +
      '        <img id="np-img" alt="" hidden>' +
      '      </div>' +
      '      <div class="np-actions">' +
      '        <button type="button" class="btn sm primary" id="np-btn-generate">' + t('np.generate') + '</button>' +
      '        <button type="button" class="btn sm" id="np-btn-save">' + t('np.save') + '</button>' +
      '        <button type="button" class="btn sm ghost" id="np-btn-open-output">' + t('left.open_output') + '</button>' +
      '        <span class="np-size" id="np-size"></span>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      '</div>';
  }

  /** 把 S 的状态回填到当前 DOM（重建卡片或语言切换后调用） */
  function syncForm() {
    const set = (sel, val) => { const el = $(sel); if (el) el.value = val; };
    set('#np-surname', S.surname);
    set('#np-given', S.given);
    syncColor();
    const img = $('#np-img');
    if (img && S.preview) {
      img.src = S.preview;
      img.hidden = false;
      const em = $('#np-stage-empty'); if (em) em.hidden = true;
    }
    if (S.fullSize) setSizeText(t('np.size', { w: S.fullSize[0], h: S.fullSize[1] }));
  }

  /** 颜色按钮上的色块与名称同步 */
  function syncColor() {
    const cur = (S.headColor || '#FFFFFF').toUpperCase();
    const sw = $('#np-color-swatch'); if (sw) sw.style.background = cur;
    const nm = $('#np-color-name');
    if (nm) {
      const hit = NP_PALETTE.find((c) => c.color.toUpperCase() === cur);
      nm.textContent = hit ? colorLabel(hit.id) : cur;
    }
  }

  function setSizeText(text) {
    const el = $('#np-size');
    if (el) el.textContent = text || '';
  }

  // ═════════════ 后端交互 ═════════════

  async function loadInfo() {
    const a = api();
    if (!a || !a.get_nameplate_info) return;
    try {
      S.info = await a.get_nameplate_info();
    } catch (e) {
      S.info = null;
    }
    applyInfo();
  }

  function applyInfo() {
    const info = S.info || {};
    S.ready = !!info.ready;
    if (S.ready) S.searching = false;      // 素材已就绪 → 不可能还在查找
    syncPrepareButton();
    const setup = $('#np-setup');
    const body = $('#np-body');
    if (setup) setup.hidden = S.ready;
    if (body) body.hidden = !S.ready;
    if (!S.ready) return;

    const fonts = info.fonts || [];
    if (!S.font || !fonts.some((f) => f.path === S.font)) S.font = defaultFont(fonts);
    buildFontDropdown(fonts);
    // 不自动合成：仅显示提示，等用户点「生成预览」
    if (!S.preview) {
      const em = $('#np-stage-empty'); if (em) em.hidden = false;
      const img = $('#np-img'); if (img) img.hidden = true;
    }
  }

  function buildFontDropdown(fonts) {
    const slot = $('#np-font-slot');
    if (!slot) return;
    slot.innerHTML = '';
    S.fontDrop = null;
    const list = usableFonts(fonts);   // 只用白名单里的两种明朝体
    if (!list.length) {
      const span = document.createElement('span');
      span.className = 'np-empty';
      span.textContent = t('np.fonts_empty');
      slot.appendChild(span);
      return;
    }
    if (!S.font || !list.some((f) => f.path === S.font)) S.font = defaultFont(list);
    const dd = createDropdown({
      options: list.map((f) => ({ value: f.path, label: f.name })),
      value: S.font,
      placeholder: t('np.no_font'),
    });
    dd.onChange = (v) => { S.font = v; };   // 不自动渲染，等用户点「生成预览」
    slot.appendChild(dd.el);
    S.fontDrop = dd;
  }

  function params() {
    return {
      surname: S.surname,
      given: S.given,
      font: S.font,
      color: '#FFFFFF',
      head_color: S.headColor || '',
    };
  }

  /** 手动触发的渲染（不提供自动合成） */
  function generate() {
    const a = api();
    if (!a || !a.render_nameplate || !S.ready) return;
    // busy 期间不重复提交；超过 6s 视为事件丢失（后端异常等），允许重试避免永久卡住
    if (S.busy && (Date.now() - S.busyAt) < 6000) return;
    S.busy = true;
    S.busyAt = Date.now();
    setSizeText(t('np.rendering'));
    a.render_nameplate(params());
  }

  async function pickFile(opts) {
    const el = window.__electron;
    if (!el || !el.openFile) {
      toast(t('np.need_desktop'), 'warning');
      return null;
    }
    try {
      return await el.openFile(opts || {});
    } catch (e) {
      return null;
    }
  }

  /** 素材按钮文案随查找状态切换（查找中 = 「停止查找」） */
  function syncPrepareButton() {
    const btn = $('#np-btn-prepare');
    if (!btn) return;
    btn.textContent = S.searching ? t('np.cancel_search') : t('np.prepare');
    btn.classList.toggle('np-searching', S.searching);
  }

  /** 提取素材：bundlePath 为空 = 自动查找；非空 = 用户手动指定的文件 */
  async function prepare(bundlePath) {
    const a = api();
    if (!a || !a.prepare_nameplate) return;
    S.searching = true;
    syncPrepareButton();
    const start = (S.info && S.info.last_directory) || '';
    setSetupStatus(bundlePath
      ? t('np.importing_bundle', { name: fileBaseName(bundlePath) })
      : t('np.searching', { path: start || '—' }));
    try {
      await a.prepare_nameplate(bundlePath || '');   // 结果由 nameplate_assets 事件回报
    } catch (e) {
      S.searching = false;
      syncPrepareButton();
      setSetupStatus('');
    }
  }

  /** 「停止查找」：请求后端中止递归搜索（浅层探测很快不打断；等事件回报再复位按钮） */
  async function cancelSearch() {
    const a = api();
    setSetupStatus(t('np.search_cancelling'));
    if (a && a.cancel_nameplate_prepare) {
      try { await a.cancel_nameplate_prepare(); } catch (e) { /* ignore */ }
    }
  }

  /** 手动指引：弹原生文件对话框选 general-sprites*.bundle
   *  可直接跳过自动查找（正在查找时先中止）；手动选择再失败只提示、不再弹窗，避免无限循环 */
  async function manualPickBundle() {
    if (S.picking) return;
    S.picking = true;
    if (S.searching) await cancelSearch();
    setSetupStatus('');
    const path = await pickFile({
      title: t('np.pick_bundle_title'),
      filters: [{ name: 'Unity Bundle', extensions: ['bundle'] }],
    });
    S.picking = false;
    if (path) await prepare(path);
  }

  /** 自动查找失败：模态窗口详细说明「去哪找、选哪个文件」（含手动选择入口） */
  function showNotFoundModal(d) {
    const hint = (d && d.hint) || {};
    const rel = hint.rel || DEFAULT_HINT_REL;
    const file = hint.file || DEFAULT_HINT_FILE;
    const start = (d && d.start) || '';
    const searched = (d && d.searched) || [];

    const body = document.createElement('div');
    body.className = 'np-hint-modal';
    body.innerHTML =
      '<p class="np-hint-lead">' + t('np.hint_lead') + '</p>' +
      '<div class="np-hint-block">' +
      '  <div class="np-hint-label">' + t('np.hint_path_label') + '</div>' +
      '  <code class="np-hint-code" data-role="path"></code>' +
      '  <div class="np-hint-label">' + t('np.hint_file_label') + '</div>' +
      '  <code class="np-hint-code" data-role="file"></code>' +
      '</div>' +
      (start ? '<div class="np-hint-meta">' + t('np.hint_start', { path: start }) + '</div>' : '') +
      (searched.length
        ? '<details class="np-hint-searched"><summary>' + t('np.hint_searched', { count: searched.length }) +
          '</summary><ul></ul></details>'
        : '');
    // 路径文本用 textContent 赋值（含反斜杠，避免转义问题）
    body.querySelector('[data-role="path"]').textContent = rel;
    body.querySelector('[data-role="file"]').textContent = file;
    const ul = body.querySelector('.np-hint-searched ul');
    if (ul) {
      searched.forEach((s) => {
        const li = document.createElement('li');
        li.textContent = s;
        ul.appendChild(li);
      });
    }

    let modal = null;
    const footer = document.createElement('div');
    footer.appendChild(modalBtn(t('dialog.cancel'), 'btn sm', () => { if (modal) modal.close(); }));
    footer.appendChild(modalBtn(t('np.pick_manually'), 'btn sm primary', () => {
      if (modal) modal.close();
      manualPickBundle();
    }));
    modal = showModal({ title: t('np.not_found_title'), body, footer, className: 'np-hint-modal-wrap' });
  }

  function setSetupStatus(text) {
    const el = $('#np-setup-status');
    if (!el) return;
    el.textContent = text || '';
    el.hidden = !text;
  }

  // ═════════════ 事件绑定 ═════════════

  function bind() {
    const bindInput = (sel, key) => {
      const el = $(sel);
      if (!el) return;
      el.addEventListener('input', () => { S[key] = el.value; });   // 不自动渲染
    };
    bindInput('#np-surname', 'surname');
    bindInput('#np-given', 'given');

    // 首字颜色：点击打开颜色模态（角色主题色 + 坐标取色板 + hex 输入）
    const colorBtn = $('#np-color-btn');
    if (colorBtn) colorBtn.addEventListener('click', openColorModal);

    const btnOpenOut = $('#np-btn-open-output');
    if (btnOpenOut) btnOpenOut.addEventListener('click', () => {
      const a = api();
      if (a && a.open_output) a.open_output();
    });

    const btnGen = $('#np-btn-generate');
    if (btnGen) btnGen.addEventListener('click', () => generate());
    const btnSave = $('#np-btn-save');
    if (btnSave) btnSave.addEventListener('click', () => {
      const a = api();
      if (!a || !a.save_nameplate) return;
      if (!S.preview) { toast(t('np.nothing_to_save'), 'warning'); return; }
      a.save_nameplate(params());
    });

    const btnPrepare = $('#np-btn-prepare');
    if (btnPrepare) btnPrepare.addEventListener('click', () => {
      if (S.searching) cancelSearch(); else prepare('');
    });
    const btnPick = $('#np-btn-pick-bundle');
    if (btnPick) btnPick.addEventListener('click', manualPickBundle);
  }

  // ═════════════ 后端事件处理（events.js 转发）═════════════

  function onAssets(d) {
    S.searching = false;
    syncPrepareButton();

    if (!d || !d.ok) {
      if (d && d.cancelled) {
        // 用户主动中止查找：只提示，不弹窗（他知道自己在做什么）
        setSetupStatus(t('np.search_cancelled'));
        return;
      }
      if (d && d.error === 'bundle_not_found') {
        setSetupStatus(t('np.not_found', { path: (d && d.start) || '—' }));
        if (d.manual) {
          // 手动指定的文件也无效：只提示，不再弹选择框（否则会无限循环）
          toast(t('np.bundle_invalid'), 'error');
        } else {
          // 自动查找失败 → 模态窗口给出详细的查找位置指引（含手动选择入口）
          showNotFoundModal(d);
        }
        return;
      }
      const msg = (d && d.error) || '';
      setSetupStatus(t('np.prepare_failed', { msg: msg }));
      toast(t('np.prepare_failed', { msg: msg }), 'error');
      return;
    }
    setSetupStatus('');
    if (d.fonts_extracted && d.fonts_extracted.length) {
      toast(t('np.prepared_fonts', { count: d.fonts_extracted.length }), 'success');
    } else {
      toast(t('np.prepared'), 'success');
    }
    loadInfo();
  }

  function onRendered(d) {
    S.busy = false;
    if (!d || !d.ok) {
      setSizeText('');
      if (d && d.error === 'assets_missing') {
        S.ready = false;
        loadInfo();
      } else {
        toast(t('np.render_failed', { msg: (d && d.error) || '' }), 'error');
      }
      return;
    }
    S.preview = d.data_url || '';
    S.fullSize = d.full_size || null;
    const img = $('#np-img');
    if (img) { img.src = S.preview; img.hidden = false; }
    const em = $('#np-stage-empty'); if (em) em.hidden = true;
    if (S.fullSize) setSizeText(t('np.size', { w: S.fullSize[0], h: S.fullSize[1] }));
  }

  function onSaved(d) {
    if (!d || !d.ok) {
      toast(t('np.save_failed', { msg: (d && d.error) || '' }), 'error');
      return;
    }
    if (typeof d.export_count === 'number') {
      App.exportCount = d.export_count;
      refreshExportCount();
    }
    toast(t('np.saved') + '\n' + d.path, 'success');
  }

  // ═════════════ 挂载 ═════════════

  /** 首页渲染后调用（info.js 的 renderInfoPage 末尾）；重复调用只刷新文案，保留状态 */
  function renderNameplateCard() {
    const mount = $('#np-mount');
    if (!mount) return;
    mount.innerHTML = cardHtml();
    syncForm();
    bind();
    loadInfo();
  }

  MCE.renderNameplateCard = renderNameplateCard;
  MCE.npOnAssets = onAssets;
  MCE.npOnRendered = onRendered;
  MCE.npOnSaved = onSaved;
})();
