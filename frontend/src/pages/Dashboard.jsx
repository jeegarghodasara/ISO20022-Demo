import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line, CartesianGrid } from 'recharts'
import { TrendingUp, DollarSign, ArrowRightLeft, AlertTriangle } from 'lucide-react'
import { getDashboard, getTopCorridors } from '../services/api'

const COLORS = ['#00ed64', '#3b82f6', '#a855f7', '#f59e0b', '#ef4444', '#14b8a6', '#ec4899']

function formatAmount(val) {
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)}B`
  if (val >= 1e6) return `${(val / 1e6).toFixed(1)}M`
  if (val >= 1e3) return `${(val / 1e3).toFixed(1)}K`
  return val?.toFixed(0) || '0'
}

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [corridors, setCorridors] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getDashboard(), getTopCorridors()])
      .then(([d, c]) => { setDashboard(d); setCorridors(c) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="loading">Loading dashboard...</div>
  if (!dashboard) return <div className="empty-state"><p>Could not load dashboard data. Is the backend running?</p></div>

  const { summary, statusDistribution, currencyDistribution, dailyActivity } = dashboard

  return (
    <div>
      <div className="page-header">
        <h2>Payment Dashboard</h2>
        <p>Real-time analytics powered by MongoDB Aggregation Framework</p>
      </div>

      <div className="grid-4" style={{ marginBottom: 20 }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--accent-bg)', color: 'var(--accent)' }}>
            <ArrowRightLeft size={20} />
          </div>
          <div className="stat-value">{formatAmount(summary.totalCount)}</div>
          <div className="stat-label">Total Payments</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'var(--blue-bg)', color: 'var(--blue)' }}>
            <DollarSign size={20} />
          </div>
          <div className="stat-value">${formatAmount(summary.totalAmount)}</div>
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

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card">
          <div className="card-header">
            <span className="card-title">Daily Payment Activity</span>
            <span className="card-subtitle">Last 30 days</span>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={dailyActivity}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7089' }} tickFormatter={d => d.slice(5)} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7089' }} />
              <Tooltip
                contentStyle={{ background: '#1e2130', border: '1px solid #2d3148', borderRadius: 8, fontSize: 12 }}
                labelStyle={{ color: '#e8eaed' }}
              />
              <Line type="monotone" dataKey="count" stroke="#00ed64" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
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
              <Tooltip contentStyle={{ background: '#1e2130', border: '1px solid #2d3148', borderRadius: 8, fontSize: 12 }} />
            </PieChart>
          </ResponsiveContainer>
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
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
              <XAxis dataKey="currency" tick={{ fontSize: 11, fill: '#6b7089' }} />
              <YAxis tick={{ fontSize: 10, fill: '#6b7089' }} tickFormatter={v => formatAmount(v)} />
              <Tooltip
                contentStyle={{ background: '#1e2130', border: '1px solid #2d3148', borderRadius: 8, fontSize: 12 }}
                formatter={v => ['$' + formatAmount(v), 'Volume']}
              />
              <Bar dataKey="totalAmount" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
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
