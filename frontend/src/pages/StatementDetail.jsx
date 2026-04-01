import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { getStatement } from '../services/api'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatAmount(val) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function StatementDetail() {
  const { id } = useParams()
  const [statement, setStatement] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getStatement(id)
      .then(setStatement)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [id])

  if (loading) return <div className="loading">Loading statement...</div>
  if (!statement) return <div className="empty-state"><p>Statement not found</p></div>

  const s = statement

  return (
    <div>
      <div className="page-header">
        <Link to="/statements" style={{ fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
          <ArrowLeft size={14} /> Back to statements
        </Link>
        <h2>Statement: {s.statementId}</h2>
        <p>{s.accountOwner} &mdash; {s.accountIban} &mdash; {formatDate(s.statementDate)}</p>
      </div>

      <div className="grid-3" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-value amount credit">{s.accountCurrency} {formatAmount(s.balances?.openingBooked?.amount)}</div>
          <div className="stat-label">Opening Balance</div>
        </div>
        <div className="stat-card">
          <div className="stat-value amount credit">{s.accountCurrency} {formatAmount(s.balances?.closingBooked?.amount)}</div>
          <div className="stat-label">Closing Balance</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{s.summary?.entryCount}</div>
          <div className="stat-label">Total Entries</div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">Statement Entries</span>
          <span className="card-subtitle">{(s.entries || []).length} entries from separate collection</span>
        </div>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Amount</th>
                <th>Counterparty</th>
                <th>UETR</th>
                <th>Booking Date</th>
                <th>Remittance</th>
              </tr>
            </thead>
            <tbody>
              {(s.entries || []).map((e, i) => (
                <tr key={i}>
                  <td><span className={`badge ${e.creditDebit === 'CRDT' ? 'badge-success' : 'badge-red'}`}>{e.creditDebit}</span></td>
                  <td className={`amount ${e.creditDebit === 'CRDT' ? 'credit' : 'debit'}`}>
                    {e.creditDebit === 'DBIT' ? '-' : '+'}{formatAmount(e.entryAmount)}
                  </td>
                  <td>{e.counterpartyName}</td>
                  <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{e.uetr?.slice(0, 8)}...</td>
                  <td>{formatDate(e.bookingDate)}</td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{e.remittanceInfo || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
