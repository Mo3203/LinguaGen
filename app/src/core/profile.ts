/** The language being studied. Everything the interface says about the
 *  language comes from here, and here it comes from bundle.json ("profile"),
 *  which the pipeline writes from languages/<code>.json. French is the default
 *  so content exported before profiles existed still works unchanged. */
import type { Word } from './types'

export interface LanguageProfile {
  code: string
  name: string
  locale: string
  genders: Record<string, string>
  characters: string[]
  labels: {
    greeting: string
    targetToNative: string
    nativeToTarget: string
    targetOnly: string
    targetWord: string
  }
}

const FRENCH: LanguageProfile = {
  code: 'fr', name: 'French', locale: 'fr-FR',
  genders: { m: 'Masculine', f: 'Feminine' },
  characters: ['é', 'è', 'ê', 'à', 'ù', 'ç', 'î', 'ô', 'û', 'ë', 'ï', 'œ'],
  labels: {
    greeting: 'Bonjour', targetToNative: 'French to English', nativeToTarget: 'English to French',
    targetOnly: 'French only', targetWord: 'French word',
  },
}

let current: LanguageProfile = FRENCH

export function setProfile(p?: Partial<LanguageProfile> | null, code?: string) {
  if (!p && (!code || code === 'fr')) { current = FRENCH; return }
  const name = p?.name || code || 'Target'
  current = {
    ...FRENCH,
    ...p,
    code: p?.code || code || 'xx',
    name,
    labels: {
      greeting: 'Welcome',
      targetToNative: `${name} to English`, nativeToTarget: `English to ${name}`,
      targetOnly: `${name} only`, targetWord: `${name} word`,
      ...(p?.labels || {}),
    },
  } as LanguageProfile
  if (typeof document !== 'undefined') document.documentElement.lang = current.code
}

export const L = () => current

/** Where progress is stored. French keeps its original key so no progress is lost. */
export const storageKey = () => current.code === 'fr' ? 'french-study.v1' : `${current.code}-study.v1`

export const genderLabel = (g?: string | null) => (g ? current.genders[g] || '' : '')

/** The heading for a word: dictionary style where the language uses it (der Kaffee, -s). */
export const wordTitle = (w: Word) => w.display || w.word
