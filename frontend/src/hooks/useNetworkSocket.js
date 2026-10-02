import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const HISTORY_LEN = 900 // ~22min of samples at 1.5s (backend keeps 30min)
const EVENTS_LEN = 6000
const BASE_WS_URL = `ws://${window.location.host}/ws`

function eventFromConnection(type, msg) {
  const c = msg.connection
  return {
    ts: msg.ts ?? Date.now() / 1000,
    kind: type === 'conn_open' ? 'open' : 'close',
    conn_id: c.conn_id,
    process: c.process,
    pid: c.pid,
    protocol: c.protocol,
    remote_ip: c.remote_ip,
    remote_port: c.remote_port,
    domain: c.domain,
    registrable: c.registrable,
    category: c.category,
    opened_at: c.opened_at,
  }
}

/**
 * Live GhostNet state over WebSocket.
 *
 * Events: snapshot | conn_open | conn_close | conn_update | stats | dns | bandwidth | alert
 * Timeline history is hydrated once from GET /api/timeline, then appended live.
 * Alerts are hydrated from GET /api/alerts, then appended as they fire.
 */
export function useNetworkSocket() {
  const [connections, setConnections] = useState(() => new Map())
  const [stats, setStats] = useState({})
  const [status, setStatus] = useState(null)
  const [history, setHistory] = useState([])
  const [events, setEvents] = useState([])
  const [alerts, setAlerts] = useState([])
  const [bandwidth, setBandwidth] = useState({ rates: {}, connections: {} })
  const [connected, setConnected] = useState(false)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const wsRef = useRef(null)

  const mergeAlerts = useCallback((incoming) => {
    if (!incoming?.length) return
    setAlerts((prev) => {
      const known = new Set(prev.map((a) => a.id))
      const fresh = incoming.filter((a) => a.id != null && !known.has(a.id))
      return fresh.length ? [...fresh, ...prev].slice(0, 50) : prev
    })
  }, [])

  const dismissAlert = useCallback((id) => {
    setAlerts((prev) => prev.filter((a) => a.id !== id))
  }, [])

  const dismissAllAlerts = useCallback(() => setAlerts([]), [])

  // hydrate timeline from SQLite history (last hour) + persisted alerts
  useEffect(() => {
    let cancelled = false
    fetch('/api/timeline?limit=5000')
      .then((r) => (r.ok ? r.json() : { events: [] }))
      .then((data) => {
        if (cancelled || !data.events?.length) return
        setEvents(data.events.map((e) => ({ ...e, conn_id: null })).slice(-EVENTS_LEN))
      })
      .catch(() => {})

    fetch('/api/alerts?limit=50')
      .then((r) => (r.ok ? r.json() : { alerts: [] }))
      .then((data) => {
        if (!cancelled) mergeAlerts(data.alerts)
      })
      .catch(() => {})

    return () => {
      cancelled = true
    }
  }, [mergeAlerts])

  useEffect(() => {
    let cancelled = false
    let retryTimer
    let attempt = 0

    const pushEvent = (e) => {
      setEvents((prev) => (prev.length >= EVENTS_LEN ? [...prev, e].slice(-EVENTS_LEN) : [...prev, e]))
    }

    const applyRates = (payload) => {
      setBandwidth({ rates: payload.rates || {}, connections: payload.connections || {} })
      setConnections((prev) => {
        const active = payload.connections || {}
        let changed = false
        const next = new Map(prev)
        for (const [id, c] of prev) {
          const r = active[id]
          const rx = r?.rx ?? 0
          const tx = r?.tx ?? 0
          if (c.rx_bps !== rx || c.tx_bps !== tx) {
            next.set(id, { ...c, rx_bps: rx, tx_bps: tx })
            changed = true
          }
        }
        return changed ? next : prev
      })
    }

    const connect = () => {
      if (cancelled) return
      const ws = new WebSocket(BASE_WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        attempt = 0
        setConnected(true)
      }

      ws.onmessage = (raw) => {
        let msg
        try {
          msg = JSON.parse(raw.data)
        } catch {
          return
        }
        switch (msg.type) {
          case 'snapshot': {
            setConnections(new Map(msg.connections.map((c) => [c.conn_id, c])))
            setStats(msg.stats || {})
            setStatus(msg.status || null)
            if (msg.bandwidth) applyRates(msg.bandwidth)
            break
          }
          case 'conn_open':
            setConnections((prev) => {
              const next = new Map(prev)
              next.set(msg.connection.conn_id, msg.connection)
              return next
            })
            pushEvent(eventFromConnection('conn_open', msg))
            break
          case 'conn_close':
            setConnections((prev) => {
              const next = new Map(prev)
              next.delete(msg.connection.conn_id)
              return next
            })
            pushEvent(eventFromConnection('conn_close', msg))
            break
          case 'conn_update':
            setConnections((prev) => {
              if (!prev.has(msg.connection.conn_id)) return prev
              const next = new Map(prev)
              next.set(msg.connection.conn_id, msg.connection)
              return next
            })
            break
          case 'stats':
            setStats(msg.stats || {})
            setHistory((prev) => [...prev, msg.stats].slice(-HISTORY_LEN))
            break
          case 'bandwidth':
            applyRates(msg)
            break
          case 'alert':
            mergeAlerts(msg.alerts)
            break
          case 'dns':
            setConnections((prev) => {
              let changed = false
              const next = new Map(prev)
              for (const [id, c] of prev) {
                if (c.remote_ip === msg.ip && !c.hostname) {
                  next.set(id, {
                    ...c,
                    hostname: msg.hostname,
                    domain: msg.hostname,
                    registrable: msg.registrable ?? c.registrable,
                    category: msg.category ?? c.category,
                  })
                  changed = true
                }
              }
              return changed ? next : prev
            })
            break
          default:
            break
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (cancelled) return
        attempt += 1
        setReconnectAttempt(attempt)
        const delay = Math.min(1000 * 2 ** Math.min(attempt, 3), 5000)
        retryTimer = setTimeout(connect, delay)
      }

      ws.onerror = () => ws.close()
    }

    connect()
    return () => {
      cancelled = true
      clearTimeout(retryTimer)
      wsRef.current?.close()
    }
  }, [mergeAlerts])

  const connectionList = useMemo(() => [...connections.values()], [connections])

  return {
    connections,
    connectionList,
    stats,
    status,
    history,
    events,
    alerts,
    dismissAlert,
    dismissAllAlerts,
    bandwidth,
    connected,
    reconnectAttempt,
  }
}
