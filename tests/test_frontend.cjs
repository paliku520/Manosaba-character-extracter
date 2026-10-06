// Run with: node --test tests/test_frontend.cjs (no Electron process or game required).
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');
const { test } = require('node:test');
const { EventEmitter } = require('node:events');
const { PassThrough } = require('node:stream');
const repo = path.resolve(__dirname, '..');

function browser() {
  const elements = new Map(), listeners = new Map();
  function element() {
    return {
      hidden: true, disabled: false, style: {}, children: [], parent: null,
      classList: { add() {}, remove() {}, toggle() {} },
      addEventListener(type, fn) { (this.listeners ||= {})[type] = fn; },
      setAttribute() {}, querySelectorAll() { return []; },
      appendChild(child) { this.children.push(child); child.parent = this; },
      remove() { if (this.parent) this.parent.children.splice(this.parent.children.indexOf(this), 1); },
      get lastElementChild() { return this.children.at(-1); },
    };
  }
  function el(selector) {
    if (!elements.has(selector)) elements.set(selector, element());
    return elements.get(selector);
  }
  const window = { MCE: { $: el, $$: () => [], t: s => s, api: () => null,
    escapeHtml: s => s, App: { loading: false } }, addEventListener() {}, removeEventListener() {} };
  const document = {
    createElement: element,
    addEventListener(type, fn) { if (!listeners.has(type)) listeners.set(type, new Set()); listeners.get(type).add(fn); },
    removeEventListener(type, fn) { listeners.get(type)?.delete(fn); },
    dispatchEvent(event) { for (const fn of [...(listeners.get(event.type) || [])]) fn(event); },
  };
  const context = vm.createContext({ window, document, requestAnimationFrame() {},
    performance: { now: () => 0 }, console, setTimeout, clearTimeout });
  for (const file of ['ui.js', 'events.js']) {
    vm.runInContext(fs.readFileSync(path.join(repo, 'webui/js', file), 'utf8'), context, { filename: file });
  }
  return { window, document, context, el };
}

test('silent update results preserve another task progress, cancel button and status', () => {
  for (const status of ['latest', 'error']) {
    const { window, el } = browser();
    window.MCE.showProgress({ phase: 'load', current: 1, total: 10 });
    window.MCE.setStatus('Loading assets', true);
    window.__pywebview.events.update_result({ status, silent: true });
    assert.equal(window.MCE.App.loading, true);
    assert.equal(el('#btn-cancel-load').hidden, false);
    assert.equal(el('#progress-wrap').hidden, false);
    assert.equal(window.MCE.App.lastStatus, 'Loading assets');
  }
});

test('all confirmation close paths settle exactly once with the correct result', async () => {
  for (const action of ['escape', 'close', 'cancel', 'confirm']) {
    const { window, document, el } = browser();
    let calls = 0;
    const result = window.MCE.confirmDialog('Title', 'Question').then(value => { calls++; return value; });
    const backdrop = el('#modal-root').lastElementChild;
    const modal = backdrop.children[0];
    if (action === 'escape') document.dispatchEvent({ type: 'keydown', key: 'Escape' });
    else if (action === 'close') modal.children[0].children[1].listeners.click();
    else modal.children[2].children[0].children[action === 'confirm' ? 1 : 0].listeners.click();
    assert.equal(await result, action === 'confirm');
    document.dispatchEvent({ type: 'keydown', key: 'Escape' });
    assert.equal(calls, 1);
    assert.equal(el('#modal-root').children.length, 0);
  }
});

test('nested Escape closes only the top confirmation', async () => {
  const { window, document, el } = browser();
  let outerDone = false;
  const outer = window.MCE.confirmDialog('Outer', 'Question').then(value => { outerDone = true; return value; });
  const inner = window.MCE.confirmDialog('Inner', 'Question');
  document.dispatchEvent({ type: 'keydown', key: 'Escape' });
  assert.equal(await inner, false);
  assert.equal(outerDone, false);
  assert.equal(el('#modal-root').children.length, 1);
  document.dispatchEvent({ type: 'keydown', key: 'Escape' });
  assert.equal(await outer, false);
});

