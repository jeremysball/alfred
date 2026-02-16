#!/usr/bin/env bash
# run.sh - Build system prompt and run pi agent
#
# Usage: ./run.sh [workspace_dir] [-- pi args...]
#
# Examples:
#   ./run.sh                          # Use ./workspace
#   ./run.sh /path/to/project         # Use specific workspace
#   ./run.sh . -- --model claude-sonnet-4-20250514  # Pass args to pi

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORKSPACE="${1:-$SCRIPT_DIR/workspace}"

# Shift workspace arg if provided
if [[ $# -gt 0 && ! "$1" == "--" ]]; then
    shift
fi

# Handle -- separator for pi args
PI_ARGS=()
if [[ $# -gt 0 ]]; then
    if [[ "$1" == "--" ]]; then
        shift
    fi
    PI_ARGS=("$@")
fi

# Build the system prompt
"$SCRIPT_DIR/build-prompt.sh" "$WORKSPACE"

# Run pi with workspace as cwd
# pi will automatically load .pi/SYSTEM.md
cd "$WORKSPACE"
exec pi "${PI_ARGS[@]}"
