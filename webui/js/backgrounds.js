/* Background browser. Reuses the application's tabs, dropdowns, buttons and progress animations. */
(function () {
  'use strict';
  const MCE = window.MCE;
  const { $, t, api, App, on } = MCE;
  const state = { bundles: [], selected: new Set(), category: '', busy: false, preview: null };
  let categoryDropdown = null;

  function groupLabel(group) {
    const key = 'background.groups.' + group;
    return key in window.I18N.data ? t(key) : group;
  }

  function visibleBundles() {
    const query = $('#bg-search').value.trim().toLowerCase();
    return state.bundles.filter((item) => (!state.category || item.group === state.category)
      && (!query || item.id.toLowerCase().includes(query)));
  }

  function updateControls() {
    $('#bg-load').disabled = state.busy;
    $('#bg-prewarm').disabled = state.busy || !state.bundles.length;
    $('#bg-export').disabled = state.busy || state.selected.size === 0;
    $('#bg-select-all').disabled = state.busy || !visibleBundles().length;
    $('#bg-select-none').disabled = state.busy || !state.selected.size;
    $('#bg-cancel').hidden = !state.busy;
    $('#bg-cancel').disabled = false;
    if (categoryDropdown) categoryDropdown.el.querySelector('button').disabled = state.busy;
    $('#bg-summary').textContent = t('background.summary', {
      total: state.bundles.length, visible: visibleBundles().length, selected: state.selected.size,
    });
    $('#bg-list').querySelectorAll('input, button').forEach((el) => { el.disabled = state.busy; });
    $('#bg-list').querySelectorAll('.background-row').forEach((el) => {
      el.tabIndex = state.busy ? -1 : 0;
      el.setAttribute('aria-disabled', String(state.busy));
    });
  }

  function renderList() {
    const list = $('#bg-list');
    list.replaceChildren();
    const visible = visibleBundles();
    if (!visible.length) {
      const empty = document.createElement('p');
      empty.className = 'desc background-empty';
      empty.textContent = t(state.bundles.length ? 'background.no_matches' : 'background.empty');
      list.appendChild(empty);
    }
    visible.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'background-row part-item';
      row.setAttribute('role', 'button');
      row.setAttribute('aria-label', t('background.preview') + ': ' + item.id);
      row.dataset.id = item.id;
      const label = document.createElement('label');
      const checkbox = document.createElement('input');
      checkbox.type = 'checkbox';
      checkbox.setAttribute('aria-label', item.id);
      checkbox.checked = state.selected.has(item.id);
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) state.selected.add(item.id);
        else state.selected.delete(item.id);
        updateControls();
      });
      const name = document.createElement('span');
      name.textContent = item.id;
      label.appendChild(checkbox);
      row.append(label, name);
      const preview = () => {
        if (!state.busy) startJob('preview', () => api().preview_background(item.id));
      };
      row.addEventListener('click', (event) => {
        if (!event.target.closest('input, label')) preview();
      });
      row.addEventListener('keydown', (event) => {
        if (event.target === row && (event.key === 'Enter' || event.key === ' ')) {
          event.preventDefault();
          preview();
        }
      });
      list.appendChild(row);
    });
    updateControls();
  }

  function buildCategories() {
    if (categoryDropdown) categoryDropdown.closeList();
    const groups = Array.from(new Set(state.bundles.map((item) => item.group))).sort();
    const options = [{ value: '', label: t('background.all_categories') }]
      .concat(groups.map((group) => ({ value: group, label: groupLabel(group) })));
    categoryDropdown = MCE.createDropdown({ options, value: state.category });
    categoryDropdown.el.querySelector('button').setAttribute('aria-label', t('background.category'));
    categoryDropdown.onChange = (value) => { state.category = value; renderList(); };
    $('#bg-category').replaceChildren(categoryDropdown.el);
  }

  function setBusy(busy) {
    state.busy = busy;
    App.backgroundBusy = busy;
    // Character navigation/loading shares the global status/progress area.
    $('#btn-load').disabled = busy;
    $('#btn-clear-cache').disabled = busy;
    if (busy) MCE.showProgress({ current: 0, total: 1, phase: 'background' });
    else MCE.clearProgress();
    updateControls();
  }

  async function startJob(operation, request) {
    if (state.busy || App.loading) {
      MCE.toast(t('background.busy'), 'warning');
      return;
    }
    setBusy(true);
    MCE.setStatus(t('background.' + operation + '_progress'), true);
    try {
      const result = await request();
      if (!result || !result.ok) throw new Error(result && result.error || t('background.failed'));
    } catch (error) {
      setBusy(false);
      MCE.setStatus(t('background.failed'));
      MCE.toast(String(error.message || error), 'error');
    }
  }

  async function loadBackgrounds() {
    if (state.busy || App.loading) { MCE.toast(t('background.busy'), 'warning'); return; }
    const path = await api().select_directory();
    if (path) await startJob('scan', () => api().load_backgrounds(path));
  }

  function showErrors(errors) {
    if (!errors || !errors.length) return;
    const body = document.createElement('div');
    body.className = 'desc background-errors';
    body.textContent = errors.map((error) => error.id + ': ' + error.message).join('\n');
    const footer = document.createElement('div');
    const ok = MCE.btn(t('dialog.ok'), 'btn sm primary');
    footer.appendChild(ok);
    const modal = MCE.showModal({ title: t('background.errors', { count: errors.length }), body, footer });
    ok.addEventListener('click', modal.close);
  }

  on('background_progress', (p) => {
    if (state.busy) MCE.showProgress({ current: p.current, total: p.total, phase: 'background' });
  });
  on('background_complete', (result) => {
    setBusy(false);
    if (result.cancelled) {
      MCE.setStatus(t('app.status.cancelled'));
      MCE.toast(t('background.cancelled'), 'info');
      return;
    }
    if (result.error) {
      MCE.setStatus(t('background.failed'));
      MCE.toast(result.error, 'error');
      return;
    }
    if (result.operation === 'scan') {
      state.bundles = result.bundles;
      state.selected.clear();
      state.category = state.bundles.some((item) => item.group === 'mainbackground') ? 'mainbackground' : '';
      state.preview = null;
      $('#bg-directory').textContent = result.directory;
      $('#bg-preview-image').hidden = true;
      $('#bg-preview-image').removeAttribute('src');
      $('#bg-preview-meta').textContent = '';
      $('#bg-preview-label').textContent = t('background.preview_hint');
      buildCategories();
      renderList();
      MCE.setStatus(t('background.loaded', { count: result.count }));
    } else if (result.operation === 'preview') {
      state.preview = result;
      $('#bg-preview-image').src = result.data_url;
      $('#bg-preview-image').alt = result.name;
      $('#bg-preview-image').hidden = false;
      $('#bg-preview-label').textContent = result.id;
      refreshPreviewMeta();
      MCE.setStatus(t('app.status.ready'));
    } else if (result.operation === 'export') {
      App.exportCount = result.export_count;
      MCE.refreshExportCount();
      const message = t('background.export_done', { count: result.count });
      MCE.setStatus(message);
      MCE.toast(message, result.errors.length ? 'warning' : 'success');
      showErrors(result.errors);
      if (result.count && !result.errors.length) MCE.offerOpen(
        t('background.export'), message, result.output_dir,
      );
    } else if (result.operation === 'prewarm') {
      const message = t('background.prewarm_done', { count: result.count, total: result.total });
      MCE.setStatus(message);
      MCE.toast(message, result.errors.length ? 'warning' : 'success');
      showErrors(result.errors);
    }
  });

  function refreshPreviewMeta() {
    if (!state.preview) return;
    const p = state.preview;
    $('#bg-preview-meta').textContent = t('background.preview_meta', {
      name: p.name, width: p.size[0], height: p.size[1], count: p.count,
    });
  }

  MCE.refreshBackgrounds = () => { buildCategories(); renderList(); refreshPreviewMeta(); };
  MCE.loadBackgroundDirectory = (path) => startJob('scan', () => api().load_backgrounds(path));
  MCE.initBackgrounds = () => {
    $('#bg-load').addEventListener('click', loadBackgrounds);
    $('#bg-prewarm').addEventListener('click', () => startJob('prewarm',
      () => api().prewarm_backgrounds()));
    $('#bg-export').addEventListener('click', () => startJob('export',
      () => api().export_backgrounds(Array.from(state.selected))));
    $('#bg-open').addEventListener('click', () => api().open_output());
    $('#bg-cancel').addEventListener('click', async () => {
      $('#bg-cancel').disabled = true;
      try { await api().cancel_backgrounds(); }
      catch (error) { $('#bg-cancel').disabled = false; MCE.toast(String(error), 'error'); }
    });
    $('#bg-search').addEventListener('input', renderList);
    $('#bg-select-all').addEventListener('click', () => {
      visibleBundles().forEach((item) => state.selected.add(item.id)); renderList();
    });
    $('#bg-select-none').addEventListener('click', () => { state.selected.clear(); renderList(); });
    MCE.refreshBackgrounds();
  };
})();
