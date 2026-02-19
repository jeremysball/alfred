# Project Research: Raycast Extensions

**URL**: https://github.com/raycast/extensions  
**Category**: Modern Visual AI  
**Lines**: ~80

---

## 1. Hook (First 3 Seconds)

**Logo**: Store logo, 128px, centered  
**Headline**: "Raycast Extensions"  
**Badges**: Follow on X, Join community (both black, for-the-badge style)  
**Hero Image**: Header WebP image showing extensions  
**Value Prop**: "Raycast lets you control your tools with a few keystrokes."

**What grabs attention**:
- Clean, minimal aesthetic
- Dark badges (on-brand)
- Visual header showing product
- "Few keystrokes" (speed promise)

---

## 2. Structure

Information hierarchy:

1. **Logo + Headline** (centered)
2. **Badges** (X, Community)
3. **Hero Image** (extensions showcase)
4. **Getting Started** (docs link)
5. **Guidelines** (community + extension policies)
6. **Feedback** (GitHub issues)
7. **Community** (Slack)

**What comes first**: Visual identity → Immediate docs link.

---

## 3. Voice

**Tone**: Friendly, developer-focused, concise  
**Personality level**: 4/10 (professional but warm)  
**Formality**: Casual professional

**Key phrases**:
- "control your tools with a few keystrokes" (power + speed)
- "wouldn't be where it is without the feedback" (community appreciation)
- "debug nasty bugs" (relatable, casual)

**Notable**:
- Very concise (80 lines)
- Issues-only/extensions repo (not main product)
- Community-focused

---

## 4. Visuals

- **Logo**: 1 (store logo, 128px)
- **Hero Image**: 1 (header.webp)
- **Badges**: 2 (X, Community - black style)
- **Screenshots**: 0 (in hero image)

**Visual strategy**: Logo + hero image + dark badges. Minimal but polished.

---

## 5. Social Proof

**Explicit**: None (no stars, contributors shown)

**Implicit**:
- Raycast brand recognition
- Extensions ecosystem (implied maturity)

**Missing**: Stars, contributor count, testimonials

---

## 6. CTAs

**Primary**:
- Developers docs (developers.raycast.com)
- Raycast Store

**Secondary**:
- Community guidelines
- GitHub issues
- Slack community

**Placement**:
- Docs link early
- Store link prominent

---

## 7. Length Metrics

- **Word count**: ~150 words
- **Section count**: 5
- **Time to read**: 1-2 minutes
- **Above-the-fold content**: Logo, headline, hero image

**Verdict**: Extremely concise. README as entry point, not destination.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Visual minimalism**: Clean, lots of whitespace, centered everything.

2. **Dark badge style**: Black badges match brand aesthetic.

3. **Hero image**: Shows extensions in action without screenshots.

4. **Concise guidelines**: Links to policies rather than inline.

5. **Community focus**: Slack, feedback, guidelines all community-oriented.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Centered logo + headline
- Hero image as visual proof
- Dark/minimal badges
- Very concise sections

**Voice**:
- "Few keystrokes" (speed promise)
- Community appreciation
- Casual but professional

### Structural choices:

**Skip**:
- Too minimal (Alfred needs more explanation)
- Extensions-focused (different product type)

**Adapt**:
- Centered visual header
- Dark/minimal badge style
- Concise sections with links to details
- Hero image showing product

---

## 10. Raw Notes

### Badge style:
```markdown
<a aria-label="Follow Raycast on X" href="https://x.com/raycast">
  <img alt="" src="https://img.shields.io/badge/Follow%20@raycast-black.svg?style=for-the-badge&logo=X">
</a>
```

Black badges with `for-the-badge` style. On-brand.

### Hero image:
```markdown
![Header](images/header.webp)
```

WebP format, shows product in action.

### Concise value prop:
"Raycast lets you control your tools with a few keystrokes."

Short, punchy, benefit-focused.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Very clear, concise |
| Excitement | 3/5 | Polished but restrained |
| Trust | 3/5 | Brand recognition helps |
| Technical depth | 2/5 | Intentionally minimal |
| Visual appeal | 4/5 | Clean, on-brand |
| **Overall** | **3.4/5** | Effective for extensions repo |

---

## Key Takeaway for Alfred

Raycast proves that **visual minimalism + dark aesthetic** creates a premium feel. The hero image shows product without words. Badges can be on-brand (not just default colors).

For Alfred: Consider a hero image/GIF. Use centered layout. Dark badges if they fit brand.
