# Project Research: Warp

**URL**: https://github.com/warpdotdev/Warp  
**Category**: Modern Visual AI  
**Lines**: ~120

---

## 1. Hook (First 3 Seconds)

**Hero Image**: Massive 1024px wide product preview (Agentic Development Environment)  
**Link Bar**: Website · Code · Agents · Terminal · Drive · Docs · How Warp Works  
**About Section**: Clear problem/solution statement

**What grabs attention**:
- Massive hero image dominates the view
- "Agentic Development Environment" (category creation)
- Clean link bar with interpunct separators
- Bold problem statement

---

## 2. Structure

Information hierarchy:

1. **Hero Image** (massive visual)
2. **Link Bar** (7 links, centered)
3. **About** (problem/solution)
4. **Installation** (download + docs)
5. **Changelog** (weekly releases)
6. **Issues/Bugs/Features** (GitHub issues)
7. **Open Source & Contributing** (roadmap)
8. **Support** (docs, Slack, Discord)
9. **Community Guidelines**
10. **Open Source Dependencies** (shoutouts)

**What comes first**: Visual proof → Navigation → Problem statement.

---

## 3. Voice

**Tone**: Technical, ambitious, transparent  
**Personality level**: 5/10 (confident, clear)  
**Formality**: Technical but accessible

**Key phrases**:
- "terminals haven't kept up with how developers work today" (problem identification)
- "Agentic Development Environment" (category creation)
- "SOTA built-in agent" (confidence)
- "We are planning to first open-source..." (transparency)

**Notable**:
- Acknowledges problems with current tools
- Clear open-source roadmap
- Shoutouts to dependencies (community respect)

---

## 4. Visuals

- **Hero Image**: 1 (massive 1024px product preview)
- **Screenshots**: 0 (embedded in hero)
- **Badges**: 0
- **Diagrams**: 0

**Visual strategy**: One massive hero image does all the work.

---

## 5. Social Proof

**Explicit**: None

**Implicit**:
- Weekly releases (active development)
- Open-source roadmap (commitment)
- Dependency shoutouts (community respect)

**Missing**: Stars, testimonials, user counts

---

## 6. CTAs

**Primary**:
- Download Warp
- Read docs

**Secondary**:
- Create an agent (Oz)
- Join Slack/Discord
- Careers

**Placement**:
- Download early
- Create agent link in About section

---

## 7. Length Metrics

- **Word count**: ~400 words
- **Section count**: 10
- **Time to read**: 3-4 minutes
- **Above-the-fold content**: Hero image, link bar, About section

**Verdict**: Concise but comprehensive. Hero image does heavy lifting.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Massive hero image**: 1024px wide, immediately shows product.

2. **Category creation**: "Agentic Development Environment" not "terminal".

3. **Problem-first**: "terminals haven't kept up with how developers work today"

4. **Open-source transparency**: Clear roadmap for what will/won't be open.

5. **Dependency shoutouts**: Lists open-source projects they use (Tokio, NuShell, Fig, etc.)

6. **Dual-agent strategy**: Built-in Oz + support for Claude Code, Codex, Gemini CLI.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Massive hero image
- Link bar with clear navigation
- Problem-first explanation
- Open-source transparency

**Voice**:
- Problem identification first
- Category creation
- Dependency shoutouts

**Technical demonstration**:
- Hero image shows product
- Clear installation path
- Multiple support channels

### Structural choices:

**Skip**:
- Issues-only repo pattern (Alfred is the product)
- Open-source roadmap (unless relevant)

**Adapt**:
- Large hero image/GIF
- Problem-first narrative
- Link bar for navigation
- Dependency/community shoutouts

---

## 10. Raw Notes

### Hero image:
```markdown
<a href="https://www.warp.dev">
    <img width="1024" alt="Warp Agentic Development Environment product preview" 
         src="https://storage.googleapis.com/warpdotdev-content/Readme.png">
</a>
```

1024px wide, clickable, descriptive alt text.

### Link bar:
```markdown
<p align="center">
  <a href="https://www.warp.dev">Website</a>
  ·
  <a href="https://www.warp.dev/code">Code</a>
  ·
  <a href="https://www.warp.dev/agents">Agents</a>
  ...
</p>
```

Interpunct (·) separators, centered.

### Problem statement:
"We built Warp to solve two problems we kept hitting as a team writing software: terminals haven't kept up with how developers work today, and agentic development tools don't scale beyond your laptop."

Clear problem → solution narrative.

### Category creation:
"Warp is a modern terminal built for coding with agents."
"Oz is an orchestration platform for cloud agents."

Not just a terminal. Not just an agent. New categories.

### Open-source transparency:
"We are planning to first open-source our Rust UI framework, and then parts and potentially all of our client codebase. The server portion of Warp will remain closed-source for now."

Honest about what will/won't be open.

### Dependency shoutouts:
- Tokio
- NuShell
- Fig Completion Specs
- Alacritty
- Hyper

Shows community respect and technical depth.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Clear problem/solution |
| Excitement | 4/5 | Hero image helps |
| Trust | 4/5 | Transparency about open source |
| Technical depth | 4/5 | Good explanation |
| Visual appeal | 5/5 | Hero image dominates |
| **Overall** | **4.4/5** | Strong visual + clear narrative |

---

## Key Takeaway for Alfred

Warp proves that **massive hero image + problem-first narrative + category creation** is powerful. The transparency about open-source builds trust. Dependency shoutouts show community respect.

For Alfred: Large hero image showing Alfred in action. Problem-first ("LLMs forget"). Category creation ("Persistent Memory" not "chatbot"). Shoutouts to open-source dependencies.
