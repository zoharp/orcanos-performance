import { useState, useEffect, useRef } from 'react'
import { fetchWithAuth, isAdmin } from '../auth'

const API = ''

function getRegion(url) {
  if (!url) return '—'
  if (url.includes('us.orcanos')) return 'US'
  if (url.includes('app.orcanos')) return 'EU'
  return '—'
}

const STATUS = {
  pass:      { bg: '#dcfce7', color: '#16a34a', label: 'Pass' },
  warning:   { bg: '#fef9c3', color: '#ca8a04', label: 'Warn' },
  critical:  { bg: '#fee2e2', color: '#dc2626', label: 'Slow' },
  failed:    { bg: '#fce7f3', color: '#be185d', label: 'Fail' },
  timeout:   { bg: '#ffedd5', color: '#ea580c', label: 'Timeout' },
  running:   { bg: '#dbeafe', color: '#2563eb', label: 'Running' },
  completed: { bg: '#dcfce7', color: '#16a34a', label: 'Done' },
  stopped:   { bg: '#fef9c3', color: '#ca8a04', label: 'Stopped' },
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
  const hasError = !!step.error_message
  const dur = step.duration_seconds != null ? `${step.duration_seconds.toFixed(2)}s` : '—'
  const tip = hasError ? `${dur} — ${step.error_message}` : dur
  return (
    <td title={tip} style={{
      padding: '6px 8px', textAlign: 'center', fontSize: 11,
      background: s.bg, color: s.color, fontWeight: 600,
      border: '1px solid #fff', whiteSpace: 'nowrap', cursor: hasError ? 'help' : 'default',
    }}>
      {step.status === 'timeout' ? step.error_message : hasError ? `${dur} ⚠` : dur}
    </td>
  )
}

