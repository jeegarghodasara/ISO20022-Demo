import { useEffect, useState } from 'react'
import {
  FileText, Layers, BarChart3, ShieldCheck, Zap, Calculator, Clock, Database, Brain
} from 'lucide-react'
import { getValuePropsSummary, getValueProp } from '../services/api'

const iconMap = {
  FileText, Layers, BarChart3, ShieldCheck, Zap, Calculator, Clock, Database, Brain,
}

const TYPE_COLORS = {
  'pacs.008': 'var(--accent)',
  'pacs.009': 'var(--blue)',
  'pacs.004': 'var(--orange)',
  'pain.001': 'var(--purple)',
  'pain.008': 'var(--teal)',
}

function JsonBlock({ data, label, color, highlight }) {
  if (!data) return null
  const json = typeof data === 'string' ? data : JSON.stringify(data, null, 2)

  // Highlight type-specific fields if provided
  let rendered = json
  if (highlight && highlight.length > 0) {
    const lines = json.split('\n')
    rendered = lines.map(line => {
      const isHighlighted = highlight.some(field => line.includes(`"${field}"`))
      if (isHighlighted) {
        return `>>> ${line}`
      }
      return `    ${line}`
    }).join('\n')
  }

  return (
    <div style={{ marginBottom: 12 }}>
      {label && (
        <div style={{
          fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
          letterSpacing: '0.5px', marginBottom: 6, padding: '4px 8px',
          borderRadius: 4, display: 'inline-block',
          background: color ? `${color}20` : 'var(--accent-bg)',
          color: color || 'var(--accent)',
        }}>
          {label}
        </div>
      )}
      <pre style={{
        background: 'var(--bg-primary)', border: `1px solid ${color || 'var(--border)'}`,
        borderRadius: 'var(--radius)', padding: 14,
        fontSize: 11.5, lineHeight: 1.55, overflow: 'auto', maxHeight: 400,
        fontFamily: "'SF Mono', 'Fira Code', monospace",
        color: 'var(--text-secondary)', whiteSpace: 'pre-wrap',
      }}>
        {highlight ? rendered : json}
      </pre>
    </div>
  )
}

