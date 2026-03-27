/**
 * SearchOverlay Component
 * Milestone 9 Phase 1: In-Conversation Search (Ctrl+F)
 *
 * Provides in-conversation search using window.find() API
 * Features: case-insensitive search, match counter, keyboard navigation
 */

/**
 * SearchOverlay - Singleton search component for in-conversation search
 */
class SearchOverlay {
  /**
   * Get singleton instance
   * @returns {SearchOverlay}
   */
  static getInstance() {
    if (!SearchOverlay._instance) {
      SearchOverlay._instance = new SearchOverlay({
        onSearch: (query) => {
          SearchOverlay._instance.performSearch(query);
        },
        onNavigate: (direction) => {
          SearchOverlay._instance.navigate(direction);
        },
        onClose: () => {
          SearchOverlay._instance.close();
        }
      });
    }
    return SearchOverlay._instance;
  }

  /**
   * @param {Object} options - Configuration options
   * @param {Function} options.onSearch - Callback when search query changes
   * @param {Function} options.onNavigate - Callback for navigation (next/prev)
   * @param {Function} options.onClose - Callback when overlay closes
   */
  constructor(options = {}) {
    // Singleton guard (allow internal recreation for testing)
    if (SearchOverlay._instance && !options._allowRecreate) {
      return SearchOverlay._instance;
    }

    this.options = options;
    this.element = null;
    this.searchInput = null;
    this.matchCounter = null;
    this.isOpen = false;
    this.currentQuery = '';
    this.currentMatch = 0;
    this.totalMatches = 0;

    // Bind methods
    this.handleKeydown = this.handleKeydown.bind(this);
    this.handleSearchInput = this.handleSearchInput.bind(this);
  }

  /**
   * Open the search overlay
   */
  open() {
    if (this.isOpen) {
      this.searchInput?.focus();
      return;
    }

    this.render();
    this.attachEvents();
    this.isOpen = true;
    this.searchInput?.focus();
    // Note: select() may not be available in all environments (tests)
    if (this.searchInput && typeof this.searchInput.select === 'function') {
      this.searchInput.select();
    }
  }

  /**
   * Close the search overlay
   */
  close() {
    if (!this.isOpen) return;

    this.detachEvents();
    this.destroy();
    this.isOpen = false;
    this.currentQuery = '';
    this.currentMatch = 0;
    this.totalMatches = 0;

    if (this.options.onClose) {
      this.options.onClose();
    }
  }

  /**
   * Render the overlay DOM elements
   */
  render() {
    // Create overlay container
    this.element = document.createElement('div');
    this.element.className = 'search-overlay';
    this.element.setAttribute('role', 'search');
    this.element.setAttribute('aria-label', 'Search in conversation');

    // Create search input
    this.searchInput = document.createElement('input');
    this.searchInput.type = 'text';
    this.searchInput.className = 'search-input';
    this.searchInput.placeholder = 'Search...';
    this.searchInput.setAttribute('aria-label', 'Search query');

    // Create navigation buttons container
    const navButtons = document.createElement('div');
    navButtons.className = 'search-nav-buttons';

    // Previous button
    this.prevButton = document.createElement('button');
    this.prevButton.className = 'search-nav-btn search-prev-btn';
    this.prevButton.innerHTML = '↑';
    this.prevButton.setAttribute('aria-label', 'Previous match');
    this.prevButton.addEventListener('click', () => this.navigate('previous'));

    // Next button
    this.nextButton = document.createElement('button');
    this.nextButton.className = 'search-nav-btn search-next-btn';
    this.nextButton.innerHTML = '↓';
    this.nextButton.setAttribute('aria-label', 'Next match');
    this.nextButton.addEventListener('click', () => this.navigate('next'));

    navButtons.appendChild(this.prevButton);
    navButtons.appendChild(this.nextButton);

    // Create match counter
    this.matchCounter = document.createElement('span');
    this.matchCounter.className = 'search-match-counter';
    this.matchCounter.textContent = '';
    this.matchCounter.setAttribute('aria-live', 'polite');

    // Create close button
    this.closeButton = document.createElement('button');
    this.closeButton.className = 'search-close-btn';
    this.closeButton.innerHTML = '×';
    this.closeButton.setAttribute('aria-label', 'Close search');
    this.closeButton.addEventListener('click', () => this.close());

    // Assemble overlay
    this.element.appendChild(this.searchInput);
    this.element.appendChild(navButtons);
    this.element.appendChild(this.matchCounter);
    this.element.appendChild(this.closeButton);

    // Add to DOM
    document.body.appendChild(this.element);
  }

