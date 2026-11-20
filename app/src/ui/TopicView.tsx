import React from 'react'
import { Topic, Unit, Mode, AppState } from '../core/types'
import { unitStatus, STATUS_LABEL, unitEstablished, topicSummary } from '../core/status'
import { pct } from '../core/session'
import { Back, Check } from './Icons'

export default function TopicView({ topic, state, openSession, back }: {
  topic: Topic; state: AppState
  openSession: (u: Unit, m: Mode) => void; back: () => void
}) {
  const s = topicSummary(topic, state)

  return (
    <>
      <header className="topbar">
        <button className="icon-btn" onClick={back} aria-label="Back to topics"><Back size={19} /></button>
        <div className="grow">
          <h1 style={{ fontSize: 20 }}>{topic.title}</h1>
          <div className="subtitle">
            {s.units} units, {s.words} words — {s.completed} completed, {s.established} percent established
          </div>
        </div>
      </header>

      <main className="page enter">
        <div className="meter" style={{ marginBottom: 18 }}>
          <span style={{ width: `${s.established}%` }} />
        </div>

        {topic.units.map((u, i) => {
          const status = unitStatus(u, state)
          const value = unitEstablished(u, state)
          const active = state.sessions[u.id + ':study'] && !state.sessions[u.id + ':study'].finishedAt
            ? state.sessions[u.id + ':study']
            : state.sessions[u.id + ':review'] && !state.sessions[u.id + ':review'].finishedAt
              ? state.sessions[u.id + ':review'] : null
          const done = status === 'studied' || status === 'reviewed'

          return (
            <div className="card unit-card" key={u.id}>
              <div className="row">
                <span className={'unit-number' + (done ? ' done' : '')}>
                  {done ? <Check size={16} /> : i + 1}
                </span>
                <div className="grow">
                  <h2>Unit {i + 1}</h2>
                  <div className="sub">
                    {u.words.map(w => w.word).slice(0, 4).join(', ')}
                    {u.words.length > 4 ? ` and ${u.words.length - 4} more` : ''}
                  </div>
                </div>
                <span className={'tag' + (done ? ' accent' : status === 'in-progress' ? ' info' : '')}>
                  {STATUS_LABEL[status]}
                </span>
              </div>

              {active && (
                <div className="sub" style={{ marginTop: 10 }}>
                  Session in progress — {pct(active)} percent complete
                </div>
              )}

              <div className="meter" style={{ marginTop: 12 }}>
                <span style={{ width: `${value}%` }} />
              </div>

              <div className="row" style={{ marginTop: 14, gap: 10 }}>
                <button className="btn compact" onClick={() => openSession(u, 'study')}>
                  {active && active.mode === 'study' ? 'Resume study' : 'Study'}
                </button>
                <button className="btn compact secondary" onClick={() => openSession(u, 'review')}>
                  {active && active.mode === 'review' ? 'Resume review' : 'Review'}
                </button>
                <div className="grow" />
                <span className="sub">{u.words.length} words</span>
              </div>
            </div>
          )
        })}
      </main>
    </>
  )
}
