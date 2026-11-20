import React, { useEffect, useState } from 'react'
import { Bundle } from '../core/types'
import { topicAssets, allAssets, download, cachedCount, removeAll,
         storageReport, requestPersistence, Progress } from '../core/offline'
import { Download, Trash, Check } from './Icons'

type Row = { key: string; title: string; urls: string[]; cached: number }

export default function OfflineView({ bundle }: { bundle: Bundle }) {
  const [includeVideo, setIncludeVideo] = useState(true)
  const [rows, setRows] = useState<Row[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [progress, setProgress] = useState<Progress | null>(null)
  const [storage, setStorage] = useState({ usedMb: 0, quotaMb: 0, persisted: false })
  const supported = typeof caches !== 'undefined'

  const build = async () => {
    const next: Row[] = []
    for (const t of bundle.topics) {
      const urls = topicAssets(t, includeVideo)
      next.push({ key: t.topic, title: t.title, urls, cached: await cachedCount(urls) })
    }
    setRows(next)
    setStorage(await storageReport())
  }
  useEffect(() => { if (supported) build() }, [includeVideo, bundle])

  const run = async (key: string, urls: string[]) => {
    setBusy(key); setProgress({ total: urls.length, done: 0, failed: 0, bytes: 0 })
    await requestPersistence()
    await download(urls, setProgress)
    setBusy(null); setProgress(null); await build()
  }
  const clear = async (key: string, urls: string[]) => {
    setBusy(key); await removeAll(urls); setBusy(null); await build()
  }

  if (!supported) return (
    <>
      <header className="topbar"><h1>Offline</h1></header>
      <main className="page">
        <div className="card">
          <h2>Not available in this browser</h2>
          <div className="sub">Offline storage requires a secure connection. Open the published
            address rather than a local network address, then add the application to your home screen.</div>
        </div>
      </main>
    </>
  )

  const everything = allAssets(bundle, includeVideo)
  const totalCached = rows.reduce((a, r) => a + r.cached, 0)
  const totalAssets = rows.reduce((a, r) => a + r.urls.length, 0)

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Offline</h1>
          <div className="subtitle">Store your material on this device for use without a connection</div>
        </div>
      </header>
      <main className="page enter">
        <div className="card">
          <div className="row">
            <div className="grow">
              <h2>Storage in use</h2>
              <div className="sub">
                {storage.usedMb} of {storage.quotaMb} megabytes available
                {storage.persisted ? ', protected from automatic clearing' : ''}
              </div>
            </div>
          </div>
          <div className="meter" style={{ marginTop: 12 }}>
            <span style={{ width: `${Math.min(100, storage.quotaMb ? 100 * storage.usedMb / storage.quotaMb : 0)}%` }} />
          </div>
          <div className="divider" />
          <div className="row">
            <div className="grow">
              <h2>Include videos</h2>
              <div className="sub">Videos are large. Without them the scene player still gives every
                illustration and recording.</div>
            </div>
            <button onClick={() => setIncludeVideo(v => !v)} aria-pressed={includeVideo} style={{
              width: 52, height: 30, borderRadius: 15, flex: 'none',
              background: includeVideo ? 'var(--accent)' : 'var(--surface-sunk)',
              border: '1px solid ' + (includeVideo ? 'var(--accent-ink)' : 'var(--line)'), position: 'relative' }}>
              <span style={{ position: 'absolute', top: 3, left: includeVideo ? 24 : 3, width: 22, height: 22,
                borderRadius: 11, background: '#F6F3EC', boxShadow: '0 1px 3px rgba(46,48,40,.25)',
                transition: 'left .15s' }} />
            </button>
          </div>
        </div>

        <div className="card">
          <div className="row">
            <div className="grow">
              <h2>All material</h2>
              <div className="sub">{totalCached} of {totalAssets} files stored</div>
            </div>
            <button className="btn compact" disabled={!!busy}
              onClick={() => run('__all__', everything)}>
              <Download size={17} />Download all
            </button>
          </div>
          {busy === '__all__' && progress && (
            <>
              <div className="meter" style={{ marginTop: 12 }}>
                <span style={{ width: `${100 * progress.done / Math.max(1, progress.total)}%` }} />
              </div>
              <div className="sub" style={{ marginTop: 8 }}>
                {progress.done} of {progress.total} files, {Math.round(progress.bytes / 1e6)} megabytes transferred
                {progress.failed ? `, ${progress.failed} could not be fetched` : ''}
              </div>
            </>
          )}
        </div>

        <h2 className="section-title">By topic</h2>
        {rows.map(r => {
          const complete = r.cached >= r.urls.length && r.urls.length > 0
          return (
            <div className="card" key={r.key}>
              <div className="row">
                <div className="grow">
                  <h2>{r.title}</h2>
                  <div className="sub">{r.cached} of {r.urls.length} files stored</div>
                </div>
                {complete ? (
                  <>
                    <span className="tag accent"><Check size={14} />Stored</span>
                    <button className="icon-btn" aria-label="Remove downloaded files"
                      disabled={!!busy} onClick={() => clear(r.key, r.urls)}><Trash size={17} /></button>
                  </>
                ) : (
                  <button className="btn compact secondary" disabled={!!busy}
                    onClick={() => run(r.key, r.urls)}><Download size={17} />Download</button>
                )}
              </div>
              {busy === r.key && progress && (
                <>
                  <div className="meter" style={{ marginTop: 12 }}>
                    <span style={{ width: `${100 * progress.done / Math.max(1, progress.total)}%` }} />
                  </div>
                  <div className="sub" style={{ marginTop: 8 }}>
                    {progress.done} of {progress.total} files, {Math.round(progress.bytes / 1e6)} megabytes
                  </div>
                </>
              )}
              {!busy && r.urls.length === 0 && (
                <div className="sub" style={{ marginTop: 8 }}>
                  No downloadable files — this topic is using the built-in sample.
                </div>
              )}
            </div>
          )
        })}

        <div className="card flat">
          <h2>How to use this</h2>
          <div className="sub">
            Download a topic while you have a connection. Afterwards the application opens and runs
            with no network at all, including videos, recordings and illustrations. Downloads resume
            where they stopped, so an interruption costs nothing.
          </div>
        </div>
      </main>
    </>
  )
}
