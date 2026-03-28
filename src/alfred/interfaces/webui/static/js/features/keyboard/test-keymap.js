import assert from "node:assert/strict";

import { buildLeaderTree, DEFAULT_KEYMAP, formatBinding, getLeaderNodeForPath } from "./keymap.js";

function run() {
  const fixtureKeymap = {
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

  const registryTree = buildLeaderTree(DEFAULT_KEYMAP);

  assert.deepStrictEqual(DEFAULT_KEYMAP["help.open"].leader.path, [
    {
      key: "h",
      label: "Help",
      description: "Help and information",
    },
    {
      key: "h",
      label: "Keyboard help",
      description: "Open keyboard shortcuts help",
    },
  ]);

  assert.equal(DEFAULT_KEYMAP["help.open.leader.question"], undefined);

  assert.deepStrictEqual(getLeaderNodeForPath(registryTree, ["h", "h"]), {
    key: "h",
    label: "Keyboard help",
    description: "Open keyboard shortcuts help",
    actionId: "help.open",
  });

  assert.deepStrictEqual(getLeaderNodeForPath(registryTree, ["c", "enter"]), {
    key: "Enter",
    label: "Queue message",
    description: "Queue message",
    actionId: "composer.queue",
  });

  assert.throws(
    () =>
      buildLeaderTree({
        ...DEFAULT_KEYMAP,
        "duplicate.one": {
          key: "x",
          description: "Duplicate one",
          category: "Editor",
          leader: {
            path: [
              {
                key: "x",
                label: "Duplicate",
                description: "Duplicate group",
              },
            ],
          },
        },
        "duplicate.two": {
          key: "y",
          description: "Duplicate two",
          category: "Editor",
          leader: {
            path: [
              {
                key: "x",
                label: "Duplicate",
                description: "Duplicate group",
              },
            ],
          },
        },
      }),
    /Duplicate leader path: x/,
  );

  assert.throws(
    () =>
      buildLeaderTree({
        ...DEFAULT_KEYMAP,
        "conflict.one": {
          key: "z",
          description: "Conflict one",
          category: "Editor",
          leader: {
            path: [
              {
                key: "z",
                label: "Zoom",
                description: "Zoom actions",
              },
            ],
          },
        },
        "conflict.two": {
          key: "z",
          description: "Conflict two",
          category: "Editor",
          leader: {
            path: [
              {
                key: "z",
                label: "Zap",
                description: "Zap actions",
              },
            ],
          },
        },
      }),
    /Conflicting leader metadata for z/,
  );

  assert.throws(
    () =>
      buildLeaderTree({
        ...DEFAULT_KEYMAP,
        "prefix.leaf": {
          key: "o",
          description: "Open group leaf",
          category: "Editor",
          leader: {
            path: [
              {
                key: "o",
                label: "Open",
                description: "Open resources",
              },
            ],
          },
        },
        "prefix.child": {
          key: "f",
          description: "Open nested file",
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
                description: "Open nested file",
              },
            ],
          },
        },
      }),
    /Leader path collides with an existing leaf: o/,
  );
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
