import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard, ArrowRightLeft, FileText, Search,
  PlusCircle, AlertTriangle, Database, Sparkles, Brain, Library, Radio
} from 'lucide-react'

const navItems = [
  { section: 'Overview' },
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/live', icon: Radio, label: 'Live Feed' },
  { section: 'Payments' },
  { to: '/payments', icon: ArrowRightLeft, label: 'All Payments' },
  { to: '/payments/new', icon: PlusCircle, label: 'New Payment' },
  { section: 'Cash Management' },
  { to: '/statements', icon: FileText, label: 'Statements' },
  { section: 'Operations' },
  { to: '/investigations', icon: AlertTriangle, label: 'Investigations' },
  { section: 'AI & Search' },
  { to: '/ai-search', icon: Brain, label: 'AI Search' },
  { section: 'MongoDB' },
  { to: '/value-props', icon: Sparkles, label: 'Value Propositions' },
  { to: '/collections', icon: Library, label: 'Collection Explorer' },
]

function MongoDBLogo({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M34.5 7.6c-1.4-1.9-2.3-3.7-2.5-4.5-.1-.3-.3-.3-.3-.3s-.2 0-.3.3c-.2.8-1.1 2.6-2.5 4.5C21.3 18.3 20 24.7 21.2 31c1.1 5.6 4.5 9.8 7.8 12.7 0 0 .5.4.6 1.1.2.7.1 4.4.1 4.4h4.6s-.1-3.7.1-4.4c.1-.7.6-1.1.6-1.1 3.3-2.9 6.7-7.1 7.8-12.7C44 24.7 42.7 18.3 34.5 7.6z" fill="#00ED64"/>
      <path d="M33.7 44.2s-.2-.4-.6-1.1c-.1-.2-.2-.3-.2-.3-.7-.5-1.2-1-1.2-1-.4 1.5-.3 7.4-.3 7.4l1.4.2s.1-3.7.3-4.4c.1-.3.3-.5.5-.7l.1-.1z" fill="#004D29"/>
    </svg>
  )
}

export default function Layout({ children }) {
  return (
    <div className="app-layout">
      <header className="top-header">
        <div className="top-header-left">
          <MongoDBLogo size={28} />
          <span className="top-header-title">MongoDB for Payments</span>
        </div>
        <div className="top-header-right">
          <span className="top-header-badge">ISO 20022</span>
          <span className="top-header-badge">Polymorphic Demo</span>
        </div>
      </header>
      <aside className="sidebar">
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
