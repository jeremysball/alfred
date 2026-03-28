/**
 * Keymap Manager - Persisted keyboard shortcuts configuration
 *
 * Provides a central registry for keyboard shortcuts with localStorage persistence.
 * Allows runtime rebinding of shortcuts and notifies subscribers of changes.
 */

const STORAGE_KEY = "alfred-keymap-v1";

/**
 * Default keymap configuration
 * @type {Object.<string, {key: string, ctrl?: boolean, shift?: boolean, alt?: boolean, meta?: boolean, description: string, category: string}>}
 */
const DEFAULT_KEYMAP = {
  "help.open": {
    key: "F1",
    description: "Open help",
    category: "Global",
  },
  "commandPalette.open": {
    key: "P",
    ctrl: true,
    alt: true,
    description: "Open command palette",
    category: "Global",
  },
  "search.open": {
    key: "K",
    ctrl: true,
    alt: true,
    description: "Search messages",
    category: "Navigation",
  },
  "quickSwitcher.open": {
    key: "O",
    ctrl: true,
    alt: true,
    description: "Quick switcher",
    category: "Navigation",
  },
  "mentions.open": {
    key: "M",
    ctrl: true,
    alt: true,
    description: "Mention user/memory",
    category: "Composer",
  },
  "context.open": {
    key: "I",
    ctrl: true,
    alt: true,
    description: "Open system context",
    category: "Global",
  },
  "composer.focus": {
    key: "Escape",
    description: "Focus/unfocus composer",
    category: "Composer",
  },
  "composer.leader": {
    key: "S",
    ctrl: true,
    description: "Leader key (tmux-style prefix)",
    category: "Composer",
  },
  "help.open.leader.h": {
    key: "h",
    leader: true,
    description: "Open help (Leader + h)",
    category: "Global",
  },
  "help.open.leader.question": {
    key: "?",
    leader: true,
    description: "Open help (Leader + ?)",
    category: "Global",
  },
  "composer.send": {
    key: "Enter",
    description: "Send message",
    category: "Composer",
  },
  "composer.queue": {
    key: "Enter",
    leader: true,
    description: "Queue message (Ctrl+S, Enter)",
    category: "Composer",
  },
  "composer.newline": {
    key: "Enter",
    shift: true,
    description: "New line in composer",
    category: "Composer",
  },
  "message.edit": {
    key: "e",
    description: "Edit message",
    category: "Message",
  },
  "message.delete": {
    key: "d",
    description: "Delete message",
    category: "Message",
  },
  "message.copy": {
    key: "c",
    ctrl: true,
    description: "Copy message",
    category: "Message",
  },
  "navigation.up": {
    key: "ArrowUp",
    description: "Previous message",
    category: "Navigation",
  },
  "navigation.down": {
    key: "ArrowDown",
    description: "Next message",
    category: "Navigation",
  },
  "navigation.home": {
    key: "Home",
    description: "First message",
    category: "Navigation",
  },
  "navigation.end": {
    key: "End",
    description: "Last message",
    category: "Navigation",
  },
};

// In-memory keymap cache
let keymapCache = null;

// Subscribers for keymap changes
const subscribers = new Set();

/**
 * Load keymap from localStorage or use defaults
 * @returns {Object} Current keymap
 */
function loadKeymap() {
  if (keymapCache) return keymapCache;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      // Merge with defaults to ensure all actions have bindings
      keymapCache = { ...DEFAULT_KEYMAP, ...parsed };
      return keymapCache;
    }
  } catch (e) {
    console.warn("Failed to load keymap from localStorage:", e);
  }

  keymapCache = { ...DEFAULT_KEYMAP };
  return keymapCache;
}

/**
 * Save keymap to localStorage
 * @param {Object} keymap
 */
function saveKeymap(keymap) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(keymap));
    keymapCache = { ...keymap };
    notifySubscribers();
  } catch (e) {
    console.error("Failed to save keymap to localStorage:", e);
  }
}

/**
 * Get the current keymap
 * @returns {Object}
 */
function getKeymap() {
  return loadKeymap();
}

/**
 * Get a specific keybinding
 * @param {string} actionId
 * @returns {Object|undefined}
 */
function getBinding(actionId) {
  const keymap = loadKeymap();
  return keymap[actionId];
}

/**
 * Set a keybinding
 * @param {string} actionId
 * @param {Object} binding
 * @param {string} binding.key
 * @param {boolean} [binding.ctrl]
 * @param {boolean} [binding.shift]
 * @param {boolean} [binding.alt]
 * @param {boolean} [binding.meta]
 */
function setBinding(actionId, binding) {
  const keymap = loadKeymap();
  keymap[actionId] = {
    ...keymap[actionId],
    ...binding,
  };
  saveKeymap(keymap);
}

