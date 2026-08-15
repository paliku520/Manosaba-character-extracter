/* Manosaba Character Extracter — preload：模拟 pywebview 前端接口，兼容现有 webui/ 代码
 *
 * 提供（与 pywebview 等价）：
 *   - window.pywebview.api.<method>(...args)   → Promise
 *   - window.__pywebview.events.<event>(payload)   ← 后端事件推送
 *   - pywebviewready 事件
 *
 * 窗口控制 / 对话框方法由主进程直接处理（白名单），其余方法走 Python 后端。
 * 注意：contextIsolation:false，直接写入 window（前端可能重建 __pywebview.events 对象）。
 */

const { ipcRenderer, webUtils } = require('electron');

window.__pywebview = window.__pywebview || {};
window.__pywebview.events = window.__pywebview.events || {};

// 运行模式标记：Electron（自绘无边框标题栏）；PyWebView 原生窗口模式无此标记
window.__ELECTRON__ = true;

// 主进程直接处理（不经 Python）
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

// Electron 专属能力（调试日志控制台、任务栏进度/闪烁）
window.__electron = {
  openLogConsole: () => ipcRenderer.invoke('win:openLogConsole'),
  // 拖拽导入：将拖入的 File 解析为磁盘绝对路径（Electron 29+ 标准 API）
  getPathForFile: (file) => webUtils.getPathForFile(file),
  // 任务栏（Windows 原生）：读条期间显示进度，读条完成后黄色闪烁
  taskbar: {
    progress: (value) => ipcRenderer.invoke('taskbar:progress', value),
    flash: () => ipcRenderer.invoke('taskbar:flash'),
  },
};

// 日志控制台窗口：接收主进程日志行并追加显示（主窗口无 #log 元素则忽略）
ipcRenderer.on('log-line', (_e, line) => {
  const el = document.getElementById('log');
  if (el) {
    el.textContent += line + '\n';
    el.scrollTop = el.scrollHeight;
  }
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

// 兼容 pywebview 就绪事件
window.addEventListener('DOMContentLoaded', () => {
  window.dispatchEvent(new Event('pywebviewready'));
});
