# Project Research: Stripe CLI

**URL**: https://github.com/stripe/stripe-cli  
**Category**: Developer Tools  
**Lines**: ~150

---

## 1. Hook (First 3 Seconds)

**Headline**: "Stripe CLI" (clean, simple)  
**Badges**: GitHub release, Build Status (immediate credibility)  
**Value Prop**: "The Stripe CLI helps you build, test, and manage your Stripe integration right from the terminal."

**What grabs attention**:
- Badges immediately establish trust (release version, build passing)
- "build, test, and manage" covers the full lifecycle
- Terminal-focused (clear audience)

---

## 2. Structure

Information hierarchy:

1. **Headline + Badges** (trust signals)
2. **Value proposition** (one sentence)
3. **Feature bullets** (what you can do)
4. **Demo GIF** (visual proof)
5. **Installation** (macOS, Linux, Windows, Docker)
6. **Usage** (basic command structure)
7. **Commands** (link list to docs)
8. **Documentation** (link to full reference)
9. **Telemetry** (transparency)
10. **Feedback** (user voice)
11. **Contributing**
12. **License**

**What comes first**: Trust (badges) → Value (proposition) → Visual proof (GIF).

---

## 3. Voice

**Tone**: Professional, helpful, comprehensive  
**Personality level**: 2/10 (enterprise, minimal)  
**Formality**: Technical documentation

**Key phrases**:
- "helps you build, test, and manage" (active benefits)
- "Securely test webhooks" (security emphasis)
- "Please don't hesitate" (polite, welcoming)

**Notable**:
- Extremely straightforward
- No marketing fluff
- Commands are links to full docs

---

## 4. Visuals

- **Logo**: 0 (text-only header)
- **Screenshots/GIFs**: 1 (demo.gif)
- **Diagrams**: 0
- **Badges**: 2 (GitHub release, Build Status)
- **Code blocks**: 6 (install examples)

**Visual strategy**: Demo GIF is the hero. Shows tool in action without words.

---

## 5. Social Proof

**Explicit**:
- Build status badge (Travis CI)
- GitHub release badge

**Implicit**:
- Stripe brand (major company)
- Comprehensive docs (maturity signal)

**Missing**: Stars count, testimonials, contributor count

---

## 6. CTAs

**Primary**:
- Installation commands (brew, scoop, docker)

**Secondary**:
- CLI reference site (docs link)
- Feedback form

**Placement**:
- Install immediately after demo
- Docs link in Commands section
- Feedback at bottom

---

## 7. Length Metrics

- **Word count**: ~400 words
- **Section count**: 12
- **Time to read**: 4-5 minutes
- **Above-the-fold content**: Badges, value prop, feature bullets, demo GIF

**Verdict**: Balanced length. Comprehensive but not overwhelming.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Demo GIF**: Shows the tool working immediately. No explanation needed.

2. **Multi-platform install**: macOS (Homebrew), Linux, Windows (Scoop), Docker all covered.

3. **Command as links**: Each command links to full documentation. README stays concise while being comprehensive.

4. **Docker instructions**: Detailed password store setup for production use.

5. **Telemetry transparency**: Explicit section about data collection.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Badges for immediate credibility
- Feature bullets with action verbs
- Demo GIF/visual proof
- Multi-platform install instructions
- Commands as links to docs

**Voice**:
- Active benefit statements
- Security emphasis
- Polite, helpful tone

**Technical demonstration**:
- Demo GIF showing real usage
- Basic command structure shown
- Links to comprehensive docs

### Structural choices:

**Skip**:
- Enterprise dryness (add personality for Alfred)
- Heavy focus on Docker (not Alfred's primary use case)

**Adapt**:
- Demo GIF/screenshot of Alfred in action
- Multi-interface install (Telegram, CLI, library)
- Feature bullets with action verbs
- Commands link to docs pattern

---

## 10. Raw Notes

### Badge strategy:
```markdown
![GitHub release (latest by date)](https://img.shields.io/github/v/release/stripe/stripe-cli)
[![Build Status](https://travis-ci.org/stripe/stripe-cli.svg?branch=master)](https://travis-ci.org/stripe/stripe-cli)
```

Build status + release version = immediate trust.

### Feature bullets:
```markdown
**With the CLI, you can:**

- Securely test webhooks without relying on 3rd party software
- Trigger webhook events or resend events for easy testing
- Tail your API request logs in real-time
- Create, retrieve, update, or delete API objects.
```

Pattern: **With [Product], you can:** then action-oriented bullets.

### Demo placement:
GIF appears right after feature bullets. Visual proof of claims.

### Install strategy:
Platform-native package managers:
- macOS: Homebrew
- Windows: Scoop
- Linux: Link to docs
- Docker: Detailed instructions

### Command documentation:
```markdown
## Commands

The Stripe CLI supports a broad range of commands. Below are some of the most used ones:
- [`login`](https://stripe.com/docs/cli/login)
- [`listen`](https://stripe.com/docs/cli/listen)
- [`trigger`](https://stripe.com/docs/cli/trigger)
```

Links to full docs keep README short while being comprehensive.

### Transparency:
Telemetry section shows they respect user privacy by being upfront.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Excellent structure |
| Excitement | 2/5 | Professional but dry |
| Trust | 5/5 | Badges, Stripe brand |
| Technical depth | 4/5 | Good examples, links to docs |
| Visual appeal | 3/5 | Demo GIF helps |
| **Overall** | **3.8/5** | Gold standard for CLI tools |

---

## Key Takeaway for Alfred

Stripe CLI proves that **badges + demo GIF + multi-platform install** is the CLI gold standard. The demo GIF shows the tool working without explanation. Commands as links keeps the README concise.

For Alfred: Add badges (tests passing, version). Create a demo GIF or screenshot. Show multi-interface setup (Telegram, CLI). Use action-oriented feature bullets.
