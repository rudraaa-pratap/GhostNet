// Muted, balanced palette — avoids the neon AI-dashboard look
const PALETTE = [
  '#6e56cf', // violet
  '#e5484d', // red
  '#30a46c', // green
  '#e38c2d', // amber
  '#3e63dd', // blue
  '#ab4aba', // purple
  '#0d9488', // teal
  '#d6409f', // pink
  '#e54666', // crimson
  '#0090ff', // sky
]

export function appColor(name) {
  let h = 0
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0
  return PALETTE[h % PALETTE.length]
}

const CATEGORY_COLORS = {
  Ads: '#e5484d',
  Analytics: '#d6409f',
  CDN: '#0d9488',
  Google: '#3e63dd',
  GitHub: '#8b8d98',
  Microsoft: '#3e63dd',
  Apple: '#8b8d98',
  Amazon: '#e38c2d',
  Cloudflare: '#e38c2d',
  Meta: '#3e63dd',
  'X / Twitter': '#8b8d98',
  LinkedIn: '#3e63dd',
  Reddit: '#e5484d',
  Discord: '#6e56cf',
  Slack: '#ab4aba',
  Zoom: '#3e63dd',
  Spotify: '#30a46c',
  Netflix: '#e5484d',
  Twitch: '#6e56cf',
  Developer: '#30a46c',
  Gaming: '#d6409f',
  News: '#e38c2d',
  'Search / Browser': '#3e63dd',
  Storage: '#0d9488',
  Payments: '#30a46c',
  Pending: '#706f78',
  IP: '#62636c',
  Local: '#50505a',
  Other: '#62636c',
}

export function categoryColor(category) {
  return CATEGORY_COLORS[category] || appColor(category || 'Other')
}

const STATUS_COLORS = {
  ESTABLISHED: '#30a46c',
  SYN_SENT: '#e38c2d',
  SYN_RECEIVED: '#e38c2d',
  FIN_WAIT1: '#e38c2d',
  FIN_WAIT2: '#e38c2d',
  TIME_WAIT: '#62636c',
  LISTEN: '#3e63dd',
  CLOSE_WAIT: '#e5484d',
  LAST_ACK: '#e5484d',
}

export function statusColor(status) {
  return STATUS_COLORS[status] || '#62636c'
}
