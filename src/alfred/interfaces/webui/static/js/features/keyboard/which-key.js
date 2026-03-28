/**
 * WhichKey - Leader key hint overlay
 *
 * Shows available leader-mode bindings as a legend, with nested submenus
 * when a binding is a prefix for additional keys.
 */

class WhichKey {
  constructor() {
    this.container = null;
    this.isVisible = false;
    this.tree = [];
    this.activePath = [];
  }

  /**
   * Replace the root binding tree.
   * @param {Array<Object>} tree
   */
  setBindings(tree) {
    this.tree = Array.isArray(tree) ? tree : [];
    if (this.isVisible) {
      this.render();
    }
  }

  /**
   * Create the which-key DOM element
   */
  createDOM() {
    if (this.container) return;

    this.container = document.createElement("div");
    this.container.className = "which-key";
    this.container.setAttribute("role", "dialog");
    this.container.setAttribute("aria-label", "Leader key bindings");
    this.container.style.display = "none";

    const header = document.createElement("div");
    header.className = "which-key-header";
    header.textContent = "Leader (Ctrl+A)";
    this.container.appendChild(header);

    const grid = document.createElement("div");
    grid.className = "which-key-grid";
    this.container.appendChild(grid);

    const footer = document.createElement("div");
    footer.className = "which-key-footer";
    footer.innerHTML =
      '<kbd class="which-key-key">Esc</kbd><span class="which-key-label">Cancel leader mode</span>';
    this.container.appendChild(footer);

    document.body.appendChild(this.container);
  }

  /**
   * Normalize a key for matching.
   * @param {string} key
   * @returns {string}
   */
  normalizeKey(key) {
    return String(key ?? "").toLowerCase();
  }

  /**
   * Format a key for display.
   * @param {string} key
   * @returns {string}
   */
  formatKey(key) {
    const normalized = String(key ?? "");

    if (normalized === "Escape") return "Esc";
    if (normalized === "Enter") return "Enter";
    if (normalized === " ") return "Space";
    if (normalized === "ArrowUp") return "↑";
    if (normalized === "ArrowDown") return "↓";
    if (normalized === "ArrowLeft") return "←";
    if (normalized === "ArrowRight") return "→";

    if (normalized.length === 1 && /[a-z]/i.test(normalized)) {
      return normalized.toUpperCase();
    }

    return normalized;
  }

  /**
   * Build a breadcrumb label from the current path.
   * @param {Array<string>} path
   * @returns {string}
   */
  formatPath(path) {
    if (!Array.isArray(path) || path.length === 0) {
      return "Leader (Ctrl+A)";
    }

    return `Leader + ${path.map((key) => this.formatKey(key)).join(" + ")}`;
  }

  /**
   * Find bindings for a prefix path.
   * @param {Array<string>} path
   * @returns {Array<Object>}
   */
  getBindingsForPath(path = []) {
    let current = this.tree;

    for (const key of path) {
      const match = current.find(
        (binding) => this.normalizeKey(binding.key) === this.normalizeKey(key),
      );
      if (!match) {
        return [];
      }
      current = Array.isArray(match.children) ? match.children : [];
    }

    return current;
  }

  /**
   * Create a legend row for a binding.
   * @param {Object} binding
   * @returns {HTMLElement}
   */
  createItem(binding) {
    const item = document.createElement("div");
    item.className = "which-key-item";

    const keyEl = document.createElement("kbd");
    keyEl.className = "which-key-key";
    keyEl.textContent = this.formatKey(binding.key);

    const labelWrap = document.createElement("span");
    labelWrap.className = "which-key-label-wrap";

    const labelEl = document.createElement("span");
    labelEl.className = "which-key-label";
    labelEl.textContent = binding.label || binding.description || this.formatKey(binding.key);

    labelWrap.appendChild(labelEl);

    if (binding.description && binding.label && binding.description !== binding.label) {
      const descriptionEl = document.createElement("span");
      descriptionEl.className = "which-key-description";
      descriptionEl.textContent = binding.description;
      labelWrap.appendChild(descriptionEl);
    }

    item.appendChild(keyEl);
    item.appendChild(labelWrap);

    if (binding.description) {
      item.title = binding.description;
    }

    return item;
  }

  /**
   * Render the bindings for the active prefix.
   */
  render() {
    if (!this.container) this.createDOM();

    const grid = this.container.querySelector(".which-key-grid");
    const header = this.container.querySelector(".which-key-header");
    grid.innerHTML = "";

    const currentBindings = this.getBindingsForPath(this.activePath);
    header.textContent = this.formatPath(this.activePath);

    if (currentBindings.length === 0) {
      const empty = document.createElement("div");
      empty.className = "which-key-empty";
      empty.textContent = "No more leader keys";
      grid.appendChild(empty);
      this.container.classList.add("compact");
      return;
    }

    this.container.classList.toggle("compact", currentBindings.length <= 3);

    currentBindings.forEach((binding) => {
      grid.appendChild(this.createItem(binding));
    });
  }

  /**
   * Show the which-key overlay.
   * @param {HTMLElement} anchor - Element to position relative to (default: message input)
   * @param {Array<string>} path - Active leader prefix
   */
  show(anchor = null, path = []) {
    if (!this.container) this.createDOM();

    this.activePath = Array.isArray(path) ? [...path] : [];
    this.render();

    this.container.style.display = "block";
    this.container.style.visibility = "hidden";

    const target = anchor || document.getElementById("message-input");
    const rect = target?.getBoundingClientRect();
    const margin = 12;
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const boxWidth = this.container.offsetWidth;
    const boxHeight = this.container.offsetHeight;

    if (rect) {
      let left = rect.left;
      let top = rect.bottom + 8;

      if (top + boxHeight > viewportHeight - margin) {
        const aboveTop = rect.top - boxHeight - 8;
        top = aboveTop >= margin ? aboveTop : viewportHeight - boxHeight - margin;
      }

      if (left + boxWidth > viewportWidth - margin) {
        left = viewportWidth - boxWidth - margin;
      }

      left = Math.max(margin, left);
      top = Math.max(margin, top);

      this.container.style.left = `${left}px`;
      this.container.style.top = `${top}px`;
    }

    this.container.style.visibility = "visible";
    this.isVisible = true;

    window.dispatchEvent(new CustomEvent("which-key:open"));
  }

  /**
   * Hide the which-key overlay.
   */
  hide() {
    if (this.container) {
      this.container.style.display = "none";
    }
    this.isVisible = false;
    this.activePath = [];

    window.dispatchEvent(new CustomEvent("which-key:close"));
  }

  /**
   * Toggle visibility.
   * @param {HTMLElement} anchor
   * @param {Array<string>} path
   */
  toggle(anchor = null, path = []) {
    if (this.isVisible) {
      this.hide();
    } else {
      this.show(anchor, path);
    }
  }

  /**
   * Destroy the component.
   */
  destroy() {
    this.hide();
    if (this.container?.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
    this.container = null;
    this.tree = [];
  }
}

// Export for ESM and browser
export { WhichKey };

if (typeof window !== "undefined") {
  window.WhichKey = WhichKey;
}
