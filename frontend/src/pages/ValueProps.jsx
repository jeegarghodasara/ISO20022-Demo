import { useEffect, useState } from 'react'
import {
  FileText, Layers, BarChart3, ShieldCheck, Zap, Calculator, Clock, Database
} from 'lucide-react'
import { getValuePropsSummary, getValueProp } from '../services/api'

const iconMap = {
  FileText, Layers, BarChart3, ShieldCheck, Zap, Calculator, Clock, Database,
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
    const slug = name.toLowerCase().replace(/\s+/g, '-')
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

          {detail.equivalentSQL && detail.mongoQuery && (
            <div className="comparison">
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

          {detail.exampleOperation && (
            <div className="comparison">
              <div>
                <div className="code-label mongo">MongoDB</div>
                <div className="code-block mongodb">{detail.exampleOperation.mongoCommand}</div>
              </div>
              <div>
                <div className="code-label sql">SQL Equivalent</div>
                <div className="code-block">{detail.exampleOperation.equivalentSQL}</div>
              </div>
            </div>
          )}

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

          {detail.collections && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Collection TTL Policies</h4>
              <div className="table-container">
                <table>
                  <thead><tr><th>Collection</th><th>TTL</th><th>Reason</th></tr></thead>
                  <tbody>
                    {Object.entries(detail.collections).map(([name, info]) => (
                      <tr key={name}>
                        <td style={{ fontFamily: 'monospace', fontWeight: 600 }}>{name}</td>
                        <td>{info.ttl}</td>
                        <td style={{ fontSize: 12 }}>{info.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {detail.example && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Precision Example</h4>
              <div className="grid-2">
                <div className="code-block" style={{ borderColor: 'var(--red)' }}>
                  <div style={{ color: 'var(--red)', fontWeight: 600, marginBottom: 4 }}>Floating Point</div>
                  {detail.example.floatingPoint}
                </div>
                <div className="code-block mongodb">
                  <div style={{ color: 'var(--accent)', fontWeight: 600, marginBottom: 4 }}>Decimal128</div>
                  {detail.example.decimal128}
                </div>
              </div>
            </div>
          )}

          {detail.results && (
            <div style={{ marginTop: 16 }}>
              <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 8 }}>Live Aggregation Results</h4>
              <div className="code-block mongodb" style={{ maxHeight: 300, overflow: 'auto' }}>
                {JSON.stringify(detail.results, null, 2)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
