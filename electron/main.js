/* Manosaba Character Extracter — Electron 主进程
 *
 * 职责：
 *  1. 创建无边框窗口（frame:false），加载 webui/
 *     - 标题栏拖动 / 双击最大化 / Aero Snap 由 Electron 原生（-webkit-app-region: drag）处理
 *     - 边缘/角落缩放：前端 8 个缩放手柄 → win:resize → setBounds
 *     - 最大化：win.maximize()（原生不遮任务栏）
 *  2. 启动 Python 后端子进程（backend.py / 打包后 backend.exe），stdio JSON-RPC 桥接
 *  3. 文件夹选择对话框（dialog）
 */

const { app, BrowserWindow, ipcMain, dialog, screen, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const readline = require('readline');

// 禁用 Electron 开发模式的 CSP 安全警告（本应用仅加载本地文件，无远程内容；打包后本就不显示）
process.env.ELECTRON_DISABLE_SECURITY_WARNINGS = 'true';

// MCE 字符画（启动终端与日志控制台复用）
const MCE_BANNER = `███╗   ███╗ ██████╗███████╗
████╗ ████║██╔════╝██╔════╝
██╔████╔██║██║     █████╗  
██║╚██╔╝██║██║     ██╔══╝  
██║ ╚═╝ ██║╚██████╗███████╗
╚═╝     ╚═╝ ╚═════╝╚══════╝`;

// 启动字符画（终端可见；打包版无终端则不显示）
console.log('\n' + MCE_BANNER);

// 应用用户模型 ID（任务栏分组/通知归属；打包后进程名与图标由 electron-builder 提供）
app.setAppUserModelId('com.paliku520.manosaba-extracter');

let win = null;
let py = null;
let logWin = null;              // 日志控制台窗口（Electron BrowserWindow）
const logBuffer = [];           // 最近日志（打开控制台时回放）
const pending = new Map(); // id -> {resolve, reject}
let seq = 0;

/* ── Python 后端子进程 ───────────────────────────── */

function pyCommand() {
  if (app.isPackaged) {
    return {
      cmd: path.join(process.resourcesPath, 'backend', 'backend.exe'),
      args: [],
    };
  }
  // 开发模式：MCE_PYTHON 环境变量 → 项目 venv → PATH 中的 python
  const candidates = [
    process.env.MCE_PYTHON,
    path.join(__dirname, '..', '.venv', 'Scripts', 'python.exe'),
    path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe'),
    'python',
  ];
  const cmd = candidates.find((c) => c === 'python' || (c && fs.existsSync(c))) || 'python';
  return { cmd, args: [path.join(__dirname, '..', 'backend.py')] };
}

function backendEnv() {
  const env = { ...process.env, PYTHONUNBUFFERED: '1' };
  if (app.isPackaged) {
    env.MCE_DATA_DIR = dataDir();
  }
  return env;
}

// 数据目录：统一放在 exe 所在目录（绿色版/安装版都跟随安装位置，不占 C 盘）。
// 注：安装到 Program Files 等受保护目录时需管理员权限才能写入；建议自定义安装到可写目录。
function dataDir() {
  return path.dirname(app.getPath('exe'));
}

/* ── 窗口状态持久化（大小 / 位置 / 最大化） ────────── */
// 与 Python settings.py 共用 data/settings.json；save_settings 只更新传入字段、保留其余，故 window 字段互不冲突
function settingsFilePath() {
  const dataRoot = app.isPackaged ? dataDir() : path.join(__dirname, '..');
  return path.join(dataRoot, 'data', 'settings.json');
}

function readWindowState() {
  try {
    const s = JSON.parse(fs.readFileSync(settingsFilePath(), 'utf8'));
    const w = s && s.window;
    if (w && typeof w === 'object') {
      return {
        width: Math.max(960, Number(w.width) || 1280),
        height: Math.max(640, Number(w.height) || 860),
        maximized: !!w.maximized,
      };
    }
  } catch {}
  return null;
}

// 仅持久化大小与最大化状态；不保存位置（每次启动居中，避免显示器/分辨率变化导致窗口跑到屏幕外）
function saveWindowState() {
  try {
    if (!win || win.isDestroyed()) return;
    const b = win.getNormalBounds();   // 最大化/最小化时也返回正常状态的位置与大小
    const state = {
      width: Math.round(b.width),
      height: Math.round(b.height),
      maximized: win.isMaximized(),
    };
    const file = settingsFilePath();
    let data = {};
    try { data = JSON.parse(fs.readFileSync(file, 'utf8')); } catch {}
    if (typeof data !== 'object' || data === null) data = {};
    data.window = state;
    fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
  } catch {}
}

function startPython() {
  const { cmd, args } = pyCommand();
  console.log('[main] start backend:', cmd, args.join(' '));
  py = spawn(cmd, args, {
    stdio: ['pipe', 'pipe', 'pipe'],
    windowsHide: true,
    env: backendEnv(),
  });

  const rl = readline.createInterface({ input: py.stdout, crlfDelay: Infinity });
  rl.on('line', (line) => {
    const s = line.trim();
    if (!s) return;
    let msg;
    try {
      msg = JSON.parse(s);
    } catch {
      return;
    }
    if (msg.id != null && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.reject(new Error(msg.error));
      else p.resolve(msg.result);
    } else if (msg.event && win && !win.isDestroyed()) {
      win.webContents.send('py-event', msg);
    }
  });

  // stderr 按行缓冲输出（data 事件按块触发，可能包含多行；逐行打印避免合并/前缀错乱）
  let pyErrBuf = '';
  py.stderr.on('data', (d) => {
    pyErrBuf += d.toString('utf8');
    let idx;
    while ((idx = pyErrBuf.indexOf('\n')) >= 0) {
      const line = pyErrBuf.slice(0, idx).replace(/\r$/, '');
      pyErrBuf = pyErrBuf.slice(idx + 1);
      if (!line.trim()) continue;
      // 错误/警告红色高亮，普通日志正常显示（日志走 stderr 以避开 JSON 协议流）
      if (/\[(ERROR|WARNING)\]/.test(line)) console.error('[py]', line);
      else console.log('[py]', line);
      pushLog(line);   // 同步到日志控制台窗口
    }
  });
  py.on('exit', (code) => {
    console.error('[py] backend exited', code);
    py = null;
    // 拒绝所有挂起请求
    for (const [, p] of pending) p.reject(new Error('backend exited'));
    pending.clear();
  });
}

function callApi(method, args = []) {
  return new Promise((resolve, reject) => {
    if (!py || !py.stdin.writable) {
      reject(new Error('backend not running'));
      return;
    }
    const id = ++seq;
    pending.set(id, { resolve, reject });
    py.stdin.write(JSON.stringify({ id, method, args }) + '\n');
  });
}

/* ── 日志控制台（Electron 黑底控制台窗口）──────────── */

const LOG_HTML = 'data:text/html;charset=utf-8,' + encodeURIComponent(
  '<!DOCTYPE html><html><head><meta charset="utf-8"><style>' +
  'body{margin:0;background:#0c0c0c;color:#ccc;font:12px/1.55 Consolas,\'Courier New\',monospace;padding:6px 8px;white-space:pre-wrap;word-break:break-all}' +
  '::-webkit-scrollbar{width:8px}::-webkit-scrollbar-thumb{background:#333;border-radius:4px}' +
  '</style></head><body id="log"></body></html>'
);

// 推送日志到控制台（剥离 ANSI 颜色码，避免转义序列乱码；终端仍保留颜色高亮）
function pushLog(line) {
  const plain = String(line).replace(/\u001b\[[0-9;]*m/g, '');
  logBuffer.push(plain);
  if (logBuffer.length > 800) logBuffer.shift();
  if (logWin && !logWin.isDestroyed()) {
    logWin.webContents.send('log-line', plain);
  }
}

// 打开/聚焦日志控制台（标题栏按钮 / 快捷键 Ctrl+Shift+L 随时可开，关闭后随时重开）
function openLogConsole() {
  if (logWin && !logWin.isDestroyed()) {
    logWin.show();
    logWin.focus();
    return;
  }
  logWin = new BrowserWindow({
    width: 780,
    height: 520,
    title: 'MCE - Log Console',
    backgroundColor: '#0c0c0c',
    autoHideMenuBar: true,   // 隐藏菜单栏（File/Edit/View/Window/Help）
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: false,
      nodeIntegration: false,
      sandbox: false,
    },
  });
  logWin.loadURL(LOG_HTML);
  logWin.webContents.on('did-finish-load', () => {
    // 控制台首行显示 MCE 字符画，随后回放历史日志
    logWin.webContents.send('log-line', MCE_BANNER);
    logBuffer.forEach((l) => logWin.webContents.send('log-line', l));
  });
  logWin.on('closed', () => { logWin = null; });
}

function scaleFactor() {
  try {
    return screen.getDisplayMatching(win.getBounds()).scaleFactor || 1;
  } catch {
    return 1;
  }
}

function createWindow() {
  const ws = readWindowState();
  const opts = {
    width: 1280,
    height: 860,
    minWidth: 960,
    minHeight: 640,
    frame: false, // 无边框：标题栏由 webui 自绘（-webkit-app-region: drag）
    backgroundColor: '#0f1115',
    icon: path.join(__dirname, '..', 'webui', 'assets', 'icon.ico'),
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: false,
      nodeIntegration: false,
      sandbox: false,
    },
  };
  // 恢复上次窗口大小；不恢复位置（不指定 x/y → 由系统居中到主屏幕，避免跑到屏幕外）
  if (ws) {
    opts.width = ws.width;
    opts.height = ws.height;
  }
  win = new BrowserWindow(opts);
  if (ws && ws.maximized) win.maximize();
  win.loadFile(webuiIndexHtml(), launchQueryOptions());
  win.once('ready-to-show', () => win.show());
  win.on('close', () => saveWindowState());   // 兜底：任何关闭路径都保存一次（幂等）
  win.on('closed', () => {
    win = null;
  });
}

