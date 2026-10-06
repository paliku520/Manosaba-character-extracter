/* ============================================================
 * info.js — 首页（欢迎 / 使用指南 / 提示）
 *
 * 依赖：core.js（必须已加载）。
 * 由原 webui/js/app.js 拆分而来（行为、HTML 结构、API 名保持不变）。
 * ============================================================ */
(function () {
  'use strict';

  window.MCE = window.MCE || {};
  const MCE = window.MCE;
  const { $, t, App } = MCE;

  // ═════════════ 信息页 ═════════════

  // 信息板块：始终显示欢迎/指南（加载角色后不改变）
  function renderInfoPage() {
    const el = $('#info-content');
    const ver = App.info && App.info.version ? App.info.version : '';
    el.innerHTML =
      '<div class="info-hero">' +
      '<div class="hero-icon">' +
      '  <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '    <circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/>' +
      '    <path d="M8.2 8.2 20 20M8.2 15.8 20 4"/>' +
      '  </svg>' +
      '</div>' +
      '<h2>' + t('info.welcome_title', { version: ver }) + '</h2>' +
      '<p class="lead">' + t('info.welcome_lead') + '</p>' +
      // 使用教程入口：随时重看首次使用引导（见 tour.js）
      '<div class="info-hero-actions">' +
      '  <button type="button" id="btn-info-tour" class="btn primary">' +
      '    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
      '      <circle cx="12" cy="12" r="9"/><path d="M9.5 9.3a2.6 2.6 0 1 1 3.6 2.4c-.7.3-1.1.9-1.1 1.6v.3"/><path d="M12 17h.01"/>' +
      '    </svg>' +
      '    <span data-i18n="tour.open">' + t('tour.open') + '</span>' +
      '  </button>' +
      '</div>' +
      '<div class="guide-card">' +
      '  <h3>' + t('info.guide_title') + '</h3>' +
      '  <ol>' +
      '    <li><span class="step">1</span>' + t('info.guide_step1') + '</li>' +
      '    <li><span class="step">2</span>' + t('info.guide_step2') + '</li>' +
      '    <li><span class="step">3</span>' + t('info.guide_step3') + '</li>' +
      '    <li><span class="step">4</span>' + t('info.guide_step4') + '</li>' +
      '    <li><span class="step">5</span>' + t('info.guide_step5') + '</li>' +
      '  </ol>' +
      '</div>' +
      '<div class="guide-card">' +
      '  <h3>' + t('info.tips_title') + '</h3>' +
      '  <ul>' +
      '    <li>' + t('info.tip1') + '</li>' +
      '    <li>' + t('info.tip2') + '</li>' +
      '    <li>' + t('info.tip3') + '</li>' +
      '  </ul>' +
      '</div>' +
      // 名片合成卡片（由 nameplate.js 挂载：独立模块便于维护，语言切换时随本页重建）
      '<div id="np-mount"></div>' +
      '</div>';
    const tourBtn = el.querySelector('#btn-info-tour');
    if (tourBtn) tourBtn.addEventListener('click', () => { if (MCE.openTourPicker) MCE.openTourPicker(); });
    if (MCE.renderNameplateCard) MCE.renderNameplateCard();
  }

  // ── 导出 ────────────────────────────────────────────────
  MCE.renderInfoPage = renderInfoPage;
})();
