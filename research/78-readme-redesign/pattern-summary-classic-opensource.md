# Pattern Summary: Classic Open Source

**Category**: Classic Open Source
**Projects Researched**: 5 (Redis, PostgreSQL, curl, SQLite, Git)
**Date**: 2026-02-19

---

## Executive Summary

Classic open source projects share a striking characteristic: **they don't try to sell you**. Their READMEs assume you already know what the software is, or you wouldn't be reading the source repository.

The spectrum ranges from **PostgreSQL** (18 lines, pure stub) to **Redis** (939 lines, comprehensive reference). The common thread: **trust through establishment, not marketing**.

These READMEs work because the projects have decades of history, massive adoption, and zero need to convince anyone of their value.

---

## Pattern 1: The Stub README

**Projects Using It**: PostgreSQL

**The Pattern**: Minimal content that points elsewhere.

```markdown
PostgreSQL Database Management System
=====================================

This directory contains the source code distribution...

For more information look at our web site...
```

**Why It Works**:
- Project is so established it needs no introduction
- Target audience is developers reading source code
- Website handles all user-facing documentation

**For Alfred**: NOT applicable. Requires 35+ years of establishment.

---

## Pattern 2: The Directory README

**Projects Using It**: curl

**The Pattern**: README serves as a navigation hub, not documentation.

```markdown
curl is a command-line tool for transferring data...

Learn how to use curl by reading the man page or everything curl.
Find out how to install curl by reading the INSTALL document.
```

**Why It Works**:
- Respects reader's time (no duplication)
- Points to authoritative docs elsewhere
- Each section is 1-2 sentences max

**For Alfred**: Applicable IF Alfred has a separate docs site. README becomes a pointer, not the content.

---

## Pattern 3: The Contributor README

**Projects Using It**: SQLite

**The Pattern**: README explicitly states it's for source code readers, not users.

```markdown
This README file is about the source code that goes into building SQLite,
not about how SQLite is used.
```

**Why It Works**:
- Clear audience segmentation
- Removes confusion immediately
- Delegates user content to website

**For Alfred**: Consider if GitHub README should target contributors while docs site targets users.

---

## Pattern 4: The Reference README

**Projects Using It**: Redis

**The Pattern**: README is both quick start AND comprehensive reference.

```markdown
- New to Redis? Start with What is Redis and Getting Started
- Ready to build from source? Jump to Build Redis from Source
- Want to contribute? See the Code contributions section
```

**Why It Works**:
- Navigation block at top serves all audiences
- Single document serves multiple purposes
- Deep technical content available when needed

**For Alfred**: Strong candidate. Navigation block + progressive disclosure.

---

## Pattern 5: The Personality Footer

**Projects Using It**: Git

**The Pattern**: Technical content first, personality reveal at the end.

```markdown
The name "git" was given by Linus Torvalds...

 - random three-letter combination...
 - stupid. contemptible and despicable...
 - "global information tracker": Angels sing...
 - "goddamn idiotic truckload of sh*t": when it breaks
```

**Why It Works**:
- Unexpected after dry technical content
- Self-deprecating (shows humility)
- Memorable and quotable
- Humanizes the project

**For Alfred**: Strong candidate. "Why is it called Alfred?" section at the end.

---

## Pattern 6: Protocol/Capability List

**Projects Using It**: curl, Redis

**The Pattern**: List what you support to demonstrate breadth.

**curl**: "It supports these protocols: DICT, FILE, FTP, FTPS, GOPHER, GOPHERS, HTTP, HTTPS, IMAP, IMAPS, LDAP, LDAPS, MQTT, MQTTS, POP3, POP3S, RTMP, RTMPS, RTSP, SCP, SFTP, SMB, SMBS, SMTP, SMTPS, TELNET, TFTP, WS and WSS."

**Redis**: 8 use cases listed with detailed explanations

**Why It Works**:
- Immediate capability demonstration
- Specifics beat generalities
- Shows maturity and completeness

**For Alfred**: List supported interfaces (Telegram, CLI), memory types, embedding models.

---

## Pattern 7: The Architectural Deep Dive

**Projects Using It**: SQLite, Redis

**The Pattern**: Explain how the system works at a technical level.

**SQLite**: "Source Tree Map" with file-by-file explanations
**Redis**: Data types, engines, and capabilities catalog

**Why It Works**:
- Demonstrates technical sophistication
- Serves as reference for contributors
- Shows thoughtfulness of design

**For Alfred**: Consider "How Alfred Works" section with memory architecture diagram.

---

## Anti-Patterns Observed