// 前端入口：打包后 webui 作为 extraResources 在 resources/webui；开发模式在项目根 webui/
function webuiIndexHtml() {
  const webuiDir = app.isPackaged
    ? path.join(process.resourcesPath, 'webui')
    : path.join(__dirname, '..', 'webui');
  return path.join(webuiDir, 'index.html');
}

// 启动前注入已保存的设置（主题/主题色/语言），避免启动后闪变/文本跳动；splash 与首帧即正确
function launchQueryOptions() {
  try {
    const dataRoot = app.isPackaged ? dataDir() : path.join(__dirname, '..');
    const s = JSON.parse(fs.readFileSync(path.join(dataRoot, 'data', 'settings.json'), 'utf8'));
    const q = {};
    if (s.theme) q.theme = s.theme;
    if (s.accent) q.accent = s.accent;
    if (s.lang) q.lang = s.lang;
    return { query: q };
  } catch {
    return {};
  }
}

/* ── IPC：前端 → Python / 主进程 ─────────────────── */

ipcMain.handle('api', (_e, { method, args }) => callApi(method, args || []));

ipcMain.handle('win:minimize', () => {
  win.minimize();
  return { ok: true };
});

ipcMain.handle('win:maximize', () => {
  if (win.isMaximized()) win.unmaximize();
  else win.maximize();
  return { ok: true, maximized: win.isMaximized() };
});

