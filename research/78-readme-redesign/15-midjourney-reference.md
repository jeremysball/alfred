# Project Research: Midjourney Styles and Keywords Reference

**URL**: https://github.com/willwulfken/MidJourney-Styles-and-Keywords-Reference  
**Category**: Modern Visual AI (Community Resource)  
**Lines**: ~300+

---

## 1. Hook (First 3 Seconds)

**Banner**: Responsive dark/light mode banner image  
**Disclaimer**: Clear statement of non-affiliation  
**Visual Buttons**: Massive custom button images for navigation

**What grabs attention**:
- Custom-designed banner (not just logo)
- Dark/light mode responsive
- Visual buttons instead of text links
- Extremely visual approach

---

## 2. Structure

Information hierarchy:

1. **Responsive Banner** (dark/light mode)
2. **Disclaimer** (non-affiliation)
3. **Visual Button Grid** (Sponsors, PRs, Links, Discord, How-To, Notes)
4. **Section Header** ("Styles")
5. **Visual Category Buttons** (Colors, Emojis, Themes, Design Styles, etc.)

**What comes first**: Visual banner → Disclaimer → Visual navigation.

---

## 3. Voice

**Tone**: Visual, enthusiastic, community-focused  
**Personality level**: 7/10 (highly visual, engaging)  
**Formality**: Casual, creative

**Key phrases**:
- "I am not officially affiliated with MidJourney" (transparency)
- Emoji-heavy section headers

**Notable**:
- Extremely visual (custom buttons for everything)
- Community resource (not official)
- Dark/light mode throughout

---

## 4. Visuals

- **Banner**: 1 (responsive dark/light)
- **Custom Buttons**: 20+ (navigation and category buttons)
- **Screenshots**: 0 (but buttons show visual examples)
- **Icons**: Emoji throughout

**Visual strategy**: Custom-designed buttons as navigation. Extremely visual, minimal text.

---

## 5. Social Proof

**Explicit**:
- Discord thread link
- Sponsors button

**Implicit**:
- Comprehensive categorization (maturity)

**Missing**: Stars, testimonials, contributor count

---

## 6. CTAs

**Primary**:
- Style category buttons (visual)
- How-To Guide
- Discord thread

**Secondary**:
- Sponsors
- Pull requests

**Placement**:
- Visual buttons immediately after banner

---

## 7. Length Metrics

- **Word count**: ~200 words (very text-light)
- **Visual elements**: 20+ custom buttons
- **Time to read**: 2-3 minutes (mostly visual scanning)
- **Above-the-fold content**: Banner + navigation buttons

**Verdict**: Extremely visual. README as visual interface, not text document.

---

## 8. Differentiation

**What makes this README stand out**:

1. **Custom button navigation**: Every link is a custom-designed button image.

2. **Dark/light mode responsiveness**: Banner and buttons switch modes.

3. **Visual categorization**: Categories shown as buttons with icons/emojis.

4. **Transparency**: Clear disclaimer about non-affiliation.

5. **Community resource**: Not a product README, but a reference guide.

---

## 9. Alfred Applicability

### Patterns to steal:

**Structure**:
- Responsive banner (dark/light mode)
- Visual navigation elements
- Clear disclaimer/transparency

**Voice**:
- Visual-first communication
- Emoji for scannability

### Structural choices:

**Skip**:
- Custom button approach (too heavy for Alfred)
- Emoji overload

**Adapt**:
- Responsive banner/logo
- Visual organization
- Transparency about scope

---

## 10. Raw Notes

### Responsive banner:
```markdown
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="/Images/Repo_Parts/Banner/banner_dark.png">
  <source media="(prefers-color-scheme: light)" srcset="/Images/Repo_Parts/Banner/banner_light.png">
  <img alt="Midjourney Styles and Keywords Reference" src="/Images/Repo_Parts/Banner/banner_light.png">
</picture>
```

### Visual button pattern:
```markdown
<a href="/Pages/Sponsors.md">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="/Images/Repo_Parts/Buttons/button_sponsors.webp" width=377>
    <source media="(prefers-color-scheme: light)" srcset="/Images/Repo_Parts/Buttons/button_sponsors_light.webp" width=377>
    <img alt="⭐ Sponsors" src="/Images/Repo_Parts/Buttons/button_sponsors.webp" width=377>
  </picture>
</a>
```

Each button is:
- Custom-designed image
- Responsive dark/light
- Fixed width (377px)
- Alt text with emoji

### Disclaimer:
```markdown
<blockquote>
  <h6>DISCLAIMER: I am not officially affiliated with MidJourney.</h6>
</blockquote>
```

Clear transparency.

---

## Quick Scoring

| Criteria | Score | Notes |
|----------|-------|-------|
| Clarity | 4/5 | Visual but clear |
| Excitement | 5/5 | Extremely visual |
| Trust | 3/5 | Disclaimer helps |
| Technical depth | 2/5 | Reference, not product |
| Visual appeal | 5/5 | Custom everything |
| **Overall** | **3.8/5** | Unique visual approach |

---

## Key Takeaway for Alfred

Midjourney Reference proves that **extreme visual design** (custom buttons, responsive images) creates a unique experience. However, this is a reference guide, not a product README.

For Alfred: Use responsive dark/light logo. Add visual organization. But keep it simpler than custom buttons.

**Note**: This is a community reference, not the official Midjourney product (which doesn't have an open-source GitHub presence).