### 1. Zero Visuals
**All Projects**: None of the 5 classic projects have screenshots, diagrams, or GIFs.

**Problem**: Modern audiences expect visual content.

**Lesson**: Classic projects can get away with text-only. New projects cannot.

### 2. No Social Proof
**All Projects**: No stars, testimonials, or user counts mentioned.

**Problem**: For new projects, social proof is critical.

**Lesson**: Established projects have implicit social proof. New projects need explicit proof.

### 3. Assumes Prior Knowledge
**All Projects**: Assume reader knows what the software is.

**Problem**: New visitors may not understand the value proposition.

**Lesson**: New projects must explain themselves. Classic projects can skip it.

---

## Synthesis: What Alfred Can Steal

### Applicable Patterns

| Pattern | Source | Alfred Application |
|---------|--------|-------------------|
| Navigation Block | Redis | "New to Alfred?", "Ready to deploy?", "Want to contribute?" |
| Personality Footer | Git | "Why is it called Alfred?" with story |
| Capability List | curl, Redis | List interfaces, memory types, models |
| Progressive Docs | Git | Quick start → Everyday use → Full docs |
| Source Tree Map | SQLite | Explain directory structure for contributors |

### NOT Applicable

| Pattern | Source | Why Not |
|---------|--------|---------|
| Stub README | PostgreSQL | Alfred is not established |
| Zero visuals | All | Modern audiences expect visuals |
| No social proof | All | New projects need credibility signals |
| Assumes knowledge | All | Alfred needs to explain itself |

---

## Voice Spectrum

| Project | Personality | Length | Visuals | Trust Signal |
|---------|-------------|--------|---------|--------------|
| PostgreSQL | 0/10 | 18 lines | None | 35 years |
| curl | 1/10 | 60 lines | Logo | Ubiquity |
| SQLite | 2/10 | 250 lines | None | Public domain |
| Redis | 2/10 | 939 lines | None | Battle-tested |
| Git | 4/10 | 60 lines | Badge | Linus + humor |

**Key Insight**: Git scores highest on personality because of the name origin story. 2 sentences of humor in 400 words = memorable.

---

## The "Confidence vs. Effort" Tradeoff

Classic projects can use minimal READMEs because they have **confidence through establishment**:

| Project | Est. | README Length | Why Short Works |
|---------|------|---------------|-----------------|
| PostgreSQL | 1986 | 18 lines | Everyone knows PostgreSQL |
| curl | 1996 | 60 lines | De facto standard |
| SQLite | 2000 | 250 lines | Most deployed DB |
| Git | 2005 | 60 lines | Created by Linus |
| Redis | 2009 | 939 lines | Newest, needs more explanation |

**Pattern**: The older the project, the shorter the README can be.

**For Alfred**: Founded in 2026. Needs MORE explanation, not less.

---

## Key Metrics Comparison

| Metric | PostgreSQL | curl | SQLite | Git | Redis |
|--------|------------|------|--------|-----|-------|
| Lines | 18 | 60 | 250 | 60 | 939 |
| Word count | 100 | 200 | 2,000 | 400 | 5,000 |
| Time to read | 30s | 1m | 8m | 2m | 15m |
| Visuals | 0 | 1 | 0 | 1 | 0 |
| Badges | 0 | 0 | 0 | 1 | 1 |
| Personality | 0 | 1 | 2 | 4 | 2 |

---

## Recommended Structure for Alfred (from Classic OSS)

```markdown
# [Logo or Title]

[One-sentence value prop]

## Navigation
- New to Alfred? Start with [What is Alfred](#what-is-alfred)
- Ready to install? Jump to [Quick Start](#quick-start)
- Want to understand how it works? See [Architecture](#architecture)

## What is Alfred?
[2-3 paragraphs explaining value prop]

## Quick Start
[Install → First conversation in 3 steps]

## Capabilities
[List what Alfred supports: interfaces, memory types, models]

## Architecture
[How Alfred works: memory system, embeddings, retrieval]

## Contributing
[For contributors]

---

## Why "Alfred"?
[Personality footer - origin story with humor]
```

---

## Conclusion

Classic open source READMEs teach us:

1. **Brevity requires confidence** - Established projects can be short; new projects must explain
2. **Personality is optional but memorable** - Git's name origin is the most memorable thing across all 5
3. **Navigation matters more than marketing** - Help readers find what they need
4. **Delegation is valid** - Point to docs rather than duplicating
5. **Visuals are NOT required** - But this only works for established projects

**The fundamental insight**: These READMEs work because the projects have already won. Alfred has not. The lesson is not to copy their minimalism, but to understand WHY they can be minimal.
