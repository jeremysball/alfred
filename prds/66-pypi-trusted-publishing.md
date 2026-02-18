# PRD: PyPI Trusted Publishing Setup

**Issue**: #66
**Status**: Planning
**Priority**: Medium
**Created**: 2026-02-18

---

## Overview

Set up automated PyPI publishing using Trusted Publishers (OIDC) so users can install Alfred via `pip install alfred-assistant`.

---

## Problem Statement

Currently, Alfred requires manual installation by cloning the repository and setting up a Python environment with `uv`. This creates friction for users who want to try Alfred quickly. We need:

1. A published package on PyPI for easy installation
2. Automated publishing workflow that doesn't require manual API token management
3. TestPyPI integration for validating releases before production

---

## Solution Overview

### Publishing Strategy

| Trigger | Target | Purpose |
|---------|--------|---------|
| Push to `main` | TestPyPI | Validate package build, test installation |
| Git tag `v*` | Production PyPI | Official release |

### Technology Choices

- **Trusted Publishing**: OIDC-based authentication (no API tokens stored in GitHub)
- **uv publish**: Native uv support for publishing (cleaner than twine)
- **GitHub Actions**: CI/CD workflow for automation

---

## Technical Architecture

### Package Configuration

The following fields need to be added to `pyproject.toml`:

```toml
[project]
name = "alfred-assistant"
dynamic = ["version"]
description = "Persistent memory-augmented LLM assistant"
readme = "README.md"
license = {text = "MIT"}
requires-python = ">=3.12"
authors = [
    {name = "Jeremy Ball", email = "jeremy@example.com"}
]
keywords = ["llm", "assistant", "memory", "ai", "telegram", "cli"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3.14",
    "Topic :: Communications :: Chat",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
]

[project.urls]
Homepage = "https://github.com/jeremysball/alfred"
Repository = "https://github.com/jeremysball/alfred"
Issues = "https://github.com/jeremysball/alfred/issues"
```

### Version Management

Use `uv-dynamic-versioning` or similar to extract version from git tags:
- Initial version: `0.1.0`
- Semantic versioning for all releases

### Trusted Publisher Configuration

#### PyPI Setup
1. Go to https://pypi.org/manage/account/publishing/
2. Add new pending publisher:
   - **PyPI Project Name**: `alfred-assistant`
   - **Owner**: `jeremysball`
   - **Repository**: `alfred`
   - **Workflow**: `release.yml`
   - **Environment**: `pypi`

#### TestPyPI Setup
1. Go to https://test.pypi.org/manage/account/publishing/
2. Add same configuration for TestPyPI

### CI/CD Workflow

```yaml
# .github/workflows/release.yml
name: Publish to PyPI

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  publish-testpypi:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: testpypi
    permissions:
      id-token: write  # Required for OIDC
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Build package
        run: uv build
      - name: Publish to TestPyPI
        run: uv publish --publish-url https://test.pypi.org/legacy/

  publish-pypi:
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    environment: pypi
    permissions:
      id-token: write  # Required for OIDC
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
      - name: Build package
        run: uv build
      - name: Publish to PyPI
        run: uv publish
```

---

## Roadmap to Completion

| # | Milestone | Status | Description |
|---|-----------|--------|-------------|
| M1 | Package Metadata | ✅ Done | Add required fields to pyproject.toml (description, readme, license, classifiers, urls) |
| M2 | Version Management | Todo | Set up dynamic versioning from git tags, initial version 0.1.0 |
| M3 | PyPI Trusted Publisher | Todo | Configure pending publisher on PyPI (production) |
| M4 | TestPyPI Trusted Publisher | Todo | Configure pending publisher on TestPyPI |
| M5 | GitHub Environments | ✅ Done | Create `pypi` and `testpypi` environments with protection rules |
| M6 | CI/CD Workflow | ✅ Done | Create release.yml workflow for TestPyPI (main branch) and PyPI (tags) |
| M7 | Test Release | Todo | Push to main, verify TestPyPI package builds and installs |
| M8 | Production Release | Todo | Create git tag v0.1.0, verify PyPI release |

---

## Success Criteria

- [ ] Package `alfred-assistant` available on PyPI
- [ ] `pip install alfred-assistant` works correctly
- [ ] Every push to main publishes to TestPyPI
- [ ] Every git tag `v*` publishes to production PyPI
- [ ] No API tokens stored in GitHub (using OIDC only)
- [ ] Package includes proper metadata (description, license, classifiers)

---

## Dependencies

| Tool | Purpose |
|------|---------|
| `uv` | Build and publish package |
| `uv-dynamic-versioning` | Extract version from git tags |
| GitHub Actions | CI/CD automation |
| PyPI Trusted Publishing | Secure authentication |

---

## Environment Variables (GitHub)

None required - using OIDC trusted publishing instead of API tokens.

---

## Notes

- Package name `alfred-assistant` chosen to avoid conflict with existing `alfred` packages
- TestPyPI first ensures package builds correctly before production release
- GitHub Environments provide additional protection (can require approval)
