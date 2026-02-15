# OpenClaw Pi TODO

## Active Tasks

### High Priority

- [ ] **Testing**: Add E2E tests with real Telegram API
- [ ] **Error Handling**: Add retry logic for failed LLM calls
- [ ] **Monitoring**: Add health check endpoint

### Medium Priority

- [ ] **Shared Workspace**: Complete cross-thread file sharing
- [ ] **Skills**: Auto-load skills from workspace/skills/
- [ ] **Web UI**: Simple web dashboard for thread management

### Low Priority

- [ ] **Voice**: Add voice message support
- [ ] **Images**: Add image generation/understanding
- [ ] **Plugins**: Plugin system for custom commands

## Completed Recently

- [x] Token tracking from Pi session files
- [x] `/compact` command with LLM integration
- [x] `/verbose` command for Telegram logging
- [x] `/tokens` command for usage stats
- [x] Comprehensive test suite
- [x] Documentation (architecture, design, user guides)

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

## Ideas

- Slack/Discord bridge
- Multi-model routing (cheap vs expensive)
- Collaborative workspaces
- Scheduled tasks/cron jobs
