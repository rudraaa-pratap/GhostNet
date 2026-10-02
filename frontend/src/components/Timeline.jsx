import { useMemo } from 'react'
import { useNow } from '../hooks/useNow'
import { appColor } from '../utils/colors'

const WIDTH = 1000
const HEIGHT = 44
const BUCKETS = 100

function WindowButtons({ value, onChange }) {
  const options = [
    [5, '5m'],
    [15, '15m'],
    [60, '1h'],
  ]
  return (
    <div className="flex gap-1">
      {options.map(([m, label]) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] transition-colors ${
            value === m ? 'bg-ghost-accent/20 text-ghost-accent' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  )
}

const clock = (ts) =>
  new Date(ts * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

export default function Timeline({ events, windowMinutes, onWindowChange, referenceTime }) {
  const liveNow = useNow(1000)
  const now = Number.isFinite(referenceTime) ? referenceTime : liveNow

  const model = useMemo(() => {
    const start = now - windowMinutes * 60
    const span = windowMinutes * 60
    const buckets = Array.from({ length: BUCKETS }, (_, i) => ({
      t0: start + (i * span) / BUCKETS,
      t1: start + ((i + 1) * span) / BUCKETS,
      counts: {},
      total: 0,
    }))
    let opens = 0
    let closes = 0
    for (const e of events) {
      if (e.ts < start || e.ts > now) continue
      if (e.kind === 'open') opens += 1
      else closes += 1
      const idx = Math.min(BUCKETS - 1, Math.max(0, Math.floor(((e.ts - start) / span) * BUCKETS)))
      if (e.kind !== 'open') continue
      const b = buckets[idx]
      b.counts[e.process] = (b.counts[e.process] || 0) + 1
      b.total += 1
    }
    const max = Math.max(1, ...buckets.map((b) => b.total))
    return { start, now, buckets, max, opens, closes }
  }, [events, windowMinutes, now])

  const hasEvents = model.opens + model.closes > 0

  return (
    <div className="rounded-lg border border-ghost-line bg-ghost-panel px-4 py-2.5">
      <div className="flex items-center gap-4 text-[11px]">
        <span className="font-medium tracking-[0.14em] text-slate-500">TIMELINE</span>
        <span className="font-mono text-slate-400">
          <span className="text-emerald-400">+{model.opens}</span>
          {' opens '}
          <span className="text-rose-400">−{model.closes}</span>
          {' closes'}
        </span>
        <span className="font-mono text-slate-600">last {windowMinutes >= 60 ? '1h' : `${windowMinutes}m`}</span>
        <span className="ml-auto" />
        <WindowButtons value={windowMinutes} onChange={onWindowChange} />
      </div>

      <div className="relative mt-1.5 h-[44px]">
        {!hasEvents ? (
          <div className="absolute inset-0 flex items-center justify-center text-[11px] text-slate-600">
            no connection events in this window
          </div>
        ) : (
          <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} preserveAspectRatio="none" className="h-full w-full">
            <line
              x1="0"
              y1={HEIGHT - 0.5}
              x2={WIDTH}
              y2={HEIGHT - 0.5}
              stroke="#1b2636"
              strokeWidth="1"
            />
            {model.buckets.map((b, i) => {
              if (!b.total) return null
              const x = (i * WIDTH) / BUCKETS
              const w = WIDTH / BUCKETS - 1.2
              let yCursor = HEIGHT
              const segs = Object.entries(b.counts).sort((a, z) => z[1] - a[1])
              return (
                <g key={i}>
                  <title>{`${clock(b.t0)} — ${b.total} open${b.total > 1 ? 's' : ''}: ${segs
                    .map(([p, n]) => `${p}×${n}`)
                    .join(', ')}`}</title>
                  {segs.map(([process, n]) => {
                    const h = (n / b.max) * (HEIGHT - 3)
                    yCursor -= h
                    return (
                      <rect
                        key={process}
                        x={x}
                        y={yCursor}
                        width={w}
                        height={Math.max(h - 0.8, 1)}
                        fill={appColor(process)}
                        fillOpacity="0.8"
                      />
                    )
                  })}
                </g>
              )
            })}
          </svg>
        )}
      </div>

      <div className="mt-1 flex justify-between font-mono text-[10px] text-slate-600">
        <span>{clock(model.start)}</span>
        <span>{clock(model.now)}</span>
      </div>
    </div>
  )
}
