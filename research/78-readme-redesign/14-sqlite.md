# SQLite

**URL**: https://github.com/sqlite/sqlite (mirror of fossil-scm)
**Category**: Classic OSS

---

### 1. Hook (First 3 Seconds)
What grabs attention immediately?
- Headline: "SQLite Source Repository" (centered)
- Subhead/tagline: "This repository contains the complete source code for the SQLite database engine going back to 2000-05-29"
- First visual element: Centered title text

**Immediate observation**: This README is about the SOURCE CODE, not the product. Explicitly states: "This README file is about the source code that goes into building SQLite, not about how SQLite is used."

### 2. Structure
Information hierarchy (what order, what gets emphasis):
1. Title (centered)
2. What this is (source repo, not user docs)
3. Version control note (uses Fossil, GitHub is a mirror)
4. Contact (SQLite Forum)
5. Public Domain notice
6. Obtaining source code
7. Compiling for Unix
8. Compiling for Windows (MSVC)
9. Source Tree Map (directory structure)
10. Generated Source Code Files
11. The Amalgamation
12. How It All Fits Together
13. Key source code files
14. Verifying Code Authenticity
15. Contacts

### 3. Voice
- Tone: Technical, authoritative, detailed
- Personality level: 2/10 (matter-of-fact technical writing)
- Key phrases that stand out:
  - "Decades of effort have gone into optimizing SQLite"
  - "It will not be the easiest library in the world to hack"

### 4. Visuals
- Screenshots/GIFs: None
- Diagrams: None (but references sqlite.org/arch.html)
- Badges: None
- Demo videos: None

**No visuals**: Pure technical documentation

### 5. Social Proof
- GitHub stars: Not mentioned
- Testimonials: None
- User logos: None
- Usage stats: None (most deployed database in the world!)

**Remarkable**: SQLite has zero social proof in its README despite being the most widely deployed database in existence.

### 6. CTAs
Primary call-to-action: sqlite.org/ (main website for users)
Secondary CTAs:
- sqlite.org/forum/ (community)
- fossil-scm.org/ (version control)
- sqlite.org/docs/ (documentation)

**Critical distinction**: README explicitly says "See the on-line documentation for more information about what SQLite is and how it works from a user's perspective."

### 7. Length Metrics
- Word count estimate: ~2,000 words
- Section count: 15 major sections
- Time to read: 8-10 minutes
- Above-the-fold content: Title + what this is

**Note**: This README is for CONTRIBUTORS, not USERS.

### 8. Differentiation
What makes this README stand out?
- Unique element 1: Explicitly states it's for source code, not users
- Unique element 2: Uses Fossil, not Git (and explains why)
- Unique element 3: Detailed source tree map with file-by-file explanations
- Unique element 4: "The Amalgamation" concept (single-file distribution)
- What they do better than competitors: Deep technical architecture explanation

### 9. Alfred Applicability
Ideas to steal/adapt:
- Pattern: Source tree map (directory structure explained)
- Voice element: "Decades of effort" for trust building
- Structural choice: Clear separation between user docs and source docs

**Not applicable**: SQLite's source-focused README approach

### 10. Raw Notes

**Immediate intent clarification**:
```markdown
See the on-line documentation for more information
about what SQLite is and how it works from a user's perspective. This
README file is about the source code that goes into building SQLite,
not about how SQLite is used.
```

**Public domain as differentiator**:
```markdown
## Public Domain
The SQLite source code is in the public domain.

Because SQLite is in the public domain, we do not normally accept pull
requests, because if we did take a pull request, the changes in that
pull request might carry a copyright and the SQLite source code would
then no longer be fully in the public domain.
```

**Amalgamation concept (unique to SQLite)**:
```markdown
## The Amalgamation
All of the individual C source code and header files... can be combined
into a single big source file sqlite3.c called "the amalgamation".

SQLite runs about 5% faster when compiled from the amalgamation versus
when compiled from individual source files.
```

**Source Tree Map (excellent pattern for complex projects)**:
```markdown
## Source Tree Map
- src/ - Primary source code
- test/ - Testing code
- tool/ - Build tools and scripts
- ext/ - Extensions (FTS5, RTREE, etc.)
- doc/ - Internal documentation
```

**Key source files explanation (deep technical)**:
Lists each major file with 2-3 sentence explanation of its role:
- sqlite.h.in - public interface
- sqliteInt.h - internal data objects
- parse.y - LALR(1) grammar
- vdbe.c - virtual machine
- where.c - query optimizer
- btree.c - B-Tree storage
- pager.c - transactions
- etc.

**Verifying code authenticity**:
Explains SHA3-256 hash verification of source tree. Trust through cryptographic proof.

---

## Quick Scoring

| Criteria | Score 1-5 | Notes |
|----------|-----------|-------|
| Clarity | 4 | Clear for intended audience |
| Excitement | 1 | Zero excitement |
| Trust | 5 | Public domain, decades of effort |
| Technical depth | 5 | Exhaustive |
| Visual appeal | 1 | None |
| Overall | 3 | Works for contributors, not users |

## Key Lesson

**Audience segmentation**: SQLite has TWO READMEs effectively:
1. This one (for people reading source code)
2. sqlite.org (for everyone else)

The README explicitly says "This is not for you if you want to USE SQLite."

**For Alfred**: Consider if GitHub README should target users or contributors. SQLite chooses contributors because their user docs live elsewhere.
