/**
 * Shortcut Registry for Keyboard Shortcuts
 *
 * Provides registration and management of keyboard shortcuts
 * with support for modifier keys and context-aware activation.
 */

/** @type {Map<string, Shortcut>} */
const registry = new Map();

/**
 * @typedef {Object} Shortcut
 * @property {string} id - Unique identifier
 * @property {string} key - The key (e.g., '?', 'k', 'ArrowUp')
 * @property {boolean} ctrl - Requires Ctrl key
 * @property {boolean} shift - Requires Shift key
 * @property {boolean} alt - Requires Alt key
 * @property {boolean} meta - Requires Meta/Cmd key
 * @property {string} description - What the shortcut does
 * @property {string} category - 'Global', 'Navigation', 'Actions', 'Composer'
 * @property {string} [context] - 'global', 'input-focused', 'message-focused'
 * @property {function} action - Function to execute
 */

/**
 * Parse a key combination string into components
 * @param {string} combo - Key combination (e.g., 'Ctrl+K', 'Shift+?', 'ArrowUp')
 * @returns {Object} Parsed components
 */
function parseKeyCombo(combo) {
  const parts = combo.split('+').map(p => p.trim());
  const modifiers = {
    ctrl: parts.includes('Ctrl'),
    shift: parts.includes('Shift'),
    alt: parts.includes('Alt'),
    meta: parts.includes('Meta') || parts.includes('Cmd') || parts.includes('Command')
  };

  // The key is the last part or the only non-modifier part
  const key = parts.find(p =>
    !['Ctrl', 'Shift', 'Alt', 'Meta', 'Cmd', 'Command'].includes(p)
  ) || '';

  return { ...modifiers, key };
}

/**
 * Register a keyboard shortcut
 * @param {Object} config - Shortcut configuration
 * @param {string} config.id - Unique identifier
 * @param {string} config.key - Key or key combination (e.g., 'Ctrl+K', '?')
 * @param {string} config.description - What the shortcut does
 * @param {string} [config.category='Global'] - Category for grouping
 * @param {string} [config.context='global'] - When shortcut is active
 * @param {function} config.action - Function to execute
 * @throws {Error} If required fields are missing or duplicate id
 */
function register(config) {
  if (!config || typeof config !== 'object') {
    throw new Error('Shortcut config must be an object');
  }

  if (!config.id || typeof config.id !== 'string') {
    throw new Error('Shortcut id is required and must be a string');
  }

  if (!config.key || typeof config.key !== 'string') {
    throw new Error('Shortcut key is required and must be a string');
  }

  if (!config.action || typeof config.action !== 'function') {
    throw new Error('Shortcut action is required and must be a function');
  }

  if (!config.description || typeof config.description !== 'string') {
    throw new Error('Shortcut description is required and must be a string');
  }

  if (registry.has(config.id)) {
    throw new Error(`Shortcut with id "${config.id}" already exists`);
  }

  const parsed = parseKeyCombo(config.key);

  registry.set(config.id, {
    id: config.id,
    key: parsed.key.toLowerCase(),
    ctrl: parsed.ctrl,
    shift: parsed.shift,
    alt: parsed.alt,
    meta: parsed.meta,
    description: config.description,
    category: config.category || 'Global',
    context: config.context || 'global',
    action: config.action
  });
}

/**
 * Get all registered shortcuts grouped by category
 * @returns {Object} Shortcuts grouped by category
 */
function getAll() {
  const grouped = {};

  for (const shortcut of registry.values()) {
    const category = shortcut.category;
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push(shortcut);
  }

  return grouped;
}

/**
 * Get all shortcuts as a flat array
 * @returns {Shortcut[]}
 */
function getAllFlat() {
  return Array.from(registry.values());
}

/**
 * Get a shortcut by its id
 * @param {string} id
 * @returns {Shortcut|undefined}
 */
function getById(id) {
  return registry.get(id);
}

/**
 * Unregister a shortcut by id
 * @param {string} id
 * @returns {boolean}
 */
function unregister(id) {
  return registry.delete(id);
}

/**
 * Clear all shortcuts
 */
function clear() {
  registry.clear();
}

/**
 * Format shortcut for display (e.g., "Ctrl+K")
 * @param {Shortcut} shortcut
 * @returns {string}
 */
function formatShortcut(shortcut) {
  const parts = [];
  if (shortcut.ctrl) parts.push('Ctrl');
  if (shortcut.shift) parts.push('Shift');
  if (shortcut.alt) parts.push('Alt');
  if (shortcut.meta) parts.push('Cmd');

  // Format special keys nicely
  let key = shortcut.key;
  if (key === ' ') key = 'Space';
  if (key === '?') key = '?';
  if (key === 'arrowup') key = '↑';
  if (key === 'arrowdown') key = '↓';
  if (key === 'arrowleft') key = '←';
  if (key === 'arrowright') key = '→';
  if (key === 'home') key = 'Home';
  if (key === 'end') key = 'End';
  if (key === 'escape') key = 'Esc';
  if (key === 'tab') key = 'Tab';
  if (key === 'enter') key = 'Enter';

  parts.push(key);
  return parts.join('+');
}

// Export for CommonJS
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    register,
    getAll,
    getAllFlat,
    getById,
    unregister,
    clear,
    formatShortcut,
    parseKeyCombo
  };
}

// Export for browser
if (typeof window !== 'undefined') {
  window.ShortcutRegistry = {
    register,
    getAll,
    getAllFlat,
    getById,
    unregister,
    clear,
    formatShortcut,
    parseKeyCombo
  };
}
