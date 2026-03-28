/**
 * Theme Palette - Fuzzy finder for theme selection
 *
 * Opens with Leader > T > T (or any theme key)
 * Allows fuzzy searching through all available themes
 */

const THEMES = [
  { id: "dark-academia", name: "Dark Academia", description: "Classical library dark" },
  { id: "swiss-international", name: "Swiss Light", description: "Clean light style" },
  { id: "swiss-international-dark", name: "Swiss Dark", description: "Clean dark style" },
  { id: "minimal", name: "Minimal", description: "Clean and simple" },
  { id: "element-modern", name: "Element Modern", description: "True black, seamless flow" },
  {
    id: "elegant-modern-yellow",
    name: "Elegant Modern Yellow",
    description: "Monospace yellow on black",
  },
  { id: "neumorphism", name: "Neumorphism Light", description: "Soft light plastic" },
  { id: "neumorphism-dark", name: "Neumorphism Dark", description: "Soft dark plastic" },
  { id: "modern-dark", name: "Modern Dark", description: "Modern dark theme" },
  { id: "kidcore-playground", name: "Kidcore Playground", description: "Handmade scrapbook chaos" },
  { id: "kidcore-homeboard", name: "Kidcore Homeboard", description: "Personal home dashboard" },
  {
    id: "spacejam-neocities",
    name: "Space Jam Neocities",
    description: "Gaudy 90s neon browser shrine",
  },
];

class ThemePalette {
  constructor() {
    this.overlay = null;
    this.input = null;
    this.results = null;
    this.selectedIndex = 0;
    this.filteredThemes = [...THEMES];
    this.isOpen = false;

    this._handleKeydown = this._handleKeydown.bind(this);
    this._handleInput = this._handleInput.bind(this);
    this._handleClickOutside = this._handleClickOutside.bind(this);
  }

  open() {
    if (this.isOpen) return;

    this._createDOM();
    this.isOpen = true;
    this.filteredThemes = [...THEMES];
    this.selectedIndex = 0;
    this._render();

    // Focus input after a short delay
    setTimeout(() => this.input?.focus(), 50);

    document.addEventListener("keydown", this._handleKeydown);
    document.addEventListener("click", this._handleClickOutside);
  }

  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this._destroyDOM();

    document.removeEventListener("keydown", this._handleKeydown);
    document.removeEventListener("click", this._handleClickOutside);
  }

  _createDOM() {
    // Overlay
    this.overlay = document.createElement("div");
    this.overlay.className = "theme-palette-overlay";
    this.overlay.setAttribute("role", "dialog");
    this.overlay.setAttribute("aria-label", "Theme selector");

    // Container
    const container = document.createElement("div");
    container.className = "theme-palette-container";

    // Input
    this.input = document.createElement("input");
    this.input.type = "text";
    this.input.className = "theme-palette-input";
    this.input.placeholder = "Search themes...";
    this.input.setAttribute("autocomplete", "off");
    this.input.addEventListener("input", this._handleInput);

    // Results list
    this.results = document.createElement("div");
    this.results.className = "theme-palette-results";

    // Shortcuts hint
    const hints = document.createElement("div");
    hints.className = "theme-palette-hints";
    hints.innerHTML = `
      <span>↑↓ Navigate</span>
      <span>Enter Select</span>
      <span>Esc Close</span>
    `;

    container.appendChild(this.input);
    container.appendChild(this.results);
    container.appendChild(hints);
    this.overlay.appendChild(container);
    document.body.appendChild(this.overlay);
  }

  _destroyDOM() {
    if (this.overlay?.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }
    this.overlay = null;
    this.input = null;
    this.results = null;
  }

  _handleKeydown(e) {
    if (!this.isOpen) return;

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        this.close();
        break;
      case "Enter":
        e.preventDefault();
        this._select();
        break;
      case "ArrowDown":
        e.preventDefault();
        this._navigate(1);
        break;
      case "ArrowUp":
        e.preventDefault();
        this._navigate(-1);
        break;
      case "Tab":
        e.preventDefault();
        this._navigate(e.shiftKey ? -1 : 1);
        break;
    }
  }

  _handleInput() {
    const query = this.input.value.toLowerCase().trim();
    this.filteredThemes = THEMES.filter(
      (theme) =>
        theme.name.toLowerCase().includes(query) ||
        theme.description.toLowerCase().includes(query) ||
        theme.id.toLowerCase().includes(query),
    );
    this.selectedIndex = 0;
    this._render();
  }

  _handleClickOutside(e) {
    if (this.overlay && !this.overlay.contains(e.target)) {
      this.close();
    }
  }

  _navigate(direction) {
    if (this.filteredThemes.length === 0) return;
    this.selectedIndex =
      (this.selectedIndex + direction + this.filteredThemes.length) % this.filteredThemes.length;
    this._render();
    this._scrollSelectedIntoView();
  }

  _select() {
    if (this.filteredThemes.length === 0) return;
    const theme = this.filteredThemes[this.selectedIndex];
    this._applyTheme(theme.id);
    this.close();
  }

  _applyTheme(themeId) {
    document.documentElement.setAttribute("data-theme", themeId);
    localStorage.setItem("theme", themeId);
    window.addSystemMessage?.(`Theme changed to ${themeId}`);
  }

  _render() {
    if (!this.results) return;

    this.results.innerHTML = "";

    if (this.filteredThemes.length === 0) {
      this.results.innerHTML = '<div class="theme-palette-empty">No themes found</div>';
      return;
    }

    this.filteredThemes.forEach((theme, index) => {
      const item = document.createElement("div");
      item.className = "theme-palette-item";
      if (index === this.selectedIndex) {
        item.classList.add("selected");
      }
      item.innerHTML = `
        <div class="theme-palette-name">${this._highlightMatch(theme.name)}</div>
        <div class="theme-palette-description">${theme.description}</div>
      `;
      item.addEventListener("click", () => {
        this.selectedIndex = index;
        this._select();
      });
      this.results.appendChild(item);
    });
  }

  _highlightMatch(text) {
    const query = this.input?.value?.trim();
    if (!query) return text;
    const regex = new RegExp(`(${query})`, "gi");
    return text.replace(regex, "<mark>$1</mark>");
  }

  _scrollSelectedIntoView() {
    const selected = this.results?.querySelector(".selected");
    if (selected) {
      selected.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }
}

// Singleton instance
let instance = null;

function getThemePalette() {
  if (!instance) {
    instance = new ThemePalette();
  }
  return instance;
}

function openThemePalette() {
  getThemePalette().open();
}

// Export for ESM and browser
export { getThemePalette, openThemePalette, ThemePalette };

if (typeof window !== "undefined") {
  window.ThemePalette = ThemePalette;
  window.openThemePalette = openThemePalette;
}
