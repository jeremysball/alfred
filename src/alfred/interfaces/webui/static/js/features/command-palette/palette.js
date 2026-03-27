/**
 * Command Palette UI Component
 *
 * Modal overlay with search input and results list.
 * Handles keyboard navigation and command execution.
 */

// Import dependencies (works in both module and script contexts)
const { search } = typeof require !== 'undefined'
  ? require('./fuzzy-search.js')
  : (window.FuzzySearch || {});

const { getAll } = typeof require !== 'undefined'
  ? require('./commands.js')
  : (window.CommandRegistry || {});

/**
 * @typedef {Object} PaletteConfig
 * @property {string} [containerId='command-palette'] - ID for palette container
 * @property {string} [placeholder='Type a command...'] - Search input placeholder
 */

class CommandPalette {
  /**
   * @param {PaletteConfig} [config]
   */
  constructor(config = {}) {
    this.config = {
      containerId: config.containerId || 'command-palette',
      placeholder: config.placeholder || 'Type a command...'
    };

    this.isOpen = false;
    this.selectedIndex = 0;
    this.results = [];
    this.container = null;
    this.input = null;
    this.resultsList = null;
    this.backdrop = null;

    // Bind methods
    this.open = this.open.bind(this);
    this.close = this.close.bind(this);
    this.handleKeydown = this.handleKeydown.bind(this);
    this.handleInput = this.handleInput.bind(this);
    this.handleResultClick = this.handleResultClick.bind(this);
    this.executeSelected = this.executeSelected.bind(this);

    // Initialize
    this.createDOM();
    this.attachGlobalListeners();
  }

  /**
   * Create the palette DOM structure
   * @private
   */
  createDOM() {
    // Container
    this.container = document.createElement('div');
    this.container.id = this.config.containerId;
    this.container.className = 'command-palette';
    this.container.setAttribute('role', 'dialog');
    this.container.setAttribute('aria-modal', 'true');
    this.container.setAttribute('aria-label', 'Command Palette');
    this.container.style.display = 'none';

    // Backdrop
    this.backdrop = document.createElement('div');
    this.backdrop.className = 'command-palette-backdrop';
    this.backdrop.addEventListener('click', this.close);

    // Modal content
    const modal = document.createElement('div');
    modal.className = 'command-palette-modal';

    // Search input
    this.input = document.createElement('input');
    this.input.type = 'text';
    this.input.className = 'command-palette-input';
    this.input.placeholder = this.config.placeholder;
    this.input.setAttribute('aria-label', 'Search commands');
    this.input.setAttribute('autocomplete', 'off');
    this.input.setAttribute('autocorrect', 'off');
    this.input.setAttribute('autocapitalize', 'off');
    this.input.setAttribute('spellcheck', 'false');
    this.input.addEventListener('input', this.handleInput);

    // Results container
    const resultsContainer = document.createElement('div');
    resultsContainer.className = 'command-palette-results-container';

    this.resultsList = document.createElement('ul');
    this.resultsList.className = 'command-palette-results';
    this.resultsList.setAttribute('role', 'listbox');
    this.resultsList.setAttribute('aria-label', 'Command results');

    resultsContainer.appendChild(this.resultsList);

    // Assemble
    modal.appendChild(this.input);
    modal.appendChild(resultsContainer);
    this.container.appendChild(this.backdrop);
    this.container.appendChild(modal);

    // Add to document
    document.body.appendChild(this.container);
  }

