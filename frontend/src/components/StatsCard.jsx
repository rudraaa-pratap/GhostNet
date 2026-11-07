function Sparkline({ data, color = '#6e56cf' }) {
  if (!data || data.length < 2) return null
  const max = Math.max(...data, 1)
  const w = 96
  const h = 26
  const step = w / (data.length - 1)
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`)
    .join(' ')
  return (
    <svg width={w} height={h} className="mt-1 overflow-visible" aria-hidden="true">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" opacity="0.7" />
      <polyline
        points={`0,${h} ${points} ${w},${h}`}
        fill={color}
        opacity="0.06"
        stroke="none"
      />
    </svg>
  )
}

export default function StatsCard({ label, value, sub, spark, accent = '#6e56cf' }) {
  return (
    <div className="rounded-lg border border-ghost-line bg-ghost-panel px-4 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <span className="text-[12px] font-medium text-ghost-muted">
          {label}
        </span>
        <span className="h-1.5 w-1.5 rounded-full" style={{ background: accent }} />
      </div>
      <div className="mt-1 text-2xl font-semibold text-ghost-text">{value}</div>
      {sub && <div className="mt-0.5 text-[12px] text-ghost-muted">{sub}</div>}
      {spark && <Sparkline data={spark} color={accent} />}
    </div>
  )
}
