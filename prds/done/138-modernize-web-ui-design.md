# PRD: Modernize Web UI Design

**GitHub Issue**: [#138](https://github.com/jeremysball/alfred/issues/138)  
**Status**: Closed - Superseded by PRDs #138A, #142, #144, and #145  
**Priority**: High  
**Created**: 2026-03-20  
**Last Updated**: 2026-03-22

---

## 1. Problem Statement

The current Alfred web UI suffers from critical visual and UX issues that negatively impact user experience:

### Visual Problems
- **Dated aesthetic**: The "Dark Academia" theme uses muddy brown/gold colors that feel heavy and depressing
- **Poor contrast**: The "Thinking" reasoning section is barely visible (dark red on dark background)
- **Inconsistent alignment**: Message bubbles have confusing alignment - user messages appear left-aligned in some themes
- **Outdated typography**: Serif fonts feel old-fashioned for a modern tech product
- **Error-like system messages**: Gray background makes system messages appear broken or like errors

### UX Problems
- **No empty state**: Fresh sessions show nothing - confusing for first-time users
- **Missing visual hierarchy**: All elements compete for attention equally
- **No user differentiation**: No avatars/icons to visually distinguish user from assistant
- **Disconnected input**: Footer feels separate from chat, not part of the conversation flow
- **No message actions**: Can't copy, edit, or retry messages

### Layout Issues
- **Wasted space**: Max-width 800px constraints leave huge gaps on wide screens
- **No quick navigation**: Missing scroll-to-bottom button for long conversations

---

## 2. Goals & Success Criteria

### Primary Goals
1. Create a modern, clean visual aesthetic that feels professional and approachable
2. Improve visual hierarchy so users can easily scan and understand conversations
3. Add missing UX patterns (empty states, avatars, message actions)
4. Ensure consistent alignment and spacing across all viewports
5. Maintain theme system while modernizing the default experience

### Success Criteria
- [ ] Users can visually distinguish between user/assistant messages at a glance
- [ ] New users understand what to do on first visit (empty state)
- [ ] All text passes WCAG AA contrast standards (4.5:1 for normal text)
- [ ] Messages align consistently (user right, assistant left)
- [ ] Input area feels integrated with the conversation
- [ ] Users can copy message content with one click
- [ ] Mobile experience is as polished as desktop

---

## 3. Proposed Solution

### 3.1 New Default Theme: "Modern Dark"

Replace "Dark Academia" as the default with a clean, modern dark theme:

```css
/* Core Palette */
--bg-primary: #0d1117;        /* GitHub dark bg */
--bg-secondary: #161b22;      /* Slightly elevated */
--bg-tertiary: #21262d;       /* Inputs/cards */
--bg-hover: #30363d;          /* Hover states */

/* Accent Colors */
--accent-primary: #58a6ff;    /* Primary blue */
--accent-success: #238636;    /* Success green */
--accent-warning: #d29922;    /* Warning yellow */
--accent-danger: #da3633;     /* Error red */

/* Text Colors */
--text-primary: #f0f6fc;      /* Primary text */
--text-secondary: #8b949e;    /* Secondary/muted */
--text-tertiary: #6e7681;     /* Placeholders */

/* Message Colors */
--message-user-bg: #1f6feb;   /* User bubble - blue */
--message-user-text: #ffffff;
--message-assistant-bg: #21262d;
--message-assistant-border: #30363d;
```

### 3.2 Message Redesign

**Current Issues:**
- No avatars - hard to scan who said what
- Timestamps too prominent
- No visual differentiation between roles
- Inconsistent alignment

**New Design:**
```
┌─────────────────────────────────────────────────────┐
│ [👤] User                                    2:30 PM│
│ Hello, can you help me with something?              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│ [🤖] Alfred                                  2:30 PM│
│ Of course! I'd be happy to help. What do you need?  │
│                                                     │
│ [Copy] [Retry]                              [👍][👎]│
└─────────────────────────────────────────────────────┘
```

**Specifications:**
- Avatar: 32px circle with icon/initials
- User messages: Right-aligned with blue background
- Assistant messages: Left-aligned with subtle border
- Timestamps: Smaller, muted, aligned with avatar
- Action buttons: Appear on hover (desktop) or always visible (mobile)

### 3.3 Empty State

**Current:** Blank gray screen  
**New:** Friendly welcome message

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│                    🤖                               │
│                                                     │
│              Welcome to Alfred                      │
│                                                     │
│    I'm your AI assistant with persistent memory.    │
│    Ask me anything or try these commands:           │
│                                                     │
│    /new      Start a fresh conversation            │
│    /resume   Continue a previous chat              │
│    /sessions View your chat history                │
│    /help     See all available commands            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 3.4 Input Area Redesign

**Current:** Disconnected footer with sharp edges  
**New:** Floating integrated input

```
┌─────────────────────────────────────────────────────┐
│                                                     │
│   [Chat messages above]                             │
│                                                     │
│   ┌───────────────────────────────────────────┐    │
│   │  Type your message...               [Send]│    │
│   └───────────────────────────────────────────┘    │
│          Press Enter to send                        │
│          Shift+Enter for new line                   │
└─────────────────────────────────────────────────────┘
```

**Specifications:**
- Floating card style with subtle shadow
- Keyboard hint text below input
- Smooth focus animation
- Auto-expands for multi-line input

### 3.5 Reasoning Section Redesign

**Current:** Dark red on dark background, barely visible  
**New:** Collapsible with clear visual indicator

```
┌─────────────────────────────────────────────────────┐
│ [🤖] Alfred                                  2:30 PM│
│ ┌─────────────────────────────────────────────────┐ │
│ │ 💭 Thinking...                             [▼]  │ │
│ ├─────────────────────────────────────────────────┤ │
│ │ Let me break this down step by step...          │ │
│ │ 1. First, I need to understand the context      │ │
│ │ 2. Then analyze the requirements               │ │
│ └─────────────────────────────────────────────────┘ │
│                                                     │
│ Here's my response based on that thinking...        │
└─────────────────────────────────────────────────────┘
```

### 3.6 System Messages

**Current:** Gray box that looks like an error  
**New:** Subtle inline notification style

```
┌─────────────────────────────────────────────────────┐
│  ℹ️  New session started                            │
├─────────────────────────────────────────────────────┤
│  [Regular chat continues below]                     │
└─────────────────────────────────────────────────────┘
```

### 3.7 Mobile Optimizations

- Full-width message bubbles
- Bottom sheet for message actions
- Sticky input that doesn't cover content
- Swipe gestures for quick actions

---

## 4. Technical Implementation

### 4.1 File Changes

```
src/alfred/interfaces/webui/static/
├── css/
│   ├── base.css              # Update base styles
│   ├── themes.css            # Add modern-dark theme
│   └── themes/
│       ├── modern-dark.css   # NEW - Default theme
│       └── dark-academia.css # Keep as option
├── js/
│   ├── components/
│   │   ├── chat-message.js   # Add avatars, actions
│   │   └── empty-state.js    # NEW - Empty state component
│   └── main.js               # Add empty state logic
└── index.html                # Update to load new theme
```

### 4.2 CSS Architecture

Use CSS custom properties for theming:

```css
:root {
  /* Default (Modern Dark) */
  --bg-primary: #0d1117;
  --bg-secondary: #161b22;
  /* ... etc */
}

[data-theme="dark-academia"] {
  /* Override for Dark Academia */
  --bg-primary: #1a1814;
  /* ... etc */
}
```

### 4.3 Component Changes

**chat-message.js:**
- Add avatar render based on role
- Add action buttons (copy, retry, feedback)
- Improve timestamp formatting (relative time)
- Add hover states for actions

**New: empty-state.js:**
- Render welcome message
- Show command suggestions
- Animate on first load

---

## 5. Milestones

### Milestone 1: Foundation & Theme System
**Goal**: Create new Modern Dark theme and update CSS architecture

- [ ] Create `modern-dark.css` theme file with new color palette
- [ ] Update `base.css` with improved spacing and layout foundations
- [ ] Update `themes.css` to support theme switching with new default
- [ ] Update `index.html` to load new theme by default
- [ ] Ensure all existing themes still work

**Validation**: Switch between themes, all render correctly

---

### Milestone 2: Message Component Redesign
**Goal**: Modernize message bubbles with avatars and proper alignment

- [ ] Update `chat-message.js` with avatar rendering
- [ ] Implement consistent alignment (user right, assistant left)
- [ ] Redesign message header with avatar, role, timestamp
- [ ] Update message bubble styling for both themes
- [ ] Add hover effects and transitions

**Validation**: Messages look good in both themes, alignment is consistent

---

### Milestone 3: Empty State & Onboarding
**Goal**: Create welcoming first-time experience

- [ ] Create `empty-state.js` web component
- [ ] Design welcome screen with commands list
- [ ] Add empty state detection logic to `main.js`
- [ ] Animate empty state appearance
- [ ] Add "Get Started" quick action buttons

**Validation**: New session shows empty state, existing session loads messages

---

### Milestone 4: Input Area & Reasoning Redesign
**Goal**: Modernize input and reasoning sections

- [ ] Redesign input area as floating card style
- [ ] Add keyboard hints below input
- [ ] Redesign reasoning section with better visibility
- [ ] Add collapsible reasoning with smooth animation
- [ ] Update system message styling

**Validation**: Input feels integrated, reasoning is clearly visible

---

### Milestone 5: Message Actions
**Goal**: Add interactive message features

- [ ] Add copy button to messages (clipboard API)
- [ ] Add retry/regenerate button for assistant messages
- [ ] Add thumbs up/down feedback buttons
- [ ] Implement hover-to-reveal on desktop
- [ ] Implement tap-to-show on mobile

**Validation**: Can copy message text, buttons appear on hover/tap

---

### Milestone 6: Mobile Optimization
**Goal**: Ensure excellent mobile experience

- [ ] Test all changes on mobile viewport (375px)
- [ ] Optimize touch targets (min 44px)
- [ ] Add bottom sheet for message actions on mobile
- [ ] Ensure input doesn't cover content when keyboard opens
- [ ] Test on tablet viewport (768px)

**Validation**: Mobile experience feels native and polished

---

### Milestone 7: Accessibility & Polish
**Goal**: Ensure accessibility and final polish

- [ ] Verify WCAG AA contrast ratios (4.5:1 minimum)
- [ ] Add ARIA labels to interactive elements
- [ ] Ensure keyboard navigation works
- [ ] Test with screen reader
- [ ] Add focus indicators
- [ ] Performance audit (no layout thrashing)

**Validation**: Passes accessibility checks, feels polished

---

### Milestone 8: Documentation & Migration
**Goal**: Document changes and help users transition

- [ ] Update any web UI documentation
- [ ] Add theme customization guide
- [ ] Document new component APIs
- [ ] Create before/after comparison screenshots

**Validation**: Documentation is complete and accurate

---

## 6. Out of Scope

The following are intentionally NOT included in this PRD:

- New theme creation (beyond Modern Dark as default)
- Chat export/import functionality
- Message search
- Custom user avatars
- Real-time collaboration features
- Voice input/output
- Code syntax highlighting improvements
- File upload capabilities

---

## 7. Risks & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Users prefer old theme | Medium | Low | Keep Dark Academia as option |
| Breaking changes for custom CSS | Medium | Low | Document all CSS variable changes |
| Mobile performance issues | Medium | Low | Test on real devices, optimize animations |
| Accessibility regressions | High | Low | Audit each milestone with axe/lighthouse |

---

## 8. Future Considerations

Potential follow-up improvements after this PRD:

- Light theme variant
- User-customizable accent colors
- Message threading/replies
- Conversation folders/tags
- Full-text search across sessions
- Custom CSS injection for power users

---

## 9. References

- Current screenshots: `/screenshots/webui-analysis/`
- Current theme files: `src/alfred/interfaces/webui/static/css/themes/`
- Component files: `src/alfred/interfaces/webui/static/js/components/`
- Follow-up sub-PRD: `prds/138a-kidcore-neocities-party-mode-theme.md`

---

**Last Updated**: 2026-03-20  
**Next Review**: After Milestone 4 completion
