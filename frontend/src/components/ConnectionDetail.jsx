import { appColor, categoryColor, statusColor } from '../utils/colors'
import { formatDateTime, formatDuration, formatRate } from '../utils/format'

function Field({ label, value, mono = true, accent }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-ghost-line/50 py-1.5">
      <span className="w-[92px] shrink-0 text-[10px] tracking-[0.12em] text-slate-500 uppercase">
        {label}
      </span>
      <span
        className={`min-w-0 flex-1 break-all text-[12px] ${mono ? 'font-mono' : ''}`}
        style={{ color: accent || '#cbd5e1' }}
      >
        {value ?? '—'}
      </span>
    </div>
  )
}

export default function ConnectionDetail({ conn, onBack, now = 0 }) {
  if (!conn) return null

  const current = Number.isFinite(now) && now > 0 ? now : NaN
  const age = current - (conn.opened_at || 0)
  const sinceLastSeen = current - (conn.last_seen || 0)
  const cat = conn.category || 'Other'

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex items-center gap-2 border-b border-ghost-line px-3 py-3">
        <button
          type="button"
          onClick={onBack}
          className="rounded border border-ghost-line px-2 py-1 font-mono text-[11px] text-slate-400 transition-colors hover:border-ghost-accent/40 hover:text-ghost-accent"
        >
          ← back
        </button>
        <span className="h-3 w-3 shrink-0 rounded-sm" style={{ background: appColor(conn.process) }} />
        <span className="min-w-0 flex-1 truncate text-sm font-semibold text-slate-100" title={conn.process}>
          {conn.process}
        </span>
        <span
          className="shrink-0 rounded px-1.5 py-0.5 text-[9px] font-semibold tracking-wide"
          style={{
            color: categoryColor(cat),
            background: `${categoryColor(cat)}1a`,
            border: `1px solid ${categoryColor(cat)}44`,
          }}
        >
          {cat.toUpperCase()}
        </span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-2">
        <div className="mb-2 flex items-center gap-2 rounded border border-ghost-line bg-ghost-bg/60 px-2.5 py-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: statusColor(conn.status) }}
          />
          <span className="font-mono text-[11px] tracking-wide text-slate-300">{conn.status}</span>
          <span className="ml-auto font-mono text-[10px] text-slate-500">
            age {formatDuration(age)}
          </span>
        </div>

        <Field label="process" value={conn.process} mono={false} />
        <Field label="pid" value={conn.pid} />
        <Field label="protocol" value={`${conn.protocol?.toUpperCase()} · ${conn.family || '—'}`} />
        <Field label="local" value={`${conn.local_ip || '—'}:${conn.local_port ?? '—'}`} />
        <Field label="remote ip" value={conn.remote_ip || 'listening'} />
        <Field label="remote port" value={conn.remote_port || '—'} />
        <Field label="hostname" value={conn.hostname || (conn.remote_ip ? 'resolving…' : '—')} />
        <Field label="domain" value={conn.registrable || conn.domain} />
        <Field
          label="traffic"
          value={`↓ ${formatRate(conn.rx_bps || 0)}   ↑ ${formatRate(conn.tx_bps || 0)}`}
        />
        <Field label="opened" value={formatDateTime(conn.opened_at)} />
        <Field label="last seen" value={formatDateTime(conn.last_seen)} />
        <Field label="idle" value={formatDuration(sinceLastSeen)} />
        <Field label="conn id" value={conn.conn_id} />
      </div>
    </div>
  )
}
