const STATUSES = ['', 'ESTABLISHED', 'LISTEN', 'CLOSE_WAIT', 'TIME_WAIT', 'SYN_SENT', 'UDP']

export default function FilterBar({ filters, onChange, shown, total }) {
  const active = filters.q || filters.protocol || filters.status

  return (
    <div className="flex items-center gap-2">
      <div className="relative flex-1 max-w-xs">
        <span className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-slate-600">
          ⌕
        </span>
        <input
          type="text"
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
          placeholder="search app, domain, ip, port…"
          className="w-full rounded-md border border-ghost-line bg-ghost-bg py-1.5 pr-2 pl-7 font-mono text-xs text-slate-200 placeholder:text-slate-600 focus:border-ghost-accent/50 focus:outline-none"
        />
      </div>

      <select
        value={filters.protocol}
        onChange={(e) => onChange({ ...filters, protocol: e.target.value })}
        className="rounded-md border border-ghost-line bg-ghost-bg px-2 py-1.5 font-mono text-xs text-slate-300 focus:border-ghost-accent/50 focus:outline-none"
      >
        <option value="">proto: all</option>
        <option value="tcp">tcp</option>
        <option value="udp">udp</option>
      </select>

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value })}
        className="rounded-md border border-ghost-line bg-ghost-bg px-2 py-1.5 font-mono text-xs text-slate-300 focus:border-ghost-accent/50 focus:outline-none"
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s ? `state: ${s.toLowerCase()}` : 'state: all'}
          </option>
        ))}
      </select>

      {active && (
        <button
          type="button"
          onClick={() => onChange({ q: '', protocol: '', status: '' })}
          className="rounded-md border border-ghost-line px-2 py-1.5 font-mono text-xs text-slate-500 transition-colors hover:text-slate-200"
        >
          clear
        </button>
      )}

      <span className="ml-auto font-mono text-[11px] text-slate-500">
        {shown === total ? `${total} connections` : `${shown} / ${total} connections`}
      </span>
    </div>
  )
}
