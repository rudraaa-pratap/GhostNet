const STATUSES = ['', 'ESTABLISHED', 'LISTEN', 'CLOSE_WAIT', 'TIME_WAIT', 'SYN_SENT', 'UDP']

export default function FilterBar({ filters, onChange, shown, total }) {
  const active = filters.q || filters.protocol || filters.status

  return (
    <div className="flex items-center gap-2">
      <div className="relative max-w-xs flex-1">
        <span className="pointer-events-none absolute top-1/2 left-2.5 -translate-y-1/2 text-ghost-muted">
          ⌕
        </span>
        <input
          type="text"
          value={filters.q}
          onChange={(e) => onChange({ ...filters, q: e.target.value })}
          placeholder="Search app, domain, ip, port…"
          className="w-full rounded-md border border-ghost-line bg-ghost-bg py-1.5 pr-2 pl-7 text-sm text-ghost-text placeholder:text-ghost-muted/50 focus:border-ghost-accent/60 focus:outline-none"
        />
      </div>

      <select
        value={filters.protocol}
        onChange={(e) => onChange({ ...filters, protocol: e.target.value })}
        className="rounded-md border border-ghost-line px-2 py-1.5 text-sm text-ghost-text2 focus:border-ghost-accent/60 focus:outline-none"
      >
        <option value="">Proto: all</option>
        <option value="tcp">TCP</option>
        <option value="udp">UDP</option>
      </select>

      <select
        value={filters.status}
        onChange={(e) => onChange({ ...filters, status: e.target.value })}
        className="rounded-md border border-ghost-line px-2 py-1.5 text-sm text-ghost-text2 focus:border-ghost-accent/60 focus:outline-none"
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {s ? s.charAt(0) + s.slice(1).toLowerCase().replace('_', ' ') : 'State: all'}
          </option>
        ))}
      </select>

      {active && (
        <button
          type="button"
          onClick={() => onChange({ q: '', protocol: '', status: '' })}
          className="rounded-md border border-ghost-line px-2 py-1.5 text-sm text-ghost-muted transition-colors hover:text-ghost-text"
        >
          Clear
        </button>
      )}

      <span className="ml-auto text-[12px] text-ghost-muted">
        {shown === total ? `${total} connections` : `${shown} / ${total}`}
      </span>
    </div>
  )
}
