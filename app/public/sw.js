/* Language Study — offline service worker (v3)

   Policy:
     navigation / index.html  network-first  (so a redeploy is picked up)
     bundle.json              network-first  (so new material appears)
     hashed assets, media     cache-first    (immutable, safe to keep)
*/
const SHELL = 'french-study-shell-v4'
const CONTENT = 'french-study-content-v2'   // unchanged: keeps downloaded material
const SHELL_FILES = ['./', './index.html', './manifest.webmanifest',
                     './icons/icon-192.png', './icons/icon-512.png']

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(SHELL_FILES)).then(() => self.skipWaiting()))
})

self.addEventListener('activate', e => {
  e.waitUntil((async () => {
    const keep = [SHELL, CONTENT]
    for (const k of await caches.keys()) if (!keep.includes(k)) await caches.delete(k)
    await self.clients.claim()
  })())
})

self.addEventListener('fetch', e => {
  const req = e.request
  if (req.method !== 'GET') return
  const url = new URL(req.url)
  if (url.origin !== location.origin) return

  const isContent = url.pathname.includes('/content/')
  const cacheName = isContent ? CONTENT : SHELL
  const isDoc = req.mode === 'navigate' || url.pathname.endsWith('/') ||
                url.pathname.endsWith('/index.html')
  const isManifest = url.pathname.endsWith('/bundle.json')

  e.respondWith((async () => {
    const cache = await caches.open(cacheName)

    // always try the network first for the page itself and the content manifest
    if (isDoc || isManifest) {
      try {
        const fresh = await fetch(req, { cache: 'no-store' })
        if (fresh && fresh.ok) { cache.put(req, fresh.clone()).catch(() => {}); return fresh }
      } catch { /* offline */ }
      const stored = await cache.match(req, { ignoreSearch: true })
      if (stored) return stored
      if (isDoc) {
        const shell = await caches.open(SHELL)
        const idx = await shell.match('./index.html')
        if (idx) return idx
      }
    }

    // Video and audio are requested in byte ranges. The Cache API cannot answer
    // a range request directly, so build the partial response from the stored file.
    const rangeHeader = req.headers.get('range')
    if (rangeHeader) {
      const stored = await cache.match(url.pathname.replace(/^\/*/, './'), { ignoreSearch: true })
        || await cache.match(req.url, { ignoreSearch: true })
        || await cache.match(req, { ignoreSearch: true })
      if (stored) {
        const buf = await stored.arrayBuffer()
        const m = /bytes=(\d*)-(\d*)/.exec(rangeHeader)
        const total = buf.byteLength
        let start = m && m[1] ? parseInt(m[1], 10) : 0
        let end = m && m[2] ? parseInt(m[2], 10) : total - 1
        if (isNaN(start) || start < 0) start = 0
        if (isNaN(end) || end >= total) end = total - 1
        if (start > end) start = 0
        const slice = buf.slice(start, end + 1)
        return new Response(slice, {
          status: 206,
          statusText: 'Partial Content',
          headers: {
            'Content-Type': stored.headers.get('Content-Type') || 'application/octet-stream',
            'Content-Range': `bytes ${start}-${end}/${total}`,
            'Content-Length': String(slice.byteLength),
            'Accept-Ranges': 'bytes',
          },
        })
      }
    }

    const hit = await cache.match(req, { ignoreSearch: true })
    if (hit) return hit
    try {
      const res = await fetch(req)
      if (res && res.status === 200) cache.put(req, res.clone()).catch(() => {})
      return res
    } catch (err) {
      if (isDoc) {
        const shell = await caches.open(SHELL)
        const idx = await shell.match('./index.html')
        if (idx) return idx
      }
      throw err
    }
  })())
})

self.addEventListener('message', e => {
  if (e.data === 'clear-content') caches.delete(CONTENT)
  if (e.data === 'clear-shell') caches.delete(SHELL)
})
