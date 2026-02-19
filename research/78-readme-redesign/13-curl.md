# curl

**URL**: https://github.com/curl/curl
**Category**: Classic OSS

---

### 1. Hook (First 3 Seconds)
What grabs attention immediately?
- Headline: Logo (curl logo SVG)
- Subhead/tagline: "curl is a command-line tool for transferring data from or to a server using URLs"
- First visual element: curl logo (centered SVG)

**Immediate observation**: Clean, centered, logo-first. Gets straight to what it does.

### 2. Structure
Information hierarchy (what order, what gets emphasis):
1. Logo
2. One-sentence definition
3. Protocol list (26 protocols!)
4. How to use (man page, everything curl docs)
5. How to install (INSTALL document)
6. libcurl mention
7. Open Source (license)
8. Contact (mailing lists, GitHub)
9. Contributors (THANKS document)
10. Commercial support
11. Website
12. Source code (git clone)
13. Security problems
14. Backers/Sponsors

### 3. Voice
- Tone: Direct, no-nonsense, helpful
- Personality level: 1/10 (pure utility)
- Key phrases that stand out: None (no personality injections)

### 4. Visuals
- Screenshots/GIFs: None
- Diagrams: None
- Badges: None
- Demo videos: None

**Only visual**: The curl logo at the top

### 5. Social Proof
- GitHub stars: Not mentioned
- Testimonials: None
- User logos: None
- Usage stats: None
- Contributors: References THANKS document
- Backers/Sponsors: "Become a backer" and sponsors page link

**Weak social proof**: Relies on external sponsors page

### 6. CTAs
Primary call-to-action: Read the docs
- man page: curl.se/docs/manpage.html
- everything curl: everything.curl.dev
- INSTALL document: curl.se/docs/install.html

Secondary CTAs:
- Commercial support: curl.se/support.html
- Website: curl.se/
- Source: git clone https://github.com/curl/curl
- Backers: opencollective.com/curl

Placement: Each CTA is a single link in its own section

### 7. Length Metrics
- Word count estimate: ~200 words
- Section count: 14 tiny sections
- Time to read: 1-2 minutes
- Above-the-fold content: Logo + definition + protocols

**Critical observation**: This README is a directory, not documentation.

### 8. Differentiation
What makes this README stand out?
- Unique element 1: Lists all 26 supported protocols prominently
- Unique element 2: Links to "everything curl" comprehensive guide
- What they do better than competitors: Directory structure - every section is 1-2 sentences max

### 9. Alfred Applicability
Ideas to steal/adapt:
- Pattern: Logo-first, then immediate value statement
- Voice element: "Here's where to find what you need"
- Structural choice: Directory README that points to comprehensive docs

### 10. Raw Notes

**Logo placement**:
```markdown
# [![curl logo](https://curl.se/logo/curl-logo.svg)](https://curl.se/)
```

**Opening definition (perfect clarity)**:
"curl is a command-line tool for transferring data from or to a server using URLs. It supports these protocols: DICT, FILE, FTP, FTPS, GOPHER, GOPHERS, HTTP, HTTPS, IMAP, IMAPS, LDAP, LDAPS, MQTT, MQTTS, POP3, POP3S, RTMP, RTMPS, RTSP, SCP, SFTP, SMB, SMBS, SMTP, SMTPS, TELNET, TFTP, WS and WSS."

**Protocol list as credibility**: Listing 26 protocols immediately demonstrates capability.

**Section structure (each is minimal)**:
```markdown
## Open Source
curl is Open Source and is distributed under an MIT-like license.

## Contact
Contact us on a suitable mailing list or use GitHub issues/pull requests/discussions.

## Commercial support
For commercial support, maybe private and dedicated help... visit the support page.
```

**Security section (important pattern)**:
```markdown
## Security problems
Report suspected security problems privately and not in public.
```

---

## Quick Scoring

| Criteria | Score 1-5 | Notes |
|----------|-----------|-------|
| Clarity | 5 | Crystal clear directory |
| Excitement | 1 | Zero excitement |
| Trust | 4 | Professional, established tone |
| Technical depth | 2 | Delegates to docs |
| Visual appeal | 2 | Logo only |
| Overall | 3 | Works as directory, not pitch |

## Key Lesson

**The README as directory**: curl's README doesn't try to teach or sell. It's a navigational hub that says:
- Here's what this is (1 sentence)
- Here's where to learn (man page, book, install guide)
- Here's how to engage (contact, contribute, support)

**For Alfred**: Consider if README should be a directory or a pitch. curl chooses directory because everyone already knows what it is.
