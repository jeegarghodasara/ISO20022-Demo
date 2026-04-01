import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, ArrowRightLeft, FileText, Search,
  PlusCircle, AlertTriangle, Database, Sparkles
} from 'lucide-react'

const navItems = [
  { section: 'Overview' },
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { section: 'Payments' },
  { to: '/payments', icon: ArrowRightLeft, label: 'All Payments' },
  { to: '/payments/new', icon: PlusCircle, label: 'New Payment' },
  { section: 'Cash Management' },
  { to: '/statements', icon: FileText, label: 'Statements' },
  { section: 'Operations' },
  { to: '/investigations', icon: AlertTriangle, label: 'Investigations' },
  { section: 'MongoDB' },
  { to: '/value-props', icon: Sparkles, label: 'Value Propositions' },
]

export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-logo">
          <h1>
            <Database className="logo-icon" size={22} />
            ISO 20022
          </h1>
          <p>Polymorphic Payments on MongoDB</p>
        </div>
        <nav>
          {navItems.map((item, i) =>
            item.section ? (
              <div key={i} className="sidebar-section">{item.section}</div>
            ) : (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
              >
                <item.icon size={18} />
                {item.label}
              </NavLink>
            )
          )}
        </nav>
      </aside>
      <main className="main-content">{children}</main>
    </div>
  )
}
