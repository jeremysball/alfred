# Alfred - The Rememberer - Project Roadmap

This roadmap tracks the development of Alfred, an AI coding agent with persistent memory and contextual awareness.

## Completed

- [x] M1: Project Setup - Repository structure, tooling, CI/CD (PRD #11)
- [x] M2: Core Infrastructure - Configuration, context loading, prompt assembly (PRD #12)
- [x] M3: Memory Foundation - JSONL storage with embeddings (PRD #13)
- [x] M4: Vector Search - Semantic memory retrieval (PRD #14)
- [x] M5: Telegram Bot - Multi-user chat interface with CLI (PRD #15)
- [x] M6: Kimi Provider - Integration with Moonshot AI's Kimi API (PRD #16)
- [x] M7: Personality & Context - SOUL.md, USER.md, context assembly (PRD #17)
- [x] M8: Tool System - Built-in tools with Pydantic schemas (PRD #18)
- [x] Agent Loop - Streaming with tool execution (PRD #33)
- [x] Memory System V2 - Full CRUD operations (PRD #23)
- [x] PyPI Trusted Publishing - Automated package distribution (PRD #66)

## Short-term (Active Development)

- [ ] **Alfred v1.0 Vision** - Comprehensive PRD documenting architecture and roadmap (PRD #48)
- [ ] **Rich Markdown Output for CLI** - Streaming markdown-to-ANSI rendering (PRD #70)
- [ ] **README Landing Page** - Transform README into compelling OSS landing page (PRD #49)
- [ ] Fix Tool Class Type Safety - Resolve mypy override errors (PRD #44)
- [ ] Add Missing Type Annotations - Complete type coverage (PRD #45)
- [ ] Auto-Fix Ruff Violations - Clean up auto-fixable lint issues (PRD #46)
- [ ] Manual Lint Fixes - Fix remaining manual lint issues (PRD #47)

## Medium-term

- [ ] M9: Distillation - Auto-extract insights to MEMORY.md (PRD #20)
- [ ] M10: Learning - Auto-update USER.md from patterns (PRD #21)
- [ ] M11: Compaction - Summarize long conversations (PRD #19)
- [ ] M12: Testing & Quality - Comprehensive test coverage (PRD #22)
- [ ] HTTP API + Cron - Local API for scheduled actions (PRD #29)

## Long-term

- [ ] Config TOML Migration - Replace config.json with alfred.toml (PRD #30)
- [ ] Observability & Logging - Structured logging, tracing (PRD #25)

---

## Legend

- **Short-term**: Currently being worked on or next in queue
- **Medium-term**: Planned for upcoming development cycles
- **Long-term**: Future enhancements and advanced features

## How to Use This Roadmap

1. **View all PRDs**: Run `/prds-get` to see detailed PRD information
2. **Start working**: Run `/prd-start [issue-id]` to begin implementation
3. **Track progress**: PRDs are moved to `prds/done/` when completed
