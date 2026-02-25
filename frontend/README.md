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

### Environment Setup

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Edit `.env` to configure your backend API endpoint:

```env
VITE_API_BASE=http://localhost:8000
VITE_APP_NAME=trends_and_insights_agent
```

### Development

Start the development server:

```bash
npm run dev
```

The app will be available at `http://localhost:5173`.

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

Run tests:

```bash
npm test
```

Run tests with UI:

```bash
npm run test:ui
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

- The app proxies `/apps` and `/api` requests to the backend (port 8000)
- Dark mode is the default theme
- All components use Tailwind CSS with a zinc/slate palette and blue accents
- Type-only imports are required due to `verbatimModuleSyntax` in tsconfig
