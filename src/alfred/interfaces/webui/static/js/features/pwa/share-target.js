/**
 * Share Target Receiver
 * Handles incoming content shared from other apps via Web Share Target API
 */

/**
 * Parse share data from URL params
 * @returns {Object|null} Share data or null if no share
 */
export function parseShareFromURL() {
  const params = new URLSearchParams(window.location.search);
  const shareParam = params.get('share');
  
  if (!shareParam) return null;
  
  // Parse the share query string
  const shareParams = new URLSearchParams(shareParam);
  
  return {
    title: shareParams.get('title') || '',
    text: shareParams.get('text') || '',
    url: shareParams.get('url') || '',
  };
}

/**
 * Check if there's pending share data
 * @returns {boolean}
 */
export function hasShareData() {
  return !!parseShareFromURL();
}

/**
 * Format shared content for composer
 * @param {Object} shareData
 * @returns {string}
 */
function formatShareContent(shareData) {
  const parts = [];
  
  if (shareData.title) {
    parts.push(`**${shareData.title}**`);
  }
  
  if (shareData.text) {
    parts.push(shareData.text);
  }
  
  if (shareData.url) {
    parts.push(shareData.url);
  }
  
  return parts.join('\n\n');
}

/**
 * Handle incoming share data
 * Populates the composer with shared content
 * @param {Function} getComposerFn - Function that returns composer element
 * @returns {boolean} True if share was handled
 */
export function handleShareTarget(getComposerFn) {
  const shareData = parseShareFromURL();
  
  if (!shareData) return false;
  
  // Wait for composer to be available
  const tryPopulate = () => {
    const composer = getComposerFn ? getComposerFn() : document.getElementById('user-input');
    
    if (!composer) {
      // Retry after a short delay
      setTimeout(tryPopulate, 100);
      return;
    }
    
    // Populate composer
    const content = formatShareContent(shareData);
    
    if (composer.tagName === 'TEXTAREA' || composer.tagName === 'INPUT') {
      composer.value = content;
    } else {
      // ContentEditable
      composer.textContent = content;
    }
    
    // Focus and trigger input event
    composer.focus();
    composer.dispatchEvent(new Event('input', { bubbles: true }));
    
    // Clear URL params without reloading
    if (window.history.replaceState) {
      const url = new URL(window.location.href);
      url.searchParams.delete('share');
      window.history.replaceState({}, document.title, url.toString());
    }
    
    console.log('[ShareTarget] Populated composer with shared content');
  };
  
  // Start trying
  tryPopulate();
  
  return true;
}

/**
 * Initialize share target handling
 * @param {Object} options
 * @param {Function} options.getComposer - Function returning composer element
 */
export function initShareTarget(options = {}) {
  // Check for share data on load
  if (hasShareData()) {
    handleShareTarget(options.getComposer);
  }
  
  // Also check on URL changes (for SPA navigation)
  window.addEventListener('popstate', () => {
    if (hasShareData()) {
      handleShareTarget(options.getComposer);
    }
  });
}

export default {
  parseShareFromURL,
  hasShareData,
  handleShareTarget,
  initShareTarget,
};
