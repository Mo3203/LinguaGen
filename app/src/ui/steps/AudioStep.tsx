import React, { useEffect, useRef, useState } from 'react'
import { Unit, Mode, AppState, Sentence } from '../../core/types'
import { compare, Token } from '../../core/dictation'
import { media } from '../App'
import AccentBar from '../AccentBar'
import { Play, Pause, Sound, Headphones } from '../Icons'

export default function AudioStep({ unit, mode, state, update, rep, onRepDone }: {
  unit: Unit; mode: Mode; state: AppState; rep: number; onRepDone: () => void
  update: (fn: (s: AppState) => AppState) => void
}) {
  const sentences = unit.words.flatMap(w => w.sentences)
  const continuous = mode === 'review' || rep >= 1
  const [attempts, setAttempts] = useState<Record<string, string>>({})
  const [results, setResults] = useState<Record<string, { tokens: Token[]; score: number }>>({})
  const [playingAll, setPlayingAll] = useState(false)
  const stopRef = useRef(false)
  const focusTarget = useRef<any>(null)

  const practiceUrl = unit.practice ? './content/' + unit.practice : null
  const [hasPractice, setHasPractice] = useState(false)
  useEffect(() => {
    let alive = true
    if (!practiceUrl) return
    fetch(practiceUrl, { method: 'HEAD' })
      .then(r => alive && setHasPractice(r.ok)).catch(() => alive && setHasPractice(false))
    return () => { alive = false }
  }, [practiceUrl])

  const playAll = async () => {
    stopRef.current = false; setPlayingAll(true)
    for (const s of sentences) {
      if (stopRef.current) break
      await media.speak(s, state.settings.speechRate)
      await new Promise(r => setTimeout(r, continuous ? 500 : 1300))
    }
    setPlayingAll(false)
  }
  const stopAll = () => { stopRef.current = true; media.stop(); setPlayingAll(false) }

  const check = () => {
    const next: typeof results = {}
    const dictations = [...state.dictations]
    for (const s of sentences) {
      const r = compare(s.fr, attempts[s.id] || '', state.settings.strictAccents)
      next[s.id] = r
      dictations.push({ sentenceId: s.id, attempt: attempts[s.id] || '', score: r.score, at: Date.now() })
    }
    setResults(next)
    update(st => ({ ...st, dictations: dictations.slice(-500) }))
    onRepDone()
  }

  const scores = Object.values(results)
  const average = scores.length
    ? Math.round(100 * scores.reduce((a, r) => a + r.score, 0) / scores.length) : null

  return (
    <div className="enter">
      <div className="card row">
        <div className="grow">
          <h2>{continuous ? 'Continuous dictation' : 'Dictation with pauses'}</h2>
          <div className="sub">{continuous
            ? 'Play the whole set and write as it continues, without stopping.'
            : 'Play each sentence, pause, and write what you heard.'}</div>
        </div>
        {playingAll
          ? <button className="btn compact secondary" onClick={stopAll}><Pause size={17} />Stop</button>
          : <button className="btn compact" onClick={playAll}><Play size={17} />Play all</button>}
      </div>

      {hasPractice && practiceUrl && (
        <div className="card">
          <div className="row">
            <span style={{ color: 'var(--accent)' }}><Headphones size={22} /></span>
            <div className="grow">
              <h2>Unit practice track</h2>
              <div className="sub">Your generated recording — each item three times with pauses to repeat aloud.</div>
            </div>
          </div>
          <audio src={practiceUrl} controls preload="none" style={{ width: '100%', marginTop: 12 }} />
        </div>
      )}

      {sentences.map((s, i) => (
        <div className="card" key={s.id}>
          <div className="row" style={{ marginBottom: 10 }}>
            <button className="icon-btn" aria-label="Play sentence"
              onClick={() => media.speak(s, state.settings.speechRate)}><Sound size={18} /></button>
            <span className="sub">Sentence {i + 1} — {s.register.replace(/_/g, ' ')}</span>
          </div>
          <textarea className="entry" placeholder="Write what you hear"
            value={attempts[s.id] || ''}
            onFocus={e => (focusTarget.current = e.currentTarget)}
            onChange={e => setAttempts(a => ({ ...a, [s.id]: e.target.value }))} />
          {results[s.id] && (
            <div className="review">
              {results[s.id].tokens.map((t, k) => (
                <span key={k} className={'token ' + t.kind}>
                  {t.text}
                  {t.kind === 'wrong' && t.expected && <span className="correction">correct: {t.expected}</span>}
                </span>
              ))}
              <div className="sub" style={{ marginTop: 8 }}>
                Accuracy: {Math.round(results[s.id].score * 100)} percent
              </div>
            </div>
          )}
        </div>
      ))}

      <AccentBar target={focusTarget} />
      <div style={{ height: 14 }} />
      <button className="btn block" onClick={check}>Check my dictation</button>

      {average !== null && (
        <div className="card flat" style={{ marginTop: 14 }}>
          <h2>Pass accuracy: {average} percent</h2>
          <div className="legend">
            <span><span className="key" style={{ background: 'var(--affirm-soft)' }} />Correct</span>
            <span><span className="key" style={{ background: 'var(--alert-soft)' }} />Incorrect word</span>
            <span><span className="key" style={{ background: 'var(--caution-soft)' }} />Missing word</span>
            <span><span className="key" style={{ background: 'var(--surface-sunk)' }} />Extra word</span>
          </div>
        </div>
      )}
    </div>
  )
}
