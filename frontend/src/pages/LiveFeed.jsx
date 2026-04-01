import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Radio, Pause, Play, Trash2, ArrowRightLeft, RotateCcw } from 'lucide-react'
import usePaymentStream from '../hooks/usePaymentStream'
import StatusBadge from '../components/StatusBadge'
import MessageTypeBadge from '../components/MessageTypeBadge'

function formatAmount(val, currency) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return `${currency || ''} ${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatTime(ts) {
  if (!ts) return ''
  return new Date(ts).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function EventCard({ event }) {
  const p = event.payment || {}
  const isInsert = event.type === 'insert'
  const isUpdate = event.type === 'update'
  const isReturn = event.type === 'return_linked'
  const isPaymentReturn = p.messageType === 'pacs.004'

  let borderColor = 'var(--border-subtle)'
  if (isReturn) borderColor = 'var(--orange)'
  else if (isPaymentReturn) borderColor = 'var(--orange)'
  else if (isInsert) borderColor = 'var(--accent)'
  else if (isUpdate) borderColor = 'var(--blue)'

  if (isReturn) {
    return (
      <div className="feed-card" style={{ borderLeftColor: 'var(--orange)', background: 'var(--orange-bg)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <RotateCcw size={14} style={{ color: 'var(--orange)' }} />
          <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--orange)' }}>Return Linked</span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{formatTime(event.timestamp)}</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>
          Return <Link to={`/payments/${event.returnUetr}`} style={{ fontFamily: 'var(--font-code)', fontSize: 11 }}>{event.returnUetr?.slice(0, 12)}...</Link>
          {' '}linked to original{' '}
          <Link to={`/payments/${event.originalUetr}`} style={{ fontFamily: 'var(--font-code)', fontSize: 11 }}>{event.originalUetr?.slice(0, 12)}...</Link>
        </div>
        {event.returnReason?.code && (
          <div style={{ fontSize: 11, color: 'var(--orange)', marginTop: 4 }}>
            Reason: {event.returnReason.code} — {event.returnReason.description}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="feed-card" style={{ borderLeftColor: borderColor }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <span className={`feed-dot ${isInsert ? 'feed-dot-insert' : 'feed-dot-update'}`} />
        <span style={{ fontSize: 11, fontWeight: 600, color: isInsert ? 'var(--accent)' : 'var(--blue)' }}>
          {isInsert ? 'NEW' : 'UPDATED'}
        </span>
        <MessageTypeBadge type={p.messageType} />
        <StatusBadge status={p.status} />
        {p.priority === 'HIGH' && <span className="badge badge-orange" style={{ fontSize: 9 }}>HIGH</span>}
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>{formatTime(event.timestamp)}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, fontSize: 13 }}>
        <Link to={`/payments/${p.uetr}`} style={{ fontFamily: 'var(--font-code)', fontSize: 11, color: 'var(--blue-light1)' }}>
          {p.uetr?.slice(0, 12)}...
        </Link>
        <span className="amount" style={{ color: 'var(--accent)' }}>
          {formatAmount(p.settlementAmount, p.settlementCurrency)}
        </span>
        <span style={{ color: 'var(--text-secondary)' }}>
          {p.debtor?.name || '?'} &rarr; {p.creditor?.name || '?'}
        </span>
      </div>
      {isUpdate && event.updatedFields?.length > 0 && (
        <div style={{ fontSize: 11, color: 'var(--blue)', marginTop: 4 }}>
          Changed: {event.updatedFields.join(', ')}
        </div>
      )}
      {isPaymentReturn && p.originalUetr && (
        <div style={{ fontSize: 11, color: 'var(--orange)', marginTop: 4 }}>
          Return of original: <Link to={`/payments/${p.originalUetr}`} style={{ fontFamily: 'var(--font-code)', fontSize: 11 }}>{p.originalUetr?.slice(0, 16)}...</Link>
          {p.returnReason?.code && ` (${p.returnReason.code})`}
        </div>
      )}
    </div>
  )
}

export default function LiveFeed() {
  const [paused, setPaused] = useState(false)
  const { connected, events, stats, clearEvents } = usePaymentStream({ paused })

  return (
    <div>
      <div className="page-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Radio size={24} style={{ color: connected ? 'var(--accent)' : 'var(--red)' }} />
          Live Payment Feed
        </h2>
        <p>Real-time events from MongoDB Change Streams on the payments collection</p>
      </div>

      <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Change Streams:</strong> This page watches <code>db.payments.watch()</code> via
          WebSocket. Every insert and update triggers a real-time event — no polling, no external message queue.
          Run <code>python scripts/generate_payments.py --count 20 --delay 1</code> to see payments flow in live.
        </p>
      </div>

      {/* Status bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16,
        padding: '10px 16px', background: 'var(--bg-card)', borderRadius: 'var(--radius)',
        border: '1px solid var(--border-subtle)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{
            width: 8, height: 8, borderRadius: '50%',
            background: connected ? 'var(--accent)' : 'var(--red)',
            boxShadow: connected ? '0 0 8px var(--accent)' : 'none',
            animation: connected ? 'pulse 2s infinite' : 'none',
          }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: connected ? 'var(--accent)' : 'var(--red)' }}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          <strong style={{ color: 'var(--text-primary)' }}>{stats.total}</strong> events
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          <strong style={{ color: 'var(--accent)' }}>{stats.inserts}</strong> inserts
        </span>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
          <strong style={{ color: 'var(--blue)' }}>{stats.updates}</strong> updates
        </span>
        {stats.returns > 0 && (
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
            <strong style={{ color: 'var(--orange)' }}>{stats.returns}</strong> returns linked
          </span>
        )}

        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <button className="btn btn-sm" onClick={() => setPaused(!paused)}>
            {paused ? <><Play size={12} /> Resume</> : <><Pause size={12} /> Pause</>}
          </button>
          <button className="btn btn-sm" onClick={clearEvents}>
            <Trash2 size={12} /> Clear
          </button>
        </div>
      </div>

      {/* Event list */}
      {events.length === 0 ? (
        <div className="empty-state">
          <Radio size={40} style={{ color: 'var(--text-muted)', marginBottom: 12 }} />
          <p>Waiting for payment events...</p>
          <p style={{ fontSize: 12, marginTop: 8, color: 'var(--text-muted)' }}>
            Create a payment in the UI or run: <code>python scripts/generate_payments.py --delay 1</code>
          </p>
        </div>
      ) : (
        <div>
          {events.map((event, i) => (
            <EventCard key={`${event.timestamp}-${i}`} event={event} />
          ))}
        </div>
      )}
    </div>
  )
}
