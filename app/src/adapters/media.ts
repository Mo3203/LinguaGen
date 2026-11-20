import { MediaPort } from '../ports'
import { Sentence, Word } from '../core/types'
import { L } from '../core/profile'

const exists = new Map<string, boolean>()
async function urlOk(u: string): Promise<boolean> {
  if (exists.has(u)) return exists.get(u)!
  try { const r = await fetch(u, { method: 'HEAD' }); exists.set(u, r.ok); return r.ok }
  catch { exists.set(u, false); return false }
}

/** AssetOrSpeechAdapter: plays real Opus clips when deployed under ./content/,
 *  falls back to the browser's voice for the language so the app works with zero assets. */
export class AssetOrSpeechAdapter implements MediaPort {
  private audio: HTMLAudioElement | null = null

  private text(item: Sentence | Word): string {
    return 'fr' in item ? (item as Sentence).fr : ((item as Word).spoken || (item as Word).word)
  }

  async speak(item: Sentence | Word, rate: number): Promise<void> {
    this.stop()
    const ref = (item as any).audio as string | undefined
    if (ref) {
      const url = './content/' + ref
      if (await urlOk(url)) {
        await new Promise<void>((res) => {
          const a = new Audio(url)
          this.audio = a
          a.playbackRate = rate
          a.onended = () => res(); a.onerror = () => res()
          a.play().catch(() => res())
        })
        return
      }
    }
    await new Promise<void>((res) => {
      const u = new SpeechSynthesisUtterance(this.text(item))
      u.lang = L().locale; u.rate = rate
      const pick = () => {
        const v = speechSynthesis.getVoices().find(v => v.lang.startsWith(L().code))
        if (v) u.voice = v
      }
      pick(); u.onend = () => res(); u.onerror = () => res()
      speechSynthesis.speak(u)
    })
  }
  stop() {
    speechSynthesis.cancel()
    if (this.audio) { this.audio.pause(); this.audio = null }
  }
  imageUrl(item: Sentence | Word): string | null {
    const ref = (item as any).image as string | undefined
    return ref ? './content/' + ref : null
  }
  videoUrl(path?: string): string | null { return path ? './content/' + path : null }
}
