import { useMemo, useState } from 'react'
import { appColor, categoryColor } from '../utils/colors'
import { formatRate } from '../utils/format'

export default function DomainPanel({ connections, onSelect }) {
  const [category, setCategory] = useState(null)

  const groups = useMemo(() => {
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

  const categoryCounts = useMemo(() => {
    const counts = new Map()
    for (const g of groups) counts.set(g.category, (counts.get(g.category) || 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  }, [groups])

  const rows = category ? groups.filter((g) => g.category === category) : groups

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-ghost-line px-4 py-3">
        <h2 className="text-[12px] font-medium text-ghost-muted">Domains</h2>
        <span className="text-[12px] text-ghost-muted">
          {rows.length}
          {category ? ` / ${groups.length}` : ''}
        </span>
      </div>

      {categoryCounts.length > 1 && (
        <div className="scroll-thin flex gap-1.5 overflow-x-auto border-b border-ghost-line px-3 py-2">
          <button
            type="button"
            onClick={() => setCategory(null)}
            className={`shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors ${
              category === null
                ? 'bg-ghost-accent/15 text-ghost-accent'
                : 'text-ghost-muted hover:text-ghost-text'
            }`}
          >
            All {groups.length}
          </button>
          {categoryCounts.map(([name, n]) => {
            const active = category === name
            const color = categoryColor(name)
            return (
              <button
                key={name}
                type="button"
                onClick={() => setCategory(active ? null : name)}
                className="shrink-0 rounded-md px-2 py-0.5 text-[11px] font-medium transition-colors"
                style={{
                  color: active ? '#fff' : color,
                  background: active ? `${color}cc` : `${color}10`,
                }}
              >
                {name} {n}
              </button>
            )
          })}
        </div>
      )}

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="p-4 text-center text-sm text-ghost-muted">No domains yet…</div>
        )}
        {rows.map((g) => (
          <button
            key={g.key}
            type="button"
            onClick={() => onSelect?.(g.key)}
            className="row-enter block w-full border-b border-ghost-line/50 px-4 py-2.5 text-left transition-colors hover:bg-white/[0.02]"
          >
            <div className="flex items-center gap-2">
              <span
                className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium"
                style={{
                  color: categoryColor(g.category),
                  background: `${categoryColor(g.category)}12`,
                }}
              >
                {g.category}
              </span>
              <span className="flex-1 truncate font-mono text-[13px] text-ghost-text" title={g.key}>
                {g.key}
              </span>
              <span className="text-[12px] text-ghost-muted">×{g.count}</span>
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
                <span className="ml-1 font-mono text-[11px] text-ghost-muted/60">
                  :{g.ports.slice(0, 3).join(' :')}
                </span>
              )}
              {(g.rx > 0 || g.tx > 0) && (
                <span className="ml-auto font-mono text-[11px] text-ghost-text2/60">
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
