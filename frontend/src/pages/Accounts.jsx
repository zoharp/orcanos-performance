import { useState, useEffect } from 'react'
import { fetchWithAuth, isAdmin } from '../auth'

const API = ''
const VERSIONS = ['6.0', '5.2.6']

function extractAccountName(url) {
  try {
    const path = new URL(url).pathname
    const parts = path.split('/').filter(Boolean)
    return parts[0] || ''
  } catch {
    return ''
  }
}

export default function Accounts() {
  const [accounts, setAccounts] = useState([])
  const [url, setUrl] = useState('')
  const [password, setPassword] = useState('')
  const [version, setVersion] = useState('6.0')
  const [preview, setPreview] = useState('')
  const [message, setMessage] = useState(null)
  const [loading, setLoading] = useState(false)

  const [editingAccount, setEditingAccount] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', url: '', password: '', version: '', enabled: true })
  const [editMessage, setEditMessage] = useState(null)
  const [editLoading, setEditLoading] = useState(false)

  const [testingSessions, setTestingSessions] = useState({}) // {accountId: {status, timer, error}}

  useEffect(() => { loadAccounts() }, [])

  useEffect(() => {
    const interval = setInterval(async () => {
      // Poll status of active test sessions
      const activeIds = Object.keys(testingSessions).filter(id => testingSessions[id].status === 'running')
      if (activeIds.length === 0) return

      for (const accountId of activeIds) {
        try {
          const res = await fetchWithAuth(`${API}/api/accounts/${accountId}/manual-test/status`)
          const data = await res.json()

          setTestingSessions(prev => ({
            ...prev,
            [accountId]: {
              ...prev[accountId],
              timer: data.inactivity_seconds,
              status: data.status,
              error: data.error,
            }
          }))

          // Auto-stop if session closed
          if (data.status === 'closed') {
            setTimeout(() => {
              setTestingSessions(prev => {
                const newSessions = { ...prev }
                delete newSessions[accountId]
                return newSessions
              })
            }, 2000)
          }
        } catch {}
      }
    }, 1000)
    return () => clearInterval(interval)
  }, [testingSessions])

  useEffect(() => { setPreview(extractAccountName(url)) }, [url])

  async function loadAccounts() {
    try {
      const res = await fetchWithAuth(`${API}/api/accounts/`)
      setAccounts(await res.json())
    } catch {}
  }

  async function addAccount(e) {
    e.preventDefault()
    const name = extractAccountName(url)
    if (!name) return setMessage({ type: 'error', text: 'Could not extract account name from URL. Use format: https://app.orcanos.com/ACCOUNT/web/' })
    if (!password) return setMessage({ type: 'error', text: 'Password is required.' })

    setLoading(true)
    setMessage(null)
    try {
      const res = await fetchWithAuth(`${API}/api/accounts/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, url, password, version, enabled: true }),
      })
      if (!res.ok) {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to add account.' })
      } else {
        setMessage({ type: 'success', text: `Account "${name}" added.` })
        setUrl('')
        setPassword('')
        setVersion('')
        setPreview('')
        loadAccounts()
      }
    } catch {
      setMessage({ type: 'error', text: 'Cannot reach backend.' })
    }
    setLoading(false)
  }

  function openEdit(a) {
    setEditingAccount(a)
    setEditForm({ name: a.name, url: a.url, password: '', version: a.version || '', enabled: a.enabled })
    setEditMessage(null)
  }

  function closeEdit() {
    setEditingAccount(null)
    setEditMessage(null)
  }

  async function saveEdit(e) {
    e.preventDefault()
    if (!editForm.name.trim()) return setEditMessage({ type: 'error', text: 'Name is required.' })
    if (!editForm.url.trim()) return setEditMessage({ type: 'error', text: 'URL is required.' })

    setEditLoading(true)
    setEditMessage(null)
    try {
      const res = await fetchWithAuth(`${API}/api/accounts/${editingAccount.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editForm),
      })
      if (!res.ok) {
        const err = await res.json()
        setEditMessage({ type: 'error', text: err.detail || 'Failed to update account.' })
      } else {
        closeEdit()
        loadAccounts()
      }
    } catch {
      setEditMessage({ type: 'error', text: 'Cannot reach backend.' })
    }
    setEditLoading(false)
  }

  async function toggleAccount(id, enabled) {
    const acct = accounts.find(a => a.id === id)
    if (!acct) return
    await fetchWithAuth(`${API}/api/accounts/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: acct.name, url: acct.url, password: '', version: acct.version || '', enabled: !enabled }),
    })
    loadAccounts()
  }

  async function deleteAccount(id, name) {
    if (!confirm(`Delete account "${name}"?`)) return
    await fetchWithAuth(`${API}/api/accounts/${id}`, { method: 'DELETE' })
    loadAccounts()
  }

  async function startManualTest(id) {
    setTestingSessions(prev => ({ ...prev, [id]: { status: 'starting', timer: 300, error: null } }))
    try {
      const res = await fetchWithAuth(`${API}/api/accounts/${id}/manual-test/start`, { method: 'POST' })
      const data = await res.json()
      if (!res.ok) {
        setTestingSessions(prev => ({ ...prev, [id]: { status: 'error', timer: 0, error: data.detail || 'Failed to start' } }))
      } else {
        setTestingSessions(prev => ({ ...prev, [id]: { status: 'running', timer: 300, error: null } }))
      }
    } catch (e) {
      setTestingSessions(prev => ({ ...prev, [id]: { status: 'error', timer: 0, error: 'Network error' } }))
    }
  }

  async function stopManualTest(id) {
    try {
      await fetchWithAuth(`${API}/api/accounts/${id}/manual-test/stop`, { method: 'POST' })
    } catch {}
    setTestingSessions(prev => {
      const newSessions = { ...prev }
      delete newSessions[id]
      return newSessions
    })
  }

  return (
    <div style={{ padding: 24, maxWidth: 920, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Accounts</h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        Add the Orcanos accounts to test. All accounts use the shared user <code>orcanos.tech</code>.
      </p>

      {/* Add account form */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Add Account</h2>
        <form onSubmit={addAccount}>
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
            <div style={{ flex: 3, minWidth: 240 }}>
              <label style={labelStyle}>Account URL</label>
              <input
                style={inputStyle}
                value={url}
                onChange={e => setUrl(e.target.value)}
                placeholder="https://app.orcanos.com/acme/web/"
                required
              />
              {preview && (
                <div style={{ marginTop: 5, fontSize: 12, color: '#2563eb' }}>
                  Account name: <strong>{preview}</strong>
                </div>
              )}
            </div>
            <div style={{ flex: 2, minWidth: 160 }}>
              <label style={labelStyle}>Password</label>
              <input
                style={inputStyle}
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="Account password"
                required
              />
            </div>
            <div style={{ flex: 1, minWidth: 100 }}>
              <label style={labelStyle}>Version</label>
              <select style={{ ...inputStyle, cursor: 'pointer' }} value={version} onChange={e => setVersion(e.target.value)}>
                {VERSIONS.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
          </div>

          {message && (
            <div style={{
              padding: '9px 14px', borderRadius: 6, marginBottom: 12, fontSize: 13,
              background: message.type === 'error' ? '#fef2f2' : '#f0fdf4',
              color: message.type === 'error' ? '#dc2626' : '#16a34a',
              border: `1px solid ${message.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
            }}>
              {message.text}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            background: loading ? '#93c5fd' : '#2563eb', color: '#fff',
            border: 'none', borderRadius: 6, padding: '9px 20px',
            fontSize: 14, fontWeight: 600, cursor: loading ? 'default' : 'pointer',
          }}>
            {loading ? 'Adding...' : '+ Add Account'}
          </button>
        </form>
      </div>

      {/* Accounts list */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Accounts ({accounts.length})</h2>
        {accounts.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: 14 }}>No accounts added yet.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb', color: '#6b7280', textAlign: 'left' }}>
                  <th style={{ ...thStyle, fontWeight: 600 }}>Account</th>
                  <th style={{ ...thStyle, fontWeight: 600 }}>Version</th>
                  <th style={{ ...thStyle, fontWeight: 600 }}>Status</th>
                  <th style={{ ...thStyle, fontWeight: 600, textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {accounts.sort((a, b) => a.name.localeCompare(b.name)).map(a => {
                  const testSession = testingSessions[a.id]
                  const isTestingActive = testSession && testSession.status === 'running'
                  return (
                    <tr key={a.id} style={{ borderBottom: '1px solid #f3f4f6', background: isTestingActive ? '#fef3c7' : 'transparent' }}>
                      <td style={{ ...tdStyle, fontWeight: 600 }}>
                        {a.name}
                        {testSession && testSession.status === 'error' && (
                          <div style={{ marginTop: 4, fontSize: 12, color: '#dc2626' }}>
                            ⚠ {testSession.error}
                          </div>
                        )}
                      </td>
                      <td style={{ ...tdStyle, color: '#6b7280' }}>{a.version || '—'}</td>
                      <td style={tdStyle}>
                        <span style={{
                          display: 'inline-block', padding: '4px 10px', borderRadius: 99, fontSize: 12, fontWeight: 600,
                          background: a.enabled ? '#dcfce7' : '#f3f4f6',
                          color: a.enabled ? '#16a34a' : '#9ca3af',
                        }}>
                          {a.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        {isTestingActive && (
                          <div style={{ marginTop: 6, fontSize: 12, color: '#b45309', fontWeight: 600 }}>
                            🔴 Testing ({testSession.timer}s)
                          </div>
                        )}
                      </td>
                      <td style={{ ...tdStyle, textAlign: 'right', display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        {isTestingActive ? (
                          <button onClick={() => stopManualTest(a.id)} style={{ ...smallBtn, background: '#fef2f2', color: '#dc2626' }}>
                            Stop
                          </button>
                        ) : testSession && testSession.status === 'starting' ? (
                          <button disabled style={{ ...smallBtn, background: '#e5e7eb', color: '#9ca3af' }}>
                            Starting…
                          </button>
                        ) : (
                          <button onClick={() => startManualTest(a.id)} style={{ ...smallBtn, background: '#dbeafe', color: '#1e40af' }}>
                            Test
                          </button>
                        )}
                        <button onClick={() => openEdit(a)} style={{ ...smallBtn, background: '#eff6ff', color: '#2563eb' }}>Edit</button>
                        <button onClick={() => toggleAccount(a.id, a.enabled)} style={{ ...smallBtn, background: '#f3f4f6', color: '#374151' }}>
                          {a.enabled ? 'Disable' : 'Enable'}
                        </button>
                        {isAdmin() && (
                          <button onClick={() => deleteAccount(a.id, a.name)} style={{ ...smallBtn, background: '#fef2f2', color: '#dc2626' }}>Delete</button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Edit modal */}
      {editingAccount && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#fff', borderRadius: 10, padding: 28, width: 500, maxWidth: '90vw', boxShadow: '0 8px 32px rgba(0,0,0,0.18)' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Edit Account</h2>
            <form onSubmit={saveEdit}>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Account Name</label>
                <input style={inputStyle} value={editForm.name} onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))} required />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>URL</label>
                <input style={inputStyle} value={editForm.url} onChange={e => setEditForm(f => ({ ...f, url: e.target.value }))} required />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>
                  Password <span style={{ color: '#9ca3af', fontWeight: 400 }}>(leave blank to keep current)</span>
                </label>
                <input style={inputStyle} type="password" value={editForm.password} onChange={e => setEditForm(f => ({ ...f, password: e.target.value }))} placeholder="New password (optional)" />
              </div>
              <div style={{ display: 'flex', gap: 12, marginBottom: 14 }}>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Version</label>
                  <select style={{ ...inputStyle, cursor: 'pointer' }} value={editForm.version} onChange={e => setEditForm(f => ({ ...f, version: e.target.value }))}>
                    {VERSIONS.map(v => <option key={v} value={v}>{v}</option>)}
                  </select>
                </div>
                <div style={{ flex: 1 }}>
                  <label style={labelStyle}>Status</label>
                  <select
                    style={{ ...inputStyle, cursor: 'pointer' }}
                    value={editForm.enabled ? 'enabled' : 'disabled'}
                    onChange={e => setEditForm(f => ({ ...f, enabled: e.target.value === 'enabled' }))}
                  >
                    <option value="enabled">Enabled</option>
                    <option value="disabled">Disabled</option>
                  </select>
                </div>
              </div>

              {editMessage && (
                <div style={{
                  padding: '9px 14px', borderRadius: 6, marginBottom: 12, fontSize: 13,
                  background: editMessage.type === 'error' ? '#fef2f2' : '#f0fdf4',
                  color: editMessage.type === 'error' ? '#dc2626' : '#16a34a',
                  border: `1px solid ${editMessage.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
                }}>
                  {editMessage.text}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 8 }}>
                <button type="button" onClick={closeEdit} style={{ ...smallBtn, padding: '8px 16px', fontSize: 14, background: '#f3f4f6', color: '#374151' }}>
                  Cancel
                </button>
                <button type="submit" disabled={editLoading} style={{ ...smallBtn, padding: '8px 18px', fontSize: 14, background: editLoading ? '#93c5fd' : '#2563eb', color: '#fff' }}>
                  {editLoading ? 'Saving…' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }
const inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }
const smallBtn = { border: 'none', borderRadius: 4, padding: '4px 10px', fontSize: 12, fontWeight: 500, cursor: 'pointer' }
const thStyle = { padding: '8px 12px', fontWeight: 500, fontSize: 13 }
const tdStyle = { padding: '10px 12px', verticalAlign: 'middle' }