ipcMain.handle('win:isMaximized', () => ({ ok: true, maximized: win.isMaximized() }));

ipcMain.handle('win:quit', () => {
  app.quit();
});

// 调试模式：打开原生 cmd 日志控制台（不依赖调试模式，标题栏按钮/快捷键 Ctrl+Shift+L 随时可开）
ipcMain.handle('win:openLogConsole', () => {
  openLogConsole();
  return { ok: true };
});

// 全局快捷键：Ctrl+Shift+L 打开日志控制台
app.on('browser-window-created', (_e, w) => {
  w.webContents.on('before-input-event', (event, input) => {
    if (input.type === 'keyDown' && input.control && input.shift && input.key.toLowerCase() === 'l') {
      openLogConsole();
    }
  });
});

// 增量移动窗口（前端 screen 坐标为物理像素，需 ÷scaleFactor 转 DIP）
ipcMain.handle('win:move', (_e, dx, dy) => {
  const sf = scaleFactor();
  const b = win.getBounds();
  win.setBounds({
    x: Math.round(b.x + dx / sf),
    y: Math.round(b.y + dy / sf),
    width: b.width,
    height: b.height,
  });
  return { ok: true };
});

// 边缘/角落缩放（direction: l/r/t/b 组合，固定对边）
ipcMain.handle('win:resize', (_e, dir, dx, dy) => {
  const sf = scaleFactor();
  const b = win.getBounds();
  let { x, y, width, height } = b;
  const rx = dx / sf;
  const ry = dy / sf;
  if (dir.includes('l')) {
    x += rx;
    width -= rx;
  }
  if (dir.includes('r')) width += rx;
  if (dir.includes('t')) {
    y += ry;
    height -= ry;
  }
  if (dir.includes('b')) height += ry;
  const MIN_W = 960;
  const MIN_H = 640;
  if (width < MIN_W) {
    if (dir.includes('l')) x -= MIN_W - width;
    width = MIN_W;
  }
  if (height < MIN_H) {
    if (dir.includes('t')) y -= MIN_H - height;
    height = MIN_H;
  }
  win.setBounds({ x: Math.round(x), y: Math.round(y), width: Math.round(width), height: Math.round(height) });
  return { ok: true };
});

