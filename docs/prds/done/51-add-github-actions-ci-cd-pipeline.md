# PRD: Add GitHub Actions CI/CD Pipeline

## Overview

**Issue**: #51
**Status**: Planning
**Priority**: High
**Created**: 2026-02-18

Add automated CI/CD via GitHub Actions to catch code quality issues before merge and enable automated PyPI releases.

---

## Problem Statement

1. **No CI enforcement** — Pre-commit hooks exist but require manual setup (`uv run pre-commit install`). Developers can skip them.
2. **No automated releases** — Publishing to PyPI is a manual process.
3. **No dependency scanning** — Security vulnerabilities in dependencies go undetected.

---

## Solution Overview

### CI Pipeline (On Push + PR)
- **Lint**: `ruff check src/`
- **Type Check**: `mypy src/`
- **Test**: `pytest` with coverage
- **Platform**: Python 3.12 on Linux

### CD Pipeline (On Git Tag)
- **Build**: Create distribution packages
- **Publish**: Upload to PyPI automatically on `v*` tags

### Dependency Management
- **Dependabot**: Weekly checks for pip dependencies

### Trackable Pre-commit Hooks
- Move hook script to `.githooks/` folder
- Configure git via `core.hooksPath`
- Add setup instruction to README

---

## Technical Architecture

### File Structure
```
.github/
├── workflows/
│   ├── ci.yml           # Lint, type-check, test
│   └── publish.yml      # PyPI release on tag
├── dependabot.yml       # Dependency updates
└── PULL_REQUEST_TEMPLATE.md (existing)

.githooks/
└── pre-commit           # Trackable hook script
```

### CI Workflow (`ci.yml`)
**Triggers**: push to main, pull_request

**Jobs**:
1. **Lint** — `uv run ruff check src/`
2. **Type Check** — `uv run mypy src/`
3. **Test** — `uv run pytest --cov`

### Publish Workflow (`publish.yml`)
**Triggers**: push tags `v*`

**Jobs**:
1. **Build** — Create wheel and sdist
2. **Publish to PyPI** — Uses trusted publishing (no API key needed)

### Dependabot (`dependabot.yml`)
- **Ecosystem**: pip (pyproject.toml)
- **Schedule**: Weekly
- **Limit**: 5 open PRs

---

## Milestones

| # | Milestone | Description |
|---|-----------|-------------|
| 1 | CI Workflow | Add `.github/workflows/ci.yml` with lint, type-check, test |
| 2 | Publish Workflow | Add `.github/workflows/publish.yml` for PyPI releases |
| 3 | Dependabot | Add `.github/dependabot.yml` for dependency scanning |
| 4 | Trackable Hooks | Create `.githooks/pre-commit` and update README with setup |
| 5 | Documentation | Update README with CI/CD badge and setup instructions |

---

## Environment Variables

### GitHub Actions (Secrets)
- `PYPI_API_TOKEN` — For publishing (alternative: Trusted Publishing)

### Local Setup
- `uv run pre-commit install` — Install hooks (one-time setup)

---

## Success Criteria

- [ ] CI runs on every push to main and every PR
- [ ] CI fails if ruff, mypy, or pytest fail
- [ ] Pushing a `v*` tag publishes to PyPI
- [ ] Dependabot creates weekly dependency update PRs
- [ ] Pre-commit hooks are trackable and documented
- [ ] README includes CI status badge

---

## Dependencies

- GitHub repository with Actions enabled
- PyPI account (for publishing)
- `uv` for dependency management (already in use)

---

## Decision Log

| Date | Decision | Rationale | Impact |
|------|----------|-----------|--------|
| 2026-02-18 | Single Python version (3.12) | Project targets 3.12 only | Simpler CI matrix |
| 2026-02-18 | Linux only | No platform-specific code | Faster CI |
| 2026-02-18 | Keep pre-commit + CI | Local fast feedback + enforced CI | Both layers of quality |
| 2026-02-18 | Trackable hooks via .githooks | Allows committing hook script | New directory, git config change |
