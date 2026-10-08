// État temps réel partagé : UNE seule connexion (WebSocket ou simulateur) pour toutes les pages.
import { createContext, useContext, useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { getToken, login as loginWith, logout, onAuthChange } from '../data/auth.js'
import { chainAvailable, fetchChain } from '../data/chain.js'
import { base } from '../data/http.js'
import { createSource } from '../data/source.js'

const CHAIN_POLL_MS = 5000

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
  chain: null, // état des services (serveur, base, MQTT, vision, boîtier)
  error: null, // dernier échec d'action, affiché à l'opérateur (OWASP A10)
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
    case 'ack-local': {
      const keys = new Set(msg.keys)
      return { ...state, alerts: state.alerts.map((a) => (keys.has(a.key) ? { ...a, acknowledged: msg.value } : a)) }
    }
    case 'ack': // acquittement fait sur un autre poste
      return { ...state, alerts: state.alerts.map((a) => (a.id === msg.id ? { ...a, acknowledged: true } : a)) }
    case 'chain':
      return { ...state, chain: msg.chain }
    case 'error':
      return { ...state, error: msg.text ? { text: msg.text, at: Date.now() } : null }
    case 'clear-private': // déconnexion : plus aucune donnée personnelle en mémoire
      return { ...state, presence: [] }
    case 'auth':
      return msg.ok ? state : { ...state, error: { text: 'Code opérateur refusé par le serveur : session fermée.', at: Date.now() } }
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

  // Session opérateur
  const [operator, setOperator] = useState(() => !chainAvailable || Boolean(getToken()))
  useEffect(
    () =>
      onAuthChange((logged) => {
        setOperator(!chainAvailable || logged)
        if (!logged) dispatch({ type: 'clear-private' })
      }),
    [],
  )

  // État de la chaîne de surveillance (serveur seulement : le simulateur n'en a pas)
  useEffect(() => {
    if (!chainAvailable) return undefined
    let alive = true
    const poll = () => fetchChain().then((chain) => alive && dispatch({ type: 'chain', chain }))
    poll()
    const id = setInterval(poll, CHAIN_POLL_MS)
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [])

  const actions = useMemo(() => {
    const fail = (what) => (err) => dispatch({ type: 'error', text: `${what} : ${err.message}` })
    return {
      command: (actuator, value) =>
        sourceRef.current?.sendCommand({ actuator, state: value })?.catch(fail(`Commande ${actuator === 'led' ? 'du voyant' : 'du buzzer'} non envoyée`)),
      inject: (kind) => sourceRef.current?.inject(kind)?.catch(fail('Exercice non lancé')),
      acknowledge: (alerts) => {
        const list = (Array.isArray(alerts) ? alerts : [alerts]).filter((a) => !a.acknowledged)
        if (!list.length) return
        const keys = list.map((a) => a.key)
        dispatch({ type: 'ack-local', keys, value: true }) // retour immédiat (INP)
        Promise.all(list.filter((a) => a.id != null).map((a) => sourceRef.current?.ack?.(a.id))).catch((err) => {
          dispatch({ type: 'ack-local', keys, value: false }) // refusé : l'alarme redevient à traiter
          fail('Acquittement refusé')(err)
        })
      },
      dismissError: () => dispatch({ type: 'error', text: null }),
      login: (code) => loginWith(base, code),
      logout,
    }
  }, [])

  const value = useMemo(
    // simulé = aucun serveur configuré : connu dès le chargement (pas de changement d'affichage, CLS)
    () => ({ ...state, actions, operator, sourceLabel: chainAvailable ? 'Serveur FORTEX' : 'Simulateur', simulated: !chainAvailable }),
    [state, actions, operator],
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
