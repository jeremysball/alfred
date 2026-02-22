# Alfred Banner & Logo Prompts for Gemini Nano Banana Pro

## Best Practices Summary (Compiled from Research)

### Core Principles
1. **Structure your prompt**: Subject → Composition → Action → Location → Style → Technical specs
2. **Be specific, not vague**: "Deep navy blue with cyan accents" > "blue colors"
3. **Define camera/framing**: Wide shot, close-up, top-down view, etc.
4. **Specify lighting**: Chiaroscuro, soft ambient, dramatic rim lighting, etc.
5. **Include text instructions**: Specify font style, placement, rendering quality
6. **Set resolution/aspect ratio**: Essential for banners vs logos

### Nano Banana Pro Specific Tips
- Use conversational refinement if first attempt is 80% right (don't regenerate from scratch)
- For text in images, be explicit about exact spelling and style
- Specify "flat design" or "vector style" for logos to get clean edges
- Request "4K resolution" or "high resolution" for quality
- Use negative constraints: "no gradients", "no shadows", "simple background"

---

## Prompt 1: GitHub Social Banner (1280x640px)

**Purpose**: Top-of-readme banner, social media sharing

```
Create a wide horizontal banner image (1280x640 pixels, 2:1 aspect ratio) for an open-source AI assistant project called "Alfred - The Rememberer".

SUBJECT: A stylized memory moth as the central icon — an elegant moth with wings that contain glowing neural network patterns, data streams, and memory fragments visualized as soft light particles. The moth should feel wise and helpful, not creepy.

COMPOSITION: Centered moth with wings slightly spread, surrounded by a subtle aura of memories visualized as floating luminescent fragments (like fireflies or memory wisps). The moth is emerging from or merging with flowing data streams.

STYLE: Dark mode aesthetic with deep navy (#0a1628) as the primary background. Accent colors: electric cyan (#00d9ff), soft amber (#ffb84d), and white for highlights. The overall feel should be: sophisticated, technical but warm, trustworthy. Think: premium open-source project, not corporate tech.

LIGHTING: The moth wings should have a soft bioluminescent glow. Subtle rim lighting on edges. Background has depth with very faint grid patterns and particle effects suggesting data/memory.

TEXT: In the lower third, clean sans-serif text reading "Alfred" (larger, primary) and below it in smaller text: "The Rememberer". Text should be crisp white with subtle glow, professionally integrated into the design.

TECHNICAL: High resolution, clean edges, works well at small sizes. No watermarks, no signatures. Professional open-source project aesthetic.
```

---

## Prompt 2: Square Logo (512x512px)

**Purpose**: GitHub profile picture, favicon base, app icon

```
Create a square logo (512x512 pixels) for "Alfred - The Rememberer", an AI memory assistant.

SUBJECT: A minimalist, iconic moth symbol where the wings form a stylized brain or memory pattern. The moth should be abstract enough to work as an icon but still recognizable as a moth.

COMPOSITION: Centered, symmetrical design. The moth's body forms a subtle "A" shape. Wings spread horizontally to fill the square canvas comfortably with breathing room.

STYLE: Flat vector-style design with clean edges. No gradients, no complex shading — this needs to work at 32x32 as a favicon. Dark navy background (#0a1628) with the moth in electric cyan (#00d9ff) and white accents. Think: modern app icon, clean and memorable.

TEXT: No text in this version — pure icon/symbol design.

TECHNICAL: Crisp vector-like edges, high contrast, readable at small sizes. Works on both dark and light backgrounds. Consider how it looks in a circular crop (for profile pictures).

CONSTRAINTS: No gradients, no drop shadows, no photorealism. Flat, iconic, scalable.
```

---

## Prompt 3: Horizontal Logo with Wordmark

**Purpose**: Documentation headers, README inline logo

```
Create a horizontal logo with wordmark (800x200 pixels, 4:1 aspect ratio) for "Alfred - The Rememberer".

SUBJECT: A simplified moth icon on the left, with the wordmark "Alfred" next to it.

COMPOSITION: Moth icon on the left (taking up about 1/4 of width), followed by "Alfred" in clean modern typography. The moth icon should be simplified enough to work alongside text without competing with it.

STYLE: Dark navy background (#0a1628) or transparent. Moth icon in electric cyan (#00d9ff). Typography in white, using a clean geometric sans-serif font (similar to Inter, SF Pro, or system fonts). Professional open-source aesthetic.

THE MOTH ICON: Simplified, geometric moth. Wings can suggest memory/neural patterns through subtle line work. Should feel: smart, helpful, trustworthy.

TEXT: "Alfred" as the primary wordmark. Optionally a small tagline below: "remembers so you don't have to" in lighter weight/smaller size.

TECHNICAL: Works on both dark backgrounds and (with inversion) light backgrounds. Clean edges, web-ready. Transparent background preferred.
```

---

## Prompt 4: Animated-Style Banner (Alternative)

**Purpose**: More playful, personality-forward version

```
Create a wide banner (1280x640 pixels) for "Alfred", an AI assistant with persistent memory.

SUBJECT: A friendly, wise moth character with large expressive eyes (but not cartoonish — more like an illustrated storybook style). The moth is surrounded by glowing memory orbs floating around it, each orb containing tiny abstract scenes or symbols representing different types of memories.

COMPOSITION: Moth positioned slightly left-of-center, facing right, with memory trailing behind and around it like a protective aura. The right side has space for text overlay.

STYLE: Illustrated aesthetic with rich colors. Deep midnight blue background (#0a1628) transitioning to slightly lighter blue on the right. Accents in warm amber (#ffb84d), cyan (#00d9ff), and soft white. Think: Ghibli-inspired but for a tech product. Warm, approachable, slightly magical.

LIGHTING: Soft glow from the memory orbs creating ambient light. The moth has subtle bioluminescence.

FEELING: This should evoke: "A wise companion who keeps your memories safe." Warmth, trust, a touch of wonder.

TEXT SPACE: Leave the right third relatively empty for text overlay, or include text integrated into the design reading "Alfred" and "The Rememberer".

TECHNICAL: High resolution, clean illustration style, works for web and social.
```

---

## Refinement Instructions (Use After Initial Generation)

If the first output is close but needs adjustment, use conversational edits:

### For too complex/busy:
```
Simplify this design. Remove [specific elements]. Make the moth cleaner and more iconic. Reduce the number of [particles/effects]. Keep the color palette but reduce visual complexity.
```

### For wrong colors:
```
Change the color palette to use exactly these hex codes: #0a1628 (background), #00d9ff (primary accent), #ffb84d (secondary accent), #ffffff (highlights).
```

### For text issues:
```
The text should be "Alfred" exactly — fix the spelling. Make the font cleaner and more modern, similar to Inter or SF Pro.
```

### For wrong style:
```
Make this more [minimalist / illustrated / technical]. Remove [gradients / shadows / photorealistic elements].
```

---

## Quick Reference: Brand Colors

| Color | Hex | Usage |
|-------|-----|-------|
| Deep Navy | `#0a1628` | Primary background |
| Electric Cyan | `#00d9ff` | Primary accent, moth wings |
| Warm Amber | `#ffb84d` | Secondary accent, memory glow |
| Pure White | `#ffffff` | Text, highlights |
| Soft Gray | `#64748b` | Muted elements |

---

## Quick Reference: Brand Personality

- **Not**: Corporate, cold, overly technical, playful/cartoonish
- **Yes**: Sophisticated, warm, trustworthy, technically competent but human
- **Analogy**: A thoughtful librarian who knows exactly what you need before you ask
