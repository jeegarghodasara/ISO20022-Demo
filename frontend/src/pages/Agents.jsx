import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  Brain, Route, Shield, AlertTriangle, GitCompare, Send,
  Database, Clock, ChevronDown, ChevronRight, Sparkles, History,
  ThumbsUp, ThumbsDown, Activity, FileText, Layers
} from 'lucide-react'
import {
  askAgent, getAgentMemories, getMemoryStats, getAgentConversations,
  getAgentMetrics, submitFeedback, getToolLogs, triggerConsolidation
} from '../services/api'
import { useAgentContext } from '../context/AgentContext'
import StatusBadge from '../components/StatusBadge'
import MessageTypeBadge from '../components/MessageTypeBadge'

const ICON_MAP = {
  Route, Shield, AlertTriangle, GitCompare, Brain,
}

const SAMPLE_QUESTIONS = [
  { q: "What's the best route for this payment?", agent: "orchestrator" },
  { q: "Screen this payment for compliance risks", agent: "orchestrator" },
  { q: "Why did this payment fail? How do I fix it?", agent: "orchestrator" },
  { q: "Run a full analysis with all agents", agent: "orchestrator" },
  { q: "Match this payment to an invoice", agent: "orchestrator" },
]

function AgentCard({ agent, onClick, selected }) {
  const Icon = ICON_MAP[agent.icon] || Database
  return (
    <div
      onClick={() => onClick(agent.agentId)}
      className="value-prop-card"
      style={{
        cursor: 'pointer',
        borderColor: selected ? agent.color : undefined,
        background: selected ? `${agent.color}15` : undefined,
        padding: 16,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
        <div style={{
          width: 36, height: 36, borderRadius: 'var(--radius)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: `${agent.color}20`, color: agent.color,
        }}>
          <Icon size={18} />
        </div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 700 }}>{agent.name}</div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{agent.agentId}</div>
        </div>
      </div>
      <p style={{ fontSize: 11, color: 'var(--text-secondary)', marginBottom: 8 }}>{agent.description}</p>
      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-muted)' }}>
        <span><strong style={{ color: agent.color }}>{agent.memoryCount}</strong> memories</span>
        <span><strong style={{ color: agent.color }}>{agent.messageCount}</strong> messages</span>
      </div>
    </div>
  )
}