/**
 * Reset a binding to default
 * @param {string} actionId
 */
function resetBinding(actionId) {
  const keymap = loadKeymap();
  if (DEFAULT_KEYMAP[actionId]) {
    keymap[actionId] = { ...DEFAULT_KEYMAP[actionId] };
  } else {
    delete keymap[actionId];
  }
  saveKeymap(keymap);
}

/**
 * Reset all bindings to defaults
 */
function resetAllBindings() {
  keymapCache = { ...DEFAULT_KEYMAP };
  saveKeymap(keymapCache);
}

/**
 * Get all bindings grouped by category
 * @returns {Object}
 */
function getBindingsByCategory() {
  const keymap = loadKeymap();
  const grouped = {};

  Object.entries(keymap).forEach(([actionId, binding]) => {
    const category = binding.category || "Uncategorized";
    if (!grouped[category]) {
      grouped[category] = [];
    }
    grouped[category].push({
      actionId,
      ...binding,
    });
  });

  return grouped;
}

function normalizeLeaderKey(key) {
  return String(key ?? "")
    .trim()
    .toLowerCase();
}

function normalizeLeaderSegmentKey(segment) {
  if (typeof segment === "string") {
    return normalizeLeaderKey(segment);
  }

  if (segment && typeof segment === "object") {
    return normalizeLeaderKey(segment.key);
  }

  return "";
}

function isNonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function formatLeaderPath(path) {
  return path.map((segment) => normalizeLeaderSegmentKey(segment) || "?").join(" > ");
}

function validateLeaderPathSegment(segment, actionId, index) {
  if (!segment || typeof segment !== "object" || Array.isArray(segment)) {
    throw new Error(`Leader path segment ${index + 1} for ${actionId} must be an object`);
  }

  if (!isNonEmptyString(segment.key)) {
    throw new Error(`Leader path segment ${index + 1} for ${actionId} is missing a key`);
  }

  if (!isNonEmptyString(segment.label)) {
    throw new Error(`Leader path segment ${index + 1} for ${actionId} is missing a label`);
  }

  if (!isNonEmptyString(segment.description)) {
    throw new Error(`Leader path segment ${index + 1} for ${actionId} is missing a description`);
  }
}

function sameLeaderSegmentMetadata(entry, segment) {
  return (
    normalizeLeaderKey(entry.key) === normalizeLeaderKey(segment.key) &&
    entry.label === segment.label.trim() &&
    entry.description === segment.description.trim()
  );
}

function createLeaderNode(segment) {
  return {
    key: segment.key.trim(),
    label: segment.label.trim(),
    description: segment.description.trim(),
    actionId: null,
    childrenMap: new Map(),
  };
}

function compareLeaderEntries(a, b) {
  const keyComparison = normalizeLeaderKey(a.key).localeCompare(normalizeLeaderKey(b.key));
  if (keyComparison !== 0) {
    return keyComparison;
  }

  return a.label.localeCompare(b.label);
}

function materializeLeaderNodes(childrenMap) {
  return [...childrenMap.values()].sort(compareLeaderEntries).map((entry) => {
    const node = {
      key: entry.key,
      label: entry.label,
      description: entry.description,
    };

    const children = materializeLeaderNodes(entry.childrenMap);
    if (children.length > 0) {
      node.children = children;
    }

    if (entry.actionId) {
      node.actionId = entry.actionId;
    }

    return node;
  });
}

function insertLeaderPath(rootMap, path, actionId) {
  let currentMap = rootMap;

  path.forEach((segment, index) => {
    validateLeaderPathSegment(segment, actionId, index);
    const normalizedKey = normalizeLeaderKey(segment.key);
    const existing = currentMap.get(normalizedKey);
    const isLastSegment = index === path.length - 1;

    if (!existing) {
      const entry = createLeaderNode(segment);
      currentMap.set(normalizedKey, entry);

      if (isLastSegment) {
        entry.actionId = actionId;
        return;
      }

      currentMap = entry.childrenMap;
      return;
    }

    if (!sameLeaderSegmentMetadata(existing, segment)) {
      throw new Error(`Conflicting leader metadata for ${formatLeaderPath(path)}`);
    }

    if (isLastSegment) {
      if (existing.actionId || existing.childrenMap.size > 0) {
        throw new Error(`Duplicate leader path: ${formatLeaderPath(path)}`);
      }

      existing.actionId = actionId;
      return;
    }

    if (existing.actionId) {
      throw new Error(
        `Leader path collides with an existing leaf: ${formatLeaderPath(path.slice(0, index + 1))}`,
      );
    }

    currentMap = existing.childrenMap;
  });
}

