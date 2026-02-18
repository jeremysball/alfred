# Alfred - The Rememberer - Project Roadmap

This roadmap tracks the development of Alfred, an AI coding agent with persistent memory and contextual awareness.

## Completed

- [x] M1: Project Setup - Repository structure, tooling, CI/CD (PRD #11)
- [x] M2: Core Infrastructure - Configuration, context loading, prompt assembly (PRD #12)
- [x] M5: Telegram Bot - Multi-user chat interface with CLI (PRD #15)
- [x] M6: Kimi Provider - Integration with Moonshot AI's Kimi API (PRD #16)

## Short-term (Active Development)

- [ ] Fix Tool Class Type Safety - Resolve mypy override errors in tool classes (PRD #44)
- [ ] Add Missing Type Annotations - Complete type coverage for mypy strict mode (PRD #45)
- [ ] Auto-Fix Ruff Violations - Clean up 172 auto-fixable lint issues (PRD #46)
- [ ] Manual Lint Fixes - Fix remaining 23 manual lint issues (PRD #47)
- [ ] Kicking Ass README - Transform README into compelling OSS landing page (PRD #26)
- [ ] M3: Memory Foundation - Conversation history storage and retrieval (PRD #13)
- [ ] M4: Vector Search - Semantic memory search with embeddings (PRD #14)
- [ ] M7: Personality & Context - User modeling and preference learning (PRD #17)

## Medium-term

- [ ] HTTP API + Cron - Local API for scheduled actions via cron (PRD #29)
- [ ] M8: Capabilities - Tool use and function calling (PRD #18)
- [ ] M9: Compaction - Memory summarization and archival (PRD #19)
- [ ] M10: Distillation - Knowledge extraction and pattern learning (PRD #20)
- [ ] OpenClaw Template Evaluation - Assess OpenClaw framework compatibility (PRD #23)

## Long-term

- [ ] Config TOML Migration - Replace config.json with alfred.toml (PRD #30)
- [ ] M11: Learning System - Continuous improvement from interactions (PRD #21)
- [ ] M12: Testing & Quality - Comprehensive test coverage and quality gates (PRD #22)
- [ ] Observability & Logging - Structured logging, tracing, monitoring (PRD #25)

---

## Legend

- **Short-term**: Currently being worked on or next in queue
- **Medium-term**: Planned for upcoming development cycles
- **Long-term**: Future enhancements and advanced features

## How to Use This Roadmap

1. **View all PRDs**: Run `/prds-get` to see detailed PRD information
2. **Start working**: Run `/prd-start [issue-id]` to begin implementation
3. **Track progress**: PRDs are moved to `prds/done/` when completed
