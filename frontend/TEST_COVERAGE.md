# Frontend Test Suite Documentation

## Overview

This document describes the comprehensive test suite for the marketing intelligence frontend application. The test suite covers all major components, services, hooks, and features with 122 tests across 13 test files.

## Test Results

**Total Tests: 122**
**Passed: 122 (100%)**
**Failed: 0**

## Test Infrastructure

### Configuration

- **Test Runner**: Vitest 4.0.18
- **Testing Library**: @testing-library/react 16.3.2
- **User Events**: @testing-library/user-event 14.6.1
- **Mocking**: MSW (Mock Service Worker) 2.12.10
- **Coverage**: @vitest/coverage-v8 4.0.18

### Setup Files

- `vitest.config.ts` - Vitest configuration with coverage settings
- `src/test/setup.ts` - Global test setup with browser API mocks
- `src/test/test-utils.tsx` - Custom render function with providers
- `src/test/mocks/fixtures.ts` - Mock data for all entity types
- `src/test/mocks/handlers.ts` - MSW request handlers for API mocking
- `src/test/mocks/streaming.ts` - Mock EventSource for SSE testing

## Test Coverage by Module

### 1. Services (3 test files, 23 tests)

#### `src/test/services/api.test.ts` (8 tests)
Tests for the API client covering:
- Session creation and retrieval
- Session state updates
- Message sending
- Parallel agent dispatch
- Orchestration status fetching
- Auto-trend selection
- Error handling

#### `src/test/services/streaming.test.ts` (8 tests)
Tests for SSE streaming service:
- Agent event parsing (snake_case and camelCase)
- Event stream connection and parsing
- Error handling
- Connection cleanup
- Malformed JSON handling

#### `src/test/services/session.test.ts` (7 tests)
Tests for session management:
- Session creation and storage
- Session retrieval by ID
- Current session tracking
- Session clearing

### 2. Hooks (2 test files, 18 tests)

#### `src/test/hooks/useStreaming.test.ts` (9 tests)
Tests for streaming hook:
- Initial state
- Connection establishment
- Event accumulation
- Connection status reporting
- Event clearing
- URL changes
- Disconnection
- Cleanup on unmount
- Error handling

#### `src/test/hooks/useSession.test.ts` (9 tests)
Tests for session hook:
- Initial state
- Session creation with loading states
- Session loading by ID
- Session clearing
- Error handling
- Error state clearing

### 3. UI Components (6 test files, 60 tests)

#### `src/test/components/Button.test.tsx` (13 tests)
- Rendering with children
- Click event handling
- Disabled state
- 4 variants (primary, secondary, ghost, danger)
- 3 sizes (sm, md, lg)
- Custom className
- Ref forwarding

#### `src/test/components/Card.test.tsx` (10 tests)
- Card rendering and styling
- CardHeader component
- CardTitle component (h3 heading)
- CardContent component
- Complete card composition

#### `src/test/components/Badge.test.tsx` (9 tests)
- Badge rendering
- 5 variants (default, success, warning, error, info)
- Color verification
- Custom className
- Base styling
- Ref forwarding

#### `src/test/components/Modal.test.tsx` (10 tests)
- Conditional rendering based on isOpen
- Title rendering
- Overlay click to close
- Body scroll prevention
- Scroll restoration on close/unmount
- Custom className
- Children rendering

#### `src/test/components/Input.test.tsx` (11 tests)
- Default type text
- Specified types
- Value changes
- Placeholder text
- Disabled state and styling
- Value display
- Custom className
- Default styling
- Ref forwarding
- Controlled input support

#### `src/test/components/Tabs.test.tsx` (6 tests)
- Default value rendering
- Tab switching on click
- Active styling
- Multiple tabs
- Error when used outside context

### 4. Features (1 test file, 16 tests)

#### `src/test/features/TrendCard.test.tsx` (16 tests)

**SearchTrendCard (8 tests)**:
- Search trend data rendering
- Related queries display
- Traffic badge
- Selection toggle
- Selected styling
- Article expansion/collapse
- Card click toggles selection

**YTTrendCard (8 tests)**:
- YouTube trend data rendering
- Rank badge
- Selection toggle
- Selected styling
- Description expansion
- Thumbnail rendering
- YouTube link
- Published time display

### 5. Layout (1 test file, 5 tests)

#### `src/test/layout/AppShell.test.tsx` (5 tests)
- Header component presence
- Sidebar component presence
- Main content area
- Layout structure
- Scrollable main content

## Test Patterns and Best Practices

### 1. Rendering Pattern
```typescript
import { render, screen } from '../test-utils';

render(<Component />);
expect(screen.getByText('text')).toBeInTheDocument();
```

### 2. User Interactions
```typescript
import userEvent from '@testing-library/user-event';

const user = userEvent.setup();
await user.click(element);
await user.type(input, 'text');
```

### 3. API Mocking with MSW
```typescript
import { setupServer } from 'msw/node';
import { handlers } from '../mocks/handlers';

const server = setupServer(...handlers);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

### 4. Hook Testing
```typescript
import { renderHook, waitFor } from '@testing-library/react';

const { result } = renderHook(() => useCustomHook());
await waitFor(() => {
  expect(result.current.value).toBe(expected);
});
```

### 5. Component Variants
```typescript
it.each(['primary', 'secondary', 'ghost', 'danger'])(
  'renders %s variant',
  (variant) => {
    render(<Button variant={variant}>Button</Button>);
    // assertions
  }
);
```

## Coverage Goals

The test suite aims for:
- **Statements**: > 80%
- **Branches**: > 75%
- **Functions**: > 80%
- **Lines**: > 80%

Run coverage report:
```bash
npm run test:coverage
```

## Running Tests

```bash
# Run tests in watch mode
npm test

# Run tests once
npm run test:run

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Future Test Coverage

The following areas are ready for expansion:

### Features
- `features/orchestration/` - Pipeline DAG visualization and event stream
- `features/rating/` - Rubric editor and rater interface
- `features/studio/` - AV timeline, clip library, commercial player
- `features/narrative/` - Chat interface, storyboard, narrative arc

### Integration Tests
- End-to-end user workflows
- Multi-component interactions
- State management flows

### Performance Tests
- Large data set rendering
- Streaming performance
- Memory leak detection

## Mock Data

All mock data is centralized in `src/test/mocks/fixtures.ts`:
- Sessions
- Search Trends
- YouTube Trends
- Agent Events
- Rubrics and Ratings
- Artifacts (Image, Video, Commercial)

## Common Issues and Solutions

### React Act Warnings
The test suite may show React act() warnings for async state updates. These are expected when testing hooks with async operations and do not indicate test failures.

### MSW Request Matching
Ensure API endpoints in handlers match those used in services exactly, including path parameters.

### EventSource Mocking
The global EventSource is mocked in setup.ts. Additional mock behavior is available in `src/test/mocks/streaming.ts`.

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Pre-deployment checks

## Maintenance

- Update fixtures when types change
- Add new handlers when API endpoints are added
- Expand coverage for new features
- Keep mocks synchronized with real APIs
