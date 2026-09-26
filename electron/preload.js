/* Manosaba Character Extracter — preload：前端 ↔ 后端桥接层
 *
 * 对外暴露（全项目统一的桥接命名，前端/控制台页面都按此调用）：
 *   - window.pywebview.api.<method>(...args)      → Promise（主进程/后端）
 *   - window.__pywebview.events.<event>(payload)  ← 后端事件推送
 *   - window.__electron.<...>                     ← Electron 专属能力
 *
 * 分工：
 *   - MAIN_ONLY 白名单（窗口控制 / 对话框 / 退出）→ 主进程直接处理，不经 Python
 *   - 其余方法 → invoke('api') → 主进程转发给 Python 后端（backend.py）
 *
 * 注意：contextIsolation:false，直接写入 window（前端会重建 __pywebview.events 对象）。
 */

const { ipcRenderer, webUtils } = require('electron');

window.__pywebview = window.__pywebview || {};
window.__pywebview.events = window.__pywebview.events || {};

// 主进程直接处理（不经 Python）：与 electron/main.js 的 ipcMain.handle 一一对应
const MAIN_ONLY = {
  window_minimize: () => ipcRenderer.invoke('win:minimize'),
  window_maximize: () => ipcRenderer.invoke('win:maximize'),
  window_is_maximized: () => ipcRenderer.invoke('win:isMaximized'),
  window_move: (dx, dy) => ipcRenderer.invoke('win:move', dx, dy),
  window_resize: (dir, dx, dy) => ipcRenderer.invoke('win:resize', dir, dx, dy),
  window_drag_start: () => Promise.resolve({ ok: true, maximized: false }),
  quit_app: () => ipcRenderer.invoke('win:quit'),
  select_directory: () => ipcRenderer.invoke('dialog:folder'),
  select_output_dir: () => ipcRenderer.invoke('dialog:folderOutput'),
};

const api = new Proxy(
  {},
  {
    get: (_, method) => {
      if (method === 'then') return undefined; // 防止 Promise 误判
      if (Object.prototype.hasOwnProperty.call(MAIN_ONLY, method)) {
        return MAIN_ONLY[method];
      }
      return (...args) => ipcRenderer.invoke('api', { method, args });
    },
  }
);

window.pywebview = { api };

// Electron 专属能力（调试日志控制台、任务栏进度/闪烁、重启、系统信息）
window.__electron = {
  openLogConsole: () => ipcRenderer.invoke('win:openLogConsole'),
  // 重启应用（禁用硬件加速等需重启生效时使用）
  restart: () => ipcRenderer.invoke('win:restart'),
  // 系统信息（CPU/内存/GPU/显存/OS）
  sysInfo: () => ipcRenderer.invoke('sys:info'),
  gpuInfo: () => ipcRenderer.invoke('sys:gpu'),
  // 拖拽导入：将拖入的 File 解析为磁盘绝对路径（Electron 29+ 标准 API）
  getPathForFile: (file) => webUtils.getPathForFile(file),
  // 窗口最大化/还原（原生双击标题栏、Aero Snap 也会触发）→ 前端同步图标与缩放手柄
  onMaximizedChanged: (cb) => {
    if (typeof cb !== 'function') return;
    ipcRenderer.on('win:maximized-changed', (_e, maximized) => cb(!!maximized));
  },
  // 任务栏（Windows 原生）：读条期间显示进度，读条完成后黄色闪烁
  taskbar: {
    progress: (value) => ipcRenderer.invoke('taskbar:progress', value),
    flash: () => ipcRenderer.invoke('taskbar:flash'),
  },
  // 日志控制台（独立窗口）：订阅日志事件 + 清空主进程缓冲 + 导出日志文件
  logConsole: {
    // 订阅：preload 先于页面脚本运行，订阅前到达的事件会按序缓存、订阅时立即回放
    onEvent: (cb) => {
      if (typeof cb !== 'function' || logConsoleSubscriber) return;
      logConsoleSubscriber = cb;
      const buffered = logConsoleEvents.splice(0);
      for (let i = 0; i < buffered.length; i++) cb(buffered[i]);
    },
    clear: () => ipcRenderer.invoke('log:clear'),
    save: (text) => ipcRenderer.invoke('log:save', text),
  },
  // 预设导入 / 导出（原生文件对话框 + 主进程读写）
  preset: {
    importFile: () => ipcRenderer.invoke('preset:importFile'),
    exportFile: (defaultName, text) => ipcRenderer.invoke('preset:exportFile', { defaultName, text }),
  },
  // 外观同步：主窗口主题/主题色/语言/动画变更时广播给其它窗口（日志控制台等）
  //   broadcast(data)  主窗口调用，交给主进程转发给其余窗口
  //   onUpdate(cb)     子窗口订阅；若订阅前已收到过广播，立即回放最后一次
  appearance: {
    broadcast: (data) => ipcRenderer.invoke('app:broadcastAppearance', data),
    onUpdate: (cb) => {
      if (typeof cb !== 'function') return;
      appearanceSubscribers.push(cb);
      if (appearanceLast) cb(appearanceLast);
    },
  },
};

// 外观同步（主窗口 → 子窗口）：preload 先于页面脚本运行，保留最后一次广播，
// 供晚订阅的页面（如打开较慢的日志控制台）订阅时立即对齐外观。
const appearanceSubscribers = [];
let appearanceLast = null;

ipcRenderer.on('app:appearance', (_e, data) => {
  appearanceLast = data || null;
  for (let i = 0; i < appearanceSubscribers.length; i++) appearanceSubscribers[i](appearanceLast);
});

// 日志控制台窗口：主进程先发 log:init（字符画 + 历史日志），随后逐条发 log-line。
// 页面脚本可能在首条日志到达之后才订阅，因此此处先入队、订阅时按到达顺序回放，
// 保证不丢日志、且历史回放与增量日志不会乱序。
const logConsoleEvents = [];       // 订阅前缓存的事件（有序）
let logConsoleSubscriber = null;   // 控制台页面订阅回调（仅一个）

function emitLogConsoleEvent(ev) {
  if (logConsoleSubscriber) logConsoleSubscriber(ev);
  else logConsoleEvents.push(ev);
}

ipcRenderer.on('log:init', (_e, payload) => {
  emitLogConsoleEvent({
    type: 'init',
    banner: (payload && payload.banner) || '',
    lines: (payload && payload.lines) || [],
  });
});

ipcRenderer.on('log-line', (_e, payload) => {
  // 主进程发送 { text, append }：append=true 表示多行日志的续行（前端追加到同一行）
  const p = (payload && typeof payload === 'object') ? payload : { text: payload };
  emitLogConsoleEvent({
    type: 'line',
    text: String(p.text == null ? '' : p.text),
    append: !!p.append,
  });
});

// 后端事件推送 → 前端 window.__pywebview.events.<event>(payload)
ipcRenderer.on('py-event', (_e, msg) => {
  const ev = (window.__pywebview && window.__pywebview.events) || {};
  if (typeof ev[msg.event] === 'function') {
    try {
      ev[msg.event](msg.payload);
    } catch (err) {
      console.error('[preload] event handler error', err);
    }
  }
});
