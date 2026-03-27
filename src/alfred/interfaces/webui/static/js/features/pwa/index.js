/**
 * PWA Features Module
 * Progressive Web App functionality including install prompts and offline support
 */

import { initInstallPrompt, getInstallPrompt, InstallPromptManager } from './install-prompt.js';

/**
 * Initialize all PWA features
 * @param {Object} options - Configuration options
 * @param {boolean} options.debug - Enable debug logging
 */
export function initPWA(options = {}) {
  // Initialize install prompt
  const installManager = initInstallPrompt();
  
  if (options.debug) {
    console.log('[PWA] Initialized', {
      canInstall: installManager.canInstall(),
      isInstalled: installManager.getIsInstalled(),
    });
  }
  
  return {
    installManager,
  };
}

// Export individual components
export { initInstallPrompt, getInstallPrompt, InstallPromptManager };

// Default export
export default {
  initPWA,
  initInstallPrompt,
  getInstallPrompt,
  InstallPromptManager,
};
