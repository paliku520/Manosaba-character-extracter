/* ============================================================
 * hierarchy.js — 组件层级树（渲染 / 展开折叠 / 单节点复制）
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, fmt, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const setTipText = (...a) => MCE.setTipText(...a);
  const copyText = (...a) => MCE.copyText(...a);

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
    setTipText(copyBtn, t('app.click_to_copy'));
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

  // ── 导出 ────────────────────────────────────────────────
  MCE.renderHierarchy = renderHierarchy;
  MCE.buildNode = buildNode;
})();
