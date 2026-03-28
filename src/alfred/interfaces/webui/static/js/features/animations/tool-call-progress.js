/**
 * Tool call progress animations
 * Shows progress bars and pulsing states for tool execution
 */

export class ToolCallProgress {
  /**
   * Create a progress bar element
   * @param {Object} options - Configuration options
   * @param {boolean} options.indeterminate - Whether to show indeterminate animation
   * @param {number} options.progress - Initial progress (0-100)
   * @returns {HTMLElement} Progress bar container
   */
  static create({ indeterminate = false, progress = 0 } = {}) {
    const container = document.createElement("div");
    container.className = "tool-call-progress";

    const bar = document.createElement("div");
    bar.className = "tool-call-progress__bar";

    if (indeterminate) {
      bar.classList.add("tool-call-progress__bar--indeterminate");
    } else {
      bar.style.transform = `scaleX(${progress / 100})`;
    }

    container.appendChild(bar);
    return container;
  }

  /**
   * Update progress bar value
   * @param {HTMLElement} container - Progress container element
   * @param {number} progress - Progress value (0-100)
   */
  static update(container, progress) {
    const bar = container.querySelector(".tool-call-progress__bar");
    if (bar) {
      bar.classList.remove("tool-call-progress__bar--indeterminate");
      bar.style.transform = `scaleX(${Math.min(100, Math.max(0, progress)) / 100})`;
    }
  }

  /**
   * Mark tool call as executing (adds pulse animation)
   * @param {HTMLElement} element - Tool call element to animate
   */
  static markExecuting(element) {
    element.classList.add("tool-call--executing");
  }

  /**
   * Mark tool call as complete (removes pulse animation)
   * @param {HTMLElement} element - Tool call element
   */
  static markComplete(element) {
    element.classList.remove("tool-call--executing");
  }

  /**
   * Create a complete tool call UI with progress
   * @param {string} toolName - Name of the tool being called
   * @param {Object} options - Display options
   * @returns {HTMLElement} Complete tool call element
   */
  static createToolCallUI(toolName, { indeterminate = true } = {}) {
    const wrapper = document.createElement("div");
    wrapper.className = "tool-call";

    const header = document.createElement("div");
    header.className = "tool-call__header";
    header.textContent = `Running ${toolName}...`;

    const progress = ToolCallProgress.create({ indeterminate });

    wrapper.appendChild(header);
    wrapper.appendChild(progress);

    if (indeterminate) {
      ToolCallProgress.markExecuting(wrapper);
    }

    return wrapper;
  }
}
