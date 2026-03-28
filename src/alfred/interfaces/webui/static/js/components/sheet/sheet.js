/**
 * ThemedSheet - Shared surface for Help, Context, and Settings
 *
 * Usage:
 *   const sheet = new ThemedSheet({ title: 'System Context' });
 *   sheet.setContent(elementOrHTML);
 *   sheet.open();
 *
 * Features:
 * - Respects active theme colors (via CSS custom properties)
 * - Inherits global font family and size
 * - Consistent animation and focus behavior
 * - Backdrop click to close
 * - Escape key to close
 * - Mobile-friendly bottom-sheet style on narrow screens
 */

class ThemedSheet {
  constructor(options = {}) {
    this.title = options.title || "";
    this.onClose = options.onClose || (() => {});
    this._container = null;
    this._contentSlot = null;
    this._isOpen = false;
  }

  _createDOM() {
    // Backdrop
    const backdrop = document.createElement("div");
    backdrop.className = "themed-sheet-backdrop";
    backdrop.setAttribute("role", "presentation");
    backdrop.addEventListener("click", () => this.close());

    // Sheet container
    const sheet = document.createElement("div");
    sheet.className = "themed-sheet";
    sheet.setAttribute("role", "dialog");
    sheet.setAttribute("aria-modal", "true");
    sheet.setAttribute("tabindex", "-1");

    // Header
    if (this.title) {
      const header = document.createElement("div");
      header.className = "themed-sheet-header";

      const titleEl = document.createElement("h2");
      titleEl.className = "themed-sheet-title";
      titleEl.textContent = this.title;

      const closeBtn = document.createElement("button");
      closeBtn.className = "themed-sheet-close";
      closeBtn.setAttribute("aria-label", "Close");
      closeBtn.innerHTML = "×";
      closeBtn.addEventListener("click", () => this.close());

      header.appendChild(titleEl);
      header.appendChild(closeBtn);
      sheet.appendChild(header);
    }

    // Content slot
    const content = document.createElement("div");
    content.className = "themed-sheet-content";
    this._contentSlot = content;
    sheet.appendChild(content);

    // Container holds both
    const container = document.createElement("div");
    container.className = "themed-sheet-container";
    container.style.display = "none";
    container.appendChild(backdrop);
    container.appendChild(sheet);

    // Keyboard handling
    container.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.close();
      }
    });

    this._container = container;
    document.body.appendChild(container);
  }

  setContent(content) {
    if (!this._contentSlot) {
      this._createDOM();
    }
    this._contentSlot.innerHTML = "";
    if (typeof content === "string") {
      this._contentSlot.innerHTML = content;
    } else if (content instanceof HTMLElement) {
      this._contentSlot.appendChild(content);
    }
  }

  open() {
    if (!this._container) {
      this._createDOM();
    }
    if (this._isOpen) return;

    this._container.style.display = "";
    // Force reflow for animation
    void this._container.offsetHeight;
    this._container.classList.add("open");

    // Focus trap: focus the sheet or first focusable element
    const sheet = this._container.querySelector(".themed-sheet");
    const focusable = sheet.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    (focusable || sheet).focus();

    this._isOpen = true;

    // Prevent body scroll
    document.body.style.overflow = "hidden";
  }

  close() {
    if (!this._isOpen || !this._container) return;

    this._container.classList.remove("open");

    // Wait for animation then hide
    setTimeout(() => {
      if (!this._isOpen) {
        this._container.style.display = "none";
        document.body.style.overflow = "";
      }
    }, 200);

    this._isOpen = false;
    this.onClose();
  }

  destroy() {
    this.close();
    if (this._container?.parentNode) {
      this._container.parentNode.removeChild(this._container);
    }
    this._container = null;
    this._contentSlot = null;
  }

  get isOpen() {
    return this._isOpen;
  }
}

// ES Module export
export { ThemedSheet };

// CommonJS fallback
if (typeof module !== "undefined" && module.exports) {
  module.exports = { ThemedSheet };
}
