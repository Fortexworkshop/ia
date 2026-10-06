import { useEffect, useState } from 'react'
import Supervision from './pages/Supervision.jsx'
import People from './pages/People.jsx'
import Camera from './pages/Camera.jsx'

const ROUTES = [
  { path: '/', label: 'Supervision', Page: Supervision },
  { path: '/personnes', label: 'Individus', Page: People },
  { path: '/camera', label: 'Caméra', Page: Camera },
]
const current = () => window.location.hash.slice(1) || '/'

export default function App() {
  const [path, setPath] = useState(current)
  useEffect(() => {
    const onHash = () => setPath(current())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])
  const { Page } = ROUTES.find((r) => r.path === path) ?? ROUTES[0]

  return (
    <>
      <nav>
        {ROUTES.map((r) => (
          <a key={r.path} href={`#${r.path}`} className={r.path === path ? 'active' : ''}>
            {r.label}
          </a>
        ))}
      </nav>
      <Page />
    </>
  )
}
