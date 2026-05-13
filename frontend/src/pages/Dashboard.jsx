import { useState, useEffect } from 'react'

const API = ''

const STATUS = {
  pass:      { bg: '#dcfce7', color: '#16a34a', label: 'Pass' },
  warning:   { bg: '#fef9c3', color: '#ca8a04', label: 'Warn' },
  critical:  { bg: '#fee2e2', color: '#dc2626', label: 'Slow' },
  failed:    { bg: '#fce7f3', color: '#be185d', label: 'Fail' },
  running:   { bg: '#dbeafe', color: '#2563eb', label: 'Running' },
  completed: { bg: '#dcfce7', color: '#16a34a', label: 'Done' },
  pending:   { bg: '#f3f4f6', color: '#6b7280', label: 'Pending' },
}

function Badge({ status }) {
  const s = STATUS[status] || STATUS.pending
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 99,
      fontSize: 11, fontWeight: 700, background: s.bg, color: s.color,
    }}>
      {s.label}
    </span>
  )
}

function Cell({ step }) {
  const s = STATUS[step.status] || STATUS.pending
  const tip = step.error_message
    ? `Error: ${step.error_message}`
    : `${step.duration_seconds?.toFixed(2)}s`
  return (
    <td title={tip} style={{
      padding: '6px 8px', textAlign: 'center', fontSize: 11,
      background: s.bg, color: s.color, fontWeight: 600,
      border: '1px solid #fff', minWidth: 70, cursor: 'default',
    }}>
      {step.error_message ? '✕' : `${step.duration_seconds?.toFixed(2)}s`}
    </td>
  )
}

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => { loadRuns() }, [])

  async function loadRuns() {
    try {
      const res = await fetch(`${API}/api/results/runs`)
      setRuns(await res.json())
    } catch {}
  }

  async function selectRun(run) {
    setSelectedRun(run)
    setResults(null)
    setLoading(true)
    try {
      const res = await fetch(`${API}/api/results/run/${run.id}`)
      setResults(await res.json())
    } catch {}
    setLoading(false)
  }

  // Collect all unique step names in order
  const stepNames = results
    ? [...new Set(results.accounts.flatMap(a => a.steps.map(s => s.step_name)))]
    : []

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>Select a run to see per-account step timings.</p>

      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

        {/* Runs list */}
        <div style={{ width: 280, flexShrink: 0, background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
          <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', fontWeight: 600, fontSize: 14 }}>
            Recent Runs ({runs.length})
          </div>
          {runs.length === 0 ? (
            <p style={{ padding: 16, color: '#9ca3af', fontSize: 13 }}>No runs yet. Go to Scenarios and hit ▶ Run.</p>
          ) : (
            <div style={{ maxHeight: 600, overflowY: 'auto' }}>
              {runs.map(r => (
                <div
                  key={r.id}
                  onClick={() => selectRun(r)}
                  style={{
                    padding: '12px 16px', cursor: 'pointer', borderBottom: '1px solid #f3f4f6',
                    background: selectedRun?.id === r.id ? '#eff6ff' : '#fff',
                    borderLeft: selectedRun?.id === r.id ? '3px solid #2563eb' : '3px solid transparent',
                  }}
                >
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                    {r.scenario_name || `Run #${r.id}`}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 11, color: '#9ca3af' }}>
                      {r.started_at ? new Date(r.started_at).toLocaleString() : '—'}
                    </span>
                    <Badge status={r.status} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Results matrix */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {!selectedRun && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 32, textAlign: 'center', color: '#9ca3af' }}>
              Select a run from the list
            </div>
          )}

          {selectedRun && loading && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 32, textAlign: 'center', color: '#6b7280' }}>
              Loading…
            </div>
          )}

          {results && !loading && (
            <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden' }}>
              <div style={{ padding: '14px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontWeight: 700, fontSize: 15 }}>{results.scenario_name || `Run #${results.run_id}`}</span>
                  <span style={{ marginLeft: 10 }}><Badge status={results.status} /></span>
                </div>
                <span style={{ fontSize: 12, color: '#9ca3af' }}>
                  {results.started_at ? new Date(results.started_at).toLocaleString() : ''}
                </span>
              </div>

              {results.accounts.length === 0 ? (
                <p style={{ padding: 20, color: '#9ca3af' }}>No results recorded.</p>
              ) : (
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12 }}>
                    <thead>
                      <tr style={{ background: '#f8fafc' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, fontSize: 12, borderBottom: '1px solid #e5e7eb', minWidth: 120 }}>
                          Account
                        </th>
                        {stepNames.map(name => (
                          <th key={name} style={{
                            padding: '6px 8px', fontWeight: 500, fontSize: 11,
                            borderBottom: '1px solid #e5e7eb', color: '#6b7280',
                            maxWidth: 100, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
                          }} title={name}>
                            {name.length > 18 ? name.slice(0, 18) + '…' : name}
                          </th>
                        ))}
                        <th style={{ padding: '6px 8px', fontWeight: 600, fontSize: 11, borderBottom: '1px solid #e5e7eb' }}>
                          Total
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {results.accounts.map(acct => {
                        const stepMap = Object.fromEntries(acct.steps.map(s => [s.step_name, s]))
                        const total = acct.steps.reduce((sum, s) => sum + (s.duration_seconds || 0), 0)
                        const hasError = acct.steps.some(s => s.status === 'failed')
                        const worstStatus = hasError ? 'failed'
                          : acct.steps.some(s => s.status === 'critical') ? 'critical'
                          : acct.steps.some(s => s.status === 'warning') ? 'warning'
                          : 'pass'
                        return (
                          <tr key={acct.name} style={{ borderBottom: '1px solid #f3f4f6' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600, fontSize: 13 }}>
                              {acct.name}
                            </td>
                            {stepNames.map(name => (
                              stepMap[name]
                                ? <Cell key={name} step={stepMap[name]} />
                                : <td key={name} style={{ padding: '6px 8px', textAlign: 'center', color: '#d1d5db', fontSize: 11, border: '1px solid #fff' }}>—</td>
                            ))}
                            <td style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 700, fontSize: 12, ...STATUS[worstStatus] && { color: STATUS[worstStatus].color } }}>
                              {total.toFixed(2)}s
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Legend */}
              <div style={{ padding: '10px 20px', borderTop: '1px solid #f3f4f6', display: 'flex', gap: 16, fontSize: 11, color: '#6b7280' }}>
                {[['pass','< 3s'],['warning','3–8s'],['critical','> 8s'],['failed','Error']].map(([s, lbl]) => (
                  <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 2, background: STATUS[s].bg, border: `1px solid ${STATUS[s].color}`, display: 'inline-block' }} />
                    {lbl}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
