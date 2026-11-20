import React from 'react'
import { Unit, Mode, AppState } from '../core/types'
import { stepsFor, newSession, stepDef, repsDone, completeRep, setReps, canAdvance, nextStep, prevStep, pct } from '../core/session'
import VideoStep from './steps/VideoStep'
import AudioStep from './steps/AudioStep'
import ReadingStep from './steps/ReadingStep'
import RecallStep from './steps/RecallStep'
import ExerciseStep from './steps/ExerciseStep'
import { media } from './App'
import { Close, Back, Forward, Check } from './Icons'

export default function Session({ unit, mode, state, update, exit }: {
  unit: Unit; mode: Mode; state: AppState
  update: (fn: (s: AppState) => AppState) => void; exit: () => void
}) {
  const key = unit.id + ':' + mode
  const progress = state.sessions[key] || newSession(unit.id, mode)
  const setProgress = (p: typeof progress) =>
    update(s => ({ ...s, sessions: { ...s.sessions, [key]: p } }))

  const def = stepDef(progress)
  const done = repsDone(progress, def.key)
  const finished = !!progress.finishedAt
  const steps = stepsFor(mode)

  const onRepDone = () => setProgress(completeRep(progress))
  const goNext = () => {
    media.stop()
    const p = nextStep(progress)
    setProgress(p)
    if (p.finishedAt) update(s => ({ ...s, logs: [...s.logs, { unitId: unit.id, mode, at: Date.now() }] }))
  }
  const goPrev = () => { media.stop(); setProgress(prevStep(progress)) }
  const close = () => { media.stop(); exit() }

  const stepProps = { unit, mode, state, update, rep: done, onRepDone }

  return (
    <>
      <header className="topbar">
        <button className="icon-btn" onClick={close} aria-label="Close session"><Close size={19} /></button>
        <div className="grow">
          <h1 style={{ fontSize: 18 }}>{unit.title}</h1>
          <div className="subtitle">
            {mode === 'study' ? 'Study session' : 'Review session'} — step {progress.step + 1} of {steps.length}, {pct(progress)} percent complete
          </div>
        </div>
      </header>

      {!finished ? (
        <main className="page enter" key={progress.step}>
          <div className="stepline">
            {steps.map((s, i) => (
              <span key={s.key} className={'seg' + (i === progress.step ? ' current' : i < progress.step ? ' done' : '')} />
            ))}
          </div>

          <div style={{ textAlign: 'center', marginBottom: 18 }}>
            <h2 style={{ margin: 0, fontSize: 20, fontWeight: 650 }}>{def.label}</h2>
            <div className="sub" style={{ marginTop: 4 }}>{def.hint}</div>
            {def.reps > 1 && (
              <>
                <div className="passes">
                  {Array.from({ length: def.reps }, (_, i) => {
                    const state = i < done ? 'complete' : i === done ? 'active' : 'pending'
                    return (
                      <button key={i} className={'pass ' + state}
                        aria-label={`Pass ${i + 1}, ${state === 'complete' ? 'completed' : state === 'active' ? 'current' : 'not started'}. Select to work on it.`}
                        onClick={() => setProgress(setReps(progress, i))}>
                        <span className="pass-label">Pass {i + 1}</span>
                        <span className="pass-state">
                          {state === 'complete' ? 'Completed' : state === 'active' ? 'Current' : 'Not started'}
                        </span>
                      </button>
                    )
                  })}
                </div>
                <div className="sub pass-hint">
                  {done >= def.reps
                    ? 'All passes done. Select a pass to repeat it.'
                    : 'Select any pass to go back and repeat it.'}
                </div>
              </>
            )}
          </div>

          {def.key === 'video' && <VideoStep {...stepProps} />}
          {def.key === 'audio' && <AudioStep {...stepProps} />}
          {def.key === 'reading' && <ReadingStep {...stepProps} />}
          {def.key === 'recall_fr' && <RecallStep {...stepProps} direction="fr-en" />}
          {def.key === 'recall_en' && <RecallStep {...stepProps} direction="en-fr" />}
          {def.key === 'exercises' && <ExerciseStep {...stepProps} />}

          <div className="actionbar"><div className="inner">
            <button className="btn secondary compact" onClick={goPrev} disabled={progress.step === 0}>
              <Back size={17} />Previous
            </button>
            <div className="grow" />
            {!canAdvance(progress) && def.reps > 1 && (
              <button className="btn secondary compact" onClick={onRepDone}>Mark pass complete</button>
            )}
            <button className="btn" onClick={goNext} disabled={!canAdvance(progress)}>
              {progress.step === steps.length - 1 ? 'Finish session' : 'Next step'}<Forward size={17} />
            </button>
          </div></div>
        </main>
      ) : (
        <main className="page enter">
          <div className="completion">
            <span style={{ color: 'var(--accent)' }}><Check size={44} /></span>
            <h2>Session complete</h2>
            <p className="sub">Every step of the {mode === 'study' ? 'study' : 'review'} sequence is finished for this unit.</p>
          </div>
          <button className="btn block" onClick={close}>Return to units</button>
          <div style={{ height: 10 }} />
          <button className="btn block secondary" onClick={() => setProgress(newSession(unit.id, mode))}>
            Repeat this session
          </button>
        </main>
      )}
    </>
  )
}
