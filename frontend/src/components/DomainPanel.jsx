import { useMemo } from 'react'
import { appColor, categoryColor } from '../utils/colors'
import { formatRate } from '../utils/format'

export default function DomainPanel({ connections, onSelect }) {
  const rows = useMemo(() => {
    const groups = new Map()
    for (const c of connections) {
      if (!c.remote_ip) continue
      const key = c.registrable || c.domain || c.remote_ip
      let g = groups.get(key)
      if (!g) {
        g = {
          key,
          category: c.category || 'Other',
          count: 0,
          established: 0,
          processes: new Set(),
          hosts: new Set(),
          ports: new Set(),
          rx: 0,
          tx: 0,
        }
        groups.set(key, g)
      }
      g.count += 1
      if (c.status === 'ESTABLISHED') g.established += 1
      g.processes.add(c.process)
      if (c.hostname) g.hosts.add(c.hostname)
      if (c.remote_port) g.ports.add(c.remote_port)
      if (c.category && c.category !== 'Pending') g.category = c.category
      g.rx += c.rx_bps || 0
      g.tx += c.tx_bps || 0
    }
    return [...groups.values()]
      .map((g) => ({
        ...g,
        processes: [...g.processes],
        hosts: [...g.hosts],
        ports: [...g.ports].sort((a, b) => a - b),
        rx: Math.round(g.rx),
        tx: Math.round(g.tx),
      }))
      .sort((a, b) => b.count - a.count)
  }, [connections])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-ghost-line px-4 py-3">
        <h2 className="text-[11px] font-semibold tracking-[0.18em] text-slate-400">DOMAINS</h2>
        <span className="font-mono text-[11px] text-slate-500">{rows.length}</span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="p-4 text-center text-xs text-slate-600">No domains yet…</div>
        )}
        {rows.map((g) => (
          <button
            key={g.key}
            type="button"
            onClick={() => onSelect?.(g.key)}
            className="row-enter block w-full border-b border-ghost-line/60 px-4 py-2.5 text-left transition-colors hover:bg-white/[0.03]"
          >
            <div className="flex items-center gap-2">
              <span
                className="shrink-0 rounded px-1 py-0.5 text-[9px] font-semibold tracking-wide"
                style={{
                  color: categoryColor(g.category),
                  background: `${categoryColor(g.category)}1a`,
                  border: `1px solid ${categoryColor(g.category)}44`,
                }}
              >
                {g.category.toUpperCase()}
              </span>
              <span className="flex-1 truncate font-mono text-xs text-slate-200" title={g.key}>
                {g.key}
              </span>
              <span className="font-mono text-[11px] text-slate-500">×{g.count}</span>
            </div>
            <div className="mt-1.5 flex items-center gap-1.5 pl-1">
              {g.processes.slice(0, 4).map((p) => (
                <span
                  key={p}
                  className="h-2 w-2 rounded-full"
                  style={{ background: appColor(p) }}
                  title={p}
                />
              ))}
              {g.ports.length > 0 && (
                <span className="ml-1 font-mono text-[10px] text-slate-600">
                  :{g.ports.slice(0, 3).join(' :')}
                </span>
              )}
              {(g.rx > 0 || g.tx > 0) && (
                <span className="ml-auto font-mono text-[10px] text-cyan-400/80">
                  ↓{formatRate(g.rx)} ↑{formatRate(g.tx)}
                </span>
              )}
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
