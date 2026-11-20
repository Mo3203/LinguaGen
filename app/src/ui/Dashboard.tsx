import React from 'react'
import { Word, AppState } from '../core/types'
import { bucket } from '../core/scheduler'

const STAGES = [
  { key: 'new', label: 'Not started', color: '#CFC9BB' },
  { key: 'learning', label: 'Learning', color: '#B08A63' },
  { key: 'young', label: 'Consolidating', color: '#6E8C9E' },
  { key: 'mature', label: 'Established', color: '#4E6E64' },
] as const

export default function Dashboard({ words, state }: { words: Word[]; state: AppState }) {
  const counts: Record<string, number> = { new: 0, learning: 0, young: 0, mature: 0 }
  words.forEach(w => counts[bucket(state.reviews[w.id])]++)
  const total = Math.max(1, words.length)

  const days = Array.from({ length: 14 }, (_, k) => {
    const d = new Date(); d.setDate(d.getDate() - (13 - k))
    const key = d.toDateString()
    return { key, count: state.logs.filter(l => new Date(l.at).toDateString() === key).length }
  })
  const peak = Math.max(1, ...days.map(d => d.count))
  const recent = state.dictations.slice(-60)
  const dictationAverage = recent.length
    ? Math.round(100 * recent.reduce((a, d) => a + d.score, 0) / recent.length) : null

  return (
    <>
      <header className="topbar">
        <div>
          <h1>Progress</h1>
          <div className="subtitle">{words.length} words across your material</div>
        </div>
      </header>
      <main className="page enter">
        <div className="card">
          <h2>Vocabulary stages</h2>
          <div className="stacked">
            {[...STAGES].reverse().map(s => counts[s.key] > 0 && (
              <div key={s.key} style={{ width: `${100 * counts[s.key] / total}%`, background: s.color }} />
            ))}
          </div>
          <div className="legend">
            {STAGES.map(s => (
              <span key={s.key}>
                <span className="key" style={{ background: s.color }} />{s.label}: {counts[s.key]}
              </span>
            ))}
          </div>
        </div>

        <div className="card">
          <h2>Sessions completed</h2>
          <div className="sub">Last fourteen days</div>
          <div className="chart">
            {days.map(d => (
              <div key={d.key} className={'bar' + (d.count ? ' active' : '')}
                style={{ height: `${10 + 62 * d.count / peak}%` }} title={`${d.key}: ${d.count}`} />
            ))}
          </div>
        </div>

        <div className="card row">
          <div className="grow">
            <h2>Dictation accuracy</h2>
            <div className="sub">Across your last {recent.length} sentences</div>
          </div>
          <div className="french lead">{dictationAverage === null ? '—' : `${dictationAverage}%`}</div>
        </div>

        <div className="card row">
          <div className="grow">
            <h2>Total sessions</h2>
            <div className="sub">Study and review combined</div>
          </div>
          <div className="french lead">{state.logs.length}</div>
        </div>
      </main>
    </>
  )
}
