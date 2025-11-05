# Frontend Structure & UI Behaviour

The frontend lives in the `frontend/` directory and is a Vite + React 18 single
page application. It aims to stay thin and delegate as much logic as possible to
the backend.

## Stack

- React 18 with functional components and hooks.
- TypeScript for strong typing of API responses (see `src/types/api.ts`).
- React Router (configured in `src/App.tsx`).
- Leaflet for the map preview (`MapPreview.tsx`).
- Simple CSS utility sheet (`src/styles.css`) with a handful of grid/layout
  helpers. No component library is used.

## Directory Layout

```
src/
├── App.tsx             – Router definitions / layout wrapper
├── main.tsx            – Application bootstrap
├── hooks/useApi.ts     – Fetch helper that injects admin token
├── components/         – Reusable widgets (DataTable, StatusBadge, MapPreview ...)
├── pages/              – Route-level components (Databases, Imports, Jobs ...)
├── styles.css          – Lightweight global styles
└── types/api.ts        – TypeScript interfaces mirroring backend schemas
```

## `useApi` Hook

`hooks/useApi.ts` centralises API calls:

- Reads `VITE_API_BASE_URL` and rewrites docker-only hostnames to match the
  browser's origin (handles `api` → `localhost`).
- Automatically attaches the admin token via `X-API-KEY` when `VITE_ADMIN_TOKEN`
  is set.
- Provides `get`, `post`, and `del` helpers returning typed promises.
- Normalises JSON responses and throws JavaScript `Error`s on non-2xx results.

## Pages

- **DatabasesPage** – Lists managed databases, allows creation/deletion, shows
  size stats, and contains the Leaflet preview. Clicking a database name fetches
  (or reuses cached) bounds and draws a rectangle on the map.
- **ImportsPage** – Kick-starts import jobs, tracks running jobs, filters job
  history.
- **JobsPage** – Displays jobs with status chips, inline retry button (`↺`), and
  a log viewer component.
- **ReplicationPage / SettingsPage** – Configuration forms and read-only env info.

Each page is responsible only for UI composition; API interactions should go
through `useApi` to ensure consistent error handling.

## Map Preview

`components/MapPreview.tsx` wraps Leaflet and exposes an imperative handle via
`forwardRef`:

```ts
type MapPreviewHandle = {
  showBounds: (bounds: [[number, number], [number, number]]) => void;
};
```

Calling `showBounds` fits the map to the provided bounding box and renders a
semi-transparent rectangle. The map initially centres on Monaco to indicate the
UI is active even before data is loaded. The Databases page keeps a ref to this
handle and invokes it when bounds are loaded.

## Styling

Global styles live in a single CSS file. Key patterns:

- `.grid`, `.grid.two`, `.grid.three` control layout; media queries collapse the
  grid below 1024px to keep panels stacked vertically on narrow screens.
- Buttons use `.btn`; smaller variants (`btn-small-secondary`, `btn-small-danger`)
  are used for inline actions.
- Tables are wrapped in `.table-wrapper` to allow horizontal scrolling when the
  viewport is tight.

Consider migrating to CSS Modules or a design system if the UI grows
significantly; for now, the CSS sheet remains intentionally small and explicit.

## Icons & Accessibility

- Action buttons (Retry, Delete) use simple glyphs (`↺`, `×`) with accessible
  `title` and `aria-label` attributes so screen readers have context.
- Table actions are pure buttons styled as links to ensure keyboard navigation
  works out of the box.

## Testing & Development

- `npm run dev` starts Vite (hot module reload on port 5173).
- `npm run build` performs a type check (`tsc`) followed by a production build.
- `npm run lint` executes ESLint with the configured TypeScript rules.

Because the API requires the admin token for mutations, set
`VITE_ADMIN_TOKEN=change-me` (or your chosen token) in `.env` so the frontend can
perform write operations while developing.

If the Postgres service is exposed on a port other than `5433`, also set
`VITE_POSTGRES_PORT=<port>` so the Databases page shows accurate connection
strings for copy/paste into tools like QGIS.

Refer to `docs/architecture.md` for the bigger picture and to
`docs/bounding-boxes.md` for details on how the map derives the bounds it
renders.
