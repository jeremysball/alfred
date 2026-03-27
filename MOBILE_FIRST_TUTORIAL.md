# Alfred Mobile-First Features Tutorial

Complete guide to all native application experience features in PRD #159.

---

## 1. Command Palette (Ctrl+K / Cmd+K)

Quick access to all actions via searchable overlay.

### Opening
- **Desktop**: Press `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac)
- **Mobile**: Tap the palette icon in header or swipe down with two fingers

### Features
- **Fuzzy search**: Type "new" to find "New Session"
- **Recent commands**: Last 5 used commands appear at top
- **Contextual commands**: Different commands shown based on current view
- **Keyboard navigation**: ↑/↓ to select, Enter to execute, Esc to close

### Built-in Commands
| Command | Action |
|---------|--------|
| New Session | Create empty chat |
| Search Sessions | Open session search |
| Toggle Theme | Switch light/dark/auto |
| Install App | Show PWA install prompt |
| Keyboard Shortcuts | Show help overlay |
| Clear Conversation | Remove all messages |
| Export Chat | Download as markdown |

### Adding Custom Commands
```javascript
import { commandPalette } from './features/command-palette/index.js';

commandPalette.registerCommand({
  id: 'my-action',
  title: 'My Custom Action',
  shortcut: 'Ctrl+Shift+M',
  icon: '🔧',
  category: 'Tools',
  action: () => { /* your code */ }
});
```

---

## 2. Keyboard Shortcuts

### Global Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Open command palette |
| `Ctrl/Cmd + /` | Show keyboard help |
| `Ctrl/Cmd + N` | New session |
| `Ctrl/Cmd + F` | Focus search |
| `Esc` | Close modals/panels |

### Composer Shortcuts
| Shortcut | Action |
|----------|--------|
| `Enter` | Send message |
| `Shift + Enter` | New line |
| `Ctrl/Cmd + Enter` | Send (alternative) |
| `Ctrl/Cmd + Shift + ↑` | Edit last message |
| `Ctrl/Cmd + B` | Bold (wraps **) |
| `Ctrl/Cmd + I` | Italic (wraps *) |
| `Ctrl/Cmd + C` | Cancel streaming |

### Navigation Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + [` | Previous session |
| `Ctrl/Cmd + ]` | Next session |
| `Alt + 1-9` | Jump to session N |
| `Ctrl/Cmd + Shift + F` | Full search |

### Customizing Shortcuts
```javascript
import { keyboardManager } from './features/keyboard/index.js';

keyboardManager.register({
  key: 'm',
  ctrl: true,
  description: 'Toggle mute',
  action: () => audioManager.toggleMute()
});
```

---

## 3. Context Menus

Right-click or long-press for contextual actions.

### Message Context Menu
**Trigger**: Right-click any message (desktop) or long-press (mobile)

**Options**:
- Copy text
- Edit message (if yours)
- Delete message
- Reply (quotes message)
- Quote
- Regenerate (for assistant messages)
- Copy code block (if code present)

### Code Block Menu
**Trigger**: Right-click code block or long-press

**Options**:
- Copy code
- Copy with markdown
- Run in terminal (if shell)
- Open in editor

### Composer Menu
**Trigger**: Right-click in text input

**Options**:
- Paste
- Paste as plain text
- Insert from clipboard
- Clear

### Styling
Context menus adapt to:
- Current theme (light/dark)
- Viewport size (mobile = full bottom sheet)
- Safe areas (notches, home indicators)

---

## 4. System Notifications

### Toast Notifications
**Trigger**: Various system events

**Types**:
- `info`: General updates (blue)
- `success`: Actions completed (green)
- `warning`: Attention needed (yellow)
- `error`: Failures (red)

**Usage**:
```javascript
import { toast } from './features/notifications/index.js';

toast.success('Message sent!');
toast.error('Connection failed', { duration: 5000 });
toast.info('Syncing...', { persistent: true });
```

### Browser Notifications
**Setup**: Grant permission when prompted

**When triggered**:
- New message while tab inactive
- Job completion
- Connection lost/restored
- Session shared with you

