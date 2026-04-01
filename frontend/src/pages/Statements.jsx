import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getStatements } from '../services/api'
import StatusBadge from '../components/StatusBadge'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

function formatAmount(val) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function Statements() {
  const [statements, setStatements] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    getStatements({ limit: 50 })
      .then(res => { setStatements(res.data); setTotal(res.total) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="page-header">
        <h2>Bank Statements</h2>
        <p>camt.053 end-of-day statements &mdash; {total} total</p>
      </div>

      <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Schema Design:</strong> Statement headers and entries are in separate collections.
          Entries can be numerous (unbounded), so they are stored separately to prevent hitting the 16MB document limit.
          This follows the <em>separate collection for unbounded data</em> pattern.
        </p>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading">Loading statements...</div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Statement ID</th>
                  <th>Account</th>
                  <th>Owner</th>
                  <th>Date</th>
                  <th>Opening Balance</th>
                  <th>Closing Balance</th>
                  <th>Entries</th>
                  <th>Credits</th>
                  <th>Debits</th>
                </tr>
              </thead>
              <tbody>
                {statements.map(s => (
                  <tr key={s.statementId}>
                    <td>
                      <Link to={`/statements/${s.statementId}`} style={{ fontFamily: 'monospace', fontSize: 12 }}>
                        {s.statementId}
                      </Link>
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{s.accountIban?.slice(0, 12)}...</td>
                    <td>{s.accountOwner}</td>
                    <td>{formatDate(s.statementDate)}</td>
                    <td className="amount credit">{formatAmount(s.balances?.openingBooked?.amount)}</td>
                    <td className="amount credit">{formatAmount(s.balances?.closingBooked?.amount)}</td>
                    <td>{s.summary?.entryCount}</td>
                    <td className="amount credit">{s.summary?.totalCredits?.count}</td>
                    <td className="amount debit">{s.summary?.totalDebits?.count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
