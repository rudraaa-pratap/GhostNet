# GhostNet

**Real-Time Visual Network Activity Monitor** — a local-first application that shows which
applications on your computer are communicating with which internet services, in real time,
through an interactive animated network graph.

```
Chrome  ────────────────→  google.com
VS Code ────────────────→  github.com
Spotify ────────────────→  scdn.co
```

> **Privacy:** GhostNet is local-first. Network activity stays on your machine and is
> never uploaded to any external service.

---

## Features

**Phase 1 — MVP**
- **Live Network Graph** — applications and domains as nodes, active connections as
  animated, flowing edges in a D3.js force-directed graph (zoom / pan / drag).
- **Process → Internet Mapping** — PID → process name → active sockets.
- **Real-Time Statistics** — download/upload speed, active connections, applications,
  domains, request counts (with sparklines).
- **Application List** — per-app connection counts and top domains.
- **Ghost Mode** — click an application (in the graph or list) to focus only its traffic.
- **Permission-aware** — runs unprivileged (own connections via `lsof`) or elevated
  (full system view via `psutil`); the UI shows which view you have.
- **Demo mode** — synthetic traffic so the dashboard can be shown without any real
  activity or elevated privileges.

**Phase 2 — Traffic intelligence**
- **Bandwidth** — system-wide speeds (psutil) plus **per-process and per-connection**
  rates sampled from macOS `nettop` (works unprivileged), shown in the app list,
  domain panel, and live over WebSocket.
- **Domain Grouping** — connections rolled up by registrable domain (eTLD+1) with
  coarse categories (Google, Ads, CDN, GitHub, …), ports, IPs, and bandwidth.
- **Request Timeline** — connection open/close events persisted to local SQLite
  (24h retention) and visualized as a stacked event strip (5m/15m/1h windows).
- **Traffic Chart** — download/upload speed over the last 5/15/30 minutes.
- **Search & Filtering** — free-text search (app, domain, IP, port) + protocol/status
  filters across graph, lists, and domain panel.

**Phase 3 — V3**
- **Connection Details** — click any connection for its PID, protocol, both endpoints,
  status, live rates, open/idle time and full connection id.
- **Activity Replay** — scrub back through 24h of persisted events (1h/6h/24h windows),
  play/pause at 1×–10×, and exit to live. Graph, lists, stats and timeline all follow
  the cursor.
- **Alerts** — first-seen application → destination pairs are baselined on first run
  (plus a 60s warm-up so restarts never re-fire), persisted locally, and surfaced as
  toasts plus a header badge.
- **Export** — one-click printable report (statistics, applications, domains, hourly
  activity, alerts) rendered in the browser and saved via *Print → Save as PDF*.
- **Domain categories** — category chips with counts filter the domain panel.

Planned: Linux/Windows sources behind the existing `ConnectionSource` interface,
category rules expansion.

---

## Architecture

GhostNet is three independent layers — **collection**, **serving**, **presentation** —
joined only by plain data structures, so the OS-specific code never touches the UI and
the UI never touches the OS.

```
                        ┌─────────────────────────────────────────────┐
                        │  COLLECTION          backend/app/monitor/  │
                        │                                             │
   macOS kernel ───────►│  ConnectionSource (base.py)                 │
   psutil / lsof        │    ├─ macos.py   elevated / unprivileged    │
   nettop               │    └─ demo.py    synthetic traffic          │
                        │              │  RawConnection               │
                        │              ▼                              │
                        │  NetworkCollector  poll → diff → enrich     │
                        │    ├─ DnsResolver       async reverse DNS   │
                        │    ├─ aggregation       eTLD+1 + categories │
                        │    ├─ BandwidthSampler  nettop / demo rates │
                        │    └─ AlertWatcher      first-seen pairs    │
                        │              │                              │
                        │              ▼                              │
                        │  EventStore (SQLite)                        │
                        │    events · seen · alerts · meta            │
                        └──────────────┬──────────────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────────────┐
                        │  SERVING          backend/app/             │
                        │                                             │
                        │  FastAPI REST  /api/*                       │
                        │  WebSocket     /ws      broadcast per poll  │
                        │  ConnectionManager      client registry     │
                        └──────────────┬──────────────────────────────┘
                                       │  HTTP + WS  (Vite dev proxy)
                        ┌──────────────▼──────────────────────────────┐
                        │  PRESENTATION     frontend/src/            │
                        │                                             │
                        │  useNetworkSocket  live state store         │
                        │        │                                    │
                        │        ├── NetworkGraph    D3 force graph   │
                        │        ├── ProcessList / ConnectionList     │
                        │        ├── DomainPanel / ConnectionDetail   │
                        │        ├── TrafficChart / Timeline          │
                        │        ├── ReplayBar  + utils/replay        │
                        │        └── AlertToasts / StatsCard          │
                        └─────────────────────────────────────────────┘
```

