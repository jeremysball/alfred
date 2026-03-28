/**
 * Context Menu Component
 *
 * A reusable context menu that appears on right-click or Shift+F10.
 * Supports items with icons, separators, and keyboard navigation.
 */

/**
 * @typedef {Object} MenuItem
 * @property {string} id - Unique identifier
 * @property {string} label - Display text
 * @property {string} [icon] - Icon emoji or character
 * @property {function} action - Click handler
 * @property {boolean} [disabled] - Whether item is disabled
 * @property {string} [shortcut] - Keyboard shortcut display
 */

class ContextMenu {
  constructor() {
    this.container = null;
    this.triggerElement = null;
    this.items = [];
    this.isOpen = false;
    this.selectedIndex = -1;

    this.handleKeydown = this.handleKeydown.bind(this);
    this.handleOutsideClick = this.handleOutsideClick.bind(this);
    this.close = this.close.bind(this);
  }

  /**
   * Create the menu DOM structure
   * @private
   */
  createDOM() {
    this.container = document.createElement("div");
    this.container.className = "context-menu";
    this.container.setAttribute("role", "menu");
    this.container.setAttribute("aria-label", "Context menu");
    this.container.style.display = "none";
    this.container.style.position = "fixed";
    this.container.style.zIndex = "10001";

    // Backdrop for detecting outside clicks
    this.backdrop = document.createElement("div");
    this.backdrop.className = "context-menu-backdrop";
    this.backdrop.style.cssText = `
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      z-index: 10000;
    `;

    document.body.appendChild(this.backdrop);
    document.body.appendChild(this.container);
  }

  /**
   * Show the context menu
   * @param {Object} options
   * @param {number} options.x - X coordinate
   * @param {number} options.y - Y coordinate
   * @param {MenuItem[]} options.items - Menu items
   * @param {HTMLElement} [options.triggerElement] - Element that triggered menu
   */
  show({ x, y, items, triggerElement = null }) {
    // Close any existing menu
    this.close();

    this.items = items.filter((item) => item.visible !== false);
    this.triggerElement = triggerElement;
    this.selectedIndex = -1;

    this.createDOM();
    this.render();
    this.position(x, y);

    this.container.style.display = "block";
    this.isOpen = true;

    // Add event listeners
    document.addEventListener("keydown", this.handleKeydown);
    this.backdrop.addEventListener("click", this.handleOutsideClick);

    // Focus the menu for keyboard navigation
    this.container.focus();

    window.dispatchEvent(new CustomEvent("context-menu:open"));
  }

  /**
   * Position menu at coordinates, adjusting for viewport
   * @param {number} x
   * @param {number} y
   * @private
   */
  position(x, y) {
    const menuRect = this.container.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    let left = x;
    let top = y;

    // Adjust if menu goes off right edge
    if (left + menuRect.width > viewportWidth) {
      left = viewportWidth - menuRect.width - 8;
    }

    // Adjust if menu goes off bottom edge
    if (top + menuRect.height > viewportHeight) {
      top = viewportHeight - menuRect.height - 8;
    }

    // Ensure minimum padding from edges
    left = Math.max(8, left);
    top = Math.max(8, top);

    this.container.style.left = `${left}px`;
    this.container.style.top = `${top}px`;
  }

  /**
   * Render menu items
   * @private
   */
  render() {
    this.container.innerHTML = "";

    this.items.forEach((item, index) => {
      if (item.type === "separator") {
        this.renderSeparator(index);
      } else {
        this.renderItem(item, index);
      }
    });
  }

  /**
   * Render a menu item
   * @param {MenuItem} item
   * @param {number} index
   * @private
   */
  renderItem(item, index) {
    const element = document.createElement("button");
    element.className = "context-menu-item";
    element.setAttribute("role", "menuitem");
    element.setAttribute("tabindex", "-1");
    element.dataset.index = index;

    if (item.disabled) {
      element.classList.add("disabled");
      element.setAttribute("aria-disabled", "true");
    }

    // Icon
    if (item.icon) {
      const iconSpan = document.createElement("span");
      iconSpan.className = "context-menu-icon";
      iconSpan.textContent = item.icon;
      element.appendChild(iconSpan);
    }

    // Label
    const labelSpan = document.createElement("span");
    labelSpan.className = "context-menu-label";
    labelSpan.textContent = item.label;
    element.appendChild(labelSpan);

    // Shortcut
    if (item.shortcut) {
      const shortcutSpan = document.createElement("kbd");
      shortcutSpan.className = "context-menu-shortcut";
      shortcutSpan.textContent = item.shortcut;
      element.appendChild(shortcutSpan);
    }

    // Click handler
    if (!item.disabled) {
      element.addEventListener("click", (e) => {
        e.stopPropagation();
        this.selectItem(index);
      });

      element.addEventListener("mouseenter", () => {
        this.selectIndex(index);
      });
    }

    this.container.appendChild(element);
  }

