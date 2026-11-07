import { appColor, categoryColor, statusColor } from '../utils/colors'
import { formatDateTime, formatDuration, formatRate } from '../utils/format'

function Field({ label, value, mono = true, accent }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-ghost-line/40 py-1.5">
      <span className="w-[88px] shrink-0 text-[11px] text-ghost-muted">
        {label}
      </span>
      <span
        className={`min-w-0 flex-1 break-all text-[13px] ${mono ? 'font-mono' : ''}`}
        style={{ color: accent || '#ededef' }}
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
          className="rounded-md border border-ghost-line px-2 py-1 text-[12px] text-ghost-muted transition-colors hover:border-ghost-accent/40 hover:text-ghost-accent"
        >
          ← Back
        </button>
        <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ background: appColor(conn.process) }} />
        <span className="min-w-0 flex-1 truncate text-[13px] font-semibold text-ghost-text" title={conn.process}>
          {conn.process}
        </span>
        <span
          className="shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium"
          style={{
            color: categoryColor(cat),
            background: `${categoryColor(cat)}12`,
          }}
        >
          {cat}
        </span>
      </div>

      <div className="scroll-thin min-h-0 flex-1 overflow-y-auto px-4 py-2">
        <div className="mb-2 flex items-center gap-2 rounded-md border border-ghost-line bg-ghost-bg/60 px-2.5 py-1.5">
          <span
            className="h-2 w-2 rounded-full"
            style={{ background: statusColor(conn.status) }}
          />
          <span className="font-mono text-[12px] text-ghost-text">{conn.status}</span>
          <span className="ml-auto text-[11px] text-ghost-muted">
            age {formatDuration(age)}
          </span>
        </div>

        <Field label="Process" value={conn.process} mono={false} />
        <Field label="PID" value={conn.pid} />
        <Field label="Protocol" value={`${conn.protocol?.toUpperCase()} · ${conn.family || '—'}`} />
        <Field label="Local" value={`${conn.local_ip || '—'}:${conn.local_port ?? '—'}`} />
        <Field label="Remote IP" value={conn.remote_ip || 'listening'} />
        <Field label="Remote port" value={conn.remote_port || '—'} />
        <Field label="Hostname" value={conn.hostname || (conn.remote_ip ? 'resolving…' : '—')} />
        <Field label="Domain" value={conn.registrable || conn.domain} />
        <Field
          label="Traffic"
          value={`↓ ${formatRate(conn.rx_bps || 0)}   ↑ ${formatRate(conn.tx_bps || 0)}`}
        />
        <Field label="Opened" value={formatDateTime(conn.opened_at)} />
        <Field label="Last seen" value={formatDateTime(conn.last_seen)} />
        <Field label="Idle" value={formatDuration(sinceLastSeen)} />
        <Field label="Conn ID" value={conn.conn_id} />
      </div>
    </div>
  )
}
