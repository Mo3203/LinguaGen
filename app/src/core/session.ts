import { Mode, StepDef, SessionProgress } from './types'
import { L } from './profile'

/** The steps of a session. Built on request so the labels name the language studied. */
export const stepsFor = (mode: Mode): StepDef[] => {
  const { targetToNative, nativeToTarget } = L().labels
  const lang = L().name
  const all: Record<Mode, StepDef[]> = {
  study: [
    { key: 'video',     label: 'Video',     reps: 4, hint: 'Watch twice, then pause and repeat aloud twice' },
    { key: 'audio',     label: 'Listening', reps: 2, hint: 'Write what you hear: first with pauses, then continuously' },
    { key: 'reading',   label: 'Reading',   reps: 2, hint: 'Verify your spelling and accents against the text' },
    { key: 'recall_fr', label: targetToNative, reps: 1, hint: `Write the English meaning and a full ${lang} example sentence` },
    { key: 'recall_en', label: nativeToTarget, reps: 1, hint: `Write the ${lang} word and a full ${lang} example sentence` },
    { key: 'exercises', label: 'Exercises', reps: 1, hint: 'Solve this unit\'s exercises in your textbook' },
  ],
  review: [
    { key: 'video',     label: 'Video',     reps: 1, hint: 'Speak along with the audio as it plays' },
    { key: 'audio',     label: 'Listening', reps: 1, hint: 'Write what you hear without pausing' },
    { key: 'reading',   label: 'Reading',   reps: 1, hint: 'Read through once, aloud if possible' },
    { key: 'recall_fr', label: targetToNative, reps: 1, hint: 'Test yourself on each word' },
    { key: 'recall_en', label: nativeToTarget, reps: 1, hint: 'Test yourself on each word' },
    { key: 'exercises', label: 'Exercises', reps: 1, hint: 'Remaining or revision exercises' },
  ],
  }
  return all[mode]
}

export function newSession(unitId: string, mode: Mode): SessionProgress {
  return { unitId, mode, step: 0, rep: 0, doneReps: {}, startedAt: Date.now() }
}
export function stepDef(p: SessionProgress): StepDef { return stepsFor(p.mode)[p.step] }
export function repsDone(p: SessionProgress, key: string): number { return p.doneReps[key] || 0 }

export function completeRep(p: SessionProgress): SessionProgress {
  const d = stepDef(p)
  const done = Math.min(d.reps, repsDone(p, d.key) + 1)
  const doneReps = { ...p.doneReps, [d.key]: done }
  return { ...p, doneReps, rep: Math.min(done, d.reps - 1) }
}
/** Jump to a specific pass: n passes are marked complete, so you are now
 *  working on pass n + 1. Used by the tappable pass chips. */
export function setReps(p: SessionProgress, n: number): SessionProgress {
  const d = stepDef(p)
  const done = Math.max(0, Math.min(d.reps, n))
  return { ...p, doneReps: { ...p.doneReps, [d.key]: done }, rep: Math.min(done, d.reps - 1) }
}

export function canAdvance(p: SessionProgress): boolean {
  const d = stepDef(p)
  return repsDone(p, d.key) >= d.reps
}
export function nextStep(p: SessionProgress): SessionProgress {
  const last = stepsFor(p.mode).length - 1
  if (p.step >= last) return { ...p, finishedAt: Date.now() }
  return { ...p, step: p.step + 1, rep: 0 }
}
export function prevStep(p: SessionProgress): SessionProgress {
  return { ...p, step: Math.max(0, p.step - 1), rep: 0 }
}
export function pct(p: SessionProgress): number {
  const defs = stepsFor(p.mode)
  const total = defs.reduce((a, d) => a + d.reps, 0)
  const done = defs.reduce((a, d) => a + Math.min(d.reps, repsDone(p, d.key)), 0)
  return Math.round(100 * done / total)
}
