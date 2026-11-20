import React, { useEffect, useRef, useState } from 'react'
import { Unit, Mode, AppState, Word, Sentence } from '../../core/types'
import { media } from '../App'
import { Play, Pause, Previous, Next, Repeat, Film, Check } from '../Icons'
import { L, genderLabel, wordTitle } from '../../core/profile'

type Item = { kind: 'word'; w: Word } | { kind: 'sentence'; w: Word; s: Sentence }

/** Your method: passes one and two are silent watching, passes three and four
 *  pause after each item so you repeat it aloud. */
function guidance(mode: Mode, rep: number) {
  if (mode === 'review') {
    return { title: 'Shadow the audio',
             detail: 'Speak along with the recording as it plays, without stopping.',
             repeatAloud: false }
  }
  if (rep < 2) {
    return { title: `Pass ${rep + 1} of 4 — watch and listen`,
             detail: 'Keep your eyes on the screen and listen closely to the pronunciation. Do not speak yet.',
             repeatAloud: false }
  }
  return { title: `Pass ${rep + 1} of 4 — repeat aloud`,
           detail: 'The video pauses after each line. Say it out loud exactly as you heard it, then continue.',
           repeatAloud: true }
}

export default function VideoStep({ unit, mode, state, rep, onRepDone }: {
  unit: Unit; mode: Mode; state: AppState; rep: number; onRepDone: () => void
  update: (fn: (s: AppState) => AppState) => void
}) {
  const [frenchOnly, setFrenchOnly] = useState(state.settings.frenchOnly)
  const [available, setAvailable] = useState({ bilingual: false, target: false })
  const [view, setView] = useState<'video' | 'scenes'>('video')
  const g = guidance(mode, rep)

  useEffect(() => {
    let alive = true
    const probe = async (p?: string) => {
      const url = media.videoUrl(p); if (!url) return false
      try { const r = await fetch(url, { method: 'HEAD' }); return r.ok } catch { return false }
    }
    Promise.all([probe(unit.videoBil), probe(unit.videoFr)]).then(([b, f]) => {
      if (!alive) return
      setAvailable({ bilingual: b, target: f })
      if (!b && !f) setView('scenes')
    })
    return () => { alive = false }
  }, [unit.id])

  const hasVideo = available.bilingual || available.target
  const wantTarget = frenchOnly && available.target
  const videoUrl = media.videoUrl(wantTarget ? unit.videoFr : unit.videoBil)

  // ---------- guided pausing on repeat-aloud passes ----------
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const [waiting, setWaiting] = useState(false)
  const [segmentIndex, setSegmentIndex] = useState(0)
  const segments = unit.segments || []
  const guided = g.repeatAloud && segments.length > 0 && view === 'video'
  const nextBoundary = useRef<number | null>(null)

  useEffect(() => { setSegmentIndex(0); setWaiting(false); nextBoundary.current = null }, [rep, view, videoUrl])

  const onTimeUpdate = () => {
    if (!guided || waiting) return
    const v = videoRef.current; if (!v) return
    const seg = segments[segmentIndex]
    if (!seg) return
    if (v.currentTime >= seg.end - 0.05) {
      v.pause(); setWaiting(true)
    }
  }
  const continueFrom = () => {
    const v = videoRef.current
    setWaiting(false)
    setSegmentIndex(i => Math.min(segments.length - 1, i + 1))
    v?.play().catch(() => {})
  }
  const replaySegment = () => {
    const v = videoRef.current; const seg = segments[segmentIndex]
    if (!v || !seg) return
    v.currentTime = seg.start; setWaiting(false); v.play().catch(() => {})
  }

  // ---------- scene-by-scene alternative ----------
  const items: Item[] = unit.words.flatMap(w =>
    [{ kind: 'word', w } as Item, ...w.sentences.map(s => ({ kind: 'sentence', w, s }) as Item)])
  const [index, setIndex] = useState(0)
  const [playing, setPlaying] = useState(false)
  const playingRef = useRef(false)

  const playFrom = async (start: number) => {
    playingRef.current = true; setPlaying(true)
    for (let i = start; i < items.length; i++) {
      if (!playingRef.current) return
      setIndex(i)
      const it = items[i]
      await media.speak(it.kind === 'word' ? it.w : it.s, state.settings.speechRate)
      await new Promise(r => setTimeout(r, g.repeatAloud ? 1500 : 380))
    }
    playingRef.current = false; setPlaying(false); onRepDone()
  }
  const stopScenes = () => { playingRef.current = false; setPlaying(false); media.stop() }
  useEffect(() => () => stopScenes(), [])

  const Guidance = () => (
    <div className={'card flat guidance' + (g.repeatAloud ? ' speak' : '')}>
      <h2>{g.title}</h2>
      <div className="sub">{g.detail}</div>
    </div>
  )

  if (hasVideo && view === 'video' && videoUrl) {
    const seg = segments[segmentIndex]
    return (
      <div className="enter">
        <Guidance />
        <div className="media">
          <video ref={videoRef} key={videoUrl} src={videoUrl} controls playsInline
            onTimeUpdate={onTimeUpdate} onEnded={onRepDone} />
          {guided && waiting && (
            <div className="pausebar">
              <div className="grow">
                <b>Say it aloud</b>
                <div className="sub">{seg ? seg.fr : ''}</div>
              </div>
              <button className="btn compact secondary" onClick={replaySegment}>
                <Repeat size={16} />Hear again
              </button>
              <button className="btn compact" onClick={continueFrom}>
                <Check size={16} />Continue
              </button>
            </div>
          )}
          <div className="controls">
            {available.target && available.bilingual && (
              <button className="btn quiet compact" onClick={() => setFrenchOnly(v => !v)}>
                {frenchOnly ? 'Show English' : L().labels.targetOnly}
              </button>
            )}
            <button className="btn quiet compact" onClick={() => setView('scenes')}>Scene by scene</button>
            <span className="position">
              {guided ? `Line ${Math.min(segmentIndex + 1, segments.length)} of ${segments.length}`
                      : 'Pass counts when the video ends'}
            </span>
          </div>
        </div>
      </div>
    )
  }

  const it = items[index]
  const image = it.kind === 'sentence' ? media.imageUrl(it.s) : media.imageUrl(it.w)

  return (
    <div className="enter">
      <Guidance />
      <div className="media">
        <div className="frame">
          {image ? <img src={image} alt="" onError={e => (e.currentTarget.style.display = 'none')} />
                 : <span className="initial">{it.w.word.charAt(0).toUpperCase()}</span>}
        </div>
        <div className="content">
          {it.kind === 'word' ? (
            <>
              <div className="french lead">{wordTitle(it.w)}</div>
              {!frenchOnly && <div className="english">{it.w.meaning}</div>}
              <div className="tagrow">
                <span className="tag accent">{it.w.pos.replace(/_/g, ' ')}</span>
                {genderLabel(it.w.gender) && <span className="tag caution">{genderLabel(it.w.gender)}</span>}
              </div>
            </>
          ) : (
            <>
              <div className="french">{it.s.fr}</div>
              {!frenchOnly && <div className="english">{it.s.en}</div>}
              <div className="tagrow">
                <span className="tag info">{it.s.register.replace(/_/g, ' ')}</span>
                <span className="tag accent">{it.w.word}</span>
              </div>
            </>
          )}
        </div>
        <div className="controls">
          <button className="icon-btn" aria-label="Previous"
            onClick={() => { stopScenes(); setIndex(i => Math.max(0, i - 1)) }}><Previous size={18} /></button>
          {playing
            ? <button className="icon-btn prominent" aria-label="Pause" onClick={stopScenes}><Pause size={18} /></button>
            : <button className="icon-btn prominent" aria-label="Play" onClick={() => playFrom(index)}><Play size={18} /></button>}
          <button className="icon-btn" aria-label="Next"
            onClick={() => { stopScenes(); setIndex(i => Math.min(items.length - 1, i + 1)) }}><Next size={18} /></button>
          <button className="icon-btn" aria-label="Repeat this item"
            onClick={() => media.speak(it.kind === 'word' ? it.w : it.s, state.settings.speechRate)}><Repeat size={18} /></button>
          <span className="position">{index + 1} of {items.length}</span>
        </div>
      </div>
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <button className="btn secondary compact" onClick={() => setFrenchOnly(v => !v)}>
          {frenchOnly ? 'Show English' : L().labels.targetOnly}
        </button>
        {hasVideo && (
          <button className="btn secondary compact" onClick={() => setView('video')}>
            <Film size={17} />Unit video
          </button>
        )}
      </div>
    </div>
  )
}
