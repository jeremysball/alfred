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
        color: '#c9a959'
      },
      {
        id: 'dark-academia-light',
        name: 'Dark Academia Light',
        description: 'Classical library light',
        color: '#d4a574'
      },
      {
        id: 'swiss-international',
        name: 'Swiss Light',
        description: 'Clean light style',
        color: '#e30613'
      },
      {
        id: 'swiss-international-dark',
        name: 'Swiss Dark',
        description: 'Clean dark style',
        color: '#ff3333'
      },
      {
        id: 'neumorphism',
        name: 'Neumorphism Light',
        description: 'Soft light plastic',
        color: '#667eea'
      },
      {
        id: 'neumorphism-dark',
        name: 'Neumorphism Dark',
        description: 'Soft dark plastic',
        color: '#667eea'
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
          <div class="theme-color-preview" style="background: ${theme.color}"></div>
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

    toggle?.addEventListener('click', (e) => {
      e.stopPropagation();
      dropdown?.classList.toggle('hidden');
    });

    // Close menu when clicking outside
    document.addEventListener('click', () => {
      dropdown?.classList.add('hidden');
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
customElements.define('settings-menu', SettingsMenu);
