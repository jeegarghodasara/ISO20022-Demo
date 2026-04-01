import { Routes, Route } from 'react-router-dom'
import { AgentProvider } from './context/AgentContext'
import { AISearchProvider } from './context/AISearchContext'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Payments from './pages/Payments'
import PaymentDetail from './pages/PaymentDetail'
import NewPayment from './pages/NewPayment'
import Statements from './pages/Statements'
import StatementDetail from './pages/StatementDetail'
import Investigations from './pages/Investigations'
import ValueProps from './pages/ValueProps'
import AISearch from './pages/AISearch'
import Collections from './pages/Collections'
import LiveFeed from './pages/LiveFeed'
import Agents from './pages/Agents'

function App() {
  return (
    <AgentProvider>
    <AISearchProvider>
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/live" element={<LiveFeed />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/payments/new" element={<NewPayment />} />
        <Route path="/payments/:uetr" element={<PaymentDetail />} />
        <Route path="/statements" element={<Statements />} />
        <Route path="/statements/:id" element={<StatementDetail />} />
        <Route path="/investigations" element={<Investigations />} />
        <Route path="/ai-search" element={<AISearch />} />
        <Route path="/agents" element={<Agents />} />
        <Route path="/value-props" element={<ValueProps />} />
        <Route path="/collections" element={<Collections />} />
      </Routes>
    </Layout>
    </AISearchProvider>
    </AgentProvider>
  )
}

export default App
