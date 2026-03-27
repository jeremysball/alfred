/**
 * Visual Feedback Manager
 *
 * Manages drop zone visual feedback.
 *
 * Usage:
 *   const visual = new DropZoneVisual(containerElement);
 *   visual.show();
 *   visual.hide();
 */

class DropZoneVisual {
  constructor(containerElement) {
    this.container = containerElement;
    this.overlay = null;
    this.isVisible = false;

    this._createOverlay();
  }

  /**
   * Create the overlay element
   */
  _createOverlay() {
    // Add drag-drop-zone class to container
    this.container.classList.add('drag-drop-zone');

    // Create overlay element
    this.overlay = document.createElement('div');
    this.overlay.className = 'drag-drop-overlay';
    this.overlay.innerHTML = `
      <div class="drag-drop-icon">📎</div>
      <div class="drag-drop-text">Drop files here</div>
      <div class="drag-drop-subtext">Images, text files, code</div>
      <div class="drag-drop-hint">Max 10MB per file</div>
    `;

    // Append overlay to container
    this.container.appendChild(this.overlay);
  }

  /**
   * Show the drop zone
   */
  show() {
    if (this.isVisible) return;

    this.container.classList.add('drag-active');
    this.isVisible = true;
  }

  /**
   * Hide the drop zone
   */
  hide() {
    if (!this.isVisible) return;

    this.container.classList.remove('drag-active');
    this.isVisible = false;
  }

  /**
   * Destroy and clean up
   */
  destroy() {
    this.hide();

    if (this.overlay && this.overlay.parentNode) {
      this.overlay.parentNode.removeChild(this.overlay);
    }

    this.container.classList.remove('drag-drop-zone');
    this.overlay = null;
    this.container = null;
  }

  /**
   * Update the overlay text
   * @param {string} text - Main text
   * @param {string} subtext - Subtext (optional)
   */
  setText(text, subtext = null) {
    if (!this.overlay) return;

    const textEl = this.overlay.querySelector('.drag-drop-text');
    if (textEl) textEl.textContent = text;

    if (subtext) {
      const subtextEl = this.overlay.querySelector('.drag-drop-subtext');
      if (subtextEl) subtextEl.textContent = subtext;
    }
  }

  /**
   * Show error state
   * @param {string} errorMessage
   */
  showError(errorMessage) {
    if (!this.overlay) return;

    this.overlay.style.borderColor = '#f85149';
    this.setText('❌ Cannot upload', errorMessage);

    // Reset after 2 seconds
    setTimeout(() => {
      if (this.overlay) {
        this.overlay.style.borderColor = '';
        this.setText('Drop files here', 'Images, text files, code');
      }
    }, 2000);
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DropZoneVisual };
}

if (typeof window !== 'undefined') {
  window.DropZoneVisual = DropZoneVisual;
}
