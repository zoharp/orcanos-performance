import { useState, useEffect } from 'react'
import { setAuth } from '../auth'

const API = ''

export default function Login({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)
  const isDevelopment = import.meta.env.MODE === 'development'

  useEffect(() => {
    const googleClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID
    if (!googleClientId) {
      setError('Google OAuth not configured (VITE_GOOGLE_CLIENT_ID missing)')
      return
    }
    if (!window.google) {
      setError('Google Sign-In library failed to load')
      return
    }
    window.google.accounts.id.initialize({
      client_id: googleClientId,
      callback: handleGoogleLogin,
    })
    window.google.accounts.id.renderButton(document.getElementById('googleButton'), {
      theme: 'outline',
      size: 'large',
      width: '100%',
      text: 'signin_with',
    })
  }, [])

  async function handleGoogleLogin(response) {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`${API}/api/auth/google`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ credential: response.credential }),
      })
      if (!res.ok) {
        const err = await res.json()
        setError(err.detail || 'Google login failed')
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
        background: '#fff', borderRadius: 12, padding: 40, width: 380,
        boxShadow: '0 4px 24px rgba(0,0,0,0.08)', border: '1px solid #e5e7eb',
      }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#1e293b', marginBottom: 6 }}>
            Orcanos Performance
          </div>
          <div style={{ fontSize: 13, color: '#6b7280' }}>Sign in to continue</div>
        </div>

        {error && (
          <div style={{
            padding: '9px 14px', borderRadius: 6, marginBottom: 16, fontSize: 13,
            background: '#fef2f2', color: '#dc2626', border: '1px solid #fecaca',
          }}>
            {error}
          </div>
        )}

        <div id="googleButton" style={{ marginBottom: 20 }}></div>

        {isDevelopment && (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
              <div style={{ flex: 1, height: 1, background: '#e5e7eb' }}></div>
              <div style={{ fontSize: 12, color: '#9ca3af' }}>or</div>
              <div style={{ flex: 1, height: 1, background: '#e5e7eb' }}></div>
            </div>

            <details style={{ cursor: 'pointer', marginBottom: 0 }}>
              <summary style={{
                fontSize: 13, fontWeight: 600, color: '#6b7280', padding: '8px 0',
                userSelect: 'none',
              }}>
                Admin login (development only)
              </summary>
              <form onSubmit={handleSubmit} style={{ marginTop: 16 }}>
                <div style={{ marginBottom: 14 }}>
                  <label style={labelStyle}>Username</label>
                  <input
                    style={inputStyle}
                    value={username}
                    onChange={e => setUsername(e.target.value)}
                    autoComplete="username"
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

                <button type="submit" disabled={loading} style={{
                  width: '100%', padding: '10px 0',
                  background: loading ? '#93c5fd' : '#2563eb',
                  color: '#fff', border: 'none', borderRadius: 8,
                  fontSize: 15, fontWeight: 600, cursor: loading ? 'default' : 'pointer',
                }}>
                  {loading ? 'Signing in…' : 'Sign in'}
                </button>
              </form>
            </details>
          </>
        )}
      </div>
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }
const inputStyle = {
  width: '100%', padding: '9px 12px', border: '1px solid #d1d5db', borderRadius: 8,
  fontSize: 14, boxSizing: 'border-box',
}
