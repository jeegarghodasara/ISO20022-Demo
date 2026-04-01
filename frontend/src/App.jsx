import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Payments from './pages/Payments'
import PaymentDetail from './pages/PaymentDetail'
import NewPayment from './pages/NewPayment'
import Statements from './pages/Statements'
import StatementDetail from './pages/StatementDetail'
import Investigations from './pages/Investigations'
import ValueProps from './pages/ValueProps'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/payments" element={<Payments />} />
        <Route path="/payments/new" element={<NewPayment />} />
        <Route path="/payments/:uetr" element={<PaymentDetail />} />
        <Route path="/statements" element={<Statements />} />
        <Route path="/statements/:id" element={<StatementDetail />} />
        <Route path="/investigations" element={<Investigations />} />
        <Route path="/value-props" element={<ValueProps />} />
      </Routes>
    </Layout>
  )
}

export default App
