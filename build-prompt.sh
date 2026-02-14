#!/usr/bin/env bash
# build-prompt.sh - Assemble .pi/SYSTEM.md from workspace context files
#
# Usage: ./build-prompt.sh [workspace_dir]
#
# Reads: workspace/AGENTS.md, SOUL.md, USER.md, IDENTITY.md, MEMORY.md, TOOLS.md, HEARTBEAT.md
# Writes: .pi/SYSTEM.md

set -euo pipefail

WORKSPACE="${1:-$(pwd)/workspace}"
DOT_PI="$(dirname "$0")/.pi"
SYSTEM_MD="$DOT_PI/SYSTEM.md"

# Context files to load (in order)
CONTEXT_FILES=(
    "AGENTS.md"
    "SOUL.md"
    "USER.md"
    "IDENTITY.md"
    "MEMORY.md"
    "TOOLS.md"
    "HEARTBEAT.md"
)

# Ensure .pi directory exists
mkdir -p "$DOT_PI"

# Build system prompt
{
    echo "# System Prompt"
    echo ""
    echo "You are a personal assistant."
    echo ""
    echo "## Safety"
    echo ""
    echo "You have no independent goals: do not pursue self-preservation, replication, resource acquisition, or power-seeking; avoid long-term plans beyond the user's request."
    echo ""
    echo "Prioritize safety and human oversight over completion; if instructions conflict, pause and ask; comply with stop/pause/audit requests and never bypass safeguards."
    echo ""
    echo "Do not manipulate or persuade anyone to expand access or disable safeguards."
    echo ""
    echo "## Workspace"
    echo ""
    echo "Your working directory is: $WORKSPACE"
    echo ""
    echo "# Project Context"
    echo ""
    echo "The following project context files have been loaded:"
    echo ""
    
    # Load each context file if it exists
    for file in "${CONTEXT_FILES[@]}"; do
        filepath="$WORKSPACE/$file"
        if [[ -f "$filepath" ]]; then
            echo "## $file"
            echo ""
            cat "$filepath"
            echo ""
            echo ""
        fi
    done
    
    # Load skills if directory exists
    SKILLS_DIR="$WORKSPACE/skills"
    if [[ -d "$SKILLS_DIR" ]]; then
        echo "# Skills"
        echo ""
        for skill_dir in "$SKILLS_DIR"/*/; do
            if [[ -d "$skill_dir" ]]; then
                skill_name=$(basename "$skill_dir")
                skill_md="$skill_dir/SKILL.md"
                if [[ -f "$skill_md" ]]; then
                    echo "## Skill: $skill_name"
                    echo ""
                    cat "$skill_md"
                    echo ""
                    echo ""
                fi
            fi
        done
    fi
    
    # Load today's memory file if it exists
    TODAY=$(date +%Y-%m-%d)
    TODAY_MEMORY="$WORKSPACE/memory/$TODAY.md"
    if [[ -f "$TODAY_MEMORY" ]]; then
        echo "## Daily Memory ($TODAY)"
        echo ""
        cat "$TODAY_MEMORY"
        echo ""
    fi
    
    # Load yesterday's memory too
    YESTERDAY=$(date -d "yesterday" +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d 2>/dev/null || echo "")
    if [[ -n "$YESTERDAY" ]]; then
        YESTERDAY_MEMORY="$WORKSPACE/memory/$YESTERDAY.md"
        if [[ -f "$YESTERDAY_MEMORY" ]]; then
            echo "## Daily Memory ($YESTERDAY)"
            echo ""
            cat "$YESTERDAY_MEMORY"
            echo ""
        fi
    fi
    
    echo "## Runtime"
    echo ""
    echo "Runtime: agent=pi | host=${HOSTNAME:-localhost} | os=$(uname -s) $(uname -r) | pwd=$WORKSPACE"
    echo ""

} > "$SYSTEM_MD"

echo "Built: $SYSTEM_MD ($(wc -l < "$SYSTEM_MD") lines)"
