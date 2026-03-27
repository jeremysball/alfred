/**
 * Clipboard Handler
 *
 * Handles paste events for uploading images from clipboard.
 *
 * Usage:
 *   ClipboardHandler.attach();
 *   ClipboardHandler.onPaste = (files) => uploadFiles(files);
 */

const ClipboardHandler = {
  // Callback for paste events
  onPaste: null,
  isAttached: false,

  /**
   * Attach paste listener to document
   */
  attach() {
    if (this.isAttached) return;

    document.addEventListener('paste', this._handlePaste.bind(this));
    this.isAttached = true;

    console.log('ClipboardHandler: attached');
  },

  /**
   * Detach paste listener
   */
  detach() {
    if (!this.isAttached) return;

    document.removeEventListener('paste', this._handlePaste.bind(this));
    this.isAttached = false;

    console.log('ClipboardHandler: detached');
  },

  /**
   * Handle paste event
   * @param {ClipboardEvent} event
   */
  _handlePaste(event) {
    // Only handle if not in an input/textarea (unless it's the chat input)
    const target = event.target;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA';
    const isChatInput = target.id === 'chat-input' || target.closest('#chat-input');

    if (isInput && !isChatInput) {
      return; // Let normal paste happen
    }

    const files = this._extractFiles(event);

    if (files.length > 0) {
      console.log('ClipboardHandler: files pasted:', files.length);
      event.preventDefault();

      if (typeof this.onPaste === 'function') {
        this.onPaste(files, event);
      }
    }
  },

  /**
   * Extract files from clipboard
   * @param {ClipboardEvent} event
   * @returns {File[]}
   */
  _extractFiles(event) {
    const files = [];
    const items = event.clipboardData?.items;

    if (!items) return files;

    for (let i = 0; i < items.length; i++) {
      const item = items[i];

      // Handle image files
      if (item.kind === 'file' && item.type.startsWith('image/')) {
        const file = item.getAsFile();
        if (file) {
          // Generate a better filename for pasted images
          const extension = file.type === 'image/png' ? 'png' : 'jpg';
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const renamedFile = new File([file], `pasted-image-${timestamp}.${extension}`, {
            type: file.type,
          });
          files.push(renamedFile);
        }
      }
    }

    return files;
  },

  /**
   * Check if clipboard has image data
   * @returns {boolean}
   */
  async hasImage() {
    try {
      const items = await navigator.clipboard.read();
      for (const item of items) {
        for (const type of item.types) {
          if (type.startsWith('image/')) {
            return true;
          }
        }
      }
    } catch (e) {
      // Clipboard API not available or permission denied
    }
    return false;
  },
};

// Export for ESM and browser usage
export { ClipboardHandler };

if (typeof window !== 'undefined') {
  window.ClipboardHandler = ClipboardHandler;
}