function PolymorphicSamples({ samples, typeSpecificFields }) {
  const [selectedTypes, setSelectedTypes] = useState([])
  const entries = Object.entries(samples || {}).filter(([, v]) => v)

  useEffect(() => {
    // Default: select first two types that have data
    if (entries.length >= 2) {
      setSelectedTypes([entries[0][0], entries[1][0]])
    } else if (entries.length === 1) {
      setSelectedTypes([entries[0][0]])
    }
  }, [samples])

  const toggleType = (label) => {
    setSelectedTypes(prev =>
      prev.includes(label)
        ? prev.filter(t => t !== label)
        : prev.length < 3
          ? [...prev, label]
          : [prev[1], prev[2], label]  // drop oldest, keep last 2 + new
    )
  }

  // Extract messageType code from label like "pacs.008 - Customer Credit Transfer"
  const getTypeCode = (label) => label.split(' - ')[0]

  return (
    <div style={{ marginTop: 16 }}>
      <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
        Live Documents from the Same Collection (select to compare)
      </h4>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 14 }}>
        {entries.map(([label]) => {
          const typeCode = getTypeCode(label)
          const color = TYPE_COLORS[typeCode] || 'var(--text-muted)'
          const isSelected = selectedTypes.includes(label)
          return (
            <button
              key={label}
              onClick={() => toggleType(label)}
              style={{
                padding: '6px 12px', borderRadius: 'var(--radius)', fontSize: 12,
                fontWeight: 600, cursor: 'pointer', transition: 'all 0.15s',
                border: `2px solid ${isSelected ? color : 'var(--border)'}`,
                background: isSelected ? `${color}20` : 'var(--bg-card)',
                color: isSelected ? color : 'var(--text-secondary)',
              }}
            >
              {label}
            </button>
          )
        })}
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: selectedTypes.length > 1 ? `repeat(${Math.min(selectedTypes.length, 3)}, 1fr)` : '1fr',
        gap: 12,
      }}>
        {selectedTypes.map(label => {
          const typeCode = getTypeCode(label)
          const color = TYPE_COLORS[typeCode] || 'var(--accent)'
          const specifics = typeSpecificFields?.[typeCode] || []
          return (
            <div key={label}>
              <JsonBlock
                data={samples[label]}
                label={label}
                color={color}
                highlight={specifics}
              />
              {specifics.length > 0 && (
                <div style={{ fontSize: 11, color, marginTop: -6 }}>
                  {'>>>'} = type-specific fields (not present on other types)
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function ValueProps() {
  const [summary, setSummary] = useState(null)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getValuePropsSummary()
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const loadDetail = async (name) => {
    const vpList = summary?.valuePropositions || []
    const vp = vpList.find(v => v.name === name)
    if (!vp) return
    const endpoint = vp.endpoint.replace('/api/value-props/', '')
    try {
      const data = await getValueProp(endpoint)
      setDetail(data)
      setSelected(name)
    } catch (err) {
      console.error(err)
    }
  }

  if (loading) return <div className="loading">Loading value propositions...</div>

  return (
    <div>
      <div className="page-header">
        <h2>MongoDB Value Propositions</h2>
        <p>Why MongoDB is the ideal database for ISO 20022 global payment systems</p>
      </div>

      <div className="grid-3" style={{ marginBottom: 24 }}>
        {(summary?.valuePropositions || []).map(vp => {
          const Icon = iconMap[vp.icon] || Database
          return (
            <div
              key={vp.name}
              className="value-prop-card"
              onClick={() => loadDetail(vp.name)}
              style={selected === vp.name ? { borderColor: 'var(--accent)' } : {}}
            >
              <div className="vp-icon"><Icon size={24} /></div>
              <h3>{vp.name}</h3>
              <p>{vp.summary}</p>
            </div>
          )
        })}
      </div>

      {detail && (
        <div className="card vp-detail">
          <h3 style={{ marginBottom: 8, fontSize: 18 }}>{detail.title}</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, lineHeight: 1.7, marginBottom: 16 }}>
            {detail.description}
          </p>

          {detail.benefit && (
            <div style={{ background: 'var(--accent-bg)', border: '1px solid var(--accent)', borderRadius: 'var(--radius)', padding: 16, marginBottom: 16 }}>
              <p style={{ fontSize: 13, color: 'var(--accent)', lineHeight: 1.6 }}>
                <strong>Benefit:</strong> {detail.benefit}
              </p>
            </div>
          )}

          {/* Document Model: sample document */}
          {detail.sampleDocument && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                Complete Payment Document (single read, zero JOINs)
              </h4>
              <JsonBlock
                data={detail.sampleDocument}
                label="db.payments.findOne()"
                color="var(--accent)"
              />
            </div>
          )}

          {/* Flexible Schema: polymorphic samples side-by-side */}
          {detail.samples && (
            <PolymorphicSamples
              samples={detail.samples}
              typeSpecificFields={detail.typeSpecificFields}
            />
          )}

          {/* Flexible Schema: type distribution */}
          {detail.typeDistribution && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                Type Distribution in payments Collection
              </h4>
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {Object.entries(detail.typeDistribution).map(([type, count]) => (
                  <div key={type} style={{
                    background: 'var(--bg-primary)', border: `1px solid ${TYPE_COLORS[type] || 'var(--border)'}`,
                    borderRadius: 'var(--radius)', padding: '10px 16px', textAlign: 'center', minWidth: 120,
                  }}>
                    <div style={{ fontSize: 22, fontWeight: 700, color: TYPE_COLORS[type] || 'var(--text-primary)' }}>{count}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{type}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Flexible Schema: common vs type-specific fields */}
          {detail.commonFields && detail.typeSpecificFields && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                Shared vs Type-Specific Fields
              </h4>
              <div className="grid-2">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginBottom: 8 }}>
                    Shared Fields (all types)
                  </div>
                  <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                    {detail.commonFields.map(f => (
                      <span key={f} className="badge badge-success" style={{ fontSize: 10 }}>{f}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--orange)', marginBottom: 8 }}>
                    Type-Specific Fields
                  </div>
                  {Object.entries(detail.typeSpecificFields).map(([type, fields]) => (
                    <div key={type} style={{ marginBottom: 6 }}>
                      <span style={{ fontSize: 11, fontWeight: 600, color: TYPE_COLORS[type] || 'var(--text-muted)', marginRight: 6 }}>{type}:</span>
                      {fields.map(f => (
                        <span key={f} className="badge" style={{ fontSize: 10, marginRight: 3, background: `${TYPE_COLORS[type]}20`, color: TYPE_COLORS[type] }}>{f}</span>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Flexible Schema: relational alternative */}
          {detail.relationalAlternative && detail.relationalAlternative.tables && (
            <div style={{ marginTop: 16, background: 'var(--red-bg)', border: '1px solid var(--red)', borderRadius: 'var(--radius)', padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--red)', marginBottom: 8 }}>
                Relational Alternative: {detail.relationalAlternative.approach}
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 8 }}>
                {detail.relationalAlternative.tables.map(t => (
                  <span key={t} className="badge badge-red" style={{ fontSize: 10 }}>{t}</span>
                ))}
              </div>
              <p style={{ fontSize: 12, color: 'var(--red)' }}>{detail.relationalAlternative.problem}</p>
            </div>
          )}

          {/* Code comparison: MongoDB vs SQL */}
          {detail.equivalentSQL && detail.mongoQuery && (
            <div className="comparison" style={{ marginTop: 16 }}>
              <div>
                <div className="code-label mongo">MongoDB</div>
                <div className="code-block mongodb">{detail.mongoQuery}</div>
              </div>
              <div>
                <div className="code-label sql">SQL Equivalent</div>
                <div className="code-block">{detail.equivalentSQL}</div>
              </div>
            </div>
          )}

          {/* Atomic Operations: example + live history */}
          {detail.exampleOperation && (
            <>
              <div className="comparison" style={{ marginTop: 16 }}>
                <div>
                  <div className="code-label mongo">MongoDB (one atomic operation)</div>
                  <div className="code-block mongodb">{detail.exampleOperation.mongoCommand}</div>
                </div>
                <div>
                  <div className="code-label sql">SQL (multi-statement transaction)</div>
                  <div className="code-block">{detail.exampleOperation.equivalentSQL}</div>
                </div>
              </div>
              {detail.liveExample?.statusHistory && detail.liveExample.statusHistory.length > 0 && (
                <div style={{ marginTop: 16 }}>
                  <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                    Live Status History (embedded in the document)
                  </h4>
                  <JsonBlock
                    data={detail.liveExample.statusHistory}
                    label={`payment ${detail.liveExample.uetr?.slice(0, 8)}... statusHistory`}
                    color="var(--accent)"
                  />
                </div>
              )}
            </>
          )}

          {/* Relational tables needed */}
          {detail.relationalTablesNeeded && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>
                Relational Tables Needed ({detail.relationalTablesNeeded.length})
              </h4>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {detail.relationalTablesNeeded.map(t => (
                  <span key={t} className="badge badge-red">{t}</span>
                ))}
              </div>
              <p style={{ marginTop: 8, fontSize: 13, color: 'var(--text-secondary)' }}>
                vs <strong style={{ color: 'var(--accent)' }}>{detail.mongodbCollections} MongoDB collection</strong>
              </p>
            </div>
          )}

          {/* Schema Validation: actual validator JSON */}
          {detail.validator && typeof detail.validator === 'object' && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                Collection Validator Rule
              </h4>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                This JSON Schema is applied to the <strong style={{ color: 'var(--accent)' }}>payments</strong> collection
                via <code style={{ fontSize: 11, background: 'var(--bg-primary)', padding: '2px 6px', borderRadius: 4 }}>
                db.createCollection("payments", {'{'} validator: ... {'}'})</code>. MongoDB validates every insert and update against these rules.
              </p>
              <pre style={{
                background: 'var(--bg-primary)',
                border: '1px solid var(--accent)',
                borderRadius: 'var(--radius)',
                padding: 16,
                fontSize: 11.5,
                lineHeight: 1.55,
                overflow: 'auto',
                maxHeight: 500,
                fontFamily: "'SF Mono', 'Fira Code', monospace",
                color: 'var(--text-secondary)',
                whiteSpace: 'pre-wrap',
                margin: 0,
              }}>
                <span style={{ color: 'var(--text-muted)' }}>{'// db.runCommand({ collMod: "payments", validator: ... })\n\n'}</span>
                {JSON.stringify(detail.validator, null, 2)}
              </pre>
            </div>
          )}

          {/* Schema Validation: validated fields */}
          {detail.validatedFields && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Validated Fields</h4>
              <div className="table-container">
                <table>
                  <thead><tr><th>Field</th><th>Validation Rule</th></tr></thead>
                  <tbody>
                    {Object.entries(detail.validatedFields).map(([field, rule]) => (
                      <tr key={field}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{field}</td>
                        <td style={{ fontSize: 12 }}>{rule}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* TTL: collection policies */}
          {detail.collections && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Collection TTL Policies</h4>
              <div className="table-container">
                <table>
                  <thead><tr><th>Collection</th><th>TTL</th><th>Reason</th><th>Current Docs</th></tr></thead>
                  <tbody>
                    {Object.entries(detail.collections).map(([name, info]) => (
                      <tr key={name}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{name}</td>
                        <td>{info.ttl}</td>
                        <td style={{ fontSize: 12 }}>{info.reason}</td>
                        <td>{info.currentCount !== undefined ? info.currentCount : '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Decimal128: precision example */}
          {detail.example && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Precision Comparison</h4>
              <div className="grid-2">
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--red)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    {'✗'} Incorrect — Floating Point (IEEE 754 binary64)
                  </div>
                  <div className="code-block" style={{ borderColor: 'var(--red)' }}>
                    {detail.example.floatingPoint}
                  </div>
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--accent)', marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    {'✓'} Correct — Decimal128 (IEEE 754-2008)
                  </div>
                  <div className="code-block mongodb">
                    {detail.example.decimal128}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Decimal128: live amounts from DB */}
          {detail.liveAmounts && detail.liveAmounts.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Live Decimal128 Amounts from Database</h4>
              <div className="table-container">
                <table>
                  <thead><tr><th>UETR</th><th>Type</th><th>Amount (Decimal128)</th><th>Currency</th></tr></thead>
                  <tbody>
                    {detail.liveAmounts.map((p, i) => (
                      <tr key={i}>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{p.uetr}...</td>
                        <td><span className="badge badge-blue">{p.messageType}</span></td>
                        <td className="amount" style={{ color: 'var(--accent)' }}>{p.settlementAmount}</td>
                        <td>{p.settlementCurrency}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Aggregation: live results */}
          {detail.results && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Live Aggregation Results</h4>
              <JsonBlock
                data={detail.results}
                label="$facet pipeline output"
                color="var(--accent)"
              />
            </div>
          )}

          {/* Vector Search: coverage stats */}
          {detail.coverage && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>Embedding Coverage</h4>
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
                {[
                  { label: 'Payments Embedded', value: `${detail.coverage.embeddedPayments}/${detail.coverage.totalPayments}`, color: 'var(--accent)' },
                  { label: 'Coverage', value: detail.coverage.coveragePercent, color: 'var(--accent)' },
                  { label: 'Model', value: detail.coverage.model, color: 'var(--purple)' },
                  { label: 'Dimensions', value: detail.coverage.dimensions, color: 'var(--blue)' },
                ].map(s => (
                  <div key={s.label} style={{
                    background: 'var(--bg-primary)', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)', padding: '10px 18px', textAlign: 'center', minWidth: 110,
                  }}>
                    <div style={{ fontSize: 20, fontWeight: 700, color: s.color }}>{s.value}</div>
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>{s.label}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Vector Search: index definitions */}
          {detail.indexes && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>Atlas Vector Search Indexes</h4>
              <div className="grid-2">
                {Object.entries(detail.indexes).map(([name, idx]) => (
                  <div key={name} style={{
                    background: 'var(--bg-primary)', border: '1px solid var(--blue)',
                    borderRadius: 'var(--radius)', padding: 14,
                  }}>
                    <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--blue)', marginBottom: 8, fontFamily: 'monospace' }}>{name}</div>
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>{idx.purpose}</div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      <div>Path: <strong style={{ color: 'var(--text-primary)' }}>{idx.path}</strong></div>
                      <div>Dimensions: <strong style={{ color: 'var(--text-primary)' }}>{idx.dimensions}</strong></div>
                      <div>Similarity: <strong style={{ color: 'var(--text-primary)' }}>{idx.similarity}</strong></div>
                      {idx.filters.length > 0 && (
                        <div style={{ marginTop: 4 }}>
                          Pre-filters: {idx.filters.map(f => (
                            <span key={f} className="badge badge-blue" style={{ fontSize: 9, marginRight: 4 }}>{f}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Vector Search: use cases with example queries */}
          {detail.useCases && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>Use Cases & Example Pipelines</h4>
              {detail.useCases.map((uc, i) => (
                <div key={i} style={{ marginBottom: 12 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {i + 1}. {uc.name}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 6 }}>{uc.description}</div>
                  <pre style={{
                    background: 'var(--bg-primary)', border: '1px solid var(--accent)',
                    borderRadius: 'var(--radius)', padding: 12,
                    fontSize: 11, lineHeight: 1.5, overflow: 'auto',
                    fontFamily: "'SF Mono', 'Fira Code', monospace",
                    color: 'var(--accent)', whiteSpace: 'pre-wrap', margin: 0,
                  }}>
                    {uc.example}
                  </pre>
                </div>
              ))}
            </div>
          )}

          {/* Vector Search: sample embedded texts */}
          {detail.sampleTexts && detail.sampleTexts.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10 }}>
                How Payments Are Embedded (text representations)
              </h4>
              <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 10 }}>
                Each payment document is converted to a text description, then embedded into a 1024-dimensional
                vector using voyage-finance-2. This is what enables semantic similarity search.
              </p>
              <div className="table-container">
                <table>
                  <thead><tr><th>Type</th><th>UETR</th><th>Text Sent to Embedding Model</th></tr></thead>
                  <tbody>
                    {detail.sampleTexts.map((s, i) => (
                      <tr key={i}>
                        <td><span className="badge badge-blue">{s.messageType}</span></td>
                        <td style={{ fontFamily: 'monospace', fontSize: 11 }}>{s.uetr}</td>
                        <td style={{ fontSize: 11, color: 'var(--text-secondary)', maxWidth: 500 }}>{s.embeddingText}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Vector Search: relational alternative */}
          {detail.relationalAlternative && detail.relationalAlternative.problems && (
            <div style={{ marginTop: 16, background: 'var(--orange-bg, rgba(245, 158, 11, 0.08))', border: '1px solid var(--orange)', borderRadius: 'var(--radius)', padding: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--orange)', marginBottom: 8 }}>
                Without MongoDB: {detail.relationalAlternative.approach}
              </div>
              <ul style={{ margin: 0, paddingLeft: 18 }}>
                {detail.relationalAlternative.problems.map((p, i) => (
                  <li key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 4 }}>{p}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