### Data flow

1. The OS reports a socket: `PID 4832 → 142.250.196.110:443`
2. `ConnectionSource.snapshot()` returns `RawConnection` records (blocking — run in a
   thread by the collector)
3. `NetworkCollector` diffs against the previous snapshot to detect **open** / **update**
   / **close**, and maps PID → process name
4. Enrichment attaches reverse-DNS hostname, registrable domain (eTLD+1) and category
5. Open/close events are written to SQLite; `AlertWatcher` checks for unseen
   app → destination pairs
6. Every poll broadcasts `conn_open` / `conn_close` / `stats` / `bandwidth` / `dns` /
   `alert` over the WebSocket; REST serves the same data on demand
7. `useNetworkSocket` merges events into a live `Map`, and D3 re-renders the graph

### Design decisions

- **Connection-level, not packet-level.** Packet capture needs extra OS permissions and
  platform-specific code; relationships like `Chrome → TCP → google.com:443` are enough
  for the product goal.
- **`ConnectionSource` abstraction.** All OS-specific code sits behind one interface, so
  `linux.py` / `windows.py` can be added without touching the collector, API or UI.
- **`nettop` for bandwidth.** macOS exposes no per-process I/O counters through psutil,
  so per-process/per-connection rates come from `nettop` (works unprivileged); global
  rates come from `psutil.net_io_counters()`.
- **Everything stays on disk you own.** One SQLite file, no telemetry, no cloud.

---

## Tech Stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| System monitoring | Python ≥ 3.11 + psutil | Processes, PIDs, sockets, global I/O counters |
| macOS extras | `lsof`, `nettop` | Unprivileged socket enumeration; per-process bandwidth |
| Backend | FastAPI + uvicorn | REST API and application server |
| Real-time | WebSockets | Push live connection events to the browser |
| Persistence | SQLite (stdlib) | 24h event history, alert baseline, alert log |
| Frontend | React 19 + Vite 8 | Dashboard and interactive UI |
| Styling | Tailwind CSS v4 | Utility-first styling via `@tailwindcss/vite` |
| Visualization | D3.js v7 | Force-directed graph, sparklines, timeline strips |
| Linting | Ruff (Python), Oxlint (JS) | Style and correctness checks |
| Testing | pytest + pytest-asyncio, httpx TestClient | Unit + API/WebSocket integration tests |

> `framer-motion` is listed in `package.json` but not yet used — animations are CSS
> keyframes (`index.css`) plus D3 transitions.

---

## Project Structure

