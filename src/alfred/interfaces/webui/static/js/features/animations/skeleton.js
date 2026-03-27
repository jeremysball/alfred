/**
 * Skeleton loading states
 * Shimmer placeholders for async content loading
 */

export class Skeleton {
  /**
   * Create a skeleton element
   * @param {string} variant - Skeleton variant ('text', 'title', 'avatar', 'card')
   * @param {Object} options - Additional options
   * @returns {HTMLElement} Skeleton element
   */
  static create(variant = 'text', { width, height } = {}) {
    const skeleton = document.createElement('div');
    skeleton.className = `skeleton skeleton--${variant}`;

    if (width) {
      skeleton.style.width = typeof width === 'number' ? `${width}px` : width;
    }

    if (height) {
      skeleton.style.height = typeof height === 'number' ? `${height}px` : height;
    }

    return skeleton;
  }

  /**
   * Show skeletons in a container
   * @param {HTMLElement} container - Container to fill with skeletons
   * @param {number} count - Number of skeleton items
   * @param {string} variant - Skeleton variant
   */
  static show(container, count = 3, variant = 'text') {
    // Clear existing content
    container.innerHTML = '';
    container.classList.add('skeleton-container');

    for (let i = 0; i < count; i++) {
      const skeleton = this.create(variant);
      container.appendChild(skeleton);
    }
  }

  /**
   * Hide skeletons and restore container
   * @param {HTMLElement} container - Container with skeletons
   */
  static hide(container) {
    container.innerHTML = '';
    container.classList.remove('skeleton-container');
  }

  /**
   * Create a skeleton for a session list item
   * @returns {HTMLElement} Session list item skeleton
   */
  static createSessionItem() {
    const item = document.createElement('div');
    item.className = 'skeleton skeleton--session-item';
    item.style.cssText = `
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      margin-bottom: 8px;
    `;

    const avatar = this.create('avatar');
    const content = document.createElement('div');
    content.style.cssText = 'flex: 1;';

    const title = this.create('title');
    const text = this.create('text');
    text.style.width = '80%';

    content.appendChild(title);
    content.appendChild(text);

    item.appendChild(avatar);
    item.appendChild(content);

    return item;
  }

  /**
   * Show session list skeleton
   * @param {HTMLElement} container - Sessions list container
   * @param {number} count - Number of skeleton items
   */
  static showSessionList(container, count = 5) {
    container.innerHTML = '';

    for (let i = 0; i < count; i++) {
      const item = this.createSessionItem();
      container.appendChild(item);
    }
  }
}
