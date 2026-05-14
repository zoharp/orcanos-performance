import React, { useState, useEffect, useRef } from 'react'
import { fetchWithAuth, isAdmin } from '../auth'

const API = ''
const VERSIONS = ['6.0', '5.2.6']

const STATUS_COLOR = {
  pass: { bg: '#dcfce7', color: '#16a34a' },
  warning: { bg: '#fef9c3', color: '#ca8a04' },
  critical: { bg: '#fee2e2', color: '#dc2626' },
  failed: { bg: '#fee2e2', color: '#dc2626' },
  running: { bg: '#dbeafe', color: '#2563eb' },
  completed: { bg: '#dcfce7', color: '#16a34a' },
  stopped: { bg: '#fef9c3', color: '#ca8a04' },
  timed_out: { bg: '#fee2e2', color: '#dc2626' },
}

function badge(status) {
  const s = STATUS_COLOR[status] || { bg: '#f3f4f6', color: '#6b7280' }
  return {
    display: 'inline-block', padding: '2px 8px', borderRadius: 99,
    fontSize: 12, fontWeight: 600, background: s.bg, color: s.color,
  }
}

export default function Scenarios() {
  const [scenarios, setScenarios] = useState([])
  const [recordName, setRecordName] = useState('')
  const [recordUrl, setRecordUrl] = useState('https://app.orcanos.com/orcanos/web/')
  const [recordVersion, setRecordVersion] = useState('6.0')
  const [recording, setRecording] = useState(false)
  const [steps, setSteps] = useState([])
  const pollRef = useRef(null)

  const [runningScenario, setRunningScenario] = useState(null)
  const [runProgress, setRunProgress] = useState(null)
  const [message, setMessage] = useState(null)
  const runPollRef = useRef(null)
  const reqFeedRef = useRef(null)

  const [accounts, setAccounts] = useState([])
  const [selectedAccounts, setSelectedAccounts] = useState({})
  const [expandedSteps, setExpandedSteps] = useState({}) // scenarioName -> steps[]

  const [editingScenario, setEditingScenario] = useState(null)
  const [editForm, setEditForm] = useState({ name: '', version: '' })
  const [editMessage, setEditMessage] = useState(null)
  const [editLoading, setEditLoading] = useState(false)

  useEffect(() => {
    loadScenarios()
    loadAccounts()
    checkRecording()
    resumeRunIfActive()
  }, [])

  async function loadAccounts() {
    try {
      const res = await fetchWithAuth(`${API}/api/accounts/`)
      setAccounts(await res.json())
    } catch {}
  }

  async function resumeRunIfActive() {
    const saved = localStorage.getItem('activeRunId')
    if (!saved) return
    const id = parseInt(saved)
    const res = await fetchWithAuth(`${API}/api/runs/${id}/progress`).catch(() => null)
    if (!res) return
    const data = await res.json()
    if (data.status === 'running') {
      setRunningScenario(data.scenario_name || '...')
      setRunProgress(data)
      pollRunProgress(id)
    } else {
      localStorage.removeItem('activeRunId')
      setRunProgress(data)
    }
  }

  async function loadScenarios() {
    try {
      const res = await fetchWithAuth(`${API}/api/scenarios`)
      setScenarios(await res.json())
    } catch {}
  }

  async function checkRecording() {
    try {
      const res = await fetchWithAuth(`${API}/api/scenarios/record/status`)
      const data = await res.json()
      if (data.active) {
        setRecording(true)
        setSteps(data.steps || [])
        startStepPoll()
      }
    } catch {}
  }

  function startStepPoll() {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetchWithAuth(`${API}/api/scenarios/record/status`)
        const data = await res.json()
        setSteps(data.steps || [])
        if (!data.active) {
          setRecording(false)
          clearInterval(pollRef.current)
          loadScenarios()
        }
      } catch {}
    }, 1000)
  }

  const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname)

  async function startRecording(e) {
    e.preventDefault()
    if (!recordName.trim()) return
    if (!isLocal) {
      setMessage({ type: 'error', text: 'Recording can only be done locally. Record on your machine, then upload the scenario file to fly.io.' })
      return
    }
    try {
      await fetchWithAuth(`${API}/api/scenarios/record/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: recordName.trim(), url: recordUrl.trim(), version: recordVersion }),
      })
      setRecording(true)
      setSteps([])
      startStepPoll()
    } catch {
      setMessage({ type: 'error', text: 'Failed to start recording.' })
    }
  }

  async function stopRecording() {
    try {
      await fetchWithAuth(`${API}/api/scenarios/record/stop`, { method: 'POST' })
      setRecording(false)
      clearInterval(pollRef.current)
      setRecordName('')
      loadScenarios()
    } catch {
      setMessage({ type: 'error', text: 'Failed to stop recording.' })
    }
  }

  async function deleteScenario(name) {
    if (!confirm(`Delete scenario "${name}"?`)) return
    await fetchWithAuth(`${API}/api/scenarios/${name}`, { method: 'DELETE' })
    loadScenarios()
  }

  async function runScenario(name) {
    setRunningScenario(name)
    setRunProgress(null)
    setMessage(null)
    const accountId = selectedAccounts[name]
    const body = { scenario_name: name }
    if (accountId && accountId !== 'all') body.account_id = parseInt(accountId)
    try {
      const res = await fetchWithAuth(`${API}/api/runs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (!res.ok) {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to start run.' })
        setRunningScenario(null)
        return
      }
      const run = await res.json()
      localStorage.setItem('activeRunId', run.id)
      pollRunProgress(run.id)
    } catch {
      setMessage({ type: 'error', text: 'Cannot reach backend.' })
      setRunningScenario(null)
    }
  }

  function pollRunProgress(id) {
    clearInterval(runPollRef.current)
    runPollRef.current = setInterval(async () => {
      try {
        const res = await fetchWithAuth(`${API}/api/runs/${id}/progress`)
        const data = await res.json()
        setRunProgress(data)
        if (reqFeedRef.current) {
          reqFeedRef.current.scrollTop = reqFeedRef.current.scrollHeight
        }
        if (data.status === 'completed' || data.status === 'failed' || data.status === 'stopped' || data.status === 'timed_out') {
          clearInterval(runPollRef.current)
          setRunningScenario(null)
          localStorage.removeItem('activeRunId')
          const msgs = { completed: 'Run completed successfully.', failed: 'Run failed.', stopped: 'Run stopped.', timed_out: 'Run timed out.' }
          setMessage({ type: data.status === 'completed' ? 'success' : 'error', text: msgs[data.status] })
        }
      } catch {}
    }, 1000)
  }

  async function stopRun() {
    const saved = localStorage.getItem('activeRunId')
    if (!saved) return
    try {
      await fetchWithAuth(`${API}/api/runs/${saved}/stop`, { method: 'POST' })
      // Immediately poll for updated status
      setTimeout(async () => {
        try {
          const res = await fetchWithAuth(`${API}/api/runs/${saved}/progress`)
          const data = await res.json()
          setRunProgress(data)
          if (data.status !== 'running') {
            setRunningScenario(null)
            clearInterval(runPollRef.current)
            localStorage.removeItem('activeRunId')
            setMessage({ type: 'success', text: 'Run stopped.' })
          }
        } catch {}
      }, 100)
    } catch {}
  }

  async function toggleSteps(name) {
    if (expandedSteps[name]) {
      setExpandedSteps(prev => { const n = {...prev}; delete n[name]; return n })
      return
    }
    try {
      const res = await fetchWithAuth(`${API}/api/scenarios/${name}`)
      const data = await res.json()
      setExpandedSteps(prev => ({ ...prev, [name]: data.steps || [] }))
    } catch {}
  }

  function openEditScenario(s) {
    setEditingScenario(s)
    setEditForm({ name: s.name, version: s.version || '' })
    setEditMessage(null)
  }

  function closeEditScenario() {
    setEditingScenario(null)
    setEditMessage(null)
  }

  async function saveScenarioEdit(e) {
    e.preventDefault()
    if (!editForm.name.trim()) return setEditMessage({ type: 'error', text: 'Name is required.' })
    setEditLoading(true)
    setEditMessage(null)
    try {
      const res = await fetchWithAuth(`${API}/api/scenarios/${editingScenario.name}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: editForm.name.trim(), version: editForm.version }),
      })
      if (!res.ok) {
        const err = await res.json()
        setEditMessage({ type: 'error', text: err.detail || 'Failed to update scenario.' })
      } else {
        closeEditScenario()
        loadScenarios()
      }
    } catch {
      setEditMessage({ type: 'error', text: 'Cannot reach backend.' })
    }
    setEditLoading(false)
  }

  return (
    <div style={{ padding: 24, maxWidth: 920, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Scenarios</h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>
        Record a scenario once, then run it across all accounts.
      </p>

      {message && (
        <div style={{
          padding: '10px 14px', borderRadius: 6, marginBottom: 16, fontSize: 13,
          background: message.type === 'error' ? '#fef2f2' : '#f0fdf4',
          color: message.type === 'error' ? '#dc2626' : '#16a34a',
          border: `1px solid ${message.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
        }}>
          {message.text}
        </div>
      )}

      {/* Record new scenario */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 24, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>Record New Scenario</h2>
        {!recording ? (
          <form onSubmit={startRecording}>
            <div style={{ display: 'flex', gap: 10, marginBottom: 10 }}>
              <input
                style={{ flex: 1, padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}
                value={recordName}
                onChange={e => setRecordName(e.target.value)}
                placeholder="Scenario name (e.g. login_flow)"
                required
              />
              <select
                style={{ padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, cursor: 'pointer' }}
                value={recordVersion}
                onChange={e => setRecordVersion(e.target.value)}
              >
                {VERSIONS.map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <input
                style={{ flex: 1, padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}
                value={recordUrl}
                onChange={e => setRecordUrl(e.target.value)}
                placeholder="https://app.orcanos.com/orcanos/web/"
                required
              />
              <button type="submit" style={btnStyle('#2563eb')}>Start Recording</button>
            </div>
          </form>
        ) : (
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#dc2626', display: 'inline-block' }} />
              <span style={{ fontWeight: 600, color: '#dc2626' }}>Recording… ({steps.length} steps captured)</span>
              <button onClick={stopRecording} style={btnStyle('#dc2626')}>Stop & Save</button>
            </div>
            {steps.length > 0 && (
              <div style={{ background: '#f9fafb', borderRadius: 6, padding: 10, maxHeight: 160, overflowY: 'auto' }}>
                {steps.map((s, i) => (
                  <div key={i} style={{ fontSize: 12, color: '#374151', padding: '2px 0' }}>
                    {i + 1}. {s.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Run progress */}
      {runProgress && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 20, marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2 style={{ fontSize: 16, fontWeight: 600, margin: 0 }}>
              Run Progress &nbsp;<span style={badge(runProgress.status)}>{runProgress.status}</span>
            </h2>
            {runProgress.status === 'running' && (
              <button onClick={stopRun} style={{ ...smallBtn, background: '#fef2f2', color: '#dc2626', cursor: 'pointer', padding: '5px 12px' }}>
                ■ Stop
              </button>
            )}
          </div>
          <div style={{ fontSize: 14, color: '#374151', marginBottom: 6 }}>
            Accounts: {runProgress.completed_accounts} / {runProgress.total_accounts} completed
          </div>
          {runProgress.current_account && (
            <div style={{ fontSize: 13, color: '#6b7280' }}>
              Currently testing: <strong>{runProgress.current_account}</strong>
            </div>
          )}
          <div style={{ marginTop: 10, height: 6, background: '#e5e7eb', borderRadius: 3 }}>
            <div style={{
              height: 6, borderRadius: 3, background: '#2563eb',
              width: `${runProgress.total_accounts ? (runProgress.completed_accounts / runProgress.total_accounts) * 100 : 0}%`,
              transition: 'width 0.5s',
            }} />
          </div>

          {/* Live API call feed */}
          {(runProgress.recent_requests?.length > 0) && (
            <div style={{ marginTop: 14 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', marginBottom: 4, letterSpacing: 0.3 }}>
                API CALLS
              </div>
              <div
                ref={reqFeedRef}
                style={{
                  background: '#0f172a', borderRadius: 6, padding: '8px 10px',
                  maxHeight: 220, overflowY: 'auto', fontFamily: 'monospace', fontSize: 11,
                }}
              >
                {runProgress.recent_requests.map((r, i) => {
                  const color = r.duration_ms < 1000 ? '#4ade80' : r.duration_ms < 3000 ? '#fbbf24' : '#f87171'
                  return (
                    <div key={i} style={{ display: 'flex', gap: 8, padding: '1px 0', color: '#cbd5e1', lineHeight: 1.6 }}>
                      <span style={{ color: '#93c5fd', minWidth: 36 }}>{r.method}</span>
                      <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', color: '#e2e8f0' }}>
                        {r.url}
                      </span>
                      <span style={{ color: r.status < 400 ? '#86efac' : '#f87171', minWidth: 30 }}>{r.status}</span>
                      <span style={{ color, minWidth: 52, textAlign: 'right' }}>{r.duration_ms}ms</span>
                    </div>
                  )
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Saved scenarios */}
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 16 }}>
          Saved Scenarios ({scenarios.length})
        </h2>
        {scenarios.length === 0 ? (
          <p style={{ color: '#9ca3af', fontSize: 14 }}>No scenarios recorded yet.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 14 }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #e5e7eb', color: '#6b7280', textAlign: 'left' }}>
                <th style={th}>Name</th>
                <th style={th}>Version</th>
                <th style={th}>Steps</th>
                <th style={th}>Created</th>
                <th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map(s => (
                <React.Fragment key={s.name}>
                <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={td}><strong>{s.name}</strong></td>
                  <td style={{ ...td, color: '#6b7280', fontSize: 13 }}>{s.version || '—'}</td>
                  <td style={td}>{s.step_count}</td>
                  <td style={{ ...td, color: '#6b7280', fontSize: 12 }}>
                    {s.created_at ? new Date(s.created_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ ...td, display: 'flex', gap: 6, alignItems: 'center' }}>
                    <select
                      value={selectedAccounts[s.name] || 'all'}
                      onChange={e => setSelectedAccounts(prev => ({ ...prev, [s.name]: e.target.value }))}
                      disabled={!!runningScenario}
                      style={{ padding: '3px 6px', fontSize: 12, borderRadius: 4, border: '1px solid #d1d5db', color: '#374151' }}
                    >
                      <option value="all">All accounts</option>
                      {accounts
                        .filter(a => a.enabled && (!s.version || a.version === s.version))
                        .map(a => <option key={a.id} value={a.id}>{a.name}</option>)
                      }
                    </select>
                    <button
                      onClick={() => runScenario(s.name)}
                      disabled={!!runningScenario}
                      style={{
                        ...smallBtn,
                        background: runningScenario === s.name ? '#bfdbfe' : '#2563eb',
                        color: '#fff',
                        cursor: runningScenario ? 'default' : 'pointer',
                      }}
                    >
                      {runningScenario === s.name ? 'Running…' : '▶ Run'}
                    </button>
                    <button
                      onClick={() => toggleSteps(s.name)}
                      style={{ ...smallBtn, background: expandedSteps[s.name] ? '#f3f4f6' : '#f9fafb', color: '#374151', cursor: 'pointer' }}
                    >
                      {expandedSteps[s.name] ? '▲ Steps' : '▼ Steps'}
                    </button>
                    <button
                      onClick={() => openEditScenario(s)}
                      style={{ ...smallBtn, background: '#eff6ff', color: '#2563eb', cursor: 'pointer' }}
                    >
                      Edit
                    </button>
                    {isAdmin() && (
                      <button
                        onClick={() => deleteScenario(s.name)}
                        style={{ ...smallBtn, background: '#fef2f2', color: '#dc2626', cursor: 'pointer' }}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
                {expandedSteps[s.name] && (
                  <tr>
                    <td colSpan={5} style={{ padding: '0 12px 12px 12px', background: '#f9fafb' }}>
                      <div style={{ borderRadius: 6, border: '1px solid #e5e7eb', overflow: 'hidden' }}>
                        {expandedSteps[s.name].map((step, i) => (
                          <div key={i} style={{
                            display: 'flex', alignItems: 'center', gap: 10,
                            padding: '6px 12px', fontSize: 12, color: '#374151',
                            borderBottom: i < expandedSteps[s.name].length - 1 ? '1px solid #f3f4f6' : 'none',
                            background: i % 2 === 0 ? '#fff' : '#f9fafb',
                          }}>
                            <span style={{ color: '#9ca3af', minWidth: 20, textAlign: 'right' }}>{i + 1}.</span>
                            <span style={{
                              display: 'inline-block', padding: '1px 6px', borderRadius: 3, fontSize: 10, fontWeight: 600,
                              background: step.action === 'click' ? '#dbeafe' : step.action === 'fill' ? '#dcfce7' : '#f3f4f6',
                              color: step.action === 'click' ? '#2563eb' : step.action === 'fill' ? '#16a34a' : '#6b7280',
                              minWidth: 48, textAlign: 'center',
                            }}>
                              {step.action}
                            </span>
                            <span style={{ flex: 1 }}>{step.name}</span>
                            {step.value && step.value !== '{{PASSWORD}}' && (
                              <span style={{ color: '#9ca3af', fontSize: 11 }}>{step.value}</span>
                            )}
                          </div>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Edit scenario modal */}
      {editingScenario && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: '#fff', borderRadius: 10, padding: 28, width: 420, maxWidth: '90vw', boxShadow: '0 8px 32px rgba(0,0,0,0.18)' }}>
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 20 }}>Edit Scenario</h2>
            <form onSubmit={saveScenarioEdit}>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Name</label>
                <input
                  style={inputStyle}
                  value={editForm.name}
                  onChange={e => setEditForm(f => ({ ...f, name: e.target.value }))}
                  required
                />
              </div>
              <div style={{ marginBottom: 14 }}>
                <label style={labelStyle}>Version</label>
                <select
                  style={{ ...inputStyle, cursor: 'pointer' }}
                  value={editForm.version}
                  onChange={e => setEditForm(f => ({ ...f, version: e.target.value }))}
                >
                  <option value="">— No version —</option>
                  {VERSIONS.map(v => <option key={v} value={v}>{v}</option>)}
                </select>
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
                <button type="button" onClick={closeEditScenario} style={{ ...smallBtn, padding: '8px 16px', fontSize: 14, background: '#f3f4f6', color: '#374151' }}>
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

const btnStyle = (bg) => ({
  background: bg, color: '#fff', border: 'none', borderRadius: 6,
  padding: '8px 16px', fontSize: 14, fontWeight: 600, cursor: 'pointer',
  whiteSpace: 'nowrap',
})
const smallBtn = { border: 'none', borderRadius: 4, padding: '4px 10px', fontSize: 12, fontWeight: 600 }
const th = { padding: '8px 12px', fontWeight: 500, fontSize: 13 }
const td = { padding: '10px 12px', verticalAlign: 'middle' }
const labelStyle = { display: 'block', fontSize: 13, fontWeight: 500, color: '#374151', marginBottom: 4 }
const inputStyle = { width: '100%', padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14, boxSizing: 'border-box' }
