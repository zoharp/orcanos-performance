import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Scenarios from './pages/Scenarios'
import Accounts from './pages/Accounts'
import Dashboard from './pages/Dashboard'
import './App.css'

function Nav() {
  const loc = useLocation()
  const link = (to, label) => (
    <Link to={to} style={{
      padding: '8px 14px', borderRadius: 6, textDecoration: 'none', fontSize: 14, fontWeight: 500,
      background: loc.pathname === to ? '#1e40af' : 'transparent',
      color: loc.pathname === to ? '#fff' : '#cbd5e1',
    }}>{label}</Link>
  )
  return (
    <nav style={{ background: '#1e293b', padding: '0 24px', display: 'flex', alignItems: 'center', gap: 4, height: 52 }}>
      <span style={{ color: '#f1f5f9', fontWeight: 700, fontSize: 15, marginRight: 16 }}>Orcanos Performance</span>
      {link('/', 'Dashboard')}
      {link('/scenarios', 'Scenarios')}
      {link('/accounts', 'Accounts')}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
        <Nav />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scenarios" element={<Scenarios />} />
          <Route path="/accounts" element={<Accounts />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
