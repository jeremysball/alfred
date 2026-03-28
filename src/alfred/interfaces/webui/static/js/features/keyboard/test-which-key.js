import assert from "node:assert/strict";

function createMockElement(tagName) {
  const element = {
    tagName: String(tagName).toUpperCase(),
    className: "",
    children: [],
    parentNode: null,
    style: {},
    attributes: {},
    textContent: "",
    _innerHTML: "",
    classList: {
      _classes: new Set(),
      add(...classes) {
        classes.forEach((name) => this._classes.add(name));
      },
      remove(...classes) {
        classes.forEach((name) => this._classes.delete(name));
      },
      toggle(name, force) {
        if (force === true) {
          this._classes.add(name);
          return true;
        }

        if (force === false) {
          this._classes.delete(name);
          return false;
        }

        if (this._classes.has(name)) {
          this._classes.delete(name);
          return false;
        }

        this._classes.add(name);
        return true;
      },
      contains(name) {
        return this._classes.has(name);
      },
    },
    appendChild(child) {
      child.parentNode = this;
      this.children.push(child);
      return child;
    },
    get innerHTML() {
      return this._innerHTML;
    },
    set innerHTML(value) {
      this._innerHTML = String(value);
      this.children = [];
    },
    removeChild(child) {
      this.children = this.children.filter((candidate) => candidate !== child);
      child.parentNode = null;
      return child;
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return this.attributes[name];
    },
    querySelector(selector) {
      const matches = (node) => {
        if (!selector.startsWith(".")) {
          return false;
        }

        const className = selector.slice(1);
        const nodeClasses = String(node.className || "")
          .split(/\s+/)
          .filter(Boolean);
        return nodeClasses.includes(className);
      };

      const visit = (node) => {
        if (matches(node)) {
          return node;
        }

        for (const child of node.children || []) {
          const found = visit(child);
          if (found) {
            return found;
          }
        }

        return null;
      };

      return visit(this);
    },
    querySelectorAll(selector) {
      const results = [];

      const matches = (node) => {
        if (!selector.startsWith(".")) {
          return false;
        }

        const className = selector.slice(1);
        const nodeClasses = String(node.className || "")
          .split(/\s+/)
          .filter(Boolean);
        return nodeClasses.includes(className);
      };

      const visit = (node) => {
        if (matches(node)) {
          results.push(node);
        }

        for (const child of node.children || []) {
          visit(child);
        }
      };

      visit(this);
      return results;
    },
  };

  return element;
}

function setupDom() {
  const body = createMockElement("body");

  globalThis.document = {
    createElement: (tagName) => createMockElement(tagName),
    body,
    getElementById: () => null,
  };

  globalThis.window = {
    innerWidth: 1280,
    innerHeight: 800,
    dispatchEvent: () => {},
  };
}

function getItemText(item) {
  const key = item.children[0]?.textContent ?? "";
  const labelWrap = item.children[1];
  const label = labelWrap?.children[0]?.textContent ?? "";
  const description = labelWrap?.children[1]?.textContent ?? "";
  return { key, label, description };
}

function run() {
  setupDom();
}

run();

const { WhichKey } = await import("./which-key.js");

function test(name, fn) {
  try {
    fn();
    console.log(`✓ ${name}`);
  } catch (error) {
    console.error(`✗ ${name}`);
    console.error(`  Error: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  }
}

const derivedTreeFixture = [
  {
    key: "S",
    label: "Search",
    description: "Search tools",
    children: [
      {
        key: "M",
        label: "Messages",
        description: "Open messages",
        actionId: "search.messages",
      },
      {
        key: "Q",
        label: "Quick Switcher",
        description: "Open quick switcher",
        actionId: "search.quick-switcher",
      },
    ],
  },
  {
    key: "H",
    label: "Help",
    description: "Help tools",
    children: [
      {
        key: "H",
        label: "Keyboard help",
        description: "Open keyboard help",
        actionId: "help.open",
      },
    ],
  },
];

test("WhichKey renders a derived leader tree fixture without registry imports", () => {
  const whichKey = new WhichKey();

  whichKey.setBindings(derivedTreeFixture);
  whichKey.render();

  const rootGrid = whichKey.container.querySelector(".which-key-grid");
  assert.equal(rootGrid.children.length, 2);
  assert.deepEqual(getItemText(rootGrid.children[0]), {
    key: "S",
    label: "Search",
    description: "Search tools",
  });
  assert.deepEqual(getItemText(rootGrid.children[1]), {
    key: "H",
    label: "Help",
    description: "Help tools",
  });

  whichKey.activePath = ["S"];
  whichKey.render();

  const submenuGrid = whichKey.container.querySelector(".which-key-grid");
  assert.equal(submenuGrid.children.length, 2);
  assert.deepEqual(getItemText(submenuGrid.children[0]), {
    key: "M",
    label: "Messages",
    description: "Open messages",
  });
  assert.deepEqual(getItemText(submenuGrid.children[1]), {
    key: "Q",
    label: "Quick Switcher",
    description: "Open quick switcher",
  });
});

test("WhichKey header shows the current leader path", () => {
  const whichKey = new WhichKey();

  whichKey.setBindings(derivedTreeFixture);
  whichKey.activePath = ["S"];
  whichKey.render();

  const header = whichKey.container.querySelector(".which-key-header");
  assert.equal(header.textContent, "Leader + S");
});
