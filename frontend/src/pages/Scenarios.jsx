import { useState, useEffect, useRef } from 'react'

const API = ''

const STATUS_COLOR = {
  pass: { bg: '#dcfce7', color: '#16a34a' },
  warning: { bg: '#fef9c3', color: '#ca8a04' },
  critical: { bg: '#fee2e2', color: '#dc2626' },
  failed: { bg: '#fee2e2', color: '#dc2626' },
  running: { bg: '#dbeafe', color: '#2563eb' },
  completed: { bg: '#dcfce7', color: '#16a34a' },
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
  const [recording, setRecording] = useState(false)
  const [steps, setSteps] = useState([])
  const pollRef = useRef(null)

  const [runningScenario, setRunningScenario] = useState(null)
  const [runProgress, setRunProgress] = useState(null)
  const [message, setMessage] = useState(null)
  const runPollRef = useRef(null)

  useEffect(() => {
    loadScenarios()
    checkRecording()
  }, [])

  async function loadScenarios() {
    try {
      const res = await fetch(`${API}/api/scenarios`)
      setScenarios(await res.json())
    } catch {}
  }

  async function checkRecording() {
    try {
      const res = await fetch(`${API}/api/scenarios/record/status`)
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
        const res = await fetch(`${API}/api/scenarios/record/status`)
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

  async function startRecording(e) {
    e.preventDefault()
    if (!recordName.trim()) return
    try {
      await fetch(`${API}/api/scenarios/record/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: recordName.trim(), url: 'https://app.orcanos.com/orcanos/web/' }),
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
      await fetch(`${API}/api/scenarios/record/stop`, { method: 'POST' })
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
    await fetch(`${API}/api/scenarios/${name}`, { method: 'DELETE' })
    loadScenarios()
  }

  async function runScenario(name) {
    setRunningScenario(name)
    setRunProgress(null)
    setMessage(null)
    try {
      const res = await fetch(`${API}/api/runs/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_name: name }),
      })
      if (!res.ok) {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to start run.' })
        setRunningScenario(null)
        return
      }
      const run = await res.json()
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
        const res = await fetch(`${API}/api/runs/${id}/progress`)
        const data = await res.json()
        setRunProgress(data)
        if (data.status === 'completed' || data.status === 'failed') {
          clearInterval(runPollRef.current)
          setRunningScenario(null)
          setMessage({
            type: data.status === 'completed' ? 'success' : 'error',
            text: data.status === 'completed' ? 'Run completed successfully.' : 'Run failed.',
          })
        }
      } catch {}
    }, 1000)
  }

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
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
          <form onSubmit={startRecording} style={{ display: 'flex', gap: 10 }}>
            <input
              style={{ flex: 1, padding: '8px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}
              value={recordName}
              onChange={e => setRecordName(e.target.value)}
              placeholder="Scenario name (e.g. login_flow)"
              required
            />
            <button type="submit" style={btnStyle('#2563eb')}>Start Recording</button>
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
          <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 12 }}>
            Run Progress &nbsp;<span style={badge(runProgress.status)}>{runProgress.status}</span>
          </h2>
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
                <th style={th}>Steps</th>
                <th style={th}>Created</th>
                <th style={th}></th>
              </tr>
            </thead>
            <tbody>
              {scenarios.map(s => (
                <tr key={s.name} style={{ borderBottom: '1px solid #f3f4f6' }}>
                  <td style={td}><strong>{s.name}</strong></td>
                  <td style={td}>{s.step_count}</td>
                  <td style={{ ...td, color: '#6b7280', fontSize: 12 }}>
                    {s.created_at ? new Date(s.created_at).toLocaleString() : '—'}
                  </td>
                  <td style={{ ...td, display: 'flex', gap: 6 }}>
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
                      onClick={() => deleteScenario(s.name)}
                      style={{ ...smallBtn, background: '#fef2f2', color: '#dc2626', cursor: 'pointer' }}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
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
