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
    <div className="rounded-lg border border-ghost-accent/20 bg-ghost-accent/[0.04] px-3 py-2">
      <div className="flex flex-wrap items-center gap-2 text-[12px]">
        <span className="font-medium text-ghost-accent">Replay</span>

        <div className="flex gap-1">
          {REPLAY_WINDOWS.map((w) => (
            <button
              key={w}
              type="button"
              disabled={loading}
              onClick={() => onWindow?.(w)}
              className={`rounded-md px-1.5 py-0.5 transition-colors disabled:opacity-50 ${
                windowSec === w ? 'bg-ghost-accent/15 text-ghost-accent' : 'text-ghost-muted hover:text-ghost-text'
              }`}
            >
              {label(w)}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={onTogglePlay}
          className="rounded-md border border-ghost-accent/25 px-2 py-0.5 text-ghost-accent transition-colors hover:bg-ghost-accent/10"
        >
          {playing ? '❚❚ Pause' : '▶ Play'}
        </button>

        <button
          type="button"
          onClick={() => onSpeed?.(SPEEDS[(SPEEDS.indexOf(speed) + 1) % SPEEDS.length])}
          className="rounded-md border border-ghost-accent/25 px-2 py-0.5 text-ghost-accent transition-colors hover:bg-ghost-accent/10"
          title="playback speed"
        >
          {speed}×
        </button>

        <span className="text-ghost-text2">
          {clock(at)} <span className="text-ghost-muted">/ {clock(now)}</span>
        </span>

        <span className="text-ghost-muted">
          <span style={{ color: '#30a46c' }}>{counts.opens}</span> opens ·{' '}
          <span style={{ color: '#e5484d' }}>{counts.closes}</span> closes ·{' '}
          <span className="text-ghost-text">{counts.active}</span> open
        </span>

        <span className="ml-auto flex items-center gap-2">
          <span className="text-[11px] text-ghost-muted">{cursor.toFixed(1)}%</span>
          <button
            type="button"
            onClick={onExit}
            className="rounded-md bg-ghost-accent/15 px-2 py-0.5 font-medium text-ghost-accent transition-colors hover:bg-ghost-accent/25"
          >
            Go live
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
        className="mt-2 h-1 w-full cursor-pointer appearance-none rounded bg-ghost-line"
        aria-label="replay position"
      />
      <div className="mt-0.5 flex justify-between text-[11px] text-ghost-muted/50">
        <span>{clock(start)}</span>
        <span>{loading ? 'Loading events…' : `${events.length} events`}</span>
        <span>{clock(end)}</span>
      </div>
    </div>
  )
}
