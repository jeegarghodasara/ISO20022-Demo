import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Send, ArrowRightLeft, Building2, RotateCcw, FileText, CreditCard } from 'lucide-react'
import { createPayment } from '../services/api'

const PAYMENT_TYPES = [
  {
    id: 'pacs.008',
    label: 'Customer Credit Transfer',
    description: 'Send money from one customer to another via their banks (FI-to-FI)',
    icon: ArrowRightLeft,
    color: 'var(--accent)',
    bg: 'var(--accent-bg)',
  },
  {
    id: 'pacs.009',
    label: 'Bank-to-Bank Transfer',
    description: 'Direct transfer between financial institutions (cover payments, liquidity)',
    icon: Building2,
    color: 'var(--blue)',
    bg: 'var(--blue-bg)',
  },
  {
    id: 'pacs.004',
    label: 'Payment Return',
    description: 'Return a previously received payment (wrong beneficiary, account closed)',
    icon: RotateCcw,
    color: 'var(--orange)',
    bg: 'var(--orange-bg)',
  },
  {
    id: 'pain.001',
    label: 'Payment Initiation',
    description: 'Customer instructs their bank to make one or more payments',
    icon: FileText,
    color: 'var(--purple)',
    bg: 'var(--purple-bg)',
  },
  {
    id: 'pain.008',
    label: 'Direct Debit Initiation',
    description: 'Creditor instructs collection of funds from debtor account',
    icon: CreditCard,
    color: 'var(--teal)',
    bg: 'var(--teal-bg)',
  },
]

const TYPE_LABELS = Object.fromEntries(PAYMENT_TYPES.map(t => [t.id, t.label]))

