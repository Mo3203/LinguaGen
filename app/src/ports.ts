import { Bundle, Sentence, Word, AppState } from './core/types'

/** ContentPort — where units come from */
export interface ContentPort { load(): Promise<Bundle> }

/** MediaPort — how audio & images are produced */
export interface MediaPort {
  speak(item: Sentence | Word, rate: number): Promise<void>
  stop(): void
  imageUrl(item: Sentence | Word): string | null
  videoUrl(path?: string): string | null
}

/** StatePort — where learning state lives */
export interface StatePort {
  load(): AppState
  save(s: AppState): void
  export(): string
  import(json: string): AppState
}