function AgentResultPanel({ result }) {
  const [expandedAgent, setExpandedAgent] = useState(null)
  if (!result) return null

  const r = result.result || {}
  const agentResults = r.agentResults || {}
  const hasSubAgents = Object.keys(agentResults).length > 0

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Sparkles size={16} style={{ color: 'var(--accent)' }} />
        <span style={{ fontSize: 14, fontWeight: 700 }}>{r.decision}</span>
      </div>

      {/* Reasoning steps */}
      {r.reasoning && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Reasoning
          </div>
          {r.reasoning.map((step, i) => (
            <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0', display: 'flex', gap: 8 }}>
              <span style={{ color: 'var(--accent)', fontWeight: 600, minWidth: 16 }}>{i + 1}.</span>
              {step}
            </div>
          ))}
        </div>
      )}

      {/* Sub-agent results */}
      {hasSubAgents && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 700, marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Agent Results
          </div>
          {Object.entries(agentResults).map(([agentId, agentResult]) => {
            const isExpanded = expandedAgent === agentId
            const color = agentResult.agent ? ({ 'routing-agent': '#00ED64', 'compliance-agent': '#016BF8', 'exception-agent': '#FFC010', 'reconciliation-agent': '#B45AF2' }[agentId] || 'var(--text-muted)') : 'var(--text-muted)'
            return (
              <div key={agentId} style={{
                background: 'var(--bg-primary)', border: `1px solid ${isExpanded ? color : 'var(--border-subtle)'}`,
                borderRadius: 'var(--radius)', marginBottom: 8, overflow: 'hidden',
              }}>
                <div
                  onClick={() => setExpandedAgent(isExpanded ? null : agentId)}
                  style={{ padding: '10px 14px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}
                >
                  {isExpanded ? <ChevronDown size={12} style={{ color }} /> : <ChevronRight size={12} style={{ color }} />}
                  <span style={{ fontSize: 12, fontWeight: 700, color }}>{agentId}</span>
                  <span style={{ fontSize: 12, color: 'var(--text-secondary)', flex: 1 }}>{agentResult.decision}</span>
                  {agentResult.memoriesUsed > 0 && (
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>{agentResult.memoriesUsed} memories used</span>
                  )}
                </div>
                {isExpanded && (
                  <div style={{ padding: '0 14px 14px', borderTop: `1px solid var(--border-subtle)` }}>
                    {/* Reasoning */}
                    {agentResult.reasoning && (
                      <div style={{ marginTop: 10 }}>
                        {agentResult.reasoning.map((step, i) => (
                          <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', padding: '2px 0' }}>
                            {step}
                          </div>
                        ))}
                      </div>
                    )}
                    {/* Type-specific data */}
                    {agentResult.recommendation && (
                      <div style={{ marginTop: 10, padding: 10, background: 'var(--bg-card)', borderRadius: 'var(--radius)' }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color }}>Recommended: {agentResult.recommendation.method}</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Speed: {agentResult.recommendation.speed} | Cost: {agentResult.recommendation.cost} | Confidence: {(agentResult.recommendation.confidence * 100).toFixed(0)}%</div>
                      </div>
                    )}
                    {agentResult.riskFactors && agentResult.riskFactors.length > 0 && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color, marginBottom: 4 }}>Risk Factors</div>
                        {agentResult.riskFactors.map((f, i) => (
                          <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'flex', justifyContent: 'space-between', padding: '2px 0' }}>
                            <span>{f.factor}: {f.detail}</span>
                            <span style={{ color: f.weight > 0 ? 'var(--red)' : 'var(--accent)', fontWeight: 600 }}>{f.weight > 0 ? '+' : ''}{f.weight}</span>
                          </div>
                        ))}
                      </div>
                    )}
                    {agentResult.recommendedActions && (
                      <div style={{ marginTop: 10 }}>
                        <div style={{ fontSize: 11, fontWeight: 600, color, marginBottom: 4 }}>Recommended Actions</div>
                        {agentResult.recommendedActions.map((a, i) => (
                          <div key={i} style={{ fontSize: 11, color: 'var(--text-secondary)', padding: '2px 0', display: 'flex', gap: 8 }}>
                            <span className={`badge ${a.priority === 'HIGH' ? 'badge-red' : 'badge-blue'}`} style={{ fontSize: 9 }}>{a.priority}</span>
                            {a.action}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* MongoDB pipeline info */}
      <div style={{ marginTop: 12, padding: '8px 12px', background: 'var(--accent-bg)', borderRadius: 'var(--radius)', fontSize: 11, color: 'var(--accent)' }}>
        <strong>MongoDB Features Used:</strong> Vector Search (memory recall) + Aggregation (pattern analysis) + Polymorphic Documents (memory types) + TTL Indexes (memory decay)
      </div>
    </div>
  )
}

function MemoryInspector({ agentId, agentColor }) {
  const [memories, setMemories] = useState([])
  const [memoryType, setMemoryType] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!agentId) return
    setLoading(true)
    getAgentMemories(agentId, memoryType || undefined)
      .then(res => setMemories(res.memories || []))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [agentId, memoryType])

  if (!agentId) return null

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
        <h4 style={{ fontSize: 14, fontWeight: 700 }}>
          <Database size={14} style={{ color: agentColor, marginRight: 6, verticalAlign: 'middle' }} />
          Memory Inspector — {agentId}
        </h4>
        <div style={{ display: 'flex', gap: 4 }}>
          {['', 'episodic', 'semantic', 'procedural'].map(t => (
            <button key={t} className="btn btn-sm" onClick={() => setMemoryType(t)}
              style={memoryType === t ? { borderColor: agentColor, color: agentColor } : {}}
            >
              {t || 'All'}
            </button>
          ))}
        </div>
      </div>

      {loading ? <div className="loading">Loading memories...</div> : (
        memories.length === 0 ? (
          <div className="empty-state" style={{ padding: 24 }}><p>No memories yet. Ask the agent a question to create episodic memories.</p></div>
        ) : (
          <div>
            {memories.map((m, i) => (
              <div key={i} style={{
                padding: '10px 12px', marginBottom: 6,
                background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius)', fontSize: 12,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span className={`badge ${m.memoryType === 'episodic' ? 'badge-success' : m.memoryType === 'semantic' ? 'badge-blue' : 'badge-purple'}`} style={{ fontSize: 9 }}>
                    {m.memoryType}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                    <Clock size={10} style={{ verticalAlign: 'middle', marginRight: 2 }} />
                    {new Date(m.createdAt).toLocaleString()}
                  </span>
                  <span style={{ fontSize: 10, color: 'var(--text-muted)', marginLeft: 'auto' }}>
                    accessed {m.accessCount}x
                  </span>
                </div>
                <div style={{ color: 'var(--text-secondary)' }}>{m.content}</div>
                {m.context && Object.keys(m.context).length > 0 && (
                  <div style={{ marginTop: 4, fontSize: 10, color: 'var(--text-muted)' }}>
                    Context: {JSON.stringify(m.context).slice(0, 120)}{JSON.stringify(m.context).length > 120 ? '...' : ''}
                  </div>
                )}
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}

function FeedbackButtons({ conversationId, turnNumber, existingFeedback }) {
  const [feedback, setFeedback] = useState(existingFeedback?.rating || null)
  const [submitting, setSubmitting] = useState(false)

  const handleFeedback = async (rating) => {
    setSubmitting(true)
    try {
      await submitFeedback({ conversationId, turnNumber, rating })
      setFeedback(rating)
    } catch (e) {
      console.error(e)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 4, paddingLeft: 4 }}>
      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Helpful?</span>
      <button
        onClick={() => handleFeedback('up')}
        disabled={submitting || feedback === 'up'}
        style={{
          background: feedback === 'up' ? 'var(--accent-bg)' : 'transparent',
          border: `1px solid ${feedback === 'up' ? 'var(--accent)' : 'var(--border-subtle)'}`,
          borderRadius: 4, padding: '2px 6px', cursor: 'pointer',
          color: feedback === 'up' ? 'var(--accent)' : 'var(--text-muted)',
          display: 'flex', alignItems: 'center', gap: 3, fontSize: 11,
        }}
      >
        <ThumbsUp size={11} />
      </button>
      <button
        onClick={() => handleFeedback('down')}
        disabled={submitting || feedback === 'down'}
        style={{
          background: feedback === 'down' ? 'var(--red-bg)' : 'transparent',
          border: `1px solid ${feedback === 'down' ? 'var(--red)' : 'var(--border-subtle)'}`,
          borderRadius: 4, padding: '2px 6px', cursor: 'pointer',
          color: feedback === 'down' ? 'var(--red)' : 'var(--text-muted)',
          display: 'flex', alignItems: 'center', gap: 3, fontSize: 11,
        }}
      >
        <ThumbsDown size={11} />
      </button>
      {feedback && <span style={{ fontSize: 10, color: feedback === 'up' ? 'var(--accent)' : 'var(--red)' }}>Recorded</span>}
    </div>
  )
}

function MetricsPanel() {
  const [metrics, setMetrics] = useState(null)
  const [toolLogs, setToolLogs] = useState(null)
  const [consolidating, setConsolidating] = useState(false)
  const [consolidationResult, setConsolidationResult] = useState(null)
  const [activeSection, setActiveSection] = useState('metrics')

  useEffect(() => {
    getAgentMetrics().then(setMetrics).catch(console.error)
    getToolLogs(null, 20).then(res => setToolLogs(res.logs)).catch(console.error)
  }, [])

  const handleConsolidate = async () => {
    setConsolidating(true)
    try {
      const result = await triggerConsolidation()
      setConsolidationResult(result)
    } catch (e) {
      console.error(e)
    } finally {
      setConsolidating(false)
    }
  }

  return (
    <div className="card" style={{ marginTop: 16 }}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 14 }}>
        {[
          { id: 'metrics', label: 'Performance', icon: Activity },
          { id: 'tools', label: 'Tool Logs', icon: FileText },
          { id: 'consolidation', label: 'Memory Consolidation', icon: Layers },
        ].map(s => {
          const Icon = s.icon
          return (
            <button key={s.id} className="btn btn-sm" onClick={() => setActiveSection(s.id)}
              style={activeSection === s.id ? { borderColor: 'var(--accent)', color: 'var(--accent)' } : {}}
            >
              <Icon size={12} /> {s.label}
            </button>
          )
        })}
      </div>

      {/* Performance Metrics */}
      {activeSection === 'metrics' && metrics && (
        <div>
          {metrics.overall && (
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 14 }}>
              <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius)', padding: '8px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--accent)' }}>{metrics.overall.totalInvocations || 0}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Total Invocations</div>
              </div>
              <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius)', padding: '8px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--blue)' }}>{(metrics.overall.avgLatencyMs || 0).toFixed(0)}ms</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Avg Latency</div>
              </div>
              <div style={{ background: 'var(--bg-primary)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius)', padding: '8px 16px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: 'var(--purple)' }}>{metrics.overall.totalMemoriesUsed || 0}</div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>Memories Used</div>
              </div>
            </div>
          )}
          {metrics.perAgent && metrics.perAgent.length > 0 && (
            <div className="table-container">
              <table>
                <thead><tr><th>Agent</th><th>Invocations</th><th>Avg Latency</th><th>Max Latency</th><th>Memories Used</th><th>Success</th><th>Errors</th></tr></thead>
                <tbody>
                  {metrics.perAgent.map((m, i) => (
                    <tr key={i}>
                      <td style={{ fontWeight: 600 }}>{m._id}</td>
                      <td>{m.totalInvocations}</td>
                      <td>{(m.avgLatencyMs || 0).toFixed(0)}ms</td>
                      <td>{(m.maxLatencyMs || 0).toFixed(0)}ms</td>
                      <td>{m.totalMemoriesUsed}</td>
                      <td style={{ color: 'var(--accent)' }}>{m.successCount}</td>
                      <td style={{ color: m.errorCount > 0 ? 'var(--red)' : 'var(--text-muted)' }}>{m.errorCount}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tool Call Logs */}
      {activeSection === 'tools' && toolLogs && (
        <div>
          <div style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 10, padding: '6px 10px', background: 'var(--accent-bg)', borderRadius: 'var(--radius)' }}>
            <strong>Audit Trail:</strong> Every database operation (vector search, aggregation, find) executed by agents is logged for compliance.
          </div>
          {toolLogs.length === 0 ? (
            <div className="empty-state" style={{ padding: 24 }}><p>No tool calls logged yet. Ask an agent a question first.</p></div>
          ) : (
            <div className="table-container">
              <table>
                <thead><tr><th>Time</th><th>Agent</th><th>Tool</th><th>Input</th><th>Output</th><th>Latency</th></tr></thead>
                <tbody>
                  {toolLogs.map((log, i) => (
                    <tr key={i}>
                      <td style={{ fontSize: 10, whiteSpace: 'nowrap' }}>{log.timestamp ? new Date(log.timestamp).toLocaleTimeString('en-GB') : ''}</td>
                      <td style={{ fontSize: 11 }}>{log.agentId}</td>
                      <td><span className="badge badge-blue" style={{ fontSize: 9 }}>{log.toolName}</span></td>
                      <td style={{ fontSize: 10, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>{JSON.stringify(log.toolInput).slice(0, 60)}</td>
                      <td style={{ fontSize: 10 }}>{log.outputSummary}</td>
                      <td style={{ fontSize: 11, fontFamily: 'var(--font-code)' }}>{log.latencyMs ? `${log.latencyMs.toFixed(0)}ms` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Memory Consolidation */}
      {activeSection === 'consolidation' && (
        <div>
          <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.6 }}>
            Memory consolidation distills episodic memories into permanent semantic knowledge —
            like how the brain consolidates during sleep. MongoDB aggregation pipelines group
            episodic memories by corridor, risk level, and reason code to produce summarized knowledge.
          </p>
          <button className="btn btn-primary" onClick={handleConsolidate} disabled={consolidating}>
            <Layers size={14} /> {consolidating ? 'Consolidating...' : 'Run Consolidation'}
          </button>
          {consolidationResult && (
            <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-primary)', borderRadius: 'var(--radius)', border: '1px solid var(--accent)' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--accent)', marginBottom: 6 }}>
                Consolidation complete — {consolidationResult.totalSemanticMemoriesCreated} semantic memories created
              </div>
              <pre style={{ fontSize: 11, fontFamily: 'var(--font-code)', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', margin: 0 }}>
                {JSON.stringify(consolidationResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Agents() {
  const {
    agents, loading, refreshAgents,
    selectedAgent, setSelectedAgent,
    question, setQuestion,
    uetr, setUetr,
    result, setResult,
    error, setError,
    showMemory, setShowMemory,
    loadConversation, conversationHistory,
    // Multi-turn
    activeConversationId, turns, conversationFull, sizeBytes,
    addTurn, startNewConversation,
  } = useAgentContext()

  const [asking, setAsking] = useState(false)

  const handleAsk = async (e) => {
    e?.preventDefault()
    if (!question.trim()) return
    setAsking(true)
    setError(null)
    try {
      const data = await askAgent({
        question,
        uetr: uetr || undefined,
        agentId: selectedAgent || 'orchestrator',
        conversationId: activeConversationId || undefined,
      })
      if (data.conversationFull && !data.result) {
        // Conversation hit the limit before processing
        setError(`Conversation reached the 10KB limit (${(data.sizeBytes / 1024).toFixed(1)}KB). Please start a new conversation.`)
      } else {
        addTurn(data)
        setQuestion('')
      }
      refreshAgents()
    } catch (err) {
      setError(err.message)
    } finally {
      setAsking(false)
    }
  }

  const handleSample = (q) => {
    setQuestion(q)
  }

  const sizePercent = sizeBytes > 0 ? Math.min(100, (sizeBytes / 10240) * 100) : 0

  if (loading) return <div className="loading">Loading agents...</div>

  const selectedInfo = agents.find(a => a.agentId === selectedAgent)

  return (
    <div>
      <div className="page-header">
        <h2 style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Brain size={24} style={{ color: 'var(--accent)' }} />
          AI Payment Agents
        </h2>
        <p>Multi-agent architecture with persistent MongoDB-backed memory</p>
      </div>

      <div className="card" style={{ marginBottom: 16, borderColor: 'var(--accent)', background: 'var(--accent-bg)' }}>
        <p style={{ fontSize: 13, color: 'var(--accent)' }}>
          <strong>MongoDB Multi-Agent Architecture:</strong> Five specialized agents collaborate to handle payment operations.
          Each agent has persistent memory stored in MongoDB (episodic + semantic + procedural), uses Vector Search for
          memory retrieval, and communicates via Change Streams. No external infrastructure needed &mdash;
          MongoDB is the memory store, vector database, and message bus.
        </p>
      </div>

      {/* Agent cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(230px, 1fr))', gap: 12, marginBottom: 20 }}>
        {agents.map(agent => (
          <AgentCard
            key={agent.agentId}
            agent={agent}
            onClick={(id) => {
              setSelectedAgent(id === selectedAgent ? null : id)
              setShowMemory(null)
            }}
            selected={selectedAgent === agent.agentId}
          />
        ))}
      </div>

      {/* Ask an Agent */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
          <Send size={16} style={{ color: 'var(--accent)' }} />
          Ask an Agent
          {selectedAgent && (
            <span style={{ fontSize: 12, fontWeight: 500, color: selectedInfo?.color || 'var(--text-muted)' }}>
              &mdash; {selectedInfo?.name || selectedAgent}
            </span>
          )}
        </h4>

        <form onSubmit={handleAsk}>
          <div className="grid-2" style={{ marginBottom: 12 }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Question</label>
              <input
                type="text" value={question} onChange={e => setQuestion(e.target.value)}
                placeholder="e.g., What's the best route for this payment?"
              />
            </div>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Payment UETR (optional)</label>
              <input
                type="text" value={uetr} onChange={e => setUetr(e.target.value)}
                placeholder="Paste a UETR to give the agents payment context"
                style={{ fontFamily: 'var(--font-code)', fontSize: 12 }}
              />
            </div>
          </div>

          {/* Sample questions */}
          <div style={{ marginBottom: 12 }}>
            <span style={{ fontSize: 11, color: 'var(--text-muted)', marginRight: 8 }}>Try:</span>
            {SAMPLE_QUESTIONS.map(s => (
              <button key={s.q} type="button" onClick={() => handleSample(s.q)}
                style={{
                  fontSize: 11, padding: '3px 8px', margin: '2px 4px 2px 0',
                  borderRadius: 12, border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-primary)', color: 'var(--text-secondary)', cursor: 'pointer',
                }}
              >
                {s.q}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button type="submit" className="btn btn-primary" disabled={asking || !question.trim() || conversationFull}>
              <Send size={14} /> {asking ? 'Agents working...' : turns.length > 0 ? `Follow-up (Turn ${turns.length + 1})` : 'Ask'}
            </button>
            {turns.length > 0 && (
              <button type="button" className="btn btn-sm" onClick={startNewConversation}>
                New Conversation
              </button>
            )}
          </div>

          {/* Conversation size indicator */}
          {turns.length > 0 && (
            <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 10 }}>
              <span>Turn {turns.length} | {(sizeBytes / 1024).toFixed(1)}KB / 10KB</span>
              <div style={{ flex: 1, maxWidth: 200, height: 4, background: 'var(--border-subtle)', borderRadius: 2, overflow: 'hidden' }}>
                <div style={{
                  width: `${sizePercent}%`, height: '100%', borderRadius: 2,
                  background: sizePercent > 80 ? 'var(--red)' : sizePercent > 50 ? 'var(--orange)' : 'var(--accent)',
                  transition: 'width 0.3s',
                }} />
              </div>
              {conversationFull && (
                <span style={{ color: 'var(--red)', fontWeight: 600 }}>Limit reached — start a new conversation</span>
              )}
            </div>
          )}
        </form>
      </div>

      {/* Conversation full prompt */}
      {conversationFull && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--orange)', background: 'var(--orange-bg)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <p style={{ fontSize: 13, color: 'var(--orange)' }}>
              This conversation has reached the 10KB document size limit ({turns.length} turns, {(sizeBytes / 1024).toFixed(1)}KB).
              Start a new conversation to continue.
            </p>
            <button className="btn btn-sm" onClick={startNewConversation} style={{ borderColor: 'var(--orange)', color: 'var(--orange)', whiteSpace: 'nowrap' }}>
              New Conversation
            </button>
          </div>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="card" style={{ marginBottom: 16, borderColor: 'var(--red)', background: 'var(--red-bg)' }}>
          <p style={{ fontSize: 13, color: 'var(--red)' }}>{error}</p>
        </div>
      )}

      {/* Multi-turn conversation thread */}
      {turns.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          {turns.map((turn, i) => (
            <div key={i} style={{ marginBottom: 12 }}>
              {/* User question */}
              <div style={{
                display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 6,
                padding: '10px 14px', background: 'var(--bg-primary)', borderRadius: 'var(--radius)',
                border: '1px solid var(--border-subtle)',
              }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--blue)', minWidth: 48 }}>Turn {turn.turnNumber}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{turn.question}</div>
                  {turn.uetr && <div style={{ fontSize: 10, fontFamily: 'var(--font-code)', color: 'var(--text-muted)', marginTop: 2 }}>UETR: {turn.uetr.slice(0, 16)}...</div>}
                </div>
                <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                  {turn.timestamp ? new Date(turn.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : ''}
                </span>
              </div>
              {/* Agent result */}
              <AgentResultPanel result={{ result: turn.result }} />
              {/* Feedback buttons */}
              {activeConversationId && (
                <FeedbackButtons
                  conversationId={activeConversationId}
                  turnNumber={turn.turnNumber}
                  existingFeedback={turn.feedback}
                />
              )}
            </div>
          ))}
        </div>
      )}

      {/* Single result (for loaded past conversations with old format) */}
      {turns.length === 0 && result && (
        <AgentResultPanel result={result} />
      )}

      {/* Memory Inspector toggle */}
      {selectedAgent && (
        <div style={{ marginTop: 16 }}>
          <button
            className="btn btn-sm"
            onClick={() => setShowMemory(showMemory ? null : selectedAgent)}
            style={showMemory ? { borderColor: selectedInfo?.color, color: selectedInfo?.color } : {}}
          >
            <Database size={12} /> {showMemory ? 'Hide' : 'View'} Memory Inspector
          </button>
        </div>
      )}

      <MemoryInspector
        agentId={showMemory}
        agentColor={selectedInfo?.color || 'var(--accent)'}
      />

      {/* Metrics, Tool Logs, Consolidation */}
      <MetricsPanel />

      {/* Conversation History — loaded from MongoDB */}
      {conversationHistory.length > 0 && (
        <div className="card" style={{ marginTop: 16 }}>
          <h4 style={{ fontSize: 14, fontWeight: 700, marginBottom: 12, display: 'flex', alignItems: 'center', gap: 8 }}>
            <History size={16} style={{ color: 'var(--blue)' }} />
            Conversation History
            <span style={{ fontSize: 11, fontWeight: 400, color: 'var(--text-muted)' }}>
              {conversationHistory.length} conversations stored in MongoDB
            </span>
          </h4>
          <div style={{ fontSize: 11, color: 'var(--accent)', marginBottom: 12, padding: '6px 10px', background: 'var(--accent-bg)', borderRadius: 'var(--radius)' }}>
            <strong>MongoDB Value Prop:</strong> Multi-turn conversations stored as growing documents with atomic $push.
            Each conversation is one document with a turns[] array — full context in a single read. 10KB limit per conversation.
          </div>
          <div>
            {conversationHistory.map((conv, i) => {
              const isActive = activeConversationId === conv.conversationId
              const turnCount = conv.turns?.length || 1
              const convSize = conv.sizeBytes || 0
              const firstQuestion = conv.turns?.[0]?.question || conv.lastQuestion || conv.question || ''
              return (
                <div
                  key={conv.conversationId || i}
                  onClick={() => loadConversation(conv)}
                  style={{
                    padding: '10px 12px', marginBottom: 4, cursor: 'pointer',
                    background: isActive ? 'var(--accent-bg)' : 'var(--bg-primary)',
                    border: `1px solid ${isActive ? 'var(--accent)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius)', transition: 'border-color 0.15s',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                    <span className="badge badge-blue" style={{ fontSize: 9, minWidth: 'fit-content' }}>
                      {turnCount} {turnCount === 1 ? 'turn' : 'turns'}
                    </span>
                    <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', flex: 1 }}>
                      {firstQuestion}
                    </span>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>
                      {conv.createdAt ? new Date(conv.createdAt).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }) : ''}
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {convSize > 0 && (
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                        {(convSize / 1024).toFixed(1)}KB
                      </span>
                    )}
                    {conv.lastQuestion && turnCount > 1 && (
                      <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        Latest: {conv.lastQuestion}
                      </span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
