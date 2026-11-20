import { Unit, Topic, AppState } from './types'
import { bucket } from './scheduler'

export type UnitStatus = 'not-started' | 'in-progress' | 'studied' | 'reviewed'

export function unitStatus(u: Unit, s: AppState): UnitStatus {
  const study = s.sessions[u.id + ':study']
  const review = s.sessions[u.id + ':review']
  if (review?.finishedAt) return 'reviewed'
  if (study?.finishedAt) return 'studied'
  if (study || review) return 'in-progress'
  return 'not-started'
}

export const STATUS_LABEL: Record<UnitStatus, string> = {
  'not-started': 'Not started',
  'in-progress': 'In progress',
  'studied': 'Studied',
  'reviewed': 'Reviewed',
}

/** Share of a unit's words that have reached a lasting stage. */
export function unitEstablished(u: Unit, s: AppState): number {
  const known = u.words.filter(w => ['young', 'mature'].includes(bucket(s.reviews[w.id]))).length
  return Math.round(100 * known / Math.max(1, u.words.length))
}

export interface TopicSummary {
  units: number
  words: number
  started: number
  completed: number
  established: number
}

export function topicSummary(t: Topic, s: AppState): TopicSummary {
  const words = t.units.reduce((a, u) => a + u.words.length, 0)
  let started = 0, completed = 0, known = 0
  for (const u of t.units) {
    const st = unitStatus(u, s)
    if (st !== 'not-started') started++
    if (st === 'studied' || st === 'reviewed') completed++
    known += u.words.filter(w => ['young', 'mature'].includes(bucket(s.reviews[w.id]))).length
  }
  return {
    units: t.units.length, words, started, completed,
    established: Math.round(100 * known / Math.max(1, words)),
  }
}

/** The unit the learner should most plausibly open next. */
export function suggestNext(topics: Topic[], s: AppState): { unit: Unit; topic: Topic } | null {
  for (const t of topics) {
    for (const u of t.units) {
      if (unitStatus(u, s) === 'in-progress') return { unit: u, topic: t }
    }
  }
  for (const t of topics) {
    for (const u of t.units) {
      if (unitStatus(u, s) === 'not-started') return { unit: u, topic: t }
    }
  }
  return null
}
