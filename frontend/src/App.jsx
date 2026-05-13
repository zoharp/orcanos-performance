import { useState } from 'react'
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import Scenarios from './pages/Scenarios'
import Accounts from './pages/Accounts'
import Dashboard from './pages/Dashboard'
import Settings from './pages/Settings'
import Login from './pages/Login'
import { isAuthenticated, getUsername, getRole, clearAuth } from './auth'
import './App.css'

function Nav({ onLogout }) {
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
      {link('/settings', 'Settings')}
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 13, color: '#94a3b8' }}>
          {getUsername()}
          <span style={{
            marginLeft: 6, fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
            color: getRole() === 'admin' ? '#f59e0b' : '#64748b',
          }}>
            {getRole()}
          </span>
        </span>
        <button onClick={onLogout} style={{
          background: 'none', border: '1px solid #334155', color: '#cbd5e1',
          borderRadius: 5, padding: '4px 12px', fontSize: 12, cursor: 'pointer',
        }}>
          Sign out
        </button>
      </div>
    </nav>
  )
}

function ProtectedRoute({ children }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  const [loggedIn, setLoggedIn] = useState(isAuthenticated())

  function handleLogout() {
    clearAuth()
    setLoggedIn(false)
  }

  return (
    <BrowserRouter>
      <div style={{ minHeight: '100vh', background: '#f8fafc', fontFamily: 'system-ui, sans-serif' }}>
        {loggedIn && <Nav onLogout={handleLogout} />}
        <Routes>
          <Route path="/login" element={
            loggedIn ? <Navigate to="/" replace /> : <Login onLogin={() => setLoggedIn(true)} />
          } />
          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/scenarios" element={<ProtectedRoute><Scenarios /></ProtectedRoute>} />
          <Route path="/accounts" element={<ProtectedRoute><Accounts /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Settings /></ProtectedRoute>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
