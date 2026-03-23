# Template Sync and Conflict Recovery

This guide explains how Alfred keeps template-driven context files in sync, what happens when the workspace diverges, and how to recover from a conflict.

## Where sync state lives

Alfred writes template sync records to `XDG_CACHE_HOME/alfred/template-sync.json`.

Each record is scoped to one workspace path. Alfred ignores sync records that point at a different workspace, even if they share the same cache directory. That keeps restart recovery and conflict state tied to the current checkout.

The sync store is lazy-loaded. Alfred reads it when template reconciliation needs it, not at manager construction time.

## What happens on restart

When Alfred starts or reconnects, it reconciles each managed template through `TemplateManager.reconcile_template()`.

That reconciliation compares three things:

1. the current template file
2. the current workspace file
3. the saved base snapshot from the last clean sync

If the workspace still matches the saved base snapshot, Alfred fast-forwards the file to the current template content and refreshes the base snapshot.

If both the template and the workspace changed, Alfred writes standard git conflict markers into the workspace file and marks the file conflicted.

If the workspace already contains conflict markers, Alfred keeps the file blocked and leaves the markers in place. The app stays up, but the affected context file is unavailable until the conflict is fixed. This keeps the path fail closed.

## What a conflict looks like

Alfred uses the standard git marker format:

```md
<<<<<<< ours
Local workspace content
=======
Upstream template content
>>>>>>> theirs
```

Use those markers as the source of truth. Do not replace them with custom prose or a different conflict syntax.

## How Alfred warns you

A conflicted file is blocked from context loading. The `/context` command shows the blocked files and the warning text directly.

The WebUI uses the same warning payload, so the conflict is visible in the browser too. You do not need to inspect logs to see that a file is blocked.

The warning remains visible until Alfred sees a clean file again.

## Manual recovery

Follow this sequence when a template conflicts:

1. Open the conflicted file in the current workspace.
2. Decide which changes to keep.
3. Remove the conflict markers and leave clean Markdown behind.
4. Save the file.
5. Run Alfred again or reconnect so reconciliation can re-read the file.
6. Confirm that `/context` no longer reports the warning and that the WebUI clears it too.

If the warning does not clear, check that you edited the workspace copy Alfred is using. Sync records are workspace-scoped, so another checkout or stale cache entry will not apply.

## Quick recovery checklist

- Clean the file on disk.
- Keep the current workspace path.
- Re-run Alfred or reconnect.
- Verify the warning disappears.

If the file is clean and the warning still appears, treat that as a signal that the workspace and cache do not match.
