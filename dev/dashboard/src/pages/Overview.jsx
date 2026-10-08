import { useMemo } from 'react'
import Alarm from '../components/Alarm.jsx'
import Icon from '../components/Icon.jsx'
import SensorTile from '../components/SensorTile.jsx'
import SiteState from '../components/SiteState.jsx'
import Switch from '../components/Switch.jsx'
import { SENSORS, STALE_AFTER_MS, activeAlarms, time } from '../state/model.js'

// Une alarme d'exercice émise par le serveur ne correspond à aucune mesure réelle : elle ne colore
// pas la tuile. Avec le simulateur local, les mesures changent vraiment : elle la colore.
const marksTile = (a) => a.source !== 'test'
import { useLive, useNow } from '../state/live.jsx'

const SCENARIOS = [
  { kind: 'heat', label: 'Surchauffe' },
  { kind: 'gas', label: 'Fuite de gaz' },
  { kind: 'intrusion', label: 'Intrusion' },
]

export default function Overview() {
  const { readings, alerts, outputs, commands, actions, simulated } = useLive()
  const active = useMemo(() => activeAlarms(alerts), [alerts])

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Vue d'ensemble</h1>
          <p className="lede">Site SENTINEL-X-01 · micro-centrale AetherCorp</p>
        </div>
      </div>

      <SiteState />

      <Sensors readings={readings} active={active} />

      <div className="grid split">
        <section className="panel" aria-labelledby="active-title">
          <div className="panel-head">
            <h2 id="active-title">Alarmes à traiter</h2>
            {active.length > 0 && (
              <button type="button" className="btn small quiet" onClick={() => actions.acknowledge(active)}>
                Tout acquitter ({active.length})
              </button>
            )}
          </div>
          {active.length === 0 ? (
            <p className="empty-state">
              <Icon name="check" /> Aucune alarme non acquittée.
            </p>
          ) : (
            <ul className="alarms scroll" aria-labelledby="active-title">
              {active.slice(0, 6).map((a) => (
                <Alarm key={a.key} alert={a} onAck={actions.acknowledge} />
              ))}
            </ul>
          )}
          {active.length > 6 && <a href="#/alarmes">Voir les {active.length} alarmes</a>}
        </section>

        <section className="panel" aria-labelledby="act-title">
          <h2 id="act-title">Actionneurs du boîtier</h2>
          <p className="muted small">Signalisation locale sur site. Une intrusion confirmée les déclenche automatiquement.</p>
          <div className="switches">
            <Switch label="Buzzer" checked={outputs.buzzer} onChange={(v) => actions.command('buzzer', v)} detailOn="Sonne" />
            <Switch label="Voyant lumineux (LED)" checked={outputs.led} onChange={(v) => actions.command('led', v)} detailOn="Allumé" detailOff="Éteint" />
          </div>
          {commands.length > 0 && (
            <p className="muted small">
              Dernière commande à {time(commands[0].ts)} : {commands[0].cmd.actuator === 'led' ? 'voyant' : 'buzzer'}{' '}
              {commands[0].cmd.state ? 'activé' : 'coupé'}
              {commands[0].delivered === false && ' (non transmise au boîtier : liaison MQTT indisponible)'}
            </p>
          )}
        </section>
      </div>

      <details className="exercise">
        <summary>
          <Icon name="flask" width="20" height="20" /> Mode exercice : simuler un incident
        </summary>
        <div>
          <p className="muted">
            Déclenche un scénario pour tester la chaîne d'alerte.{' '}
            {simulated
              ? 'Simulateur local : les mesures évoluent pendant 20 s.'
              : 'Le serveur émet une alarme marquée « Exercice », distincte des alarmes réelles.'}
          </p>
          <div className="btn-row">
            {SCENARIOS.map((s) => (
              <button key={s.kind} type="button" className="btn" onClick={() => actions.inject(s.kind)}>
                {s.label}
              </button>
            ))}
          </div>
        </div>
      </details>
    </div>
  )
}

// Isolé : seul ce bloc se re-rend chaque seconde (fraîcheur des données), pas toute la page.
function Sensors({ readings, active }) {
  const now = useNow()
  const last = readings.at(-1)
  const stale = !last || now - last.ts > STALE_AFTER_MS
  const minutes = readings.length > 1 ? Math.max(1, Math.round((readings.at(-1).ts - readings[0].ts) / 60000)) : 0
  const series = useMemo(() => Object.fromEntries(SENSORS.map((s) => [s.key, readings.map((r) => Number(r[s.key]))])), [readings])

  return (
    <section aria-labelledby="sensors-title">
      <h2 id="sensors-title" className="sr-only">
        Mesures des capteurs
      </h2>
      <div className="grid sensors">
        {SENSORS.map((s) => (
          <SensorTile
            key={s.key}
            sensor={s}
            values={series[s.key]}
            alarm={active.find((a) => marksTile(a) && s.kinds.includes(a.kind))}
            stale={stale && readings.length > 0}
            minutes={minutes}
          />
        ))}
      </div>
    </section>
  )
}