```
ghostnet/
├── README.md                    # this file
├── .gitignore
├── GhostNet_Project_Explanation.pdf   # design brief / roadmap
│
├── backend/
│   ├── pyproject.toml           # deps, ruff + pytest config
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, WS endpoint, CLI (--demo)
│   │   ├── api/
│   │   │   └── routes.py        # all REST endpoints
│   │   ├── monitor/
│   │   │   ├── base.py          # RawConnection / Connection / ConnectionSource
│   │   │   ├── macos.py         # psutil (elevated) / lsof (unprivileged) + detect_source()
│   │   │   ├── bandwidth.py     # per-process & per-connection rates via nettop
│   │   │   ├── demo.py          # synthetic traffic source
│   │   │   └── collector.py     # poll → diff → enrich → persist → emit loop
│   │   ├── services/
│   │   │   ├── dns.py           # async reverse DNS with TTL cache
│   │   │   ├── aggregation.py   # eTLD+1 extraction, category rules, domain roll-ups
│   │   │   ├── history.py       # EventStore: events, seen, alerts, meta tables
│   │   │   └── alerts.py        # AlertWatcher: first-seen app → destination
│   │   └── websocket/
│   │       └── manager.py       # WebSocket connection registry + broadcast
│   ├── data/ghostnet.db         # local DB (gitignored, override with GHOSTNET_DB)
│   └── tests/                   # 55 tests: unit + API + WebSocket integration
│
└── frontend/
    ├── index.html
    ├── vite.config.js           # dev proxy: /api and /ws → 127.0.0.1:8000
    ├── package.json
    └── src/
        ├── main.jsx
        ├── App.jsx
        ├── index.css            # tailwind import + animation keyframes
        ├── pages/
        │   └── Dashboard.jsx    # composition, ghost mode, replay, export
        ├── components/
        │   ├── NetworkGraph.jsx     # D3 force-directed graph (zoom/pan/drag)
        │   ├── ProcessList.jsx      # per-application rows
        │   ├── ConnectionList.jsx   # per-socket rows
        │   ├── ConnectionDetail.jsx # full connection drill-down
        │   ├── DomainPanel.jsx      # domain groups + category chips
        │   ├── TrafficChart.jsx     # download/upload sparkline chart
        │   ├── Timeline.jsx         # stacked open/close event buckets
        │   ├── ReplayBar.jsx        # time scrubber, play/pause, speed
        │   ├── FilterBar.jsx        # search + protocol/status filters
        │   ├── StatsCard.jsx        # stat tile with sparkline
        │   ├── AlertToasts.jsx      # first-seen destination toasts
        │   └── PermissionBanner.jsx # limited-view warning
        ├── hooks/
        │   ├── useNetworkSocket.js  # WebSocket state store + hydration
        │   └── useNow.js            # ticking clock for live timestamps
        └── utils/
            ├── format.js            # bytes / rates / durations / clocks
            ├── colors.js            # app, category and status palettes
            ├── replay.js            # fold events into historical state
            └── report.js            # printable HTML report builder
```

---

## API Reference

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/api/health` | Liveness probe |
| GET | `/api/status` | Source, elevation, demo flag, uptime, poll interval |
| GET | `/api/connections` | Live sockets; `q`, `protocol`, `status`, `app`, `limit` |
| GET | `/api/processes` | Per-application roll-up with live rates |
| GET | `/api/domains` | Per-eTLD+1 roll-up with category, ports, IPs, rates |
| GET | `/api/stats` | Current stats + recent speed history |
| GET | `/api/timeline` | Open/close events; `since`, `until`, `kind`, `limit` |
| GET | `/api/alerts` | Recent first-seen app → destination alerts |
| GET | `/api/report` | Snapshot for the printable export; `window` |
| WS | `/ws` | Server push (see events below) |

**WebSocket events** — `snapshot` (on connect), `conn_open`, `conn_close`,
`conn_update`, `stats`, `bandwidth`, `dns`, `alert`.

---

## Getting Started

### Backend

```bash
cd backend
uv sync
uv run python -m app.main            # normal (own connections only)
uv run python -m app.main --demo     # synthetic demo traffic
sudo uv run python -m app.main       # full system-wide view (macOS)
```

### Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173 (proxies /api + /ws)
```

### Checks

```bash
cd backend && uv run ruff check app tests && uv run pytest
cd frontend && npm run lint && npm run build
```

---

## Notes

- **macOS permissions:** without `sudo`, macOS only exposes the current user's sockets.
  GhostNet detects this and shows a "limited view" banner in the UI.
- **Alerts baseline** — the first run records what's already connected without firing;
  a 60s warm-up window then absorbs startup churn, so restarting never re-alerts.
- **Storage** — one SQLite file at `backend/data/ghostnet.db` (override with
  `GHOSTNET_DB`). Events prune after 24 hours; `seen` and `alerts` persist indefinitely.
- **Replay fidelity** — history stores who talked to whom and when, not byte counts, so
  replay reconstructs the graph and counts but not per-connection rates.
- **Export** — the report opens in a new tab and calls `window.print()`; choose
  *Save as PDF* in the print dialog. Popups must be allowed for the site.
