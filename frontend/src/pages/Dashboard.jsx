import { useCallback, useMemo, useState } from 'react'
import DomainPanel from '../components/DomainPanel'
import FilterBar from '../components/FilterBar'
import NetworkGraph from '../components/NetworkGraph'
import PermissionBanner from '../components/PermissionBanner'
import ProcessList from '../components/ProcessList'
import StatsCard from '../components/StatsCard'
import Timeline from '../components/Timeline'
import TrafficChart from '../components/TrafficChart'
import { useNetworkSocket } from '../hooks/useNetworkSocket'
import { formatBytes, formatRate } from '../utils/format'

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
  const { connectionList, stats, status, history, events, bandwidth, connected } =
    useNetworkSocket()
  const [selectedApp, setSelectedApp] = useState(null)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [rightTab, setRightTab] = useState('apps')
  const [trafficWindow, setTrafficWindow] = useState(15)
  const [timelineWindow, setTimelineWindow] = useState(15)

  const handleNodeClick = useCallback(
    (processName) => setSelectedApp((prev) => (prev === processName ? null : processName)),
    [],
  )

  const filtered = useMemo(
    () => connectionList.filter((c) => matches(c, filters)),
    [connectionList, filters],
  )
  const graphConnections = useMemo(
    () => (selectedApp ? filtered.filter((c) => c.process === selectedApp) : filtered),
    [filtered, selectedApp],
  )

  const downHistory = history.map((h) => h.down)
  const upHistory = history.map((h) => h.up)

  const tabButton = (id, label) => (
    <button
      key={id}
      type="button"
      onClick={() => setRightTab(id)}
      className={`border-b-2 px-3 py-2 text-[11px] font-semibold tracking-[0.14em] transition-colors ${
        rightTab === id
          ? 'border-ghost-accent text-ghost-accent'
          : 'border-transparent text-slate-500 hover:text-slate-300'
      }`}
    >
      {label}
    </button>
  )

  return (
    <div className="flex h-full flex-col">
      {/* header */}
      <header className="flex items-center gap-4 border-b border-ghost-line bg-ghost-panel/80 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2.5">
          <span className="text-lg leading-none text-ghost-accent">◈</span>
          <h1 className="text-[15px] font-bold tracking-[0.22em] text-slate-100">GHOSTNET</h1>
        </div>
        <span className="flex items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold tracking-widest text-emerald-300">
          <span
            className={`h-1.5 w-1.5 rounded-full bg-emerald-400 ${connected ? 'live-dot' : ''}`}
            style={connected ? undefined : { background: '#64748b', animation: 'none' }}
          />
          {connected ? 'LIVE' : 'OFFLINE'}
        </span>

        <div className="ml-auto flex items-center gap-2 text-[11px]">
          {status?.demo && (
            <span className="rounded border border-violet-400/40 bg-violet-500/15 px-2 py-0.5 font-semibold tracking-wider text-violet-300">
              DEMO DATA
            </span>
          )}
          <span className="rounded bg-white/[0.05] px-2 py-0.5 font-mono text-slate-400">
            src: {status?.source ?? '—'}
            {status ? (status.elevated ? ' · full view' : ' · limited') : ''}
          </span>
        </div>
      </header>

      <PermissionBanner status={status} />

      {/* stats row */}
      <div className="grid grid-cols-2 gap-3 px-4 pt-4 lg:grid-cols-4">
        <StatsCard
          label="DOWNLOAD"
          value={formatRate(stats.download_bps || 0)}
          sub={`total ${formatBytes(stats.total_recv || 0)}`}
          spark={downHistory}
          accent="#22d3ee"
        />
        <StatsCard
          label="UPLOAD"
          value={formatRate(stats.upload_bps || 0)}
          sub={`total ${formatBytes(stats.total_sent || 0)}`}
          spark={upHistory}
          accent="#a78bfa"
        />
        <StatsCard
          label="CONNECTIONS"
          value={stats.connections ?? 0}
          sub={`${stats.established ?? 0} established · ${stats.applications ?? 0} apps · ${stats.domains ?? 0} domains`}
          accent="#34d399"
        />
        <StatsCard
          label="REQUESTS"
          value={(stats.requests ?? 0).toLocaleString()}
          sub={`session uptime ${formatUptime(status?.uptime)}`}
          accent="#fbbf24"
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
          total={connectionList.length}
        />
      </div>

      {/* main split */}
      <div className="mt-3 flex min-h-0 flex-1 gap-3 px-4 pb-3">
        <div className="relative min-w-0 flex-1 overflow-hidden rounded-lg border border-ghost-line bg-ghost-panel">
          {selectedApp && (
            <div className="absolute top-3 left-3 z-10 flex items-center gap-2 rounded border border-ghost-accent/40 bg-ghost-bg/90 px-2.5 py-1.5 text-[11px] text-ghost-accent">
              <span>ghost mode: {selectedApp}</span>
              <button
                type="button"
                onClick={() => setSelectedApp(null)}
                className="text-slate-500 transition-colors hover:text-slate-200"
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

        <aside className="flex w-[330px] shrink-0 flex-col overflow-hidden rounded-lg border border-ghost-line bg-ghost-panel">
          <div className="flex border-b border-ghost-line">
            {tabButton('apps', 'APPLICATIONS')}
            {tabButton('domains', 'DOMAINS')}
          </div>
          <div className="min-h-0 flex-1">
            {rightTab === 'apps' ? (
              <ProcessList
                connections={filtered}
                selected={selectedApp}
                onSelect={setSelectedApp}
                pidRates={bandwidth.rates}
              />
            ) : (
              <DomainPanel
                connections={filtered}
                onSelect={(domain) => {
                  setFilters({ ...EMPTY_FILTERS, q: domain })
                  setRightTab('apps')
                }}
              />
            )}
          </div>
        </aside>
      </div>

      {/* request timeline */}
      <div className="px-4 pb-3">
        <Timeline
          events={events}
          windowMinutes={timelineWindow}
          onWindowChange={setTimelineWindow}
        />
      </div>

      {/* status bar */}
      <footer className="flex items-center gap-4 border-t border-ghost-line bg-ghost-panel/60 px-4 py-1.5 font-mono text-[10px] text-slate-500">
        <span>uptime {formatUptime(status?.uptime)}</span>
        <span>requests {(stats.requests ?? 0).toLocaleString()}</span>
        <span>poll {status?.poll_interval ?? '—'}s</span>
        <span>bandwidth: {status?.bandwidth ?? '—'}</span>
        <span className="ml-auto">
          {connected
            ? `ws connected${status?.ws_clients ? ` · ${status.ws_clients} clients` : ''}`
            : 'ws reconnecting…'}
        </span>
      </footer>
    </div>
  )
}
