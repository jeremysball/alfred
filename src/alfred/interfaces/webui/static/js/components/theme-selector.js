/**
 * Settings Menu Web Component
 */
import { applyThemeContrast, getContrastPalette } from "../utils/contrast.js";

const SETTINGS_PORTAL_ID = "settings-portal-root";
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
  ].join("; ");
}

class SettingsMenu extends HTMLElement {
  constructor() {
    super();
    // localStorage.getItem('alfred-theme')
    this._currentTheme =
      localStorage.getItem("theme") || localStorage.getItem("alfred-theme") || "dark-academia";
    this._fontSize = localStorage.getItem("alfred-font-size") || "";
    this._fontFamily = localStorage.getItem("alfred-font-family") || "";
    this._themes = [
      {
        id: "swiss-international",
        name: "Swiss Light",
        description: "Clean light style",
        previewColor: "#990000",
        surfaceColor: "#ffffff",
      },
      {
        id: "minimal",
        name: "Minimal",
        description: "Clean and simple",
        previewColor: "#1565c0",
        surfaceColor: "#f5f5f5",
      },
      {
        id: "neumorphism",
        name: "Neumorphism Light",
        description: "Soft light plastic",
        previewColor: "#3d4fb8",
        surfaceColor: "#e0e5ec",
      },
      {
        id: "neumorphism-dark",
        name: "Neumorphism Dark",
        description: "Soft dark plastic",
        previewColor: "#3d4fb8",
        surfaceColor: "#1a202c",
      },
      {
        id: "swiss-international-dark",
        name: "Swiss Dark",
        description: "Clean dark style",
        previewColor: "#cc0000",
        surfaceColor: "#2a2a2a",
      },
      {
        id: "dark-academia",
        name: "Dark Academia",
        description: "Classical library dark",
        previewColor: "#8b6914",
        surfaceColor: "#24201c",
      },
      {
        id: "element-modern",
        name: "Element Modern",
        description: "True black, seamless flow",
        previewColor: "#A855F7",
        surfaceColor: "#0a0a0a",
      },
      {
        id: "elegant-modern-yellow",
        name: "Elegant Modern Yellow",
        description: "Monospace yellow on black",
        previewColor: "#FBBF24",
        surfaceColor: "#0a0a0a",
      },
      {
        id: "kidcore-playground",
        name: "Kidcore Playground",
        description: "Handmade scrapbook chaos",
        previewColor: "#ff4fd8",
        surfaceColor: "#26003d",
      },
      {
        id: "spacejam-neocities",
        name: "Space Jam Neocities",
        description: "Gaudy 90s neon browser shrine",
        previewColor: "#00e5ff",
        surfaceColor: "#180022",
      },
    ];
    this._fontSizes = [
      { id: "", name: "Default", description: "Inherit from theme" },
      { id: "small", name: "Small", description: "90% base size" },
      { id: "medium", name: "Medium", description: "100% base size" },
      { id: "large", name: "Large", description: "115% base size" },
      { id: "xlarge", name: "Extra Large", description: "130% base size" },
    ];
    this._fontFamilies = [
      { id: "", name: "Default", description: "Inherit from theme" },
      { id: "system", name: "System", description: "System UI fonts" },
      { id: "serif", name: "Serif", description: "Georgia, Times New Roman" },
      { id: "mono", name: "Monospace", description: "JetBrains Mono, Fira Code" },
      { id: "sans", name: "Sans-serif", description: "Inter, Helvetica, Arial" },
    ];
    this._isOpen = false;
    this._portalRoot = null;
    this._portalClickHandler = null;
    this._portalResizeHandler = null;
    this._portalRootBound = false;
  }

  connectedCallback() {
    this._applyTheme(this._currentTheme);
    this._applyFontSize(this._fontSize);
    this._applyFontFamily(this._fontFamily);
    this._ensurePortalRoot();
    this._render();
  }

  disconnectedCallback() {
    this._stopPortalTracking();
    this._clearPortal();
    this._detachPortalRootListener();
  }

  _applyTheme(themeId) {
    // document.documentElement.setAttribute('data-theme', themeId)
    document.documentElement.setAttribute("data-theme", themeId);
    // localStorage.setItem('alfred-theme', themeId)
    localStorage.setItem("theme", themeId);
    localStorage.setItem("alfred-theme", themeId);
    this._currentTheme = themeId;
    applyThemeContrast();
  }

