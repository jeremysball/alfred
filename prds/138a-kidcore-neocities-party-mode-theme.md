# Sub-PRD: Kidcore Neocities Full Chaos Theme for Web UI

**Parent PRD**: [#138 Modernize Web UI Design](./138-modernize-web-ui-design.md)  
**Local ID**: 138A (sub-PRD, no GitHub issue)  
**Status**: Draft  
**Priority**: Medium  
**Created**: 2026-03-21

---

## 1. Problem Statement

PRD #138 improves Alfred's default Web UI, but it does not cover the user's actual request here: a deliberately obnoxious, super-colorful, hyper-animated, kidcore / Neocities-style theme.

This should not become a whole secondary design system with lots of toggles and modes. It is one opt-in theme that is supposed to feel loud, tacky, nostalgic, and a little bad on purpose.

The point is not restraint.

The point is:
- rainbow gradients
- stickers and badges
- glitter and marquee energy
- bouncy animations
- silly sound effects
- looping music
- strong early-web personal-site vibes

This theme is **not** the default. It is a special-purpose aesthetic mode for users who explicitly want chaos.

---

## 2. Goals & Success Criteria

### Goals

1. Add one new opt-in theme: `kidcore-playground`.
2. Make the UI feel unmistakably kidcore / Neocities / toybox chaos.
3. Add heavy styling and animation directly into the theme rather than through extra configuration layers.
4. Add sound effects and looping music with only the minimum controls required.
5. Keep the app usable enough that chat, scrolling, and input still work.

### Success Criteria

- [ ] Theme appears in the theme selector and persists across refresh.
- [ ] Theme visibly transforms the app shell, header, messages, composer, and controls.
- [ ] Theme includes animated decorative effects by default.
- [ ] Sound effects fire for core interactions.
- [ ] Music starts only after clicking a visible play control.
- [ ] A visible mute / stop control exists.
- [ ] The UI is visually ridiculous without completely breaking message reading or input.

---

## 3. Non-Goals

This sub-PRD intentionally does **not** include:

- Party Mode toggles
- low-stimulation mode
- separate controls for sound FX vs music
- advanced motion settings
- accessibility preference center
- theme editor / customization panel
- making this the default theme

Users who do not want this experience can simply choose another theme.

---

## 4. Proposed Solution

### 4.1 Theme Identity

Add a single theme: `kidcore-playground`.

Visual direction:
- hot pink, cyan, lime, yellow, purple, electric blue
- glossy buttons and candy surfaces
- checkerboard / sparkle / star motifs
- sticker-like badges such as `NEW!`, `WOW!`, `YIPPEE!`
- chunky borders and layered shadows
- animated gradients, wiggles, floats, shimmers, and bounces
- retro-web / GeoCities / Neocities / toy-box energy

### 4.2 Scope of Styling

The theme should visibly affect:
- app shell
- header
- connection pill
- message cards
- composer / send button
- status bar
- toast notifications
- session list cards
- tool call cards
- empty / onboarding presentation if present

### 4.3 Audio Behavior

Audio is part of the theme, but kept simple.

Rules:
- music does **not** autoplay on page load
- music starts only after clicking a visible play button
- sound effects and music belong to the same theme behavior
- one visible mute / stop control can kill the noise
- no deeper settings UI is required

### 4.4 Product Standard

This theme should be judged against the following standard:

> "Does this feel like a chaotic, glittery, over-designed personal website from the best and worst parts of the old web?"

Not:

> "Is this elegant, restrained, or highly configurable?"

---

## 5. Implementation Milestones

### Milestone 1: Theme Registration & Base Surfaces
**Goal**: Add the theme and restyle the core UI surfaces.

- [ ] Add `kidcore-playground.css`
- [ ] Register the theme in `theme-selector.js`
- [ ] Load the theme stylesheet from `index.html`
- [ ] Restyle the shell, header, messages, composer, and primary controls
- [ ] Verify theme selection and persistence still work

**Validation**: The new theme is selectable and immediately transforms the main UI.

### Milestone 2: Full Chaos Visual Layer
**Goal**: Add the intentionally obnoxious decorative effects.

- [ ] Add animated gradients, sparkles, sticker/badge accents, and marquee-style flair
- [ ] Add theme-specific motion like wiggle, shimmer, bounce, and float
- [ ] Push status bar, toasts, and session/tool cards further into the theme aesthetic
- [ ] Verify the app still reads as a chat UI rather than pure visual soup

**Validation**: The UI feels obviously ridiculous and heavily themed.

### Milestone 3: Audio & Music
**Goal**: Add the theme's noise.

- [ ] Add sound effects for key interactions
- [ ] Add looping background music
- [ ] Add a visible play control for starting music
- [ ] Add a visible mute / stop control
- [ ] Wire sounds without blocking the app when audio fails or is blocked

**Validation**: Audio works after explicit user action and can be shut off easily.

### Milestone 4: Browser Verification & Final Polish
**Goal**: Make sure the theme is chaotic but still shippable.

- [ ] Verify the theme in a real browser session
- [ ] Verify music start / mute controls work
- [ ] Verify input, scrolling, and message rendering still work
- [ ] Verify mobile does not fully implode
- [ ] Fix obvious regressions caused by the theme

**Validation**: The theme is absurd, functional, and opt-in.

---

## 6. Likely Files

```text
src/alfred/interfaces/webui/static/
├── css/
│   ├── base.css
│   ├── themes.css
│   └── themes/
│       └── kidcore-playground.css
├── js/
│   ├── main.js
│   ├── audio-manager.js
│   └── components/
│       ├── theme-selector.js
│       ├── status-bar.js
│       ├── toast-container.js
│       ├── session-list.js
│       └── tool-call.js
├── audio/
│   ├── kidcore-loop.mp3
│   ├── click.mp3
│   ├── send.mp3
│   ├── success.mp3
│   └── error.mp3
└── index.html

tests/webui/
├── test_kidcore_theme.py
├── test_kidcore_chaos.py
└── test_kidcore_audio.py
```

---

## 7. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Theme becomes unreadable | High | Medium | Keep message/content surfaces readable even when everything else is loud |
| Theme becomes too configurable | Medium | Medium | Do not add extra preference layers |
| Browser blocks music | Medium | High | Require explicit play button |
| Theme annoys users | Low | High | It is opt-in; users can switch themes |
| Animations hurt performance | Medium | Medium | Fix obvious regressions during browser verification |

---

## 8. Acceptance Notes

This theme is intentionally maximalist and should lean into that.

It does **not** need to be tasteful.

It **does** need to:
- look wild
- feel fun
- make noise
- remain selectable
- remain stoppable
- not completely wreck the app

---

## 9. Next Step

Create execution plans for Milestones 1-4 and implement them test-first.

---

**Last Updated**: 2026-03-21
