/**
 * Help Modal for Keyboard Shortcuts
 *
 * Displays all registered shortcuts organized by category.
 * Open with `?` key.
 */

// Import from shortcuts module (works with both CommonJS and browser)
const { getAll, formatShortcut } = typeof require !== 'undefined'
  ? require('./shortcuts.js')
  : (window.ShortcutRegistry || {});

class HelpModal {
  constructor() {
    this.isOpen = false;
    this.container = null;
    this.backdrop = null;

    this.handleKeydown = this.handleKeydown.bind(this);
    this.close = this.close.bind(this);

    this.createDOM();
  }

  /**
   * Create the help modal DOM structure
   * @private
   */
  createDOM() {
    // Container
    this.container = document.createElement('div');
    this.container.className = 'keyboard-help-modal';
    this.container.setAttribute('role', 'dialog');
    this.container.setAttribute('aria-modal', 'true');
    this.container.setAttribute('aria-label', 'Keyboard Shortcuts');
    this.container.style.display = 'none';

    // Backdrop
    this.backdrop = document.createElement('div');
    this.backdrop.className = 'keyboard-help-backdrop';
    this.backdrop.addEventListener('click', this.close);

    // Modal content
    const modal = document.createElement('div');
    modal.className = 'keyboard-help-content';

    // Header
    const header = document.createElement('div');
    header.className = 'keyboard-help-header';
    header.innerHTML = `
      <h2>Keyboard Shortcuts</h2>
      <button class="keyboard-help-close" aria-label="Close">&times;</button>
    `;
    header.querySelector('.keyboard-help-close').addEventListener('click', this.close);

    // Content area (populated on show)
    this.contentArea = document.createElement('div');
    this.contentArea.className = 'keyboard-help-body';

    // Footer
    const footer = document.createElement('div');
    footer.className = 'keyboard-help-footer';
    footer.textContent = 'Press ? to toggle this help';

    // Assemble
    modal.appendChild(header);
    modal.appendChild(this.contentArea);
    modal.appendChild(footer);
    this.container.appendChild(this.backdrop);
    this.container.appendChild(modal);

    // Add to document
    document.body.appendChild(this.container);
  }

  /**
   * Render shortcuts organized by category
   * @private
   */
  renderShortcuts() {
    const grouped = getAll ? getAll() : {};
    this.contentArea.innerHTML = '';

    const categories = Object.keys(grouped).sort();

    if (categories.length === 0) {
      this.contentArea.innerHTML = '<p class="keyboard-help-empty">No shortcuts registered</p>';
      return;
    }

    categories.forEach(category => {
      const section = document.createElement('section');
      section.className = 'keyboard-help-section';

      const heading = document.createElement('h3');
      heading.className = 'keyboard-help-category';
      heading.textContent = category;
      section.appendChild(heading);

      const list = document.createElement('ul');
      list.className = 'keyboard-help-list';

      // Sort shortcuts by key for consistent ordering
      const shortcuts = grouped[category].sort((a, b) => {
        return formatShortcut(a).localeCompare(formatShortcut(b));
      });

      shortcuts.forEach(shortcut => {
        const item = document.createElement('li');
        item.className = 'keyboard-help-item';

        const keyEl = document.createElement('kbd');
        keyEl.className = 'keyboard-help-key';
        keyEl.textContent = formatShortcut(shortcut);

        const descEl = document.createElement('span');
        descEl.className = 'keyboard-help-description';
        descEl.textContent = shortcut.description;

        item.appendChild(keyEl);
        item.appendChild(descEl);
        list.appendChild(item);
      });

      section.appendChild(list);
      this.contentArea.appendChild(section);
    });
  }

  /**
   * Show the help modal
   */
  show() {
    if (this.isOpen) return;

    this.isOpen = true;
    this.renderShortcuts();
    this.container.style.display = 'block';

    // Add escape listener
    document.addEventListener('keydown', this.handleKeydown);

    // Focus management - focus the close button
    const closeBtn = this.container.querySelector('.keyboard-help-close');
    if (closeBtn) {
      closeBtn.focus();
    }

    window.dispatchEvent(new CustomEvent('keyboard-help:open'));
  }

  /**
   * Close the help modal
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this.container.style.display = 'none';

    // Remove escape listener
    document.removeEventListener('keydown', this.handleKeydown);

    window.dispatchEvent(new CustomEvent('keyboard-help:close'));
  }

  /**
   * Toggle the help modal
   */
  toggle() {
    if (this.isOpen) {
      this.close();
    } else {
      this.show();
    }
  }

  /**
   * Handle keyboard events
   * @param {KeyboardEvent} e
   * @private
   */
  handleKeydown(e) {
    if (e.key === 'Escape') {
      e.preventDefault();
      this.close();
    }
  }

  /**
   * Destroy the modal and clean up
   */
  destroy() {
    this.close();
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }
}

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { HelpModal };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.HelpModal = HelpModal;
}
