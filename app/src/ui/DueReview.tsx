import React, { useMemo, useState } from 'react'
import { Word, AppState, Grade } from '../core/types'
import { isDue, newCard, grade } from '../core/scheduler'
import { media } from './App'
import { Close, Sound, Check } from './Icons'
import { L, wordTitle } from '../core/profile'

export default function DueReview({ words, state, update, exit }: {
  words: Word[]; state: AppState
  update: (fn: (s: AppState) => AppState) => void; exit: () => void
}) {
  const queue = useMemo(() => words.filter(w => isDue(state.reviews[w.id])), [])
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)

  if (index >= queue.length) return (
    <>
      <header className="topbar">
        <button className="icon-btn" onClick={exit} aria-label="Close"><Close size={19} /></button>
        <h1 style={{ fontSize: 18 }}>Scheduled review</h1>
      </header>
      <main className="page enter">
        <div className="completion">
          <span style={{ color: 'var(--accent)' }}><Check size={40} /></span>
          <h2>Review complete</h2>
          <p className="sub">Nothing further is due right now.</p>
        </div>
        <button className="btn block" onClick={exit}>Return to units</button>
      </main>
    </>
  )

  const w = queue[index]
  const direction = index % 2 === 0 ? 'fr-en' : 'en-fr'
  const submit = (g: Grade) => {
    update(s => ({ ...s, reviews: { ...s.reviews, [w.id]: grade(s.reviews[w.id] || newCard(), g) } }))
    setRevealed(false); setIndex(index + 1)
  }

  return (
    <>
      <header className="topbar">
        <button className="icon-btn" onClick={exit} aria-label="Close"><Close size={19} /></button>
        <div className="grow">
          <h1 style={{ fontSize: 18 }}>Scheduled review</h1>
          <div className="subtitle">
            Word {index + 1} of {queue.length} — {direction === 'fr-en' ? L().labels.targetToNative : L().labels.nativeToTarget}
          </div>
        </div>
      </header>
      <main className="page enter" key={w.id + direction}>
        <div className="card" style={{ textAlign: 'center', padding: '34px 18px' }}>
          <div className="french lead">{direction === 'fr-en' ? wordTitle(w) : w.meaning}</div>
          {direction === 'fr-en' && (
            <button className="icon-btn" style={{ margin: '16px auto 0' }} aria-label="Pronounce"
              onClick={() => media.speak(w, state.settings.speechRate)}><Sound size={18} /></button>
          )}
        </div>
        {!revealed ? (
          <button className="btn block" onClick={() => setRevealed(true)}>Reveal answer</button>
        ) : (
          <div className="card enter">
            <label className="field">Answer</label>
            <div className="french">{direction === 'fr-en' ? w.meaning : wordTitle(w)}</div>
            {w.sentences[0] && <p className="sub" style={{ marginTop: 10 }}>{w.sentences[0].fr}</p>}
            <div className="grades">
              <button className="btn grade-again" onClick={() => submit(0)}>Again</button>
              <button className="btn grade-hard" onClick={() => submit(1)}>Hard</button>
              <button className="btn grade-good" onClick={() => submit(2)}>Good</button>
              <button className="btn grade-easy" onClick={() => submit(3)}>Easy</button>
            </div>
          </div>
        )}
      </main>
    </>
  )
}
