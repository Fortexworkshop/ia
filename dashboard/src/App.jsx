import { useEffect, useState } from 'react'
import Supervision from './pages/Supervision.jsx'
import People from './pages/People.jsx'
import Camera from './pages/Camera.jsx'

const ROUTES = [
  { path: '/', label: 'Supervision', Page: Supervision },
  { path: '/personnes', label: 'Individus', Page: People },
  { path: '/camera', label: 'Caméra', Page: Camera },
]
const THEMES = [
  { id: 'auto', label: 'Thème : automatique' },
  { id: 'light', label: 'Thème : clair' },
  { id: 'dark', label: 'Thème : sombre' },
]
const storedTheme = () => {
  try {
    return localStorage.getItem('theme') || 'auto'
  } catch {
    return 'auto'
  }
}
const current = () => window.location.hash.slice(1) || '/'

export default function App() {
  const [path, setPath] = useState(current)
  useEffect(() => {
    const onHash = () => setPath(current())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  const [theme, setTheme] = useState(storedTheme)
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
  const nextTheme = () => setTheme(THEMES[(THEMES.findIndex((t) => t.id === theme) + 1) % THEMES.length].id)
  const route = ROUTES.find((r) => r.path === path) ?? ROUTES[0]
  const { Page } = route

  useEffect(() => {
    document.title = `${route.label} · Fortex`
  }, [route])

  return (
    <>
      <a className="skip" href="#contenu">Aller au contenu</a>
      <header>
        <h1>Fortex <span>supervision</span></h1>
        <button onClick={nextTheme}>{THEMES.find((t) => t.id === theme).label}</button>
      </header>
      <nav aria-label="Navigation principale">
        {ROUTES.map((r) => (
          <a key={r.path} href={`#${r.path}`} aria-current={r.path === route.path ? 'page' : undefined}>
            {r.label}
          </a>
        ))}
      </nav>
      <main id="contenu" tabIndex={-1}>
        <Page />
      </main>
    </>
  )
}
