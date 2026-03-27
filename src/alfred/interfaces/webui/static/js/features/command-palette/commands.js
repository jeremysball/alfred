/**
 * Command Registry for Command Palette
 *
 * Provides registration and retrieval of commands that can be
 * executed via the command palette (Ctrl+K).
 */

/** @type {Map<string, Command>} */
const registry = new Map();

/**
 * @typedef {Object} Command
 * @property {string} id - Unique identifier for the command
 * @property {string} title - Display title for the command
 * @property {string[]} [keywords] - Additional search keywords
 * @property {string} [shortcut] - Keyboard shortcut display (e.g., "Ctrl+Shift+C")
 * @property {function} action - Function to execute when command is selected
 */

/**
 * Register a command in the palette
 * @param {Command} command - The command to register
 * @throws {Error} If required fields are missing or command already exists
 */
function register(command) {
  if (!command || typeof command !== 'object') {
    throw new Error('Command must be an object');
  }

  if (!command.id || typeof command.id !== 'string') {
    throw new Error('Command id is required and must be a string');
  }

  if (!command.title || typeof command.title !== 'string') {
    throw new Error('Command title is required and must be a string');
  }

  if (!command.action || typeof command.action !== 'function') {
    throw new Error('Command action is required and must be a function');
  }

  if (registry.has(command.id)) {
    throw new Error(`Command with id "${command.id}" already exists`);
  }

  registry.set(command.id, {
    id: command.id,
    title: command.title,
    keywords: command.keywords || [],
    shortcut: command.shortcut || null,
    action: command.action
  });
}

/**
 * Get all registered commands
 * @returns {Command[]} Array of all registered commands
 */
function getAll() {
  return Array.from(registry.values());
}

/**
 * Get a command by its id
 * @param {string} id - The command id
 * @returns {Command|undefined} The command or undefined if not found
 */
function getById(id) {
  return registry.get(id);
}

/**
 * Unregister a command by its id
 * @param {string} id - The command id to remove
 * @returns {boolean} True if command was removed, false if not found
 */
function unregister(id) {
  return registry.delete(id);
}

/**
 * Clear all registered commands (useful for testing)
 */
function clear() {
  registry.clear();
}

// Export for ESM and browser usage
export { register, getAll, getById, unregister, clear };

if (typeof window !== 'undefined') {
  window.CommandRegistry = { register, getAll, getById, unregister, clear };
}
