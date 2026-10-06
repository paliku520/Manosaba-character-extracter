/* ============================================================
 * about.js — 关于页（作者 / 链接 / 系统信息）+ 背景轮播 + 彩蛋
 *
 * 依赖：core.js（必须已加载）。
 * 由原 webui/js/app.js 拆分而来（行为、HTML 结构、API 名保持不变）。
 * 注意：系统的 _loadSysInfo 导出名为 loadSysInfo（core.js 启动时调用）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, escapeHtml, App } = MCE;

  // ═════════════ 关于页 ═════════════

  const _aboutIcons = {
    scissors: '<svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M8.2 8.2 20 20M8.2 15.8 20 4"/></svg>',
    tag: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.6 13.4 13.4 20.6a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r=".5"/></svg>',
    download: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3"/></svg>',
    refresh: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6"/></svg>',
    user: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
    users: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/></svg>',
    play: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"/></svg>',
    branch: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>',
    code: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>',
    repo: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M3 12h18M3 18h18"/><circle cx="8" cy="6" r="1"/><circle cx="16" cy="12" r="1"/><circle cx="8" cy="18" r="1"/></svg>',
    bug: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"/></svg>',
    heart: '<svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8l1 1.1L12 21l7.8-7.5 1-1.1a5.5 5.5 0 0 0 0-7.8Z"/></svg>',
    external: '<svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14 21 3"/></svg>',
  };
  const _aI = (k) => _aboutIcons[k] || '';

  // 贡献者卡片数据（名称与链接为固定的专有名词，角色说明走 i18n）
  const _contributors = [
    {
      initial: 'R',
      name: 'Rainfrost2907',
      roleKey: 'about.contrib_role_contributor',
      descKey: 'about.contrib_rf_desc',
      url: 'https://github.com/Rainfrost2907',
      brand: 'gh',
    },
    {
      initial: 'L',
      name: 'lingk7',
      roleKey: 'about.contrib_role_original',
      descKey: 'about.contrib_lk_desc',
      url: 'https://github.com/lingk7',
      brand: 'gh',
    },
  ];

  function _renderContributors() {
    return _contributors.map((c) =>
      '<div class="about-contrib">' +
      '  <div class="about-contrib-avatar" aria-hidden="true">' + escapeHtml(c.initial) + '</div>' +
      '  <div class="about-contrib-info">' +
      '    <span class="about-contrib-name">' + escapeHtml(c.name) + '</span>' +
      '    <span class="about-contrib-role">' + escapeHtml(t(c.roleKey)) + '</span>' +
      '    <span class="about-contrib-desc">' + escapeHtml(t(c.descKey)) + '</span>' +
      '  </div>' +
      '  <button type="button" class="about-open ' + c.brand + '" data-url="' + c.url + '" data-tip="' + escapeHtml(t('about.dev_click')) + '">' + _aI('external') + t('about.open_btn') + '</button>' +
      '</div>'
    ).join('');
  }

  function renderAboutPage() {
    const el = $('#about-content');
    if (!el) return;
    const ver = App.info && App.info.version ? 'v' + App.info.version : '';
    el.innerHTML =
      '<div class="about-hero">' +
      '<div class="about-icon"><img src="assets/logo.ico" alt="logo"></div>' +
      '<h2>' + t('about.app_name') + '</h2>' +
      '<p class="about-version-line">' +
      '  <span class="about-ver">' + _aI('tag') + t('about.version_label', { version: ver }) + '</span>' +
      '</p>' +
      '<div class="about-export-badge">' +
      '  <span class="about-export-icon">' + _aI('download') + '</span>' +
      '  <div class="about-export-body">' +
      '    <span class="about-export-label">' + t('about.export_count') + '</span>' +
      '    <span class="about-export-num" id="about-export-count">' + App.exportCount + '</span>' +
      '  </div>' +
      '</div>' +
      '<button id="btn-about-update" class="btn sm ghost">' + _aI('refresh') + t('about.update_btn') + '</button>' +
      '</div>' +
      '<p class="about-desc">' + t('about.description') + '</p>' +
      '<div class="about-grid">' +
      '<div class="about-section">' +
      '  <h3>' + _aI('user') + t('about.dev_title') + '</h3>' +
      '  <div class="about-row">' + t('about.dev_name') + '</div>' +
      '  <div class="about-link">' + _aI('play') + '<span class="about-link-label">' + t('about.dev_bilibili') + ': ' + t('about.dev_click') + ' →</span><button type="button" class="about-open bili" data-url="https://space.bilibili.com/511874938" data-tip="' + escapeHtml(t('about.dev_click')) + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '  <div class="about-link">' + _aI('branch') + '<span class="about-link-label">' + t('about.dev_github') + ': ' + t('about.dev_click') + ' →</span><button type="button" class="about-open gh" data-url="https://github.com/paliku520" data-tip="' + escapeHtml(t('about.dev_click')) + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '</div>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('code') + t('about.links_title') + '</h3>' +
      '  <div class="about-link">' + _aI('repo') + '<span class="about-link-label">' + t('about.links_repo') + '</span><button type="button" class="about-open" data-url="https://github.com/paliku520/Manosaba-character-extracter" data-tip="' + escapeHtml(t('about.dev_click')) + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '  <div class="about-link">' + _aI('bug') + '<span class="about-link-label">' + t('about.links_issues') + '</span><button type="button" class="about-open" data-url="https://github.com/paliku520/Manosaba-character-extracter/issues" data-tip="' + escapeHtml(t('about.dev_click')) + '">' + _aI('external') + t('about.open_btn') + '</button></div>' +
      '</div>' +
      '<div class="about-section wide">' +
      '  <h3>' + _aI('users') + t('about.contrib_title') + '</h3>' +
      '  <div class="about-contrib-grid">' + _renderContributors() + '</div>' +
      '</div>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('code') + t('about.sys_title') + '</h3>' +
      '  <div class="about-sys" id="about-sys">' + t('about.sys_loading') + '</div>' +
      '</div>' +
      '<div class="about-section">' +
      '  <h3>' + _aI('heart') + t('about.thanks_title') + '</h3>' +
      '  <p class="about-thanks" id="about-thanks-easter">' + t('about.thanks_text') + '</p>' +
      '</div>' +
      '</div>' +
      '<p class="about-copy">' + t('about.copyright') + '</p>' +
      '<p class="about-note">' + t('about.license_note') + '</p>' +
      '<p class="about-disclaimer">' + t('app.disclaimer') + '</p>';

    // 彩蛋入口：点击致谢文本触发
    const easterEl = el.querySelector('#about-thanks-easter');
    if (easterEl) easterEl.addEventListener('click', showEasterEgg);
    // 彩蛋入口：点击 logo 播放 kiang 音频
    const logoBox = el.querySelector('.about-icon');
    if (logoBox) logoBox.addEventListener('click', playKiangSound);
    // 系统信息（CPU/内存/GPU/显存/OS）
    _renderSysInfo();
  }

  // ═════════════ 系统信息（每次启动检查 CPU/GPU/内存配置）══════════════
  function _renderSysInfo() {
    const el = $('#about-sys');
    if (!el) return;
    const s = App.sysInfo;
    if (!s) { el.textContent = t('about.sys_loading'); return; }
    const rows = [];
    rows.push(t('about.sys_cpu', { model: s.cpuModel, cores: s.cpuCores, speed: s.cpuSpeedGHz }));
    rows.push(t('about.sys_mem', { mem: s.totalMemGB }));
    if (s.gpuName && !/unknown/i.test(s.gpuName)) {
      rows.push(s.gpuVramGB
        ? t('about.sys_gpu', { name: s.gpuName, vram: s.gpuVramGB })
        : t('about.sys_gpu_name', { name: s.gpuName }));
    }
    rows.push(t('about.sys_os', { os: s.osType + ' ' + s.osRelease, arch: s.osArch }));
    el.innerHTML = rows.map((x) => '<div class="about-sys-row">' + x + '</div>').join('');
  }

  function _loadSysInfo() {
    if (!window.__electron || !window.__electron.sysInfo) return;
    window.__electron.sysInfo().then((s) => {
      if (!s) return;
      App.sysInfo = s;
      // 若关于页已渲染则刷新
      if ($('#about-sys')) _renderSysInfo();
      // 输出到日志控制台（经 console 钩子转发为 [JS] 来源）；GPU 仅显示可识别的型号
      try {
        const lines = [
          t('about.sys_cpu', { model: s.cpuModel, cores: s.cpuCores, speed: s.cpuSpeedGHz }),
          t('about.sys_mem', { mem: s.totalMemGB }),
        ];
        if (s.gpuName && !/unknown/i.test(s.gpuName)) {
          lines.push(s.gpuVramGB
            ? t('about.sys_gpu', { name: s.gpuName, vram: s.gpuVramGB })
            : t('about.sys_gpu_name', { name: s.gpuName }));
        }
        lines.push(t('about.sys_os', { os: s.osType + ' ' + s.osRelease, arch: s.osArch }));
        console.log(t('log.sysinfo') + '\n' + lines.join('\n'));
      } catch (e) { /* ignore */ }
    }).catch(() => {});
  }

  // 彩蛋：点击关于页 logo 播放 kiang 目录音频（每次点击从头重播）
  let _kiangAudio = null;
  function playKiangSound() {
    if (!_kiangAudio) {
      _kiangAudio = new Audio('assets/EasterEgg/kiang/0201Trial08_Ema022.wav');
      _kiangAudio.volume = 0.8;
    }
    _kiangAudio.currentTime = 0;
    _kiangAudio.play().catch(() => {});
  }

  // ═════════════ 彩蛋（执行按钮：心跳 → 长按填充 → 完成音效/对勾 → 过渡关闭） ═════════════
  const EASTER_FILL_RATE = 100 / 9;  // 长按时填充速度（%/秒，约 9 秒填满，贴近 001 音效时长）
  const EASTER_DRAIN_RATE = 35;      // 松开时进度倒退速度（%/秒）

  function showEasterEgg() {
    // 移除旧覆盖层（重复点击时重建）
    const old = $('#easter-overlay');
    if (old) old.remove();
    const overlay = document.createElement('div');
    overlay.className = 'easter-overlay';
    overlay.id = 'easter-overlay';
    // 第一步：背景图（随机一张）立即显示
    const bgIdx = 1 + Math.floor(Math.random() * 7);
    overlay.style.backgroundImage =
      'url("assets/EasterEgg/execution/bg/' + String(bgIdx).padStart(2, '0') + '.webp")';
    document.body.appendChild(overlay);

    // 第二步：等待 1 秒后再加载叠加层与 phone，两者同步纯淡入（不缩放）
    setTimeout(() => {
      const scrim = document.createElement('div');
      scrim.className = 'easter-scrim';
      overlay.appendChild(scrim);

      const phone = document.createElement('div');
      phone.className = 'easter-phone';
      phone.innerHTML =
        '  <button type="button" class="exec-btn" id="exec-btn" aria-label="execution">' +
        '    <img class="exec-layer exec-base" src="assets/EasterEgg/execution/ExecutionButton_Base.png" alt="">' +
        '    <div class="exec-fill"></div>' +
        '    <img class="exec-layer exec-frame" src="assets/EasterEgg/execution/ExecutionButton_Frame.png" alt="">' +
        '    <img class="exec-label" src="assets/EasterEgg/execution/ExecutionButton_Label.png" alt="">' +
        '    <img class="exec-check" src="assets/EasterEgg/execution/ExecutionButton_CheckIcon.png" alt="">' +
        '  </button>';
      overlay.appendChild(phone);

      const eb = phone.querySelector('#exec-btn');
      const fill = phone.querySelector('.exec-fill');
      const check = phone.querySelector('.exec-check');

      // 三个音效：心跳（进入即播，循环）/ 长按（按住循环）/ 完成（一次）
      const sHeart = new Audio('assets/EasterEgg/execution/Sfx_Scenario_035 Human heartbeat.wav');
      const sHold = new Audio('assets/EasterEgg/execution/Sfx_System_ExecuteButton_001.wav');
      const sDone = new Audio('assets/EasterEgg/execution/Sfx_System_ExecuteButton_002.wav');
      sHeart.loop = false; sHeart.volume = .55;  // 心跳只播一次
      sHold.loop = true; sHold.volume = .6;
      sDone.volume = .9;

      let progress = 0, holding = false, completed = false, raf = null, lastTs = 0;

      function tick(ts) {
        if (!lastTs) lastTs = ts;
        const dt = Math.min((ts - lastTs) / 1000, .1);
        lastTs = ts;
        if (holding) {
          progress = Math.min(100, progress + EASTER_FILL_RATE * dt);
          if (progress >= 100) { complete(); return; }
        } else {
          // 未按住 → 进度倒退
          progress = Math.max(0, progress - EASTER_DRAIN_RATE * dt);
        }
        fill.style.height = progress + '%';
        raf = requestAnimationFrame(tick);
      }
      function startHold(e) {
        if (completed) return;
        e.preventDefault();
        holding = true; lastTs = 0;
        if (!raf) raf = requestAnimationFrame(tick);
        sHold.currentTime = 0;
        sHold.play().catch(() => {});
      }
      function stopHold() {
        holding = false;
        sHold.pause(); sHold.currentTime = 0;
      }
      function complete() {
        completed = true; holding = false;
        if (raf) { cancelAnimationFrame(raf); raf = null; }
        eb.disabled = true;   // 禁止再次长按
        // 强制立即恢复未长按大小（覆盖仍可能生效的 :active 缩放）
        eb.style.transition = 'none';
        eb.style.transform = 'rotate(0deg)';
        sHold.pause(); sHold.currentTime = 0;
        sHeart.pause(); sHeart.currentTime = 0;
        fill.style.height = '100%';
        sDone.currentTime = 0;
        sDone.play().catch(() => {});
        check.classList.add('show');
        // 过渡关闭界面（填满后 1.5 秒才开始淡出）；淡出开始时随机播放一段结束音频（End_1~5）
        setTimeout(() => {
          const endIdx = 1 + Math.floor(Math.random() * 5);
          const sEnd = new Audio('assets/EasterEgg/execution/End_' + endIdx + '.wav');
          sEnd.volume = .9;
          sEnd.play().catch(() => {});
          overlay.classList.add('closing');
          setTimeout(() => overlay.remove(), 500);
        }, 1500);
      }

      // 叠加层与 phone 同步淡入（双 rAF 确保过渡生效），同时播放心跳
      requestAnimationFrame(() => requestAnimationFrame(() => {
        scrim.classList.add('show');
        phone.classList.add('show');
        sHeart.play().catch(() => {});
      }));

      eb.addEventListener('pointerdown', startHold);
      // 还原游戏内 bug：按住不松开时，即使光标移出按钮，长按进度也不断
      // （不监听 pointerleave 打断；pointercancel 仍处理系统手势/触控取消）
      eb.addEventListener('pointercancel', stopHold);
      window.addEventListener('pointerup', stopHold);
    }, 1000);
    // 进入彩蛋后不能直接退出：仅完成执行后过渡关闭（不提供点击遮罩关闭）
  }

  // 关于页背景轮播（参考站 images/bg/01~45.webp，随机起始、定时切换）
  const ABOUT_BG_COUNT = 45;
  function aboutBgUrl(i) {
    return 'assets/bg/' + String(i + 1).padStart(2, '0') + '.webp';
  }
  function initAboutBg() {
    const layer = $('#about-bg-layer');
    if (!layer) return;
    let idx = Math.floor(Math.random() * ABOUT_BG_COUNT);
    layer.style.backgroundImage = 'url("' + aboutBgUrl(idx) + '")';
    setInterval(() => {
      idx = (idx + 1) % ABOUT_BG_COUNT;
      layer.style.opacity = 0;
      setTimeout(() => {
        layer.style.backgroundImage = 'url("' + aboutBgUrl(idx) + '")';
        layer.style.opacity = 1;
      }, 500);
    }, 8000);
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.renderAboutPage = renderAboutPage;
  MCE.renderSysInfo = _renderSysInfo;
  MCE.loadSysInfo = _loadSysInfo;
  MCE.playKiangSound = playKiangSound;
  MCE.showEasterEgg = showEasterEgg;
  MCE.initAboutBg = initAboutBg;
})();
