import React, { useRef, useState } from 'react'
import { Unit, AppState, Grade } from '../../core/types'
import { newCard, grade } from '../../core/scheduler'
import AccentBar from '../AccentBar'
import { Check } from '../Icons'
import { L, genderLabel, wordTitle } from '../../core/profile'

export default function RecallStep({ unit, direction, state, update, onRepDone }: {
  unit: Unit; direction: 'fr-en' | 'en-fr'; state: AppState; rep: number
  update: (fn: (s: AppState) => AppState) => void; onRepDone: () => void; mode: string
}) {
  const words = unit.words
  const [index, setIndex] = useState(0)
  const [answer, setAnswer] = useState('')
  const [example, setExample] = useState('')
  const [revealed, setRevealed] = useState(false)
  const [finished, setFinished] = useState(false)
  const focusTarget = useRef<any>(null)

  const title = direction === 'fr-en' ? L().labels.targetToNative : L().labels.nativeToTarget

  if (finished || words.length === 0) return (
    <div className="completion enter">
      <span style={{ color: 'var(--accent)' }}><Check size={40} /></span>
      <h2>{title} complete</h2>
      <p className="sub">Your grades have been saved to the review schedule.</p>
    </div>
  )

  const w = words[index]
  const prompt = direction === 'fr-en' ? wordTitle(w) : w.meaning
  const expected = direction === 'fr-en' ? w.meaning : wordTitle(w)

  const submit = (g: Grade) => {
    update(s => ({ ...s, reviews: { ...s.reviews, [w.id]: grade(s.reviews[w.id] || newCard(), g) } }))
    setAnswer(''); setExample(''); setRevealed(false)
    if (index + 1 >= words.length) { setFinished(true); onRepDone() } else setIndex(index + 1)
  }

  return (
    <div className="enter" key={w.id}>
      <div className="card" style={{ textAlign: 'center' }}>
        <div className="sub">Word {index + 1} of {words.length}</div>
        <div className="french lead" style={{ margin: '12px 0 6px' }}>{prompt}</div>
        {direction === 'fr-en' && (
          <div className="tagrow" style={{ justifyContent: 'center' }}>
            <span className="tag accent">{w.pos.replace(/_/g, ' ')}</span>
            {genderLabel(w.gender) && <span className="tag caution">{genderLabel(w.gender)}</span>}
          </div>
        )}
      </div>

      <div className="card">
        <label className="field">{direction === 'fr-en' ? 'English meaning' : L().labels.targetWord}</label>
        <input className="entry" value={answer}
          onFocus={e => (focusTarget.current = e.currentTarget)}
          onChange={e => setAnswer(e.target.value)} placeholder="Your answer" />
        <div style={{ height: 14 }} />
        <label className="field">A complete example sentence in {L().name}</label>
        <textarea className="entry" value={example}
          onFocus={e => (focusTarget.current = e.currentTarget)}
          onChange={e => setExample(e.target.value)} placeholder="Write a full sentence" />
        <AccentBar target={focusTarget} />
      </div>

      {!revealed ? (
        <button className="btn block" onClick={() => setRevealed(true)}>Reveal answer</button>
      ) : (
        <div className="card enter">
          <label className="field">Answer</label>
          <div className="french">{expected}</div>
          <div className="divider" />
          <label className="field">Reference sentences</label>
          {w.sentences.map(s => (
            <p key={s.id} style={{ margin: '8px 0', fontSize: 16 }}>{s.fr}</p>
          ))}
          <label className="field" style={{ marginTop: 16 }}>How well did you recall it?</label>
          <div className="grades">
            <button className="btn grade-again" onClick={() => submit(0)}>Again</button>
            <button className="btn grade-hard" onClick={() => submit(1)}>Hard</button>
            <button className="btn grade-good" onClick={() => submit(2)}>Good</button>
            <button className="btn grade-easy" onClick={() => submit(3)}>Easy</button>
          </div>
        </div>
      )}
    </div>
  )
}
