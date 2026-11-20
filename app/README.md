# French Study — the web app

A phone-installable study app implementing your exact 6-step process
(video ×4 · dictation ×2 · reading ×2 · FR→EN · EN→FR · exercises), with
spaced-repetition scheduling, dictation auto-checking, progress, and a
light clean UI. Ports & Adapters throughout.

## Run it (2 commands)
    npm install
    npm run dev
Open the printed URL. On your phone (same Wi-Fi): `npm run dev -- --host`
then open the network URL and "Add to Home Screen".

Production build: `npm run build` → deploy the `dist/` folder anywhere
static (Cloudflare Pages / Netlify: drag-and-drop the folder).

## It already works, empty-handed
Out of the box it uses a built-in sample (3 topics from your real dataset)
and the browser's French voice for audio. Every feature functions.

## Plug in your real content
On the machine/Colab that has your `language_system` project:

    python tools/export_web.py --root /path/to/language_system --out web_content
    # add --with-videos to include the unit MP4s (large)

Copy `web_content/*` into `public/content/` here, rebuild, done:
real Kokoro audio and SDXL images replace the fallbacks automatically
(the app probes `content/` and falls back per-asset if missing).

## Architecture (hexagonal)
    src/core/       pure logic: session machine, scheduler, dictation diff, types
    src/ports.ts    ContentPort · MediaPort · StatePort
    src/adapters/   StaticBundleAdapter · AssetOrSpeechAdapter · LocalStateAdapter
    src/ui/         React screens & steps (imports core + ports only)
Swap an adapter (e.g. cloud sync) without touching core or UI.

## Your data
All progress lives in this browser (localStorage). Settings → Export backup
gives you a JSON you can import on another device.

## Textbook exercises
The Exercises step is a tracker: book reference + notes + done-check.
Your purchased books stay on paper/PDF; nothing is redistributed.
