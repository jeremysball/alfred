#!/usr/bin/env bash
# setup.sh - Install pi-coding-agent and set up workspace
#
# Usage: ./setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd"

echo "=== Installing pi-coding-agent ==="

# Check if npm is available
if ! command -v npm &>/dev/null; then
    echo "Error: npm is required but not installed." >&2
    exit 1
fi

# Install pi globally
npm install -g @mariozechner/pi-coding-agent

# Verify installation
if ! command -v pi &>/dev/null; then
    echo "Error: pi was installed but not found in PATH" >&2
    exit 1
fi

echo "✓ pi installed: $(pi --version 2>/dev/null || echo 'version unknown')"

# Set up workspace
echo ""
echo "=== Setting up workspace ==="

mkdir -p "$SCRIPT_DIR/workspace/memory"
mkdir -p "$SCRIPT_DIR/workspace/skills"
mkdir -p "$SCRIPT_DIR/.pi"

# Copy templates if workspace is empty
if [[ ! -f "$SCRIPT_DIR/workspace/AGENTS.md" ]]; then
    cp "$SCRIPT_DIR/templates/AGENTS.md" "$SCRIPT_DIR/workspace/"
    echo "✓ Copied AGENTS.md template"
fi

for file in SOUL.md USER.md IDENTITY.md TOOLS.md HEARTBEAT.md; do
    if [[ ! -f "$SCRIPT_DIR/workspace/$file" && -f "$SCRIPT_DIR/templates/$file" ]]; then
        cp "$SCRIPT_DIR/templates/$file" "$SCRIPT_DIR/workspace/"
        echo "✓ Copied $file template"
    fi
done

# Build initial system prompt
"$SCRIPT_DIR/build-prompt.sh" "$SCRIPT_DIR/workspace"

echo ""
echo "=== Setup complete ==="
echo ""
echo "To run the agent:"
echo "  cd $SCRIPT_DIR"
echo "  ./run.sh"
echo ""
echo "Or one-shot:"
echo "  ./ask.sh \"What files are in this project?\""
echo ""
echo "Set your API key first:"
echo "  export ANTHROPIC_API_KEY=sk-ant-..."
