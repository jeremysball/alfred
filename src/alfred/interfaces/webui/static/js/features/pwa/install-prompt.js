/**
 * PWA Install Prompt Manager
 * Handles beforeinstallprompt event and custom install UI
 */

class InstallPromptManager {
  constructor() {
    this.deferredPrompt = null;
    this.isInstalled = false;
    this.installButton = null;

    this._init();
  }

  /**
   * Initialize the install prompt manager
   * @private
   */
  _init() {
    // Check if already installed
    this._checkInstalled();

    // Listen for beforeinstallprompt
    window.addEventListener("beforeinstallprompt", (e) => {
      // Prevent the mini-infobar from appearing on mobile
      e.preventDefault();
      // Store the event for later use
      this.deferredPrompt = e;
      // Show install button
      this._showInstallButton();
    });

    // Listen for appinstalled event
    window.addEventListener("appinstalled", () => {
      this.isInstalled = true;
      this.deferredPrompt = null;
      this._hideInstallButton();
      this._log("PWA was installed");
    });

    // Listen for display mode changes
    if (window.matchMedia) {
      const mediaQuery = window.matchMedia("(display-mode: standalone)");
      mediaQuery.addEventListener("change", (e) => {
        this.isInstalled = e.matches;
        if (e.matches) {
          this._hideInstallButton();
        }
      });
    }
  }

  /**
   * Check if app is already installed
   * @private
   */
  _checkInstalled() {
    // Check display mode
    const isStandalone = window.matchMedia("(display-mode: standalone)").matches;
    const isFullscreen = window.matchMedia("(display-mode: fullscreen)").matches;
    const isMinimalUi = window.matchMedia("(display-mode: minimal-ui)").matches;

    // Check iOS standalone mode
    const isIOSStandalone = window.navigator.standalone === true;

    this.isInstalled = isStandalone || isFullscreen || isMinimalUi || isIOSStandalone;

    if (this.isInstalled) {
      this._log("App is already installed");
    }
  }

  /**
   * Show the install button
   * @private
   */
  _showInstallButton() {
    if (this.isInstalled || !this.deferredPrompt) return;

    // Create install button if it doesn't exist
    if (!this.installButton) {
      this.installButton = this._createInstallButton();
    }

    this.installButton.classList.add("visible");
    this._log("Install button shown");
  }

  /**
   * Hide the install button
   * @private
   */
  _hideInstallButton() {
    if (this.installButton) {
      this.installButton.classList.remove("visible");
    }
  }

  /**
   * Create the install button element
   * @private
   * @returns {HTMLElement}
   */
  _createInstallButton() {
    const button = document.createElement("button");
    button.className = "pwa-install-button";
    button.setAttribute("aria-label", "Install Alfred as an app");
    button.innerHTML = `
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 2L2 7l10 5 10-5-10-5z"/>
        <path d="M2 17l10 5 10-5"/>
        <path d="M2 12l10 5 10-5"/>
      </svg>
      <span>Install App</span>
    `;

    button.addEventListener("click", () => this._triggerInstall());

    // Insert into header or body
    const header = document.querySelector("header, .header, #header");
    if (header) {
      header.appendChild(button);
    } else {
      document.body.appendChild(button);
    }

    return button;
  }

  /**
   * Trigger the install prompt
   * @private
   */
  async _triggerInstall() {
    if (!this.deferredPrompt) {
      this._log("No deferred prompt available");
      return;
    }

    // Show the install prompt
    this.deferredPrompt.prompt();

    // Wait for user response
    const { outcome } = await this.deferredPrompt.userChoice;

    if (outcome === "accepted") {
      this._log("User accepted install");
    } else {
      this._log("User dismissed install");
    }

    // Clear the deferred prompt
    this.deferredPrompt = null;
    this._hideInstallButton();
  }

  /**
   * Check if install is available
   * @returns {boolean}
   */
  canInstall() {
    return !this.isInstalled && !!this.deferredPrompt;
  }

  /**
   * Get install status
   * @returns {boolean}
   */
  getIsInstalled() {
    return this.isInstalled;
  }

  /**
   * Manually trigger install (for command palette integration)
   */
  async install() {
    await this._triggerInstall();
  }

  /**
   * Log helper
   * @private
   */
  _log(...args) {
    if (window.APP_CONFIG?.debug) {
      console.log("[InstallPrompt]", ...args);
    }
  }
}

// Create singleton instance
let installManager = null;

/**
 * Initialize the install prompt manager
 * @returns {InstallPromptManager}
 */
export function initInstallPrompt() {
  if (!installManager) {
    installManager = new InstallPromptManager();
  }
  return installManager;
}

/**
 * Get the install prompt manager instance
 * @returns {InstallPromptManager|null}
 */
export function getInstallPrompt() {
  return installManager;
}

export { InstallPromptManager };
export default InstallPromptManager;
