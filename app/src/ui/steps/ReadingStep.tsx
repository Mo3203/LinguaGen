import React, { useState } from 'react'
import { Unit, AppState } from '../../core/types'
import { media } from '../App'
import { Sound, Check } from '../Icons'
import { genderLabel, wordTitle } from '../../core/profile'

export default function ReadingStep({ unit, state, onRepDone }: {
  unit: Unit; state: AppState; rep: number; onRepDone: () => void
  mode: string; update: (fn: (s: AppState) => AppState) => void
}) {
  const [showEnglish, setShowEnglish] = useState(!state.settings.frenchOnly)
  return (
    <div className="enter">
      <div className="row" style={{ justifyContent: 'flex-end', marginBottom: 12 }}>
        <button className="btn secondary compact" onClick={() => setShowEnglish(v => !v)}>
          {showEnglish ? 'Hide English' : 'Show English'}
        </button>
      </div>

      {unit.words.map(w => (
        <div className="card" key={w.id}>
          <div className="row">
            <div className="grow">
              <div className="french">{wordTitle(w)}</div>
              {showEnglish && <div className="english">{w.meaning}</div>}
            </div>
            <button className="icon-btn" aria-label="Pronounce word"
              onClick={() => media.speak(w, state.settings.speechRate)}><Sound size={18} /></button>
          </div>
          <div className="tagrow">
            <span className="tag accent">{w.pos.replace(/_/g, ' ')}</span>
            {genderLabel(w.gender) && <span className="tag caution">{genderLabel(w.gender)}</span>}
          </div>
          <div className="divider" />
          {w.sentences.map(s => (
            <div key={s.id} style={{ marginBottom: 14 }}>
              <div className="row" style={{ alignItems: 'flex-start', gap: 10 }}>
                <div className="grow">
                  <div style={{ fontSize: 17, fontWeight: 550 }}>{s.fr}</div>
                  {showEnglish && <div className="english" style={{ fontSize: 14.5 }}>{s.en}</div>}
                </div>
                <button className="icon-btn" aria-label="Play sentence"
                  onClick={() => media.speak(s, state.settings.speechRate)}><Sound size={17} /></button>
              </div>
            </div>
          ))}
        </div>
      ))}

      <button className="btn block" onClick={onRepDone}><Check size={18} />Reading pass complete</button>
      <p className="sub" style={{ textAlign: 'center', marginTop: 10 }}>
        Compare the spelling and accents here against what you wrote during dictation.
      </p>
    </div>
  )
}