// 文件夹选择对话框
ipcMain.handle('dialog:folder', async () => {
  const r = await dialog.showOpenDialog(win, { properties: ['openDirectory'] });
  return r.canceled ? null : r.filePaths[0];
});

ipcMain.handle('dialog:folderOutput', async () => {
  const r = await dialog.showOpenDialog(win, { properties: ['openDirectory'] });
  return r.canceled ? null : r.filePaths[0];
});

/* ── 任务栏（Windows 原生：进度显示 + 完成后黄色闪烁）────────── */

// 读条期间在任务栏图标显示进度（0~1；Windows 任务栏绿色进度条）
ipcMain.handle('taskbar:progress', (_e, value) => {
  if (!win || win.isDestroyed()) return { ok: false };
  const v = Number(value);
  if (!isFinite(v)) return { ok: false };
  win.setProgressBar(Math.max(0, Math.min(1, v)));
  return { ok: true };
});

// 读条完成后：任务栏图标黄色闪烁（FlashWindowEx，直到窗口被聚焦）+ 移除任务栏进度
ipcMain.handle('taskbar:flash', () => {
  if (!win || win.isDestroyed()) return { ok: false };
  win.flashFrame(true);
  win.setProgressBar(-1);
  return { ok: true };
});

/* ── 生命周期 ────────────────────────────────────── */

let backendStopping = false;

function stopBackend() {
  if (!py) return;
  // 关闭 stdin → backend 主循环收到 EOF → 自行输出退出日志并清理退出
  try {
    py.stdin.end();
  } catch {}
  // 兜底：8s 后仍存活则强杀（正常情况 backend 收到 EOF 会自动退出）
  const timer = setTimeout(() => {
    try {
      py.kill();
    } catch {}
  }, 8000);
  py.once('exit', () => clearTimeout(timer));
}

function stopBackendAndQuit() {
  if (backendStopping) return;
  backendStopping = true;
  if (!py) {
    app.quit();
    return;
  }
  stopBackend();
  // 窗口已关闭；主进程保持存活等待后端清理（收集完整退出日志），限时 4s
  const timer = setTimeout(() => {
    try {
      py.kill();
    } catch {}
    app.quit();
  }, 4000);
  py.once('exit', () => {
    clearTimeout(timer);
    app.quit();
  });
}

app.whenReady().then(() => {
  // 移除默认应用菜单（日志控制台等窗口不显示 File/Edit/View/Window/Help 菜单栏）
  Menu.setApplicationMenu(null);
  startPython();
  createWindow();
});

// 退出前：立即销毁窗口（用户看到窗口消失），再等后端清理完成后真正退出
app.on('before-quit', (e) => {
  if (backendStopping) return; // 二次 app.quit() 直接放行
  e.preventDefault();
  saveWindowState();   // 持久化窗口大小/位置/最大化（必须在 destroy 前；destroy 不触发 close）
  if (win && !win.isDestroyed()) win.destroy();
  stopBackendAndQuit();
});

app.on('window-all-closed', () => {
  stopBackendAndQuit();
});