function SCard({ title, children }) {
  return (
    <div style={{
      background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8,
      padding: '14px 18px', flex: 1, minWidth: 180,
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#9ca3af', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 10 }}>
        {title}
      </div>
      {children}
    </div>
  )
}

function Sparkline({ data }) {
  if (!data || data.length < 2) {
    return <span style={{ color: '#9ca3af', fontSize: 12 }}>Not enough data</span>
  }
  const vals = data.map(d => d.total_seconds).slice(-10)
  const min = Math.min(...vals)
  const max = Math.max(...vals)
  const range = max - min || 1
  const W = 90, H = 30, PAD = 3
  const points = vals.map((v, i) => ({
    x: PAD + (i / (vals.length - 1)) * (W - PAD * 2),
    y: H - PAD - ((v - min) / range) * (H - PAD * 2),
  }))
  const pts = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
  const diff = vals[vals.length - 1] - vals[vals.length - 2]
  const trendColor = diff <= 0 ? '#16a34a' : '#dc2626'
  const trendArrow = diff <= 0 ? '▼' : '▲'
  const lastPt = points[points.length - 1]
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <svg width={W} height={H} style={{ overflow: 'visible' }}>
        <polyline points={pts} fill="none" stroke="#93c5fd" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
        <circle cx={lastPt.x.toFixed(1)} cy={lastPt.y.toFixed(1)} r={3} fill="#2563eb" />
      </svg>
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: trendColor }}>
          {trendArrow} {Math.abs(diff).toFixed(1)}s
        </div>
        <div style={{ fontSize: 10, color: '#9ca3af' }}>{data.length} runs</div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  const [runs, setRuns] = useState([])
  const [selectedRun, setSelectedRun] = useState(null)
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState(null)
  const pollRef = useRef(null)

  useEffect(() => {
    loadRuns()
    loadSummary()
  }, [])

  // Status of selected run derived from fresh runs list
  const selectedRunStatus = runs.find(r => r.id === selectedRun?.id)?.status ?? selectedRun?.status

  // Poll only when the selected run is active; stop and refresh when it finishes
  useEffect(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
    if (!selectedRun || selectedRunStatus !== 'running') return

    pollRef.current = setInterval(async () => {
      const fresh = await loadRuns()
      if (!fresh) return
      const updated = fresh.find(r => r.id === selectedRun.id)
      if (!updated || updated.status !== 'running') {
        clearInterval(pollRef.current)
        pollRef.current = null
        try {
          const res = await fetchWithAuth(`${API}/api/results/run/${selectedRun.id}`)
          if (res.ok) setResults(await res.json())
        } catch {}
        loadSummary()
      }
    }, 5000)

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [selectedRun?.id, selectedRunStatus])

  async function loadRuns() {
    try {
      const res = await fetchWithAuth(`${API}/api/results/runs`)
      const data = await res.json()
      setRuns(data)
      if (data.length > 0 && !selectedRun) selectRun(data[0])
      return data
    } catch {}
    return null
  }

  async function loadSummary() {
    try {
      const res = await fetchWithAuth(`${API}/api/results/summary`)
      setSummary(await res.json())
    } catch {}
  }

  async function selectRun(run) {
    setSelectedRun(run)
    setResults(null)
    setLoading(true)
    try {
      const res = await fetchWithAuth(`${API}/api/results/run/${run.id}`)
      setResults(await res.json())
    } catch {}
    setLoading(false)
  }

  async function deleteRun(e, run) {
    e.stopPropagation()
    if (!confirm(`Delete run #${run.id} (${run.scenario_name || ''})?`)) return
    await fetchWithAuth(`${API}/api/runs/${run.id}`, { method: 'DELETE' })
    if (selectedRun?.id === run.id) { setSelectedRun(null); setResults(null) }
    loadRuns()
  }

  const stepNames = results
    ? [...new Set(results.accounts.flatMap(a => a.steps.map(s => s.step_name)))]
    : []

  return (
    <div style={{ padding: 24, maxWidth: 1600, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Dashboard</h1>
      <p style={{ color: '#6b7280', marginBottom: 20 }}>Select a run to see per-account step timings.</p>

      {/* Scorecards */}
      {summary && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
          <SCard title="Performance Trend">
            <Sparkline data={summary.trend} />
          </SCard>
          <SCard title="Slowest Account">
            {summary.slowest_account ? (
              <>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#dc2626' }}>{summary.slowest_account.avg_seconds}s</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>{summary.slowest_account.name}</div>
              </>
            ) : <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>}
          </SCard>
          <SCard title="Avg Scenario Time">
            {summary.avg_scenario_seconds != null ? (
              <>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#2563eb' }}>{summary.avg_scenario_seconds}s</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2 }}>across {summary.trend.length} runs</div>
              </>
            ) : <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>}
          </SCard>
          <SCard title="Slowest Step">
            {summary.slowest_step ? (
              <>
                <div style={{ fontSize: 22, fontWeight: 700, color: '#ca8a04' }}>{summary.slowest_step.avg_seconds}s</div>
                <div style={{ fontSize: 12, color: '#6b7280', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 170 }} title={summary.slowest_step.name}>
                  {summary.slowest_step.name}
                </div>
              </>
            ) : <span style={{ color: '#9ca3af', fontSize: 13 }}>No data</span>}
          </SCard>
        </div>
      )}

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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{r.scenario_name || `Run #${r.id}`}</span>
                    {isAdmin() && (
                      <button onClick={e => deleteRun(e, r)} title="Delete run" style={{
                        background: 'none', border: 'none', cursor: 'pointer',
                        color: '#d1d5db', fontSize: 14, padding: '0 2px', lineHeight: 1,
                      }}>✕</button>
                    )}
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 }}>
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
                  <table style={{ borderCollapse: 'collapse', width: '100%', fontSize: 12, minWidth: 800 }}>
                    <thead>
                      <tr style={{ background: '#f8fafc' }}>
                        <th style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, fontSize: 12, borderBottom: '1px solid #e5e7eb', minWidth: 120 }}>
                          Account
                        </th>
                        <th style={{ padding: '8px 12px', textAlign: 'center', fontWeight: 600, fontSize: 12, borderBottom: '1px solid #e5e7eb', minWidth: 60 }}>
                          Region
                        </th>
                        {stepNames.map(name => (
                          <th key={name} style={{
                            padding: '6px 8px', fontWeight: 500, fontSize: 11,
                            borderBottom: '1px solid #e5e7eb', color: '#6b7280',
                            whiteSpace: 'nowrap',
                          }} title={name}>
                            {name}
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
                        const successSteps = acct.steps.filter(s => s.status !== 'failed')
                        const total = successSteps.reduce((sum, s) => sum + (s.duration_seconds || 0), 0)
                        const errorCount = acct.steps.length - successSteps.length
                        const hasError = errorCount > 0
                        const worstStatus = hasError ? 'failed'
                          : acct.steps.some(s => s.status === 'critical') ? 'critical'
                          : acct.steps.some(s => s.status === 'warning') ? 'warning'
                          : 'pass'
                        return (
                          <tr key={acct.name} style={{ borderBottom: '1px solid #f3f4f6' }}>
                            <td style={{ padding: '8px 12px', fontWeight: 600, fontSize: 13 }}>
                              {acct.name}
                            </td>
                            <td style={{ padding: '8px 12px', textAlign: 'center', fontSize: 12, color: '#6b7280' }}>
                              {getRegion(acct.url)}
                            </td>
                            {stepNames.map(name => (
                              stepMap[name]
                                ? <Cell key={name} step={stepMap[name]} />
                                : <td key={name} style={{ padding: '6px 8px', textAlign: 'center', color: '#d1d5db', fontSize: 11, border: '1px solid #fff' }}>—</td>
                            ))}
                            <td style={{ padding: '6px 10px', textAlign: 'center', fontWeight: 700, fontSize: 12, color: STATUS[worstStatus]?.color, whiteSpace: 'nowrap' }}>
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
                {[['pass','< 3s'],['warning','3–8s'],['critical','> 8s'],['timeout','Timeout'],['failed','Error']].map(([s, lbl]) => (
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
