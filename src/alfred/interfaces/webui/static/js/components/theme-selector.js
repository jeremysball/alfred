/**
 * Settings Menu Web Component
 */
import { applyThemeContrast, getContrastPalette } from '../utils/contrast.js';

const SETTINGS_PORTAL_ID = 'settings-portal-root';
const DESKTOP_BREAKPOINT = 769;

function buildThemeOptionStyle(theme) {
  const palette = getContrastPalette(theme.surfaceColor);
  return [
    `background: ${theme.surfaceColor}`,
    `--theme-option-bg: ${theme.surfaceColor}`,
    `--theme-option-text: ${palette.text}`,
    `--theme-option-muted: ${palette.muted}`,
    `--theme-option-accent: ${palette.accent}`,
    `--theme-option-active-border: 2px solid ${palette.accent}`,
  ].join('; ');
}

class SettingsMenu extends HTMLElement {
  constructor() {
    super();
    this._currentTheme = localStorage.getItem('alfred-theme') || 'dark-academia';
    this._themes = [
      { id: 'dark-academia', name: 'Dark Academia', description: 'Classical library dark', previewColor: '#8b6914', surfaceColor: '#24201c' },
      { id: 'dark-academia-light', name: 'Dark Academia Light', description: 'Classical library light', previewColor: '#8b5a2b', surfaceColor: '#f4efe6' },
      { id: 'swiss-international', name: 'Swiss Light', description: 'Clean light style', previewColor: '#990000', surfaceColor: '#ffffff' },
      { id: 'swiss-international-dark', name: 'Swiss Dark', description: 'Clean dark style', previewColor: '#cc0000', surfaceColor: '#2a2a2a' },
      { id: 'neumorphism', name: 'Neumorphism Light', description: 'Soft light plastic', previewColor: '#3d4fb8', surfaceColor: '#e0e5ec' },
      { id: 'neumorphism-dark', name: 'Neumorphism Dark', description: 'Soft dark plastic', previewColor: '#3d4fb8', surfaceColor: '#1a202c' },
      { id: 'minimal', name: 'Minimal', description: 'Clean and simple', previewColor: '#1565c0', surfaceColor: '#f5f5f5' },
      { id: 'element-modern', name: 'Element Modern', description: 'True black, seamless flow', previewColor: '#A855F7', surfaceColor: '#0a0a0a' },
      { id: 'kidcore-playground', name: 'Kidcore Playground', description: 'Handmade scrapbook chaos', previewColor: '#ff4fd8', surfaceColor: '#26003d' },
      { id: 'spacejam-neocities', name: 'Space Jam Neocities', description: 'Gaudy 90s neon browser shrine', previewColor: '#00e5ff', surfaceColor: '#180022' }
    ];
    this._isOpen = false;
    this._portalRoot = null;
    this._portalClickHandler = null;
    this._portalResizeHandler = null;
    this._portalRootBound = false;
  }

  connectedCallback() {
    this._applyTheme(this._currentTheme);
    this._ensurePortalRoot();
    this._render();
  }

  disconnectedCallback() {
    this._stopPortalTracking();
    this._clearPortal();
    this._detachPortalRootListener();
  }

  _applyTheme(themeId) {
    document.documentElement.setAttribute('data-theme', themeId);
    localStorage.setItem('alfred-theme', themeId);
    this._currentTheme = themeId;
    applyThemeContrast();
  }

  _buildThemeOptionsMarkup() {
    return this._themes.map(theme => {
      const isActive = theme.id === this._currentTheme;
      return `
        <div class="theme-option ${isActive ? 'active' : ''}" data-theme="${theme.id}" style="${buildThemeOptionStyle(theme)}">
          <div class="theme-color-preview" style="background: ${theme.previewColor}"></div>
          <div class="theme-info">
            <div class="theme-name">${theme.name}</div>
            <div class="theme-description">${theme.description}</div>
          </div>
          ${isActive ? '<div class="theme-check">✓</div>' : ''}
        </div>
      `;
    }).join('');
  }

