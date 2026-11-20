import React from 'react'
import { L } from '../core/profile'
export default function AccentBar({ target }: { target: React.RefObject<HTMLTextAreaElement | HTMLInputElement> }) {
  const insert = (ch: string) => {
    const el = target.current; if (!el) return
    const s = el.selectionStart ?? el.value.length, e = el.selectionEnd ?? s
    el.value = el.value.slice(0, s) + ch + el.value.slice(e)
    el.dispatchEvent(new Event('input', { bubbles: true }))
    el.focus(); el.setSelectionRange(s + 1, s + 1)
  }
  return (
    <div className="accents">
      {L().characters.map(c => (
        <button key={c} onMouseDown={e => { e.preventDefault(); insert(c) }}>{c}</button>
      ))}
    </div>
  )
}
