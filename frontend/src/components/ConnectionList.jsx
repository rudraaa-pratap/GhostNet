import { useMemo } from 'react'
import { appColor, statusColor } from '../utils/colors'
import { formatRate } from '../utils/format'

export default function ConnectionList({ connections, selected, onSelect }) {
  const rows = useMemo(
    () =>
      [...connections]
        .sort((a, b) => (b.rx_bps + b.tx_bps) - (a.rx_bps + a.tx_bps) || a.process.localeCompare(b.process))
        .map((c) => ({
          ...c,
          key: c.conn_id,
          rate: (c.rx_bps || 0) + (c.tx_bps || 0),
        })),
    [connections],
  )

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center justify-between border-b border-ghost-line px-4 py-3">
        <h2 className="text-[11px] font-semibold tracking-[0.18em] text-slate-400">CONNECTIONS</h2>
        <span className="font-mono text-[11px] text-slate-500">{rows.length}</span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="p-4 text-center text-xs text-slate-600">Waiting for traffic…</div>
        )}
        {rows.map((c) => {
          const active = selected === c.key
          return (
            <button
              key={c.key}
              type="button"
              onClick={() => onSelect?.(active ? null : c)}
              className={`row-enter block w-full border-b border-ghost-line/60 px-4 py-2.5 text-left transition-colors ${
                active ? 'bg-ghost-accent/10' : 'hover:bg-white/[0.03]'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: statusColor(c.status) }}
                  title={c.status}
                />
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: appColor(c.process) }}
                />
                <span className="flex-1 truncate text-sm font-medium text-slate-200">
                  {c.process}
                </span>
                <span className="font-mono text-[10px] uppercase tracking-wide text-slate-500">
                  {c.protocol}
                </span>
              </div>

              <div className="mt-1 flex items-center gap-2 pl-4.5">
                <span className="flex-1 truncate font-mono text-[11px] text-slate-400" title={c.domain}>
                  {c.domain}
                </span>
                <span className="font-mono text-[11px] text-slate-500">:{c.remote_port}</span>
              </div>

              <div className="mt-1 flex items-center gap-2 pl-4.5 font-mono text-[10px]">
                <span className="text-slate-600">pid {c.pid}</span>
                <span className="text-slate-700">·</span>
                <span className="text-slate-600">{c.status.toLowerCase()}</span>
                {c.rate > 0 && (
                  <span className="ml-auto text-cyan-400/75">
                    ↓{formatRate(c.rx_bps || 0)} <span className="text-violet-400/75">↑{formatRate(c.tx_bps || 0)}</span>
                  </span>
                )}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}
