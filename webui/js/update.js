/* ============================================================
 * update.js — 检查更新弹窗 + Release 更新内容渲染（极简 Markdown → HTML）
 *
 * 依赖：core.js（必须已加载）；跨模块函数用转发别名晚绑定。
 * 由原 webui/js/app.js 拆分而来（行为、事件名、API 名保持不变）。
 * 说明：事件注册 on('update_result', …) 在 events.js，转调本模块 showUpdateDialog。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { t, api, escapeHtml, App } = MCE;

  // ── 跨模块转发别名（晚绑定）──────────────────────────────
  const btn = (...a) => MCE.btn(...a);
  const showModal = (...a) => MCE.showModal(...a);

  // ── Release 更新内容（极简 Markdown → HTML） ──
  // 只支持 Release 说明常用语法（标题/列表/代码/强调/链接/引用/分隔线）；
  // 先整体转义再套标签（不会产生注入），链接不写 href，改用 data-url 由点击委托调后端 open_url 打开，
  // 避免在 WebView 内部跳转（外部链接统一用系统浏览器打开）。
  const RELEASE_NOTES_MAX = 20000;   // 渲染上限（防止异常超长说明卡顿）

  function renderReleaseNotes(md) {
    const link = (text, url) =>
      '<a class="rn-link" role="link" tabindex="0" data-url="' + escapeHtml(url) + '">' + text + '</a>';
    const inline = (s) => {
      let h = escapeHtml(s);
      h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
      h = h.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, text, url) => link(text, url));
      h = h.replace(/(^|[\s(（【])(https?:\/\/[^\s<)）】]+)/g, (m, pre, url) => pre + link(url, url));
      h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      h = h.replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
      h = h.replace(/~~([^~]+)~~/g, '<del>$1</del>');
      return h;
    };

    const lines = String(md == null ? '' : md).slice(0, RELEASE_NOTES_MAX)
      .replace(/\r\n?/g, '\n').split('\n');
    let html = '';
    let list = '';        // 当前打开的列表标签：'' / 'ul' / 'ol'
    let para = [];        // 待输出的段落行
    let code = null;      // 代码块内容行（null 表示不在代码块内）

    const flushPara = () => {
      if (para.length) { html += '<p>' + para.map(inline).join('<br>') + '</p>'; para = []; }
    };
    const closeList = () => { if (list) { html += '</' + list + '>'; list = ''; } };

    for (const raw of lines) {
      const line = raw.replace(/\s+$/, '');
      // 代码块围栏：``` / ~~~（首尾各一次）
      if (/^\s*(```|~~~)/.test(line)) {
        if (code === null) { flushPara(); closeList(); code = []; }
        else { html += '<pre><code>' + escapeHtml(code.join('\n')) + '</code></pre>'; code = null; }
        continue;
      }
      if (code !== null) { code.push(raw); continue; }
      if (!line.trim()) { flushPara(); closeList(); continue; }

      let m;
      if ((m = line.match(/^\s{0,3}(#{1,6})\s+(.*)$/))) {
        flushPara(); closeList();
        const lvl = m[1].length <= 1 ? 4 : 5;
        html += '<h' + lvl + '>' + inline(m[2].trim()) + '</h' + lvl + '>';
      } else if (/^\s{0,3}(-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
        flushPara(); closeList();
        html += '<hr>';
      } else if ((m = line.match(/^\s*[-*+]\s+(.*)$/))) {
        flushPara();
        if (list !== 'ul') { closeList(); html += '<ul>'; list = 'ul'; }
        html += '<li>' + inline(m[1]) + '</li>';
      } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
        flushPara();
        if (list !== 'ol') { closeList(); html += '<ol>'; list = 'ol'; }
        html += '<li>' + inline(m[1]) + '</li>';
      } else if ((m = line.match(/^\s{0,3}>\s?(.*)$/))) {
        flushPara(); closeList();
        html += '<blockquote>' + inline(m[1]) + '</blockquote>';
      } else if (/^\s*<!--/.test(line)) {
        // 忽略 HTML 注释行（GitHub 自动生成的分隔注释等）
      } else {
        closeList();
        para.push(line.trim());
      }
    }
    flushPara(); closeList();
    if (code !== null && code.length) html += '<pre><code>' + escapeHtml(code.join('\n')) + '</code></pre>';
    return html;
  }

  // 更新弹窗：版本信息 +（可在设置中关闭 / 弹窗内关闭的）Release 更新内容 + 前往下载
  function showUpdateDialog(r) {
    const body = document.createElement('div');
    const msg = document.createElement('div');
    msg.className = 'desc';
    msg.textContent = t('dialog.update_available_msg', { new: r.latest, current: r.current });
    body.appendChild(msg);

    if (App.showReleaseNotes) {
      const title = document.createElement('div');
      title.className = 'update-notes-title';
      title.setAttribute('data-i18n', 'dialog.release_notes_title');
      title.textContent = t('dialog.release_notes_title');
      body.appendChild(title);

      const box = document.createElement('div');
      const notes = (r.notes || '').trim();
      if (notes) {
        box.className = 'update-notes';
        box.innerHTML = renderReleaseNotes(notes);
        // 说明内的链接统一交给后端在系统浏览器打开
        const openLink = (e) => {
          const a = e.target.closest('.rn-link');
          if (a && a.dataset.url && api()) { e.preventDefault(); api().open_url(a.dataset.url); }
        };
        box.addEventListener('click', openLink);
        box.addEventListener('keydown', (e) => {
          if (e.key === 'Enter' || e.key === ' ') openLink(e);
        });
      } else {
        box.className = 'update-notes is-empty';
        box.textContent = t('dialog.release_notes_empty');
      }
      body.appendChild(box);

      // 弹窗内关闭更新内容展示（持久化；可在设置中重新开启）
      const hideRow = document.createElement('label');
      hideRow.className = 'form-row update-notes-hide';
      const hideCb = document.createElement('input');
      hideCb.type = 'checkbox';
      const hideText = document.createElement('span');
      hideText.setAttribute('data-i18n', 'dialog.release_notes_hide');
      hideText.textContent = t('dialog.release_notes_hide');
      hideRow.appendChild(hideCb);
      hideRow.appendChild(hideText);
      body.appendChild(hideRow);
      hideCb.addEventListener('change', () => {
        App.showReleaseNotes = !hideCb.checked;
        if (App.info) App.info.show_release_notes = App.showReleaseNotes;
        if (api()) api().set_show_release_notes(App.showReleaseNotes);
      });
    }

    const footer = document.createElement('div');
    const closeBtn = btn(t('dialog.close'), 'btn sm', null);
    const go = btn(t('dialog.open_release'), 'btn sm primary', null);
    footer.appendChild(closeBtn); footer.appendChild(go);
    const { close } = showModal({
      titleKey: 'dialog.update_available_title',
      body,
      footer,
    });
    closeBtn.addEventListener('click', close);
    go.addEventListener('click', () => { api().open_url(r.url); close(); });
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.renderReleaseNotes = renderReleaseNotes;
  MCE.showUpdateDialog = showUpdateDialog;
})();