/**
 * Build a deterministic leader tree from the keymap registry.
 * @param {Object<string, Object>} keymap
 * @returns {Array<Object>}
 */
function buildLeaderTree(keymap) {
  const rootMap = new Map();

  Object.entries(keymap ?? {}).forEach(([actionId, binding]) => {
    const path = binding?.leader?.path;
    if (!Array.isArray(path) || path.length === 0) {
      return;
    }

    insertLeaderPath(rootMap, path, actionId);
  });

  return materializeLeaderNodes(rootMap);
}

/**
 * Resolve a leader tree node by a chord path.
 * @param {Array<Object>} tree
 * @param {Array<string|Object>} path
 * @returns {Object|null}
 */
function getLeaderNodeForPath(tree, path) {
  if (!Array.isArray(tree) || !Array.isArray(path) || path.length === 0) {
    return null;
  }

  let currentNodes = tree;
  let currentNode = null;

  for (const segment of path) {
    const key = normalizeLeaderSegmentKey(segment);
    if (!key) {
      return null;
    }

    currentNode = currentNodes.find((node) => normalizeLeaderKey(node.key) === key) ?? null;
    if (!currentNode) {
      return null;
    }

    currentNodes = Array.isArray(currentNode.children) ? currentNode.children : [];
  }

  return currentNode;
}

/**
 * Format a binding for display
 * @param {Object} binding
 * @returns {string}
 */
function formatBinding(binding) {
  const parts = [];
  if (binding.ctrl) parts.push("Ctrl");
  if (binding.shift) parts.push("Shift");
  if (binding.alt) parts.push("Alt");
  if (binding.meta) parts.push("Cmd");

  // Handle leader keybindings
  if (binding.leader) {
    parts.unshift("Ctrl+S");
  }

  let key = binding.key;
  // Format special keys
  if (key === " ") key = "Space";
  if (key === "ArrowUp") key = "↑";
  if (key === "ArrowDown") key = "↓";
  if (key === "ArrowLeft") key = "←";
  if (key === "ArrowRight") key = "→";

  parts.push(key);
  return parts.join("+");
}

/**
 * Check if a key event matches a binding
 * @param {KeyboardEvent} event
 * @param {Object} binding
 * @returns {boolean}
 */
function matchesBinding(event, binding) {
  if (!binding) return false;

  const keyMatch = event.key.toLowerCase() === binding.key.toLowerCase();
  const ctrlMatch = !!event.ctrlKey === !!binding.ctrl;
  const shiftMatch = !!event.shiftKey === !!binding.shift;
  const altMatch = !!event.altKey === !!binding.alt;
  const metaMatch = !!event.metaKey === !!binding.meta;

  return keyMatch && ctrlMatch && shiftMatch && altMatch && metaMatch;
}

/**
 * Subscribe to keymap changes
 * @param {Function} callback
 * @returns {Function} Unsubscribe function
 */
function subscribe(callback) {
  subscribers.add(callback);
  return () => subscribers.delete(callback);
}

/**
 * Notify all subscribers of changes
 */
function notifySubscribers() {
  subscribers.forEach((cb) => {
    try {
      cb(keymapCache);
    } catch (e) {
      console.error("Keymap subscriber error:", e);
    }
  });
}

/**
 * Export keymap to JSON string
 * @returns {string}
 */
function exportKeymap() {
  return JSON.stringify(loadKeymap(), null, 2);
}

/**
 * Import keymap from JSON string
 * @param {string} json
 * @returns {boolean}
 */
function importKeymap(json) {
  try {
    const parsed = JSON.parse(json);
    // Validate structure
    if (typeof parsed !== "object") return false;

    // Merge with defaults
    const merged = { ...DEFAULT_KEYMAP, ...parsed };
    saveKeymap(merged);
    return true;
  } catch (e) {
    console.error("Failed to import keymap:", e);
    return false;
  }
}

// Export API
export {
  buildLeaderTree,
  DEFAULT_KEYMAP,
  exportKeymap,
  formatBinding,
  getBinding,
  getBindingsByCategory,
  getKeymap,
  getLeaderNodeForPath,
  importKeymap,
  loadKeymap,
  matchesBinding,
  resetAllBindings,
  resetBinding,
  saveKeymap,
  setBinding,
  subscribe,
};

// Browser global
if (typeof window !== "undefined") {
  window.KeymapManager = {
    DEFAULT_KEYMAP,
    loadKeymap,
    saveKeymap,
    getKeymap,
    getBinding,
    setBinding,
    resetBinding,
    resetAllBindings,
    getBindingsByCategory,
    formatBinding,
    matchesBinding,
    subscribe,
    exportKeymap,
    importKeymap,
  };
}
