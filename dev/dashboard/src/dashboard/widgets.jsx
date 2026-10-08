// Catalogue des éléments (widgets) de la vue d'ensemble : contenu + réglages propres à chaque type.
// Le cadre (titre, barre d'outils d'édition) est fourni par WidgetGrid.
import { useMemo } from 'react'
import Alarm from '../components/Alarm.jsx'
import CameraFeed from '../components/CameraFeed.jsx'
import Icon from '../components/Icon.jsx'
import SensorTile from '../components/SensorTile.jsx'
import Switch from '../components/Switch.jsx'
import OperatorOnly from '../components/OperatorOnly.jsx'
import { ON_SITE, SENSORS, STALE_AFTER_MS, activeAlarms, ago, lastPointages, time } from '../state/model.js'
import { useLive, useNow } from '../state/live.jsx'

const sensorOf = (key) => SENSORS.find((s) => s.key === key) ?? SENSORS[0]

// Une alarme d'exercice émise par le serveur ne correspond à aucune mesure réelle : elle ne colore
// pas la tuile. Avec le simulateur local, les mesures changent vraiment : elle la colore.
const marksTile = (a) => a.source !== 'test'

/* ---------- Capteur ---------- */
function SensorWidget({ config }) {
  const { readings, alerts } = useLive()
  const now = useNow()
  const sensor = sensorOf(config.sensor)
  const values = useMemo(() => readings.map((r) => Number(r[sensor.key])), [readings, sensor.key])
  const alarm = useMemo(() => activeAlarms(alerts).find((a) => marksTile(a) && sensor.kinds.includes(a.kind)), [alerts, sensor])
  const last = readings.at(-1)
  const minutes = readings.length > 1 ? Math.max(1, Math.round((last.ts - readings[0].ts) / 60000)) : 0
  const lastEventTs = sensor.binary ? readings.findLast((r) => r[sensor.key])?.ts : undefined
  return (
    <SensorTile
      sensor={sensor}
      values={values}
      alarm={alarm}
      stale={Boolean(last) && now - last.ts > STALE_AFTER_MS}
      minutes={minutes}
      lastEventTs={lastEventTs}
      now={now}
    />
  )
}

function SensorSettings({ widget, onChange, idPrefix }) {
  return (
    <div className="field">
      <label htmlFor={`${idPrefix}-sensor`}>Grandeur mesurée</label>
      <select id={`${idPrefix}-sensor`} value={widget.config.sensor} onChange={(e) => onChange({ config: { sensor: e.target.value } })}>
        {SENSORS.map((s) => (
          <option key={s.key} value={s.key}>
            {s.label}
          </option>
        ))}
      </select>
    </div>
  )
}

/* ---------- Alarmes à traiter ---------- */
function AlarmsWidget({ config }) {
  const { alerts, actions, operator } = useLive()
  const active = useMemo(() => activeAlarms(alerts), [alerts])
  const limit = config.limit ?? 6
  return (
    <>
      {active.length === 0 ? (
        <p className="empty-state">
          <Icon name="check" /> Aucune alarme non acquittée.
        </p>
      ) : (
        <ul className="alarms scroll">
          {active.slice(0, limit).map((a) => (
            <Alarm key={a.key} alert={a} onAck={operator ? actions.acknowledge : null} />
          ))}
        </ul>
      )}
      <div className="btn-row">
        {operator && active.length > 1 && (
          <button type="button" className="btn small quiet" onClick={() => actions.acknowledge(active)}>
            Tout acquitter ({active.length})
          </button>
        )}
        {active.length > limit && (
          <a className="link-more" href="#/alarmes">
            Voir les {active.length} alarmes
          </a>
        )}
      </div>
    </>
  )
}

function AlarmsSettings({ widget, onChange, idPrefix }) {
  return (
    <div className="field">
      <label htmlFor={`${idPrefix}-limit`}>Nombre d'alarmes affichées</label>
      <input
        id={`${idPrefix}-limit`}
        type="number"
        min="1"
        max="30"
        inputMode="numeric"
        value={widget.config.limit ?? 6}
        onChange={(e) => onChange({ config: { limit: Math.max(1, Math.min(30, Number(e.target.value) || 1)) } })}
      />
    </div>
  )
}

/* ---------- Actionneurs ---------- */
function ActuatorsWidget() {
  const { outputs, commands, actions, operator } = useLive()
  const last = commands[0]
  return (
    <>
      <div className="switches">
        <Switch label="Buzzer" checked={outputs.buzzer} disabled={!operator} onChange={(v) => actions.command('buzzer', v)} detailOn="Sonne" />
        <Switch label="Voyant lumineux (LED)" checked={outputs.led} disabled={!operator} onChange={(v) => actions.command('led', v)} detailOn="Allumé" detailOff="Éteint" />
      </div>
      {!operator && <OperatorOnly what="commander le buzzer et le voyant" />}
      <p className="muted small">
        {last
          ? `Dernière commande à ${time(last.ts)} : ${last.cmd.actuator === 'led' ? 'voyant' : 'buzzer'} ${last.cmd.state ? 'activé' : 'coupé'}${last.delivered === false ? ' (non transmise : liaison MQTT indisponible)' : ''}.`
          : 'Une intrusion confirmée les déclenche automatiquement.'}
      </p>
    </>
  )
}