  _applyFontSize(sizeId) {
    const root = document.documentElement;
    root.classList.remove(
      "font-size-small",
      "font-size-medium",
      "font-size-large",
      "font-size-xlarge",
    );
    if (sizeId && sizeId !== "") {
      root.classList.add(`font-size-${sizeId}`);
    }
    // localStorage.setItem('alfred-font-size', sizeId)
    localStorage.setItem("alfred-font-size", sizeId);
    // localStorage.getItem('alfred-font-family')
    // localStorage.getItem('alfred-font-size')
    this._fontSize = sizeId;
  }

  _applyFontFamily(fontId) {
    const root = document.documentElement;
    root.classList.remove(
      "font-family-system",
      "font-family-serif",
      "font-family-mono",
      "font-family-sans",
    );
    if (fontId && fontId !== "") {
      root.classList.add(`font-family-${fontId}`);
    }
    // localStorage.setItem('alfred-font-family', fontId)
    localStorage.setItem("alfred-font-family", fontId);
    this._fontFamily = fontId;
  }

  _buildThemeOptionsMarkup() {
    return this._themes
      .map((theme) => {
        const isActive = theme.id === this._currentTheme;
        return `
        <div class="theme-option ${isActive ? "active" : ""}" data-theme="${theme.id}" style="${buildThemeOptionStyle(theme)}">
          <div class="theme-color-preview" style="background: ${theme.previewColor}"></div>
          <div class="theme-info">
            <div class="theme-name">${theme.name}</div>
            <div class="theme-description">${theme.description}</div>
          </div>
          ${isActive ? '<div class="theme-check">✓</div>' : ""}
        </div>
      `;
      })
      .join("");
  }

  _render() {
    this.innerHTML = `
      <div class="settings-menu-wrapper">
        <button class="settings-toggle" type="button" aria-label="Settings" aria-expanded="${String(this._isOpen)}">
          <svg class="settings-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"/>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
          </svg>
        </button>
      </div>
    `;

    this._attachToggleListeners();
    this._syncPortal();
  }

