/**
 * PWA Features Module
 * Progressive Web App functionality including install prompts and offline support
 */

import { initInstallPrompt, getInstallPrompt, InstallPromptManager } from './install-prompt.js';
import { initAutoTheme, getThemeManager, ThemeManager } from '../theme/auto-theme.js';
import { initShareTarget, handleShareTarget, hasShareData, parseShareFromURL } from './share-target.js';

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
    console.log('[PWA] Initialized', {
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
export { initInstallPrompt, getInstallPrompt, InstallPromptManager };
export { initAutoTheme, getThemeManager, ThemeManager };
export { initShareTarget, handleShareTarget, hasShareData, parseShareFromURL };

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
