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

Planned: activity replay, domain categories UI polish, PDF report export.

## Tech Stack

| Layer | Technology |
| --- | --- |
| System monitoring | Python + psutil (+ `lsof` fallback on macOS) |
| Backend | FastAPI |
| Real-time | WebSockets |
| Frontend | React (Vite) |
| Styling | Tailwind CSS |
| Visualization | D3.js |

## Project Structure

```
ghostnet/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, WS endpoint, CLI (--demo)
│   │   ├── api/routes.py      # status, connections, processes, stats, domains, timeline
│   │   ├── monitor/
│   │   │   ├── base.py        # models + ConnectionSource interface
│   │   │   ├── macos.py       # psutil (elevated) / lsof (non-elevated) sources
│   │   │   ├── bandwidth.py   # per-process/per-connection rates via nettop
│   │   │   ├── demo.py        # synthetic traffic source
│   │   │   └── collector.py   # poll → diff → enrich → emit loop
│   │   ├── services/
│   │   │   ├── dns.py         # async reverse DNS w/ TTL cache
│   │   │   ├── aggregation.py # registrable domains + categories + roll-ups
│   │   │   └── history.py     # SQLite event store (timeline, 24h retention)
│   │   └── websocket/manager.py
│   ├── data/ghostnet.db       # local timeline DB (gitignored)
│   └── tests/
├── frontend/
│   └── src/
│       ├── components/        # NetworkGraph, ProcessList, DomainPanel, Timeline,
│       │                      # TrafficChart, FilterBar, StatsCard, …
│       ├── pages/Dashboard.jsx
│       └── hooks/             # useNetworkSocket, useNow
├── README.md
└── .gitignore
```

## Getting Started

### Backend

```bash
cd backend
uv sync
uv run python -m app.main            # normal (own connections only)
uv run python -m app.main --demo     # synthetic demo traffic
sudo uv run python -m app.main       # full system-wide view (macOS)
```

API: `http://127.0.0.1:8000/api/status` · WebSocket: `ws://127.0.0.1:8000/ws`

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

## Notes

- **macOS permissions:** without `sudo`, macOS only exposes the current user's sockets.
  GhostNet detects this and shows a "limited view" banner in the UI.
- Connection-level monitoring only (no packet capture) by design — see the technical
  limitation notes in the project document.
- Per-connection/per-process bandwidth comes from `nettop` because macOS has no
  `psutil` process I/O counters; global speeds come from `netio` counters.
- Timeline history is stored locally in `backend/data/ghostnet.db` (override with
  `GHOSTNET_DB`) and pruned after 24 hours.
