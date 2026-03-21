(() => {
  const ACTIVE_THEMES = new Set(['kidcore-playground', 'spacejam-neocities']);
  const UPDATE_STORAGE_KEY = 'alfred-kidcore-updates';
  const EXPORTED_FILENAME_PREFIX = 'alfred-scrapbook';

  const DEFAULT_UPDATE_ENTRIES = Object.freeze([
    {
      id: 'seed-update-1',
      title: 'retro tools',
      message: 'search, nav, export, and notes are alive',
      createdAt: '2026-03-01T09:00:00.000Z',
    },
    {
      id: 'seed-update-2',
      title: 'button polish',
      message: 'the scrapbook now feels more like a tiny personal site than a widget drawer',
      createdAt: '2026-03-04T14:30:00.000Z',
    },
    {
      id: 'seed-update-3',
      title: 'neon pass',
      message: 'the interface leans harder into loud retro browser energy',
      createdAt: '2026-03-08T18:15:00.000Z',
    },
  ]);

  function readJSON(key, fallback) {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) {
        return structuredClone(fallback);
      }

      const parsed = JSON.parse(raw);
      return parsed ?? structuredClone(fallback);
    } catch {
      return structuredClone(fallback);
    }
  }

  function writeJSON(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
    } catch {
      // Ignore storage failures in private browsing or blocked storage contexts.
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function uid(prefix) {
    if (window.crypto?.randomUUID) {
      return `${prefix}-${window.crypto.randomUUID()}`;
    }

    return `${prefix}-${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
  }

  function formatTimestamp(value) {
    try {
      return new Date(value).toLocaleString();
    } catch {
      return String(value || '');
    }
  }

  function normalizeUpdateEntry(entry) {
    return {
      id: entry?.id || uid('update'),
      title: String(entry?.title || 'Untitled update').trim() || 'Untitled update',
      message: String(entry?.message || '').trim(),
      createdAt: entry?.createdAt || new Date().toISOString(),
    };
  }

  function matchesQuery(value, query) {
    if (!query) {
      return true;
    }

    return String(value || '').toLowerCase().includes(query);
  }

  function collectGuestbookEntries() {
    const state = window.__alfredKidcoreSite?.getState?.();
    if (Array.isArray(state?.guestbookEntries)) {
      return state.guestbookEntries;
    }

    return [];
  }

  function collectUpdateEntries(userEntries) {
    return [
      ...DEFAULT_UPDATE_ENTRIES,
      ...userEntries.map(normalizeUpdateEntry),
    ];
  }

  function downloadJson(filename, payload) {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.rel = 'noreferrer';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
  }

  class ScrapbookEnhancer {
    constructor(root) {
      this.root = root;
      this.searchInput = root.querySelector('#kidcore-homeboard-search');
      this.clearSearchButton = root.querySelector('#kidcore-homeboard-clear-search');
      this.exportButton = root.querySelector('#kidcore-homeboard-export');
      this.searchSummary = root.querySelector('#kidcore-homeboard-search-summary');
      this.guestbookList = root.querySelector('#kidcore-guestbook-entries');
      this.updatesList = root.querySelector('#kidcore-updates-list');
      this.updatesSummary = root.querySelector('#kidcore-updates-summary');
      this.updateForm = root.querySelector('#kidcore-update-form');
      this.updateTitle = root.querySelector('#kidcore-update-title');
      this.updateMessage = root.querySelector('#kidcore-update-message');
      this.updateSubmit = root.querySelector('#kidcore-update-submit');
      const storedUpdates = readJSON(UPDATE_STORAGE_KEY, []);
      this.updateEntries = Array.isArray(storedUpdates) ? storedUpdates.map(normalizeUpdateEntry) : [];
      this.searchQuery = '';
      this.filterQueued = false;

      this.guestbookObserver = new MutationObserver(() => this.scheduleFilter());
      if (this.guestbookList) {
        this.guestbookObserver.observe(this.guestbookList, { childList: true });
      }

      this.bindEvents();
      this.renderUpdates();
      this.applyFilters();
    }

    bindEvents() {
      this.searchInput?.addEventListener('input', () => {
        this.searchQuery = this.searchInput.value.trim().toLowerCase();
        this.applyFilters();
      });

      this.searchInput?.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') {
          event.preventDefault();
          this.clearSearch();
        }
      });

      this.clearSearchButton?.addEventListener('click', () => {
        this.clearSearch();
      });

      this.exportButton?.addEventListener('click', () => {
        this.exportSnapshot();
      });

      this.updateForm?.addEventListener('submit', (event) => {
        event.preventDefault();
        this.handleUpdateSubmit();
      });

      this.updateSubmit?.addEventListener('click', () => {
        // Leave submit handling to the form, but keep the button reachable from tests.
      });
    }

    syncVisibility() {
      // Visibility is owned by the main homeboard component.
    }

    clearSearch() {
      this.searchQuery = '';
      if (this.searchInput) {
        this.searchInput.value = '';
      }
      this.applyFilters();
    }

    scheduleFilter() {
      if (this.filterQueued) {
        return;
      }

      this.filterQueued = true;
      window.requestAnimationFrame(() => {
        this.filterQueued = false;
        this.applyFilters();
      });
    }

    applyFilters() {
      this.filterGuestbookEntries();
      this.filterUpdateEntries();
      this.renderSearchSummary();
    }

    filterGuestbookEntries() {
      if (!this.guestbookList) {
        return;
      }

      const entries = Array.from(this.guestbookList.querySelectorAll('.kidcore-guestbook-entry'));
      const data = collectGuestbookEntries();
      const query = this.searchQuery;

      entries.forEach((entryEl, index) => {
        const entryData = data[index];
        const searchable = entryData ? `${entryData.name || ''} ${entryData.message || ''}` : entryEl.textContent || '';
        const matches = matchesQuery(searchable, query);
        entryEl.hidden = !matches;
        entryEl.setAttribute('aria-hidden', String(!matches));
      });
    }

    filterUpdateEntries() {
      if (!this.updatesList) {
        return;
      }

      const entries = Array.from(this.updatesList.querySelectorAll('.kidcore-update-entry'));
      const query = this.searchQuery;
      const data = collectUpdateEntries(this.updateEntries);

      if (entries.length !== data.length) {
        this.renderUpdates();
        return;
      }

      entries.forEach((entryEl, index) => {
        const entryData = data[index];
        const searchable = `${entryData.title || ''} ${entryData.message || ''}`;
        const matches = matchesQuery(searchable, query);
        entryEl.hidden = !matches;
        entryEl.setAttribute('aria-hidden', String(!matches));
      });
    }

    renderSearchSummary() {
      if (!this.searchSummary) {
        return;
      }

      if (!this.searchQuery) {
        this.searchSummary.textContent = 'browse guestbook notes, updates, and links.';
        if (this.updatesSummary) {
          this.updatesSummary.textContent = `${this.updateEntries.length} local ${this.updateEntries.length === 1 ? 'update' : 'updates'}`;
        }
        return;
      }

      const query = this.searchQuery;
      const guestbookMatches = collectGuestbookEntries().filter((entry) =>
        matchesQuery(`${entry.name || ''} ${entry.message || ''}`, query)
      ).length;
      const updateMatches = collectUpdateEntries(this.updateEntries).filter((entry) =>
        matchesQuery(`${entry.title || ''} ${entry.message || ''}`, query)
      ).length;

      this.searchSummary.textContent = `${guestbookMatches} matching guestbook ${guestbookMatches === 1 ? 'entry' : 'entries'} and ${updateMatches} matching update ${updateMatches === 1 ? 'entry' : 'entries'} for "${query}".`;

      if (this.updatesSummary) {
        this.updatesSummary.textContent = `${this.updateEntries.length} local ${this.updateEntries.length === 1 ? 'update' : 'updates'}`;
      }
    }

    renderUpdates() {
      if (!this.updatesList) {
        return;
      }

      const entries = collectUpdateEntries(this.updateEntries);
      const query = this.searchQuery;

      this.updatesList.innerHTML = entries
        .map((entry) => {
          const matches = matchesQuery(`${entry.title || ''} ${entry.message || ''}`, query);
          const hiddenAttr = matches ? '' : ' hidden aria-hidden="true"';

          return `
            <li class="kidcore-update-entry" data-update-id="${escapeHtml(entry.id)}"${hiddenAttr}>
              <div class="kidcore-update-entry-header">
                <strong class="kidcore-update-title">${escapeHtml(entry.title)}</strong>
                <span class="kidcore-update-time">${escapeHtml(formatTimestamp(entry.createdAt))}</span>
              </div>
              <p class="kidcore-update-message">${escapeHtml(entry.message || '')}</p>
            </li>
          `;
        })
        .join('');

      this.renderSearchSummary();
      this.filterGuestbookEntries();
    }

    handleUpdateSubmit() {
      const title = this.updateTitle?.value.trim() || 'Untitled update';
      const message = this.updateMessage?.value.trim() || '';

      if (!message) {
        this.toast('Update details cannot be empty.', 'warning');
        return;
      }

      this.updateEntries.unshift(normalizeUpdateEntry({
        id: uid('update'),
        title,
        message,
        createdAt: new Date().toISOString(),
      }));
      writeJSON(UPDATE_STORAGE_KEY, this.updateEntries);
      if (this.updateMessage) {
        this.updateMessage.value = '';
      }
      if (this.updateTitle) {
        this.updateTitle.value = '';
      }
      this.renderUpdates();
      this.toast('Update posted.', 'success');
    }

    exportSnapshot() {
      const payload = {
        exportedAt: new Date().toISOString(),
        theme: document.documentElement.getAttribute('data-theme') || '',
        guestbookEntries: collectGuestbookEntries(),
        updates: collectUpdateEntries(this.updateEntries),
        searchQuery: this.searchQuery,
      };
      downloadJson(`${EXPORTED_FILENAME_PREFIX}-${Date.now()}.json`, payload);
      this.toast('Scrapbook exported as JSON.', 'success');
    }

    toast(message, level = 'info') {
      const toastContainer = document.getElementById('toast-container');
      if (toastContainer?.show) {
        toastContainer.show(message, level, 4000);
        return;
      }

      if (level === 'error') {
        console.error(message);
      } else {
        console.log(message);
      }
    }
  }

  function initScrapbook() {
    const root = document.getElementById('kidcore-homeboard');
    if (!root) {
      return;
    }

    if (window.__alfredKidcoreScrapbook) {
      return;
    }

    const enhancer = new ScrapbookEnhancer(root);
    window.__alfredKidcoreScrapbook = enhancer;
    window.__alfredKidcoreHomeboard = enhancer;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initScrapbook, { once: true });
  } else {
    initScrapbook();
  }
})();
