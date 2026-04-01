import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, CartesianGrid } from 'recharts'
import { TrendingUp, DollarSign, ArrowRightLeft, AlertTriangle, Radio, Code, ChevronDown, ChevronRight } from 'lucide-react'
import { getDashboard, getTopCorridors } from '../services/api'
import usePaymentStream from '../hooks/usePaymentStream'

const COLORS = ['#00ED64', '#016BF8', '#B45AF2', '#FFC010', '#DB3030', '#00A35C', '#ec4899']

const CHART_STYLE = {
  grid: '#3D4F58',
  tick: '#889397',
  tooltip: { background: '#1C2D38', border: '1px solid #3D4F58', borderRadius: 8, fontSize: 12 },
  label: { color: '#FFFFFF' },
}

function formatAmount(val) {
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)}B`
  if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`
  if (val >= 1e3) return `${(val / 1e3).toFixed(1)}K`
  return val?.toFixed(0) || '0'
}

function PipelineToggle({ pipeline, label, description }) {
  const [open, setOpen] = useState(false)
  if (!pipeline) return null

  return (
    <div style={{ marginTop: 8, borderTop: '1px solid var(--border-subtle)', paddingTop: 8 }}>
      <div
        onClick={() => setOpen(!open)}
        style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 11, color: 'var(--blue)' }}
      >
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
        <Code size={12} />
        <span style={{ fontWeight: 600 }}>View Aggregation Pipeline</span>
        {description && !open && (
          <span style={{ color: 'var(--text-muted)', marginLeft: 4 }}>&mdash; {description}</span>
        )}
      </div>
      {open && (
        <pre style={{
          background: 'var(--bg-primary)', border: '1px solid var(--blue)',
          borderRadius: 'var(--radius)', padding: 12, marginTop: 8,
          fontSize: 11, lineHeight: 1.55, overflow: 'auto', maxHeight: 260,
          fontFamily: 'var(--font-code)', color: 'var(--text-secondary)',
          whiteSpace: 'pre-wrap', margin: '8px 0 0 0',
        }}>
          <span style={{ color: 'var(--text-muted)' }}>{'// '}{description}{'\n\n'}</span>
          <span style={{ color: 'var(--blue)' }}>db.payments.aggregate</span>{'(\n'}
          {JSON.stringify(pipeline, null, 2)}
          {'\n)'}
        </pre>
      )}
    </div>
  )
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [corridors, setCorridors] = useState(null)
  const [loading, setLoading] = useState(true)
  const [liveInserts, setLiveInserts] = useState(0)
  const [liveVolume, setLiveVolume] = useState(0)

  const { connected, lastEvent, stats } = usePaymentStream()

  useEffect(() => {
    Promise.all([getDashboard(), getTopCorridors()])
      .then(([d, c]) => { setDashboard(d); setCorridors(c) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  // Increment live counters on each insert event
  useEffect(() => {
    if (lastEvent?.type === 'insert' && lastEvent.payment) {
      setLiveInserts(prev => prev + 1)
      setLiveVolume(prev => prev + (lastEvent.payment.settlementAmount || 0))
    }
  }, [lastEvent])

  if (loading) return <div className="loading">Loading dashboard...</div>
  if (!dashboard) return <div className="empty-state"><p>Could not load dashboard data. Is the backend running?</p></div>

  const { summary, statusDistribution, currencyDistribution, dailyActivity, pipelines } = dashboard

  return (
    <div>
      <div className="page-header">
        <h2>Payment Dashboard</h2>
        <p>Real-time analytics powered by MongoDB Aggregation Framework</p>
      </div>

      {/* Live connection indicator */}
      {connected && liveInserts > 0 && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12,
          padding: '6px 12px', background: 'var(--accent-bg)', borderRadius: 'var(--radius)',
          border: '1px solid var(--accent)', width: 'fit-content',
        }}>
          <Radio size={12} style={{ color: 'var(--accent)', animation: 'pulse 2s infinite' }} />
          <span style={{ fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}>
            +{liveInserts} payments (+${formatAmount(liveVolume)}) since page load
          </span>
        </div>
      )}

      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="stat-card" style={liveInserts > 0 ? { borderColor: 'var(--accent)' } : {}}>
          <div className="stat-icon" style={{ background: 'var(--accent-bg)', color: 'var(--accent)' }}>
            <ArrowRightLeft size={20} />
          </div>
          <div className="stat-value">
            {formatAmount(summary.totalCount + liveInserts)}
            {connected && <Radio size={10} style={{ color: 'var(--accent)', marginLeft: 6, verticalAlign: 'middle', animation: 'pulse 2s infinite' }} />}
          </div>
          <div className="stat-label">Total Payments</div>
        </div>
        <div className="stat-card" style={liveVolume > 0 ? { borderColor: 'var(--blue)' } : {}}>
          <div className="stat-icon" style={{ background: 'var(--blue-bg)', color: 'var(--blue)' }}>
            <DollarSign size={20} />
          </div>
          <div className="stat-value">
            ${formatAmount(summary.totalAmount + liveVolume)}
            {connected && <Radio size={10} style={{ color: 'var(--blue)', marginLeft: 6, verticalAlign: 'middle', animation: 'pulse 2s infinite' }} />}
          </div>
          <div className="stat-label">Total Volume</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--purple-bg)', color: 'var(--purple)' }}>
            <TrendingUp size={20} />
          </div>
          <div className="stat-value">${formatAmount(summary.avgAmount)}</div>
          <div className="stat-label">Avg Payment</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--orange-bg)', color: 'var(--orange)' }}>
            <AlertTriangle size={20} />
          </div>
          <div className="stat-value">
            {statusDistribution.find(s => s.status === 'RJCT')?.count || 0}
          </div>
          <div className="stat-label">Rejected</div>
        </div>
      </div>

      {/* Summary pipeline */}
      {pipelines?.summary && (
        <div className="card" style={{ marginBottom: 20 }}>
          <PipelineToggle
            pipeline={pipelines.summary.pipeline}
            label={pipelines.summary.label}
            description={pipelines.summary.description}
          />
        </div>
      )}

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Daily Payment Activity</span>
            <span className="card-subtitle">Last 30 days</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyActivity}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_STYLE.grid} />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: CHART_STYLE.tick }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: CHART_STYLE.tick }} />
              <Tooltip contentStyle={CHART_STYLE.tooltip} labelStyle={CHART_STYLE.label} />
              <Line type="monotone" dataKey="count" stroke="#00ED64" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <PipelineToggle
            pipeline={pipelines?.dailyActivity?.pipeline}
            label={pipelines?.dailyActivity?.label}
            description={pipelines?.dailyActivity?.description}
          />
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Status Distribution</span>
            <span className="card-subtitle">All payments</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie
                data={statusDistribution}
                cx="50%" cy="50%"
                outerRadius={80}
                dataKey="count"
                nameKey="status"
                label={({ status, count }) => `${status}: ${count}`}
              >
                {statusDistribution.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={CHART_STYLE.tooltip} />
            </PieChart>
          </ResponsiveContainer>
          <PipelineToggle
            pipeline={pipelines?.statusDistribution?.pipeline}
            label={pipelines?.statusDistribution?.label}
            description={pipelines?.statusDistribution?.description}
          />
        </div>
      </div>

      <div className="grid-2">
        <div className="card">
          <div className="card-header">
            <span className="card-title">Volume by Currency</span>
            <span className="card-subtitle">MongoDB $group aggregation</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={currencyDistribution.slice(0, 6)}>
              <CartesianGrid strokeDasharray="3 3" stroke={CHART_STYLE.grid} />
              <XAxis dataKey="currency" tick={{ fontSize: 11, fill: CHART_STYLE.tick }} />
              <YAxis tick={{ fontSize: 10, fill: CHART_STYLE.tick }} tickFormatter={v => formatAmount(v)} />
              <Tooltip contentStyle={CHART_STYLE.tooltip} formatter={v => ['$' + formatAmount(v), 'Volume']} />
              <Bar dataKey="totalAmount" fill="#016BF8" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <PipelineToggle
            pipeline={pipelines?.currencyDistribution?.pipeline}
            label={pipelines?.currencyDistribution?.label}
            description={pipelines?.currencyDistribution?.description}
          />
        </div>

        <div className="card">
          <div className="card-header">
            <span className="card-title">Top Payment Corridors</span>
            <span className="card-subtitle">Country pairs by volume</span>
          </div>
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Corridor</th>
                  <th>Count</th>
                  <th>Volume</th>
                </tr>
              </thead>
              <tbody>
                {(corridors?.data || []).slice(0, 6).map((c, i) => (
                  <tr key={i}>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{c.corridor}</td>
                    <td>{c.count}</td>
                    <td className="amount">${formatAmount(c.totalVolume)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  )
}
