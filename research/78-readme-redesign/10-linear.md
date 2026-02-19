# Project Research: Linear

**URL**: https://github.com/linear/linear  
**Category**: Developer Tools  
**Lines**: ~100

---

## 1. Hook (First 3 Seconds)

**Logo**: Centered, clickable, links to linear.app (64px)  
**Headline**: "Linear API" (centered)  
**Tagline**: "The purpose-built tool for planning and building products"  
**Sub-tagline**: "Streamline issues, projects, and product roadmaps with the system for modern software development."  
**Badges**: License (MIT), Build, Release, Schema, Dependencies (all GitHub Actions)

**What grabs attention**:
- Clean, minimal aesthetic
- Clickable logo (drives to product)
- Multiple CI badges (shows engineering rigor)
- Clear redirect to actual docs

---

## 2. Structure

Information hierarchy:

1. **Logo** (centered, clickable)
2. **Headline** (H1, centered)
3. **Tagline** (H3, centered)
4. **Sub-tagline** (centered)
5. **Badges Row** (5 CI badges)
6. **⚠️ Monorepo Readme** (clear redirect)
7. **Structure** (monorepo explanation)
8. **Open Source Packages** (list with links)
9. **Get Started** (Node requirements, commands)
10. **Plugin Flow** (technical explanation)
11. **License**

**What comes first**: Visual identity → Clear redirect warning.

---

## 3. Voice

**Tone**: Technical, minimal, focused  
**Personality level**: 2/10 (very minimal)  
**Formality**: Engineering-focused

**Key phrases**:
- "purpose-built tool" (specificity)
- "⚠️ Monorepo Readme" (clear warning)
- "should never be manually updated" (clear rules)

**Notable**:
- Immediately redirects to actual docs
- Monorepo structure clearly explained
- Generated code warnings

---

## 4. Visuals

- **Logo**: 1 (small, 64px, centered)
- **Badges**: 5 (CI status badges)
- **Screenshots**: 0
- **Diagrams**: 0

**Visual strategy**: Minimalist. Logo + badges only. Content-focused.

---

## 5. Social Proof

**Explicit**:
- 5 CI badges (engineering rigor)
- MIT license

**Implicit**:
- Monorepo structure (mature engineering)
- Code generation (sophistication)

**Missing**: Stars, contributors, testimonials

---

## 6. CTAs

**Primary**:
- Link to developers.linear.app (actual docs)

**Secondary**:
- Package README links
- Build/test commands

**Placement**:
- Redirect warning immediately after header
- Package links in structure section

---

## 7. Length Metrics

- **Word count**: ~250 words
- **Section count**: 7
- **Time to read**: 2-3 minutes
- **Above-the-fold content**: Logo, headline, tagline, redirect warning

**Verdict**: Extremely minimal. README as entry point, not destination.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Immediate redirect**: "⚠️ Monorepo Readme" - clear that this isn't the docs.

2. **Monorepo transparency**: Clear structure explanation, generated code warnings.

3. **CI badge density**: 5 badges showing comprehensive CI coverage.

4. **Plugin flow documentation**: Explains code generation architecture.

5. **Minimalist aesthetic**: Small logo, centered everything, lots of whitespace.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Clickable logo (drives to product)
- Clear redirect if README isn't the docs
- Monorepo/package structure clarity
- CI badge density

**Voice**:
- Minimal, focused
- Clear warnings/redirects
- Technical precision

**Technical demonstration**:
- Package list with descriptions
- Build commands clearly listed
- Architecture explanation

### Structural choices:

**Skip**:
- Extreme minimalism (Alfred needs more explanation)
- Monorepo complexity (if not applicable)

**Adapt**:
- Clickable logo to product/docs
- Clear structure if multiple packages
- CI badges for trust

---

## 10. Raw Notes

### Header structure:
```markdown
<p align="center">
  <a href="https://linear.app" target="_blank" rel="noopener noreferrer">
    <img width="64" src="..." alt="Linear logo">
  </a>
</p>
<h1 align="center">Linear API</h1>
<h3 align="center">The purpose-built tool...</h3>
<p align="center">Streamline issues...</p>
```

Everything centered. Logo links to product.

### Redirect strategy:
```markdown
## ⚠️ Monorepo Readme

If you are looking for documentation on the Linear SDK or Linear API, 
visit [**developers.linear.app**](https://developers.linear.app/docs) instead.
```

Clear, prominent, helpful.

### CI badges:
- License (MIT)
- Build
- Release
- Schema
- Dependencies

Shows engineering rigor across dimensions.

### Package structure:
```markdown
### Structure

This monorepo uses `pnpm` workspaces to manage and publish packages.

Generated code uses file prefix `_generated` and should never be manually updated.

Open source packages:
- [sdk](...) - The Linear Client SDK...
- [import](...) - Import tooling...
```

Clear package list with descriptions.

### Build commands:
```shell
pnpm install
pnpm build
pnpm test
pnpm schema
pnpm changeset
```

Simple, standard commands.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Excellent redirect, clear structure |
| Excitement | 1/5 | Extremely minimal |
| Trust | 4/5 | CI badges show rigor |
| Technical depth | 3/5 | Good structure explanation |
| Visual appeal | 2/5 | Minimalist to a fault |
| **Overall** | **3.0/5** | Effective as entry point, not destination |

---

## Key Takeaway for Alfred

Linear proves that **minimalism + clear redirects** works when the README isn't the destination. The CI badges show engineering rigor. Monorepo structure is clearly explained.

For Alfred: If using monorepo structure, explain it clearly. Use CI badges. But Alfred's README should BE the destination (more like PostHog/Supabase, not Linear).
