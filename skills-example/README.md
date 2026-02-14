# Skills System

How OpenClaw makes agent capabilities modular and discoverable.

## What Are Skills?

Skills are self-contained capability modules. Each skill is a folder with a SKILL.md file that tells the agent:

1. **When to use it** (description)
2. **How to use it** (instructions)
3. **What it needs** (requirements)

## Skill Structure

```
skills/
├── weather/
│   └── SKILL.md
├── serper/
│   ├── SKILL.md
│   └── scripts/
│       └── serper_search.py
└── brainstorming/
    └── SKILL.md
```

## SKILL.md Format

```markdown
---
name: weather
description: Get current weather and forecasts (no API key required).
homepage: https://wttr.in/:help
metadata:
  openclaw:
    emoji: 🌤️
    requires:
      bins: ["curl"]
---

# Weather

Two free services, no API keys needed.

## wttr.in (primary)

Quick one-liner:

\`\`\`bash
curl -s "wttr.in/London?format=3"
# Output: London: ⛅️ +8°C
\`\`\`

Full forecast:

\`\`\`bash
curl -s "wttr.in/London?T"
\`\`\`
```

## How Skills Are Discovered

The system prompt includes a skills section:

```markdown
## Skills (mandatory)

Before replying: scan <available_skills> <description> entries.

- If exactly one skill clearly applies: read its SKILL.md at <location>, then follow it.
- If multiple could apply: choose the most specific one, then read/follow it.
- If none clearly apply: do not read any SKILL.md.

Constraints: never read more than one skill up front; only read after selecting.

<available_skills>
  <skill>
    <name>weather</name>
    <description>Get current weather and forecasts...</description>
    <location>/skills/weather/SKILL.md</location>
  </skill>
  <skill>
    <name>serper</name>
    <description>Search the web using Serper.dev...</description>
    <location>/skills/serper/SKILL.md</location>
  </skill>
</available_skills>
```

## Skill Selection Logic

1. Agent receives user message: "What's the weather in London?"
2. Agent scans available skill descriptions
3. "weather" skill matches
4. Agent reads `/skills/weather/SKILL.md`
5. Agent follows instructions in the skill
6. Agent responds with weather data

**Key constraint:** Only one skill per turn (keeps context focused).

## Skill Metadata

Skills can declare requirements:

```yaml
metadata:
  openclaw:
    emoji: 🌤️
    requires:
      bins: ["curl"]           # Needs curl binary
      config: ["api.keys"]     # Needs config value
```

The system can check these before suggesting the skill.

## Types of Skills

### 1. API Wrappers

Skills that teach the agent how to use an API:

```markdown
## Serper Search

API endpoint: https://google.serper.dev/search

Headers:
- X-API-KEY: your-api-key

Example:
curl -X POST "https://google.serper.dev/search" \
  -H "X-API-KEY: $SERPER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q": "your query"}'
```

### 2. Process Guides

Skills that teach a methodology:

```markdown
# Brainstorming

When user wants to explore ideas:

1. **Understand context** — What's the goal?
2. **Generate options** — List 5-10 possibilities
3. **Evaluate** — Pros/cons for each
4. **Narrow** — Pick top 2-3
5. **Refine** — Develop selected ideas
```

### 3. Tool Instructions

Skills that explain how to use a tool:

```markdown
# Systematic Debugging

When encountering bugs:

1. **Reproduce** — Can you make it happen again?
2. **Isolate** — What's the smallest case?
3. **Hypothesize** — What might cause this?
4. **Test** — Verify hypothesis
5. **Fix** — Implement solution
6. **Verify** — Confirm fix works
```

## Example Skills

### Weather (Simple)

```markdown
---
name: weather
description: Get current weather and forecasts (no API key required).
---

# Weather

## wttr.in

curl -s "wttr.in/London?format=3"
# London: ⛅️ +8°C

curl -s "wttr.in/London?T"  # Full forecast
```

### Deep Research (Complex)

```markdown
---
name: deep-research
description: Conduct thorough, multi-source research on any topic.
---

# Deep Research

## Process

1. **Initial scan** — Quick search to understand landscape
2. **Source triangulation** — Find 3+ independent sources
3. **Deep dive** — Read full content of key sources
4. **Synthesis** — Connect findings into coherent picture
5. **Citations** — Document all sources

## Output Format

- Summary (2-3 paragraphs)
- Key findings (bulleted)
- Sources (with links)
- Open questions
```

## Implementing Your Own

### Directory Structure

```
skills/
├── my-skill/
│   ├── SKILL.md       # Required
│   └── scripts/       # Optional helper scripts
│       └── helper.py
```

### Registration

Skills are auto-discovered from the skills directory. The system scans for SKILL.md files and builds the available_skills list.

### Dynamic Loading

Skills aren't loaded into context until needed. The system prompt only includes descriptions. Full SKILL.md content loads when selected.

## Why Skills?

1. **Modular** — Add/remove capabilities easily
2. **Discoverable** — Agent knows what's available
3. **Focused** — Only load what's needed
4. **Shareable** — Skills can be packaged and distributed
5. **Extensible** — Users can add their own

The skills system makes the agent's capabilities open-ended without bloating every prompt.
