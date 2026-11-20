import { Card, Grade } from './types'
const DAY = 86400000

export function newCard(): Card {
  return { due: Date.now(), interval: 0, ease: 2.5, reps: 0, lapses: 0 }
}
/** FSRS-style spaced scheduler (SM-2+ family). Swappable behind this module. */
export function grade(c: Card, g: Grade, now = Date.now()): Card {
  let { interval, ease, reps, lapses } = c
  if (g === 0) {                        // again
    lapses += 1; ease = Math.max(1.3, ease - 0.2)
    return { due: now + 10 * 60000, interval: 0, ease, reps: reps + 1, lapses }
  }
  if (g === 1) {                        // hard
    ease = Math.max(1.3, ease - 0.15)
    interval = Math.max(1, interval * 1.2 || 1)
  } else if (g === 2) {                 // good
    interval = reps === 0 ? 1 : interval === 0 ? 1 : interval < 3 ? 3 : interval * ease
  } else {                              // easy
    ease += 0.15
    interval = (interval || 1) * ease * 1.3
  }
  interval = Math.min(365, Math.round(interval * 10) / 10)
  return { due: now + interval * DAY, interval, ease, reps: reps + 1, lapses }
}
export function isDue(c: Card | undefined, now = Date.now()): boolean {
  return !c ? false : c.due <= now
}
export type Bucket = 'new' | 'learning' | 'young' | 'mature'
export function bucket(c: Card | undefined): Bucket {
  if (!c || c.reps === 0) return 'new'
  if (c.interval < 7) return 'learning'
  if (c.interval < 30) return 'young'
  return 'mature'
}