export default function NewPayment() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [selectedType, setSelectedType] = useState(null)
  const [form, setForm] = useState({
    amount: '',
    currency: 'EUR',
    settlementDate: new Date().toISOString().split('T')[0],
    settlementMethod: 'CLRG',
    chargeBearer: 'SHAR',
    priority: 'NORM',
    serviceLevel: 'SEPA',
    purpose: 'SUPP',
    debtorName: '',
    debtorIban: '',
    debtorCountry: 'DE',
    debtorBic: '',
    creditorName: '',
    creditorIban: '',
    creditorCountry: 'GB',
    creditorBic: '',
    remittanceInfo: '',
    // pacs.004 specific
    originalUetr: '',
    returnReasonCode: 'AC04',
    returnReasonDescription: '',
    // pain.001 specific
    numberOfTransactions: '1',
    requestedExecutionDate: new Date().toISOString().split('T')[0],
    initiatingPartyName: '',
    initiatingPartyBic: '',
    // pain.008 specific
    mandateId: '',
    creditorSchemeId: '',
    sequenceType: 'FRST',
  })

  const update = (field) => (e) => setForm({ ...form, [field]: e.target.value })

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const payload = buildPayload()
      const result = await createPayment(payload)
      navigate(`/payments/${result.uetr}`)
    } catch (err) {
      alert('Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const buildPayload = () => {
    const base = {
      messageType: selectedType,
      amount: parseFloat(form.amount),
      currency: form.currency,
      settlementDate: form.settlementDate,
      priority: form.priority,
      remittanceInfo: form.remittanceInfo,
    }

    if (selectedType === 'pacs.008') {
      return {
        ...base,
        settlementMethod: form.settlementMethod,
        chargeBearer: form.chargeBearer,
        serviceLevel: form.serviceLevel,
        purpose: form.purpose,
        debtor: {
          name: form.debtorName,
          address: { country: form.debtorCountry },
          account: { iban: form.debtorIban },
        },
        creditor: {
          name: form.creditorName,
          address: { country: form.creditorCountry },
          account: { iban: form.creditorIban },
        },
        debtorAgent: { bic: form.debtorBic },
        creditorAgent: { bic: form.creditorBic },
      }
    }

    if (selectedType === 'pacs.009') {
      return {
        ...base,
        settlementMethod: form.settlementMethod,
        chargeBearer: form.chargeBearer,
        serviceLevel: form.serviceLevel,
        debtor: {
          name: form.debtorName,
          account: { iban: form.debtorIban },
        },
        creditor: {
          name: form.creditorName,
          account: { iban: form.creditorIban },
        },
        debtorAgent: { bic: form.debtorBic },
        creditorAgent: { bic: form.creditorBic },
        instructingAgent: { bic: form.debtorBic },
        instructedAgent: { bic: form.creditorBic },
      }
    }

    if (selectedType === 'pacs.004') {
      return {
        ...base,
        originalUetr: form.originalUetr,
        returnReason: {
          code: form.returnReasonCode,
          description: form.returnReasonDescription,
        },
        debtor: {
          name: form.debtorName,
          account: { iban: form.debtorIban },
        },
        creditor: {
          name: form.creditorName,
          account: { iban: form.creditorIban },
        },
        debtorAgent: { bic: form.debtorBic },
        creditorAgent: { bic: form.creditorBic },
      }
    }

    if (selectedType === 'pain.001') {
      return {
        ...base,
        requestedExecutionDate: form.requestedExecutionDate,
        numberOfTransactions: parseInt(form.numberOfTransactions),
        initiatingParty: {
          name: form.initiatingPartyName,
          id: { orgId: { bic: form.initiatingPartyBic } },
        },
        debtor: {
          name: form.debtorName,
          account: { iban: form.debtorIban },
        },
        creditor: {
          name: form.creditorName,
          address: { country: form.creditorCountry },
          account: { iban: form.creditorIban },
        },
        debtorAgent: { bic: form.debtorBic },
        creditorAgent: { bic: form.creditorBic },
      }
    }

    if (selectedType === 'pain.008') {
      return {
        ...base,
        mandateId: form.mandateId,
        creditorSchemeId: form.creditorSchemeId,
        sequenceType: form.sequenceType,
        requestedCollectionDate: form.requestedExecutionDate,
        debtor: {
          name: form.debtorName,
          account: { iban: form.debtorIban },
        },
        creditor: {
          name: form.creditorName,
          account: { iban: form.creditorIban },
        },
        debtorAgent: { bic: form.debtorBic },
        creditorAgent: { bic: form.creditorBic },
      }
    }

    return base
  }

  // --- Payment Type Selection Screen ---
  if (!selectedType) {
    return (
      <div>
        <div className="page-header">
          <h2>New Payment</h2>
          <p>Select a payment type to create an ISO 20022 message</p>
        </div>

        <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
          <p style={{ fontSize: 13, color: 'var(--accent)' }}>
            <strong>MongoDB Polymorphic Pattern:</strong> All payment types are stored in a single collection
            with type-specific fields. MongoDB's flexible document model handles the varying structures naturally &mdash;
            no complex table-per-type or sparse columns needed.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 16 }}>
          {PAYMENT_TYPES.map(type => {
            const Icon = type.icon
            return (
              <div
                key={type.id}
                className="value-prop-card"
                onClick={() => setSelectedType(type.id)}
                style={{ cursor: 'pointer' }}
              >
                <div className="vp-icon" style={{ background: type.bg, color: type.color }}>
                  <Icon size={24} />
                </div>
                <h3 style={{ fontSize: 15 }}>{type.label}</h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>{type.id}</p>
                <p>{type.description}</p>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const currentType = PAYMENT_TYPES.find(t => t.id === selectedType)
  const CurrentIcon = currentType.icon

  // --- Payment Form (type-specific) ---
  return (
    <div>
      <div className="page-header">
        <div
          onClick={() => setSelectedType(null)}
          style={{ fontSize: 13, display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 8, cursor: 'pointer', color: 'var(--accent)' }}
        >
          &larr; Change payment type
        </div>
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 36, height: 36, borderRadius: 'var(--radius)', background: currentType.bg, color: currentType.color }}>
            <CurrentIcon size={20} />
          </span>
          New {currentType.label}
        </h2>
        <p>Creating an ISO 20022 <strong>{selectedType}</strong> message</p>
      </div>

      <div className="card" style={{ marginBottom: 20, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Polymorphic Pattern:</strong> This <strong>{selectedType}</strong> document shares the payments
          collection with other message types. Each type stores its own specific fields alongside common ones.
          MongoDB validates the structure while allowing this natural polymorphism &mdash; no ALTER TABLE or migration needed.
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="detail-grid">
          <div>
            {/* Payment Details - common to all types */}
            <div className="card" style={{ marginBottom: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Payment Details</h4>
              <div className="grid-2">
                <div className="form-group">
                  <label>Amount</label>
                  <input type="number" step="0.01" required value={form.amount} onChange={update('amount')} placeholder="10000.00" />
                </div>
                <div className="form-group">
                  <label>Currency</label>
                  <select value={form.currency} onChange={update('currency')}>
                    {['EUR', 'USD', 'GBP', 'JPY', 'AUD', 'CHF', 'CAD'].map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="grid-2">
                <div className="form-group">
                  <label>{selectedType === 'pain.001' ? 'Requested Execution Date' : selectedType === 'pain.008' ? 'Requested Collection Date' : 'Settlement Date'}</label>
                  <input
                    type="date"
                    required
                    value={selectedType === 'pain.001' || selectedType === 'pain.008' ? form.requestedExecutionDate : form.settlementDate}
                    onChange={update(selectedType === 'pain.001' || selectedType === 'pain.008' ? 'requestedExecutionDate' : 'settlementDate')}
                  />
                </div>
                <div className="form-group">
                  <label>Priority</label>
                  <select value={form.priority} onChange={update('priority')}>
                    <option value="NORM">Normal</option>
                    <option value="HIGH">High</option>
                  </select>
                </div>
              </div>
              <div className="form-group">
                <label>Remittance Info</label>
                <input type="text" value={form.remittanceInfo} onChange={update('remittanceInfo')} placeholder="Invoice INV-2026-0042" />
              </div>
            </div>

            {/* pacs.004 - Return specific fields */}
            {selectedType === 'pacs.004' && (
              <div className="card" style={{ marginBottom: 16, borderColor: 'var(--orange)', borderWidth: 1 }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--orange)' }}>Return Details</h4>
                <div className="form-group">
                  <label>Original Payment UETR</label>
                  <input type="text" required value={form.originalUetr} onChange={update('originalUetr')} placeholder="550e8400-e29b-41d4-a716-446655440000" />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Return Reason Code</label>
                    <select value={form.returnReasonCode} onChange={update('returnReasonCode')}>
                      <option value="AC04">AC04 - Account Closed</option>
                      <option value="AC06">AC06 - Account Blocked</option>
                      <option value="AG01">AG01 - Transaction Forbidden</option>
                      <option value="AM05">AM05 - Duplicate Payment</option>
                      <option value="BE04">BE04 - Missing Creditor Address</option>
                      <option value="MD01">MD01 - No Mandate</option>
                      <option value="MS02">MS02 - Refusal by Customer</option>
                      <option value="RC01">RC01 - Invalid BIC</option>
                    </select>
                  </div>
                  <div className="form-group">
                    <label>Reason Description</label>
                    <input type="text" value={form.returnReasonDescription} onChange={update('returnReasonDescription')} placeholder="Beneficiary account has been closed" />
                  </div>
                </div>
              </div>
            )}

            {/* pain.001 - Initiation specific fields */}
            {selectedType === 'pain.001' && (
              <div className="card" style={{ marginBottom: 16, borderColor: 'var(--purple)', borderWidth: 1 }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--purple)' }}>Initiation Details</h4>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Initiating Party Name</label>
                    <input type="text" required value={form.initiatingPartyName} onChange={update('initiatingPartyName')} placeholder="ACME Corp Treasury" />
                  </div>
                  <div className="form-group">
                    <label>Initiating Party BIC</label>
                    <input type="text" required value={form.initiatingPartyBic} onChange={update('initiatingPartyBic')} placeholder="DEUTDEFF" />
                  </div>
                </div>
                <div className="form-group">
                  <label>Number of Transactions</label>
                  <input type="number" min="1" max="100" value={form.numberOfTransactions} onChange={update('numberOfTransactions')} />
                </div>
              </div>
            )}

            {/* pain.008 - Direct Debit specific fields */}
            {selectedType === 'pain.008' && (
              <div className="card" style={{ marginBottom: 16, borderColor: 'var(--teal)', borderWidth: 1 }}>
                <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16, color: 'var(--teal)' }}>Direct Debit Details</h4>
                <div className="form-group">
                  <label>Mandate ID</label>
                  <input type="text" required value={form.mandateId} onChange={update('mandateId')} placeholder="MNDT-2026-00001" />
                </div>
                <div className="grid-2">
                  <div className="form-group">
                    <label>Creditor Scheme ID</label>
                    <input type="text" required value={form.creditorSchemeId} onChange={update('creditorSchemeId')} placeholder="DE98ZZZ09999999999" />
                  </div>
                  <div className="form-group">
                    <label>Sequence Type</label>
                    <select value={form.sequenceType} onChange={update('sequenceType')}>
                      <option value="FRST">First</option>
                      <option value="RCUR">Recurring</option>
                      <option value="FNAL">Final</option>
                      <option value="OOFF">One-Off</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Debtor / Sender */}
            <div className="card">
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>
                {selectedType === 'pain.008' ? 'Debtor (Payer)' : selectedType === 'pacs.009' ? 'Ordering Institution' : 'Debtor (Sender)'}
              </h4>
              <div className="form-group">
                <label>Name</label>
                <input type="text" required value={form.debtorName} onChange={update('debtorName')} placeholder={selectedType === 'pacs.009' ? 'Deutsche Bank AG' : 'John Schmidt'} />
              </div>
              <div className="form-group">
                <label>IBAN</label>
                <input type="text" required value={form.debtorIban} onChange={update('debtorIban')} placeholder="DE89370400440532013000" />
              </div>
              <div className="grid-2">
                {(selectedType === 'pacs.008' || selectedType === 'pain.001') && (
                  <div className="form-group">
                    <label>Country</label>
                    <input type="text" maxLength={2} value={form.debtorCountry} onChange={update('debtorCountry')} />
                  </div>
                )}
                <div className="form-group">
                  <label>Agent BIC</label>
                  <input type="text" required value={form.debtorBic} onChange={update('debtorBic')} placeholder="DEUTDEFF" />
                </div>
              </div>
            </div>
          </div>

          <div>
            {/* Creditor / Receiver */}
            <div className="card" style={{ marginBottom: 16 }}>
              <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>
                {selectedType === 'pain.008' ? 'Creditor (Collector)' : selectedType === 'pacs.009' ? 'Beneficiary Institution' : 'Creditor (Receiver)'}
              </h4>
              <div className="form-group">
                <label>Name</label>
                <input type="text" required value={form.creditorName} onChange={update('creditorName')} placeholder={selectedType === 'pacs.009' ? 'Barclays Bank PLC' : 'Jane Smith'} />
              </div>
              <div className="form-group">
                <label>IBAN</label>
                <input type="text" required value={form.creditorIban} onChange={update('creditorIban')} placeholder="GB29NWBK60161331926819" />
              </div>
              <div className="grid-2">
                {(selectedType === 'pacs.008' || selectedType === 'pain.001') && (
                  <div className="form-group">
                    <label>Country</label>
                    <input type="text" maxLength={2} value={form.creditorCountry} onChange={update('creditorCountry')} />
                  </div>
                )}
                <div className="form-group">
                  <label>Agent BIC</label>
                  <input type="text" required value={form.creditorBic} onChange={update('creditorBic')} placeholder="NWBKGB2L" />
                </div>
              </div>
            </div>

            {/* Polymorphic Schema Preview */}
            <div className="card" style={{ marginBottom: 16, background: 'var(--bg-primary)', border: '1px solid var(--border)' }}>
              <h4 style={{ fontSize: 12, fontWeight: 600, marginBottom: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Document Schema Preview
              </h4>
              <pre style={{ fontSize: 11, color: 'var(--text-secondary)', lineHeight: 1.6, whiteSpace: 'pre-wrap', fontFamily: "'SF Mono', 'Fira Code', monospace" }}>
{`{
  "messageType": "${selectedType}",
  "uetr": "<auto-generated>",
  // -- Common fields --
  "settlementAmount": Decimal128("${form.amount || '0'}"),
  "settlementCurrency": "${form.currency}",
  "status": "ACTC",
  "debtor": { ... },
  "creditor": { ... },`}
{selectedType === 'pacs.004' ? `
  // -- Return-specific fields --
  "originalUetr": "${form.originalUetr || '<reference>'}",
  "returnReason": {
    "code": "${form.returnReasonCode}",
    "description": "..."
  },` : ''}
{selectedType === 'pacs.009' ? `
  // -- Bank Transfer-specific fields --
  "instructingAgent": { "bic": "..." },
  "instructedAgent": { "bic": "..." },` : ''}
{selectedType === 'pain.001' ? `
  // -- Initiation-specific fields --
  "initiatingParty": { "name": "...", "id": { ... } },
  "numberOfTransactions": ${form.numberOfTransactions},
  "requestedExecutionDate": "...",` : ''}
{selectedType === 'pain.008' ? `
  // -- Direct Debit-specific fields --
  "mandateId": "${form.mandateId || '<mandate-ref>'}",
  "creditorSchemeId": "...",
  "sequenceType": "${form.sequenceType}",` : ''}
{`  "statusHistory": [{ ... }]
}`}
              </pre>
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: 14 }} disabled={loading}>
              <Send size={16} />
              {loading ? 'Creating Payment...' : `Submit ${currentType.label}`}
            </button>
          </div>
        </div>
      </form>
    </div>
  )
}