  _render() {
    this.innerHTML = `
      <div class="settings-menu-wrapper">
        <button class="settings-toggle" type="button" aria-label="Settings" aria-expanded="${String(this._isOpen)}">
          <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1"/>
          </svg>
        </button>
      </div>
    `;

    this._attachToggleListeners();
    this._syncPortal();
  }

  _attachToggleListeners() {
    const toggle = this.querySelector('.settings-toggle');
    if (!toggle) {
      return;
    }

    toggle.addEventListener('click', (event) => {
      event.stopPropagation();
      this._isOpen = !this._isOpen;
      this._render();
    });
  }

  _ensurePortalRoot() {
    const existingRoot = document.getElementById(SETTINGS_PORTAL_ID);
    if (existingRoot) {
      this._portalRoot = existingRoot;
      this._bindPortalRootListener();
      return existingRoot;
    }

    const root = document.createElement('div');
    root.id = SETTINGS_PORTAL_ID;
    root.className = 'settings-portal-root';
    root.setAttribute('aria-hidden', 'true');
    document.body.appendChild(root);
    this._portalRoot = root;
    this._bindPortalRootListener();
    return root;
  }

  _bindPortalRootListener() {
    if (!this._portalRoot || this._portalRootBound) {
      return;
    }

    this._portalClickHandler = (event) => {
      const overlay = event.target.closest('.settings-overlay');
      if (overlay) {
        event.stopPropagation();
        this._isOpen = false;
        this._render();
        return;
      }

      const themeOption = event.target.closest('.theme-option');
      if (themeOption && this._portalRoot?.contains(themeOption)) {
        event.stopPropagation();
        const themeId = themeOption.dataset.theme;
        if (themeId) {
          this._applyTheme(themeId);
        }
        this._isOpen = false;
        this._render();
      }
    };

    this._portalRoot.addEventListener('click', this._portalClickHandler);
    this._portalRootBound = true;
  }

  _detachPortalRootListener() {
    if (!this._portalRoot || !this._portalRootBound || !this._portalClickHandler) {
      return;
    }

    this._portalRoot.removeEventListener('click', this._portalClickHandler);
    this._portalRootBound = false;
    this._portalClickHandler = null;
  }

  _syncPortal() {
    const portalRoot = this._ensurePortalRoot();
    portalRoot.setAttribute('aria-hidden', String(!this._isOpen));

    if (!this._isOpen) {
      this._clearPortal();
      return;
    }

    portalRoot.innerHTML = `
      <div class="settings-overlay"></div>
      <div class="settings-content" role="dialog" aria-label="Theme settings">
        <div class="settings-section-header">Theme</div>
        ${this._buildThemeOptionsMarkup()}
      </div>
    `;

    this._portalRoot = portalRoot;
    this._positionPortal();
    this._startPortalTracking();
  }

  _clearPortal() {
    if (this._portalRoot) {
      this._portalRoot.innerHTML = '';
    }
    this._stopPortalTracking();
  }

  _startPortalTracking() {
    if (this._portalResizeHandler) {
      return;
    }

    this._portalResizeHandler = () => {
      this._positionPortal();
    };
    window.addEventListener('resize', this._portalResizeHandler, { passive: true });
  }

  _stopPortalTracking() {
    if (!this._portalResizeHandler) {
      return;
    }

    window.removeEventListener('resize', this._portalResizeHandler);
    this._portalResizeHandler = null;
  }

  _positionPortal() {
    if (!this._isOpen || !this._portalRoot) {
      return;
    }

    const content = this._portalRoot.querySelector('.settings-content');
    const toggle = this.querySelector('.settings-toggle');
    if (!content || !toggle) {
      return;
    }

    content.style.position = 'fixed';
    content.style.transform = 'none';

    if (window.innerWidth < DESKTOP_BREAKPOINT) {
      content.style.top = 'auto';
      content.style.right = '0';
      content.style.bottom = '0';
      content.style.left = '0';
      return;
    }

    const rect = toggle.getBoundingClientRect();
    const top = Math.round(rect.bottom + 8);
    const right = Math.max(16, Math.round(window.innerWidth - rect.right));

    content.style.top = `${top}px`;
    content.style.right = `${right}px`;
    content.style.bottom = 'auto';
    content.style.left = 'auto';
  }
}

customElements.define('settings-menu', SettingsMenu);
