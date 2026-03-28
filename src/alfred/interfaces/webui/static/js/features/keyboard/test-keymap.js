import assert from "node:assert/strict";

import { buildLeaderTree, DEFAULT_KEYMAP, formatBinding } from "./keymap.js";

function run() {
  const fixtureKeymap = {
    ...DEFAULT_KEYMAP,
    "editor.archive": {
      key: "a",
      description: "Archive current conversation",
      category: "Editor",
      leader: {
        path: [
          {
            key: "a",
            label: "Archive",
            description: "Archive current conversation",
          },
        ],
      },
    },
    "editor.openFile": {
      key: "f",
      description: "Open a file",
      category: "Editor",
      leader: {
        path: [
          {
            key: "o",
            label: "Open",
            description: "Open resources",
          },
          {
            key: "f",
            label: "File",
            description: "Open a file",
          },
        ],
      },
    },
    "editor.openFolder": {
      key: "d",
      description: "Open a folder",
      category: "Editor",
      leader: {
        path: [
          {
            key: "o",
            label: "Open",
            description: "Open resources",
          },
          {
            key: "d",
            label: "Folder",
            description: "Open a folder",
          },
        ],
      },
    },
    "editor.toggleSidebar": {
      key: "b",
      ctrl: true,
      description: "Toggle sidebar",
      category: "Editor",
    },
  };

  assert.equal(formatBinding(DEFAULT_KEYMAP["composer.leader"]), "Ctrl+S");

  const tree = buildLeaderTree(fixtureKeymap);

  assert.deepStrictEqual(tree, [
    {
      key: "a",
      label: "Archive",
      description: "Archive current conversation",
      actionId: "editor.archive",
    },
    {
      key: "o",
      label: "Open",
      description: "Open resources",
      children: [
        {
          key: "d",
          label: "Folder",
          description: "Open a folder",
          actionId: "editor.openFolder",
        },
        {
          key: "f",
          label: "File",
          description: "Open a file",
          actionId: "editor.openFile",
        },
      ],
    },
  ]);
}

try {
  run();
  console.log("✓ leader tree derives from canonical registry fixture");
  console.log("✓ composer.leader formats as Ctrl+S");
} catch (error) {
  console.error("✗ leader tree derives from canonical registry fixture");
  console.error(`  Error: ${error instanceof Error ? error.message : String(error)}`);
  process.exit(1);
}
