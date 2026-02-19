# Project Research: Letta (formerly MemGPT)

**URL**: https://github.com/letta-ai/letta  
**Category**: AI Memory & Context  
**Lines**: ~130  

---

## 1. Hook (First 3 Seconds)

**Logo**: Dynamic dark/light mode logo at the top (centered, 500px width)  
**Headline**: "Letta (formerly MemGPT)"  
**Subhead**: "Letta is the platform for building stateful agents: AI with advanced memory that can learn and self-improve over time."

**What grabs attention**:
- Immediately clarifies rebrand (MemGPT was well-known)
- "Stateful agents" is technical but explained
- Promise of "learn and self-improve" (active benefits)
- No fluff: straight to value proposition

---

## 2. Structure

Information hierarchy:

1. **Logo + Identity** (visual anchor)
2. **One-line value prop** (what it is)
3. **Two paths** (CLI vs API)
4. **CLI quickstart** (Node.js install, 2 steps)
5. **API quickstart** (Install, Hello World in TS + Python)
6. **Contributing/Community** (Discord, forum, socials)
7. **Legal** (minimal footer)

**What comes first**: The dual-path offering (Letta Code vs Letta API). They know their audience splits between "I want to use it" and "I want to build with it."

---

## 3. Voice

**Tone**: Technical, confident, slightly playful  
**Personality level**: 6/10 (the "Timber the dog" example adds warmth)  
**Formality**: Professional but approachable

**Key phrases**:
- "self-improving superintelligence" (ambitious but matter-of-fact)
- "Timber is my best friend and collaborator" (unexpected, memorable)
- "democratize self-improving superintelligence" (mission-driven)

**Notable**: They use their own product in the example (meta). The example shows personality injection into memory blocks.

---

## 4. Visuals

- **Logo**: 1 (responsive dark/light mode)
- **Screenshots/GIFs**: 0 (surprising for an AI tool)
- **Diagrams**: 0
- **Badges**: 0 (none visible)
- **Code blocks**: 4 (2 install, 2 Hello World)

**Visual strategy**: Pure text + code. They rely on the code examples to show, not tell. The dark/light logo is the only visual polish.

---

## 5. Social Proof

**Explicit**:
- "over a hundred contributors from around the world"

**Implicit**:
- Formerly MemGPT (established brand recognition)
- Model leaderboard mentioned (authority)
- Multiple SDKs (TS + Python, maturity signal)

**Missing**: GitHub stars count, user testimonials, company logos

---

## 6. CTAs

**Primary**: 
- Letta Code link (docs)
- Letta API link (docs)

**Secondary**:
- Install commands (npm install, pip install)
- Quickstart guide link
- API reference link

**Community CTAs** (in Contributing section):
- Join Discord
- Chat on forum
- Follow socials (Twitter, LinkedIn, YouTube)

**Placement**: Links appear in the intro paragraph, then again inline with code examples. Contributing CTAs at the bottom.

---

## 7. Length Metrics

- **Word count**: ~400 words
- **Section count**: 4 (Get started CLI, Get started API, Contributing, Legal)
- **Time to read**: 2-3 minutes
- **Above-the-fold content**: Logo, headline, subhead, 2 product links

**Verdict**: Extremely concise. They prioritize "get started quickly" over explaining the "why."

---

## 8. Differentiation

**What makes this README stand out**:

1. **Dual-path clarity**: They immediately split between CLI users and API users. No confusion about who this is for.

2. **Self-referential example**: Using their own product (Timber the dog building Letta) in the Hello World is clever and memorable.

3. **Rebrand handling**: "(formerly MemGPT)" right in the H1 manages expectations for existing users.

4. **Model-agnostic but opinionated**: "we recommend Opus 4.5 and GPT-5.2" + leaderboard shows expertise without being rigid.

5. **Memory as first-class**: The example immediately shows `memory_blocks` with `human` and `persona` labels. This is the core differentiator and it's in the first code sample.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Immediate path bifurcation (CLI vs API / Telegram vs library use)
- Code-first explanation (show the memory system in action immediately)
- Concise to the point of minimalism

**Voice**:
- Technical confidence without arrogance
- Self-referential humor/example (Alfred could have a meta-example)
- Mission-driven language ("democratize" equivalent for Alfred?)

**Technical demonstration**:
- Show memory configuration in the first code snippet
- Two-language support (Python + whatever Alfred uses)
- Working example that demonstrates the core value prop

### Structural choices:

**Skip**:
- No feature list (they don't list "features")
- No architecture diagram (they trust the code)
- No screenshots (unusual, maybe too minimal for Alfred)

**Adapt**:
- The dual-path approach fits Alfred perfectly (Telegram vs CLI vs library)
- Memory blocks as configuration is a great pattern
- Contributing section with multiple community options

---

## 10. Raw Notes

### Header:
```markdown
<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="...">
    <source media="(prefers-color-scheme: light)" srcset="...">
    <img alt="Letta logo" src="..." width="500">
  </picture>
</p>
```
Note: Uses HTML for responsive logo. Good technique.

### Value prop:
"Letta is the platform for building stateful agents: AI with advanced memory that can learn and self-improve over time."

Pattern: [Product] is [category]: [unique attribute] that [benefit].

### CLI section:
"Requires Node.js 18+" - explicit dependency upfront, no surprises.

"When running the CLI tool, your agent help you code and do any task you can do on your computer."
- Active voice, immediate benefit

### API section:
"Use the Letta API to integrate stateful agents into your own applications."
- Clear purpose statement

### Hello World:
The example includes:
1. Import
2. Client init with API key
3. Agent creation with memory_blocks
4. Message sending
5. Response handling

This is a complete working example in ~20 lines.

### Memory blocks structure:
```javascript
memory_blocks: [
  { label: "human", value: "..." },
  { label: "persona", value: "..." }
]
```
Simple, declarative, powerful.

### Contributing section:
- Discord (primary)
- Forum (alternative)
- Socials (Twitter, LinkedIn, YouTube)

Multi-channel approach, inclusive.

### Legal footer:
Small, understated, necessary. Doesn't distract.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Immediate understanding of what it does |
| Excitement | 3/5 | Competent but not thrilling |
| Trust | 4/5 | Former MemGPT, leaderboard, model recs |
| Technical depth | 4/5 | Good code examples, brief but sufficient |
| Visual appeal | 2/5 | Clean but sparse (only logo) |
| **Overall** | **3.6/5** | Excellent for developers, lacks emotional punch |

---

## Key Takeaway for Alfred

Letta proves you can be compelling without being verbose. Their strength is **radical clarity**: they know exactly who they are (stateful agent platform) and immediately show you how to use it. They don't explain memory architecture or justify the approach. They just show working code with memory blocks.

For Alfred: Lead with the dual-interface reality (Telegram vs CLI). Show memory in the first code sample. Be confident about what Alfred does without over-explaining. But consider adding one visual or screenshot to break up the text (where Letta is too sparse).