function main(directory, packaged = false) {
  const child = new EventEmitter();
  child.stdin = new PassThrough(); child.stdout = new PassThrough(); child.stderr = new PassThrough();
  child.kill = () => child.emit('exit', 0);
  const errors = [], requests = [], lifecycle = new Map();
  const app = { isPackaged: packaged, setAppUserModelId() {}, commandLine: { appendSwitch() {} },
    disableHardwareAcceleration() {}, on(name, fn) { lifecycle.set(name, fn); },
    whenReady() { return { then() {} }; }, getPath() { return directory; }, quit() { app.quitCalled = true; } };
  const processStub = { env: { MCE_DATA_DIR: directory, MCE_PYTHON: process.execPath },
    platform: process.platform, resourcesPath: directory };
  const electron = { app, BrowserWindow: class {}, ipcMain: { handle() {} },
    dialog: { showErrorBox(title, message) { errors.push({ title, message }); } }, screen: {}, Menu: {} };
  const context = vm.createContext({ require(name) {
    if (name === 'electron') return electron;
    if (name === 'child_process') return { spawn: () => child, spawnSync: () => ({ status: 0 }) };
    return require(name);
  }, __dirname: path.join(repo, 'electron'), process: processStub,
  console: { log() {}, error() {} }, setTimeout, clearTimeout });
  const source = fs.readFileSync(path.join(repo, 'electron/main.js'), 'utf8');
  vm.runInContext(source + `\nglobalThis.testApi = { startPython, callApi, backendEnv, settingsFilePath,
    saveLastDirectory, saveWindowState, stopBackendAndQuit,
    setWindow(value) { win = value; } };`, context);
  child.stdin.on('data', buffer => requests.push(JSON.parse(buffer.toString())));
  const cleanup = () => { child.stdin.end(); child.stdout.end(); child.stderr.end(); };
  return { api: context.testApi, child, app, requests, errors, cleanup };
}

test('custom data directory is shared by Electron and backend in both modes', () => {
  const directory = path.join(os.tmpdir(), 'mce-custom-directory');
  for (const packaged of [false, true]) {
    const fixture = main(directory, packaged);
    assert.equal(fixture.api.settingsFilePath(), path.join(directory, 'data/settings.json'));
    assert.equal(fixture.api.backendEnv().MCE_DATA_DIR, path.resolve(directory));
    fixture.cleanup();
  }
});

test('spawn failure rejects pending and future RPC without unhandled events', async () => {
  const fixture = main(path.join(os.tmpdir(), 'mce-spawn-failure'));
  fixture.api.startPython();
  const pending = fixture.api.callApi('get_app_info');
  const rejected = assert.rejects(pending, /ENOENT/);
  assert.doesNotThrow(() => fixture.child.emit('error', new Error('spawn backend ENOENT')));
  await rejected;
  await assert.rejects(fixture.api.callApi('get_app_info'), /ENOENT/);
  assert.equal(fixture.errors.length, 1);
  fixture.cleanup();
});

test('broken backend stdin rejects requests without unhandled stream error', async () => {
  const fixture = main(path.join(os.tmpdir(), 'mce-broken-pipe'));
  fixture.api.startPython();
  const pending = fixture.api.callApi('get_app_info');
  const rejected = assert.rejects(pending, /EPIPE/);
  fixture.child.stdin.emit('error', new Error('EPIPE'));
  await rejected;
  await assert.rejects(fixture.api.callApi('get_app_info'), /EPIPE/);
  fixture.cleanup();
});

test('native settings use backend transactions and shutdown waits for window persistence', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'mce-native-settings-'));
  const fixture = main(directory);
  try {
    fixture.api.startPython();
    const saved = fixture.api.saveLastDirectory(directory);
    assert.equal(fixture.requests[0].method, 'save_native_settings');
    assert.deepEqual(fixture.requests[0].args, [null, directory]);
    fixture.child.stdout.write(JSON.stringify({ id: fixture.requests[0].id, result: { ok: true } }) + '\n');
    await saved;
    fixture.api.setWindow({ isDestroyed: () => false, isMaximized: () => true,
      getNormalBounds: () => ({ width: 1234, height: 789 }) });
    const windowSaved = fixture.api.saveWindowState();
    const quitting = fixture.api.stopBackendAndQuit();
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(fixture.child.stdin.writableEnded, false);
    assert.equal(fixture.requests[1].method, 'save_native_settings');
    assert.equal(fixture.requests[1].args[0].width, 1234);
    fixture.child.stdout.write(JSON.stringify({ id: fixture.requests[1].id, result: { ok: true } }) + '\n');
    await windowSaved;
    await quitting;
    assert.equal(fixture.child.stdin.writableEnded, true);
    fixture.child.emit('exit', 0);
    assert.equal(fixture.app.quitCalled, true);
    assert.equal(fs.existsSync(path.join(directory, 'data/settings.json')), false, 'main must not write settings');
  } finally {
    fixture.cleanup();
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
