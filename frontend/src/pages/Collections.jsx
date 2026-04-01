import { useState, useEffect } from 'react'
import { Database, ChevronDown, ChevronRight, Search as SearchIcon, Shield, Key, Radar } from 'lucide-react'
import { getCollections, getCollectionDetail } from '../services/api'

const TYPE_COLORS = {
  'pacs.008': 'var(--accent)',
  'pacs.009': 'var(--blue)',
  'pacs.004': 'var(--orange)',
  'pain.001': 'var(--purple)',
  'pain.008': 'var(--teal)',
}

function IsoTypeBadge({ type }) {
  const color = TYPE_COLORS[type] || 'var(--text-muted)'
  return (
    <span style={{
      fontSize: 10, padding: '2px 6px', borderRadius: 10,
      background: `${color}20`, color, fontWeight: 600, marginRight: 4,
    }}>
      {type}
    </span>
  )
}

function SchemaTree({ schema, depth = 0 }) {
  if (!schema || typeof schema !== 'object') return null
  return (
    <div style={{ paddingLeft: depth > 0 ? 16 : 0 }}>
      {Object.entries(schema).map(([key, value]) => {
        const isNested = typeof value === 'object' && value !== null
        return (
          <div key={key} style={{ marginBottom: 3 }}>
            <span style={{ fontFamily: 'monospace', fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>{key}</span>
            {isNested ? (
              <>
                <span style={{ fontSize: 11, color: 'var(--text-muted)', marginLeft: 6 }}>Object</span>
                <SchemaTree schema={value} depth={depth + 1} />
              </>
            ) : (
              <span style={{ fontSize: 11, color: 'var(--blue)', marginLeft: 8 }}>{value}</span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function IndexCard({ index, isVector }) {
  const [expanded, setExpanded] = useState(false)
  const icon = isVector ? <Radar size={14} style={{ color: 'var(--purple)' }} /> : <Key size={14} style={{ color: 'var(--orange)' }} />
  const borderColor = isVector ? 'var(--purple)' : 'var(--border)'

  return (
    <div style={{
      background: 'var(--bg-primary)', border: `1px solid ${borderColor}`,
      borderRadius: 'var(--radius)', padding: 12, marginBottom: 8,
    }}>
      <div
        onClick={() => setExpanded(!expanded)}
        style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}
      >
        {expanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        {icon}
        <span style={{ fontFamily: 'monospace', fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
          {index.name}
        </span>
        {isVector && (
          <span className="badge badge-purple" style={{ fontSize: 9 }}>Vector</span>
        )}
        {!isVector && index.unique && (
          <span className="badge badge-orange" style={{ fontSize: 9 }}>Unique</span>
        )}
        {!isVector && index.expireAfterSeconds != null && (
          <span className="badge badge-teal" style={{ fontSize: 9 }}>TTL: {index.expireAfterSeconds}s</span>
        )}
        {isVector && index.queryable && (
          <span className="badge badge-success" style={{ fontSize: 9 }}>Queryable</span>
        )}
        {isVector && !index.queryable && (
          <span className="badge badge-orange" style={{ fontSize: 9 }}>{index.status}</span>
        )}
      </div>
      {expanded && (
        <div style={{ marginTop: 10, paddingLeft: 28 }}>
          {!isVector && (
            <pre style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', padding: 10,
              fontSize: 11, lineHeight: 1.5, overflow: 'auto', maxHeight: 300,
              fontFamily: "'SF Mono', 'Fira Code', monospace",
              color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0,
            }}>
              {JSON.stringify({
                key: index.key,
                ...(index.unique ? { unique: true } : {}),
                ...(index.sparse ? { sparse: true } : {}),
                ...(index.expireAfterSeconds != null ? { expireAfterSeconds: index.expireAfterSeconds } : {}),
              }, null, 2)}
            </pre>
          )}
          {isVector && index.latestDefinition && (
            <pre style={{
              background: 'var(--bg-card)', border: '1px solid var(--border)',
              borderRadius: 'var(--radius)', padding: 10,
              fontSize: 11, lineHeight: 1.5, overflow: 'auto', maxHeight: 300,
              fontFamily: "'SF Mono', 'Fira Code', monospace",
              color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0,
            }}>
              {JSON.stringify(index.latestDefinition, null, 2)}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export default function Collections() {
  const [collections, setCollections] = useState([])
  const [loading, setLoading] = useState(true)
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    getCollections()
      .then(res => setCollections(res.collections))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const loadDetail = async (name) => {
    setSelected(name)
    setDetailLoading(true)
    setDetail(null)
    try {
      const data = await getCollectionDetail(name)
      setDetail(data)
    } catch (err) {
      console.error(err)
    } finally {
      setDetailLoading(false)
    }
  }

  if (loading) return <div className="loading">Loading collections...</div>

  return (
    <div>
      <div className="page-header">
        <h2>Collection Explorer</h2>
        <p>Browse MongoDB collections, schemas, and indexes for the ISO 20022 payment system</p>
      </div>

      <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Flexible Schema:</strong> Each collection stores documents with different shapes.
          Click any collection to inspect its schema (inferred from a sample document), regular indexes,
          and Atlas Vector Search indexes.
        </p>
      </div>

      {/* Collection Tiles */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 12, marginBottom: 24 }}>
        {collections.map(coll => (
          <div
            key={coll.name}
            className="value-prop-card"
            onClick={() => loadDetail(coll.name)}
            style={{
              cursor: 'pointer',
              borderColor: selected === coll.name ? 'var(--accent)' : undefined,
              background: selected === coll.name ? 'var(--accent-bg)' : undefined,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
              <Database size={16} style={{ color: 'var(--accent)' }} />
              <span style={{ fontFamily: 'monospace', fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>
                {coll.name}
              </span>
            </div>
            <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent)', marginBottom: 4 }}>
              {coll.documentCount.toLocaleString()}
              <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 4 }}>docs</span>
            </div>
            {coll.description && (
              <p style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, lineHeight: 1.4 }}>{coll.description}</p>
            )}
            {coll.isoTypes.length > 0 && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
                {coll.isoTypes.map(t => <IsoTypeBadge key={t} type={t} />)}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Detail Panel */}
      {detailLoading && <div className="loading">Loading collection details...</div>}

      {detail && !detailLoading && (
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <Database size={20} style={{ color: 'var(--accent)' }} />
            <h3 style={{ fontSize: 18, fontFamily: 'monospace' }}>{detail.name}</h3>
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{detail.documentCount.toLocaleString()} documents</span>
          </div>

          {detail.description && (
            <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>{detail.description}</p>
          )}

          {/* Schema Validation badge */}
          {detail.validator && (
            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '6px 12px', borderRadius: 'var(--radius)',
              background: 'var(--accent-bg)', border: '1px solid var(--accent)',
              fontSize: 12, color: 'var(--accent)', fontWeight: 600, marginBottom: 16,
            }}>
              <Shield size={14} />
              Schema Validation: {detail.validationLevel} / {detail.validationAction}
            </div>
          )}

          <div className="detail-grid">
            <div>
              {/* Schema Shape */}
              <div style={{ marginBottom: 20 }}>
                <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Document Schema
                </h4>
                <div style={{
                  background: 'var(--bg-primary)', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)', padding: 14,
                }}>
                  <SchemaTree schema={detail.schemaShape} />
                </div>
              </div>

              {/* Sample Document */}
              {detail.sampleDocument && (
                <div>
                  <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Sample Document
                  </h4>
                  <pre style={{
                    background: 'var(--bg-primary)', border: '1px solid var(--border)',
                    borderRadius: 'var(--radius)', padding: 14,
                    fontSize: 11, lineHeight: 1.5, overflow: 'auto', maxHeight: 400,
                    fontFamily: "'SF Mono', 'Fira Code', monospace",
                    color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0,
                  }}>
                    {JSON.stringify(detail.sampleDocument, null, 2)}
                  </pre>
                </div>
              )}
            </div>

            <div>
              {/* Regular Indexes */}
              <div style={{ marginBottom: 20 }}>
                <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  Regular Indexes ({detail.regularIndexes.length})
                </h4>
                {detail.regularIndexes.map((idx, i) => (
                  <IndexCard key={i} index={idx} isVector={false} />
                ))}
              </div>

              {/* Vector / Search Indexes */}
              {detail.searchIndexes.length > 0 && (
                <div>
                  <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Atlas Search / Vector Indexes ({detail.searchIndexes.length})
                  </h4>
                  {detail.searchIndexes.map((idx, i) => (
                    <IndexCard key={i} index={idx} isVector={true} />
                  ))}
                </div>
              )}

              {/* Schema Validator */}
              {detail.validator && (
                <div style={{ marginTop: 20 }}>
                  <h4 style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Schema Validator
                  </h4>
                  <pre style={{
                    background: 'var(--bg-primary)', border: '1px solid var(--accent)',
                    borderRadius: 'var(--radius)', padding: 14,
                    fontSize: 11, lineHeight: 1.5, overflow: 'auto', maxHeight: 400,
                    fontFamily: "'SF Mono', 'Fira Code', monospace",
                    color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0,
                  }}>
                    {JSON.stringify(detail.validator, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
