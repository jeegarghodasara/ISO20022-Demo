import { useEffect, useRef, useState, useCallback } from 'react'

const WS_URL = 'ws://localhost:8000/ws/payments'
const RECONNECT_DELAY = 3000

/**
 * Hook to connect to the MongoDB Change Stream via WebSocket.
 *
 * Returns:
 *   - connected: boolean
 *   - events: array of all received events (most recent first)
 *   - lastEvent: the most recent event
 *   - stats: { inserts, updates, returns, total }
 *   - clearEvents: function to reset the event list
 *
 * Options:
 *   - filter: function(event) => boolean — only keep matching events
 *   - maxEvents: max events to keep in memory (default 200)
 *   - paused: if true, events are received but not added to the list
 */
export default function usePaymentStream({ filter, maxEvents = 200, paused = false } = {}) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState([])
  const [lastEvent, setLastEvent] = useState(null)
  const [stats, setStats] = useState({ inserts: 0, updates: 0, returns: 0, total: 0 })
  const wsRef = useRef(null)
  const pausedRef = useRef(paused)
  const reconnectTimer = useRef(null)

  // Keep pausedRef in sync
  useEffect(() => { pausedRef.current = paused }, [paused])

  const clearEvents = useCallback(() => {
    setEvents([])
    setStats({ inserts: 0, updates: 0, returns: 0, total: 0 })
  }, [])

  useEffect(() => {
    let unmounted = false

    function connect() {
      if (unmounted) return
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        if (!unmounted) setConnected(true)
      }

      ws.onclose = () => {
        if (!unmounted) {
          setConnected(false)
          // Reconnect after delay
          reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
        }
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (msg) => {
        try {
          const event = JSON.parse(msg.data)

          // Skip connection confirmations and pongs
          if (event.type === 'connected' || event.type === 'pong') return

          // Apply filter if provided
          if (filter && !filter(event)) return

          setLastEvent(event)

          // Update stats
          setStats(prev => ({
            inserts: prev.inserts + (event.type === 'insert' ? 1 : 0),
            updates: prev.updates + (event.type === 'update' ? 1 : 0),
            returns: prev.returns + (event.type === 'return_linked' ? 1 : 0),
            total: prev.total + 1,
          }))

          // Add to event list unless paused
          if (!pausedRef.current) {
            setEvents(prev => {
              const next = [event, ...prev]
              return next.length > maxEvents ? next.slice(0, maxEvents) : next
            })
          }
        } catch (e) {
          // ignore parse errors
        }
      }
    }

    connect()

    // Ping to keep alive
    const pingInterval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)

    return () => {
      unmounted = true
      clearTimeout(reconnectTimer.current)
      clearInterval(pingInterval)
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, []) // intentionally no deps — connect once

  return { connected, events, lastEvent, stats, clearEvents }
}
