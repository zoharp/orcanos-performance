import { useState } from 'react'
import { setAuth } from '../auth'

const API = ''

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Login failed')
      } else {
        const data = await res.json()
        setAuth(data.access_token, data.role, data.username)
        onLogin()
      }
    } catch {
      setError('Cannot reach server')
    }
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: '100vh', background: '#f8fafc',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'system-ui, sans-serif',
    }}>
      <div style={{
        background: '#fff', borderRadius: 12, padding: 40, width: 360,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)', border: '1px solid #e5e7eb',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>
            Orcanos Performance
          </div>
          <div style={{ fontSize: 13, color: '#6b7280' }}>Sign in to continue</div>
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: 14 }}>
            <label style={labelStyle}>Username</label>
            <input
              style={inputStyle}
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              autoFocus
              required
            />
          </div>
          <div style={{ marginBottom: 20 }}>
            <label style={labelStyle}>Password</label>
            <input
              style={inputStyle}
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div style={{
              padding: '9px 14px', borderRadius: 6, marginBottom: 14, fontSize: 13,
              background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca',
            }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            width: '100%', padding: '10px 0',
            background: loading ? '#93c5fd' : '#2563eb',
            color: '#fff', border: 'none', borderRadius: 8,
            fontSize: 15, fontWeight: 600, cursor: loading ? 'default' : 'pointer',
          }}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }
const inputStyle = {
  width: '100%', padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8,
  fontSize: 14, boxSizing: 'border-box',
}
