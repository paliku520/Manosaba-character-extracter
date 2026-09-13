/* Manosaba Character Extracter — 日志控制台前端（独立窗口 webui/console/）
 *
 * 数据来源：Electron 主进程（preload 暴露 window.__electron.logConsole）
 *   - 'init' 事件：{ banner, lines }  打开控制台时回放的历史日志（主进程侧缓冲）
 *   - 'line' 事件：{ text, append }   增量日志；append=true 为多行日志的续行
 *   preload 在页面脚本订阅前会按到达顺序缓存事件、订阅时立即回放，
 *   因此不会丢日志也不会与 init 回放乱序。
 *
 * 多行日志（如“系统信息:”后跟 CPU/内存/系统三行）在 stderr 中按行到达，
 * 只有首行带级别；主进程按“一条日志 = 一条记录”合并后推送，
 * 本页把续行追加到同一行，使其在级别过滤 / 搜索时不会被拆散丢失。
 *
 * 展示能力：级别过滤（DEBUG/INFO/WARNING/ERROR）/ 关键字搜索（命中高亮）/
 *           自动跟随底部 / 自动换行 / 复制可见日志 / 导出日志文件 / 清空。
 */

(function () {
  'use strict';

  // 内存与 DOM 中保留的最大行数（超出丢弃最早的行，避免长时间运行内存膨胀）
  const MAX_LINES = 3000;
  // 搜索输入防抖（毫秒）：避免连续输入时反复重建列表
  const SEARCH_DEBOUNCE = 120;

  // ── 内置兜底文案：后端未就绪时界面仍可读；就绪后由 get_app_info 的翻译表覆盖 ──
  const FALLBACK = {
    zh_CN: {
      'console.title': '日志控制台',
      'console.filter_all': '全部',
      'console.filter_debug': '调试',
      'console.filter_info': '信息',
      'console.filter_warning': '警告',
      'console.filter_error': '错误',
      'console.search_placeholder': '搜索日志…',
      'console.autoscroll': '自动滚动',
      'console.wrap': '自动换行',
      'console.copy': '复制',
      'console.save': '导出日志',
      'console.clear': '清空',
      'console.empty': '暂无日志',
      'console.no_match': '没有匹配的日志',
      'console.status': '共 {total} 行 · 显示 {shown} 行',
      'console.copied': '已复制 {count} 行到剪贴板',
      'console.copy_failed': '复制失败',
      'console.save_done': '日志已保存: {path}',
      'console.save_failed': '保存失败: {msg}',
      'console.jump_latest': '跳到最新',
    },
    en_US: {
      'console.title': 'Log Console',
      'console.filter_all': 'All',
      'console.filter_debug': 'Debug',
      'console.filter_info': 'Info',
      'console.filter_warning': 'Warning',
      'console.filter_error': 'Error',
      'console.search_placeholder': 'Search logs…',
      'console.autoscroll': 'Auto scroll',
      'console.wrap': 'Wrap lines',
      'console.copy': 'Copy',
      'console.save': 'Export log',
      'console.clear': 'Clear',
      'console.empty': 'No logs yet',
      'console.no_match': 'No matching logs',
      'console.status': '{total} lines · showing {shown}',
      'console.copied': 'Copied {count} lines',
      'console.copy_failed': 'Copy failed',
      'console.save_done': 'Log saved: {path}',
      'console.save_failed': 'Save failed: {msg}',
      'console.jump_latest': 'Jump to latest',
    },
    ja_JP: {
      'console.title': 'ログコンソール',
      'console.filter_all': 'すべて',
      'console.filter_debug': 'デバッグ',
      'console.filter_info': '情報',
      'console.filter_warning': '警告',
      'console.filter_error': 'エラー',
      'console.search_placeholder': 'ログを検索…',
      'console.autoscroll': '自動スクロール',
      'console.wrap': '折り返し',
      'console.copy': 'コピー',
      'console.save': 'ログを保存',
      'console.clear': 'クリア',
      'console.empty': 'ログがありません',
      'console.no_match': '一致するログがありません',
      'console.status': '全 {total} 行 · 表示 {shown} 行',
      'console.copied': '{count} 行をコピーしました',
      'console.copy_failed': 'コピーに失敗しました',
      'console.save_done': 'ログを保存しました: {path}',
      'console.save_failed': '保存に失敗しました: {msg}',
      'console.jump_latest': '最新へ',
    },
    mgl_MG: {
      'console.title': 'Log Console',
      'console.filter_all': 'All',
      'console.filter_debug': 'Debug',
      'console.filter_info': 'Info',
      'console.filter_warning': 'Warning',
      'console.filter_error': 'Error',
      'console.search_placeholder': 'Search logs…',
      'console.autoscroll': 'Auto scroll',
      'console.wrap': 'Wrap lines',
      'console.copy': 'Copy',
      'console.save': 'Export log',
      'console.clear': 'Clear',
      'console.empty': 'No logs yet',
      'console.no_match': 'No matching logs',
      'console.status': '{total} lines · showing {shown}',
      'console.copied': 'Copied {count} lines',
      'console.copy_failed': 'Copy failed',
      'console.save_done': 'Log saved: {path}',
      'console.save_failed': 'Save failed: {msg}',
      'console.jump_latest': 'Jump to latest',
    },
  };

  // 日志行解析：标准行 = [yyyy-MM-dd HH:mm:ss] [来源] [级别] 内容
  const RE_FULL = /^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\]\s*\[([^\]\s]{1,12})\]\s*\[([A-Za-z]{1,12})\]\s?([\s\S]*)$/;
  // 无级别行（logtools 的 NONE 级别）：[yyyy-MM-dd HH:mm:ss] [来源] 内容
  const RE_TS = /^\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})\]\s*\[([^\]\s]{1,12})\]\s?([\s\S]*)$/;

  const $ = (id) => document.getElementById(id);

  const logEl = $('c-log');
  const bannerEl = $('c-banner');
  const countEl = $('c-count');
  const countsEl = $('c-counts');
  const msgEl = $('c-msg');
  const emptyEl = $('c-empty');
  const jumpEl = $('c-jump');
  const levelsEl = $('c-levels');
  const searchEl = $('c-search');
  const autoEl = $('c-autoscroll');
  const wrapEl = $('c-wrap');
  const copyEl = $('c-copy');
  const saveEl = $('c-save');
  const clearEl = $('c-clear');

  // 日志“记录”列表：[{ id, text }]（id 与 DOM 行的 data-id 对应，
  // 便于把多行日志的续行精确并回同一行；text 可包含换行）
  const state = { lines: [], filter: 'all', search: '' };
  let lineSeq = 0;
  const consoleApi = (window.__electron && window.__electron.logConsole) || null;

  /* ── 语言（沿用主界面的 i18n.js：data-i18n 由 applyDom 刷新） ── */

  function langFromQuery() {
    try {
      return new URLSearchParams(location.search).get('lang') || 'zh_CN';
    } catch (e) {
      return 'zh_CN';
    }
  }

  function t(key, params) {
    return window.I18N ? window.I18N.t(key, params) : key;
  }

  function applyFallbackI18n() {
    const lang = langFromQuery();
    if (window.I18N) window.I18N.set(FALLBACK[lang] || FALLBACK.zh_CN, lang, null);
  }

  // 翻译表由 Python 后端统一提供（单一数据源）；后端未就绪时静默保留兜底文案
  async function loadI18n() {
    try {
      const api = window.pywebview && window.pywebview.api;
      if (!api || typeof api.get_app_info !== 'function') return;
      const info = await api.get_app_info();
      if (info && info.translations) {
        window.I18N.set(info.translations, info.current_lang, info.lang_names);
        document.title = t('console.title');
        refresh();
      }
    } catch (e) { /* 后端未就绪：保留内置兜底文案 */ }
  }

  /* ── 日志行解析 / 渲染 ─────────────────────────────── */

  function normLevel(raw) {
    const s = String(raw || '').toUpperCase();
    if (s === 'DEBUG') return 'debug';
    if (s === 'INFO') return 'info';
    if (s === 'WARN' || s === 'WARNING') return 'warning';
    if (s === 'ERROR' || s === 'CRITICAL' || s === 'FATAL') return 'error';
    return 'plain';
  }

  function parseLine(line) {
    let m = RE_FULL.exec(line);
    if (m) return { time: m[2], src: m[3], level: normLevel(m[4]), text: m[5] };
    m = RE_TS.exec(line);
    if (m) return { time: m[2], src: m[3], level: 'plain', text: m[4] };
    // 无前缀行（log_raw 的分隔线 / 多行消息的续行等）：原样展示，保留字符画对齐
    return { time: '', src: '', level: 'plain', text: line };
  }

  // 把 text 写入 parent，命中搜索词的部分用 <mark> 高亮（全部走 textNode，不拼接 HTML）
  function appendHighlighted(parent, text, needle) {
    const s = String(text == null ? '' : text);
    if (!needle) {
      parent.appendChild(document.createTextNode(s));
      return;
    }
    const lower = s.toLowerCase();
    let from = 0;
    for (;;) {
      const idx = lower.indexOf(needle, from);
      if (idx < 0) {
        parent.appendChild(document.createTextNode(s.slice(from)));
        return;
      }
      if (idx > from) parent.appendChild(document.createTextNode(s.slice(from, idx)));
      const mark = document.createElement('mark');
      mark.textContent = s.slice(idx, idx + needle.length);
      parent.appendChild(mark);
      from = idx + needle.length;
    }
  }

  function cell(cls, text) {
    const span = document.createElement('span');
    span.className = cls;
    span.textContent = text;
    return span;
  }

  function buildRow(rec) {
    const p = parseLine(rec.text);
    const row = document.createElement('div');
    row.dataset.id = String(rec.id);

    // 无时间戳的原始行：整行展示，不做四列缩进（保持 ASCII 字符画/分隔线原样）
    if (!p.time) {
      row.className = 'll ll-plain';
      const msg = document.createElement('span');
      msg.className = 'll-msg';
      appendHighlighted(msg, p.text, state.search);
      row.appendChild(msg);
      return row;
    }

    row.className = 'll level-' + p.level;
    row.appendChild(cell('ll-time', p.time));
    row.appendChild(cell('ll-src', p.src));
    row.appendChild(cell('ll-lv', p.level === 'plain' ? '' : p.level.toUpperCase()));
    const msg = document.createElement('span');
    msg.className = 'll-msg';
    appendHighlighted(msg, p.text, state.search);
    row.appendChild(msg);
    return row;
  }

  function pass(rec) {
    if (state.filter !== 'all' && parseLine(rec.text).level !== state.filter) return false;
    if (state.search && rec.text.toLowerCase().indexOf(state.search) < 0) return false;
    return true;
  }

  function visibleLines() {
    const out = [];
    for (let i = 0; i < state.lines.length; i++) {
      if (pass(state.lines[i])) out.push(state.lines[i].text);
    }
    return out;
  }

  /* ── 滚动 / 计数 ───────────────────────────────────── */

  function atBottom() {
    return logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight <= 4;
  }

  function scrollToBottom() {
    logEl.scrollTop = logEl.scrollHeight;
  }

  function refresh() {
    const shown = logEl.children.length;
    const total = state.lines.length;
    countEl.textContent = String(total);
    countsEl.textContent = t('console.status', { total: total, shown: shown });
    emptyEl.textContent = total ? t('console.no_match') : t('console.empty');
    emptyEl.hidden = shown > 0;
  }

  /* ── 追加 / 重建 ───────────────────────────────────── */

  // 追加一条日志记录：append=true 表示多行日志的续行，并入上一条记录（不新增行）
  function addLine(text, append, bulk) {
    const s = text == null ? '' : String(text);
    // 仅在“追加前已贴底且勾选了自动滚动”时跟随；用户上翻时不打断阅读
    const follow = !bulk && autoEl.checked && atBottom();

    if (append && state.lines.length) {
      const rec = state.lines[state.lines.length - 1];
      rec.text += '\n' + s;
      syncRow(rec);
      if (bulk) return;
      refresh();
      if (follow) scrollToBottom();
      jumpEl.hidden = atBottom();
      return;
    }

    const rec = { id: ++lineSeq, text: s };
    state.lines.push(rec);
    if (state.lines.length > MAX_LINES) dropOldest();
    if (pass(rec)) logEl.appendChild(buildRow(rec));

    if (bulk) return;
    refresh();
    if (follow) scrollToBottom();
    jumpEl.hidden = atBottom();
  }

  // 丢弃最早的一条记录；若已在列表中渲染则同步移除对应 DOM 行（保持列表与记录一一对应）
  function dropOldest() {
    const rec = state.lines.shift();
    const first = logEl.firstElementChild;
    if (first && first.dataset.id === String(rec.id)) logEl.removeChild(first);
  }

  // 续行并入后同步该记录对应的 DOM 行：内容变了重渲染；合并后不再匹配过滤条件则移除
  function syncRow(rec) {
    const row = logEl.lastElementChild;
    const matches = pass(rec);
    if (row && row.dataset.id === String(rec.id)) {
      if (matches) row.replaceWith(buildRow(rec));
      else logEl.removeChild(row);
    } else if (matches) {
      logEl.appendChild(buildRow(rec));
    }
  }

  // 过滤 / 搜索变化：按内存中的原始记录整体重建列表
  function rerender() {
    const frag = document.createDocumentFragment();
    for (let i = 0; i < state.lines.length; i++) {
      if (pass(state.lines[i])) frag.appendChild(buildRow(state.lines[i]));
    }
    logEl.replaceChildren(frag);
    refresh();
    if (autoEl.checked) scrollToBottom();
    jumpEl.hidden = atBottom();
  }

  /* ── 主进程事件（init 回放 + 增量行） ───────────────── */

  function handleEvent(ev) {
    if (!ev) return;
    if (ev.type === 'init') {
      if (bannerEl && ev.banner) bannerEl.textContent = ev.banner;
      const lines = ev.lines || [];
      for (let i = 0; i < lines.length; i++) addLine(lines[i], false, true);
      refresh();
      if (autoEl.checked) scrollToBottom();
      jumpEl.hidden = atBottom();
      return;
    }
    if (ev.type === 'line') addLine(ev.text, ev.append);
  }

  /* ── 状态提示（状态栏右侧短暂消息） ─────────────────── */

  let msgTimer = null;
  function flash(text, ms) {
    if (!msgEl) return;
    clearTimeout(msgTimer);
    msgEl.textContent = text || '';
    msgEl.classList.toggle('show', !!text);
    if (text) msgTimer = setTimeout(() => msgEl.classList.remove('show'), ms || 2600);
  }

  /* ── 复制 / 导出 / 清空 ────────────────────────────── */

  async function copyText(text) {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(text);
        return true;
      }
    } catch (e) { /* 回退到 execCommand */ }
    try {
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.top = '-1000px';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      ta.remove();
      return ok;
    } catch (e) {
      return false;
    }
  }

  function bindEvents() {
    // 级别过滤
    levelsEl.addEventListener('click', (e) => {
      const btn = e.target.closest ? e.target.closest('.c-chip') : null;
      if (!btn) return;
      state.filter = btn.dataset.level || 'all';
      const chips = levelsEl.querySelectorAll('.c-chip');
      for (let i = 0; i < chips.length; i++) chips[i].classList.toggle('active', chips[i] === btn);
      rerender();
    });

    // 关键字搜索（防抖）
    let searchTimer = null;
    searchEl.addEventListener('input', () => {
      clearTimeout(searchTimer);
      searchTimer = setTimeout(() => {
        state.search = searchEl.value.trim().toLowerCase();
        rerender();
      }, SEARCH_DEBOUNCE);
    });

    // 自动滚动 / 自动换行
    autoEl.addEventListener('change', () => {
      if (autoEl.checked) {
        scrollToBottom();
        jumpEl.hidden = true;
      }
    });
    wrapEl.addEventListener('change', () => {
      logEl.classList.toggle('nowrap', !wrapEl.checked);
    });

    // 滚动时显示“跳到最新”（非底部且有内容时）
    logEl.addEventListener('scroll', () => {
      jumpEl.hidden = atBottom() || !logEl.scrollHeight;
    }, { passive: true });
    jumpEl.addEventListener('click', () => {
      scrollToBottom();
      jumpEl.hidden = true;
    });

    // 复制当前可见（过滤后）日志
    copyEl.addEventListener('click', async () => {
      const shown = visibleLines();
      if (!shown.length) {
        flash(t('console.empty'));
        return;
      }
      const ok = await copyText(shown.join('\n'));
      flash(ok ? t('console.copied', { count: shown.length }) : t('console.copy_failed'));
    });

    // 导出当前可见日志到文件（主进程弹原生保存对话框）
    saveEl.addEventListener('click', async () => {
      const text = visibleLines().join('\n');
      if (!text) {
        flash(t('console.empty'));
        return;
      }
      if (!consoleApi || !consoleApi.save) return;
      const r = await consoleApi.save(text);
      if (r && r.ok) flash(t('console.save_done', { path: r.path }), 4500);
      else if (!r || !r.canceled) flash(t('console.save_failed', { msg: (r && r.error) || '' }), 5000);
    });

    // 清空（同时清掉主进程侧历史缓冲，重开控制台不会回放已清空的日志）
    clearEl.addEventListener('click', async () => {
      state.lines = [];
      logEl.replaceChildren();
      refresh();
      jumpEl.hidden = true;
      if (consoleApi && consoleApi.clear) await consoleApi.clear();
    });
  }

  /* ── 初始化 ────────────────────────────────────────── */

  applyFallbackI18n();
  bindEvents();
  refresh();
  // 先订阅（preload 会按序回放订阅前缓存的事件），再拉取翻译表
  if (consoleApi) consoleApi.onEvent(handleEvent);
  loadI18n();
})();
