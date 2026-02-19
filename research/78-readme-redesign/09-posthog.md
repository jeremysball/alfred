# Project Research: PostHog

**URL**: https://github.com/PostHog/posthog  
**Category**: Developer Tools  
**Lines**: ~150

---

## 1. Hook (First 3 Seconds)

**Logo**: Centered, clean  
**Badges**: Contributors, PRs Welcome, Docker Pulls, Commit Activity, Closed Issues  
**Link Bar**: Docs - Community - Roadmap - Why PostHog? - Changelog - Bug reports  
**Video**: Demo thumbnail linking to YouTube  
**Headline**: "PostHog is an all-in-one, open source platform for building successful products"

**What grabs attention**:
- Video thumbnail (visual, engaging)
- Multiple trust badges (activity, contributors)
- "all-in-one" (comprehensive value prop)
- Generous free tier mentioned early

---

## 2. Structure

Information hierarchy:

1. **Logo** (centered)
2. **Badges Row** (trust signals)
3. **Link Bar** (navigation)
4. **Video Demo** (visual proof)
5. **Headline + Feature List** (comprehensive)
6. **Table of Contents** (organized)
7. **Getting Started** (Cloud vs Self-host)
8. **Setting up PostHog** (SDKs)
9. **Learning More** (handbook, guides)
10. **Contributing**
11. **Open-source vs Paid** (transparent)
12. **Hiring** (fun ending)

**What comes first**: Trust (badges) → Navigation → Visual proof (video).

---

## 3. Voice

**Tone**: Friendly, comprehensive, transparent  
**Personality level**: 5/10 (professional with personality)  
**Formality**: Developer-friendly

**Key phrases**:
- "all-in-one, open source platform" (clear positioning)
- "Best of all, all of this is free" (generosity)
- "We <3 contributions big and small" (personality)
- "our code isn't the only thing that's open source" (handbook reference)

**Notable**:
- Fun hiring section at end
- Transparent about open source vs paid
- Emoji use (<3, 💯)

---

## 4. Visuals

- **Logo**: 1 (centered)
- **Video**: 1 (YouTube demo thumbnail)
- **Screenshots**: 0
- **Badges**: 5 (contributors, PRs, Docker, commits, issues)
- **Tables**: 1 (SDK language matrix)
- **Diagrams**: 0

**Visual strategy**: Video as hero. Badges for trust. Table for SDK coverage.

---

## 5. Social Proof

**Explicit**:
- GitHub contributors badge
- Docker Pulls badge
- Commit activity badge
- Closed issues badge

**Implicit**:
- Generous free tier (confidence)
- Multiple products (maturity)
- Company handbook open source (transparency)

**Missing**: Stars count, testimonials

---

## 6. CTAs

**Primary**:
- PostHog Cloud signup (US + EU)
- One-line self-host deploy

**Secondary**:
- SDK installation
- Product docs
- Contributing

**Placement**:
- Cloud signup early
- Self-host one-liner prominent
- SDK matrix for developers

---

## 7. Length Metrics

- **Word count**: ~600 words
- **Section count**: 12
- **Time to read**: 6-8 minutes
- **Above-the-fold content**: Logo, badges, video, headline

**Verdict**: Balanced. Video adds engagement. TOC helps navigate.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Video demo**: YouTube thumbnail as hero. Shows product in action.

2. **Generous free tier**: "Your first 1 million events... are free every month" (specific, compelling)

3. **One-line deploy**: `/bin/bash -c "$(curl...)` for self-hosting.

4. **Transparent pricing**: Explicit section on open source vs paid.

5. **Open source handbook**: "Our code isn't the only thing that's open source" (unique)

6. **Fun hiring section**: Hedgehog image + "Hey! If you're reading this..."

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Video demo as hero
- Badges row for trust
- Table of Contents
- One-line install command
- Transparent pricing section

**Voice**:
- Friendly but professional
- Generosity in free tier
- Fun personality (hiring section)

**Technical demonstration**:
- One-line deploy
- SDK matrix
- Product-specific docs

### Structural choices:

**Skip**:
- Massive feature list (Alfred is simpler)
- Self-host complexity

**Adapt**:
- Video/screenshot hero
- Badges row (tests, version, etc.)
- One-line install (pip install)
- Fun element at end

---

## 10. Raw Notes

### Badge strategy:
- GitHub contributors
- PRs Welcome
- Docker Pulls
- Commit activity
- Closed issues

Shows project health across dimensions.

### Link bar:
```markdown
<a href="...">Docs</a> - <a href="...">Community</a> - <a href="...">Roadmap</a> - 
<a href="...">Why PostHog?</a> - <a href="...">Changelog</a> - <a href="...">Bug reports</a>
```

Navigation bar right after badges.

### Video demo:
```markdown
<a href="https://www.youtube.com/watch?v=...">
  <img src="..." alt="PostHog Demonstration">
</a>
```

YouTube thumbnail links to demo video.

### One-line deploy:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/posthog/posthog/HEAD/bin/deploy-hobby)"
```

Simple self-host option.

### SDK matrix:
| Frontend | Mobile | Backend |
|----------|--------|---------|
| JavaScript | React Native | Python |
| Next.js | Android | Node |
| React | iOS | PHP |
| Vue | Flutter | Ruby |

Clear language support.

### Hiring section:
```markdown
## We're hiring!

<img src="..." alt="Hedgehog working" width="350px"/>

Hey! If you're reading this, you've proven yourself as a dedicated README reader.

You might also make a great addition to our team.
```

Fun, memorable, personality-driven.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Excellent structure, TOC helps |
| Excitement | 4/5 | Video + personality |
| Trust | 5/5 | Badges + transparency |
| Technical depth | 4/5 | Good SDK coverage |
| Visual appeal | 4/5 | Video hero helps |
| **Overall** | **4.4/5** | Engaging, transparent, comprehensive |

---

## Key Takeaway for Alfred

PostHog proves that **video demo + generous free tier + personality** creates engagement. The one-line deploy is powerful. Fun hiring section shows personality.

For Alfred: Consider a demo video. Use badges for trust. Add personality in unexpected places.
