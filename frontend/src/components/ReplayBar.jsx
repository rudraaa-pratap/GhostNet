import { useMemo } from 'react'
import { useNow } from '../hooks/useNow'
import { REPLAY_WINDOWS, countsAt } from '../utils/replay'

const SPEEDS = [1, 2, 5, 10]

const clock = (ts) =>
  new Date(ts * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })

function label(windowSec) {
  if (windowSec >= 86400) return '24h'
  if (windowSec >= 3600) return `${Math.round(windowSec / 3600)}h`
  return `${Math.round(windowSec / 60)}m`
}

export default function ReplayBar({
  start,
  end,
  at,
  playing,
  speed,
  windowSec,
  events,
  loading,
  onChange,
  onTogglePlay,
  onSpeed,
  onWindow,
  onExit,
}) {
  const now = useNow(1000)
  const counts = useMemo(() => countsAt(events, at), [events, at])
  const span = Math.max(1, end - start)
  const cursor = ((at - start) / span) * 100

  return (
    <div className="rounded-lg border border-amber-400/30 bg-amber-500/[0.06] px-3 py-2">
      <div className="flex flex-wrap items-center gap-2 text-[11px]">
        <span className="font-semibold tracking-[0.16em] text-amber-300">REPLAY</span>

        <div className="flex gap-1">
          {REPLAY_WINDOWS.map((w) => (
            <button
              key={w}
              type="button"
              disabled={loading}
              onClick={() => onWindow?.(w)}
              className={`rounded px-1.5 py-0.5 font-mono transition-colors disabled:opacity-50 ${
                windowSec === w ? 'bg-amber-400/20 text-amber-200' : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {label(w)}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onTogglePlay}
          className="rounded border border-amber-400/40 px-2 py-0.5 font-mono text-amber-200 transition-colors hover:bg-amber-400/10"
        >
          {playing ? '❚❚ pause' : '▶ play'}
        </button>

        <button
          type="button"
          onClick={() => onSpeed?.(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])}
          className="rounded border border-amber-400/40 px-2 py-0.5 font-mono text-amber-200 transition-colors hover:bg-amber-400/10"
          title="playback speed"
        >
          {speed}×
        </button>

        <span className="font-mono text-slate-400">
          {clock(at)} <span className="text-slate-600">/ {clock(now)}</span>
        </span>

        <span className="font-mono text-slate-500">
          <span className="text-emerald-400">{counts.opens}</span> opens ·{' '}
          <span className="text-rose-400">{counts.closes}</span> closes ·{' '}
          <span className="text-slate-300">{counts.active}</span> open
        </span>

        <span className="ml-auto flex items-center gap-2">
          <span className="font-mono text-[10px] text-slate-600">{cursor.toFixed(1)}%</span>
          <button
            type="button"
            onClick={onExit}
            className="rounded bg-ghost-accent/15 px-2 py-0.5 font-semibold tracking-wider text-ghost-accent transition-colors hover:bg-ghost-accent/25"
          >
            GO LIVE
          </button>
        </span>
      </div>

      <input
        type="range"
        min={start}
        max={end}
        step={Math.max(1, span / 2000)}
        value={at}
        onChange={(e) => onChange?.(Number(e.target.value))}
        className="mt-2 h-1 w-full cursor-pointer appearance-none rounded bg-slate-700 accent-amber-400"
        aria-label="replay position"
      />
      <div className="mt-0.5 flex justify-between font-mono text-[10px] text-slate-600">
        <span>{clock(start)}</span>
        <span>{loading ? 'loading events…' : `${events.length} events in window`}</span>
        <span>{clock(end)}</span>
      </div>
    </div>
  )
}
