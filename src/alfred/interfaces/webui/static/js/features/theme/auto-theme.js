/**
 * Auto-Theme Module
 * Detects and follows system color scheme preference
 */

const STORAGE_KEY = "alfred-theme-preference";

/**
 * Theme Manager class
 */
class ThemeManager {
  constructor() {
    this.systemPreference = "light";
    this.userPreference = null; // null = follow system
    this.mediaQuery = null;

    this._init();
  }

  /**
   * Initialize theme manager
   * @private
   */
  _init() {
    // Load saved preference
    this._loadPreference();

    // Set up system preference listener
    this._setupSystemListener();

    // Apply initial theme
    this._applyTheme();

    // Expose for debugging
    window.__alfredThemeManager = this;
  }

  /**
   * Load saved preference from localStorage
   * @private
   */
  _loadPreference() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        this.userPreference = parsed.userPreference || null;
      }
    } catch (e) {
      console.warn("[ThemeManager] Failed to load preference:", e);
    }
  }

  /**
   * Save preference to localStorage
   * @private
   */
  _savePreference() {
    try {
      localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          userPreference: this.userPreference,
          timestamp: Date.now(),
        }),
      );
    } catch (e) {
      console.warn("[ThemeManager] Failed to save preference:", e);
    }
  }

  /**
   * Set up system color scheme listener
   * @private
   */
  _setupSystemListener() {
    if (!window.matchMedia) return;

    this.mediaQuery = window.matchMedia("(prefers-color-scheme: dark)");

    // Set initial system preference
    this.systemPreference = this.mediaQuery.matches ? "dark" : "light";

    // Listen for changes
    this.mediaQuery.addEventListener("change", (e) => {
      this.systemPreference = e.matches ? "dark" : "light";
      if (this.userPreference === null) {
        this._applyTheme();
        this._notifyChange();
      }
    });
  }

  /**
   * Apply the current theme
   * @private
   */
  _applyTheme() {
    const theme = this.getEffectiveTheme();
    const root = document.documentElement;

    // Remove both theme classes
    root.classList.remove("theme-light", "theme-dark");

    // Add current theme class
    root.classList.add(`theme-${theme}`);

    // Also set data attribute for CSS selectors
    root.setAttribute("data-theme", theme);

    // Update meta theme-color
    this._updateMetaThemeColor(theme);

    // Dispatch custom event
    window.dispatchEvent(
      new CustomEvent("themechange", {
        detail: { theme, source: this.userPreference === null ? "system" : "user" },
      }),
    );
  }

  /**
   * Update meta theme-color tag
   * @private
   * @param {string} theme - 'light' or 'dark'
   */
  _updateMetaThemeColor(_theme) {
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) {
      // Use manifest theme color (blue) for both modes
      // or adapt based on theme
      meta.setAttribute("content", "#3b82f6");
    }
  }

  /**
   * Notify components of theme change
   * @private
   */
  _notifyChange() {
    // Trigger any registered callbacks
    if (this._callbacks) {
      this._callbacks.forEach((cb) => cb(this.getEffectiveTheme()));
    }
  }

  /**
   * Get the effective theme (accounting for system preference)
   * @returns {string} 'light' or 'dark'
   */
  getEffectiveTheme() {
    if (this.userPreference !== null) {
      return this.userPreference;
    }
    return this.systemPreference;
  }

  /**
   * Get current user preference
   * @returns {string|null} 'light', 'dark', or null (system)
   */
  getUserPreference() {
    return this.userPreference;
  }

  /**
   * Set user theme preference
   * @param {string|null} preference - 'light', 'dark', or null for system
   */
  setTheme(preference) {
    if (preference !== null && preference !== "light" && preference !== "dark") {
      console.warn("[ThemeManager] Invalid theme:", preference);
      return;
    }

    this.userPreference = preference;
    this._savePreference();
    this._applyTheme();
  }

  /**
   * Toggle between light and dark (user preference)
   */
  toggleTheme() {
    const current = this.getEffectiveTheme();
    this.setTheme(current === "light" ? "dark" : "light");
  }

  /**
   * Cycle through: system → light → dark → system
   */
  cycleTheme() {
    if (this.userPreference === null) {
      this.setTheme("light");
    } else if (this.userPreference === "light") {
      this.setTheme("dark");
    } else {
      this.setTheme(null); // back to system
    }
  }

  /**
   * Register callback for theme changes
   * @param {Function} callback
   * @returns {Function} Unsubscribe function
   */
  onThemeChange(callback) {
    if (!this._callbacks) {
      this._callbacks = [];
    }
    this._callbacks.push(callback);

    // Return unsubscribe function
    return () => {
      const index = this._callbacks.indexOf(callback);
      if (index > -1) {
        this._callbacks.splice(index, 1);
      }
    };
  }
}

// Singleton instance
let themeManager = null;

/**
 * Initialize theme manager
 * @returns {ThemeManager}
 */
export function initAutoTheme() {
  if (!themeManager) {
    themeManager = new ThemeManager();
  }
  return themeManager;
}

/**
 * Get theme manager instance
 * @returns {ThemeManager|null}
 */
export function getThemeManager() {
  return themeManager;
}

export { ThemeManager };
export default ThemeManager;
