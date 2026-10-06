import { useEffect, useMemo, useRef, useState } from 'react'
import { createSource } from '../data/source.js'
import Sparkline from '../Sparkline.jsx'

const HISTORY = 60
const SENSORS = [
  { key: 'temp', label: 'Température', unit: '°C', color: 'var(--series-temp)', digits: 1 },
  { key: 'hum', label: 'Humidité', unit: '%', color: 'var(--series-hum)', digits: 0 },
  { key: 'gas', label: 'Gaz / fumées', unit: 'ppm', color: 'var(--series-gas)', digits: 0 },
  { key: 'pir', label: 'Présence', unit: '', color: 'var(--series-presence)', digits: 0, min: 0, max: 1 },
]
const TESTS = [
  { kind: 'heat', label: 'Surchauffe' },
  { kind: 'gas', label: 'Fuite de gaz' },
  { kind: 'intrusion', label: 'Intrusion' },
]
const LEVELS = { critical: 'critique', warning: 'avertissement' }
const time = (ts) => new Date(ts).toLocaleTimeString('fr-FR')

export default function Supervision() {
  const sourceRef = useRef(null)
  const [readings, setReadings] = useState([])
  const [alerts, setAlerts] = useState([])
  const [log, setLog] = useState([])
  const [outputs, setOutputs] = useState({ buzzer: false, led: false })
  const [online, setOnline] = useState(false)

  useEffect(() => {
    const source = createSource()
    sourceRef.current = source
    const unsub = source.subscribe((msg) => {
      if (msg.type === 'reading') {
        setOnline(true)
        setReadings((r) => [...r.slice(-(HISTORY - 1)), msg])
      } else if (msg.type === 'alert') {
        setAlerts((a) => [msg, ...a].slice(0, 30))
      } else if (msg.type === 'command-ack') {
        setLog((l) => [msg, ...l].slice(0, 10))
      }
    })
    return () => {
      unsub()
      source.close?.()
    }
  }, [])

  const last = readings.at(-1)
  const series = useMemo(
    () => Object.fromEntries(SENSORS.map((s) => [s.key, readings.map((r) => r[s.key])])),
    [readings],
  )

  const toggle = (name) => {
    const next = !outputs[name]
    setOutputs((o) => ({ ...o, [name]: next }))
    sourceRef.current.sendCommand({ actuator: name, state: next })
  }

  return (
    <div className="page">
      <p role="status" className={online ? 'badge ok' : 'badge'}>
        {online ? 'Source simulée active' : 'En attente de données'}
      </p>

      <section className="grid">
        {SENSORS.map((s) => (
          <article className="card" key={s.key}>
            <h2>{s.label}</h2>
            <p className="value">
              {last ? last[s.key].toFixed(s.digits) : '–'} <small>{s.unit}</small>
            </p>
            <Sparkline label={`Courbe : ${s.label}`} values={series[s.key]} color={s.color} min={s.min} max={s.max} />
          </article>
        ))}
      </section>

      <section className="grid two">
        <article className="card">
          <h2>Commandes (actionneurs)</h2>
          <div className="row">
            <button aria-pressed={outputs.buzzer} className={outputs.buzzer ? 'on' : ''} onClick={() => toggle('buzzer')}>
              Buzzer : {outputs.buzzer ? 'activé' : 'désactivé'}
            </button>
            <button aria-pressed={outputs.led} className={outputs.led ? 'on' : ''} onClick={() => toggle('led')}>
              LED : {outputs.led ? 'activée' : 'désactivée'}
            </button>
          </div>
          <ul className="list" aria-live="polite">
            {log.map((l) => (
              <li key={l.ts + l.cmd.actuator}>
                {time(l.ts)} · {l.cmd.actuator} → {l.cmd.state ? 'activé' : 'désactivé'}
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h2>Plateforme de test</h2>
          <p className="hint">Injecte un scénario dans le simulateur (8 s).</p>
          <div className="row">
            {TESTS.map((t) => (
              <button key={t.kind} onClick={() => sourceRef.current.inject(t.kind)}>
                {t.label}
              </button>
            ))}
          </div>
        </article>
      </section>

      <section className="card">
        <h2 id="alertes">Alertes</h2>
        {alerts.length === 0 ? (
          <p className="hint" role="status">Aucune alerte.</p>
        ) : (
          <ul className="list" aria-labelledby="alertes" aria-live="polite">
            {alerts.map((a, i) => (
              <li key={a.ts + a.kind + i} className={a.level}>
                {time(a.ts)} · <b>{a.kind}</b> {a.value}
                {a.unit} · {LEVELS[a.level]}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
