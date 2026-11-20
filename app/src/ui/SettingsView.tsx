import React, { useRef } from 'react'
import { AppState } from '../core/types'
import { LocalStateAdapter } from '../adapters/state'
import { APP_VERSION, APP_BUILT } from '../version'
import { L } from '../core/profile'

export default function SettingsView({ state, update, store, setState }: {
  state: AppState; update: (fn: (s: AppState) => AppState) => void
  store: LocalStateAdapter; setState: (s: AppState) => void
}) {
  const fileRef = useRef<HTMLInputElement | null>(null)
  const set = (patch: Partial<AppState['settings']>) =>
    update(s => ({ ...s, settings: { ...s.settings, ...patch } }))

  const exportBackup = () => {
    const blob = new Blob([store.export()], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `${L().name.toLowerCase()}-study-backup-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
  }
  const importBackup = (f: File) => f.text().then(t => {
    try { setState(store.import(t)); alert('Backup imported successfully.') }
    catch { alert('That file could not be read as a valid backup.') }
  })

  const Switch = ({ on, onChange, label }: { on: boolean; onChange: (v: boolean) => void; label: string }) => (
    <button onClick={() => onChange(!on)} aria-label={label} aria-pressed={on} style={{
      width: 52, height: 30, borderRadius: 15, flex: 'none',
      background: on ? 'var(--accent)' : 'var(--surface-sunk)',
      border: '1px solid ' + (on ? 'var(--accent-ink)' : 'var(--line)'),
      position: 'relative', transition: 'background .15s',
    }}>
      <span style={{
        position: 'absolute', top: 3, left: on ? 24 : 3, width: 22, height: 22, borderRadius: 11,
        background: '#F6F3EC', boxShadow: '0 1px 3px rgba(46,48,40,.25)', transition: 'left .15s',
      }} />
    </button>
  )

  const speedPercent = Math.round(state.settings.speechRate * 100)

  return (
    <>
      <header className="topbar"><h1>Preferences</h1></header>
      <main className="page enter">
        <div className="card row">
          <div className="grow">
            <h2>Require exact accents</h2>
            <div className="sub">When checking dictation, treat letters with and without marks ({L().characters.slice(0, 4).join(', ')}) as different</div>
          </div>
          <Switch on={state.settings.strictAccents} label="Require exact accents"
            onChange={v => set({ strictAccents: v })} />
        </div>

        <div className="card row">
          <div className="grow">
            <h2>{L().labels.targetOnly} by default</h2>
            <div className="sub">Hide English translations in the video, reading and player views</div>
          </div>
          <Switch on={state.settings.frenchOnly} label={`${L().labels.targetOnly} by default`}
            onChange={v => set({ frenchOnly: v })} />
        </div>

        <div className="card">
          <h2>Speaking speed</h2>
          <div className="sub">Currently {speedPercent} percent of normal speed</div>
          <input type="range" min="0.6" max="1.3" step="0.05" style={{ width: '100%', marginTop: 12 }}
            value={state.settings.speechRate}
            onChange={e => set({ speechRate: parseFloat(e.target.value) })} />
        </div>

        <div className="card">
          <h2>Your learning data</h2>
          <div className="sub">
            Progress is stored on this device. Export a backup to keep it safe or move it to another device.
          </div>
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn compact" onClick={exportBackup}>Export backup</button>
            <button className="btn compact secondary" onClick={() => fileRef.current?.click()}>Import backup</button>
            <input ref={fileRef} type="file" accept="application/json" hidden
              onChange={e => e.target.files?.[0] && importBackup(e.target.files[0])} />
          </div>
        </div>

        <div className="card">
          <h2>Application version</h2>
          <div className="sub">
            Version {APP_VERSION}, built {APP_BUILT}. If you have published an update and still
            see the previous version, use the button below and then reload the page.
          </div>
          <div className="row" style={{ marginTop: 14 }}>
            <button className="btn compact secondary" onClick={async () => {
              try {
                const regs = await navigator.serviceWorker?.getRegistrations?.() || []
                await Promise.all(regs.map(r => r.update()))
                navigator.serviceWorker?.controller?.postMessage('clear-shell')
                alert('Application files refreshed. Reload the page to finish.')
              } catch { alert('Could not refresh automatically. Reload the page.') }
            }}>Refresh application files</button>
          </div>
        </div>

        <div className="card">
          <h2>Study material</h2>
          <div className="sub">
            When a content folder is installed, the application uses your generated videos, recordings and
            illustrations. Without it, a sample drawn from your dataset is used with the browser voice.
          </div>
        </div>
      </main>
    </>
  )
}
