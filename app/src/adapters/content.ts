import { ContentPort } from '../ports'
import { Bundle } from '../core/types'
import sample from '../content/bundle.json'

/** StaticBundleAdapter: uses /content/bundle.json if you deployed real content,
 *  otherwise the built-in sample generated from the real dataset. */
export class StaticBundleAdapter implements ContentPort {
  async load(): Promise<Bundle> {
    try {
      const r = await fetch('./content/bundle.json')
      if (r.ok) return await r.json()
    } catch { /* offline or absent -> sample */ }
    return sample as unknown as Bundle
  }
}
