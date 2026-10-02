import { useEffect } from 'react'
import { categoryColor } from '../utils/colors'
import { formatClock } from '../utils/format'

const VISIBLE = 4
const AUTO_DISMISS_MS = 12000

function Toast({ alert, onDismiss }) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss?.(alert.id), AUTO_DISMISS_MS)
    return () => clearTimeout(timer)
  }, [alert.id, onDismiss])

  const color = categoryColor(alert.category)

  return (
    <div
      className="pointer-events-auto flex w-full items-start gap-2 rounded-md border bg-ghost-panel/95 px-3 py-2 shadow-lg shadow-black/40 backdrop-blur"
      style={{ borderColor: `${color}55` }}
    >
      <span
        className="mt-0.5 shrink-0 rounded px-1 py-0.5 text-[9px] font-semibold tracking-wide"
        style={{ color, background: `${color}1a`, border: `1px solid ${color}44` }}
      >
        {(alert.category || 'OTHER').toUpperCase()}
      </span>

      <div className="min-w-0 flex-1">
        <div className="truncate text-[12px] font-medium text-slate-200">
          {alert.process} <span className="text-slate-600">→</span>{' '}
          <span className="font-mono">{alert.site}</span>
        </div>
        <div className="mt-0.5 font-mono text-[10px] text-slate-500">
          first seen {formatClock(alert.ts)}
          {alert.port ? ` · :${alert.port}` : ''}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onDismiss?.(alert.id)}
        className="shrink-0 text-slate-600 transition-colors hover:text-slate-300"
        aria-label="dismiss alert"
      >
        ✕
      </button>
    </div>
  )
}

export default function AlertToasts({ alerts, onDismiss }) {
  if (!alerts?.length) return null
  return (
    <div className="pointer-events-none fixed top-16 right-4 z-40 flex w-80 flex-col gap-2">
      <div className="flex items-center gap-2 pl-1 text-[10px] font-semibold tracking-[0.16em] text-amber-300">
        <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
        NEW DESTINATIONS
      </div>
      {alerts.slice(0, VISIBLE).map((a) => (
        <Toast key={a.id} alert={a} onDismiss={onDismiss} />
      ))}
      {alerts.length > VISIBLE && (
        <span className="pl-1 font-mono text-[10px] text-slate-600">
          +{alerts.length - VISIBLE} older — see report export
        </span>
      )}
    </div>
  )
}