**Customizing**:
```javascript
import { notificationService } from './features/notifications/index.js';

notificationService.requestPermission();
notificationService.notify({
  title: 'Alfred',
  body: 'New message',
  icon: '/static/icons/icon-192x192.png',
  tag: 'new-message',
  requireInteraction: false
});
```

### Favicon Badges
Shows unread count in tab icon when:
- Tab is not active
- New messages arrive
- @ mentions received

---

## 5. Drag & Drop

### File Upload
**Desktop**: Drag files anywhere onto the chat
**Mobile**: Tap attachment button or paste from clipboard

**Supported**:
- Images (jpg, png, gif, webp, svg)
- Documents (pdf, txt, md)
- Code files (py, js, ts, etc.)
- Archives (zip, with auto-extract option)

**Features**:
- Visual drop zone overlay
- Progress indicators
- Auto-compression for large images
- Multi-file support
- Clipboard paste (Ctrl/Cmd + V)

### URL Drop
Drag a URL to:
- Paste as link
- Fetch and summarize (if web search enabled)
- Create bookmark memory

### Image Handling
- Drag image from browser → Embed in chat
- Drag to composer → Upload
- Right-click image → "Add to conversation"

### Code Example
```javascript
import { dragDropManager } from './features/drag-drop/index.js';

dragDropManager.onDrop = async (files) => {
  for (const file of files) {
    if (file.type.startsWith('image/')) {
      await uploadImage(file);
    } else {
      await uploadDocument(file);
    }
  }
};
```

---

## 6. Mobile Gestures

### Pull-to-Refresh
**Trigger**: Pull down from top of message list

**Action**: Reconnects WebSocket and fetches latest messages

**Visual**: Animated spinner with progress indicator

**Code**:
```javascript
import { pullToRefresh } from './features/mobile-gestures/index.js';

pullToRefresh.enable({
  element: document.querySelector('.message-list'),
  threshold: 80, // pixels to trigger
  onRefresh: async () => {
    await reconnectAndSync();
  }
});
```

### Swipe-to-Reply
**Trigger**: Swipe right on any message

**Action**: Quotes message in composer

**Visual**: Reply icon appears during swipe

**Code**:
```javascript
import { swipeToReply } from './features/mobile-gestures/index.js';

swipeToReply.enable({
  selector: '.message-item',
  threshold: 100,
  onReply: (messageId) => {
    composer.quoteMessage(messageId);
  }
});
```

### Long-Press Context Menu
**Trigger**: Press and hold on message (mobile)

**Duration**: 500ms

**Haptic**: Light vibration on menu open

**Prevents**: Text selection conflict

**Code**:
```javascript
import { longPressMenu } from './features/mobile-gestures/index.js';

longPressMenu.enable({
  selector: '.message-item',
  duration: 500,
  menuItems: [
    { label: 'Copy', action: 'copy' },
    { label: 'Reply', action: 'reply' },
    { label: 'Delete', action: 'delete', danger: true }
  ]
});
```

### Fullscreen Compose (Mobile)
**Trigger**: Focus composer on small screens

**Behavior**:
- Hides header for max space
- Shows larger input area
- Dismiss with ↓ button or swipe down
- Auto-activates on mobile landscape

**Code**:
```javascript
import { fullscreenCompose } from './features/mobile-gestures/index.js';

fullscreenCompose.enable({
  breakpoint: 768, // pixels
  autoExpand: true,
  onEnter: () => header.hide(),
  onExit: () => header.show()
});
```

### Double-Tap to Like
**Trigger**: Double-tap message

**Action**: Adds 👍 reaction

### Pinch to Zoom (Images)
**Trigger**: Pinch on image attachments

**Behavior**: Fullscreen lightbox with zoom

---

## 7. Offline Support

### Connection Monitor
Automatically detects online/offline state.

**Indicators**:
- Subtle banner when offline
- "Reconnecting..." spinner
- "Back online" toast when restored