  /**
   * Render a separator
   * @param {number} index
   * @private
   */
  renderSeparator(index) {
    const separator = document.createElement("div");
    separator.className = "context-menu-separator";
    separator.setAttribute("role", "separator");
    separator.dataset.index = index;
    this.container.appendChild(separator);
  }

  /**
   * Select an item by index
   * @param {number} index
   * @private
   */
  selectIndex(index) {
    // Remove previous selection
    const prev = this.container.querySelector(".context-menu-item.selected");
    if (prev) {
      prev.classList.remove("selected");
    }

    this.selectedIndex = index;

    // Add selection to new item
    const items = this.container.querySelectorAll(".context-menu-item:not(.disabled)");
    if (items[index]) {
      items[index].classList.add("selected");
      items[index].focus();
    }
  }

  /**
   * Execute selected item action
   * @param {number} index
   * @private
   */
  selectItem(index) {
    const item = this.items[index];
    if (item && !item.disabled && item.action) {
      this.close();
      item.action();
    }
  }

  /**
   * Handle keyboard navigation
   * @param {KeyboardEvent} e
   * @private
   */
  handleKeydown(e) {
    if (!this.isOpen) return;

    const items = this.container.querySelectorAll(".context-menu-item:not(.disabled)");

    switch (e.key) {
      case "Escape":
        e.preventDefault();
        this.close();
        break;

      case "ArrowDown":
        e.preventDefault();
        if (this.selectedIndex < items.length - 1) {
          this.selectIndex(this.selectedIndex + 1);
        } else {
          this.selectIndex(0);
        }
        break;

      case "ArrowUp":
        e.preventDefault();
        if (this.selectedIndex > 0) {
          this.selectIndex(this.selectedIndex - 1);
        } else {
          this.selectIndex(items.length - 1);
        }
        break;

      case "Enter":
      case " ":
        e.preventDefault();
        if (this.selectedIndex >= 0) {
          this.selectItem(this.selectedIndex);
        }
        break;

      case "Home":
        e.preventDefault();
        this.selectIndex(0);
        break;

      case "End":
        e.preventDefault();
        this.selectIndex(items.length - 1);
        break;

      case "Tab":
        e.preventDefault();
        if (e.shiftKey) {
          if (this.selectedIndex > 0) {
            this.selectIndex(this.selectedIndex - 1);
          } else {
            this.selectIndex(items.length - 1);
          }
        } else {
          if (this.selectedIndex < items.length - 1) {
            this.selectIndex(this.selectedIndex + 1);
          } else {
            this.selectIndex(0);
          }
        }
        break;
    }
  }

  /**
   * Handle click outside menu
   * @private
   */
  handleOutsideClick() {
    this.close();
  }

  /**
   * Close the menu
   */
  close() {
    if (!this.isOpen) return;

    this.isOpen = false;

    // Remove event listeners
    document.removeEventListener("keydown", this.handleKeydown);
    if (this.backdrop) {
      this.backdrop.removeEventListener("click", this.handleOutsideClick);
    }

    // Remove DOM elements
    if (this.container?.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    if (this.backdrop?.parentNode) {
      this.backdrop.parentNode.removeChild(this.backdrop);
    }

    // Return focus to trigger element
    if (this.triggerElement?.focus) {
      this.triggerElement.focus();
    }

    this.container = null;
    this.backdrop = null;
    this.items = [];
    this.selectedIndex = -1;

    window.dispatchEvent(new CustomEvent("context-menu:close"));
  }

  /**
   * Check if menu is currently open
   * @returns {boolean}
   */
  isMenuOpen() {
    return this.isOpen;
  }
}

// Export for ESM and browser usage
export { ContextMenu };

if (typeof window !== "undefined") {
  window.ContextMenu = ContextMenu;
}
