import { useState, useEffect } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { Search, ChevronLeft, ChevronRight, Code, ChevronDown, ChevronRight as ChevronRightIcon } from 'lucide-react'
import { getPayments, searchPayments } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import MessageTypeBadge from '../components/MessageTypeBadge'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatAmount(val, currency) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return `${currency || ''} ${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function buildMongoQuery({ searchQuery, status, currency, messageType, page, limit }) {
  if (searchQuery) {
    return {
      method: 'find',
      query: {
        $or: [
          { uetr: { $regex: searchQuery, $options: 'i' } },
          { endToEndId: { $regex: searchQuery, $options: 'i' } },
          { 'debtor.name': { $regex: searchQuery, $options: 'i' } },
          { 'creditor.name': { $regex: searchQuery, $options: 'i' } },
          { messageId: { $regex: searchQuery, $options: 'i' } },
        ],
      },
      sort: { createdAt: -1 },
      limit: 50,
    }
  }

  const query = {}
  if (status) query.status = status
  if (currency) query.settlementCurrency = currency
  if (messageType) query.messageType = messageType

  return {
    method: 'find',
    query,
    sort: { settlementDate: -1 },
    skip: (page - 1) * limit,
    limit,
  }
}

function QueryPreview({ searchQuery, status, currency, messageType, page, visible }) {
  const [expanded, setExpanded] = useState(true)
  if (!visible) return null

  const q = buildMongoQuery({ searchQuery, status, currency, messageType, page, limit: 20 })
  const hasFilters = searchQuery || status || currency || messageType

  const queryLines = [`db.payments.${q.method}(`]
  queryLines.push(`  ${JSON.stringify(q.query, null, 2).split('\n').join('\n  ')}`)
  queryLines.push(')')
  if (q.sort) queryLines.push(`.sort(${JSON.stringify(q.sort)})`)
  if (q.skip) queryLines.push(`.skip(${q.skip})`)
  queryLines.push(`.limit(${q.limit})`)

  return (
    <div style={{
      marginBottom: 16, background: 'var(--bg-card)',
      border: '1px solid var(--blue)', borderRadius: 'var(--radius)', padding: '12px 16px',
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
      >
        {expanded
          ? <ChevronDown size={14} style={{ color: 'var(--blue)' }} />
          : <ChevronRightIcon size={14} style={{ color: 'var(--blue)' }} />
        }
        <Code size={14} style={{ color: 'var(--blue)' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--blue)' }}>
          MongoDB Query
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {searchQuery
            ? `$or text search across 5 fields`
            : hasFilters
              ? `Filtered query on polymorphic collection`
              : `Full collection scan with sort`
          }
        </span>
      </div>
      {expanded && (
        <pre style={{
          background: 'var(--bg-primary)', border: '1px solid var(--blue)',
          borderRadius: 'var(--radius)', padding: 14, marginTop: 10,
          fontSize: 12, lineHeight: 1.6, overflow: 'auto', maxHeight: 300,
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: '10px 0 0 0',
        }}>
          <span style={{ color: 'var(--text-muted)' }}>{'// Query sent to MongoDB — single collection, all payment types\n\n'}</span>
          {queryLines.join('\n')}
        </pre>
      )}
    </div>
  )
}

export default function Payments() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [payments, setPayments] = useState([])
  const [total, setTotal] = useState(0)
  const [pages, setPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [activeSearch, setActiveSearch] = useState('')

  const page = parseInt(searchParams.get('page') || '1')
  const status = searchParams.get('status') || ''
  const currency = searchParams.get('currency') || ''
  const messageType = searchParams.get('type') || ''

  useEffect(() => {
    setLoading(true)
    const params = { page, limit: 20 }
    if (status) params.status = status
    if (currency) params.currency = currency
    if (messageType) params.message_type = messageType

    getPayments(params)
      .then(res => {
        setPayments(res.data)
        setTotal(res.total)
        setPages(res.pages)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
    setActiveSearch('')
  }, [page, status, currency, messageType])

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) return
    setLoading(true)
    setActiveSearch(searchQuery)
    try {
      const res = await searchPayments(searchQuery)
      setPayments(res.data)
      setTotal(res.total)
      setPages(1)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const updateFilter = (key, value) => {
    const params = new URLSearchParams(searchParams)
    if (value) params.set(key, value)
    else params.delete(key)
    params.set('page', '1')
    setSearchParams(params)
  }

  return (
    <div>
      <div className="page-header">
        <h2>Payments</h2>
        <p>All ISO 20022 payment messages &mdash; {total} total</p>
      </div>

      <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Polymorphic Pattern:</strong> This single collection stores Credit Transfers, Bank Transfers,
          Payment Returns, and Direct Debits together. Each document has type-specific fields alongside shared ones &mdash;
          no UNION queries or table-per-type needed.
        </p>
      </div>

      <form onSubmit={handleSearch}>
        <div className="search-bar">
          <Search size={16} />
          <input
            type="text"
            placeholder="Search by UETR, End-to-End ID, debtor/creditor name..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </form>

      <div className="filters">
        <select value={messageType} onChange={e => updateFilter('type', e.target.value)}>
          <option value="">All Payment Types</option>
          <option value="pacs.008">Customer Credit Transfer</option>
          <option value="pacs.009">Bank-to-Bank Transfer</option>
          <option value="pacs.004">Payment Return</option>
          <option value="pain.001">Payment Initiation</option>
          <option value="pain.008">Direct Debit</option>
        </select>
        <select value={status} onChange={e => updateFilter('status', e.target.value)}>
          <option value="">All Statuses</option>
          <option value="ACTC">ACTC - Technical OK</option>
          <option value="ACCP">ACCP - Accepted</option>
          <option value="ACSP">ACSP - Processing</option>
          <option value="ACSC">ACSC - Settled</option>
          <option value="RJCT">RJCT - Rejected</option>
        </select>
        <select value={currency} onChange={e => updateFilter('currency', e.target.value)}>
          <option value="">All Currencies</option>
          {['USD', 'EUR', 'GBP', 'JPY', 'AUD'].map(c => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>

      <QueryPreview
        searchQuery={activeSearch}
        status={status}
        currency={currency}
        messageType={messageType}
        page={page}
        visible={!loading && (activeSearch || status || currency || messageType)}
      />

      <div className="card">
        {loading ? (
          <div className="loading">Loading payments...</div>
        ) : (
          <>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>UETR</th>
                    <th>Payment Type</th>
                    <th>Status</th>
                    <th>Amount</th>
                    <th>Debtor</th>
                    <th>Creditor</th>
                    <th>Settlement Date</th>
                    <th>Direction</th>
                  </tr>
                </thead>
                <tbody>
                  {payments.map(p => (
                    <tr key={p.uetr}>
                      <td>
                        <Link to={`/payments/${p.uetr}`} style={{ fontFamily: 'monospace', fontSize: 12 }}>
                          {p.uetr?.slice(0, 8)}...
                        </Link>
                      </td>
                      <td><MessageTypeBadge type={p.messageType} /></td>
                      <td><StatusBadge status={p.status} /></td>
                      <td className="amount">{formatAmount(p.settlementAmount, p.settlementCurrency)}</td>
                      <td>{p.debtor?.name || '-'}</td>
                      <td>{p.creditor?.name || '-'}</td>
                      <td>{formatDate(p.settlementDate)}</td>
                      <td><span className={`badge ${p.direction === 'inbound' ? 'badge-teal' : 'badge-purple'}`}>{p.direction}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="pagination">
              <span>Showing {payments.length} of {total} payments</span>
              <div className="pagination-buttons">
                <button
                  className="btn btn-sm"
                  disabled={page <= 1}
                  onClick={() => updateFilter('page', String(page - 1))}
                >
                  <ChevronLeft size={14} /> Prev
                </button>
                <span style={{ padding: '5px 10px', fontSize: 12 }}>Page {page} of {pages}</span>
                <button
                  className="btn btn-sm"
                  disabled={page >= pages}
                  onClick={() => updateFilter('page', String(page + 1))}
                >
                  Next <ChevronRight size={14} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
