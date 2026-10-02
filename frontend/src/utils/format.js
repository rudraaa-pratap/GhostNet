export function formatBytes(n, digits = 1) {
  if (!Number.isFinite(n) || n < 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0
  let v = n
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024
    i++
  }
  return `${v.toFixed(i === 0 ? 0 : digits)} ${units[i]}`
}

export function formatRate(bytesPerSec) {
  return `${formatBytes(bytesPerSec)}/s`
}

export function shortLabel(domain) {
  if (!domain) return ''
  const bare = domain.replace(/^www\./, '')
  const parts = bare.split('.')
  if (parts.length <= 2) return bare
  return parts.slice(-2).join('.')
}

export function formatClock(ts) {
  if (!Number.isFinite(ts)) return '—'
  return new Date(ts * 1000).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function formatDateTime(ts) {
  if (!Number.isFinite(ts)) return '—'
  return new Date(ts * 1000).toLocaleString()
}

export function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return '—'
  const s = Math.floor(seconds % 60)
  const m = Math.floor((seconds / 60) % 60)
  const h = Math.floor(seconds / 3600)
  if (h > 0) return `${h}h ${m}m ${s}s`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

