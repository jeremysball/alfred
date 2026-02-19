# Redis

**URL**: https://github.com/redis/redis
**Category**: Classic OSS

---

### 1. Hook (First 3 Seconds)
What grabs attention immediately?
- Headline: None (starts with codecov badge)
- Subhead/tagline: "This document serves as both a quick start guide to Redis and a detailed resource for building it from source"
- First visual element: Badge (codecov)

**Immediate observation**: No logo, no hero section, no tagline. Opens with navigation block and badges.

### 2. Structure
Information hierarchy (what order, what gets emphasis):
1. Navigation block (where to go based on intent)
2. Table of contents (25+ items)
3. What is Redis? (positioning statement)
4. Key use cases (8 detailed bullet points)
5. Why choose Redis? (value props with explanations)
6. Getting started (multiple paths)
7. Data types, engines, capabilities (extensive technical catalog)
8. Build from source (massive section - OS-specific instructions)
9. Code contributions
10. Trademarks

### 3. Voice
- Tone: Technical, comprehensive, professional
- Personality level: 2/10 (minimal personality, pure information)
- Key phrases that stand out:
  - "For developers, who are building real-time data-driven applications"
  - "battle tested in production workloads at a massive scale"
  - "There is a good chance you indirectly interact with Redis several times daily"

### 4. Visuals
- Screenshots/GIFs: None
- Diagrams: None
- Badges: codecov only
- Demo videos: None

**Notable**: Zero visuals. 939 lines of pure text.

### 5. Social Proof
- GitHub stars: Not mentioned in README
- Testimonials: None
- User logos: None
- Usage stats: "There is a good chance you indirectly interact with Redis several times daily"

**Weakness**: No visible social proof despite being one of the most popular projects on GitHub.

### 6. CTAs
Primary call-to-action: Redis Cloud (https://cloud.redis.io/)
Secondary CTAs:
- Docker: `docker run -d -p 6379:6379 redis:latest`
- Binary distributions (Snap, Homebrew, RPM, Debian)
- Build from source

Placement: CTAs scattered throughout Getting Started section

### 7. Length Metrics
- Word count estimate: ~5,000 words
- Section count: 25+ sections
- Time to read: 15-20 minutes
- Above-the-fold content: Navigation block + TOC

**Critical observation**: This README is a complete reference document, not a landing page.

### 8. Differentiation
What makes this README stand out?
- Unique element 1: Comprehensive OS-specific build instructions (Ubuntu 20.04, 22.04, 24.04, Debian 11/12, AlmaLinux, Rocky Linux, macOS 13/14/15)
- Unique element 2: Navigation block at top that segments users by intent
- What they do better than competitors: Serves as both quick start AND detailed reference

### 9. Alfred Applicability
Ideas to steal/adapt:
- Pattern: Navigation block at top ("New to Alfred?", "Ready to deploy?", "Want to contribute?")
- Voice element: "battle tested" language for trust
- Structural choice: Dual-purpose README (quick start + reference)

### 10. Raw Notes

**Navigation block (excellent pattern)**:
```markdown
- New to Redis? Start with [What is Redis](#what-is-redis) and [Getting Started](#getting-started)
- Ready to build from source? Jump to [Build Redis from Source](#build-redis-from-source)
- Want to contribute? See the [Code contributions](#code-contributions) section
- Looking for detailed documentation? Navigate to [redis.io/docs](https://redis.io/docs/)
```

**Positioning statement (clear, specific)**:
"For developers, who are building real-time data-driven applications, Redis is the preferred, fastest, and most feature-rich cache, data structure server, and document and vector query engine."

**Use cases list (comprehensive but overwhelming)**:
- Caching
- Distributed Session Store
- Data Structure Server
- NoSQL Data Store
- Search and Query Engine
- Event Store & Message Broker
- Vector Store for GenAI
- Real-Time Analytics

**Why choose Redis section structure**:
Each reason has a clear heading + 2-3 sentence explanation:
- Performance: sub-millisecond latency
- Flexibility: native data structures
- Extensibility: modules API
- Simplicity: text-based protocol
- Ubiquity: battle tested at scale
- Versatility: de facto standard for use cases

**Starter projects by language (smart)**:
Links to redis-developer repos for Python, C#/.NET, Go, JavaScript, Java/Spring

---

## Quick Scoring

| Criteria | Score 1-5 | Notes |
|----------|-----------|-------|
| Clarity | 4 | Very clear, but dense |
| Excitement | 2 | No emotional hooks |
| Trust | 5 | Battle-tested positioning |
| Technical depth | 5 | Exhaustive |
| Visual appeal | 1 | None |
| Overall | 3 | Reference doc, not landing page |
