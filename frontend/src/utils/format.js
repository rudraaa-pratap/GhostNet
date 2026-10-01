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
