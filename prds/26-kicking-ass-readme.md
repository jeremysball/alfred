# PRD: Kicking Ass README

## Overview

**Issue**: #26
**Parent**: #10 (Alfred - The Rememberer)
**Status**: Planning
**Priority**: High
**Created**: 2026-02-17

Transform README from functional documentation into a compelling project landing page that showcases Alfred's value and makes adoption frictionless.

---

## Problem Statement

The current README works but doesn't sell Alfred. It lacks:

1. **Visual polish** - No badges, no screenshots, no demo
2. **Clear value proposition** - "Remembers everything" doesn't explain why that matters
3. **Professional credibility** - Missing build status, version, license badges
4. **Usage examples** - No code showing Alfred in action
5. **Contribution path** - References non-existent CONTRIBUTING.md
6. **Roadmap visibility** - Users can't see where the project is headed

For an OSS project to attract users and contributors, the README is the first impression. It needs to immediately communicate: "This is useful. This is legit. This is easy to try."

---

## Solution

Restructure README following OSS best practices with these improvements:

### 1. Add Badges (Trust Signals)
- License (MIT)
- Build status (GitHub Actions)
- Python version
- Code style (ruff)

### 2. Rewrite Value Proposition
Lead with the problem Alfred solves, not just what it does. Answer "Why Alfred?" before explaining "What Alfred does."

### 3. Add Visual Elements
- Keep Memory Moth banner
- Add screenshot or ASCII demo showing conversation flow
- Consider GIF of Alfred remembering context across sessions

### 4. Structure for Scanning
- Clear sections with visual hierarchy
- Bullet points for features, not paragraphs
- Code examples that actually work
- Collapse dev setup for users who just want to try it

### 5. Fix Broken References
- Create CONTRIBUTING.md or remove the link
- Ensure all referenced files exist
- Add Architecture section or link to docs

### 6. Add Roadmap Section
- Link to open issues/milestones
- Show what's coming next
- Invite contributors to specific areas

---

## Acceptance Criteria

- [ ] README follows OSS template structure
- [ ] Badges display correctly (license, build, python)
- [ ] Clear 2-3 sentence value proposition above the fold
- [ ] Working code example showing Alfred in action
- [ ] All referenced files exist (CONTRIBUTING.md or removed)
- [ ] Visual demo (screenshot/GIF/ASCII) shows Alfred remembering
- [ ] Roadmap section with link to issues
- [ ] Mobile-friendly (no broken tables on narrow screens)
- [ ] Grammar and spelling verified

---

## File Changes

### README.md (Rewrite)
```
# Alfred - The Rememberer

[Badges row]

[Banner image]

[Value proposition - 2-3 sentences answering "Why Alfred?"]

## Features
[Scannable bullet list with concrete benefits]

## Quick Start
[Minimal working example - 3 commands max]

## How It Works
[Architecture diagram or brief explanation]

## Documentation
[Link to docs/ directory]

## Roadmap
[Link to issues, key upcoming features]

## Contributing
[Link to CONTRIBUTING.md or brief guide]

## License
MIT
```

### CONTRIBUTING.md (New - Optional)
If created, include:
- Development setup
- Code style (ruff, mypy)
- PR process
- Testing requirements

### docs/ROADMAP.md (New - Optional)
If created:
- Short-term goals
- Medium-term goals
- Long-term vision

---

## Milestones

1. **Value Proposition & Badges**
   - Rewrite opening with clear "Why Alfred" messaging
   - Add 3-4 badges (license, build, python, style)

2. **Visual Demo**
   - Add screenshot or ASCII demo showing Alfred remembering context
   - Consider session recording or GIF

3. **Structure & Navigation**
   - Reorganize sections for scannability
   - Add table of contents for long sections
   - Ensure mobile-friendly formatting

4. **Fix Broken References**
   - Create CONTRIBUTING.md OR remove reference
   - Verify all links work
   - Ensure code examples are copy-pasteable

5. **Roadmap & Community**
   - Add Roadmap section linking to issues
   - Add "Good First Issue" link if applicable
   - Invite contributions to specific areas

---

## README Structure (Target)

```markdown
# Alfred - The Rememberer

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Build Status](https://img.shields.io/github/actions/workflow/status/jeremysball/alfred/ci.yml)](https://github.com/jeremysball/alfred/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-orange.svg)](https://docs.astral.sh/ruff/)

![Memory Moth Banner](docs/assets/memory-moth-banner.png)

A persistent memory-augmented LLM assistant that remembers conversations across sessions. Alfred builds understanding of you over time, recalling relevant context without being asked.

## Why Alfred?

Most AI assistants start fresh every conversation. Alfred remembers. He learns your preferences, recalls past discussions, and brings relevant context into current chats automatically. No more repeating yourself or pasting old conversations.

## Features

- **Persistent Memory** - Every conversation stored and indexed
- **Contextual Recall** - Relevant memories surface automatically
- **Adaptive Personality** - Matches your communication style over time
- **Privacy-First** - All memory stored locally, you control the data

## Quick Start

### Try It Now

```bash
pip install alfred
export TELEGRAM_BOT_TOKEN=your_token
export OPENAI_API_KEY=your_key
alfred
```

### See It In Action

[Demo showing Alfred remembering previous conversation]

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
- [API Reference](docs/API.md)

## Roadmap

See [open issues](https://github.com/jeremysball/alfred/issues) for planned features. Current focus:

- [ ] Vector-based memory search
- [ ] Multi-user support
- [ ] Web interface

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

[MIT](LICENSE)
```

---

## Success Metrics

How we'll know the README is working:

1. **Clarity** - New user can explain what Alfred does in one sentence after reading
2. **Credibility** - Badges and structure convey "legit OSS project"
3. **Actionable** - User can get running in < 5 minutes
4. **Inviting** - Contributor knows where to start

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-17 | Follow OSS template | Alfred is an OSS project targeting contributors and users | Provides proven structure |
| 2026-02-17 | Add visual demo | Text description doesn't convey "memory" capability | Need screenshot or ASCII demo |
| 2026-02-17 | Keep banner | Memory Moth is unique branding | Visual identity established |
