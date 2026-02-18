# PRD: Alfred README - OSS Landing Page

## Overview

**Issue**: #49
**Status**: Planning
**Priority**: High
**Created**: 2026-02-18
**Supersedes**: #26

Transform Alfred's README from a functional reference into a compelling landing page that motivates developers to try Alfred and contributors to join.

---

## Problem Statement

The current README explains *how* to use Alfred but not *why* anyone should care. It lacks:
- A clear value proposition
- Emotional hook or memorable framing
- Compelling examples that show Alfred's uniqueness
- Clear differentiation from other AI assistants

---

## Solution Overview

Rewrite the README following OSS landing page best practices:

1. **Hook**: Lead with what makes Alfred different (persistent memory)
2. **Demonstrate**: Show, don't tell — real examples of Alfred remembering
3. **Quick Start**: Fastest path to "wow" moment
4. **Differentiators**: Clear comparison to alternatives
5. **Contributing**: Lower barrier to entry

---

## Target Audience

**Primary**: Individual developers who want an AI assistant that remembers them

**Secondary**: Contributors interested in AI agents, memory systems, or LLM tooling

---

## README Structure

### 1. Hero Section
- Memorable tagline
- One-sentence value proposition
- Visual (banner image already exists)

### 2. The Problem (Brief)
- 2-3 sentences on why current assistants are frustrating
- User pain point: repeating yourself, losing context

### 3. The Alfred Difference
- Memory persistence visualization
- Example conversation showing recall

### 4. Quick Start
- Minimal steps to running Alfred
- One command to try it
- Link to detailed setup

### 5. Features
- Bullet list of capabilities
- Link to full documentation

### 6. How It Works (Brief)
- Architecture diagram or simple explanation
- Not a deep dive — just enough to understand

### 7. Contributing
- How to get started
- Link to AGENTS.md or contributing guide

### 8. License
- MIT (brief)

---

## Key Messages

### Tagline Options
- "The AI assistant that actually remembers you"
- "Your AI, with long-term memory"
- "Chat with context that persists"

### Value Proposition
Alfred remembers every conversation. Ask about something you discussed months ago — he recalls it. No more repeating yourself. No more lost context.

### Differentiation
| Feature | Alfred | ChatGPT | Claude |
|---------|--------|---------|--------|
| Persistent Memory | ✅ Forever | ❌ Per session | ❌ Per session |
| Local Storage | ✅ Your files | ❌ Cloud only | ❌ Cloud only |
| Custom Personality | ✅ Edit SOUL.md | ❌ Fixed | ❌ Fixed |
| Tool Access | ✅ Read/write/bash | Limited | Limited |

---

## Style Guidelines

From `crafting-effective-readmes` skill:

1. **Be specific, not grandiose** — Say what Alfred actually does, not "revolutionary" or "groundbreaking"
2. **Omit needless words** — Every sentence earns its place
3. **Use active voice** — "Alfred remembers" not "Memories are stored"
4. **Concrete examples** — Real conversations, not hypotheticals
5. **No puffery** — Avoid "seamless", "robust", "cutting-edge"

---

## What Stays / What Goes

### Keep (Updated)
- Banner image
- Quick start section
- Docker instructions (moved to bottom)
- Template system docs (condensed)

### Rewrite
- Introduction → Hero + value prop
- "What Alfred Does" → Problem + solution
- Features → Differentiators + examples

### Remove
- Redundant configuration details (link to docs)
- Verbose troubleshooting (link to wiki/docs)

---

## Success Criteria

- [ ] New visitor understands Alfred's value in <30 seconds
- [ ] Clear path from landing to first conversation
- [ ] Differentiation from alternatives is obvious
- [ ] README length under 200 lines
- [ ] All links work and point to correct locations

---

## Milestones

- [x] **Draft Complete**: New README written following structure above
- [x] **Review Pass**: Applied writing-clearly-and-concisely skill (active voice, no puffery, removed em-dashes)
- [x] **Visual Enhancement**: Added Mermaid architecture diagram to "How It Works"
- [x] **Links Verified**: AGENTS.md link validated, all references correct

---

## References

- Current README: `/workspace/alfred-prd/README.md`
- Crafting Effective READMEs skill: `.pi/skills/crafting-effective-readmes/`
- Writing Clearly skill: `.pi/skills/writing-clearly-and-concisely/`
- OSS README template: `.pi/skills/crafting-effective-readmes/templates/oss.md`

---

## Notes

- Keep Docker/deployment details — they're useful but secondary
- Template system is a differentiator — keep it visible
- Don't oversell; Alfred is early-stage but functional
