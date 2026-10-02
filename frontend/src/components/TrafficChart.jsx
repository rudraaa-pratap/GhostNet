import { useMemo, useState } from 'react'
import { useNow } from '../hooks/useNow'
import { formatRate } from '../utils/format'

const WIDTH = 1000
const HEIGHT = 100

function pathFor(points, xOf, yOf, close) {
  if (!points.length) return ''
  let d = `M ${xOf(points[0])} ${yOf(points[0])}`
  for (let i = 1; i < points.length; i++) d += ` L ${xOf(points[i])} ${yOf(points[i])}`
  if (close) d += ` L ${xOf(points[points.length - 1])} ${HEIGHT} L ${xOf(points[0])} ${HEIGHT} Z`
  return d
}

function WindowButtons({ value, onChange }) {
  return (
    <div className="flex gap-1">
      {[5, 15, 30].map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onChange(m)}
          className={`rounded px-1.5 py-0.5 font-mono text-[10px] transition-colors ${
            value === m ? 'bg-ghost-accent/20 text-ghost-accent' : 'text-slate-500 hover:text-slate-300'
          }`}
        >
          {m}m
        </button>
      ))}
    </div>
  )
}

export default function TrafficChart({ history, windowMinutes, onWindowChange }) {
  const [hover, setHover] = useState(null)
  const now = useNow(2000)

  const { down, up, max, t0, t1 } = useMemo(() => {
    const t1 = now
    const t0 = t1 - windowMinutes * 60
    const rows = history.filter((h) => h.t >= t0)
    const down = rows.map((h) => ({ t: h.t, v: h.down }))
    const up = rows.map((h) => ({ t: h.t, v: h.up }))
    const max = Math.max(1, ...down.map((p) => p.v), ...up.map((p) => p.v))
    return { down, up, max, t0, t1 }
  }, [history, windowMinutes, now])

  const xOf = (p) => ((p.t - t0) / Math.max(t1 - t0, 1)) * WIDTH
  const yOf = (p) => HEIGHT - (p.v / max) * (HEIGHT - 4) - 2

  const currentDown = down.length ? down[down.length - 1].v : 0
  const currentUp = up.length ? up[up.length - 1].v : 0

  return (
    <div className="rounded-lg border border-ghost-line bg-ghost-panel px-4 py-2.5">
      <div className="flex items-center gap-4 text-[11px]">
        <span className="font-medium tracking-[0.14em] text-slate-500">TRAFFIC</span>
        <span className="flex items-center gap-1.5 font-mono text-cyan-300">
          <span className="h-2 w-2 rounded-full bg-cyan-400" />
          ↓ {formatRate(currentDown)}
        </span>
        <span className="flex items-center gap-1.5 font-mono text-violet-300">
          <span className="h-2 w-2 rounded-full bg-violet-400" />
          ↑ {formatRate(currentUp)}
        </span>
        <span className="font-mono text-slate-600">peak {formatRate(max)}</span>
        <span className="ml-auto" />
        <WindowButtons value={windowMinutes} onChange={onWindowChange} />
      </div>

      <div className="relative mt-1.5 h-[72px]">
        {down.length < 2 ? (
          <div className="absolute inset-0 flex items-center justify-center text-[11px] text-slate-600">
            collecting samples…
          </div>
        ) : (
          <svg
            viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
            preserveAspectRatio="none"
            className="h-full w-full"
            onMouseMove={(e) => {
              const rect = e.currentTarget.getBoundingClientRect()
              const frac = (e.clientX - rect.left) / rect.width
              const t = t0 + frac * (t1 - t0)
              const nearest = down.reduce(
                (best, p) => (Math.abs(p.t - t) < Math.abs(best.t - t) ? p : best),
                down[0],
              )
              setHover(nearest)
            }}
            onMouseLeave={() => setHover(null)}
          >
            <line x1="0" y1={HEIGHT / 2} x2={WIDTH} y2={HEIGHT / 2} stroke="#1e3654" strokeWidth="1" />
            <path
              d={pathFor(down, xOf, yOf, true)}
              fill="#22d3ee"
              fillOpacity="0.12"
              stroke="none"
            />
            <path
              d={pathFor(up, xOf, yOf, true)}
              fill="#a78bfa"
              fillOpacity="0.12"
              stroke="none"
            />
            <path
              d={pathFor(down, xOf, yOf, false)}
              fill="none"
              stroke="#22d3ee"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d={pathFor(up, xOf, yOf, false)}
              fill="none"
              stroke="#a78bfa"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            {hover && (
              <line
                x1={xOf(hover)}
                y1="0"
                x2={xOf(hover)}
                y2={HEIGHT}
                stroke="#334155"
                strokeWidth="1"
                vectorEffect="non-scaling-stroke"
              />
            )}
          </svg>
        )}
        {hover && (
          <div
            className="pointer-events-none absolute top-1 rounded border border-ghost-line bg-ghost-bg/95 px-2 py-1 font-mono text-[10px] text-slate-300"
            style={{
              left: `${((hover.t - t0) / Math.max(t1 - t0, 1)) * 100}%`,
              transform: `translateX(${hover.t - t0 > (t1 - t0) / 2 ? '-105%' : '5%'})`,
            }}
          >
            {formatRate(hover.v)} · {new Date(hover.t * 1000).toLocaleTimeString()}
          </div>
        )}
      </div>
    </div>
  )
}
