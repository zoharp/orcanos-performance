import { useState, useEffect } from 'react'
import { fetchWithAuth } from '../auth'

const API = ''

export default function Settings() {
  const [form, setForm] = useState(null)
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { load() }, [])

  async function load() {
    try {
      const res = await fetchWithAuth(`${API}/api/config/`)
      setForm(await res.json())
    } catch {
      setMessage({ type: 'error', text: 'Failed to load config.' })
    }
  }

  async function save(e) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const res = await fetchWithAuth(`${API}/api/config/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          step_timeout_seconds: Number(form.step_timeout_seconds),
          pass_threshold_seconds: Number(form.pass_threshold_seconds),
          warn_threshold_seconds: Number(form.warn_threshold_seconds),
        }),
      })
      if (!res.ok) {
        const err = await res.json()
        setMessage({ type: 'error', text: err.detail || 'Failed to save.' })
      } else {
        setMessage({ type: 'success', text: 'Settings saved.' })
      }
    } catch {
      setMessage({ type: 'error', text: 'Cannot reach backend.' })
    }
    setSaving(false)
  }

  function set(key, val) {
    setForm(f => ({ ...f, [key]: val }))
  }

  if (!form) return <div style={{ padding: 24, color: '#6b7280' }}>Loading…</div>

  return (
    <div style={{ padding: 24, maxWidth: 480, margin: '0 auto' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 4 }}>Settings</h1>
      <p style={{ color: '#6b7280', marginBottom: 24 }}>Thresholds apply to the next run. Saved to <code>config.json</code>.</p>

      {message && (
        <div style={{
          padding: '10px 14px', borderRadius: 6, marginBottom: 20, fontSize: 13,
          background: message.type === 'error' ? '#fef2f2' : '#f0fdf4',
          color: message.type === 'error' ? '#dc2626' : '#16a34a',
          border: `1px solid ${message.type === 'error' ? '#fecaca' : '#bbf7d0'}`,
        }}>
          {message.text}
        </div>
      )}

      <form onSubmit={save}>
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>

          <Field
            label="Pass threshold"
            hint="Steps faster than this are green"
            unit="seconds"
            value={form.pass_threshold_seconds}
            onChange={v => set('pass_threshold_seconds', v)}
          />
          <Field
            label="Warn threshold"
            hint="Steps between pass and this are yellow"
            unit="seconds"
            value={form.warn_threshold_seconds}
            onChange={v => set('warn_threshold_seconds', v)}
          />
          <Field
            label="Step timeout"
            hint="Steps exceeding this are marked timeout and skipped"
            unit="seconds"
            value={form.step_timeout_seconds}
            onChange={v => set('step_timeout_seconds', v)}
          />

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, paddingTop: 4, borderTop: '1px solid #f3f4f6' }}>
            <div style={{ fontSize: 12, color: '#9ca3af', flex: 1 }}>
              <ColorBar pass={form.pass_threshold_seconds} warn={form.warn_threshold_seconds} timeout={form.step_timeout_seconds} />
            </div>
          </div>

          <button type="submit" disabled={saving} style={{
            background: saving ? '#93c5fd' : '#2563eb', color: '#fff',
            border: 'none', borderRadius: 6, padding: '10px 20px',
            fontSize: 14, fontWeight: 600, cursor: saving ? 'default' : 'pointer',
          }}>
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, hint, unit, value, onChange }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 13, fontWeight: 600, color: '#374151', marginBottom: 4 }}>
        {label}
      </label>
      <p style={{ fontSize: 12, color: '#9ca3af', marginBottom: 6 }}>{hint}</p>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <input
          type="number"
          min="1"
          step="1"
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{ width: 80, padding: '7px 10px', border: '1px solid #d1d5db', borderRadius: 6, fontSize: 14 }}
          required
        />
        <span style={{ fontSize: 13, color: '#6b7280' }}>{unit}</span>
      </div>
    </div>
  )
}

function ColorBar({ pass, warn, timeout }) {
  const total = Math.max(Number(timeout) + 5, 60)
  const pPct = (pass / total) * 100
  const wPct = ((warn - pass) / total) * 100
  const tPct = ((timeout - warn) / total) * 100
  return (
    <div>
      <div style={{ display: 'flex', height: 10, borderRadius: 4, overflow: 'hidden', marginBottom: 4 }}>
        <div style={{ width: `${pPct}%`, background: '#16a34a' }} title={`0–${pass}s: pass`} />
        <div style={{ width: `${wPct}%`, background: '#ca8a04' }} title={`${pass}–${warn}s: warning`} />
        <div style={{ width: `${tPct}%`, background: '#dc2626' }} title={`${warn}–${timeout}s: critical`} />
        <div style={{ flex: 1, background: '#ea580c' }} title={`>${timeout}s: timeout`} />
      </div>
      <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#6b7280' }}>
        <span style={{ color: '#16a34a' }}>■ 0–{pass}s pass</span>
        <span style={{ color: '#ca8a04' }}>■ {pass}–{warn}s warn</span>
        <span style={{ color: '#dc2626' }}>■ {warn}–{timeout}s critical</span>
        <span style={{ color: '#ea580c' }}>■ &gt;{timeout}s timeout</span>
      </div>
    </div>
  )
}
