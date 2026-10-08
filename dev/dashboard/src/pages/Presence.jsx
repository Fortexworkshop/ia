// Présence : qui est sur site (évacuation, sécurité), détections de la vision et pointages par geste.
// Événements du backend (type "presence") : historique au chargement puis WebSocket.
import { useMemo } from 'react'
import Icon from '../components/Icon.jsx'
import OperatorOnly from '../components/OperatorOnly.jsx'
import { ON_SITE, POINTAGES, isToday, lastPointages, time } from '../state/model.js'
import { useLive } from '../state/live.jsx'


export default function Presence() {
  const { presence, operator } = useLive()

  const today = useMemo(() => presence.filter((e) => isToday(e.ts)), [presence])
  const detections = useMemo(() => today.filter((e) => e.kind === 'detection'), [today])
  const pointages = useMemo(() => today.filter((e) => e.kind in POINTAGES), [today])
  const status = useMemo(() => lastPointages(presence), [presence])
  const onSite = status.filter((e) => e.kind !== 'sortie')
  const key = (e) => e.id ?? `${e.ts}-${e.kind}-${e.person}`
  const who = (person) => person || 'Personne non reconnue'

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Présence</h1>
          <p className="lede">
            Pointage sans contact : la personne est reconnue par la caméra, puis pointe d'un geste du pouce (haut :
            entrée, côté : pause ou reprise, bas : sortie).
          </p>
        </div>
      </div>

      {!operator ? (
        <OperatorOnly what="consulter la présence (données personnelles)" />
      ) : (
      <>
      <div className="grid split">
        <section className="panel" aria-labelledby="onsite-title">
          <div className="panel-head">
            <h2 id="onsite-title">Sur site maintenant</h2>
            <span className="tag">{onSite.length} personne{onSite.length > 1 ? 's' : ''}</span>
          </div>
          {status.length === 0 ? (
            <p className="empty-state">
              <Icon name="info" /> Aucun pointage aujourd'hui.
            </p>
          ) : (
            <ul className="onsite">
              {status.map((e) => (
                <li key={e.person}>
                  <span>
                    <b>{e.person}</b>
                  </span>
                  <span className={`tag ${e.kind === 'sortie' ? '' : e.kind === 'pause' ? 'warning' : 'ok'}`}>
                    {ON_SITE[e.kind]} depuis {time(e.ts)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="panel" aria-labelledby="det-title">
          <h2 id="det-title">Détections de la caméra</h2>
          {detections.length === 0 ? (
            <p className="empty-state">
              <Icon name="info" /> Aucune personne détectée aujourd'hui.
            </p>
          ) : (
            <ul className="onsite scroll">
              {detections.map((e) => (
                <li key={key(e)}>
                  <span>
                    <b>{who(e.person)}</b>
                  </span>
                  <time className="muted small" dateTime={new Date(e.ts).toISOString()}>
                    {time(e.ts)}
                  </time>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <section aria-labelledby="log-title">
        <h2 id="log-title" style={{ marginBottom: 'var(--sp-3)' }}>
          Journal des pointages du jour
        </h2>
        {pointages.length === 0 ? (
          <p className="empty-state panel">
            <Icon name="info" /> Aucun pointage aujourd'hui.
          </p>
        ) : (
          <div className="table-wrap">
            <table>
              <caption className="sr-only">Pointages du jour, du plus récent au plus ancien</caption>
              <thead>
                <tr>
                  <th scope="col">Heure</th>
                  <th scope="col">Personne</th>
                  <th scope="col">Pointage</th>
                </tr>
              </thead>
              <tbody>
                {pointages.map((e) => (
                  <tr key={key(e)}>
                    <td>
                      <time dateTime={new Date(e.ts).toISOString()}>{time(e.ts)}</time>
                    </td>
                    <th scope="row" style={{ fontWeight: 600 }}>
                      {who(e.person)}
                      </th>
                    <td>{POINTAGES[e.kind]}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      </>
      )}
    </div>
  )
}
