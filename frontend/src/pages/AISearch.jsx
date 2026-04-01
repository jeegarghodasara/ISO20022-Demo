import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Search, Radar, FileSearch, AlertCircle, Sparkles, Code, ChevronDown, ChevronRight } from 'lucide-react'
import {
  getAISearchStatus,
  naturalLanguageSearch,
  findSimilarTransactions,
  remittanceMatch,
} from '../services/api'
import StatusBadge from '../components/StatusBadge'
import MessageTypeBadge from '../components/MessageTypeBadge'

function formatAmount(val, currency) {
  if (!val && val !== 0) return '-'
  const num = typeof val === 'number' ? val : parseFloat(val)
  return `${currency || ''} ${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function ScoreBadge({ score }) {
  if (!score && score !== 0) return null
  const pct = (score * 100).toFixed(1)
  const color = score > 0.8 ? 'var(--accent)' : score > 0.6 ? 'var(--orange)' : 'var(--text-muted)'
  return (
    <span style={{ fontSize: 11, fontWeight: 700, color, fontFamily: 'monospace' }}>
      {pct}%
    </span>
  )
}

function ResultCard({ payment, showScore }) {
  return (
    <div style={{
      background: 'var(--bg-primary)', border: '1px solid var(--border)',
      borderRadius: 'var(--radius)', padding: 14, marginBottom: 8,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Link to={`/payments/${payment.uetr}`} style={{ fontFamily: 'monospace', fontSize: 12 }}>
            {payment.uetr?.slice(0, 12)}...
          </Link>
          <MessageTypeBadge type={payment.messageType} />
          <StatusBadge status={payment.status} />
        </div>
        {showScore && <ScoreBadge score={payment.score} />}
      </div>
      <div style={{ display: 'flex', gap: 24, fontSize: 13, color: 'var(--text-secondary)' }}>
        <span className="amount" style={{ color: 'var(--accent)' }}>
          {formatAmount(payment.settlementAmount, payment.settlementCurrency)}
        </span>
        <span>{payment.debtor?.name || '-'} &rarr; {payment.creditor?.name || '-'}</span>
      </div>
      {payment.embeddingText && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 6, lineHeight: 1.5, fontStyle: 'italic' }}>
          {payment.embeddingText.slice(0, 200)}{payment.embeddingText.length > 200 ? '...' : ''}
        </div>
      )}
      {payment.remittanceSummary?.unstructuredText && (
        <div style={{ fontSize: 11, color: 'var(--blue)', marginTop: 4 }}>
          Remittance: {payment.remittanceSummary.unstructuredText}
        </div>
      )}
    </div>
  )
}

const TABS = [
  { id: 'natural', label: 'Natural Language Search', icon: Search, color: 'var(--accent)' },
  { id: 'similar', label: 'Similar Transactions', icon: Radar, color: 'var(--orange)' },
  { id: 'remittance', label: 'Remittance Matching', icon: FileSearch, color: 'var(--purple)' },
]

const SAMPLE_QUERIES = {
  natural: [
    'Large EUR transfers to Germany that were rejected',
    'High priority payments from Deutsche Bank',
    'Settled credit transfers over 50000 USD',
    'Payment returns due to closed accounts',
    'Direct debits with recurring mandates',
    'Failed cross-border transfers to UK',
  ],
  remittance: [
    'Invoice 2026-42 from ACME Corporation',
    'Monthly subscription payment for cloud services',
    'Q1 consulting fees',
    'Salary payment January',
    'Office rent payment Berlin',
    'Software license renewal',
  ],
}

function buildPipelinePreview(activeTab, queryText, uetr, resultCount) {
  if (activeTab === 'natural') {
    return {
      description: 'Natural Language → Voyage Finance embedding → $vectorSearch on payment_vector_index',
      pipeline: [
        {
          $vectorSearch: {
            index: 'payment_vector_index',
            path: 'embedding',
            queryVector: `voyage-finance-2("${queryText}") → [float × 1024]`,
            numCandidates: (resultCount || 15) * 20,
            limit: resultCount || 15,
          },
        },
        {
          $project: {
            uetr: 1,
            messageType: 1,
            settlementAmount: 1,
            settlementCurrency: 1,
            status: 1,
            debtor: 1,
            creditor: 1,
            score: { $meta: 'vectorSearchScore' },
          },
        },
      ],
    }
  }
  if (activeTab === 'similar') {
    return {
      description: `Fetch payment ${uetr?.slice(0, 8)}... → use its stored embedding → $vectorSearch for nearest neighbors`,
      pipeline: [
        {
          $vectorSearch: {
            index: 'payment_vector_index',
            path: 'embedding',
            queryVector: `payments.findOne({ uetr: "${uetr?.slice(0, 18)}..." }).embedding → [float × 1024]`,
            numCandidates: (resultCount || 10) * 20,
            limit: (resultCount || 10) + 1,
          },
        },
        {
          $project: {
            uetr: 1,
            messageType: 1,
            settlementAmount: 1,
            status: 1,
            debtor: 1,
            creditor: 1,
            score: { $meta: 'vectorSearchScore' },
          },
        },
      ],
    }
  }
  // remittance
  return {
    description: 'Remittance text → Voyage Finance embedding → $vectorSearch on remittance_vector_index',
    pipeline: [
      {
        $vectorSearch: {
          index: 'remittance_vector_index',
          path: 'remittanceEmbedding',
          queryVector: `voyage-finance-2("${queryText}") → [float × 1024]`,
          numCandidates: (resultCount || 10) * 20,
          limit: resultCount || 10,
        },
      },
      {
        $project: {
          uetr: 1,
          messageType: 1,
          settlementAmount: 1,
          remittanceSummary: 1,
          debtor: 1,
          creditor: 1,
          score: { $meta: 'vectorSearchScore' },
        },
      },
    ],
  }
}

function VectorQueryPreview({ activeTab, queryText, uetr, resultCount }) {
  const [expanded, setExpanded] = useState(true)
  const preview = buildPipelinePreview(activeTab, queryText, uetr, resultCount)

  return (
    <div className="card" style={{ marginBottom: 16, borderColor: 'var(--blue)', background: 'var(--bg-card)' }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', marginBottom: expanded ? 10 : 0 }}
      >
        {expanded ? <ChevronDown size={14} style={{ color: 'var(--blue)' }} /> : <ChevronRight size={14} style={{ color: 'var(--blue)' }} />}
        <Code size={14} style={{ color: 'var(--blue)' }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--blue)' }}>
          MongoDB Vector Search Pipeline
        </span>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 'auto' }}>
          {preview.description}
        </span>
      </div>
      {expanded && (
        <pre style={{
          background: 'var(--bg-primary)',
          border: '1px solid var(--blue)',
          borderRadius: 'var(--radius)',
          padding: 16,
          fontSize: 12,
          lineHeight: 1.6,
          overflow: 'auto',
          maxHeight: 400,
          fontFamily: "'SF Mono', 'Fira Code', monospace",
          color: 'var(--text-secondary)',
          whiteSpace: 'pre-wrap',
          margin: 0,
        }}>
          <span style={{ color: 'var(--text-muted)' }}>{'// Aggregation pipeline sent to MongoDB Atlas\n'}</span>
          <span style={{ color: 'var(--blue)' }}>db.payments.aggregate</span>{'(\n'}
          {JSON.stringify(preview.pipeline, null, 2)
            .replace(/"(\$vectorSearch|\$project|\$meta)"/g, (_, m) => `"${m}"`)
          }
          {'\n)'}
        </pre>
      )}
    </div>
  )
}

export default function AISearch() {
  const [activeTab, setActiveTab] = useState('natural')
  const [status, setStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [uetrInput, setUetrInput] = useState('')
  const [results, setResults] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    getAISearchStatus().then(setStatus).catch(console.error)
  }, [])

  const handleSearch = async (e) => {
    e?.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)

    try {
      let data
      if (activeTab === 'natural') {
        data = await naturalLanguageSearch({ query, limit: 15 })
      } else if (activeTab === 'similar') {
        data = await findSimilarTransactions({ uetr: uetrInput, limit: 10 })
      } else {
        data = await remittanceMatch({ query, limit: 10 })
      }
      setResults(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSampleQuery = (q) => {
    setQuery(q)
    // Auto-search with the sample query
    setLoading(true)
    setError(null)
    setResults(null)
    const fn = activeTab === 'natural' ? naturalLanguageSearch : remittanceMatch
    fn({ query: q, limit: 15 })
      .then(setResults)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }

  return (
    <div>
      <div className="page-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Sparkles size={24} style={{ color: 'var(--accent)' }} />
          AI-Powered Search
        </h2>
        <p>MongoDB Vector Search + Voyage AI embeddings on polymorphic payment data</p>
      </div>

      <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Vector Search:</strong> Every payment document is embedded into a vector representation
          using Voyage AI. MongoDB Atlas Vector Search indexes these embeddings for sub-second semantic similarity
          queries across all polymorphic payment types in a single collection.
        </p>
      </div>

      {/* Status indicator */}
      {status && (
        <div style={{ display: 'flex', gap: 16, marginBottom: 16, fontSize: 12, color: 'var(--text-muted)' }}>
          <span>Model: <strong style={{ color: 'var(--text-primary)' }}>{status.model}</strong></span>
          <span>Dimensions: <strong style={{ color: 'var(--text-primary)' }}>{status.dimensions}</strong></span>
          <span>Embedded: <strong style={{ color: status.ready ? 'var(--accent)' : 'var(--red)' }}>{status.coverage}</strong> ({status.embeddedPayments}/{status.totalPayments})</span>
        </div>
      )}

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 16 }}>
        {TABS.map(tab => {
          const Icon = tab.icon
          const isActive = activeTab === tab.id
          return (
            <button
              key={tab.id}
              onClick={() => { setActiveTab(tab.id); setResults(null); setError(null) }}
              style={{
                padding: '10px 18px', borderRadius: 'var(--radius)', fontSize: 13, fontWeight: 600,
                cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8,
                border: `1px solid ${isActive ? tab.color : 'var(--border)'}`,
                background: isActive ? `${tab.color}20` : 'var(--bg-card)',
                color: isActive ? tab.color : 'var(--text-secondary)',
                transition: 'all 0.15s',
              }}
            >
              <Icon size={16} /> {tab.label}
            </button>
          )
        })}
      </div>

      {/* Search Form */}
      <div className="card" style={{ marginBottom: 16 }}>
        {activeTab === 'similar' ? (
          <>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              Find Similar Transactions
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
              Enter a payment UETR to find structurally similar transactions. Useful for fraud detection and pattern analysis.
            </p>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={uetrInput}
                onChange={e => setUetrInput(e.target.value)}
                placeholder="Enter payment UETR (e.g., 550e8400-e29b-41d4-a716-...)"
                style={{
                  flex: 1, padding: '10px 14px', background: 'var(--bg-primary)',
                  border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                  color: 'var(--text-primary)', fontSize: 13, fontFamily: 'monospace',
                }}
              />
              <button type="submit" className="btn btn-primary" disabled={loading || !uetrInput.trim()}>
                <Radar size={16} /> {loading ? 'Searching...' : 'Find Similar'}
              </button>
            </form>
          </>
        ) : (
          <>
            <h4 style={{ fontSize: 14, fontWeight: 600, marginBottom: 12 }}>
              {activeTab === 'natural' ? 'Describe what you\'re looking for' : 'Enter remittance text to match'}
            </h4>
            <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
              {activeTab === 'natural'
                ? 'Use plain English to search across all payment types. No need to know field names or ISO codes.'
                : 'Paste invoice references, payment descriptions, or partial text. Semantic matching handles typos and abbreviations.'
              }
            </p>
            <form onSubmit={handleSearch} style={{ display: 'flex', gap: 8 }}>
              <input
                type="text"
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder={activeTab === 'natural'
                  ? 'e.g., "large transfers to Germany that failed"'
                  : 'e.g., "Invoice 2026-42 from ACME Corp"'
                }
                style={{
                  flex: 1, padding: '10px 14px', background: 'var(--bg-primary)',
                  border: '1px solid var(--border)', borderRadius: 'var(--radius)',
                  color: 'var(--text-primary)', fontSize: 13,
                }}
              />
              <button type="submit" className="btn btn-primary" disabled={loading || !query.trim()}>
                <Search size={16} /> {loading ? 'Searching...' : 'Search'}
              </button>
            </form>

            {/* Sample queries */}
            <div style={{ marginTop: 12 }}>
              <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 8 }}>Try:</span>
              {(SAMPLE_QUERIES[activeTab] || []).map(q => (
                <button
                  key={q}
                  onClick={() => handleSampleQuery(q)}
                  style={{
                    fontSize: 11, padding: '3px 8px', margin: '2px 4px 2px 0',
                    borderRadius: 12, border: '1px solid var(--border)',
                    background: 'var(--bg-primary)', color: 'var(--text-secondary)',
                    cursor: 'pointer',
                  }}
                >
                  {q}
                </button>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--red)', background: 'var(--red-bg)' }}>
          <p style={{ fontSize: 13, color: 'var(--red)', display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertCircle size={16} /> {error}
          </p>
        </div>
      )}

      {/* Vector Search Pipeline Preview */}
      {results && (
        <VectorQueryPreview
          activeTab={activeTab}
          queryText={activeTab === 'similar' ? null : query}
          uetr={activeTab === 'similar' ? uetrInput : null}
          resultCount={(results.similar || results.results || []).length}
        />
      )}

      {/* Results */}
      {results && (
        <div>
          {/* Similar Transactions: show reference payment */}
          {activeTab === 'similar' && results.reference && (
            <div className="card" style={{ marginBottom: 16, borderColor: 'var(--orange)' }}>
              <h4 style={{ fontSize: 13, color: 'var(--orange)', marginBottom: 10 }}>Reference Payment</h4>
              <ResultCard payment={results.reference} showScore={false} />
            </div>
          )}

          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h4 style={{ fontSize: 14, fontWeight: 600 }}>
                {activeTab === 'similar' ? 'Similar Transactions' : 'Search Results'}
                <span style={{ fontSize: 12, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 8 }}>
                  {results.total || (results.similar || results.results || []).length} found
                </span>
              </h4>
              {results.model && (
                <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                  via {results.model}
                </span>
              )}
            </div>

            {(results.similar || results.results || []).map((p, i) => (
              <ResultCard key={p.uetr || i} payment={p} showScore={true} />
            ))}

            {(results.similar || results.results || []).length === 0 && (
              <div className="empty-state">
                <p>No results found. Try a different query.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
