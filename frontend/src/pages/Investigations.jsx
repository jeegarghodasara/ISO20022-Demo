import { useEffect, useState } from 'react'
import { getInvestigations, resolveInvestigation } from '../services/api'
import StatusBadge from '../components/StatusBadge'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function Investigations() {
  const [investigations, setInvestigations] = useState([])
  const [loading, setLoading] = useState(true)
  const [total, setTotal] = useState(0)
  const [selected, setSelected] = useState(null)

  const load = () => {
    setLoading(true)
    getInvestigations({ limit: 50 })
      .then(res => { setInvestigations(res.data); setTotal(res.total) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleResolve = async (caseId) => {
    try {
      await resolveInvestigation(caseId, { resolution: 'ACCP', details: 'Resolved via demo UI' })
      load()
    } catch (err) {
      alert(err.message)
    }
  }

  return (
    <div>
      <div className="page-header">
        <h2>Investigations</h2>
        <p>camt.026-029, camt.055-056 exception handling &mdash; {total} cases</p>
      </div>

      <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Embedded Arrays:</strong> Each investigation contains its full message chain
          embedded as an array. Resolving a case uses atomic <code>$push</code> to append the resolution
          message and <code>$set</code> to update status &mdash; all in one operation.
        </p>
      </div>

      <div className="card">
        {loading ? (
          <div className="loading">Loading investigations...</div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Case ID</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Original UETR</th>
                  <th>Reason</th>
                  <th>Initiator</th>
                  <th>Created</th>
                  <th>Messages</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {investigations.map(inv => (
                  <tr key={inv.caseId}>
                    <td style={{ fontFamily: 'monospace', fontSize: 11, fontWeight: 600 }}>{inv.caseId?.slice(0, 20)}...</td>
                    <td><span className="badge badge-purple">{inv.messageType}</span></td>
                    <td><StatusBadge status={inv.status} /></td>
                    <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{inv.originalUetr?.slice(0, 8)}...</td>
                    <td style={{ fontSize: 12 }}>{inv.reasonDescription || inv.reason}</td>
                    <td>{inv.initiator?.bic}</td>
                    <td>{formatDate(inv.createdAt)}</td>
                    <td>{inv.messages?.length || 0}</td>
                    <td>
                      {inv.status === 'OPEN' && (
                        <button className="btn btn-sm btn-primary" onClick={() => handleResolve(inv.caseId)}>
                          Resolve
                        </button>
                      )}
                    </td>
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
