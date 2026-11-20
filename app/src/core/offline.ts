import { Bundle, Topic, Unit } from './types'

export const CONTENT_CACHE = 'french-study-content-v2'
const prefix = (p: string) => './content/' + p

/** Every asset a unit needs to run without a network. */
export function unitAssets(u: Unit, includeVideo = true): string[] {
  const set = new Set<string>()
  if (u.practice) set.add(prefix(u.practice))
  if (includeVideo) {
    if (u.videoBil) set.add(prefix(u.videoBil))
    if (u.videoFr) set.add(prefix(u.videoFr))
  }
  for (const w of u.words) {
    if (w.audio) set.add(prefix(w.audio))
    if (w.image) set.add(prefix(w.image))
    for (const s of w.sentences) {
      if (s.audio) set.add(prefix(s.audio))
      if (s.image) set.add(prefix(s.image))
    }
  }
  return [...set]
}

export function topicAssets(t: Topic, includeVideo = true): string[] {
  const set = new Set<string>()
  for (const u of t.units) unitAssets(u, includeVideo).forEach(a => set.add(a))
  return [...set]
}

export function allAssets(b: Bundle, includeVideo = true): string[] {
  const set = new Set<string>([prefix('bundle.json').replace('content/content/', 'content/')])
  set.add('./content/bundle.json')
  for (const t of b.topics) topicAssets(t, includeVideo).forEach(a => set.add(a))
  return [...set]
}

export interface Progress { total: number; done: number; failed: number; bytes: number }

/** Fetch and store a list of assets, reporting progress. Resumes: already
 *  cached entries are skipped, so re-running after an interruption is cheap. */
export async function download(urls: string[], onProgress: (p: Progress) => void,
                               concurrency = 6): Promise<Progress> {
  const cache = await caches.open(CONTENT_CACHE)
  const p: Progress = { total: urls.length, done: 0, failed: 0, bytes: 0 }
  let cursor = 0

  const worker = async () => {
    while (cursor < urls.length) {
      const url = urls[cursor++]
      try {
        const existing = await cache.match(url)
        if (existing) {
          p.done++
        } else {
          const res = await fetch(url)
          if (res.ok) {
            const buf = await res.clone().arrayBuffer()
            p.bytes += buf.byteLength
            await cache.put(url, res)
            p.done++
          } else p.failed++
        }
      } catch { p.failed++ }
      onProgress({ ...p })
    }
  }
  await Promise.all(Array.from({ length: concurrency }, worker))
  return p
}

/** How many of these assets are already stored. */
export async function cachedCount(urls: string[]): Promise<number> {
  if (!('caches' in self)) return 0
  const cache = await caches.open(CONTENT_CACHE)
  let n = 0
  const step = 40
  for (let i = 0; i < urls.length; i += step) {
    const batch = urls.slice(i, i + step)
    const hits = await Promise.all(batch.map(u => cache.match(u).then(Boolean).catch(() => false)))
    n += hits.filter(Boolean).length
  }
  return n
}

export async function removeAll(urls: string[]): Promise<void> {
  const cache = await caches.open(CONTENT_CACHE)
  await Promise.all(urls.map(u => cache.delete(u).catch(() => false)))
}

export async function storageReport(): Promise<{ usedMb: number; quotaMb: number; persisted: boolean }> {
  let usedMb = 0, quotaMb = 0, persisted = false
  try {
    const est = await navigator.storage?.estimate?.()
    usedMb = Math.round((est?.usage || 0) / 1e6)
    quotaMb = Math.round((est?.quota || 0) / 1e6)
    persisted = (await navigator.storage?.persisted?.()) || false
  } catch { /* unsupported */ }
  return { usedMb, quotaMb, persisted }
}

/** Ask the browser not to evict our data. Safari grants this for installed apps. */
export async function requestPersistence(): Promise<boolean> {
  try { return (await navigator.storage?.persist?.()) || false } catch { return false }
}
