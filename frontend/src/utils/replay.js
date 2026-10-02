/** Reconstruct historical connection state from persisted timeline events. */

export const REPLAY_WINDOWS = [3600, 21600, 86400]

/** Timeline rows lack a conn_id, so open/close are paired by socket identity. */
export function eventKey(e) {
  return `${e.process}|${e.pid}|${e.remote_ip}|${e.remote_port}|${e.local_port}|${e.opened_at}`
}

function toConnection(e, key) {
  const remoteIp = e.remote_ip || ''
  const domain = e.domain || remoteIp
  const hostname = domain && domain !== remoteIp ? domain : ''
  return {
    conn_id: `replay:${key}`,
    pid: e.pid,
    process: e.process,
    protocol: e.protocol,
    family: '',
    local_ip: '',
    local_port: e.local_port,
    remote_ip: remoteIp,
    remote_port: e.remote_port || 0,
    status: 'ESTABLISHED',
    hostname,
    domain,
    registrable: e.registrable || '',
    category: e.category || '',
    rx_bps: 0,
    tx_bps: 0,
    opened_at: e.opened_at || e.ts,
    last_seen: e.ts,
  }
}

/**
 * Fold open/close events up to `at` into the set of connections that existed
 * at that instant. `events` must be chronological ascending.
 */
export function reconstructState(events, at) {
  const open = new Map()
  for (const e of events) {
    if (e.ts > at) break
    const key = eventKey(e)
    if (e.kind === 'open') open.set(key, toConnection(e, key))
    else open.delete(key)
  }
  return [...open.values()]
}

/** Open/close counts observed up to `at` (used by the scrubber readout). */
export function countsAt(events, at) {
  let opens = 0
  let closes = 0
  for (const e of events) {
    if (e.ts > at) break
    if (e.kind === 'open') opens += 1
    else closes += 1
  }
  return { opens, closes, active: opens - closes }
}
