import { useMemo } from 'react'
import { appColor } from '../utils/colors'
import { formatBytes } from '../utils/format'

export default function ProcessList({ connections, selected, onSelect, pidRates }) {
  const rows = useMemo(() => {
    const byApp = new Map()
    for (const c of connections) {
      let row = byApp.get(c.process)
      if (!row) {
        row = {
          process: c.process,
          pids: new Set(),
          count: 0,
          established: 0,
          domains: new Map(),
          rx: 0,
          tx: 0,
        }
        byApp.set(c.process, row)
      }
      row.pids.add(c.pid)
      row.count += 1
      if (c.status === 'ESTABLISHED') row.established += 1
      if (c.remote_ip) row.domains.set(c.domain, (row.domains.get(c.domain) || 0) + 1)
      const rate = pidRates?.[c.pid]
      if (rate) {
        row.rx += rate.rx || 0
        row.tx += rate.tx || 0
      }
    }
    return [...byApp.values()]
      .map((r) => ({
        process: r.process,
        pids: [...r.pids],
        count: r.count,
        established: r.established,
        rx: Math.round(r.rx),
        tx: Math.round(r.tx),
        domains: [...r.domains.entries()].sort((a, b) => b[1] - a[1]),
      }))
      .sort((a, b) => b.count - a.count)
  }, [connections, pidRates])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-ghost-line px-4 py-3">
        <h2 className="text-[12px] font-medium text-ghost-muted">Applications</h2>
        <span className="text-[12px] text-ghost-muted">{rows.length}</span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="p-4 text-center text-sm text-ghost-muted">Waiting for traffic…</div>
        )}
        {rows.map((row) => {
          const active = selected === row.process
          return (
            <button
              key={row.process}
              type="button"
              onClick={() => onSelect?.(active ? null : row.process)}
              className={`row-enter block w-full border-b border-ghost-line/50 px-4 py-2.5 text-left transition-colors ${
                active ? 'bg-ghost-accent/8' : 'hover:bg-white/[0.02]'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: appColor(row.process) }}
                />
                <span className="flex-1 truncate text-[13px] font-medium text-ghost-text">
                  {row.process}
                </span>
                <span className="text-[12px] text-ghost-muted">
                  {row.established}/{row.count}
                </span>
              </div>
              <div className="mt-1.5 flex flex-wrap gap-1 pl-4">
                {row.domains.slice(0, 3).map(([domain, n]) => (
                  <span
                    key={domain}
                    className="rounded-md bg-white/[0.04] px-1.5 py-0.5 font-mono text-[11px] text-ghost-muted"
                    title={domain}
                  >
                    {domain}
                    {n > 1 ? ` ×${n}` : ''}
                  </span>
                ))}
                {row.domains.length > 3 && (
                  <span className="px-1 py-0.5 text-[11px] text-ghost-muted/50">
                    +{row.domains.length - 3}
                  </span>
                )}
              </div>
              {(row.rx > 0 || row.tx > 0) && (
                <div className="mt-1 pl-4 font-mono text-[11px] text-ghost-text2/60">
                  ↓ {formatBytes(row.rx)}/s  ↑ {formatBytes(row.tx)}/s
                </div>
              )}
            </button>
          )
        })}
      </div>
    </div>
  )
}
