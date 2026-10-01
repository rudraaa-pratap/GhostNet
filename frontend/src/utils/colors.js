const PALETTE = [
  '#22d3ee',
  '#f472b6',
  '#a78bfa',
  '#34d399',
  '#fbbf24',
  '#60a5fa',
  '#fb7185',
  '#4ade80',
  '#e879f9',
  '#38bdf8',
]

export function appColor(name) {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const CATEGORY_COLORS = {
  Ads: '#fb7185',
  Analytics: '#f472b6',
  CDN: '#2dd4bf',
  Google: '#38bdf8',
  GitHub: '#94a3b8',
  Microsoft: '#60a5fa',
  Apple: '#a78bfa',
  Amazon: '#fb923c',
  Cloudflare: '#fbbf24',
  Meta: '#818cf8',
  'X / Twitter': '#38bdf8',
  LinkedIn: '#38bdf8',
  Reddit: '#f87171',
  Discord: '#818cf8',
  Slack: '#e879f9',
  Zoom: '#22d3ee',
  Spotify: '#4ade80',
  Netflix: '#f87171',
  Twitch: '#c084fc',
  Developer: '#34d399',
  Gaming: '#f472b6',
  News: '#fbbf24',
  'Search / Browser': '#38bdf8',
  Storage: '#2dd4bf',
  Payments: '#4ade80',
  Pending: '#94a3b8',
  IP: '#64748b',
  Local: '#475569',
  Other: '#64748b',
}

export function categoryColor(category) {
  return CATEGORY_COLORS[category] || appColor(category || 'Other')
}
