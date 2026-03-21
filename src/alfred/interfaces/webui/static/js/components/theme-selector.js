/**
 * Settings Menu Web Component
 *
 * Usage: <settings-menu></settings-menu>
 *
 * Contains:
 * - Theme selector (Dark Academia, Swiss International, Neumorphism)
 */
class SettingsMenu extends HTMLElement {
  constructor() {
    super();
    this._currentTheme = localStorage.getItem('alfred-theme') || 'dark-academia';
    this._themes = [
      {
        id: 'dark-academia',
        name: 'Dark Academia',
        description: 'Classical library dark',
        color: '#c9a959',
        previewColor: '#8b6914'
      },
      {
        id: 'dark-academia-light',
        name: 'Dark Academia Light',
        description: 'Classical library light',
        color: '#d4a574',
        previewColor: '#8b5a2b'
      },
      {
        id: 'swiss-international',
        name: 'Swiss Light',
        description: 'Clean light style',
        color: '#e30613',
        previewColor: '#990000'
      },
      {
        id: 'swiss-international-dark',
        name: 'Swiss Dark',
        description: 'Clean dark style',
        color: '#ff3333',
        previewColor: '#cc0000'
      },
      {
        id: 'neumorphism',
        name: 'Neumorphism Light',
        description: 'Soft light plastic',
        color: '#667eea',
        previewColor: '#3d4fb8'
      },
      {
        id: 'neumorphism-dark',
        name: 'Neumorphism Dark',
        description: 'Soft dark plastic',
        color: '#667eea',
        previewColor: '#3d4fb8'
      },
      {
        id: 'minimal',
        name: 'Minimal',
        description: 'Clean and simple',
        color: '#2196f3',
        previewColor: '#1565c0'
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
          <div class="theme-color-preview" style="background: ${theme.previewColor || theme.color}"></div>
          <div class="theme-info">
            <div class="theme-name">${theme.name}</div>
            <div class="theme-description">${theme.description}</div>
          </div>
          ${isActive ? '<div class="theme-check">✓</div>' : ''}
        </div>
      `;
    }).join('');

    this.innerHTML = `
      <div class="settings-menu">
        <button class="settings-toggle" title="Settings">
          <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1"/>
          </svg>
        </button>
        <div class="settings-dropdown hidden">
          <div class="settings-section">
            <div class="settings-section-header">Theme</div>
            ${themeOptions}
          </div>
        </div>
      </div>
    `;
  }

  _setupListeners() {
    const toggle = this.querySelector('.settings-toggle');
    const dropdown = this.querySelector('.settings-dropdown');

    // Toggle click handler
    toggle?.addEventListener('click', (e) => {
      e.preventDefault();
      e.stopPropagation();
      const isHidden = dropdown?.classList.contains('hidden');
      if (isHidden) {
        this._openMenu();
      } else {
        this._closeMenu();
      }
    });

    // Close on backdrop click
    dropdown?.addEventListener('click', (e) => {
      if (e.target === dropdown) {
        this._closeMenu();
      }
    });

    // Theme selection
    this.querySelectorAll('.theme-option').forEach(option => {
      option.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        const themeId = option.dataset.theme;
        this._applyTheme(themeId);
        this._closeMenu();
        this._render();
        this._setupListeners();
      });
    });
  }

  _openMenu() {
    const dropdown = this.querySelector('.settings-dropdown');
    dropdown?.classList.remove('hidden');
    // Close when clicking outside
    this._outsideClickHandler = (e) => {
      if (!this.contains(e.target)) {
        this._closeMenu();
      }
    };
    setTimeout(() => {
      document.addEventListener('click', this._outsideClickHandler);
    }, 0);
  }

  _closeMenu() {
    const dropdown = this.querySelector('.settings-dropdown');
    dropdown?.classList.add('hidden');
    if (this._outsideClickHandler) {
      document.removeEventListener('click', this._outsideClickHandler);
      this._outsideClickHandler = null;
    }
  }
}

// Register the custom element
customElements.define('settings-menu', SettingsMenu);
