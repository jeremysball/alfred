# Demo GIF Storyboard for Alfred

**Duration**: 15 seconds  
**Resolution**: 800x600 (or 1200x800 for retina)  
**FPS**: 15  
**Format**: GIF or MP4 → GIF

---

## Scene 1: CLI Interface (0-5 seconds)

**Visual**: Terminal window, dark theme

**Action**:
```
$ alfred chat

Alfred: Hello! I'm Alfred, your AI assistant with memory.
        What would you like to work on?

You: Let's design a database schema for the user module

Alfred: *thinking* 🔍

Alfred: I'll help you design that schema. What entities 
        do we need to track for users?

You: Users, profiles, and authentication

Alfred: Got it. Here's a proposed schema...
        [schema appears]
```

**Transition**: Fade to Scene 2

---

## Scene 2: Time Passes (5-6 seconds)

**Visual**: Simple "2 days later" text overlay with calendar icon

**Action**:
- Text fades in: "📅 2 days later..."
- Hold for 1 second
- Fade out

---

## Scene 3: Return to CLI (6-11 seconds)

**Visual**: Terminal window (same as Scene 1)

**Action**:
```
$ alfred chat

Alfred: Welcome back! We were working on database schemas 
        last time. How's that going?

You: What did we decide about the user table?

Alfred: *searching memory* 🔍

Alfred: You decided on:
        - users: id, email, created_at
        - profiles: user_id, name, bio
        - auth: user_id, hash, last_login

You: Right! Thanks Alfred.

Alfred: *tips hat* 🎩 Anytime!
```

**Transition**: Fade to Scene 4

---

## Scene 4: Telegram Interface (11-15 seconds)

**Visual**: Phone mockup with Telegram chat

**Action**:
- Show phone receiving notification
- Open Telegram to @AlfredMemoryBot
- Show message:

```
You: [mobile] Remind me what we decided about the DB

Alfred: 🧠 From your conversation 2 days ago:

        You designed a 3-table schema:
        • users (auth)
        • profiles (info)  
        • auth (security)

        Want me to show the full schema?

You: No, that's perfect. Thanks!

Alfred: 🎩 Always here to help!
```

**Final Frame**: Alfred logo + tagline: "Alfred remembers so you don't have to"

---

## Recording Instructions

### Option 1: Terminal Recording (CLI scenes)

**Tools**: asciinema, terminalizer, or simple screen recording

**Steps**:
1. Set up clean terminal (iTerm2 or Warp recommended)
2. Use dark theme (Solarized Dark or Dracula)
3. Record actual Alfred interaction
4. Speed up pauses (keep natural typing rhythm)
5. Export as GIF

**Terminal Setup**:
```bash
# Clean prompt
export PS1="$ "

# Clear screen
alias cls='clear'

# Start recording
asciinema rec demo.cast
```

### Option 2: Phone Recording (Telegram scene)

**Tools**: iOS Simulator + screen recording, or actual phone

**Steps**:
1. Set up Telegram bot
2. Open conversation
3. Record interaction
4. Crop to phone frame
5. Export as GIF segment

### Option 3: Simulated (After Effects/Figma)

**Tools**: Figma, After Effects, or simple HTML/CSS animation

**Steps**:
1. Design terminal UI in Figma
2. Animate text appearing
3. Add cursor blink
4. Export frames
5. Compile to GIF

---

## Technical Specs

**Recommended**:
- **Tool**: terminalizer (https://terminalizer.com/)
- **Theme**: "flat" or custom dark theme
- **Frame delay**: 100ms (10 FPS for typing, 30 FPS for animations)
- **Max colors**: 256 (for GIF)
- **Optimization**: gifsicle or similar

**Alternative Tools**:
- asciinema + asciicast2gif
- screen recording + ffmpeg
- Kap (macOS screen recorder with GIF export)
- LICEcap (simple GIF recorder)

---

## Editing Notes

1. **Scene transitions**: Use simple fades (200ms)
2. **Cursor**: Show blinking cursor during typing
3. **Emojis**: Keep emojis in output (🧠 🔍 🎩)
4. **Speed**: Real-time typing is too slow, use 1.5-2x speed
5. **Loops**: GIF should loop smoothly (return to start)

---

## Final Deliverable

**Filename**: `alfred-demo.gif`  
**Location**: `assets/alfred-demo.gif`  
**Size**: < 5MB (GitHub limit for README)  
**Dimensions**: 800x600 or 1200x800

---

## Fallback Option

If GIF creation is complex, use:
1. **Static screenshot** showing both CLI and Telegram
2. **Link to YouTube video** with full demo
3. **Multiple screenshots** showing the workflow

**Recommended fallback**: Static hero image with play button overlay linking to YouTube.
