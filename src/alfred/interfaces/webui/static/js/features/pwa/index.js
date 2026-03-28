/**
 * PWA Features Module
 * Progressive Web App functionality including install prompts and offline support
 */

import { getThemeManager, initAutoTheme, ThemeManager } from "../theme/auto-theme.js";
import { getInstallPrompt, InstallPromptManager, initInstallPrompt } from "./install-prompt.js";
import {
  handleShareTarget,
  hasShareData,
  initShareTarget,
  parseShareFromURL,
} from "./share-target.js";

/**
 * Initialize all PWA features
 * @param {Object} options - Configuration options
 * @param {boolean} options.debug - Enable debug logging
 * @param {Function} options.getComposer - Function returning composer element
 */
export function initPWA(options = {}) {
  // Initialize install prompt
  const installManager = initInstallPrompt();

  // Initialize auto-theme
  const themeManager = initAutoTheme();

  // Initialize share target
  initShareTarget({ getComposer: options.getComposer });

  if (options.debug) {
    console.log("[PWA] Initialized", {
      canInstall: installManager.canInstall(),
      isInstalled: installManager.getIsInstalled(),
      theme: themeManager.getEffectiveTheme(),
    });
  }

  return {
    installManager,
    themeManager,
  };
}

// Export individual components
export {
  getInstallPrompt,
  getThemeManager,
  handleShareTarget,
  hasShareData,
  InstallPromptManager,
  initAutoTheme,
  initInstallPrompt,
  initShareTarget,
  parseShareFromURL,
  ThemeManager,
};

// Default export
export default {
  initPWA,
  initInstallPrompt,
  getInstallPrompt,
  InstallPromptManager,
  initAutoTheme,
  getThemeManager,
  ThemeManager,
  initShareTarget,
  handleShareTarget,
  hasShareData,
  parseShareFromURL,
};
