# Git

**URL**: https://github.com/git/git
**Category**: Classic OSS

---

### 1. Hook (First 3 Seconds)
What grabs attention immediately?
- Headline: "Git - fast, scalable, distributed revision control system"
- Subhead/tagline: None (headline IS the description)
- First visual element: CI badge only

**Immediate observation**: Classic underline styling (===), no logo, badge at top. Gets straight to the point.

### 2. Structure
Information hierarchy (what order, what gets emphasis):
1. CI Badge
2. Title + description
3. What Git is (2 paragraphs)
4. Installation pointer
5. Documentation pointers
6. CVS migration note
7. Mailing list info
8. Translation info
9. Security disclosure
10. Maintainer notes
11. Origin of the name "git" (personality!)

### 3. Voice
- Tone: Technical, helpful, with unexpected humor at the end
- Personality level: 4/10 (mostly technical, but the name origin is pure personality)
- Key phrases that stand out:
  - "unusually rich command set"
  - "group of hackers around the net"
  - "the stupid content tracker"
  - "goddamn idiotic truckload of sh*t: when it breaks"

### 4. Visuals
- Screenshots/GIFs: None
- Diagrams: None
- Badges: CI badge only (GitHub Actions)
- Demo videos: None

**Only visual**: One badge

### 5. Social Proof
- GitHub stars: Not mentioned
- Testimonials: None
- User logos: None
- Usage stats: None

**No social proof** - Git is too ubiquitous to need it.

### 6. CTAs
Primary call-to-action: git-scm.com/ (main website)
Secondary CTAs:
- INSTALL file (for building)
- Documentation/gittutorial.adoc (getting started)
- Documentation/giteveryday.adoc (useful minimum)
- git help <command> (built-in help)
- git@vger.kernel.org (mailing list)

Placement: Embedded in natural paragraph flow

### 7. Length Metrics
- Word count estimate: ~400 words
- Section count: ~10 sections
- Time to read: 2-3 minutes
- Above-the-fold content: Badge + title + what is Git

**Just right**: Long enough to be helpful, short enough to read quickly.

### 8. Differentiation
What makes this README stand out?
- Unique element 1: Origin of the name "git" section (pure personality)
- Unique element 2: Direct links to tutorial + everyday commands
- Unique element 3: CVS migration note (historical context)
- What they do better than competitors: Name origin story is memorable and humanizing

### 9. Alfred Applicability
Ideas to steal/adapt:
- Pattern: Origin story / name explanation at the end
- Voice element: Self-deprecating humor ("stupid content tracker")
- Structural choice: Tutorial link + everyday commands link (progressive onboarding)

### 10. Raw Notes

**Opening (classic, direct)**:
```markdown
Git is a fast, scalable, distributed revision control system with an
unusually rich command set that provides both high-level operations
and full access to internals.
```

**Author credit (brief, humble)**:
```markdown
It was originally written by Linus Torvalds with help of a group of
hackers around the net.
```

**Documentation structure (progressive)**:
1. gittutorial.adoc - to get started
2. giteveryday.adoc - useful minimum set of commands
3. git-<commandname>.adoc - individual command docs
4. man git-<commandname> or git help <commandname> - if installed

**Mailing list engagement**:
```markdown
The user discussion and development of Git take place on the Git
mailing list -- everyone is welcome to post bug reports, feature
requests, comments and patches to git@vger.kernel.org
```

**Maintainer notes (insider info)**:
```markdown
The maintainer frequently sends the "What's cooking" reports that
list the current status of various development topics...
```

**Name origin (the personality gem)**:
```markdown
The name "git" was given by Linus Torvalds when he wrote the very
first version. He described the tool as "the stupid content tracker"
and the name as (depending on your mood):

 - random three-letter combination that is pronounceable, and not
   actually used by any common UNIX command. The fact that it is a
   mispronunciation of "get" may or may not be relevant.
 - stupid. contemptible and despicable. simple. Take your pick from the
   dictionary of slang.
 - "global information tracker": you're in a good mood, and it actually
   works for you. Angels sing, and a light suddenly fills the room.
 - "goddamn idiotic truckload of sh*t": when it breaks
```

---

## Quick Scoring

| Criteria | Score 1-5 | Notes |
|----------|-----------|-------|
| Clarity | 5 | Clear and direct |
| Excitement | 3 | Name origin adds personality |
| Trust | 5 | Linus + hackers = credibility |
| Technical depth | 3 | Delegates to docs |
| Visual appeal | 1 | Badge only |
| Overall | 4 | Best of the classic OSS category |

## Key Lesson

**Personality at the end**: Git's README is 90% technical utility, 10% personality - and that 10% is all at the very end. The name origin section is:

1. Unexpected (after dry technical content)
2. Self-deprecating (shows humility)
3. Memorable ("goddamn idiotic truckload of sh*t")
4. Human (shows the creator's sense of humor)

**For Alfred**: Consider adding a personality section at the end. "Why is it called Alfred?" could be memorable and humanizing.

**Also note**: Git's README assumes you already know what Git is. It focuses on:
- Where to learn (tutorials)
- How to engage (mailing list)
- What to expect (maintainer updates)
