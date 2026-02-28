# Marketing Intelligence Frontend

React + TypeScript frontend for the multi-agent marketing intelligence system.

## Tech Stack

- **React 19** with TypeScript
- **Vite** for build tooling
- **React Router** for navigation
- **TanStack Query** for server state management
- **Zustand** for client state (if needed)
- **Tailwind CSS v4** for styling
- **Vitest** for testing

## Getting Started

### Install Dependencies

```bash
npm install
```

### Running Locally (Recommended)

The easiest way to run the full stack is from the **project root**:

```bash
cd ..          # navigate to zghost root
./run_local.sh
```

This starts all backend services (API server, voice, memory) and the frontend dev server together. Open [http://localhost:5173](http://localhost:5173).

See the [root README](../README.md) for full setup instructions.

### Running the Frontend Only

If the backend services are already running (or you're pointing at a Cloud Run deployment):

```bash
npm run dev
```

The app will be available at [http://localhost:5173](http://localhost:5173).

### Services & Ports

The frontend Vite dev server proxies all API requests to the backend automatically:

| Route Pattern | Proxied To | Service |
|---------------|-----------|---------|
| `/api/memories/*` | `localhost:8082` | Memory Bank API |
| `/api/*` | `localhost:8000` | API Server (ADK runner, sessions, SSE) |
| `/ws/*` | `localhost:8081` | Voice WebSocket (Gemini Live) |

This means you only need to open **port 5173** in your browser — all backend communication flows through Vite's proxy.

To proxy to a Cloud Run deployment instead of local services:

```bash
VITE_CLOUD_BACKEND=true npm run dev
```

### Port Forwarding (Remote Development)

If running on a remote machine (VM, Cloud Workstation, SSH):

**VS Code Remote** — Open the **Ports** panel and forward port `5173`. VS Code usually auto-detects this. Since Vite proxies all backend routes, forwarding port 5173 alone is sufficient.

**SSH tunnel**:

```bash
ssh -L 5173:localhost:5173 your-remote-host
```

Then open `http://localhost:5173` in your local browser.

### Environment Setup

Create a `.env` file for production builds:

```env
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=trends_and_insights_agent
```

For local development, no `.env` is required — the Vite proxy handles routing.

### Build for Production

```bash
npm run build
```

Built files will be in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

### Testing

Run unit tests (Vitest):

```bash
npm test
```

Run unit tests with UI:

```bash
npm run test:ui
```

Run Playwright E2E tests (requires all services running via `./run_local.sh`):

```bash
npx playwright test              # headless
npx playwright test --headed     # watch in browser
npx playwright show-report       # view HTML report
```

## Project Structure

```
src/
├── app/                    # Application setup
│   ├── App.tsx             # Root component
│   ├── providers.tsx       # Context providers
│   └── routes.tsx          # Route configuration
├── components/             # Reusable components
│   ├── layout/             # Layout components (Header, Sidebar, AppShell)
│   └── ui/                 # UI primitives (Button, Card, etc.)
├── features/               # Feature modules
│   ├── trends/             # Trend configuration
│   ├── orchestration/      # Agent pipeline dashboard
│   ├── rating/             # Rubric configuration & rating
│   ├── studio/             # AV studio display
│   └── narrative/          # Interactive narrative
├── services/               # API clients
│   ├── api.ts              # REST API client
│   ├── streaming.ts        # SSE streaming client
│   ├── session.ts          # Session management
│   └── agents.ts           # Agent dispatch service
├── hooks/                  # Custom React hooks
├── types/                  # TypeScript type definitions
├── lib/                    # Utilities
└── test/                   # Test setup

```

## Features

### Implemented

- Modern React 19 + TypeScript setup
- Tailwind CSS v4 with dark mode theme
- Responsive layout with collapsible sidebar
- API client with proxy configuration
- TypeScript types matching backend Pydantic models
- SSE streaming hook for real-time agent events
- Session management
- Component library (Button, Card, Badge, Input, Slider, Tabs, Modal, Spinner)

### To Be Built (by other team members)

- Trend configuration UI (Task #3)
- Agent orchestration dashboard (Task #4)
- Rating rubric interface (Task #5)
- AV studio display (Task #6)
- Interactive narrative visualization (Task #6)
- Comprehensive test suite (Task #7)

## Development Notes

- Vite proxies `/api/memories/*` → port 8082, `/api/*` → port 8000, `/ws/*` → port 8081 (see `vite.config.ts`)
- `/api/memories` proxy rule must come **before** `/api` in the config, or memory requests route to the wrong service
- Dark mode is the default theme
- All components use Tailwind CSS with a zinc/slate palette and blue accents
- Type-only imports are required due to `verbatimModuleSyntax` in tsconfig
- The API server takes ~2-3 minutes to finish loading `root_agent` — the UI loads instantly but pipelines won't run until the backend is ready
