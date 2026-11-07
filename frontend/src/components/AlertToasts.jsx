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
      className="pointer-events-auto flex w-full items-start gap-2 rounded-lg border border-ghost-line bg-ghost-panel/95 px-3 py-2.5 shadow-lg shadow-black/30 backdrop-blur"
    >
      <span
        className="mt-0.5 shrink-0 rounded-md px-1.5 py-0.5 text-[10px] font-medium"
        style={{ color, background: `${color}12` }}
      >
        {(alert.category || 'Other')}
      </span>

      <div className="min-w-0 flex-1">
        <div className="truncate text-[13px] font-medium text-ghost-text">
          {alert.process} <span className="text-ghost-muted">→</span>{' '}
          <span className="font-mono">{alert.site}</span>
        </div>
        <div className="mt-0.5 font-mono text-[11px] text-ghost-muted">
          first seen {formatClock(alert.ts)}
          {alert.port ? ` · :${alert.port}` : ''}
        </div>
      </div>

      <button
        type="button"
        onClick={() => onDismiss?.(alert.id)}
        className="shrink-0 text-ghost-muted transition-colors hover:text-ghost-text"
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
      <div className="flex items-center gap-2 pl-1 text-[11px] font-medium text-ghost-accent">
        <span className="h-1.5 w-1.5 rounded-full bg-ghost-accent" />
        New destinations
      </div>
      {alerts.slice(0, VISIBLE).map((a) => (
        <Toast key={a.id} alert={a} onDismiss={onDismiss} />
      ))}
      {alerts.length > VISIBLE && (
        <span className="pl-1 text-[11px] text-ghost-muted">
          +{alerts.length - VISIBLE} older — see report export
        </span>
      )}
    </div>
  )
}
