import { StatePort } from '../ports'
import { AppState, defaultSettings } from '../core/types'
import { storageKey } from '../core/profile'

const empty = (): AppState => ({
  reviews: {}, sessions: {}, logs: [], dictations: [], exercises: {},
  settings: { ...defaultSettings },
})

export class LocalStateAdapter implements StatePort {
  load(): AppState {
    try {
      const raw = localStorage.getItem(storageKey())
      if (!raw) return empty()
      const s = JSON.parse(raw)
      return { ...empty(), ...s, settings: { ...defaultSettings, ...(s.settings || {}) } }
    } catch { return empty() }
  }
  save(s: AppState) { localStorage.setItem(storageKey(), JSON.stringify(s)) }
  export(): string { return localStorage.getItem(storageKey()) || JSON.stringify(empty()) }
  import(json: string): AppState {
    const parsed = JSON.parse(json)          // throws on invalid
    localStorage.setItem(storageKey(), JSON.stringify(parsed))
    return this.load()
  }
}
