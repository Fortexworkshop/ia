import { Suspense, lazy, useEffect, useRef, useState } from 'react'
import ErrorBoundary from './components/ErrorBoundary.jsx'
import Feedback from './components/Feedback.jsx'
import Icon, { Logo } from './components/Icon.jsx'
import LoginDialog, { openLogin } from './components/LoginDialog.jsx'
import Overview from './pages/Overview.jsx'
import { activeAlarms, ago, STALE_AFTER_MS } from './state/model.js'
import { LiveProvider, useLive, useNow } from './state/live.jsx'

// Vue d'ensemble dans le bundle principal (élément LCP) ; les autres pages à la demande.
const Alarms = lazy(() => import('./pages/Alarms.jsx'))
const Presence = lazy(() => import('./pages/Presence.jsx'))
const People = lazy(() => import('./pages/People.jsx'))
const Camera = lazy(() => import('./pages/Camera.jsx'))

const ROUTES = [
  { path: '/', label: "Vue d'ensemble", icon: 'overview', Page: Overview },
  { path: '/alarmes', label: 'Alarmes', icon: 'alarm', Page: Alarms },
  { path: '/presence', label: 'Présence', icon: 'presence', Page: Presence },
  { path: '/individus', label: 'Individus', icon: 'people', Page: People },
  { path: '/camera', label: 'Caméra', icon: 'camera', Page: Camera },
]
const ALIASES = { '/personnes': '/individus' }
// Historique long et supervision technique : Grafana (infra/grafana), si son adresse est configurée
const GRAFANA_URL = import.meta.env.VITE_GRAFANA_URL

const THEMES = [
  { id: 'auto', label: 'automatique', icon: 'contrast' },
  { id: 'dark', label: 'sombre', icon: 'moon' },
  { id: 'light', label: 'clair', icon: 'sun' },
]
const readTheme = () => {
  try {
    return localStorage.getItem('theme') || 'auto'
  } catch {
    return 'auto'
  }
}
const currentPath = () => {
  const path = window.location.hash.slice(1) || '/'
  return ALIASES[path] ?? path
}

export default function App() {
  return (
    <LiveProvider>
      <Shell />
    </LiveProvider>
  )
}

function Shell() {
  const [path, setPath] = useState(currentPath)
  const mainRef = useRef(null)
  const first = useRef(true)
  const route = ROUTES.find((r) => r.path === path) ?? ROUTES[0]

  useEffect(() => {
    const onHash = () => setPath(currentPath())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  // Changement de page : titre du document (RGAA 8.6) et focus sur le contenu (navigation clavier)
  useEffect(() => {
    document.title = `${route.label} · FORTEX Supervision`
    if (first.current) {
      first.current = false
      return
    }
    mainRef.current?.focus()
    window.scrollTo(0, 0)
  }, [route])

  const { Page } = route

  return (
    <div className="shell">
      <a className="skip" href="#contenu" onClick={(e) => (e.preventDefault(), mainRef.current?.focus())}>
        Aller au contenu
      </a>
      <TopBar />
      <SideNav current={route.path} />
      <main id="contenu" ref={mainRef} tabIndex={-1}>
        <Feedback />
        <ErrorBoundary key={route.path} name={route.label}>
          <Suspense fallback={<div className="page-loading">Chargement…</div>}>
            <Page />
          </Suspense>
        </ErrorBoundary>
      </main>
      <LoginDialog />
    </div>
  )
}

function TopBar() {
  const [theme, setTheme] = useState(readTheme)
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'auto') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    try {
      localStorage.setItem('theme', theme)
    } catch {
      /* stockage indisponible : le choix vaut pour cette session */
    }
  }, [theme])
  const index = THEMES.findIndex((t) => t.id === theme)
  const next = THEMES[(index + 1) % THEMES.length]

  return (
    <header className="topbar">
      <a className="brand" href="#/" aria-label="FORTEX, supervision SENTINEL-X : vue d'ensemble">
        <Logo />
        <span className="brand-name">
          FORTEX
          <span className="brand-sub">Supervision SENTINEL-X</span>
        </span>
      </a>
      <div className="topbar-meta">
        <LinkState />
        <Clock />
        <OperatorButton />
        <button
          type="button"
          className="btn small quiet"
          onClick={() => setTheme(next.id)}
          aria-label={`Thème ${THEMES[index].label}. Passer au thème ${next.label}`}
        >
          <Icon name={THEMES[index].icon} /> <span className="theme-label" aria-hidden="true">Thème {THEMES[index].label}</span>
        </button>
      </div>
    </header>
  )
}

function OperatorButton() {
  const { operator, simulated, actions } = useLive()
  if (simulated) return null // simulateur local : pas de serveur, pas de session
  return operator ? (
    <button type="button" className="btn small quiet" onClick={actions.logout}>
      <Icon name="shield" /> <span className="op-label">Opérateur · </span>Se déconnecter
    </button>
  ) : (
    <button type="button" className="btn small" onClick={openLogin}>
      <Icon name="shield" /> Connexion opérateur
    </button>
  )
}

function LinkState() {
  const { online, lastReadingAt, sourceLabel, simulated } = useLive()
  const now = useNow()
  const stale = !online || lastReadingAt == null || now - lastReadingAt > STALE_AFTER_MS
  return (
    <span className={`link-state ${stale ? 'stale' : 'ok'}`}>
      {!online
        ? 'Serveur injoignable'
        : `${simulated ? 'Simulateur' : sourceLabel || 'Serveur'} · mesure ${ago(lastReadingAt == null ? null : now - lastReadingAt)}`}
    </span>
  )
}

function Clock() {
  const now = useNow()
  return (
    <time className="clock" dateTime={new Date(now).toISOString()} aria-label="Heure du poste">
      {new Date(now).toLocaleTimeString('fr-FR')}
    </time>
  )
}

function SideNav({ current }) {
  const { alerts } = useLive()
  const active = activeAlarms(alerts)
  const critical = active.some((a) => a.level === 'critical')
  return (
    <nav className="sidenav" aria-label="Navigation principale">
      <ul>
        {ROUTES.map((r) => (
          <li key={r.path}>
            <a href={`#${r.path}`} aria-current={r.path === current ? 'page' : undefined}>
              <Icon name={r.icon} />
              {r.label}
              {r.path === '/alarmes' && active.length > 0 && (
                <span className={`nav-count ${critical ? '' : 'warning'}`}>
                  {active.length}
                  <span className="sr-only"> non acquittée{active.length > 1 ? 's' : ''}</span>
                </span>
              )}
            </a>
          </li>
        ))}
        {GRAFANA_URL && (
          <li>
            <a href={GRAFANA_URL} target="_blank" rel="noopener noreferrer">
              <Icon name="overview" />
              Historique (Grafana)
              <span className="sr-only"> : s'ouvre dans un nouvel onglet</span>
            </a>
          </li>
        )}
      </ul>
    </nav>
  )
}
