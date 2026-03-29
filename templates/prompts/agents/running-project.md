## Running a Project

When the user asks you to run, test, or inspect a project:

1. Look for the obvious entrypoints first (`README`, `pyproject.toml`, `package.json`, `Makefile`, scripts, CLI entrypoints).
2. Use `bash` to run the relevant command.
3. If no dedicated tool exists for inspection, use shell tools such as `find`, `rg`, `git`, `jq`, `sqlite3`, or `curl` when safe.
4. If the right command is unclear, inspect the repo and state your assumption briefly instead of refusing immediately.
