/**
 * Settings Menu Web Component
 */
import { applyThemeContrast, getContrastPalette } from '../utils/contrast.js';

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
      { id: 'kidcore-playground', name: 'Kidcore Playground', description: 'Neocities glitter chaos', previewColor: '#ff4fd8', surfaceColor: '#26003d' }
    ];
    this._isOpen = false;
  }

  connectedCallback() {
    this._applyTheme(this._currentTheme);
    this._render();
  }

  _applyTheme(themeId) {
    document.documentElement.setAttribute('data-theme', themeId);
    localStorage.setItem('alfred-theme', themeId);
    this._currentTheme = themeId;
    applyThemeContrast();
  }

  _render() {
    const themeOptions = this._themes.map(theme => {
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

    const isHidden = this._isOpen ? '' : 'hidden';

    this.innerHTML = `
      <div class="settings-menu-wrapper">
        <button class="settings-toggle" type="button" aria-label="Settings">
          <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1"/>
          </svg>
        </button>
        <div class="settings-overlay ${isHidden}"></div>
        <div class="settings-content ${isHidden}">
          <div class="settings-section-header">Theme</div>
          ${themeOptions}
        </div>
      </div>
    `;

    this._attachListeners();
  }

  _attachListeners() {
    const toggle = this.querySelector('.settings-toggle');
    const overlay = this.querySelector('.settings-overlay');

    if (!toggle) return;

    toggle.addEventListener('click', (e) => {
      e.stopPropagation();
      this._isOpen = !this._isOpen;
      this._render();
    });

    if (overlay) {
      overlay.addEventListener('click', (e) => {
        e.stopPropagation();
        this._isOpen = false;
        this._render();
      });
    }

    this.querySelectorAll('.theme-option').forEach(option => {
      option.addEventListener('click', (e) => {
        e.stopPropagation();
        this._applyTheme(option.dataset.theme);
        this._isOpen = false;
        this._render();
      });
    });
  }
}

customElements.define('settings-menu', SettingsMenu);
