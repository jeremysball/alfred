/**
 * Help Sheet for Keyboard Shortcuts
 *
 * Displays all registered keyboard shortcuts organized by category.
 * Uses the shared themed sheet surface for consistent theming.
 * Opens with F1 (configurable via keymap).
 */

import { ThemedSheet } from "../../components/sheet/sheet.js";
import {
  formatBinding,
  formatLeaderBreadcrumb,
  getBinding,
  getBindingsByCategory,
  subscribe,
} from "./keymap.js";

class HelpSheet {
  constructor() {
    this.sheet = null;
    this.contentElement = null;
    this.unsubscribe = null;
    this.boundHandleKeydown = this.handleGlobalKeydown.bind(this);
    this.boundHandleOpenEvent = this.handleOpenEvent.bind(this);

    // Listen for keymap changes
    this.unsubscribe = subscribe(() => {
      if (this.sheet?.isOpen) {
        this.renderShortcuts();
      }
    });

    // Attach global listener for help shortcut
    document.addEventListener("keydown", this.boundHandleKeydown);
    window.addEventListener("help:open", this.boundHandleOpenEvent);
    window.addEventListener("keyboard-help:open", this.boundHandleOpenEvent);
  }

  /**
   * Handle global keydown for help shortcut
   * @param {KeyboardEvent} e
   */
  handleGlobalKeydown(e) {
    const binding = getBinding("help.open");
    if (binding && this.matchesBinding(e, binding)) {
      e.preventDefault();
      this.toggle();
    }
  }

  /**
   * Handle explicit open events from other UI paths
   * @private
   */
  handleOpenEvent() {
    this.show();
  }

  /**
   * Check if event matches binding
   * @param {KeyboardEvent} event
   * @param {Object} binding
   * @returns {boolean}
   */
  matchesBinding(event, binding) {
    const keyMatch = event.key.toLowerCase() === binding.key.toLowerCase();
    const ctrlMatch = !!event.ctrlKey === !!binding.ctrl;
    const shiftMatch = !!event.shiftKey === !!binding.shift;
    const altMatch = !!event.altKey === !!binding.alt;
    const metaMatch = !!event.metaKey === !!binding.meta;

    return keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch;
  }

  /**
   * Create the sheet if not exists
   * @private
   */
  ensureSheet() {
    if (this.sheet) return;

    this.sheet = new ThemedSheet({
      title: "Keyboard Shortcuts",
      onClose: () => {
        window.dispatchEvent(new CustomEvent("keyboard-help:close"));
      },
    });

    this.contentElement = document.createElement("div");
    this.contentElement.className = "keyboard-help-content";
    this.sheet.setContent(this.contentElement);
  }

  /**
   * Render shortcuts organized by category
   * @private
   */
  renderShortcuts() {
    if (!this.contentElement) return;

    const grouped = getBindingsByCategory();
    this.contentElement.innerHTML = "";

    const categories = Object.keys(grouped).sort();

    if (categories.length === 0) {
      this.contentElement.innerHTML = '<p class="keyboard-help-empty">No shortcuts registered</p>';
      return;
    }

    categories.forEach((category) => {
      const section = document.createElement("section");
      section.className = "keyboard-help-section";

      const heading = document.createElement("h3");
      heading.className = "keyboard-help-category";
      heading.textContent = category;
      section.appendChild(heading);

      const list = document.createElement("ul");
      list.className = "keyboard-help-list";

      // Sort by key for consistent ordering
      const bindings = grouped[category].sort((a, b) => {
        return formatBinding(a).localeCompare(formatBinding(b));
      });

      bindings.forEach((binding) => {
        const item = document.createElement("li");
        item.className = "keyboard-help-item";

        const keyEl = document.createElement("kbd");
        keyEl.className = "keyboard-help-key";
        keyEl.textContent = formatBinding(binding);

        const detailsEl = document.createElement("span");
        detailsEl.className = "keyboard-help-details";

        const descEl = document.createElement("span");
        descEl.className = "keyboard-help-description";
        descEl.textContent = binding.description;
        detailsEl.appendChild(descEl);

        if (Array.isArray(binding.leader?.path) && binding.leader.path.length > 0) {
          const pathEl = document.createElement("span");
          pathEl.className = "keyboard-help-path";
          pathEl.textContent = formatLeaderBreadcrumb(binding.leader.path);
          detailsEl.appendChild(pathEl);
        }

        item.appendChild(keyEl);
        item.appendChild(detailsEl);
        list.appendChild(item);
      });

      section.appendChild(list);
      this.contentElement.appendChild(section);
    });
  }

  /**
   * Show the help sheet
   */
  show() {
    this.ensureSheet();
    this.renderShortcuts();
    this.sheet.open();
    window.dispatchEvent(new CustomEvent("keyboard-help:open"));
  }

  /**
   * Close the help sheet
   */
  close() {
    if (this.sheet) {
      this.sheet.close();
    }
  }

  /**
   * Toggle the help sheet
   */
  toggle() {
    if (this.sheet?.isOpen) {
      this.close();
    } else {
      this.show();
    }
  }

  /**
   * Destroy the help sheet and clean up
   */
  destroy() {
    this.close();
    if (this.sheet) {
      this.sheet.destroy();
      this.sheet = null;
    }
    if (this.unsubscribe) {
      this.unsubscribe();
      this.unsubscribe = null;
    }
    document.removeEventListener("keydown", this.boundHandleKeydown);
    window.removeEventListener("help:open", this.boundHandleOpenEvent);
    window.removeEventListener("keyboard-help:open", this.boundHandleOpenEvent);
  }
}

// Export for ESM and browser
export { HelpSheet };

if (typeof window !== "undefined") {
  window.HelpSheet = HelpSheet;
}
