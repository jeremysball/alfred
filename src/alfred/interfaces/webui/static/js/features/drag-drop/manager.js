/**
 * Drag-Drop Manager
 *
 * Handles drag and drop events for file upload.
 * Attaches to a DOM element and manages drop zone state.
 *
 * Usage:
 *   const manager = new DragDropManager();
 *   manager.attachToElement(document.getElementById('chat-container'));
 *
 *   // Set callbacks
 *   manager.onFilesDropped = (files) => {
 *     files.forEach(file => uploadFile(file));
 *   };
 */

class DragDropManager {
  constructor(options = {}) {
    this.targetElement = null;
    this.isDragging = false;
    this.dragCounter = 0; // Track nested dragenter/dragleave

    // Configuration
    this.options = {
      preventDefault: true,
      stopPropagation: true,
      ...options
    };

    // Callbacks (to be set by consumer)
    this.onDragEnter = null;
    this.onDragLeave = null;
    this.onFilesDropped = null;
    this.onDragOver = null;

    // Bound handlers (for proper event listener removal)
    this._handleDragEnter = this._handleDragEnter.bind(this);
    this._handleDragLeave = this._handleDragLeave.bind(this);
    this._handleDragOver = this._handleDragOver.bind(this);
    this._handleDrop = this._handleDrop.bind(this);
  }

  /**
   * Attach drag-drop handlers to a DOM element
   * @param {HTMLElement} element - The element to attach to
   */
  attachToElement(element) {
    if (!element || !(element instanceof HTMLElement)) {
      console.error('DragDropManager: Invalid element provided');
      return false;
    }

    // Detach from previous element if any
    this.detach();

    this.targetElement = element;

    // Attach listeners
    element.addEventListener('dragenter', this._handleDragEnter);
    element.addEventListener('dragleave', this._handleDragLeave);
    element.addEventListener('dragover', this._handleDragOver);
    element.addEventListener('drop', this._handleDrop);

    console.log('DragDropManager attached to element:', element);
    return true;
  }

  /**
   * Detach all event listeners
   */
  detach() {
    if (!this.targetElement) return;

    this.targetElement.removeEventListener('dragenter', this._handleDragEnter);
    this.targetElement.removeEventListener('dragleave', this._handleDragLeave);
    this.targetElement.removeEventListener('dragover', this._handleDragOver);
    this.targetElement.removeEventListener('drop', this._handleDrop);

    this.targetElement = null;
    this.isDragging = false;
    this.dragCounter = 0;

    console.log('DragDropManager detached');
  }

  /**
   * Check if files are being dragged (not just any drag)
   * @param {DragEvent} event
   * @returns {boolean}
   */
  _hasFiles(event) {
    return event.dataTransfer && event.dataTransfer.types.includes('Files');
  }

  /**
   * Handle dragenter event
   * @param {DragEvent} event
   */
  _handleDragEnter(event) {
    if (this.options.preventDefault) {
      event.preventDefault();
    }
    if (this.options.stopPropagation) {
      event.stopPropagation();
    }

    // Only handle file drags
    if (!this._hasFiles(event)) return;

    this.dragCounter++;

    if (this.dragCounter === 1) {
      this.isDragging = true;
      console.log('DragDropManager: dragenter - files detected');

      if (typeof this.onDragEnter === 'function') {
        this.onDragEnter(event);
      }
    }
  }

  /**
   * Handle dragleave event
   * @param {DragEvent} event
   */
  _handleDragLeave(event) {
    if (this.options.preventDefault) {
      event.preventDefault();
    }
    if (this.options.stopPropagation) {
      event.stopPropagation();
    }

    // Only handle file drags
    if (!this._hasFiles(event)) return;

    this.dragCounter--;

    if (this.dragCounter <= 0) {
      this.dragCounter = 0;
      this.isDragging = false;
      console.log('DragDropManager: dragleave - drop zone cleared');

      if (typeof this.onDragLeave === 'function') {
        this.onDragLeave(event);
      }
    }
  }

  /**
   * Handle dragover event
   * @param {DragEvent} event
   */
  _handleDragOver(event) {
    // Must prevent default to allow drop
    if (this.options.preventDefault) {
      event.preventDefault();
    }
    if (this.options.stopPropagation) {
      event.stopPropagation();
    }

    // Only handle file drags
    if (!this._hasFiles(event)) return;

    // Set drop effect
    if (event.dataTransfer) {
      event.dataTransfer.dropEffect = 'copy';
    }

    if (typeof this.onDragOver === 'function') {
      this.onDragOver(event);
    }
  }

  /**
   * Handle drop event
   * @param {DragEvent} event
   */
  _handleDrop(event) {
    if (this.options.preventDefault) {
      event.preventDefault();
    }
    if (this.options.stopPropagation) {
      event.stopPropagation();
    }

    // Reset state
    this.dragCounter = 0;
    this.isDragging = false;

    console.log('DragDropManager: drop event');

    // Extract files
    const files = this._extractFiles(event);

    if (files.length > 0) {
      console.log('DragDropManager: files dropped:', files.length, files.map(f => f.name));

      if (typeof this.onFilesDropped === 'function') {
        this.onFilesDropped(files, event);
      }
    } else {
      console.log('DragDropManager: no files in drop');
    }

    // Trigger dragleave callback since we're done
    if (typeof this.onDragLeave === 'function') {
      this.onDragLeave(event);
    }
  }

  /**
   * Extract files from drop event
   * @param {DragEvent} event
   * @returns {File[]}
   */
  _extractFiles(event) {
    if (!event.dataTransfer) return [];

    const files = [];
    const items = event.dataTransfer.items || event.dataTransfer.files;

    if (items) {
      // Use DataTransferItemList if available (modern browsers)
      for (let i = 0; i < items.length; i++) {
        const item = items[i];
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
    }

    return files;
  }

  /**
   * Get current drag state
   * @returns {boolean}
   */
  getIsDragging() {
    return this.isDragging;
  }

  /**
   * Destroy the manager and clean up
   */
  destroy() {
    this.detach();
    this.onDragEnter = null;
    this.onDragLeave = null;
    this.onFilesDropped = null;
    this.onDragOver = null;
  }
}

// Export for different module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { DragDropManager };
}

if (typeof window !== 'undefined') {
  window.DragDropManager = DragDropManager;
}
