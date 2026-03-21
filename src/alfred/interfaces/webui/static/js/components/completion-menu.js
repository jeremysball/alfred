/**
 * Completion Menu Web Component
 *
 * Usage:
 * <completion-menu
 *   items='[{"value": "/new", "description": "Start new session"}]'
 *   selected-index="-1"
 *   visible="false">
 * </completion-menu>
 *
 * Events:
 *   - select: Fired when an item is selected (detail: { value, description })
 *   - dismiss: Fired when menu should be dismissed
 */
class CompletionMenu extends HTMLElement {
  constructor() {
    super();
    this._items = [];
    this._selectedIndex = -1;
    this._visible = false;
    this._filter = '';
  }

  static get observedAttributes() {
    return ['items', 'selected-index', 'visible'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue === newValue) return;

    switch (name) {
      case 'items':
        try {
          this._items = JSON.parse(newValue || '[]');
        } catch {
          this._items = [];
        }
        break;
      case 'selected-index':
        this._selectedIndex = parseInt(newValue, 10) || -1;
        break;
      case 'visible':
        this._visible = newValue === 'true';
        break;
    }
    this._render();
  }

  connectedCallback() {
    this._render();
    this.addEventListener('click', this._handleClick);
  }

  disconnectedCallback() {
    this.removeEventListener('click', this._handleClick);
  }

  _handleClick = (e) => {
    const item = e.target.closest('.completion-item');
    if (item) {
      const index = parseInt(item.dataset.index, 10);
      this.selectItem(index);
    }
  };

  _render() {
    if (!this._visible || this._items.length === 0) {
      this.innerHTML = '';
      this.style.display = 'none';
      return;
    }

    this.style.display = 'block';

    const filteredItems = this._filter
      ? this._items.filter(item =>
          item.value.toLowerCase().includes(this._filter.toLowerCase()) ||
          (item.description && item.description.toLowerCase().includes(this._filter.toLowerCase()))
        )
      : this._items;

    const itemsHtml = filteredItems.map((item, index) => `
      <div
        class="completion-item ${index === this._selectedIndex ? 'selected' : ''}"
        data-index="${index}"
      >
        <span class="completion-value">${this._escapeHtml(item.value)}</span>
        ${item.description ? `<span class="completion-description">${this._escapeHtml(item.description)}</span>` : ''}
      </div>
    `).join('');

    this.innerHTML = `
      <div class="completion-menu">
        ${itemsHtml}
      </div>
    `;
  }

  _escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Public API
  show() {
    this._visible = true;
    this.setAttribute('visible', 'true');
  }

  hide() {
    this._visible = false;
    this.setAttribute('visible', 'false');
    this._selectedIndex = -1;
    this._filter = '';
  }

  setItems(items) {
    this._items = items;
    this.setAttribute('items', JSON.stringify(items));
  }

  setFilter(filter) {
    this._filter = filter;
    this._render();
  }

  selectNext() {
    const filteredCount = this._getFilteredCount();
    this._selectedIndex = (this._selectedIndex + 1) % filteredCount;
    this.setAttribute('selected-index', this._selectedIndex.toString());
    this._scrollToSelected();
  }

  selectPrevious() {
    const filteredCount = this._getFilteredCount();
    this._selectedIndex = this._selectedIndex <= 0
      ? filteredCount - 1
      : this._selectedIndex - 1;
    this.setAttribute('selected-index', this._selectedIndex.toString());
    this._scrollToSelected();
  }

  selectItem(index) {
    const filteredItems = this._getFilteredItems();
    if (index >= 0 && index < filteredItems.length) {
      this.dispatchEvent(new CustomEvent('select', {
        detail: filteredItems[index],
        bubbles: true
      }));
      this.hide();
    }
  }

  selectCurrent() {
    const filteredCount = this._getFilteredCount();
    if (filteredCount === 0) return;

    // If no selection, default to first item
    const index = this._selectedIndex >= 0 ? this._selectedIndex : 0;
    this.selectItem(index);
  }

  _getFilteredItems() {
    if (!this._filter) return this._items;
    return this._items.filter(item =>
      item.value.toLowerCase().includes(this._filter.toLowerCase()) ||
      (item.description && item.description.toLowerCase().includes(this._filter.toLowerCase()))
    );
  }

  _getFilteredCount() {
    return this._getFilteredItems().length;
  }

  _scrollToSelected() {
    const selected = this.querySelector('.completion-item.selected');
    if (selected) {
      selected.scrollIntoView({ block: 'nearest' });
    }
  }

  isVisible() {
    return this._visible;
  }
}

// Register the custom element
customElements.define('completion-menu', CompletionMenu);
