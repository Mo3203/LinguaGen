import React from 'react'
import { Unit, AppState } from '../../core/types'
import { Book, Check } from '../Icons'

export default function ExerciseStep({ unit, state, update, onRepDone }: {
  unit: Unit; state: AppState; rep: number; mode: string
  update: (fn: (s: AppState) => AppState) => void; onRepDone: () => void
}) {
  const entry = state.exercises[unit.id] || { done: false, ref: '', note: '' }
  const set = (patch: Partial<typeof entry>) =>
    update(s => ({ ...s, exercises: { ...s.exercises, [unit.id]: { ...entry, ...patch } } }))

  return (
    <div className="enter">
      <div className="card">
        <div className="row" style={{ marginBottom: 10 }}>
          <span style={{ color: 'var(--accent)' }}><Book size={22} /></span>
          <div className="grow">
            <h2>Textbook exercises</h2>
            <div className="sub">Work through this unit's exercises in your textbook, then record what you did.</div>
          </div>
        </div>
        <div className="divider" />
        <label className="field">Book and lesson reference</label>
        <input className="entry" value={entry.ref} placeholder="For example: Assimil lesson 12, exercises 1 to 3"
          onChange={e => set({ ref: e.target.value })} />
        <div style={{ height: 14 }} />
        <label className="field">Notes and mistakes to revisit</label>
        <textarea className="entry" value={entry.note} placeholder="What was difficult?"
          onChange={e => set({ note: e.target.value })} />
      </div>
      <button className="btn block" onClick={() => { set({ done: true }); onRepDone() }}>
        <Check size={18} />Exercises complete
      </button>
    </div>
  )
}
