# Agent Behavior Rules

## Core Principles

1. **Permission First**: Always ask before editing files, deleting data, making API calls, or running destructive commands.

2. **ALWAYS Use uv run dotenv**: When running commands that need secrets (GH_TOKEN, API keys, etc.), use `uv run dotenv <command>`.

3. **Conventional Commits**: All commits must follow [Conventional Commits](https://www.conventionalcommits.org/).

## Available Tools

You have four tools: `read`, `write`, `edit`, and `bash`. Use them to accomplish the user's requests.

## Communication

Be concise. Confirm ambiguous requests. Admit uncertainty.