  /**
   * Attach global keyboard listeners
   * @private
   */
  attachGlobalListeners() {
    document.addEventListener('keydown', (e) => {
      // Ctrl+K or Cmd+K to open
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        this.open();
      }
    });
  }

  /**
   * Open the command palette
   */
  open() {
    if (this.isOpen) return;

    this.isOpen = true;
    this.container.style.display = 'block';
    this.input.value = '';
    this.input.focus();
    this.selectedIndex = 0;

    // Initial render with all commands
    this.performSearch('');

    // Add document keydown listener for this instance
    document.addEventListener('keydown', this.handleKeydown);

    // Dispatch event
    window.dispatchEvent(new CustomEvent('command-palette:open'));
  }

  /**
   * Close the command palette
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;
    this.container.style.display = 'none';
    this.input.blur();

    // Remove document keydown listener
    document.removeEventListener('keydown', this.handleKeydown);

    // Dispatch event
    window.dispatchEvent(new CustomEvent('command-palette:close'));
  }

  /**
   * Handle keyboard navigation
   * @param {KeyboardEvent} e
   * @private
   */
  handleKeydown(e) {
    if (!this.isOpen) return;

    switch (e.key) {
      case 'Escape':
        e.preventDefault();
        this.close();
        break;

      case 'ArrowDown':
        e.preventDefault();
        this.moveSelection(1);
        break;

      case 'ArrowUp':
        e.preventDefault();
        this.moveSelection(-1);
        break;

      case 'Enter':
        e.preventDefault();
        this.executeSelected();
        break;

      case 'Tab':
        // Allow tab to cycle between input and results
        if (e.shiftKey && document.activeElement === this.input) {
          e.preventDefault();
          this.focusResults();
        } else if (!e.shiftKey && document.activeElement === this.input) {
          e.preventDefault();
          this.focusResults();
        }
        break;
    }
  }

  /**
   * Handle input changes
   * @param {InputEvent} e
   * @private
   */
  handleInput(e) {
    this.performSearch(e.target.value);
  }

  /**
   * Handle result item click
   * @param {MouseEvent} e
   * @private
   */
  handleResultClick(e) {
    const item = e.target.closest('.command-palette-result');
    if (item) {
      const index = parseInt(item.dataset.index, 10);
      this.executeCommand(index);
    }
  }

  /**
   * Perform search and update results
   * @param {string} query
   * @private
   */
  performSearch(query) {
    const commands = getAll ? getAll() : [];
    this.results = search ? search(query, commands, { limit: 10 }) : [];
    this.selectedIndex = 0;
    this.renderResults();
  }

  /**
   * Render search results
   * @private
   */
  renderResults() {
    this.resultsList.innerHTML = '';

    if (this.results.length === 0) {
      const empty = document.createElement('li');
      empty.className = 'command-palette-empty';
      empty.textContent = 'No commands found';
      this.resultsList.appendChild(empty);
      return;
    }

    this.results.forEach((result, index) => {
      const item = document.createElement('li');
      item.className = 'command-palette-result';
      item.dataset.index = index;
      item.setAttribute('role', 'option');
      item.setAttribute('aria-selected', index === this.selectedIndex ? 'true' : 'false');

      if (index === this.selectedIndex) {
        item.classList.add('selected');
      }

      // Build highlighted title
      const title = this.highlightText(
        result.command.title,
        result.highlightIndices
      );

      // Title element
      const titleEl = document.createElement('span');
      titleEl.className = 'command-palette-result-title';
      titleEl.innerHTML = title;

      // Shortcut element (if present)
      if (result.command.shortcut) {
        const shortcutEl = document.createElement('kbd');
        shortcutEl.className = 'command-palette-result-shortcut';
        shortcutEl.textContent = result.command.shortcut;
        item.appendChild(shortcutEl);
      }

      item.appendChild(titleEl);
      item.addEventListener('click', this.handleResultClick);

      this.resultsList.appendChild(item);
    });
  }

  /**
   * Highlight matched characters in text
   * @param {string} text
   * @param {number[]} indices
   * @returns {string}
   * @private
   */
  highlightText(text, indices) {
    if (!indices || indices.length === 0) return text;

    let result = '';
    let lastIndex = 0;

    // Sort indices to process in order
    const sortedIndices = [...indices].sort((a, b) => a - b);

    for (const index of sortedIndices) {
      result += text.slice(lastIndex, index);
      result += `<mark>${text[index]}</mark>`;
      lastIndex = index + 1;
    }

    result += text.slice(lastIndex);
    return result;
  }

  /**
   * Move selection up or down
   * @param {number} delta - 1 for down, -1 for up
   * @private
   */
  moveSelection(delta) {
    if (this.results.length === 0) return;

    this.selectedIndex += delta;

    // Wrap around
    if (this.selectedIndex < 0) {
      this.selectedIndex = this.results.length - 1;
    } else if (this.selectedIndex >= this.results.length) {
      this.selectedIndex = 0;
    }

    this.renderResults();
    this.scrollSelectedIntoView();
  }

  /**
   * Scroll selected item into view
   * @private
   */
  scrollSelectedIntoView() {
    const selected = this.resultsList.querySelector('.selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  }

  /**
   * Execute the currently selected command
   * @private
   */
  executeSelected() {
    this.executeCommand(this.selectedIndex);
  }

  /**
   * Execute a command by index
   * @param {number} index
   * @private
   */
  executeCommand(index) {
    if (index < 0 || index >= this.results.length) return;

    const result = this.results[index];
    if (result && result.command && result.command.action) {
      this.close();
      result.command.action();

      // Dispatch event
      window.dispatchEvent(new CustomEvent('command-palette:execute', {
        detail: { command: result.command }
      }));
    }
  }

  /**
   * Focus on results list for tab navigation
   * @private
   */
  focusResults() {
    const firstResult = this.resultsList.querySelector('.command-palette-result');
    if (firstResult) {
      firstResult.focus();
    }
  }

  /**
   * Destroy the palette and clean up
   */
  destroy() {
    this.close();
    if (this.container && this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }
}

// Export for both CommonJS and ES modules
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { CommandPalette };
}

if (typeof window !== 'undefined') {
  window.CommandPalette = CommandPalette;
}
