/* ============================================================
 * parts.js — 部件选择（渲染 / 排序 / 搜索 / 勾选 / 已选列表）
 *            + 长矛 / Nanoka / meme 彩蛋 + Anan 素描本自定义文字
 *
 * 长矛彩蛋锁定状态（_spearEasterActive / _spearPreviewReady）的 backing 在本模块，
 * 供其他模块经 MCE.spear（getter/setter 门面）读写。
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, $$, t, api, fmt, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const toast = (...a) => MCE.toast(...a);
  const btn = (...a) => MCE.btn(...a);
  const showModal = (...a) => MCE.showModal(...a);
  const confirmDialog = (...a) => MCE.confirmDialog(...a);
  const createDropdown = (...a) => MCE.createDropdown(...a);
  const setTipText = (...a) => MCE.setTipText(...a);
  const copyText = (...a) => MCE.copyText(...a);
  const switchTab = (...a) => MCE.switchTab(...a);
  const charDisplayName = (...a) => MCE.charDisplayName(...a);
  const openPartLightbox = (...a) => MCE.openPartLightbox(...a);
  const clearPreview = (...a) => MCE.clearPreview(...a);
  const schedulePreview = (...a) => MCE.schedulePreview(...a);
  const doComposite = (...a) => MCE.doComposite(...a);

  // 部件区下方占位提示：select=请选择角色 / loading=正在读取角色数据 / none=隐藏
  function setPartsPlaceholder(state) {
    const box = $('#parts-empty');
    if (box) box.hidden = state === 'none';
    const sel = $('#parts-empty-hint');
    if (sel) sel.hidden = state !== 'select';
    const load = $('#parts-loading-hint');
    if (load) load.hidden = state !== 'loading';
  }

  // 预设栏仅在「已加载含组件数据的角色」后展示
  function showPresetBar(show) {
    const bar = document.querySelector('.parts-preset-bar');
    if (bar) bar.hidden = !show;
  }

  function clearPartsUI(placeholder) {
    spearTeardown();        // 切换角色/清缓存时解除长矛彩蛋状态（防御性）
    teardownPartsEaster();  // 切换角色时移除 nanoka 部件卡彩蛋
    resetPresetBar();       // 重置预设下拉（新角色数据到达后由 renderParts 重新填充）
    showPresetBar(false);   // 角色数据就绪前不展示预设栏
    setPartsPlaceholder(placeholder === 'loading' ? 'loading' : 'select');
    $('#parts-list').innerHTML = '';
    $('#parts-name').textContent = '—';
    $('#parts-count').textContent = '';
    $('#sel-count').textContent = '0';
    $('#selected-list').innerHTML = '';
    $('#hierarchy-tree').innerHTML = '';
    $('#hierarchy-empty').hidden = false;
    // 恢复常规部件布局（退出预览模式）
    $('#preview-panel').hidden = true;
    const pl = $('#parts-layout');
    if (pl) pl.hidden = false;
    $('#preview-grid').innerHTML = '';
  }

  // ═════════════ 部件选择 ═════════════

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
    $('#parts-name').textContent = charDisplayName(data.name);
    $('#parts-count').textContent = data.count + ' ' + t('parts.total');
    setPartsPlaceholder('none');   // 数据已就绪：隐藏下方占位提示
    showPresetBar(true);           // 拼接模式（含组件数据）才展示预设栏
    renderPresetOptions('');   // 填充预设下拉（后端随角色数据下发 presets）

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
      setTipText(h, cat);
      const caret = document.createElement('span');
      caret.className = 'part-caret';
      caret.innerHTML =
        '<svg viewBox="0 0 16 16" width="12" height="12"><path d="M4 6l4 4 4-4" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg>';
      const nameSpan = document.createElement('span');
      nameSpan.textContent = cat;
      const cnt = document.createElement('span');
      cnt.className = 'g-count';
      cnt.textContent = parts.length;
      const desel = document.createElement('button');
      desel.type = 'button';
      desel.className = 'part-deselect';
      desel.textContent = t('parts.deselect_group');
      setTipText(desel, cat);
      desel.addEventListener('click', (e) => {
        e.stopPropagation();   // 不触发展开/折叠
        deselectGroup(g);
      });
      h.appendChild(caret); h.appendChild(nameSpan); h.appendChild(desel); h.appendChild(cnt);
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
          '  <span class="part-sub">' +
          '    <span class="part-meta"></span>' +
          '    <span class="part-alpha"></span>' +
          '  </span>' +
          '</span>';

        item.querySelector('.part-name').textContent = p.name;
        item.querySelector('.part-meta').textContent =
          'x:' + fmt(pos.x) + '  y:' + fmt(pos.y) + '  order:' + p.sorting_order +
          '  ' + sz[0] + '×' + sz[1];
        item.querySelector('.part-alpha').textContent = 'α ' + Number(alpha).toFixed(2);

        const cb = item.querySelector('input[type=checkbox]');
        // 重建列表时恢复勾选状态（语言切换等会重建，App.selected 仍保留选中项）
        cb.checked = App.selected.has(p.name);
        // 仅点击复选框切换勾选；点击卡片其他区域不触发选择/合成
        cb.addEventListener('change', () => onPartToggle(p.name, cb.checked));

        // 右键部件行 → 放大预览（后端用合成逻辑把该部件画到临时画布的真实位置上）
        item.addEventListener('contextmenu', (e) => {
          if (MCE.spear.active) return;
          e.preventDefault();
          e.stopPropagation();
          openPartLightbox(p.name);
        });

        App.partEls[p.name] = { cb, thumb: item.querySelector('.part-thumb') };
        g.appendChild(item);
      });
      list.appendChild(g);
    });

    // 重建列表后恢复已缓存的缩略图（语言切换等重建时 App.thumbnails 仍保留）
    Object.keys(App.thumbnails).forEach((name) => {
      const el = App.partEls[name];
      if (!el) return;
      const img = document.createElement('img');
      img.src = App.thumbnails[name];
      el.thumb.innerHTML = '';
      el.thumb.appendChild(img);
    });
    setupPartsEaster();  // 简体中文 + nanoka 时，部件标题卡变为可点击彩蛋入口
  }

  // ── Nanoka 彩蛋（仅简体中文 + 当前角色 nanoka：部件标题卡可点击 → "超级拼装"）──
  let _partsEaster = null;        // { title, enter, leave } 已激活的部件卡彩蛋状态
  let _memeEasterActive = false;  // meme 全屏覆盖层是否显示中（防重复触发）
  let _spearEasterActive = false; // noah 长矛彩蛋进行中（界面锁定）
  let _spearPreviewReady = false; // 长矛彩蛋：合成完成前不可点击预览人物结束
  // noah 长矛彩蛋强制选择的组件（右键 leia 触发；仅取实际存在的部件）
  const SPEAR_PARTS = [
    'ArmL02', 'ArmR01', 'Body', 'Cheeks_Normal',
    'ClippingMask_Effect_Root_01', 'ClippingMask_Effect_Root_02',
    'ClippingMask_Effect_Root_03', 'ClippingMask_Effect_Root_04',
    'ClippingMask_Eyes', 'ClippingMask_Facial_01', 'ClippingMask_Facial_02',
    'Eyes_Fearful_Open', 'Mouth_Normal_Closed', 'Pale01',
  ];

  // 简体中文且当前角色为 nanoka 时，让部件标题卡（角色名 + 部件数）可点击；
  // 悬停时内部文本临时替换为"超级拼装"，离开后恢复原样
  function setupPartsEaster() {
    const active = !!App.info && App.info.current_lang === 'zh_CN' && App.currentName === 'nanoka';
    if (!active) { teardownPartsEaster(); return; }
    if (_partsEaster) return;  // 已激活
    const countEl = $('#parts-count');
    if (!countEl) return;
    const enter = () => {
      if (!_partsEaster) return;
      _partsEaster.origCount = countEl.textContent;
      countEl.textContent = '超级拼装';
    };
    const leave = () => {
      if (!_partsEaster) return;
      if (_partsEaster.origCount !== undefined) countEl.textContent = _partsEaster.origCount;
    };
    _partsEaster = { countEl, enter, leave, origCount: undefined };
    countEl.classList.add('parts-easter');   // 仅带颜色的数量卡成为彩蛋入口
    countEl.addEventListener('mouseenter', enter);
    countEl.addEventListener('mouseleave', leave);
    countEl.addEventListener('click', showMemeEaster);
  }

  // 移除部件卡彩蛋（切换角色 / 语言非简体中文时恢复普通状态）
  function teardownPartsEaster() {
    if (!_partsEaster) return;
    const st = _partsEaster;
    _partsEaster = null;
    st.countEl.classList.remove('parts-easter');
    st.countEl.removeEventListener('mouseenter', st.enter);
    st.countEl.removeEventListener('mouseleave', st.leave);
    st.countEl.removeEventListener('click', showMemeEaster);
    if (st.origCount !== undefined) st.countEl.textContent = st.origCount;
  }

  // 彩蛋：点击部件标题卡 → 播放 meme 音频并淡入 meme 图片；
  // 音频结束后 1 秒淡出移除；期间用户无法强制退出（无关闭按钮 / 屏蔽 Esc / 拦截点击）
  function showMemeEaster() {
    if (_memeEasterActive) return;
    _memeEasterActive = true;
    const old = $('#meme-easter-overlay');
    if (old) old.remove();

    const overlay = document.createElement('div');
    overlay.className = 'meme-easter-overlay';
    overlay.id = 'meme-easter-overlay';
    overlay.innerHTML =
      '<div class="meme-easter-img-wrap">' +
      '  <img class="meme-easter-img" src="assets/EasterEgg/assembly_meme_cn/meme.jpg" alt="">' +
      '</div>';
    document.body.appendChild(overlay);

    const img = overlay.querySelector('.meme-easter-img');

    // 用户不能强制退出：屏蔽 Esc / 点击 / 滚轮 / 右键，全部拦截
    const blockKeys = (e) => {
      if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); }
    };
    document.addEventListener('keydown', blockKeys, true);
    overlay.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); });
    overlay.addEventListener('wheel', (e) => e.preventDefault(), { passive: false });
    overlay.addEventListener('contextmenu', (e) => e.preventDefault());

    // 播放音频；结束后 1 秒淡出并移除（播放出错也按同样流程收尾）
    let closed = false;
    const finish = () => {
      if (closed) return;
      closed = true;
      setTimeout(() => {
        overlay.classList.add('closing');
        setTimeout(() => {
          if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
          _memeEasterActive = false;
          document.removeEventListener('keydown', blockKeys, true);
        }, 500);
      }, 1000);
    };
    const audio = new Audio('assets/EasterEgg/assembly_meme_cn/meme_1.wav');
    audio.volume = 1;

    // 图片淡入时长与音频长度一致：元数据就绪后按 duration 设置过渡时长，再同时开始淡入 + 播放
    const beginShow = () => {
      const d = audio.duration;
      if (d > 0) img.style.transitionDuration = d + 's';
      requestAnimationFrame(() => requestAnimationFrame(() => img.classList.add('show')));
      audio.play().catch(finish);
    };
    if (audio.readyState >= 1) beginShow();
    else audio.addEventListener('loadedmetadata', beginShow, { once: true });

    audio.addEventListener('ended', finish);
    audio.addEventListener('error', finish);
  }

  // ── Noah 长矛彩蛋 ──────────────────────────────────────────
  // 位于 noah 组件选择界面时，右键侧边栏的 leia → 光标变为长矛、锁定界面并强制选择指定组件；
  // 点击预览中的人物结束（播放 balloon_pop.ogg + 清空预览 + 取消全选），随后解除锁定。

  // 彩蛋可用条件：noah 组件选择界面（角色已加载、非无组件预览模式）、且未处于彩蛋中
  function spearEasterAvailable() {
    return !!App.characterData && App.currentName === 'noah' && !App.previewMode && !_spearEasterActive;
  }

  // 开始彩蛋：锁定界面 + 强制选择组件 + 生成人物预览
  function startSpearEaster() {
    if (!spearEasterAvailable()) return;
    _spearEasterActive = true;
    _spearPreviewReady = false;   // 合成完成前不可点击预览人物
    // 光标变为长矛（body.spear-lock 全局强制，覆盖各元素自带 cursor；热点在矛尖 1,2，64px 光标图）
    document.body.classList.add('spear-lock');
    // 锁定在 noah 组件选择界面
    switchTab('parts');
    // 强制选择指定组件（仅选择实际存在的部件）
    App.selected.clear();
    App.characterData.transform_data.forEach((p) => {
      if (SPEAR_PARTS.indexOf(p.name) !== -1) App.selected.add(p.name);
    });
    Object.keys(App.partEls).forEach((name) => {
      const el = App.partEls[name];
      if (el) el.cb.checked = App.selected.has(name);
    });
    updateSelUI();
    // 立即生成人物预览（供用户点击结束彩蛋）
    if (api() && App.selected.size > 0) {
      api().composite(Array.from(App.selected), sketchTextArg(), sketchSizeArg(), sketchAlignArg());
    }
  }

  // 结束彩蛋：播放音频 + 清空预览 + 取消全选 + 解除锁定
  function finishSpearEaster() {
    if (!_spearEasterActive) return;
    const audio = new Audio('assets/EasterEgg/simple_spear/balloon_pop.ogg');
    audio.volume = 1;
    audio.play().catch(() => {});
    clearPreview();
    App.selected.clear();
    Object.keys(App.partEls).forEach((name) => {
      const el = App.partEls[name];
      if (el) el.cb.checked = false;
    });
    updateSelUI();
    _spearEasterActive = false;
    _spearPreviewReady = false;
    document.body.classList.remove('spear-lock');
  }

  // 防御性解除（切换角色 / 清缓存等场景）
  function spearTeardown() {
    _spearEasterActive = false;
    _spearPreviewReady = false;
    document.body.classList.remove('spear-lock');
  }

  function onPartToggle(name, checked) {
    if (MCE.spear.active) {
      // 长矛彩蛋锁定期间禁止改选部件：还原复选框视觉状态（原生切换已发生）
      const el = App.partEls[name];
      if (el) el.cb.checked = !checked;
      return;
    }
    if (checked) App.selected.add(name);
    else App.selected.delete(name);
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    if (App.autoUpdate) schedulePreview();
  }

  // ── Anan 素描本自定义文字（特殊合成逻辑）──
  // 仅 Anan 角色，且选中 Arms01/Arms02 其中之一（拿素描本的手臂变体）时启用；
  // 普通手臂 ArmL/ArmR 不触发。文字经后端渲染到素描本的 Option_Arms0x 位置。
  function isAnanSketchMode() {
    if (!App.characterData) return false;
    const isAnan = App.currentName === 'anan' || (App.characterData.name || '') === 'anan';
    if (!isAnan) return false;
    const arms = ['Arms01', 'Arms02'].filter((n) => App.selected.has(n));
    return arms.length === 1;
  }

  // 字号滑块值同步到右侧数字
  function syncSketchSizeLabel() {
    const slider = $('#sketch-size');
    const v = $('#sketch-size-value');
    if (slider && v) v.textContent = slider.value;
  }

  // 对齐分段：高亮 + 滑动指示条位置同步到已应用的对齐方式
  function syncSketchAlign() {
    const seg = $('#sketch-align');
    if (!seg) return;
    const val = App.sketchAlign || 'center';
    const ind = seg.querySelector('.seg-ind');
    let idx = 0;
    seg.querySelectorAll('button[data-align]').forEach((b, i) => {
      b.classList.toggle('active', b.dataset.align === val);
      if (b.dataset.align === val) idx = i;
    });
    if (ind) ind.style.transform = 'translateX(' + (idx * 100) + '%)';
  }

  // “编辑文字”按钮：有文字时鼠标悬停用统一气泡显示已输入内容（不再内嵌摘要小气泡，避免样式不统一）
  function syncSketchSummary() {
    const text = (App.sketchText || '').trim();
    const btn = $('#btn-sketch-edit');
    if (!btn) return;
    btn.classList.toggle('has-text', !!text);
    setTipText(btn, text || '');
  }

  // 打开素描本文字编辑模态窗口（最大 5 行；确定后提交并刷新预览）
  function openSketchModal() {
    const ta = document.createElement('textarea');
    ta.className = 'sketch-modal-textarea';
    ta.rows = 5;
    ta.maxLength = 500;
    ta.value = App.sketchText || '';
    // 最大行数限制：超过 5 行时截断到前 5 行
    ta.addEventListener('input', () => {
      const lines = ta.value.split('\n');
      if (lines.length > 5) {
        ta.value = lines.slice(0, 5).join('\n');
        ta.setSelectionRange(ta.value.length, ta.value.length);
      }
    });
    const footer = document.createElement('div');
    const no = btn(t('dialog.cancel'), 'btn sm', () => close());
    const yes = btn(t('dialog.ok'), 'btn sm primary', () => {
      App.sketchText = ta.value;
      close();
      syncSketchSummary();
      if (isAnanSketchMode() && App.selected.size > 0) schedulePreview();
    });
    footer.appendChild(no); footer.appendChild(yes);
    const { close } = showModal({ titleKey: 'parts.sketch_label', body: ta, footer });
    setTimeout(() => ta.focus(), 60);
  }

  // 切换角色/选择变化时同步素描本输入区显隐；首次进入时从已应用状态回填
  let sketchInputWasHidden = true;
  function updateSketchInput() {
    const wrap = $('#sketch-input-wrap');
    if (!wrap) return;
    const active = isAnanSketchMode();
    if (active && sketchInputWasHidden) {
      const slider = $('#sketch-size');
      if (slider) slider.value = App.sketchSize || 56;
      syncSketchSizeLabel();
      syncSketchAlign();
      syncSketchSummary();
    }
    sketchInputWasHidden = !active;
    wrap.hidden = !active;
    const editBtn = $('#btn-sketch-edit');
    const slider = $('#sketch-size');
    const seg = $('#sketch-align');
    if (editBtn) editBtn.disabled = !active;
    if (slider) slider.disabled = !active;
    if (seg) seg.querySelectorAll('button[data-align]').forEach((b) => { b.disabled = !active; });
  }

  // 合成时传递的文字/字号/对齐参数：仅素描模式有效，否则空串/默认（后端忽略）
  function sketchTextArg() {
    return isAnanSketchMode() ? (App.sketchText || '').trim() : '';
  }
  function sketchSizeArg() {
    return isAnanSketchMode() ? (App.sketchSize || 56) : 56;
  }
  function sketchAlignArg() {
    return isAnanSketchMode() ? (App.sketchAlign || 'center') : 'center';
  }

  function updateSelUI() {
    $('#sel-count').textContent = App.selected.size;
    updatePresetButtons();
    updateSketchInput();
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
        setTipText(li, t('app.click_to_copy'));
        li.addEventListener('click', () => copyText(p.name));
        ul.appendChild(li);
      }
    });
  }

  function selectAll(checked) {
    if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止全选/取消全选
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

  // 取消指定分组内所有部件的选择（分组头部的“取消选择”按钮）
  function deselectGroup(groupEl) {
    if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止取消分组选择
    if (!App.characterData) return;
    let removed = 0;
    groupEl.querySelectorAll('.part-item').forEach((item) => {
      const cb = item.querySelector('input[type=checkbox]');
      const name = item.querySelector('.part-name').textContent;
      if (App.selected.delete(name)) removed++;
      if (cb) cb.checked = false;
    });
    if (removed > 0) {
      console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
      updateSelUI();
      if (App.autoUpdate) schedulePreview();
    }
  }

  // 排除项：HairClippingMask* 需用户自行勾选（不纳入快速勾选）
  function isExcludedClipMask(name) {
    return typeof name === 'string' && name.indexOf('HairClippingMask') === 0;
  }

  // 快速勾选 ClippingMask 部件：用后端 mask_mapping 权威的 masked 列表（clipping_mask_parts），
  // 不清除现有选择（仅追加）；HairClippingMask* 排除在外，由用户自行勾选。
  function selectClipMaskParts() {
    if (MCE.spear.active) return;   // 长矛彩蛋锁定期间禁止勾选
    if (!App.characterData) return;
    const list = App.characterData.clipping_mask_parts || [];
    let added = 0;   // 仅统计本次新增（App.selected.add 幂等，重复点击不再重复提示）
    list.forEach((name) => {
      if (isExcludedClipMask(name)) return;   // HairClippingMask 留给用户手动勾选
      if (!App.selected.has(name)) added++;
      App.selected.add(name);
      const el = App.partEls[name];
      if (el) el.cb.checked = true;
    });
    if (added === 0) return;   // 无新增：状态已一致，不刷新预览/不提示
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    if (App.autoUpdate) schedulePreview();
    toast(t('parts.clip_selected', { count: added }), 'success');
  }

  // ── 用户预设（记录部件的 sorting_order，随时一键恢复）──────
  // 预设由用户自行保存 / 删除，存放在 data/presets/<角色>/<预设名>.json；
  // 应用时按 sorting_order 在当前部件表里匹配勾选（同一 order 命中多条时优先取
  // 预设里记录的同名部件），并恢复素描本文字参数。

  function presetList() {
    const d = App.characterData;
    return (d && Array.isArray(d.presets)) ? d.presets : [];
  }

  // 当前预设下拉实例（自绘下拉，选项变化时整体重建）
  let _presetDropdown = null;

  function presetList() {
    const d = App.characterData;
    return (d && Array.isArray(d.presets)) ? d.presets : [];
  }

  function currentPresetName() {
    return _presetDropdown ? _presetDropdown.value : '';
  }

  // 预设选项文案（下拉条目 / 按钮气泡共用）；内置预设附标记
  function presetOptionLabel(name) {
    const p = presetList().find((x) => x.name === name);
    if (!p) return t('parts.preset_placeholder');
    const label = t('parts.preset_option', { name: p.name, count: (p.parts || []).length });
    return p.builtin ? label + t('parts.preset_builtin_suffix') : label;
  }

  // 触发按钮宽度有限（过长省略号）：悬停展示完整名称（统一 .ui-tip 气泡）；无预设时不挂提示
  function syncPresetTip() {
    if (!_presetDropdown) return;
    const trigger = _presetDropdown.el.querySelector('.color-picker-btn');
    if (!trigger) return;
    const hasPresets = presetList().length > 0;
    setTipText(trigger, hasPresets ? presetOptionLabel(currentPresetName()) : '');
  }

  // 重置预设栏（切换角色 / 清空部件页）
  function resetPresetBar() {
    if (_presetDropdown) { _presetDropdown.el.remove(); _presetDropdown = null; }
    const save = $('#btn-preset-save');
    if (save) save.disabled = true;
    const del = $('#btn-preset-delete');
    if (del) del.disabled = true;
  }

  // 预设下拉：自绘（与设置/预览画质同款，不用原生 select）：只列出真实预设；
  // 未选择时按钮显示占位文案（列表里不再放多余的“预设…”条目）；
  // 选项集合随保存/删除变化，因此每次整体重建；keep 指定要保留的选中项。
  function renderPresetOptions(keep) {
    const slot = $('#preset-slot');
    if (!slot) return;
    const prev = (keep === undefined) ? currentPresetName() : keep;
    const options = presetList().map((p) => ({ value: p.name, label: presetOptionLabel(p.name) }));
    const next = options.some((o) => o.value === prev) ? prev : '';
    if (_presetDropdown) _presetDropdown.el.remove();
    _presetDropdown = createDropdown({
      options,
      value: next,
      placeholder: t('parts.preset_placeholder'),
    });
    _presetDropdown.onChange = (v) => { onPresetSelect(v); syncPresetTip(); };
    const trigger = _presetDropdown.el.querySelector('.color-picker-btn');
    if (trigger) trigger.disabled = options.length === 0;   // 无预设：点开也是空列表
    slot.appendChild(_presetDropdown.el);
    syncPresetTip();
    updatePresetButtons();
  }

  // ── 标识名 / 预设名校验（与后端 preset_store.validate_preset_name 一致，先在前端拦一道）──
  const PRESET_NAME_MAX = 40;
  const PRESET_NAME_BAD_CHARS = /[<>:"/\\|?*\u0000-\u001f]/;

  // 返回错误说明（'' = 合法）：empty / too_long / invalid_chars / trailing_dot_space
  function checkPresetName(name) {
    const raw = String(name || '').trim();
    if (!raw) return 'empty';
    if (raw.length > PRESET_NAME_MAX) return 'too_long';
    if (PRESET_NAME_BAD_CHARS.test(raw)) return 'invalid_chars';
    if (/[. ]$/.test(raw)) return 'trailing_dot_space';
    return '';
  }

  // 后端预设错误码 → 文案（保存 / 导入共用；未知错误回退到 fallbackKey）
  function presetErrorText(r, name, fallbackKey) {
    const err = (r && r.error) || '';
    switch (err) {
      case 'builtin': return t('parts.preset_builtin_name', { name });
      case 'bad_name': return t('parts.preset_name_invalid');
      case 'name_conflict': return t('parts.preset_name_conflict', { name });
      case 'game_mismatch': return t('parts.preset_import_game_mismatch', { name: (r && r.game) || '' });
      case 'no_game':
      case 'unknown_game': return t('parts.preset_import_bad_game', { name: (r && r.game) || '' });
      case 'character_mismatch': return t('parts.preset_import_char_mismatch', { name: (r && r.character) || '' });
      case 'no_character_id':
      case 'unknown_character': return t('parts.preset_import_bad_character', { name: (r && r.character) || '' });
      case 'no_match': return t('parts.preset_import_no_match');
      default: return t(fallbackKey);
    }
  }

  // 当前（或指定）预设是否为内置：内置不可删除 / 不可覆盖
  function isBuiltinSelected(name) {
    const target = (name === undefined) ? currentPresetName() : name;
    return presetList().some((p) => p.name === target && p.builtin);
  }

  function updatePresetButtons() {
    const locked = isBuiltinSelected();
    const del = $('#btn-preset-delete');
    if (del) {
      del.disabled = !currentPresetName() || locked;
      setTipText(del, locked ? t('parts.preset_builtin_readonly') : '');
    }
    const save = $('#btn-preset-save');
    if (save) save.disabled = !App.characterData || App.selected.size === 0;
    const exp = $('#btn-preset-export');
    if (exp) exp.disabled = !currentPresetName();
  }

  // 恢复预设里的素描本参数（仅 Anan 素描模式有意义；同步滑块/分段/摘要）
  function restoreSketch(sk) {
    if (typeof sk.text === 'string') App.sketchText = sk.text;
    const size = Number(sk.size);
    if (size) App.sketchSize = size;
    if (sk.align) App.sketchAlign = sk.align;
    const slider = $('#sketch-size');
    if (slider) slider.value = String(App.sketchSize || 56);
    syncSketchSizeLabel();
    syncSketchAlign();
    syncSketchSummary();
  }

  // 应用预设：按 sorting_order 恢复勾选，并恢复素描本参数；返回选中数量
  function applyPreset(preset) {
    if (!App.characterData || !preset) return 0;
    const byOrder = {};
    App.characterData.transform_data.forEach((p) => {
      (byOrder[p.sorting_order] = byOrder[p.sorting_order] || []).push(p.name);
    });
    App.selected.clear();
    (preset.parts || []).forEach((e) => {
      const names = byOrder[e.sorting_order];
      if (!names || !names.length) return;   // 该 order 在当前数据里不存在（脏预设）→ 跳过
      const picked = names.indexOf(e.name) >= 0 ? [e.name] : names;
      picked.forEach((n) => App.selected.add(n));
    });
    Object.keys(App.partEls).forEach((name) => {
      App.partEls[name].cb.checked = App.selected.has(name);
    });
    restoreSketch(preset.sketch || {});
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    return App.selected.size;
  }

  // 下拉切换：选中即应用并刷新预览
  function onPresetSelect(name) {
    updatePresetButtons();
    if (!name) return;
    const preset = presetList().find((p) => p.name === name);
    if (!preset) return;
    const n = applyPreset(preset);
    if (n === 0) { toast(t('parts.preset_empty'), 'warning'); return; }
    toast(t('parts.preset_applied', { name, count: n }), 'success');
    if (App.autoUpdate) schedulePreview();
    else doComposite();
  }

  // 保存预设：弹窗输入名称 → 选中的部件（含 sorting_order）+ 素描本参数写入后端
  function savePreset() {
    if (!App.characterData) return;
    if (App.selected.size === 0) { toast(t('parts.preset_need_selection'), 'warning'); return; }
    const input = document.createElement('input');
    input.className = 'preset-name-input';
    input.type = 'text';
    input.maxLength = 40;
    input.placeholder = t('parts.preset_name_hint');
    input.value = currentPresetName() || '';
    const footer = document.createElement('div');
    const no = btn(t('dialog.cancel'), 'btn sm', () => close());
    const yes = btn(t('dialog.ok'), 'btn sm primary', async () => {
      const pname = input.value.trim();
      if (checkPresetName(pname)) {
        toast(t('parts.preset_name_invalid'), 'warning');
        input.focus();
        return;
      }
      if (isBuiltinSelected(pname)) {
        // 内置预设：禁止同名新建 / 覆盖
        toast(t('parts.preset_builtin_name', { name: pname }), 'warning');
        return;
      }
      if (presetList().some((p) => p.name === pname)) {
        const ok = await confirmDialog(
          t('parts.preset_overwrite_title'),
          t('parts.preset_overwrite_msg', { name: pname })
        );
        if (!ok) return;
      }
      close();
      const r = await api().save_preset(
        App.characterData.name, pname, Array.from(App.selected),
        sketchTextArg(), sketchSizeArg(), sketchAlignArg()
      );
      if (!r || !r.success) {
        const known = r && ['builtin', 'bad_name', 'name_conflict'].indexOf(r.error) >= 0;
        toast(known ? presetErrorText(r, pname, 'parts.preset_save_failed')
                    : t('parts.preset_save_failed'), 'error');
        if (r && r.presets) {
          App.characterData.presets = r.presets;
          renderPresetOptions(currentPresetName());
        }
        return;
      }
      App.characterData.presets = r.presets || [];
      renderPresetOptions(pname);
      toast(t('parts.preset_saved', { name: pname, count: App.selected.size }), 'success');
    });
    footer.appendChild(no); footer.appendChild(yes);
    const { close } = showModal({ titleKey: 'parts.preset_name_title', body: input, footer });
    setTimeout(() => { input.focus(); input.select(); }, 60);
  }

  // 删除当前选中的预设（确认后删除）
  async function deletePreset() {
    const pname = currentPresetName();
    if (!pname || !App.characterData) return;
    if (isBuiltinSelected(pname)) {
      toast(t('parts.preset_builtin_readonly'), 'warning');
      return;
    }
    const ok = await confirmDialog(
      t('parts.preset_delete_title'),
      t('parts.preset_delete_msg', { name: pname })
    );
    if (!ok) return;
    const r = await api().delete_preset(App.characterData.name, pname);
    if (!r || !r.success) {
      toast(r && r.error === 'builtin'
        ? t('parts.preset_builtin_readonly')
        : t('parts.preset_delete_failed'), 'error');
      if (r && r.presets) { App.characterData.presets = r.presets; renderPresetOptions(''); }
      return;
    }
    App.characterData.presets = r.presets || [];
    renderPresetOptions('');
    toast(t('parts.preset_deleted', { name: pname }), 'success');
  }

  // ── 预设导入 / 导出（模态窗口）─────────────────────────
  // 代码格式: <游戏标识>,<角色标识>,<排序值>…   例: manosaba,hiro,1,52,97,130
  // 文件格式: 本工具导出的预设 .json（character_name / name / parts[{name, sorting_order}] / sketch）

  function presetGame() {
    return (App.info && App.info.mode) || 'manosaba';
  }

  // 预设 → 代码文本（排序值升序，便于阅读与对比）
  function presetToCode(preset) {
    const orders = (preset.parts || [])
      .map((p) => Number(p.sorting_order) || 0)
      .sort((a, b) => a - b);
    return [presetGame(), App.characterData.name].concat(orders).join(',');
  }

  // 代码文本 → {game, character, orders}；逗号/空白分隔均可，格式不对返回 null
  function parsePresetCode(text) {
    const segs = String(text || '').replace(/^\uFEFF/, '').trim().split(/[\s,]+/).filter(Boolean);
    if (segs.length < 2) return null;
    const orders = segs.slice(2).map((s) => Number(s));
    if (orders.some((n) => !Number.isFinite(n))) return null;
    return { game: segs[0], character: segs[1], orders: orders.map((n) => Math.trunc(n)) };
  }

  // 预设 → JSON 文本（与 data/presets 里的文件同构；带 game 标识便于导入时校验）
  function presetToJson(preset) {
    return JSON.stringify({
      game: presetGame(),
      character_name: App.characterData.name,
      name: preset.name,
      parts: (preset.parts || []).map((p) => ({ name: p.name, sorting_order: p.sorting_order })),
      sketch: preset.sketch || { text: '', size: 56, align: 'center' },
      updated: preset.updated || '',
    }, null, 2);
  }

  // JSON 文本 → {game, character, name, parts}；解析失败/无部件返回 null
  function parsePresetJson(text) {
    // 去掉 UTF-8 BOM：记事本等编辑器保存的 .json 会带 \uFEFF，否则 JSON.parse 直接抛错
    const src = String(text || '').replace(/^\uFEFF/, '').trim();
    let raw = null;
    try { raw = JSON.parse(src); } catch (e) { return null; }
    if (!raw || typeof raw !== 'object') return null;
    const parts = (Array.isArray(raw.parts) ? raw.parts : [])
      .filter((p) => p && p.name)
      .map((p) => ({ name: String(p.name), sorting_order: Number(p.sorting_order) || 0 }));
    if (!parts.length) return null;
    return {
      game: String(raw.game || raw.mode || ''),
      character: String(raw.character_name || raw.character || ''),
      name: String(raw.name || ''),
      parts,
    };
  }

  function readFileText(file) {
    return new Promise((resolve) => {
      const fr = new FileReader();
      fr.onload = () => resolve(String(fr.result || ''));
      fr.onerror = () => resolve(null);
      fr.readAsText(file, 'utf-8');
    });
  }

  // 选 .json：Electron 走原生对话框（主进程读盘），浏览器退回 <input type=file>
  function pickPresetFile() {
    const ep = window.__electron && window.__electron.preset;
    if (ep && ep.importFile) return ep.importFile();
    return new Promise((resolve) => {
      const inp = document.createElement('input');
      inp.type = 'file';
      inp.accept = '.json,application/json';
      inp.addEventListener('change', () => {
        const f = inp.files && inp.files[0];
        if (!f) { resolve({ cancelled: true }); return; }
        readFileText(f).then((text) => resolve(
          text === null ? { error: 'read_failed' } : { name: f.name, text }
        ));
      });
      inp.click();
    });
  }

  // 保存文本文件：Electron 走原生保存对话框，浏览器退回 Blob 下载
  async function saveTextFile(defaultName, text) {
    const ep = window.__electron && window.__electron.preset;
    if (ep && ep.exportFile) return ep.exportFile(defaultName, text);
    try {
      const url = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = defaultName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      return { ok: true, path: '' };
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  }

  // 执行导入 + 应用结果（已确认标识与当前角色一致）
  // 返回 'ok' | 'cancel'（用户取消了覆盖确认）| 'fail'——调用方据此决定是否关闭模态
  async function runPresetImport(job) {
    const run = (overwrite) => api().import_preset(
      App.characterData.name, job.pname, job.orders, job.parts, job.game, overwrite
    );
    let r = await run(false);
    if (r && r.error === 'exists') {
      const yes = await confirmDialog(t('parts.preset_overwrite_title'),
                                      t('parts.preset_import_exists', { name: job.pname }));
      if (!yes) return 'cancel';
      r = await run(true);
    }
    if (!r || !r.success) {
      toast(presetErrorText(r, job.pname, 'parts.preset_import_failed'), 'error');
      if (r && r.presets) {
        App.characterData.presets = r.presets;
        renderPresetOptions(currentPresetName());
      }
      return 'fail';
    }
    App.characterData.presets = r.presets || [];
    const imported = (r.preset && r.preset.name) || job.pname;
    renderPresetOptions(imported);
    toast(t('parts.preset_imported', {
      name: imported, count: r.count || 0, skipped: ((r.skipped || []).length),
    }), 'success');
    return 'ok';
  }

  // 导入模态：两个标签页（文件 / 代码）+ 预设名输入
  // initial：可选 {name, text}——由窗口级拖入 .json 时预填（见 importPresetFile）。
  // 这里做形状校验，避免事件对象之类的真值被当成文件内容而弹出假的"JSON 格式不正确"。
  function importPreset(initial) {
    if (!App.characterData) return;
    const initialFile = (initial && typeof initial.text === 'string') ? initial : null;
    const state = { mode: 'file', fileName: '', fileParsed: null };

    const body = document.createElement('div');
    body.className = 'preset-modal';
    const tabs = document.createElement('div');
    tabs.className = 'preset-tabs';
    const tabFile = btn(t('parts.preset_tab_file'), 'preset-tab active', () => setMode('file'));
    const tabCode = btn(t('parts.preset_tab_code'), 'preset-tab', () => setMode('code'));
    tabs.appendChild(tabFile);
    tabs.appendChild(tabCode);

    // 文件面板：「选择 / 拖入」单按钮 + 状态行
    const filePane = document.createElement('div');
    filePane.className = 'preset-pane';
    // 按钮本身即拖放卡片：点击 = 系统文件选择框，拖入 = 直接预填；虚线区域，拖拽经过时高亮
    // （实际落点仍是整个模态，拖到哪都能放）
    const dropCard = document.createElement('button');
    dropCard.type = 'button';
    dropCard.className = 'preset-drop-card';
    dropCard.innerHTML =
      '<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true">' +
      '<path d="M12 15V4m0 0 3.5 3.5M12 4 8.5 7.5M4.5 14.5V18a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2v-3.5"' +
      ' fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>';
    const dropTitle = document.createElement('span');
    dropTitle.className = 'preset-drop-title';
    dropTitle.textContent = t('parts.preset_import_choose');
    const dropSub = document.createElement('span');
    dropSub.className = 'preset-drop-sub';
    dropSub.textContent = t('parts.preset_import_file_hint');
    dropCard.appendChild(dropTitle);
    dropCard.appendChild(dropSub);
    dropCard.addEventListener('click', () => chooseFile());
    const fileStatus = document.createElement('div');
    fileStatus.className = 'preset-file-status';
    fileStatus.textContent = t('parts.preset_import_no_file');
    filePane.appendChild(dropCard);
    filePane.appendChild(fileStatus);

    // 代码面板：<游戏标识>,<角色标识>,<排序值>…
    const codePane = document.createElement('div');
    codePane.className = 'preset-pane';
    codePane.hidden = true;
    const codeHint = document.createElement('p');
    codeHint.className = 'hint';
    codeHint.textContent = t('parts.preset_import_code_hint');
    const codeArea = document.createElement('textarea');
    codeArea.className = 'preset-textarea';
    codeArea.rows = 4;
    codeArea.spellcheck = false;
    codeArea.placeholder = t('parts.preset_import_code_placeholder');
    codePane.appendChild(codeHint);
    codePane.appendChild(codeArea);

    // 预设名（文件导入时会被文件里的名字预填）
    const nameRow = document.createElement('div');
    nameRow.className = 'preset-name-row';
    const nameLabel = document.createElement('label');
    nameLabel.textContent = t('parts.preset_import_name');
    const nameInput = document.createElement('input');
    nameInput.type = 'text';
    nameInput.className = 'preset-name-input';
    nameInput.maxLength = 40;
    nameInput.value = t('parts.preset_import_default_name');
    nameRow.appendChild(nameLabel);
    nameRow.appendChild(nameInput);

    body.appendChild(tabs);
    body.appendChild(filePane);
    body.appendChild(codePane);
    body.appendChild(nameRow);

    const footer = document.createElement('div');
    const cancel = btn(t('dialog.cancel'), 'btn sm', () => close());
    const okBtn = btn(t('dialog.ok'), 'btn sm primary', () => doImport());
    footer.appendChild(cancel);
    footer.appendChild(okBtn);

    const { close, backdrop } = showModal({ titleKey: 'parts.preset_import_title', body, footer });

    function setMode(mode) {
      state.mode = mode;
      const isFile = mode === 'file';
      tabFile.classList.toggle('active', isFile);
      tabCode.classList.toggle('active', !isFile);
      filePane.hidden = !isFile;
      codePane.hidden = isFile;
      if (!isFile) setTimeout(() => codeArea.focus(), 40);
    }

    function applyFile(res) {
      if (!res || res.cancelled) return;
      const parsed = parsePresetJson(res.text);
      if (!parsed) { toast(t('parts.preset_import_bad_file'), 'error'); return; }
      state.fileName = res.name || '';
      state.fileParsed = parsed;
      if (parsed.name) nameInput.value = parsed.name;
      const mismatch = !!parsed.character && parsed.character !== App.characterData.name;
      fileStatus.textContent = t('parts.preset_import_loaded',
        { name: state.fileName, count: parsed.parts.length })
        + (mismatch ? ' · ' + t('parts.preset_import_char_mismatch', { name: parsed.character }) : '');
      fileStatus.classList.toggle('ok', !mismatch);
    }

    async function chooseFile() {
      const res = await pickPresetFile();
      if (res && res.error) { toast(t('parts.preset_import_bad_file'), 'error'); return; }
      applyFile(res);
    }

    // 拖入 .json 也能导入：整个模态遮罩层都可放下（头/底/四周均可），卡片只负责高亮反馈
    // stopPropagation 必要：否则窗口级的「拖入游戏目录」会抢走这次拖放并弹文件夹遮罩
    const dropZone = backdrop || body;
    const markDrop = (on) => dropCard.classList.toggle('drop', on);
    dropZone.addEventListener('dragover', (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (state.mode !== 'file') setMode('file');   // 在「代码」页拖入时自动切回文件页
      markDrop(true);
    });
    dropZone.addEventListener('dragleave', (e) => {
      e.stopPropagation();
      if (e.target === dropZone) markDrop(false);
    });
    dropZone.addEventListener('drop', async (e) => {
      e.preventDefault();
      e.stopPropagation();
      markDrop(false);
      const f = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      if (!f) return;
      setMode('file');
      applyFile({ name: f.name, text: await readFileText(f) });
    });

    // 窗口级拖入的 .json（charlist.js 转交）：打开模态即预填，省去再点一次「选择 JSON 文件」
    if (initialFile) { setMode('file'); applyFile(initialFile); }

    async function doImport() {
      const pname = nameInput.value.trim();
      if (!pname) { toast(t('parts.preset_import_need_name'), 'warning'); return; }
      if (checkPresetName(pname)) {
        toast(t('parts.preset_name_invalid'), 'warning');
        nameInput.focus();
        return;
      }
      let orders = null;
      let parts = null;
      let game = '';
      let character = '';
      if (state.mode === 'code') {
        const parsed = parsePresetCode(codeArea.value);
        if (!parsed || !parsed.orders.length) {
          toast(t('parts.preset_import_bad_code'), 'warning');
          return;
        }
        game = parsed.game;
        character = parsed.character;
        orders = parsed.orders;
      } else {
        if (!state.fileParsed) { toast(t('parts.preset_import_need_file'), 'warning'); return; }
        // 旧文件可能没有 game 字段：视为当前作品（角色标识仍严格校验）
        game = state.fileParsed.game || presetGame();
        character = state.fileParsed.character;
        parts = state.fileParsed.parts;
      }

      // ── 标识名匹配：游戏 / 角色必须与当前会话一致；不合法立即拦下 ──
      // （不自动跳转角色：未知角色/作品一律不触发加载或分析，避免误操作）
      const modes = ((App.info && App.info.modes) || [presetGame()]).map((m) => String(m).toLowerCase());
      if (!game) {
        toast(t('parts.preset_import_bad_game', { name: '' }), 'warning');
        return;
      }
      if (modes.indexOf(game.toLowerCase()) < 0) {
        toast(t('parts.preset_import_bad_game', { name: game }), 'warning');
        return;
      }
      if (game.toLowerCase() !== presetGame().toLowerCase()) {
        toast(t('parts.preset_import_game_mismatch', { name: game }), 'warning');
        return;
      }
      const knownChars = Object.keys(App.bundles || {});
      const matched = knownChars.filter((n) => n.toLowerCase() === String(character).toLowerCase())[0] || '';
      if (!character) {
        toast(t('parts.preset_import_bad_character', { name: '' }), 'warning');
        return;
      }
      if (knownChars.length && !matched) {
        toast(t('parts.preset_import_bad_character', { name: character }), 'warning');
        return;
      }
      const current = App.characterData.name || '';
      if ((matched || character).toLowerCase() !== current.toLowerCase()) {
        toast(t('parts.preset_import_char_mismatch', { name: matched || character }), 'warning');
        return;
      }
      // 仅成功时关闭导入模态：取消覆盖确认 / 各种报错都保留输入，方便改完重试
      if (await runPresetImport({ pname, orders, parts, game, character }) === 'ok') close();
    }
  }

  // 把「拖入窗口的预设 .json」转成导入模态的预填内容（读盘失败按文件格式错误提示）
  async function importPresetFile(file) {
    if (!App.characterData || !file) return;
    const text = await readFileText(file);
    if (text === null) { toast(t('parts.preset_import_bad_file'), 'error'); return; }
    importPreset({ name: file.name || '', text });
  }

  // 导出模态：两个标签页（文件 / 代码），内容可复制；文件页可另存为 .json
  function exportPreset() {
    if (!App.characterData) return;
    const preset = presetList().find((p) => p.name === currentPresetName());
    if (!preset) { toast(t('parts.preset_export_need_select'), 'warning'); return; }
    const jsonText = presetToJson(preset);
    const codeText = presetToCode(preset);

    const body = document.createElement('div');
    body.className = 'preset-modal';
    const tabs = document.createElement('div');
    tabs.className = 'preset-tabs';
    const tabFile = btn(t('parts.preset_tab_file'), 'preset-tab active', () => setMode('file'));
    const tabCode = btn(t('parts.preset_tab_code'), 'preset-tab', () => setMode('code'));
    tabs.appendChild(tabFile);
    tabs.appendChild(tabCode);

    // 通用面板：提示 + 只读文本框 + 操作按钮行
    function makePane(hintText, text, actions) {
      const pane = document.createElement('div');
      pane.className = 'preset-pane';
      const hint = document.createElement('p');
      hint.className = 'hint';
      hint.textContent = hintText;
      const area = document.createElement('textarea');
      area.className = 'preset-textarea';
      area.rows = 8;
      area.readOnly = true;
      area.spellcheck = false;
      area.value = text;
      const row = document.createElement('div');
      row.className = 'preset-tab-actions';
      actions.forEach((a) => row.appendChild(a));
      pane.appendChild(hint);
      pane.appendChild(area);
      pane.appendChild(row);
      return pane;
    }

    const saveBtn = btn(t('parts.preset_export_save'), 'btn sm primary', async () => {
      const r = await saveTextFile(App.characterData.name + '_' + preset.name + '.json', jsonText);
      if (!r || (r.ok !== true && !r.canceled && !r.cancelled)) {
        toast(t('parts.preset_export_failed'), 'error');
        return;
      }
      if (r.ok && r.path) toast(t('parts.preset_export_saved', { path: r.path }), 'success');
    });
    // JSON 面板只保留「保存为文件」：文本本身可手动选中复制，不再单独放复制按钮
    const filePane = makePane(t('parts.preset_export_json_hint'), jsonText, [saveBtn]);
    const codePane = makePane(t('parts.preset_export_code_hint'), codeText, [
      btn(t('parts.preset_export_copy'), 'btn sm', () => copyText(codeText)),
    ]);
    codePane.hidden = true;

    body.appendChild(tabs);
    body.appendChild(filePane);
    body.appendChild(codePane);

    const footer = document.createElement('div');
    footer.appendChild(btn(t('parts.lightbox_close'), 'btn sm', () => close()));
    const { close } = showModal({ titleKey: 'parts.preset_export_title', body, footer });

    function setMode(mode) {
      const isFile = mode === 'file';
      tabFile.classList.toggle('active', isFile);
      tabCode.classList.toggle('active', !isFile);
      filePane.hidden = !isFile;
      codePane.hidden = isFile;
    }
  }

  // 语言切换后刷新部件页头部（角色名 + 计数）
  function refreshPartsHeader() {
    if (!App.characterData) return;
    $('#parts-name').textContent = charDisplayName(App.characterData.name);
    $('#parts-count').textContent = App.characterData.count + ' ' + t('parts.total');
    renderPresetOptions();   // 语言切换后刷新预设下拉文案（占位项 / 条目）
    setupPartsEaster();  // 语言切换后按当前语言/角色刷新部件卡彩蛋状态
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.clearPartsUI = clearPartsUI;
  MCE.setPartsPlaceholder = setPartsPlaceholder;
  MCE.naturalCmp = naturalCmp;
  MCE.partPrefix = partPrefix;
  MCE.sortParts = sortParts;
  MCE.filterParts = filterParts;
  MCE.renderParts = renderParts;
  MCE.setupPartsEaster = setupPartsEaster;
  MCE.teardownPartsEaster = teardownPartsEaster;
  MCE.showMemeEaster = showMemeEaster;
  MCE.spearEasterAvailable = spearEasterAvailable;
  MCE.startSpearEaster = startSpearEaster;
  MCE.finishSpearEaster = finishSpearEaster;
  MCE.spearTeardown = spearTeardown;
  MCE.onPartToggle = onPartToggle;
  MCE.isAnanSketchMode = isAnanSketchMode;
  MCE.syncSketchSizeLabel = syncSketchSizeLabel;
  MCE.syncSketchAlign = syncSketchAlign;
  MCE.syncSketchSummary = syncSketchSummary;
  MCE.openSketchModal = openSketchModal;
  MCE.updateSketchInput = updateSketchInput;
  MCE.sketchTextArg = sketchTextArg;
  MCE.sketchSizeArg = sketchSizeArg;
  MCE.sketchAlignArg = sketchAlignArg;
  MCE.updateSelUI = updateSelUI;
  MCE.selectAll = selectAll;
  MCE.onPresetSelect = onPresetSelect;
  MCE.savePreset = savePreset;
  MCE.deletePreset = deletePreset;
  MCE.importPreset = importPreset;
  MCE.importPresetFile = importPresetFile;
  MCE.exportPreset = exportPreset;
  MCE.renderPresetOptions = renderPresetOptions;
  MCE.deselectGroup = deselectGroup;
  MCE.isExcludedClipMask = isExcludedClipMask;
  MCE.selectClipMaskParts = selectClipMaskParts;
  MCE.refreshPartsHeader = refreshPartsHeader;
  // 长矛彩蛋锁定状态门面（backing 为本模块的 let；其他模块读写经此，避免跨闭包）
  MCE.spear = {
    get active() { return _spearEasterActive; },
    set active(v) { _spearEasterActive = v; },
    get previewReady() { return _spearPreviewReady; },
    set previewReady(v) { _spearPreviewReady = v; },
  };
})();
