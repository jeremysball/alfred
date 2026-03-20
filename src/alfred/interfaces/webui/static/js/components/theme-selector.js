/**
 * Theme Selector Web Component
 *
 * Usage: <theme-selector></theme-selector>
 *
 * Allows switching between available themes:
 * - dark-academia: Classical, warm, literary aesthetic
 * - swiss-international: Clean, grid-based, typographic
 * - neumorphism: Soft, tactile, extruded plastic
 */
class ThemeSelector extends HTMLElement {
  constructor() {
    super();
    this._currentTheme = localStorage.getItem('alfred-theme') || 'dark-academia';
    this._themes = [
      {
        id: 'dark-academia',
        name: 'Dark Academia',
        description: 'Classical library aesthetic',
        icon: '📚'
      },
      {
        id: 'swiss-international',
        name: 'Swiss International',
        description: 'Clean typographic style',
        icon: '🇨🇭'
      },
      {
        id: 'neumorphism',
        name: 'Neumorphism',
        description: 'Soft tactile plastic',
        icon: '🔮'
      }
    ];
  }

  connectedCallback() {
    this._applyTheme(this._currentTheme);
    this._render();
    this._setupListeners();
  }

  _applyTheme(themeId) {
    document.documentElement.setAttribute('data-theme', themeId);
    localStorage.setItem('alfred-theme', themeId);
    this._currentTheme = themeId;
  }

  _render() {
    const themeOptions = this._themes.map(theme => {
      const isActive = theme.id === this._currentTheme;
      return `
        <div class="theme-option ${isActive ? 'active' : ''}" data-theme="${theme.id}">
          <span class="theme-icon">${theme.icon}</span>
          <div class="theme-info">
            <div class="theme-name">${theme.name}</div>
            <div class="theme-description">${theme.description}</div>
          </div>
        </div>
      `;
    }).join('');

    this.innerHTML = `
      <div class="theme-selector">
        <button class="theme-toggle" title="Change theme">
          <span class="current-theme-icon">
            ${this._themes.find(t => t.id === this._currentTheme)?.icon || '🎨'}
          </span>
        </button>
        <div class="theme-menu hidden">
          <div class="theme-menu-header">Select Theme</div>
          ${themeOptions}
        </div>
      </div>
    `;
  }

  _setupListeners() {
    const toggle = this.querySelector('.theme-toggle');
    const menu = this.querySelector('.theme-menu');

    toggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      menu?.classList.toggle('hidden');
    });

    // Close menu when clicking outside
    document.addEventListener('click', () => {
      menu?.classList.add('hidden');
    });

    // Theme selection
    this.querySelectorAll('.theme-option').forEach(option => {
      option.addEventListener('click', (e) => {
        e.stopPropagation();
        const themeId = option.dataset.theme;
        this._applyTheme(themeId);
        this._render();
        this._setupListeners();
      });
    });
  }
}

// Register the custom element
customElements.define('theme-selector', ThemeSelector);