  _attachToggleListeners() {
    const toggle = this.querySelector(".settings-toggle");
    if (!toggle) {
      return;
    }

    toggle.addEventListener("click", (event) => {
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

    const root = document.createElement("div");
    root.id = SETTINGS_PORTAL_ID;
    root.className = "settings-portal-root";
    root.setAttribute("aria-hidden", "true");
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
      const overlay = event.target.closest(".settings-overlay");
      if (overlay) {
        event.stopPropagation();
        this._isOpen = false;
        this._render();
        return;
      }

      const themeOption = event.target.closest(".theme-option");
      if (themeOption && this._portalRoot?.contains(themeOption)) {
        event.stopPropagation();
        const themeId = themeOption.dataset.theme;
        if (themeId) {
          this._applyTheme(themeId);
        }
        this._isOpen = false;
        this._render();
        return;
      }

      const fontSizeOption = event.target.closest("[data-font-size]");
      if (fontSizeOption && this._portalRoot?.contains(fontSizeOption)) {
        event.stopPropagation();
        const sizeId = fontSizeOption.dataset.fontSize;
        this._applyFontSize(sizeId);
        this._syncPortal();
        return;
      }

      const fontFamilyOption = event.target.closest("[data-font-family]");
      if (fontFamilyOption && this._portalRoot?.contains(fontFamilyOption)) {
        event.stopPropagation();
        const fontId = fontFamilyOption.dataset.fontFamily;
        this._applyFontFamily(fontId);
        this._syncPortal();
        return;
      }
    };

    this._portalRoot.addEventListener("click", this._portalClickHandler);
    this._portalRootBound = true;
  }

  _detachPortalRootListener() {
    if (!this._portalRoot || !this._portalRootBound || !this._portalClickHandler) {
      return;
    }

    this._portalRoot.removeEventListener("click", this._portalClickHandler);
    this._portalRootBound = false;
    this._portalClickHandler = null;
  }

  _buildFontSizeOptionsMarkup() {
    return this._fontSizes
      .map((size) => {
        const isActive = size.id === this._fontSize;
        return `
        <div class="font-option ${isActive ? "active" : ""}" data-font-size="${size.id}">
          <div class="font-option-info">
            <div class="font-option-name">${size.name}</div>
            <div class="font-option-description">${size.description}</div>
          </div>
          ${isActive ? '<div class="font-check">✓</div>' : ""}
        </div>
      `;
      })
      .join("");
  }

  _buildFontFamilyOptionsMarkup() {
    return this._fontFamilies
      .map((font) => {
        const isActive = font.id === this._fontFamily;
        return `
        <div class="font-option ${isActive ? "active" : ""}" data-font-family="${font.id}">
          <div class="font-option-info">
            <div class="font-option-name">${font.name}</div>
            <div class="font-option-description">${font.description}</div>
          </div>
          ${isActive ? '<div class="font-check">✓</div>' : ""}
        </div>
      `;
      })
      .join("");
  }

  _buildKeybindsMarkup() {
    const KeymapManager = window.KeymapManager;
    if (!KeymapManager) {
      return '<div class="keybinds-unavailable">Keyboard shortcuts unavailable</div>';
    }

    const grouped = KeymapManager.getBindingsByCategory();
    const categories = Object.keys(grouped).sort();

    return categories
      .map((category) => {
        const bindings = grouped[category].sort((a, b) =>
          a.description.localeCompare(b.description),
        );

        return `
        <div class="keybind-category">
          <div class="keybind-category-header">${category}</div>
          <div class="keybind-list">
            ${bindings
              .map(
                (binding) => `
              <div class="keybind-item" data-action="${binding.actionId}">
                <span class="keybind-description">${binding.description}</span>
                <kbd class="keybind-key">${KeymapManager.formatBinding(binding)}</kbd>
              </div>
            `,
              )
              .join("")}
          </div>
        </div>
      `;
      })
      .join("");
  }

  _syncPortal() {
    const portalRoot = this._ensurePortalRoot();
    portalRoot.setAttribute("aria-hidden", String(!this._isOpen));

    if (!this._isOpen) {
      this._clearPortal();
      return;
    }

    portalRoot.innerHTML = `
      <div class="settings-overlay"></div>
      <div class="settings-content" role="dialog" aria-label="Settings">
        <div class="settings-section">
          <div class="settings-section-header">Theme</div>
          ${this._buildThemeOptionsMarkup()}
        </div>
        <div class="settings-section">
          <div class="settings-section-header">Font Size</div>
          ${this._buildFontSizeOptionsMarkup()}
        </div>
        <div class="settings-section">
          <div class="settings-section-header">Font Family</div>
          ${this._buildFontFamilyOptionsMarkup()}
        </div>
        <div class="settings-section">
          <div class="settings-section-header">Keyboard Shortcuts</div>
          <div class="keybinds-container">
            ${this._buildKeybindsMarkup()}
          </div>
          <div class="keybinds-footer">
            <button class="keybinds-reset-btn" type="button">Reset to defaults</button>
            <button class="keybinds-help-btn" type="button">Open Help (F1)</button>
          </div>
        </div>
      </div>
    `;

    // Attach keybind listeners
    const resetBtn = portalRoot.querySelector(".keybinds-reset-btn");
    if (resetBtn) {
      resetBtn.addEventListener("click", () => {
        if (window.KeymapManager) {
          window.KeymapManager.resetAllBindings();
          this._syncPortal();
        }
      });
    }

    const helpBtn = portalRoot.querySelector(".keybinds-help-btn");
    if (helpBtn && window.alfredHelpSheet) {
      helpBtn.addEventListener("click", () => {
        this._isOpen = false;
        this._render();
        window.alfredHelpSheet.show();
      });
    }

    this._portalRoot = portalRoot;
    this._positionPortal();
    this._startPortalTracking();
  }

  _clearPortal() {
    if (this._portalRoot) {
      this._portalRoot.innerHTML = "";
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
    window.addEventListener("resize", this._portalResizeHandler, { passive: true });
  }

  _stopPortalTracking() {
    if (!this._portalResizeHandler) {
      return;
    }

    window.removeEventListener("resize", this._portalResizeHandler);
    this._portalResizeHandler = null;
  }

  _positionPortal() {
    if (!this._isOpen || !this._portalRoot) {
      return;
    }

    const content = this._portalRoot.querySelector(".settings-content");
    const toggle = this.querySelector(".settings-toggle");
    if (!content || !toggle) {
      return;
    }

    content.style.position = "fixed";
    content.style.transform = "none";

    if (window.innerWidth < DESKTOP_BREAKPOINT) {
      content.style.top = "auto";
      content.style.right = "0";
      content.style.bottom = "0";
      content.style.left = "0";
      return;
    }

    const rect = toggle.getBoundingClientRect();
    const top = Math.round(rect.bottom + 8);
    const right = Math.max(16, Math.round(window.innerWidth - rect.right));

    content.style.top = `${top}px`;
    content.style.right = `${right}px`;
    content.style.bottom = "auto";
    content.style.left = "auto";
  }
}

customElements.define("settings-menu", SettingsMenu);
