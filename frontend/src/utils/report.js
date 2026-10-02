import { formatBytes, formatDuration, formatRate } from './format'

function esc(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function table(headers, rows) {
  return `<table>
    <thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody>
  </table>`
}

function statsGrid(stats) {
  const cells = [
    ['Download', formatRate(stats.download_bps || 0), `total ${formatBytes(stats.total_recv || 0)}`],
    ['Upload', formatRate(stats.upload_bps || 0), `total ${formatBytes(stats.total_sent || 0)}`],
    ['Connections', stats.connections ?? 0, `${stats.established ?? 0} established`],
    ['Applications', stats.applications ?? 0, `${stats.domains ?? 0} domains`],
    ['Requests', stats.requests ?? 0, 'session total'],
  ]
  return `<div class="grid">${cells
    .map(
      ([label, value, sub]) =>
        `<div class="cell"><div class="label">${esc(label)}</div>` +
        `<div class="value">${esc(value)}</div><div class="sub">${esc(sub)}</div></div>`,
    )
    .join('')}</div>`
}

function hourlyRows(hourly) {
  if (!hourly?.length) return [['—', '0', '0']]
  return hourly.map((b) => [
    new Date(b.hour * 1000).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
    b.opens,
    b.closes,
  ])
}

/** Render a report snapshot as a standalone printable HTML document. */
export function buildReportHtml(report) {
  const { status = {}, stats = {}, processes = [], domains = [], timeline = {}, alerts = [] } = report
  const generated = new Date((report.generated_at || Date.now() / 1000) * 1000)

  const appRows = processes.slice(0, 25).map((p) => [
    p.process,
    p.pids.join(', '),
    p.connections,
    p.established,
    formatRate(p.rx_bps || 0),
    formatRate(p.tx_bps || 0),
    p.domains.slice(0, 3).join(', '),
  ])

  const domainRows = domains.slice(0, 40).map((d) => [
    d.domain,
    d.category,
    d.connections,
    d.processes.join(', '),
    d.ports.slice(0, 4).join(', '),
    formatRate(d.rx_bps || 0),
    formatRate(d.tx_bps || 0),
  ])

  const alertRows = alerts.slice(0, 40).map((a) => [
    new Date(a.ts * 1000).toLocaleString(),
    a.process,
    a.site,
    a.category,
  ])

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>GhostNet report — ${esc(generated.toLocaleString())}</title>
<style>
  @page { margin: 16mm 14mm; }
  * { box-sizing: border-box; }
  body { font: 13px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         color: #0f172a; margin: 0; padding: 24px; background: #fff; }
  h1 { font-size: 20px; margin: 0 0 2px; letter-spacing: .18em; }
  h2 { font-size: 13px; letter-spacing: .14em; text-transform: uppercase;
       color: #475569; margin: 26px 0 8px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }
  .meta { color: #64748b; font-size: 12px; margin-bottom: 4px; }
  .badge { display: inline-block; padding: 1px 7px; border: 1px solid #cbd5e1;
           border-radius: 999px; font-size: 11px; color: #475569; margin-left: 6px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }
  .cell { border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; }
  .cell .label { font-size: 10px; letter-spacing: .12em; text-transform: uppercase; color: #94a3b8; }
  .cell .value { font-size: 18px; font-weight: 600; margin-top: 2px; }
  .cell .sub { font-size: 11px; color: #64748b; }
  table { width: 100%; border-collapse: collapse; font-size: 11.5px; }
  th { text-align: left; font-size: 10px; letter-spacing: .1em; text-transform: uppercase;
       color: #94a3b8; border-bottom: 1px solid #cbd5e1; padding: 5px 8px; }
  td { padding: 5px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
  tbody tr:nth-child(even) { background: #f8fafc; }
  .foot { margin-top: 28px; font-size: 11px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 8px; }
  @media print { body { padding: 0; } h2 { page-break-after: avoid; } table { page-break-inside: auto; }
                 tr { page-break-inside: avoid; } }
</style>
</head>
<body>
  <h1>GHOSTNET REPORT</h1>
  <div class="meta">Generated ${esc(generated.toLocaleString())}</div>
  <div class="meta">
    source ${esc(status.source || '—')}
    <span class="badge">${status.elevated ? 'full view' : 'limited view'}</span>
    <span class="badge">${status.demo ? 'demo data' : 'live data'}</span>
    <span class="badge">uptime ${esc(formatDuration(status.uptime))}</span>
    <span class="badge">window ${esc(formatDuration(report.window))}</span>
  </div>

  <h2>Statistics</h2>
  ${statsGrid(stats)}

  <h2>Applications — ${processes.length} total</h2>
  ${table(['Application', 'PIDs', 'Conns', 'Est.', 'Download', 'Upload', 'Top domains'], appRows)}

  <h2>Domains — ${domains.length} total</h2>
  ${table(['Domain', 'Category', 'Conns', 'Processes', 'Ports', 'Download', 'Upload'], domainRows)}

  <h2>Activity — ${timeline.events ?? 0} events (opens ${timeline.opens ?? 0} / closes ${timeline.closes ?? 0})</h2>
  ${table(['Bucket', 'Opens', 'Closes'], hourlyRows(timeline.hourly))}

  ${alerts.length ? `<h2>Alerts — ${alerts.length} total</h2>${table(['Time', 'Application', 'Site', 'Category'], alertRows)}` : ''}

  <div class="foot">
    GhostNet is local-first — this report was generated on this machine and never uploaded.
    Connection-level monitoring only (no packet capture).
  </div>
</body>
</html>`
}
