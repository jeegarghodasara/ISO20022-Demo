import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, RefreshCw, Radio, RotateCcw } from 'lucide-react'
import { getPayment, updatePaymentStatus } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import MessageTypeBadge, { MESSAGE_TYPE_LABELS } from '../components/MessageTypeBadge'
import usePaymentStream from '../hooks/usePaymentStream'

function formatDate(d) {
  if (!d) return '-'
  return new Date(d).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function formatAmount(val, currency) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return `${currency || ''} ${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function PaymentDetail() {
  const { uetr } = useParams()
  const [payment, setPayment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(false)

  // Change Stream: watch for updates to THIS specific payment
  const { connected, lastEvent } = usePaymentStream({
    filter: (event) => {
      const eventUetr = event.payment?.uetr || event.originalUetr
      return eventUetr === uetr
    },
  })

  const load = () => {
    setLoading(true)
    getPayment(uetr)
      .then(setPayment)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [uetr])

  // Auto-reload when a Change Stream event arrives for this payment
  useEffect(() => {
    if (lastEvent && !loading) {
      load()
    }
  }, [lastEvent])

  const handleStatusUpdate = async (newStatus) => {
    setUpdating(true)
    try {
      await updatePaymentStatus(uetr, { status: newStatus })
      load()
    } catch (err) {
      alert(err.message)
    } finally {
      setUpdating(false)
    }
  }

  if (loading) return <div className="loading">Loading payment details...</div>
  if (!payment) return <div className="empty-state"><p>Payment not found</p></div>

  const p = payment
  const typeLabel = MESSAGE_TYPE_LABELS[p.messageType] || p.messageType

  return (
    <div>
      <div className="page-header">
        <Link to="/payments" style={{ fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 8 }}>
          <ArrowLeft size={14} /> Back to payments
        </Link>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          Payment {p.uetr?.slice(0, 8)}...
          <StatusBadge status={p.status} />
          <MessageTypeBadge type={p.messageType} />
        </h2>
        <p>{typeLabel} | Message ID: {p.messageId}</p>
      </div>

      {/* Return detection banner — shown when a pacs.004 return has been linked */}
      {p.returnedBy && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--orange)', background: 'var(--orange-bg)' }}>
          <p style={{ fontSize: 13, color: 'var(--orange)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <RotateCcw size={16} />
            <strong>Return Detected:</strong> This payment has been returned.
            <Link to={`/payments/${p.returnedBy}`} style={{ fontFamily: 'var(--font-code)', fontSize: 12, color: 'var(--orange)' }}>
              View return {p.returnedBy?.slice(0, 12)}...
            </Link>
          </p>
        </div>
      )}

      {/* MongoDB Value Prop callout */}
      <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Polymorphic Document Model:</strong> This <strong>{typeLabel}</strong> ({p.messageType}) document
          contains both shared fields and type-specific data in a single read.
          {p.messageType === 'pacs.004' && ' The return reason and original payment reference are embedded directly.'}
          {p.messageType === 'pacs.009' && ' The instructing/instructed agent details are specific to bank-to-bank transfers.'}
          {p.messageType === 'pain.001' && ' The initiating party and transaction count fields are unique to payment initiations.'}
          {p.messageType === 'pain.008' && ' The mandate and sequence type fields are specific to direct debits.'}
          {' '}In a relational database, this would require JOINs across shared + type-specific tables.
        </p>
      </div>

      <div className="detail-grid">
        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="detail-section">
              <h4>Payment Identification</h4>
              <div className="detail-row"><span className="label">UETR</span><span className="value" style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.uetr}</span></div>
              <div className="detail-row"><span className="label">End-to-End ID</span><span className="value">{p.endToEndId}</span></div>
              <div className="detail-row"><span className="label">Transaction ID</span><span className="value">{p.txId}</span></div>
              <div className="detail-row"><span className="label">Instruction ID</span><span className="value">{p.instrId}</span></div>
              <div className="detail-row"><span className="label">Payment Type</span><span className="value"><MessageTypeBadge type={p.messageType} /></span></div>
            </div>
          </div>

          <div className="card" style={{ marginBottom: 16 }}>
            <div className="detail-section">
              <h4>Settlement</h4>
              <div className="detail-row"><span className="label">Amount</span><span className="value amount">{formatAmount(p.settlementAmount, p.settlementCurrency)}</span></div>
              <div className="detail-row"><span className="label">Settlement Date</span><span className="value">{formatDate(p.settlementDate)}</span></div>
              {p.settlementMethod && <div className="detail-row"><span className="label">Method</span><span className="value">{p.settlementMethod}</span></div>}
              {p.chargeBearer && <div className="detail-row"><span className="label">Charge Bearer</span><span className="value">{p.chargeBearer}</span></div>}
              {p.exchangeRate && p.exchangeRate !== 1 && (
                <div className="detail-row"><span className="label">Exchange Rate</span><span className="value">{p.exchangeRate}</span></div>
              )}
            </div>
          </div>

          {/* pacs.004 - Return-specific section */}
          {p.messageType === 'pacs.004' && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--orange)' }}>
              <div className="detail-section">
                <h4 style={{ color: 'var(--orange)' }}>Return Details</h4>
                {p.originalUetr && (
                  <div className="detail-row">
                    <span className="label">Original UETR</span>
                    <span className="value">
                      <Link to={`/payments/${p.originalUetr}`} style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.originalUetr}</Link>
                    </span>
                  </div>
                )}
                {p.returnReason && (
                  <>
                    <div className="detail-row"><span className="label">Reason Code</span><span className="value"><span className="badge badge-orange">{p.returnReason.code}</span></span></div>
                    {p.returnReason.description && <div className="detail-row"><span className="label">Description</span><span className="value">{p.returnReason.description}</span></div>}
                  </>
                )}
                {p.originalPaymentRef && (
                  <>
                    <div className="detail-row"><span className="label">Original Amount</span><span className="value amount">{formatAmount(p.originalPaymentRef.settlementAmount, p.originalPaymentRef.settlementCurrency)}</span></div>
                    <div className="detail-row"><span className="label">Original Type</span><span className="value">{MESSAGE_TYPE_LABELS[p.originalPaymentRef.messageType] || p.originalPaymentRef.messageType}</span></div>
                  </>
                )}
              </div>
            </div>
          )}

          {/* pain.001 - Initiation-specific section */}
          {p.messageType === 'pain.001' && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--purple)' }}>
              <div className="detail-section">
                <h4 style={{ color: 'var(--purple)' }}>Initiation Details</h4>
                {p.initiatingParty && (
                  <>
                    <div className="detail-row"><span className="label">Initiating Party</span><span className="value">{p.initiatingParty.name}</span></div>
                    {p.initiatingParty.id?.orgId?.bic && <div className="detail-row"><span className="label">Party BIC</span><span className="value">{p.initiatingParty.id.orgId.bic}</span></div>}
                  </>
                )}
                <div className="detail-row"><span className="label">Transactions</span><span className="value">{p.numberOfTransactions}</span></div>
                {p.controlSum && <div className="detail-row"><span className="label">Control Sum</span><span className="value amount">{formatAmount(p.controlSum, p.settlementCurrency)}</span></div>}
                {p.requestedExecutionDate && <div className="detail-row"><span className="label">Requested Execution</span><span className="value">{formatDate(p.requestedExecutionDate)}</span></div>}
              </div>
            </div>
          )}

          {/* pain.008 - Direct Debit-specific section */}
          {p.messageType === 'pain.008' && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--teal)' }}>
              <div className="detail-section">
                <h4 style={{ color: 'var(--teal)' }}>Direct Debit Details</h4>
                {p.mandateId && <div className="detail-row"><span className="label">Mandate ID</span><span className="value">{p.mandateId}</span></div>}
                {p.creditorSchemeId && <div className="detail-row"><span className="label">Creditor Scheme ID</span><span className="value">{p.creditorSchemeId}</span></div>}
                {p.sequenceType && <div className="detail-row"><span className="label">Sequence Type</span><span className="value"><span className="badge badge-teal">{p.sequenceType === 'FRST' ? 'First' : p.sequenceType === 'RCUR' ? 'Recurring' : p.sequenceType === 'FNAL' ? 'Final' : 'One-Off'}</span></span></div>}
                {p.requestedCollectionDate && <div className="detail-row"><span className="label">Collection Date</span><span className="value">{formatDate(p.requestedCollectionDate)}</span></div>}
              </div>
            </div>
          )}

          <div className="card" style={{ marginBottom: 16 }}>
            <div className="detail-section">
              <h4>{p.messageType === 'pacs.009' ? 'Ordering Institution' : p.messageType === 'pain.008' ? 'Debtor (Payer)' : 'Debtor'}</h4>
              <div className="detail-row"><span className="label">Name</span><span className="value">{p.debtor?.name}</span></div>
              <div className="detail-row"><span className="label">IBAN</span><span className="value" style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.debtor?.account?.iban}</span></div>
              {p.debtor?.address?.country && <div className="detail-row"><span className="label">Country</span><span className="value">{p.debtor?.address?.country}</span></div>}
              <div className="detail-row"><span className="label">Agent BIC</span><span className="value">{p.debtorAgent?.bic}</span></div>
            </div>
          </div>

          <div className="card">
            <div className="detail-section">
              <h4>{p.messageType === 'pacs.009' ? 'Beneficiary Institution' : p.messageType === 'pain.008' ? 'Creditor (Collector)' : 'Creditor'}</h4>
              <div className="detail-row"><span className="label">Name</span><span className="value">{p.creditor?.name}</span></div>
              <div className="detail-row"><span className="label">IBAN</span><span className="value" style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.creditor?.account?.iban}</span></div>
              {p.creditor?.address?.country && <div className="detail-row"><span className="label">Country</span><span className="value">{p.creditor?.address?.country}</span></div>}
              <div className="detail-row"><span className="label">Agent BIC</span><span className="value">{p.creditorAgent?.bic}</span></div>
            </div>
          </div>
        </div>

        <div>
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="detail-section">
              <h4 style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  Status History
                  {connected && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--accent)', fontWeight: 600, textTransform: 'none', letterSpacing: 0 }}>
                      <Radio size={10} style={{ animation: 'pulse 2s infinite' }} /> Live
                    </span>
                  )}
                </span>
                <button className="btn btn-sm" onClick={load} disabled={updating}><RefreshCw size={12} /> Refresh</button>
              </h4>
              <div style={{ marginBottom: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {['ACSP', 'ACSC', 'RJCT'].map(s => (
                  <button key={s} className="btn btn-sm" onClick={() => handleStatusUpdate(s)} disabled={updating || p.status === s}>
                    Set {s}
                  </button>
                ))}
              </div>
              <ul className="timeline">
                {(p.statusHistory || []).map((h, i) => (
                  <li key={i} className="timeline-item">
                    <div className="timeline-dot" />
                    <div className="timeline-content">
                      <div className="timeline-status"><StatusBadge status={h.status} /></div>
                      <div className="timeline-time">{formatDate(h.timestamp)}</div>
                      {h.reason && <div style={{ fontSize: 12, color: 'var(--red)', marginTop: 2 }}>Reason: {h.reason}</div>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          {/* pacs.009 - Instructing/Instructed agents */}
          {p.messageType === 'pacs.009' && (p.instructingAgent?.bic || p.instructedAgent?.bic) && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--blue)' }}>
              <div className="detail-section">
                <h4 style={{ color: 'var(--blue)' }}>Agent Chain</h4>
                {p.instructingAgent?.bic && <div className="detail-row"><span className="label">Instructing Agent</span><span className="value">{p.instructingAgent.bic}</span></div>}
                {p.instructedAgent?.bic && <div className="detail-row"><span className="label">Instructed Agent</span><span className="value">{p.instructedAgent.bic}</span></div>}
                {p.intermediaryAgent1?.bic && <div className="detail-row"><span className="label">Intermediary Agent</span><span className="value">{p.intermediaryAgent1.bic}</span></div>}
              </div>
            </div>
          )}

          {p.remittanceDetails && p.remittanceDetails.length > 0 && (
            <div className="card" style={{ marginBottom: 16 }}>
              <div className="detail-section">
                <h4>Remittance Details</h4>
                <p style={{ fontSize: 12, color: 'var(--accent)', marginBottom: 12 }}>
                  Stored in separate collection to handle unbounded data (MongoDB anti-pattern prevention)
                </p>
                <div className="table-container">
                  <table>
                    <thead>
                      <tr><th>Type</th><th>Document #</th><th>Amount</th><th>Date</th></tr>
                    </thead>
                    <tbody>
                      {p.remittanceDetails.map((r, i) => (
                        <tr key={i}>
                          <td><span className="badge badge-blue">{r.documentType}</span></td>
                          <td>{r.documentNumber}</td>
                          <td className="amount">{formatAmount(r.remittedAmt, r.currency)}</td>
                          <td>{formatDate(r.relatedDate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          <div className="card">
            <div className="detail-section">
              <h4>Remittance Summary</h4>
              <div className="detail-row"><span className="label">Type</span><span className="value">{p.remittanceSummary?.type}</span></div>
              <div className="detail-row"><span className="label">Documents</span><span className="value">{p.remittanceSummary?.documentCount}</span></div>
              {p.remittanceSummary?.unstructuredText && (
                <div className="detail-row"><span className="label">Text</span><span className="value">{p.remittanceSummary.unstructuredText}</span></div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
