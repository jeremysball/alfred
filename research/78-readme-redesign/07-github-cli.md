# Project Research: GitHub CLI

**URL**: https://github.com/cli/cli  
**Category**: Developer Tools  
**Lines**: ~150

---

## 1. Hook (First 3 Seconds)

**Headline**: "GitHub CLI"  
**Tagline**: "`gh` is GitHub on the command line."  
**Value Prop**: "It brings pull requests, issues, and other GitHub concepts to the terminal next to where you are already working with `git` and your code."

**What grabs attention**:
- Simple, memorable command name (`gh`)
- Screenshot immediately shows the tool in action
- "next to where you are already working" (meets users where they are)

---

## 2. Structure

Information hierarchy:

1. **Headline + Tagline** (clear identity)
2. **Value proposition** (one sentence)
3. **Screenshot** (visual proof)
4. **Platform support** (macOS, Windows, Linux)
5. **Documentation** (installation, manual)
6. **Contributing** (feedback, building, PRs)
7. **Installation** (detailed, multi-platform)
8. **Verification** (binary attestation - security)
9. **Comparison with hub** (legacy context)

**What comes first**: Identity → Value → Visual proof.

---

## 3. Voice

**Tone**: Friendly, technical, comprehensive  
**Personality level**: 3/10 (approachable but professional)  
**Formality**: Developer-focused

**Key phrases**:
- "GitHub on the command line" (simple, powerful)
- "next to where you are already working" (empathy)
- "If anything feels off" (welcoming feedback)

**Notable**:
- Acknowledges predecessor (hub) with respect
- Security-first (binary verification section)
- Multiple install paths (comprehensive)

---

## 4. Visuals

- **Logo**: 0 (text-only)
- **Screenshots**: 1 (gh pr status screenshot)
- **Diagrams**: 0
- **Badges**: 0 (unusual)
- **Code blocks**: 6 (install examples, verification)

**Visual strategy**: Single screenshot showing real usage. No badges, relies on GitHub brand.

---

## 5. Social Proof

**Explicit**: None (no badges, no stars shown)

**Implicit**:
- GitHub official project (strongest social proof)
- GitHub Enterprise support (enterprise credibility)
- Multiple platform support (broad adoption)

**Missing**: Stars count, testimonials, contributor count

---

## 6. CTAs

**Primary**:
- Installation docs (platform-specific links)
- Manual (usage instructions)

**Secondary**:
- Contributing guide
- Feedback instructions

**Placement**:
- Docs link early
- Installation details lower (linked from TOC)

---

## 7. Length Metrics

- **Word count**: ~450 words
- **Section count**: 9
- **Time to read**: 5-6 minutes
- **Above-the-fold content**: Headline, tagline, value prop, screenshot

**Verdict**: Concise. Installation details linked out to keep README short.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Acknowledges legacy**: Explicit comparison with `hub` shows respect for predecessor and explains rationale for new tool.

2. **Security transparency**: Detailed binary verification section (Build Provenance Attestation) shows enterprise-grade security thinking.

3. **Installation outsourcing**: Rather than inline install instructions, they link to platform-specific docs. Keeps README clean.

4. **Multiple context support**: GitHub.com, Enterprise Cloud, Enterprise Server (shows broad compatibility).

5. **Codespaces/Actions integration**: Shows they understand modern developer workflows.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Short tagline (`gh` is GitHub on the command line)
- Screenshot of real usage
- Platform support statement early
- Link to detailed docs instead of inline everything

**Voice**:
- Simple, memorable positioning
- Acknowledge alternatives respectfully
- Meet users where they are

**Technical demonstration**:
- Single screenshot shows value
- Security transparency (if relevant)
- Multiple install contexts (Docker, codespaces, etc.)

### Structural choices:

**Skip**:
- Binary verification section (overkill for Alfred)
- Legacy comparison (no predecessor to acknowledge)

**Adapt**:
- Short, memorable tagline
- Screenshot of Alfred in action
- Platform/interface support statement
- Link to detailed installation docs

---

## 10. Raw Notes

### Tagline strategy:
```markdown
`gh` is GitHub on the command line.
```

Simple, memorable, positions clearly.

### Value proposition:
"It brings pull requests, issues, and other GitHub concepts to the terminal next to where you are already working with `git` and your code."

Pattern: [Product] brings [features] to [location] next to where you already work.

### Screenshot placement:
Immediately after description. Shows `gh pr status` output.

### Platform support:
"GitHub CLI is supported for users on GitHub.com, GitHub Enterprise Cloud, and GitHub Enterprise Server 2.20+ with support for macOS, Windows, and Linux."

Covers all bases: service types + operating systems.

### Documentation links:
```markdown
## Documentation

For [installation options see below](#installation), for usage instructions [see the manual](https://cli.github.com/manual/).
```

Keeps README short by linking out.

### Installation approach:
Links to platform-specific docs instead of inline:
- [macOS](docs/install_macos.md)
- [Linux & Unix](docs/install_linux.md)
- [Windows](docs/install_windows.md)

### Security section:
Detailed binary verification with `gh at verify` and Sigstore cosign. Shows enterprise maturity.

### Legacy acknowledgment:
```markdown
## Comparison with hub

For many years, [hub](https://github.com/github/hub) was the unofficial GitHub CLI tool. `gh` is a new project...
```

Respectful, explains rationale, links to detailed comparison.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Simple, focused |
| Excitement | 2/5 | Professional, dry |
| Trust | 5/5 | GitHub official |
| Technical depth | 4/5 | Good structure, links to docs |
| Visual appeal | 3/5 | Screenshot helps |
| **Overall** | **3.8/5** | Clean, professional, effective |

---

## Key Takeaway for Alfred

GitHub CLI proves that **short tagline + screenshot + linked docs** keeps READMEs clean while being comprehensive. The security section shows enterprise maturity. Acknowledging legacy tools with respect builds trust.

For Alfred: Create a memorable tagline. Use a screenshot (not GIF). Link to detailed installation docs. Show interface support (Telegram, CLI) prominently.