/* ---------- Sur site ---------- */
function OnSiteWidget() {
  const { presence, operator } = useLive()
  const status = useMemo(() => lastPointages(presence), [presence])
  const here = status.filter((e) => e.kind !== 'sortie')
  if (!operator) return <OperatorOnly what="voir les personnes présentes (données personnelles)" />
  return status.length === 0 ? (
    <p className="empty-state">
      <Icon name="info" /> Aucun pointage aujourd'hui.
    </p>
  ) : (
    <>
      <p>
        <b>{here.length}</b> personne{here.length > 1 ? 's' : ''} sur site
      </p>
      <ul className="onsite">
        {status.map((e) => (
          <li key={e.person}>
            <b>{e.person}</b>
            <span className={`tag ${e.kind === 'sortie' ? '' : e.kind === 'pause' ? 'warning' : 'ok'}`}>
              {ON_SITE[e.kind]} · {time(e.ts)}
            </span>
          </li>
        ))}
      </ul>
    </>
  )
}

/* ---------- Caméra ---------- */
function CameraWidget() {
  const { chain, simulated } = useLive()
  // état de la vision interrogé toutes les 5 s par LiveProvider (chaîne de surveillance)
  const vision = simulated ? null : chain?.vision ?? { running: false, pending: true }
  return (
    <>
      <CameraFeed vision={vision} />
      <a className="link-more" href="#/camera">
        Piloter la caméra
      </a>
    </>
  )
}

/* ---------- Consignes ---------- */
function NoteWidget({ config }) {
  return (
    <>
      {config.text ? (
        <p className="note">{config.text}</p>
      ) : (
        <p className="muted">Aucune consigne. Passez en mode « Personnaliser » pour en écrire.</p>
      )}
      {/* Rappel visible : une consigne écrite ici n'apparaît pas sur les autres postes */}
      <p className="muted small">Consigne enregistrée sur ce poste uniquement.</p>
    </>
  )
}

function NoteSettings({ widget, onChange, idPrefix }) {
  return (
    <div className="field wide">
      <label htmlFor={`${idPrefix}-text`}>Texte affiché</label>
      <textarea
        id={`${idPrefix}-text`}
        rows={4}
        maxLength={1000}
        value={widget.config.text ?? ''}
        onChange={(e) => onChange({ config: { text: e.target.value } })}
        aria-describedby={`${idPrefix}-text-help`}
      />
      <p id={`${idPrefix}-text-help`} className="help">
        Exemple : numéro d'astreinte, procédure en cas d'alarme gaz. Visible seulement sur ce poste.
      </p>
    </div>
  )
}

/* ---------- Exercice ---------- */
const SCENARIOS = [
  { kind: 'heat', label: 'Surchauffe' },
  { kind: 'gas', label: 'Fuite de gaz' },
  { kind: 'intrusion', label: 'Intrusion' },
]
function ExerciseWidget() {
  const { actions, simulated, operator } = useLive()
  if (!operator) return <OperatorOnly what="lancer un exercice" />
  return (
    <>
      <p className="muted">
        Déclenche un scénario pour tester la chaîne d'alerte.{' '}
        {simulated ? 'Simulateur local : les mesures évoluent pendant 20 s.' : 'Le serveur émet une alarme marquée « Exercice », distincte des alarmes réelles.'}
      </p>
      <div className="btn-row">
        {SCENARIOS.map((s) => (
          <button key={s.kind} type="button" className="btn" onClick={() => actions.inject(s.kind)}>
            {s.label}
          </button>
        ))}
      </div>
    </>
  )
}

