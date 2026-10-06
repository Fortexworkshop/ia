import { PEOPLE } from '../data/people.js'

const initials = (name) => name.split(' ').map((p) => p[0]).join('').slice(0, 2).toUpperCase()

export default function People() {
  return (
    <section>
      <h2>Individus détectés</h2>
      <p className="hint">Données simulées. Photos et noms sont des données personnelles : accès restreint à prévoir.</p>
      <div className="grid">
        {PEOPLE.map((p) => (
          <article className="card person" key={p.id}>
            {p.photoUrl ? <img src={p.photoUrl} alt={p.name} /> : <div className="avatar">{initials(p.name)}</div>}
            <div>
              <b>{p.name}</b>
              <p className="hint">Vu à {new Date(p.lastSeen).toLocaleTimeString('fr-FR')}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
