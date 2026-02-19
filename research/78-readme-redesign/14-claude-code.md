# Project Research: Claude Code

**URL**: https://github.com/anthropics/claude-code  
**Category**: Modern Visual AI  
**Lines**: ~120

---

## 1. Hook (First 3 Seconds)

**Badges**: Node.js 18+, npm version  
**Value Prop**: "Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows -- all through natural language commands."

**What grabs attention**:
- Clear Node.js requirement badge
- "Agentic coding tool" (category definition)
- "Lives in your terminal" (location/context)
- "Understands your codebase" (key benefit)
- Demo GIF immediately visible

---

## 2. Structure

Information hierarchy:

1. **Badges** (Node.js, npm)
2. **Value Proposition** (comprehensive)
3. **Documentation Link** (prominent)
4. **Demo GIF** (visual proof)
5. **Get Started** (installation methods)
6. **Plugins** (extensibility)
7. **Reporting Bugs** (feedback)
8. **Discord Community**
9. **Data Collection** (transparency)

**What comes first**: Badges → Value prop → Docs link → Demo.

---

## 3. Voice

**Tone**: Technical, helpful, transparent  
**Personality level**: 3/10 (professional, clear)  
**Formality**: Technical documentation

**Key phrases**:
- "lives in your terminal" (personification)
- "understands your codebase" (intelligence)
- "all through natural language commands" (ease of use)
- "We welcome your feedback" (community)

**Notable**:
- Transparency about data collection
- Multiple install methods
- Deprecation notice (npm) with alternatives

---

## 4. Visuals

- **Badges**: 2 (Node.js version, npm version)
- **Demo GIF**: 1 (./demo.gif)
- **Screenshots**: 0
- **Logo**: 0

**Visual strategy**: Badges for credibility, GIF for demonstration.

---

## 5. Social Proof

**Explicit**:
- npm version badge

**Implicit**:
- Anthropic brand
- Discord community
- Plugin ecosystem

**Missing**: Stars, testimonials, user counts

---

## 6. CTAs

**Primary**:
- Official documentation
- Install (multiple methods)

**Secondary**:
- Plugins
- Bug reporting (/bug command)
- Discord community

**Placement**:
- Docs link early (after value prop)
- Installation prominent
- Deprecation note clearly marked

---

## 7. Length Metrics

- **Word count**: ~300 words
- **Section count**: 9
- **Time to read**: 3-4 minutes
- **Above-the-fold content**: Badges, value prop, docs link, demo GIF

**Verdict**: Balanced. Comprehensive value prop with visual proof.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Comprehensive value prop**: One sentence covers: what it is, where it lives, what it does, how it helps.

2. **Multiple install methods**: curl, Homebrew, WinGet, PowerShell, npm (deprecated).

3. **Deprecation transparency**: Clear note that npm is deprecated with alternatives.

4. **Demo GIF**: Shows tool in action.

5. **Data transparency**: Detailed section on data collection, usage, and retention.

6. **In-tool bug reporting**: `/bug` command mentioned.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Badges for requirements
- Comprehensive value proposition
- Demo GIF
- Multiple install methods
- Deprecation transparency

**Voice**:
- "Lives in your terminal" (personification)
- Clear benefit statements
- Transparency about data

**Technical demonstration**:
- Demo GIF
- Multiple install paths
- Plugin extensibility

### Structural choices:

**Skip**:
- Heavy data collection section (unless relevant)

**Adapt**:
- Comprehensive one-sentence value prop
- Multiple install methods (pip, Docker, source)
- Demo GIF
- Deprecation/transparency notices

---

## 10. Raw Notes

### Badge strategy:
```markdown
![](https://img.shields.io/badge/Node.js-18%2B-brightgreen?style=flat-square)
[![npm]](https://www.npmjs.com/package/@anthropic-ai/claude-code)
[npm]: https://img.shields.io/npm/v/@anthropic-ai/claude-code.svg?style=flat-square
```

Requirements + version.

### Value proposition:
"Claude Code is an agentic coding tool that lives in your terminal, understands your codebase, and helps you code faster by executing routine tasks, explaining complex code, and handling git workflows -- all through natural language commands."

Pattern: [Product] is [category] that [location], [capability], and [benefit] by [features] -- all through [method].

### Documentation prominence:
"**Learn more in the [official documentation](https://code.claude.com/docs/en/overview)**."

Bold + early.

### Deprecation notice:
```markdown
> [!NOTE]
> Installation via npm is deprecated. Use one of the recommended methods below.
```

GitHub-style note, clear alternatives provided.

### Install methods:
- curl (MacOS/Linux)
- Homebrew (MacOS/Linux)
- PowerShell (Windows)
- WinGet (Windows)
- npm (Deprecated)

Comprehensive platform coverage.

### Data transparency:
Detailed section on:
- What data is collected
- How it's used
- Privacy safeguards
- Links to Terms and Privacy Policy

Builds trust through transparency.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Excellent value prop |
| Excitement | 3/5 | Demo GIF helps |
| Trust | 5/5 | Data transparency |
| Technical depth | 4/5 | Good install coverage |
| Visual appeal | 3/5 | Demo GIF |
| **Overall** | **4.0/5** | Comprehensive, transparent, effective |

---

## Key Takeaway for Alfred

Claude Code proves that **comprehensive value proposition + demo GIF + transparency** builds trust. The one-sentence description covers everything. Multiple install methods reduce friction. Data transparency is refreshing.

For Alfred: Write a comprehensive one-sentence value prop. Include a demo GIF. Be transparent about data/storage. Provide multiple install methods.
