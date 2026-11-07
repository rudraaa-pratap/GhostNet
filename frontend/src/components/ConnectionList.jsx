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
        <h2 className="text-[12px] font-medium text-ghost-muted">Connections</h2>
        <span className="text-[12px] text-ghost-muted">{rows.length}</span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto">
        {rows.length === 0 && (
          <div className="p-4 text-center text-sm text-ghost-muted">Waiting for traffic…</div>
        )}
        {rows.map((c) => {
          const active = selected === c.key
          return (
            <button
              key={c.key}
              type="button"
              onClick={() => onSelect?.(active ? null : c)}
              className={`row-enter block w-full border-b border-ghost-line/50 px-4 py-2.5 text-left transition-colors ${
                active ? 'bg-ghost-accent/8' : 'hover:bg-white/[0.02]'
              }`}
            >
              <div className="flex items-center gap-2">
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: statusColor(c.status) }}
                  title={c.status}
                />
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: appColor(c.process) }}
                />
                <span className="flex-1 truncate text-[13px] font-medium text-ghost-text">
                  {c.process}
                </span>
                <span className="text-[11px] uppercase text-ghost-muted">
                  {c.protocol}
                </span>
              </div>

              <div className="mt-1 flex items-center gap-2 pl-4">
                <span className="flex-1 truncate font-mono text-[12px] text-ghost-text2" title={c.domain}>
                  {c.domain}
                </span>
                <span className="font-mono text-[12px] text-ghost-muted">:{c.remote_port}</span>
              </div>

              <div className="mt-1 flex items-center gap-2 pl-4 font-mono text-[11px]">
                <span className="text-ghost-muted/60">pid {c.pid}</span>
                <span className="text-ghost-muted/30">·</span>
                <span className="text-ghost-muted/60">{c.status.toLowerCase()}</span>
                {c.rate > 0 && (
                  <span className="ml-auto text-ghost-text2/60">
                    ↓{formatRate(c.rx_bps || 0)} ↑{formatRate(c.tx_bps || 0)}
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
