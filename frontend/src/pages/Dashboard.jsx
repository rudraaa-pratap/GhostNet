import { useCallback, useEffect, useMemo, useState } from 'react'
import AlertToasts from '../components/AlertToasts'
import ConnectionDetail from '../components/ConnectionDetail'
import ConnectionList from '../components/ConnectionList'
import DomainPanel from '../components/DomainPanel'
import FilterBar from '../components/FilterBar'
import NetworkGraph from '../components/NetworkGraph'
import PermissionBanner from '../components/PermissionBanner'
import ProcessList from '../components/ProcessList'
import ReplayBar from '../components/ReplayBar'
import StatsCard from '../components/StatsCard'
import Timeline from '../components/Timeline'
import TrafficChart from '../components/TrafficChart'
import { useNetworkSocket } from '../hooks/useNetworkSocket'
import { useNow } from '../hooks/useNow'
import { formatBytes, formatClock, formatRate } from '../utils/format'
import { buildReportHtml } from '../utils/report'
import { reconstructState } from '../utils/replay'

const EMPTY_FILTERS = { q: '', protocol: '', status: '' }

function formatUptime(seconds) {
  if (!Number.isFinite(seconds)) return '—'
  const s = Math.floor(seconds % 60)
  const m = Math.floor((seconds / 60) % 60)
  const h = Math.floor(seconds / 3600)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function matches(c, filters) {
  const { q, protocol, status } = filters
  if (protocol && c.protocol !== protocol) return false
  if (status && c.status !== status) return false
  if (q) {
    const needle = q.toLowerCase()
    const haystack = `${c.process} ${c.domain} ${c.hostname} ${c.registrable} ${c.category} ${c.remote_ip} ${c.remote_port} ${c.protocol} ${c.status}`.toLowerCase()
    if (!haystack.includes(needle)) return false
  }
  return true
}

export default function Dashboard() {
  const {
    connectionList,
    stats,
    status,
    history,
    events,
    alerts,
    dismissAlert,
    dismissAllAlerts,
    bandwidth,
    connected,
  } = useNetworkSocket()
  const now = useNow(1000)
  const [selectedApp, setSelectedApp] = useState(null)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [rightTab, setRightTab] = useState('apps')
  const [detailConn, setDetailConn] = useState(null)
  const [exporting, setExporting] = useState(false)
  const [replay, setReplay] = useState(null)
  const [trafficWindow, setTrafficWindow] = useState(15)
  const [timelineWindow, setTimelineWindow] = useState(15)

  const loadReplayWindow = useCallback(async (windowSec) => {
    const end = Math.floor(Date.now() / 1000)
    const start = end - windowSec
    setReplay((prev) => ({
      start,
      end,
      at: prev && prev.at >= start && prev.at <= end ? prev.at : end,
      events: prev?.events ?? [],
      playing: false,
      speed: prev?.speed ?? 1,
      window: windowSec,
      loading: true,
    }))
    try {
      const res = await fetch(`/api/timeline?since=${start}&limit=20000`)
      const data = res.ok ? await res.json() : { events: [] }
      setReplay((prev) =>
        prev && prev.window === windowSec
          ? { ...prev, events: data.events || [], loading: false }
          : prev,
      )
    } catch {
      setReplay((prev) => (prev ? { ...prev, loading: false } : prev))
    }
  }, [])

  const exitReplay = useCallback(() => setReplay(null), [])

  const togglePlay = useCallback(() => {
    setReplay((prev) => {
      if (!prev) return prev
      if (prev.playing) return { ...prev, playing: false }
      return { ...prev, playing: true, at: prev.at >= prev.end ? prev.start : prev.at }
    })
  }, [])

  useEffect(() => {
    if (!replay?.playing) return undefined
    const id = setInterval(() => {
      setReplay((prev) => {
        if (!prev?.playing) return prev
        const next = prev.at + 0.2 * prev.speed
        return next >= prev.end
          ? { ...prev, at: prev.end, playing: false }
          : { ...prev, at: next }
      })
    }, 200)
    return () => clearInterval(id)
  }, [replay?.playing])

  const handleNodeClick = useCallback(
    (processName) => setSelectedApp((prev) => (prev === processName ? null : processName)),
    [],
  )

  const handleExport = useCallback(async () => {
    if (exporting) return
    setExporting(true)
    try {
      const res = await fetch('/api/report')
      if (!res.ok) throw new Error(`report failed: ${res.status}`)
      const win = window.open('', '_blank')
      if (!win) throw new Error('popup blocked — allow popups for this site')
      win.document.open()
      win.document.write(buildReportHtml(await res.json()))
      win.document.close()
      win.focus()
      setTimeout(() => win.print(), 400)
    } catch (err) {
      window.alert(`Export failed: ${err.message}`)
    } finally {
      setExporting(false)
    }
  }, [exporting])

  const replayConnections = useMemo(
    () => (replay ? reconstructState(replay.events, replay.at) : null),
    [replay],
  )

  const filtered = useMemo(
    () => (replayConnections ?? connectionList).filter((c) => matches(c, filters)),
    [replayConnections, connectionList, filters],
  )
  const graphConnections = useMemo(
    () => (selectedApp ? filtered.filter((c) => c.process === selectedApp) : filtered),
    [filtered, selectedApp],
  )

  // Rates are unknowable from history, so replay reports counts only.
  const viewStats = useMemo(() => {
    if (!replay) return stats
    const opens = replay.events.filter((e) => e.kind === 'open' && e.ts <= replay.at).length
    return {
      ...stats,
      connections: filtered.length,
      applications: new Set(filtered.map((c) => c.process)).size,
      domains: new Set(filtered.filter((c) => c.remote_ip).map((c) => c.domain)).size,
      requests: opens,
    }
  }, [replay, stats, filtered])

  const downHistory = history.map((h) => h.down)
  const upHistory = history.map((h) => h.up)

  const tabButton = (id, label) => (
    <button
      key={id}
      type="button"
      onClick={() => {
        setDetailConn(null)
        setRightTab(id)
      }}
      className={`border-b-2 px-3 py-2 text-[12px] font-medium transition-colors ${
        rightTab === id
          ? 'border-ghost-accent text-ghost-accent'
          : 'border-transparent text-ghost-muted hover:text-ghost-text2'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <header className="flex items-center gap-3 border-b border-ghost-line bg-ghost-panel/80 px-4 py-2.5 backdrop-blur">
        <div className="flex items-center gap-2">
          <span className="text-base leading-none text-ghost-accent">◈</span>
          <h1 className="text-[14px] font-semibold text-ghost-text">GhostNet</h1>
        </div>

        <span className="flex items-center gap-1.5 rounded-full border border-ghost-green/30 bg-ghost-green/8 px-2 py-0.5 text-[11px] font-medium text-ghost-green">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? 'bg-ghost-green live-dot' : 'bg-ghost-muted'}`}
          />
          {connected ? 'Live' : 'Offline'}
        </span>

        <div className="ml-auto flex items-center gap-2 text-[12px]">
          {status?.demo && (
            <span className="rounded-md border border-violet-400/30 bg-violet-500/10 px-2 py-0.5 font-medium text-violet-400/80">
              Demo
            </span>
          )}
          <span className="text-ghost-muted">
            {status?.source ?? '—'}
            {status ? (status.elevated ? ' · full' : ' · limited') : ''}
          </span>
          {alerts.length > 0 && (
            <button
              type="button"
              onClick={dismissAllAlerts}
              className="rounded-md border border-amber-400/30 bg-amber-400/8 px-2 py-0.5 font-medium text-amber-400/80 transition-colors hover:bg-amber-400/15"
              title="New application → destination pairs. Click to clear."
            >
              {alerts.length} alert{alerts.length > 1 ? 's' : ''}
            </button>
          )}
          <button
            type="button"
            onClick={replay ? exitReplay : () => loadReplayWindow(replay?.window ?? 3600)}
            className={`rounded-md border px-2 py-0.5 font-medium transition-colors ${
              replay
                ? 'border-amber-400/40 bg-amber-400/10 text-amber-400/80'
                : 'border-ghost-line text-ghost-text2 hover:border-ghost-accent/40 hover:text-ghost-accent'
            }`}
            title="Scrub back through 24h of recorded connection events"
          >
            {replay ? 'Replaying' : 'Replay'}
          </button>
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="rounded-md border border-ghost-line px-2 py-0.5 font-medium text-ghost-text2 transition-colors hover:border-ghost-accent/40 hover:text-ghost-accent disabled:opacity-40"
            title="Download a printable report of the current state"
          >
            {exporting ? 'Building…' : 'Export'}
          </button>
        </div>
      </header>

      <PermissionBanner status={status} />

      {/* stats row */}
      <div className="grid grid-cols-2 gap-3 px-4 pt-3 lg:grid-cols-4">
        <StatsCard
          label="Download"
          value={formatRate(viewStats.download_bps || 0)}
          sub={`total ${formatBytes(viewStats.total_recv || 0)}`}
          spark={downHistory}
          accent="#6e56cf"
        />
        <StatsCard
          label="Upload"
          value={formatRate(viewStats.upload_bps || 0)}
          sub={`total ${formatBytes(viewStats.total_sent || 0)}`}
          spark={upHistory}
          accent="#3e63dd"
        />
        <StatsCard
          label="Connections"
          value={viewStats.connections ?? 0}
          sub={`${viewStats.established ?? 0} established · ${viewStats.applications ?? 0} apps · ${viewStats.domains ?? 0} domains`}
          accent="#30a46c"
        />
        <StatsCard
          label="Requests"
          value={(viewStats.requests ?? 0).toLocaleString()}
          sub={replay ? 'opens up to scrub position' : `session uptime ${formatUptime(status?.uptime)}`}
          accent="#e38c2d"
        />
      </div>

      {/* bandwidth over time */}
      <div className="mt-3 px-4">
        <TrafficChart
          history={history}
          windowMinutes={trafficWindow}
          onWindowChange={setTrafficWindow}
        />
      </div>

      {/* filters */}
      <div className="mt-3 px-4">
        <FilterBar
          filters={filters}
          onChange={setFilters}
          shown={filtered.length}
          total={(replayConnections ?? connectionList).length}
        />
      </div>

      {/* activity replay scrubber */}
      {replay && (
        <div className="mt-3 px-4">
          <ReplayBar
            start={replay.start}
            end={replay.end}
            at={replay.at}
            playing={replay.playing}
            speed={replay.speed}
            windowSec={replay.window}
            events={replay.events}
            loading={replay.loading}
            onChange={(at) => setReplay((prev) => (prev ? { ...prev, at } : prev))}
            onTogglePlay={togglePlay}
            onSpeed={(speed) => setReplay((prev) => (prev ? { ...prev, speed } : prev))}
            onWindow={loadReplayWindow}
            onExit={exitReplay}
          />
        </div>
      )}

      {/* main split */}
      <div className="mt-3 flex min-h-0 flex-1 gap-3 px-4 pb-3">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-lg border border-ghost-line bg-ghost-panel">
          {selectedApp && (
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 rounded-md border border-ghost-accent/30 bg-ghost-bg/90 px-2.5 py-1.5 text-[12px] text-ghost-accent">
              <span>Filtering: {selectedApp}</span>
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className="text-ghost-muted transition-colors hover:text-ghost-text"
              >
                ✕
              </button>
            </div>
          )}
          <NetworkGraph
            connections={graphConnections}
            selected={selectedApp}
            onNodeClick={handleNodeClick}
          />
        </div>

        <aside className="flex w-[320px] shrink-0 flex-col overflow-hidden rounded-lg border border-ghost-line bg-ghost-panel">
          <div className="flex border-b border-ghost-line">
            {tabButton('apps', 'Apps')}
            {tabButton('domains', 'Domains')}
            {tabButton('conns', 'Conns')}
          </div>
          <div className="min-h-0 flex-1">
            {detailConn ? (
              <ConnectionDetail
                conn={detailConn}
                now={now}
                onBack={() => setDetailConn(null)}
              />
            ) : rightTab === 'apps' ? (
              <ProcessList
                connections={filtered}
                selected={selectedApp}
                onSelect={setSelectedApp}
                pidRates={bandwidth.rates}
              />
            ) : rightTab === 'domains' ? (
              <DomainPanel
                connections={filtered}
                onSelect={(domain) => {
                  setFilters({ ...EMPTY_FILTERS, q: domain })
                  setRightTab('apps')
                }}
              />
            ) : (
              <ConnectionList
                connections={filtered}
                selected={detailConn?.conn_id}
                onSelect={setDetailConn}
              />
            )}
          </div>
        </aside>
      </div>

      {/* request timeline */}
      <div className="px-4 pb-3">
        <Timeline
          events={replay ? replay.events : events}
          windowMinutes={replay ? replay.window / 60 : timelineWindow}
          onWindowChange={(m) => (replay ? loadReplayWindow(m * 60) : setTimelineWindow(m))}
          referenceTime={replay ? replay.at : undefined}
        />
      </div>

      <AlertToasts alerts={alerts} onDismiss={dismissAlert} />

      {/* status bar */}
      <footer className="flex items-center gap-4 border-t border-ghost-line bg-ghost-panel/60 px-4 py-1.5 text-[11px] text-ghost-muted">
        {replay && (
          <span className="text-amber-400/70">replay {formatClock(replay.at)}</span>
        )}
        <span>uptime {formatUptime(status?.uptime)}</span>
        <span>requests {(viewStats.requests ?? 0).toLocaleString()}</span>
        <span>poll {status?.poll_interval ?? '—'}s</span>
        <span>bandwidth: {status?.bandwidth ?? '—'}</span>
        <span className="ml-auto">
          {connected
            ? `connected${status?.ws_clients ? ` · ${status.ws_clients} clients` : ''}`
            : 'reconnecting…'}
        </span>
      </footer>
    </div>
  )
}
