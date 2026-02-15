# Alfred TODO

## Active Tasks

### High Priority

- [x] **Fix Documentation**: Remove all references to "persistent Pi processes" (never existed)
  - [x] alfred/telegram_bot.py docstrings
  - [x] alfred/telegram_bot.py /start message
- [x] **Integrate telegramify-markdown**: Use telegramify() for native entity rendering
  - [x] Add dependency
  - [x] Create _send_markdown() helper
  - [x] Replace reply_text() calls with entity-based sending
- [x] **AGENTS.md**: Document telegramify-markdown usage

### Medium Priority

- [ ] **Testing**: Add E2E tests with real Telegram API
- [ ] **Error Handling**: Add retry logic for failed LLM calls
- [ ] **Monitoring**: Add health check endpoint
- [ ] **Shared Workspace**: Complete cross-thread file sharing
- [ ] **Skills**: Auto-load skills from workspace/skills/

### Low Priority

- [ ] **Web UI**: Simple web dashboard for thread management
- [ ] **Voice**: Add voice message support
- [ ] **Images**: Add image generation/understanding
- [ ] **Plugins**: Plugin system for custom commands

## Completed Recently

- [x] Rename project to Alfred
- [x] Add BELIEFS.md with core principles
- [x] Add AGENTS.md with guidelines
- [x] Add table rendering (Playwright approach - being replaced)
- [x] Token tracking from Pi session files
- [x] `/compact` command with LLM integration
- [x] `/verbose` command for Telegram logging
- [x] `/tokens` command for usage stats
- [x] Comprehensive test suite

## Backlog

### Performance
- [ ] Cache embeddings for semantic search
- [ ] Batch token sync operations
- [ ] Optimize thread loading for large histories

### Security
- [ ] Encrypt sensitive session files
- [ ] Rate limiting per user
- [ ] Audit logging

### DevOps
- [ ] Docker containerization
- [ ] CI/CD pipeline
- [ ] Automated releases
