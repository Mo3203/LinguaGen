import React, { useMemo, useState } from 'react'
import { Bundle, Unit, Topic, Mode, AppState } from '../core/types'
import { topicSummary, suggestNext, unitStatus } from '../core/status'
import { pct } from '../core/session'
import { Forward, Check } from './Icons'
import { L } from '../core/profile'

export default function Home({ bundle, state, dueCount, openTopic, openSession, openDue }: {
  bundle: Bundle; state: AppState; dueCount: number
  openTopic: (t: Topic) => void
  openSession: (u: Unit, m: Mode) => void
  openDue: () => void
}) {
  const [query, setQuery] = useState('')

  const totals = useMemo(() => {
    const units = bundle.topics.reduce((a, t) => a + t.units.length, 0)
    const words = bundle.topics.reduce((a, t) => a + t.units.reduce((b, u) => b + u.words.length, 0), 0)
    let completed = 0
    for (const t of bundle.topics) for (const u of t.units) {
      const st = unitStatus(u, state)
      if (st === 'studied' || st === 'reviewed') completed++
    }
    return { topics: bundle.topics.length, units, words, completed }
  }, [bundle, state])

  const resumable = Object.values(state.sessions).find(s => !s.finishedAt)
  const resumeUnit = resumable && bundle.topics.flatMap(t => t.units).find(u => u.id === resumable.unitId)
  const suggestion = useMemo(() => suggestNext(bundle.topics, state), [bundle, state])

  const q = query.trim().toLowerCase()
  const visible = q
    ? bundle.topics.filter(t =>
        t.title.toLowerCase().includes(q) ||
        t.units.some(u => u.words.some(w =>
          (w.display || w.word).toLowerCase().includes(q) || w.meaning.toLowerCase().includes(q))))
    : bundle.topics

  return (
    <>
      <header className="topbar">
        <div>
          <h1>{L().labels.greeting}</h1>
          <div className="subtitle">{totals.completed} of {totals.units} units completed</div>
        </div>
      </header>

      <main className="page enter">
        {resumable && resumeUnit ? (
          <div className="notice">
            <div className="row">
              <div className="grow">
                <b>Continue where you stopped</b>
                <div className="sub" style={{ marginTop: 3 }}>
                  {resumeUnit.title} — {resumable.mode === 'study' ? 'Study' : 'Review'} session,
                  {' '}{pct(resumable)} percent complete
                </div>
              </div>
              <button className="btn compact" onClick={() => openSession(resumeUnit, resumable.mode)}>Resume</button>
            </div>
          </div>
        ) : suggestion ? (
          <div className="notice">
            <div className="row">
              <div className="grow">
                <b>Suggested next unit</b>
                <div className="sub" style={{ marginTop: 3 }}>{suggestion.unit.title}</div>
              </div>
              <button className="btn compact" onClick={() => openSession(suggestion.unit, 'study')}>Begin</button>
            </div>
          </div>
        ) : null}

        <div className="card row">
          <div className="grow">
            <h2>Scheduled review</h2>
            <div className="sub">
              {dueCount === 0 ? 'Nothing is due at the moment'
                : `${dueCount} ${dueCount === 1 ? 'word is' : 'words are'} ready for review`}
            </div>
          </div>
          <button className="btn compact" disabled={dueCount === 0} onClick={openDue}>
            Begin<Forward size={17} />
          </button>
        </div>

        <input className="entry search" value={query} onChange={e => setQuery(e.target.value)}
          placeholder="Search topics or words" aria-label="Search topics or words" />

        <h2 className="section-title">
          {q ? `${visible.length} matching topics`
             : `${totals.topics} topics, ${totals.units} units, ${totals.words} words`}
        </h2>

        {visible.map(t => {
          const s = topicSummary(t, state)
          const finished = s.completed === s.units && s.units > 0
          return (
            <button className="card topic-card" key={t.topic} onClick={() => openTopic(t)}>
              <div className="row">
                <div className="grow">
                  <h2>{t.title}</h2>
                  <div className="sub">
                    {s.units} units, {s.words} words
                    {s.started > 0 ? ` — ${s.completed} of ${s.units} completed` : ''}
                  </div>
                </div>
                {finished
                  ? <span className="tag accent"><Check size={14} />Complete</span>
                  : <span className="tag">{s.established} percent</span>}
                <span style={{ color: 'var(--muted)' }}><Forward size={18} /></span>
              </div>
              <div className="meter" style={{ marginTop: 12 }}>
                <span style={{ width: `${s.established}%` }} />
              </div>
            </button>
          )
        })}

        {visible.length === 0 && (
          <div className="card">
            <h2>No matches</h2>
            <div className="sub">No topic or word matches that search.</div>
          </div>
        )}
      </main>
    </>
  )
}
