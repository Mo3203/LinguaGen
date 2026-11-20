import React, { useEffect, useMemo, useState } from 'react'
import { Bundle, Unit, Topic, Mode, AppState, Word } from '../core/types'
import { StaticBundleAdapter } from '../adapters/content'
import { AssetOrSpeechAdapter } from '../adapters/media'
import { LocalStateAdapter } from '../adapters/state'
import { setProfile } from '../core/profile'
import { isDue } from '../core/scheduler'
import { Library, Analytics, Preferences, Offline } from './Icons'
import Home from './Home'
import TopicView from './TopicView'
import Session from './Session'
import DueReview from './DueReview'
import Dashboard from './Dashboard'
import SettingsView from './SettingsView'
import OfflineView from './OfflineView'

const content = new StaticBundleAdapter()
export const media = new AssetOrSpeechAdapter()
const store = new LocalStateAdapter()

export type View =
  | { name: 'home' } | { name: 'topic'; topic: Topic } | { name: 'session'; unit: Unit; mode: Mode }
  | { name: 'due' } | { name: 'stats' } | { name: 'offline' } | { name: 'settings' }

export default function App() {
  const [bundle, setBundle] = useState<Bundle | null>(null)
  const [state, setState] = useState<AppState | null>(null)
  const [view, setView] = useState<View>({ name: 'home' })

  // the language comes with the content; progress is read only once it is known
  useEffect(() => {
    content.load().then(b => {
      setProfile(b.profile, b.language)
      setState(store.load())
      setBundle(b)
    })
  }, [])
  const update = (fn: (s: AppState) => AppState) =>
    setState(prev => { if (!prev) return prev; const next = fn(prev); store.save(next); return next })

  const allWords: Word[] = useMemo(() =>
    bundle ? bundle.topics.flatMap(t => t.units.flatMap(u => u.words)) : [], [bundle])
  const dueCount = state ? allWords.filter(w => isDue(state.reviews[w.id])).length : 0

  if (!bundle || !state) return (
    <div className="app"><div className="page" style={{ display: 'grid', placeItems: 'center' }}>
      <span className="sub">Loading your material…</span></div></div>
  )

  const tab = ['session', 'due', 'topic'].includes(view.name) ? null : view.name
  const tabs = [
    { key: 'home', label: 'Study', Icon: Library },
    { key: 'stats', label: 'Progress', Icon: Analytics },
    { key: 'offline', label: 'Offline', Icon: Offline },
    { key: 'settings', label: 'Preferences', Icon: Preferences },
  ] as const

  return (
    <div className="app">
      {view.name === 'home' && <Home bundle={bundle} state={state} dueCount={dueCount}
        openTopic={topic => setView({ name: 'topic', topic })}
        openSession={(unit, mode) => setView({ name: 'session', unit, mode })}
        openDue={() => setView({ name: 'due' })} />}
      {view.name === 'topic' && <TopicView topic={view.topic} state={state}
        openSession={(unit, mode) => setView({ name: 'session', unit, mode })}
        back={() => setView({ name: 'home' })} />}
      {view.name === 'session' && <Session unit={view.unit} mode={view.mode} state={state}
        update={update} exit={() => {
          const t = bundle.topics.find(t => t.units.some(u => u.id === view.unit.id))
          setView(t ? { name: 'topic', topic: t } : { name: 'home' })
        }} />}
      {view.name === 'due' && <DueReview words={allWords} state={state} update={update}
        exit={() => setView({ name: 'home' })} />}
      {view.name === 'stats' && <Dashboard words={allWords} state={state} />}
      {view.name === 'offline' && <OfflineView bundle={bundle} />}
      {view.name === 'settings' && <SettingsView state={state} update={update} store={store} setState={setState} />}

      {tab && (
        <nav className="navbar"><div className="inner">
          {tabs.map(({ key, label, Icon }) => (
            <button key={key} className={'navtab' + (tab === key ? ' selected' : '')}
              onClick={() => setView({ name: key } as View)}>
              <Icon size={21} />{label}
            </button>
          ))}
        </div></nav>
      )}
    </div>
  )
}
