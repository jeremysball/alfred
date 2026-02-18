# TODO

## PRD Tasks

### Active PRDs
- [x] **#54** - In-Memory Session Storage - Foundation for CLI conversation memory ✓ COMPLETE
  - [x] Session data model (Session, Message, Role)
  - [x] SessionManager singleton
  - [x] Context integration (session history in LLM context)
  - [x] CLI wiring (auto-start session, add user/assistant messages)
  - [x] Tests: 28 new tests, all passing

### Next PRDs
- [ ] **#55** - Advanced Session Features - LLM context control, substring search
- [ ] **#53** - Full Session System - Persistence, summarization, multi-session

### Other PRDs
- [ ] Create PRD for making default behavior not print tool information (add flag to enable it)
- [ ] Create PRD for CLI commands (sessions, resume, newsession, etc.)
- [ ] Create PRD for a throbber

## Bugs / Technical Debt
- [ ] Fix templates not being copied to data folder on startup
- [ ] ContextAssembler loads from templates - make this configurable (data vs templates priority)