/* ---------- Chaîne de surveillance ---------- */
// N'affiche que ce que le serveur remonte réellement ; ce qui n'est pas supervisé est dit comme tel.
function ChainWidget() {
  const { chain, online, lastReadingAt, simulated } = useLive()
  const now = useNow()
  if (simulated) return <p className="muted">Simulateur local : pas de chaîne de surveillance à superviser.</p>
  // Avant la première réponse, les six lignes sont déjà là (« vérification ») : aucun saut de mise en page
  const device = chain?.devices[0]
  const fresh = lastReadingAt != null && now - lastReadingAt <= STALE_AFTER_MS
  const pending = ['pending', 'vérification…']
  const rows = !chain
    ? ['Boîtier', 'Serveur de supervision', 'Liaison MQTT (TLS)', 'Base de données', 'IA vision', 'IA prédictive'].map((n) => [n, ...pending])
    : [
        ['Boîtier', fresh ? 'ok' : 'down', fresh ? `${device?.node_id ?? 'en ligne'} · mesure ${ago(now - lastReadingAt)}` : `aucune mesure ${ago(lastReadingAt == null ? null : now - lastReadingAt)}`],
        ['Serveur de supervision', chain.health && online ? 'ok' : 'down', chain.health ? (online ? 'joignable, temps réel actif' : 'joignable, temps réel coupé') : 'injoignable'],
        ['Liaison MQTT (TLS)', chain.health?.mqtt_connected ? 'ok' : 'down', chain.health?.mqtt_connected ? 'connectée' : 'coupée'],
        ['Base de données', chain.health?.database_ok ? 'ok' : 'down', chain.health?.database_ok ? 'historique enregistré' : 'indisponible : rien n’est archivé'],
        ['IA vision', !chain.vision?.available ? 'unknown' : chain.vision.running ? 'ok' : 'down', !chain.vision?.available ? 'non pilotable depuis ce serveur' : chain.vision.running ? 'détection d’intrusion active' : chain.vision.crashed ? `arrêtée sur une erreur (code ${chain.vision.exit_code}) : voir data/vision.log` : 'arrêtée : aucune détection'],
        ['IA prédictive', 'unknown', 'état non remonté au serveur'],
      ]
  const LABEL = { ok: 'Actif', down: 'Hors service', unknown: 'Non supervisé', pending: 'En attente' }
  return (
    <ul className="chain">
      {rows.map(([name, state, detail]) => (
        <li key={name} className={state}>
          <span className="chain-name">{name}</span>
          <span className="chain-state">
            <Icon name={state === 'ok' ? 'check' : state === 'down' ? 'warning' : 'info'} /> {LABEL[state]}
          </span>
          <span className="chain-detail muted small">{detail}</span>
        </li>
      ))}
    </ul>
  )
}

/* ---------- Registre ---------- */
export const WIDGETS = {
  chain: {
    label: 'Chaîne de surveillance',
    description: 'État du boîtier, du serveur, de la liaison, de la base et des IA.',
    icon: 'shield',
    sizes: ['m', 'l'],
    defaultSize: 'm',
    defaults: {},
    title: () => 'Chaîne de surveillance',
    Component: ChainWidget,
  },
  sensor: {
    label: 'Capteur',
    description: 'Valeur en direct, tendance et courbe d’une grandeur mesurée.',
    icon: 'overview',
    sizes: ['s', 'm', 'l'],
    defaultSize: 's',
    defaults: { sensor: 'temp' },
    title: (w) => sensorOf(w.config.sensor).label,
    Component: SensorWidget,
    Settings: SensorSettings,
  },
  alarms: {
    label: 'Alarmes à traiter',
    description: 'Alarmes non acquittées, de la plus grave à la plus récente.',
    icon: 'alarm',
    sizes: ['m', 'l'],
    defaultSize: 'm',
    defaults: { limit: 6 },
    title: () => 'Alarmes à traiter',
    Component: AlarmsWidget,
    Settings: AlarmsSettings,
  },
  actuators: {
    label: 'Actionneurs',
    description: 'Commande du buzzer et du voyant du boîtier.',
    icon: 'mute',
    sizes: ['s', 'm', 'l'],
    defaultSize: 'm',
    defaults: {},
    title: () => 'Actionneurs du boîtier',
    Component: ActuatorsWidget,
  },
  onsite: {
    label: 'Personnes sur site',
    description: 'Dernier pointage de chaque personne aujourd’hui (évacuation).',
    icon: 'presence',
    sizes: ['s', 'm', 'l'],
    defaultSize: 'm',
    defaults: {},
    title: () => 'Personnes sur site',
    Component: OnSiteWidget,
  },
  camera: {
    label: 'Caméra',
    description: 'Flux vidéo annoté par l’IA de vision.',
    icon: 'camera',
    sizes: ['m', 'l'],
    defaultSize: 'm',
    defaults: {},
    title: () => 'Caméra',
    Component: CameraWidget,
  },
  note: {
    label: 'Consignes de poste',
    description: 'Texte libre : astreinte, procédures, rappels.',
    icon: 'info',
    sizes: ['s', 'm', 'l'],
    defaultSize: 'm',
    defaults: { text: '' },
    title: () => 'Consignes de poste',
    Component: NoteWidget,
    Settings: NoteSettings,
  },
  exercise: {
    label: 'Mode exercice',
    description: 'Simuler un incident pour tester la chaîne d’alerte.',
    icon: 'flask',
    sizes: ['m', 'l'],
    defaultSize: 'l',
    defaults: {},
    title: () => 'Mode exercice : simuler un incident',
    Component: ExerciseWidget,
  },
}

export const titleOf = (w) => w.title?.trim() || WIDGETS[w.type].title(w)
