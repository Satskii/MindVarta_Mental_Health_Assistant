# MindVarta — Frontend

Student Mental Health Support · Voice Chatbot UI

---

## Directory Structure

```
frontend-MindVarta/
├── index.html                        # HTML entry point (loads fonts, mounts #root)
├── vite.config.js                    # Vite + React plugin config
├── package.json                      # Dependencies & scripts
│
├── public/
│   └── favicon.svg                   # App favicon
│
└── src/
    ├── main.jsx                      # ReactDOM.createRoot entry
    ├── App.jsx                       # BrowserRouter + Routes (/ and /chat)
    │
    ├── pages/
    │   ├── LandingPage.jsx           # Route: "/" — re-exports landing component
    │   └── ChatPage.jsx              # Route: "/chat" — assembles chat layout
    │
    ├── components/
    │   ├── landing/
    │   │   └── LandingPage.jsx       # Hero section, navbar, feature cards
    │   │
    │   └── chat/
    │       ├── Sidebar.jsx           # Collapsible sidebar: new chat, history, nav
    │       ├── ChatHeader.jsx        # Top bar: sidebar toggle, language picker, icons
    │       ├── MessageList.jsx       # Scrollable message thread + typing indicator
    │       ├── ChatInput.jsx         # Textarea + mic button + send button
    │       └── SettingsModal.jsx     # Full settings overlay (theme, voice, privacy)
    │
    ├── context/
    │   ├── ThemeContext.jsx          # dark/light theme state + localStorage persist
    │   └── ChatContext.jsx           # Conversation list, active chat, message state
    │
    ├── hooks/
    │   ├── useVoice.js               # MediaRecorder wrapper — wire to backend STT
    │   └── useAutoResize.js          # Textarea auto-height hook
    │
    └── styles/
        ├── global.css                # CSS variables (dark+light), resets, animations
        ├── landing.css               # Landing page: navbar, hero, orbs, feature cards
        ├── chat.css                  # Chat layout: sidebar, header, messages, input
        └── settings.css              # Settings modal, toggles, theme switcher
```

---

## Getting Started

```bash
# 1. Install dependencies
npm install

# 2. Start dev server
npm run dev

# 3. Open in browser
# → http://localhost:5173
```

---

## Pages

| Route   | Component              | Description                          |
|---------|------------------------|--------------------------------------|
| `/`     | `LandingPage.jsx`      | Hero, CTA buttons, feature cards     |
| `/chat` | `ChatPage.jsx`         | Full chat UI with sidebar            |

---

## Theming

All colors are CSS custom properties defined in `global.css`.  
Toggle dark/light via the ☀️/🌙 button in the navbar or sidebar.  
Theme persists to `localStorage` under the key `MindVarta-theme`.

---

## Backend Integration Points

When you're ready to connect your backend, look for these hooks:

### 1. Chat Response — `ChatPage.jsx`
```jsx
// Replace the setTimeout mock with your API call:
const response = await fetch('/api/chat', {
  method: 'POST',
  body: JSON.stringify({ message: text }),
})
const data = await response.json()
addMessage({ role: 'assistant', text: data.reply })
```

### 2. Voice Input — `src/hooks/useVoice.js`
```js
// In the mr.onstop handler, send the audio blob to your STT endpoint:
const formData = new FormData()
formData.append('audio', blob, 'recording.webm')
const res = await fetch('/api/transcribe', { method: 'POST', body: formData })
const { transcript } = await res.json()
onTranscript(transcript)
```

### 3. Text-to-Speech — `ChatInput.jsx` / `ChatPage.jsx`
```js
// After receiving a bot reply, call your TTS API and play the audio:
const audio = new Audio('/api/tts?text=' + encodeURIComponent(reply))
if (!muted) audio.play()
```

---

## Scripts

| Command         | Description              |
|-----------------|--------------------------|
| `npm run dev`   | Start Vite dev server    |
| `npm run build` | Production build         |
| `npm run preview` | Preview production build |

---

## Tech Stack

- **React 18** — UI
- **React Router v6** — client-side routing
- **Vite 5** — dev server & bundler
- **Custom CSS** — zero UI library dependencies, full CSS variables system
- **Google Fonts** — Sora (display) + DM Sans (body)