**Events**:
```javascript
import { connectionMonitor } from './features/offline/index.js';

connectionMonitor.on('offline', () => {
  composer.disable('Offline - messages queued');
});

connectionMonitor.on('online', () => {
  composer.enable();
  syncPendingMessages();
});
```

### Offline Queue
Messages sent while offline are:
1. Saved to IndexedDB
2. Shown with "pending" status
3. Auto-sent when connection restored
4. Retried with exponential backoff

### Service Worker
Caches:
- Static assets (JS, CSS, icons)
- Recent messages
- Session list

Enables:
- App launch while offline
- Viewing cached conversations
- Queueing new messages

---

## 8. PWA Features

### Install Prompt
**Trigger**: Manual (Command Palette) or automatic on eligible browsers

**Custom UI**: Branded install card with benefits

**Deferred**: Chrome's mini-infobar suppressed

**Code**:
```javascript
import { pwaInstall } from './features/pwa/index.js';

// Show custom prompt
pwaInstall.showPrompt();

// Check if installed
if (pwaInstall.isInstalled) {
  // Hide install UI
}

// Listen for install
pwaInstall.on('installed', () => {
  toast.success('App installed!');
});
```

### Share Target
Receive content from other apps on mobile.

**Supported**:
- Shared URLs → New message with link
- Shared text → New message
- Shared images → Attachment upload

**Usage**: Use Android/iOS share sheet → Select "Alfred"

### Shortcuts
Long-press app icon for quick actions:
- New Chat
- Resume Last Session
- View Notifications

### Theme Auto-Detection
Follows system preference:
```javascript
const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
prefersDark.addEventListener('change', (e) => {
  theme.set(e.matches ? 'dark' : 'light');
});
```

---

## 9. Animations

### Message Animations
- New messages slide in from bottom
- Streaming text reveals character by character
- Code blocks expand with spring physics

### Skeleton Loaders
Shown while:
- Loading session list
- Waiting for first response
- Fetching search results

### Typing Indicator
Animated dots when assistant is generating:
```
● ● ●
```

### Tool Call Progress
Visual feedback for running tools:
- Progress bars
- Status badges
- Expandable details

### Reduced Motion
Respects `prefers-reduced-motion`:
```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 10. Search & Navigation

### Quick Session Switcher
**Trigger**: Command Palette → "Search Sessions" or `Ctrl/Cmd + P`

**Features**:
- Fuzzy find by title or content
- Recent sessions at top
- Arrow keys to navigate
- Enter to switch

### Full Search
**Trigger**: `Ctrl/Cmd + Shift + F`

Searches across:
- All session titles
- Message content
- @ mentions
- Tool outputs

Results show:
- Session name
- Matching snippet
- Timestamp
- Relevance score

### @ Mentions
Type `@` in composer to:
- Reference previous messages
- Link to memories
- Tag tool outputs

Format: `@message-123`, `@memory-456`

---

## Quick Reference

### Mobile Gestures Cheat Sheet
| Gesture | Action |
|---------|--------|
| Pull down | Refresh/reconnect |
| Swipe right on message | Reply |
| Long press | Context menu |
| Double tap | Like/reaction |
| Pinch image | Zoom |
| Two-finger swipe down | Command palette |
| Swipe up composer | Fullscreen compose |

### Keyboard Shortcuts Cheat Sheet
| Shortcut | Action |
|----------|--------|
| `Ctrl/Cmd + K` | Command palette |
| `Ctrl/Cmd + N` | New session |
| `Ctrl/Cmd + F` | Search |
| `Ctrl/Cmd + /` | Help |
| `Ctrl/Cmd + C` | Cancel stream |
| `Alt + 1-9` | Jump to session |
| `Esc` | Close/Back |

---

## Testing Features

Run the built-in tests:
```bash
# Command palette
open tests/webui/command-palette-demo.html

# Mobile gestures
open tests/webui/test-gestures.html

# Keyboard shortcuts
open tests/webui/test-keyboard.html
```

Or in browser console:
```javascript
// Test notifications
window._testToast?.();

// Test offline
window._simulateOffline?.();

// Test install prompt
window._testInstallPrompt?.();
```
