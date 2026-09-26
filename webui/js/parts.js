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
  const setTipText = (...a) => MCE.setTipText(...a);
  const copyText = (...a) => MCE.copyText(...a);
  const switchTab = (...a) => MCE.switchTab(...a);
  const charDisplayName = (...a) => MCE.charDisplayName(...a);
  const openPartLightbox = (...a) => MCE.openPartLightbox(...a);
  const clearPreview = (...a) => MCE.clearPreview(...a);
  const schedulePreview = (...a) => MCE.schedulePreview(...a);

  function clearPartsUI() {
    spearTeardown();        // 切换角色/清缓存时解除长矛彩蛋状态（防御性）
    teardownPartsEaster();  // 切换角色时移除 nanoka 部件卡彩蛋
    $('#parts-list').innerHTML = '';
    $('#parts-empty').hidden = false;
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
    let n = 0;
    list.forEach((name) => {
      if (isExcludedClipMask(name)) return;   // HairClippingMask 留给用户手动勾选
      App.selected.add(name);
      const el = App.partEls[name];
      if (el) el.cb.checked = true;
      n++;
    });
    if (n === 0) return;
    console.log(t('log.js_selected', { count: App.selected.size, total: App.characterData.transform_data.length }));
    updateSelUI();
    if (App.autoUpdate) schedulePreview();
    toast(t('parts.clip_selected', { count: n }), 'success');
  }

  // 语言切换后刷新部件页头部（角色名 + 计数）
  function refreshPartsHeader() {
    if (!App.characterData) return;
    $('#parts-name').textContent = charDisplayName(App.characterData.name);
    $('#parts-count').textContent = App.characterData.count + ' ' + t('parts.total');
    setupPartsEaster();  // 语言切换后按当前语言/角色刷新部件卡彩蛋状态
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.clearPartsUI = clearPartsUI;
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
