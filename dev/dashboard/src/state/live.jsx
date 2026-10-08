// État temps réel partagé : UNE seule connexion (WebSocket ou simulateur) pour toutes les pages.
import { createContext, useContext, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { createSource } from '../data/source.js'

const HISTORY = 120 // mesures gardées en mémoire (4 min à 1 mesure / 2 s)
const MAX_ALERTS = 200
const MAX_PRESENCE = 200

const initial = {
  online: false,
  readings: [],
  lastReadingAt: null,
  alerts: [],
  commands: [],
  outputs: { buzzer: false, led: false },
  presence: [],
}

// Heures : millisecondes (mesures, alertes) ou texte ISO (présence) -> toujours des millisecondes
const toMs = (ts) => (typeof ts === 'number' ? ts : Date.parse(ts) || Date.now())

const alertKey = (a) => a.id ?? `${a.ts}-${a.kind}-${a.source}`

function reducer(state, raw) {
  const msg = raw.ts === undefined ? raw : { ...raw, ts: toMs(raw.ts) }
  switch (msg.type) {
    case 'status':
      return { ...state, online: msg.online }
    case 'reading': {
      const readings = [...state.readings, msg]
      // l'historique peut arriver après une mesure temps réel : on garde l'ordre chronologique
      if (readings.length > 1 && readings.at(-2).ts > msg.ts) readings.sort((a, b) => a.ts - b.ts)
      return {
        ...state,
        online: true,
        readings: readings.slice(-HISTORY),
        lastReadingAt: Math.max(state.lastReadingAt ?? 0, msg.ts),
      }
    }
    case 'alert': {
      const key = alertKey(msg)
      if (state.alerts.some((a) => alertKey(a) === key)) return state
      const alerts = [{ ...msg, key, acknowledged: Boolean(msg.acknowledged) }, ...state.alerts]
      return { ...state, alerts: alerts.sort((a, b) => b.ts - a.ts).slice(0, MAX_ALERTS) }
    }
    case 'ack': {
      const keys = new Set(msg.keys)
      return { ...state, alerts: state.alerts.map((a) => (keys.has(a.key) ? { ...a, acknowledged: true } : a)) }
    }
    case 'command-ack':
      return {
        ...state,
        commands: [msg, ...state.commands].slice(0, 20),
        outputs: { ...state.outputs, [msg.cmd.actuator]: msg.cmd.state },
      }
    case 'presence': {
      if (msg.id != null && state.presence.some((p) => p.id === msg.id)) return state
      return { ...state, presence: [msg, ...state.presence].sort((a, b) => b.ts - a.ts).slice(0, MAX_PRESENCE) }
    }
    default:
      return state
  }
}

const LiveContext = createContext(null)

export function LiveProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initial)
  const sourceRef = useRef(null)
  const [announcement, setAnnouncement] = useState('')

  useEffect(() => {
    const source = createSource()
    sourceRef.current = source
    const unsubscribe = source.subscribe((msg) => {
      dispatch(msg)
      // Annonce vocale (lecteur d'écran) des nouvelles alarmes temps réel, pas de l'historique
      if (msg.type === 'alert' && msg.live) {
        setAnnouncement(`${msg.level === 'critical' ? 'Alarme critique' : 'Avertissement'} : ${msg.message || msg.kind}`)
      }
    })
    return () => {
      unsubscribe()
      source.close?.()
    }
  }, [])

  const actions = useMemo(
    () => ({
      command: (actuator, value) => sourceRef.current?.sendCommand({ actuator, state: value }),
      inject: (kind) => sourceRef.current?.inject(kind),
      acknowledge: (alerts) => {
        const list = Array.isArray(alerts) ? alerts : [alerts]
        if (!list.length) return
        dispatch({ type: 'ack', keys: list.map((a) => a.key) }) // retour immédiat (INP)
        list.forEach((a) => a.id != null && sourceRef.current?.ack?.(a.id))
      },
    }),
    [],
  )

  const value = useMemo(
    () => ({ ...state, actions, sourceLabel: sourceRef.current?.label ?? '', simulated: Boolean(sourceRef.current?.simulated) }),
    [state, actions],
  )

  return (
    <LiveContext.Provider value={value}>
      {children}
      {/* Région d'annonce unique : role="alert" pour que l'alarme soit lue immédiatement (RGAA 7.5) */}
      <div className="sr-only" role="alert" aria-atomic="true">
        {announcement}
      </div>
    </LiveContext.Provider>
  )
}

export function useLive() {
  const ctx = useContext(LiveContext)
  if (!ctx) throw new Error('useLive doit être utilisé dans <LiveProvider>')
  return ctx
}

// Horloge partagée (1 s) : seuls les composants qui l'utilisent se re-rendent chaque seconde.
export function useNow(intervalMs = 1000) {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])
  return now
}
