#!/bin/bash

# Test Runner for Todo-Sidebar Extension
# This script runs the tests in TDD fashion

set -e

echo "🧪 Running Todo-Sidebar Extension Tests (TDD)"
echo "=============================================="
echo ""

# Check if vitest is installed
if ! command -v npx &> /dev/null; then
    echo "❌ Error: npx is not installed"
    exit 1
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Run tests
echo "Running tests..."
npx vitest run

echo ""
echo "✅ All tests passed!"
echo ""
echo "Next steps:"
echo "  - If tests fail: Fix the implementation"
echo "  - If tests pass: Move to next feature or refactor"