  /**
   * Destroy overlay DOM elements
   */
  destroy() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = null;
    this.searchInput = null;
    this.matchCounter = null;
    this.prevButton = null;
    this.nextButton = null;
    this.closeButton = null;
  }

  /**
   * Attach event listeners
   */
  attachEvents() {
    // Keyboard events (global for Escape, local for others)
    document.addEventListener('keydown', this.handleKeydown);

    // Search input
    this.searchInput?.addEventListener('input', this.handleSearchInput);
  }

  /**
   * Detach event listeners
   */
  detachEvents() {
    document.removeEventListener('keydown', this.handleKeydown);
    this.searchInput?.removeEventListener('input', this.handleSearchInput);
  }

  /**
   * Handle keyboard events
   * @param {KeyboardEvent} event
   */
  handleKeydown(event) {
    if (!this.isOpen) return;

    switch (event.key) {
      case 'Escape':
        event.preventDefault();
        this.close();
        break;
      case 'Enter':
        event.preventDefault();
        if (event.shiftKey) {
          this.navigate('previous');
        } else {
          this.navigate('next');
        }
        break;
    }
  }

  /**
   * Handle search input changes
   * @param {InputEvent} event
   */
  handleSearchInput(event) {
    const query = event.target.value;
    this.currentQuery = query;

    if (this.options.onSearch) {
      this.options.onSearch(query);
    }

    // Perform search and update counter
    this.performSearch(query);
  }

  /**
   * Perform search using window.find()
   * @param {string} query - Search query
   */
  performSearch(query) {
    if (!query) {
      this.updateMatchCounter(0, 0);
      return;
    }

    // Clear previous selection
    window.getSelection()?.removeAllRanges();

    // Use browser's native find
    // window.find(query, caseSensitive, backwards, wrapAround)
    const found = window.find(query, false, false, true);

    if (found) {
      // For MVP, we can't easily count total matches with window.find()
      // Just show that we found something
      this.currentMatch = 1;
      this.totalMatches = 1; // Simplified for MVP
      this.updateMatchCounter(this.currentMatch, this.totalMatches);
    } else {
      this.currentMatch = 0;
      this.totalMatches = 0;
      this.updateMatchCounter(0, 0);
    }
  }

  /**
   * Navigate between matches
   * @param {string} direction - 'next' or 'previous'
   */
  navigate(direction) {
    if (!this.currentQuery) return;

    const backwards = direction === 'previous';

    // Use window.find to navigate
    const found = window.find(this.currentQuery, false, backwards, true);

    if (found) {
      if (direction === 'next') {
        this.currentMatch = Math.min(this.currentMatch + 1, this.totalMatches);
      } else {
        this.currentMatch = Math.max(this.currentMatch - 1, 1);
      }
      this.updateMatchCounter(this.currentMatch, this.totalMatches);
    }

    if (this.options.onNavigate) {
      this.options.onNavigate(direction);
    }
  }

  /**
   * Update match counter display
   * @param {number} current - Current match index
   * @param {number} total - Total matches
   */
  updateMatchCounter(current, total) {
    if (!this.matchCounter) return;

    if (total === 0) {
      this.matchCounter.textContent = 'No matches';
    } else {
      this.matchCounter.textContent = `${current} of ${total}`;
    }
  }
}

// Singleton instance storage
SearchOverlay._instance = null;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { SearchOverlay };
}
