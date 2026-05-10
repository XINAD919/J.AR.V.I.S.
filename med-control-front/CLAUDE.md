# MedControl Frontend

Next.js 16.2.4 frontend for the MedAI medical reminder assistant. All UI text is in Spanish.

## Dev commands

```bash
npm run dev      # dev server at http://localhost:3000
npm run build    # production build
npm run lint     # ESLint
```

Run from `front/med-control/`. Requires the FastAPI backend running at `http://localhost:8000`.

## Stack

- **Next.js 16.2.4** — App Router, no Pages Router
- **React 19.2.4** — use `'use client'` for any component that needs hooks or browser APIs
- **Tailwind CSS v4** — `@import "tailwindcss"` in globals.css; no tailwind.config.js
- **TypeScript** — strict mode
- **lucide-react** — icons
- **react-markdown** — Markdown rendering in chat

## Next.js 16 breaking changes to know

- `params` and `searchParams` in page/layout components are async — must be awaited
- Middleware file is `middleware.ts` (not `proxy.ts`)
- ESM-only packages (like react-markdown v10) work natively — no `transpilePackages` needed

## Project structure

```
app/
├── lib/
│   ├── types.ts     # TypeScript interfaces (Reminder, Channel, ChatMessage)
│   └── api.ts       # All API calls + WebSocket helper
├── components/
│   ├── SideBar.tsx  # Sidebar with navigation
│   └── NavItem.tsx  # Active-aware nav link
├── page.tsx         # Dashboard — today's reminders + upcoming
├── chat/page.tsx    # WebSocket chat with AI agent
├── calendar/page.tsx# Agenda cronológica de recordatorios
├── settings/page.tsx# Gestión de canales de notificación
└── family/page.tsx  # Placeholder "próximamente"
```

## Backend integration

- API base: `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`)
- WebSocket: `NEXT_PUBLIC_WS_URL` (default `ws://localhost:8000`)
- Hardcoded in `app/lib/api.ts` (no auth yet):
  - `USER_ID = "11111111-1111-1111-1111-111111111111"`
  - `SESSION_ID = "default"`

Key endpoints:
- `GET /api/users/{USER_ID}/reminders?status=&date=&medication=`
- `GET /api/users/{USER_ID}/channels?verified_only=false`
- `POST /api/users/{USER_ID}/channels`
- `DELETE /api/users/{USER_ID}/channels/{channel}`
- `PATCH /api/users/{USER_ID}/channels/{channel}/toggle-reminders`
- `WS /ws/chat?session_id=default`

## WebSocket behavior

One connection per message — backend closes the connection after each response. No `[DONE]` sentinel.

```typescript
// Pattern used in chat/page.tsx
connectChatSocket(message, onToken, onDone, onError)
// ontoken: accumulate tokens
// onclose fires onDone — that's when streaming is complete
```

## Tailwind v4 gotcha

Never build class names dynamically via interpolation — Tailwind v4 won't detect them:

```typescript
// WRONG
className={`bg-${color}-100`}

// CORRECT — use a full-class lookup object
const STATUS_CLASSES = {
  scheduled: 'bg-blue-100 text-blue-600',
  completed: 'bg-green-100 text-green-700',
  // ...
}
```

## Markdown in chat

Chat messages use `.md-prose` CSS class (defined in `globals.css`) for prose styling without `@tailwindcss/typography`.
