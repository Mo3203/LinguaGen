export type Register = 'formal_statement' | 'casual_question' | 'idiomatic'

export interface Sentence { id: string; register: Register; fr: string; en: string; audio?: string; image?: string }
export interface Word {
  id: string; word: string; pos: string; gender?: string | null
  meaning: string; spoken?: string; audio?: string; image?: string
  display?: string; plural?: string
  sentences: Sentence[]
}
export interface Segment { kind: 'word' | 'sentence'; start: number; end: number; fr: string }
export interface Unit {
  id: string; title: string; words: Word[]
  videoBil?: string; videoFr?: string; practice?: string
  segments?: Segment[]
}
export interface Topic { topic: string; title: string; units: Unit[] }
export interface Bundle {
  version: number; language: string; topics: Topic[]
  profile?: Partial<import('./profile').LanguageProfile>
}

export type Mode = 'study' | 'review'
export type StepKey = 'video' | 'audio' | 'reading' | 'recall_fr' | 'recall_en' | 'exercises'
export interface StepDef { key: StepKey; label: string; reps: number; hint: string }

export interface SessionProgress {
  unitId: string; mode: Mode; step: number; rep: number
  doneReps: Record<string, number>       // stepKey -> completed reps
  startedAt: number; finishedAt?: number
}

export type Grade = 0 | 1 | 2 | 3        // again hard good easy
export interface Card {
  due: number; interval: number; ease: number
  reps: number; lapses: number
}
export interface Dictation { sentenceId: string; attempt: string; score: number; at: number }
export interface SessionLog { unitId: string; mode: Mode; at: number }
export interface ExerciseNote { done: boolean; ref: string; note: string }

export interface AppState {
  reviews: Record<string, Card>
  sessions: Record<string, SessionProgress>
  logs: SessionLog[]
  dictations: Dictation[]
  exercises: Record<string, ExerciseNote>
  settings: Settings
}
export interface Settings {
  /** show the studied language only, without English (name kept for saved settings) */
  strictAccents: boolean; frenchOnly: boolean; speechRate: number
}
export const defaultSettings: Settings = { strictAccents: true, frenchOnly: false, speechRate: 0.95 }
