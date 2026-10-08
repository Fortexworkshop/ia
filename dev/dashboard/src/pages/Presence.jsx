// Journal de présence : détections de la vision et pointages par geste du pouce.
// Les événements viennent du backend (type "presence") : historique au chargement, puis WebSocket.
import { useEffect, useMemo, useRef, useState } from 'react'
import { createSource } from '../data/source.js'
import { peopleApi } from '../data/people.js'

const HISTORY = 50
const POINTAGES = { entree: 'Entrée', pause: 'Pause', reprise: 'Reprise', sortie: 'Sortie' }
const time = (ts) => new Date(ts).toLocaleTimeString('fr-FR')

export default function Presence() {
  const sourceRef = useRef(null)
  const [events, setEvents] = useState([])
  const [online, setOnline] = useState(false)
  const [roles, setRoles] = useState({})

  // Role de chaque individu (page « Individus »), relu toutes les 15 s
  useEffect(() => {
    if (!peopleApi) return undefined
    const load = () =>
      peopleApi
        .list()
        .then((people) => setRoles(Object.fromEntries(people.map((p) => [p.name, p.role]))))
        .catch(() => {})
    load()
    const id = setInterval(load, 15000)
    return () => clearInterval(id)
  }, [])
  const who = (person) => (person ? (roles[person] ? `${person} (${roles[person]})` : person) : 'personne inconnue')

  useEffect(() => {
    const source = createSource()
    sourceRef.current = source
    const unsub = source.subscribe((msg) => {
      if (msg.type === 'status') {
        setOnline(msg.online)
      } else if (msg.type === 'presence') {
        setOnline(true)
        setEvents((list) => [msg, ...list].slice(0, HISTORY))
      }
    })
    return () => {
      unsub()
      source.close?.()
    }
  }, [])

  const detections = useMemo(() => events.filter((e) => e.kind === 'detection'), [events])
  const pointages = useMemo(() => events.filter((e) => e.kind in POINTAGES), [events])
  const key = (event) => event.id ?? `${event.ts}-${event.kind}`

  return (
    <div className="page">
      <p role="status" className={online ? 'badge ok' : 'badge'}>
        {online ? sourceRef.current?.label ?? 'Source active' : 'En attente de données'}
      </p>

      <section className="card">
        <h2 id="detections">Détections</h2>
        <p className="hint">Une ligne à chaque fois qu'une personne se présente devant la caméra.</p>
        {detections.length === 0 ? (
          <p className="hint" role="status">Aucune personne détectée pour l'instant.</p>
        ) : (
          <ul className="list" aria-labelledby="detections" aria-live="polite">
            {detections.map((event) => (
              <li key={key(event)}>
                {time(event.ts)} · personne détectée · <b>{who(event.person)}</b>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="card">
        <h2 id="pointages">Pointages</h2>
        <p className="hint">Pouce en haut = entrée, pouce de côté = pause puis reprise, pouce en bas = sortie, par la personne reconnue.</p>
        {pointages.length === 0 ? (
          <p className="hint" role="status">Aucun pointage pour l'instant.</p>
        ) : (
          <ul className="list" aria-labelledby="pointages" aria-live="polite">
            {pointages.map((event) => (
              <li key={key(event)} className={event.kind}>
                {time(event.ts)} · <b>{POINTAGES[event.kind]}</b> · {who(event.person)}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
