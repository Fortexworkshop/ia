import { useMemo, useState } from 'react'
import Icon from '../components/Icon.jsx'
import { SOURCES, dateTime, isExercise, kindLabel, levelOf, sourceLabel } from '../state/model.js'
import { useLive } from '../state/live.jsx'

const STATES = { open: 'Non acquittées', all: 'Toutes' }

export default function Alarms() {
  const { alerts, actions } = useLive()
  const [state, setState] = useState('open')
  const [level, setLevel] = useState('all')
  const [source, setSource] = useState('all')

  const rows = useMemo(
    () =>
      alerts.filter(
        (a) =>
          (state === 'all' || !a.acknowledged) &&
          (level === 'all' || a.level === level) &&
          (source === 'all' || a.source === source),
      ),
    [alerts, state, level, source],
  )
  const open = rows.filter((a) => !a.acknowledged)
  const sources = useMemo(() => [...new Set(alerts.map((a) => a.source).filter(Boolean))], [alerts])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Alarmes</h1>
          <p className="lede">
            Journal des alarmes du site. Acquitter une alarme confirme qu'un opérateur l'a prise en compte ; elle reste dans
            l'historique.
          </p>
        </div>
        {open.length > 0 && (
          <button type="button" className="btn primary" onClick={() => actions.acknowledge(open)}>
            Acquitter les {open.length} affichées
          </button>
        )}
      </div>

      <form className="panel filters" aria-label="Filtrer les alarmes" onSubmit={(e) => e.preventDefault()}>
        <div className="field">
          <label htmlFor="f-state">État</label>
          <select id="f-state" value={state} onChange={(e) => setState(e.target.value)}>
            {Object.entries(STATES).map(([v, l]) => (
              <option key={v} value={v}>
                {l}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-level">Niveau</label>
          <select id="f-level" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="all">Tous</option>
            <option value="critical">Critique</option>
            <option value="warning">Avertissement</option>
          </select>
        </div>
        <div className="field">
          <label htmlFor="f-source">Origine</label>
          <select id="f-source" value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="all">Toutes</option>
            {sources.map((s) => (
              <option key={s} value={s}>
                {SOURCES[s] ?? s}
              </option>
            ))}
          </select>
        </div>
        <p className="muted small" role="status">
          {rows.length} alarme{rows.length > 1 ? 's' : ''} affichée{rows.length > 1 ? 's' : ''}
        </p>
      </form>

      {rows.length === 0 ? (
        <p className="empty-state panel">
          <Icon name="check" /> Aucune alarme ne correspond à ces filtres.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <caption className="sr-only">Alarmes, de la plus récente à la plus ancienne</caption>
            <thead>
              <tr>
                <th scope="col">Niveau</th>
                <th scope="col">Alarme</th>
                <th scope="col">Origine</th>
                <th scope="col">Date</th>
                <th scope="col">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {rows.map((a) => {
                const lvl = levelOf(a)
                return (
                  <tr key={a.key} className={a.acknowledged ? 'acked' : a.level}>
                    <td>
                      <span className="level">
                        <Icon name={lvl.icon} /> {lvl.label}
                      </span>
                    </td>
                    <th scope="row" style={{ fontWeight: 600 }}>
                      {kindLabel(a.kind)}
                      {a.unit && a.value !== '' && a.value != null && ` (${a.value}${a.unit})`}
                      {a.message && <div className="muted small">{a.message}</div>}
                    </th>
                    <td>
                      {sourceLabel(a.source)} {isExercise(a) && <span className="tag exercise">exercice</span>}
                    </td>
                    <td>
                      <time dateTime={new Date(a.ts).toISOString()}>{dateTime(a.ts)}</time>
                    </td>
                    <td className="num">
                      {a.acknowledged ? (
                        <span className="tag">Acquittée</span>
                      ) : (
                        <button type="button" className="btn small" onClick={() => actions.acknowledge(a)}>
                          Acquitter<span className="sr-only"> : {kindLabel(a.kind)}, {dateTime(a.ts)}</span>
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
