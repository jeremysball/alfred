#!/usr/bin/env bash
# ask.sh - One-shot: build prompt and send a single message to pi
#
# Usage: ./ask.sh "your message here" [workspace_dir]
#
# Example:
#   ./ask.sh "What files are in this project?"
#   ./ask.sh "Review the code in src/" /path/to/project

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MESSAGE="${1:-}"
WORKSPACE="${2:-$SCRIPT_DIR/workspace}"

if [[ -z "$MESSAGE" ]]; then
    echo "Usage: $0 \"your message\" [workspace_dir]" >&2
    exit 1
fi

# Build the system prompt
"$SCRIPT_DIR/build-prompt.sh" "$WORKSPACE"

# Run pi with the message, exit after response
cd "$WORKSPACE"

# Use printf to handle the message safely, pipe to pi
# --no-interactive tells pi to exit after processing
printf '%s\n' "$MESSAGE" | pi --no-interactive 2>/dev/null || {
    # Fallback if --no-interactive doesn't exist
    # Just send the message and capture output
    timeout 60 pi <<< "$MESSAGE" 2>/dev/null || pi <<< "$MESSAGE"
}
