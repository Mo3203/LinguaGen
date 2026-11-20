import React from 'react'
type P = { size?: number }
const S = (p: P) => p.size || 20
const base = (s: number) => ({
  width: s, height: s, viewBox: '0 0 24 24', fill: 'none',
  stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
})
export const Play = (p: P) => <svg {...base(S(p))}><path d="M8 5.5v13l10-6.5z" fill="currentColor" stroke="none" /></svg>
export const Pause = (p: P) => <svg {...base(S(p))}><rect x="7" y="5" width="3.4" height="14" rx="1" fill="currentColor" stroke="none" /><rect x="13.6" y="5" width="3.4" height="14" rx="1" fill="currentColor" stroke="none" /></svg>
export const Previous = (p: P) => <svg {...base(S(p))}><path d="M17 6v12L8.5 12z" fill="currentColor" stroke="none" /><rect x="6" y="5.5" width="1.8" height="13" rx=".9" fill="currentColor" stroke="none" /></svg>
export const Next = (p: P) => <svg {...base(S(p))}><path d="M7 6v12l8.5-6z" fill="currentColor" stroke="none" /><rect x="16.2" y="5.5" width="1.8" height="13" rx=".9" fill="currentColor" stroke="none" /></svg>
export const Repeat = (p: P) => <svg {...base(S(p))}><path d="M4 12a8 8 0 0 1 13.7-5.6M20 12a8 8 0 0 1-13.7 5.6" /><path d="M18 3v4h-4M6 21v-4h4" /></svg>
export const Sound = (p: P) => <svg {...base(S(p))}><path d="M5 9.5v5h3l4 3.5v-12l-4 3.5z" /><path d="M15.5 9.2a4 4 0 0 1 0 5.6" /><path d="M18 6.8a7.5 7.5 0 0 1 0 10.4" /></svg>
export const Close = (p: P) => <svg {...base(S(p))}><path d="M6 6l12 12M18 6L6 18" /></svg>
export const Check = (p: P) => <svg {...base(S(p))}><path d="M4.5 12.5l5 5 10-11" /></svg>
export const Back = (p: P) => <svg {...base(S(p))}><path d="M15 5l-7 7 7 7" /></svg>
export const Forward = (p: P) => <svg {...base(S(p))}><path d="M9 5l7 7-7 7" /></svg>
export const Library = (p: P) => <svg {...base(S(p))}><path d="M4 5.5A1.5 1.5 0 0 1 5.5 4H10v16H5.5A1.5 1.5 0 0 1 4 18.5z" /><path d="M20 5.5A1.5 1.5 0 0 0 18.5 4H14v16h4.5a1.5 1.5 0 0 0 1.5-1.5z" /></svg>
export const Analytics = (p: P) => <svg {...base(S(p))}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></svg>
export const Preferences = (p: P) => <svg {...base(S(p))}><circle cx="12" cy="12" r="3.2" /><path d="M12 3v2.2M12 18.8V21M21 12h-2.2M5.2 12H3M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6M18.4 18.4l-1.6-1.6M7.2 7.2L5.6 5.6" /></svg>
export const Book = (p: P) => <svg {...base(S(p))}><path d="M5 4.5h9a3 3 0 0 1 3 3V20a2.5 2.5 0 0 0-2.5-2.5H5z" /><path d="M19 7.5V20" /></svg>
export const Film = (p: P) => <svg {...base(S(p))}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M7 5v14M17 5v14M3 12h18" /></svg>
export const Headphones = (p: P) => <svg {...base(S(p))}><path d="M4 14v-2a8 8 0 0 1 16 0v2" /><rect x="3" y="13.5" width="4" height="6.5" rx="1.6" /><rect x="17" y="13.5" width="4" height="6.5" rx="1.6" /></svg>
export const Download = (p: P) => <svg {...base(S(p))}><path d="M12 4v11" /><path d="M7.5 11l4.5 4.5L16.5 11" /><path d="M4.5 19.5h15" /></svg>
export const Stored = (p: P) => <svg {...base(S(p))}><path d="M4.5 19.5h15" /><path d="M12 15V4" /><path d="M7.5 8.5L12 4l4.5 4.5" /></svg>
export const Trash = (p: P) => <svg {...base(S(p))}><path d="M4.5 7h15" /><path d="M9.5 7V5h5v2" /><path d="M6.5 7l1 12.5h9L17.5 7" /></svg>
export const Offline = (p: P) => <svg {...base(S(p))}><path d="M5 16.5a3.5 3.5 0 0 1 .8-6.9A5.5 5.5 0 0 1 16.7 9a3.8 3.8 0 0 1 .8 7.5z" /><path d="M12 13v6" /><path d="M9.5 16.5L12 19l2.5-2.5" /></svg>
