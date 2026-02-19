# Project Research: Zep

**URL**: https://github.com/getzep/zep  
**Category**: AI Memory & Context  
**Lines**: ~250

---

## 1. Hook (First 3 Seconds)

**Logo**: Centered, 150px, links to website  
**Headline**: "Zep: End-to-End Context Engineering Platform"  
**Subhead**: "Examples, Integrations, & More"

**What grabs attention**:
- "Context Engineering" (category creation, not just "memory")
- "sub-200ms latency" (specific performance claim)
- Clean, professional aesthetic

**Strategy**: Technical authority through specificity. They invented a category.

---

## 2. Structure

Information hierarchy:

1. **Logo + Headline + Subhead** (centered)
2. **Badges** (Discord, Twitter)
3. **What is Zep?** (H2 with emoji)
4. **How Zep works** (3-step process)
5. **Getting Started** (Cloud signup → SDKs → Help)
6. **About This Repository** (WIP notice)
7. **Repository Structure** (what's inside)
8. **Development Setup** (UV workspace)
9. **Contributing**
10. **Graphiti** (powered by mention)
11. **Community Edition (Legacy)** (deprecation notice)

**What comes first**: Category definition ("Context Engineering"), then immediate cloud signup CTA.

---

## 3. Voice

**Tone**: Technical, authoritative, cloud-focused  
**Personality level**: 3/10 (professional, minimal)  
**Formality**: Enterprise/SaaS

**Key phrases**:
- "end-to-end context engineering platform" (category definition)
- "sub-200ms latency" (specific metric)
- "relationship-aware context blocks" (technical precision)
- "This repository is currently a work in progress" (transparency)

**Notable**:
- Honest about repository status (WIP)
- Clear deprecation of Community Edition (brave move)
- Performance metrics upfront (200ms)

---

## 4. Visuals

- **Logo**: 1 (centered, 150px)
- **Screenshots/GIFs**: 0
- **Diagrams**: 0
- **Badges**: 2 (Discord, Twitter)
- **Code blocks**: 5 (install, setup, workspace commands)
- **Emoji**: 1 (💬 in H2)

**Visual strategy**: Minimalist, professional. Relies on clear text and structure.

---

## 5. Social Proof

**Explicit**:
- Discord badge
- Twitter follow count

**Implicit**:
- "SOC2 Type 2 / HIPAA compliance" (enterprise credibility)
- Graphiti open-source project (technical depth)
- Multiple SDKs (Python, TypeScript, Go)

**Missing**: GitHub stars, user testimonials, case studies

---

## 6. CTAs

**Primary**:
- Sign up for Zep Cloud (website link)
- SDK installation (pip, npm, go get)

**Secondary**:
- Documentation (help.getzep.com)
- Discord Community
- Support

**Placement**:
- Cloud signup immediately after value prop
- SDKs in their own section
- Help resources clearly listed

---

## 7. Length Metrics

- **Word count**: ~500 words
- **Section count**: 11
- **Time to read**: 5-6 minutes
- **Above-the-fold content**: Logo, headline, what it is, how it works

**Verdict**: Concise but comprehensive. Balances technical depth with brevity.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Category creation**: "Context Engineering" not "memory" or "RAG". This positions them as defining the space.

2. **Performance specificity**: "sub-200ms latency" is a concrete claim that matters for production.

3. **Transparent pivot**: They deprecated their open-source Community Edition and moved to cloud-only. The README handles this honestly with a clear deprecation notice.

4. **3-step simplification**: Complex product explained as Add → Graph RAG → Retrieve.

5. **Powered by Graphiti**: They open-sourced the underlying knowledge graph framework while monetizing the platform. Smart separation.

6. **Compliance signaling**: SOC2 Type 2 / HIPAA mentioned for enterprise trust.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Category definition ("Context Engineering")
- Performance metric upfront (sub-200ms)
- 3-step process explanation
- Clear separation between product (Zep) and underlying tech (Graphiti)

**Voice**:
- Specific metrics over vague claims
- Transparent about limitations/changes
- Enterprise credibility signals

**Technical demonstration**:
- Multi-language SDK support
- Workspace organization (UV)
- Clear deprecation communication

### Structural choices:

**Skip**:
- Cloud-only model (Alfred is self-hosted)
- Deprecation notices (not relevant)
- Heavy enterprise focus (too dry)

**Adapt**:
- Category creation approach (what space does Alfred define?)
- 3-step explanation (simplify complex concepts)
- Performance claims (be specific about Alfred's strengths)
- Multi-interface documentation (Telegram, CLI, library)

**Competitive differentiation**:
- Zep = "Context Engineering Platform" (cloud, enterprise)
- Alfred = "Persistent Memory for LLMs" (local, personal)

---

## 10. Raw Notes

### Header strategy:
```markdown
<p align="center">
  <a href="https://www.getzep.com/">
    <img src="..." width="150" alt="Zep Logo">
  </a>
</p>

<h1 align="center">
Zep: End-to-End Context Engineering Platform
</h1>

<h2 align="center">Examples, Integrations, & More</h2>
```

Note: Logo is clickable. Two headlines (H1 + H2) for hierarchy.

### Category definition:
"Zep is an end-to-end context engineering platform that delivers the right information at the right time with sub-200ms latency."

Pattern: [Product] is [category] that [benefit] with [metric].

### Problem statement:
"It solves the agent context problem by assembling comprehensive, relationship-aware context from multiple data sources..."

Clear problem identification.

### 3-step process:
1. **Add context**: Feed chat messages, business data, and events
2. **Graph RAG**: Zep automatically extracts relationships
3. **Retrieve & assemble**: Get pre-formatted, relationship-aware context

This simplifies a complex product.

### Cloud-first positioning:
"Visit www.getzep.com to sign up for Zep Cloud, our managed service..."

Primary CTA is cloud signup, not self-hosted install.

### Multi-SDK approach:
- Python: `pip install zep-cloud`
- TypeScript: `npm install @getzep/zep-cloud`
- Go: `go get github.com/getzep/zep-go/v2`

Consistent naming (`zep-cloud` vs `zep-go`).

### Deprecation handling:
```markdown
## Community Edition (Legacy)

**Note**: Zep Community Edition is no longer supported and has been deprecated.

Read more about this change in our announcement: [Announcing a New Direction...](...)
```

Honest, clear, provides migration path.

### Open-source separation:
Zep (cloud platform) is proprietary. Graphiti (knowledge graph) is open-source. Smart strategy: open-source the engine, monetize the platform.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 5/5 | Excellent 3-step explanation |
| Excitement | 2/5 | Professional but dry |
| Trust | 4/5 | Transparency about WIP/deprecation |
| Technical depth | 4/5 | Good without overwhelming |
| Visual appeal | 3/5 | Clean, minimal |
| **Overall** | **3.6/5** | Strong positioning, clear communication |

---

## Key Takeaway for Alfred

Zep proves that **category creation + specificity** builds authority. They don't compete on "memory"—they invented "Context Engineering." Their "sub-200ms" claim is concrete and credible.

For Alfred: Define the category (not "AI assistant"—too broad). Be specific about what makes Alfred unique (local? persistent? file-based?). Make concrete claims about performance or capabilities.

**The lesson**: Don't compete in existing categories. Define your own.
