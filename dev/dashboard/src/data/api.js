// Source réelle : serveur FORTEX (REST + WebSocket), même contrat que le simulateur.
// Messages reçus : { type: 'reading' | 'alert' | 'command-ack' | 'presence' | 'ack' | 'status' | 'auth', ... }
import { getToken, onAuthChange } from './auth.js'
import { request } from './http.js'
import { validMessage } from './validate.js'

export function createApiSource(baseUrl) {
  const base = baseUrl.replace(/\/$/, '')
  const wsUrl = base.replace(/^http/, 'ws') + '/ws'
  const listeners = new Set()
  const emit = (msg) => listeners.forEach((cb) => cb(msg))
  let ws = null
  let closed = false
  let retry = null
  let rejected = 0

  // Historique au chargement. Chaque partie peut échouer seule sans bloquer les autres (OWASP A10).
  async function loadHistory() {
    const parts = await Promise.allSettled([request('/api/v1/readings?limit=120'), request('/api/v1/alerts?limit=50')])
    const [readings, alerts] = parts.map((p) => (p.status === 'fulfilled' && Array.isArray(p.value) ? p.value : []))
    readings.forEach((m) => accept(m)) // historique : jamais annoncé comme nouvelle alarme
    alerts.reverse().forEach((m) => accept(m))
    if (parts.some((p) => p.status === 'rejected')) emit({ type: 'error', text: 'Historique partiellement indisponible : seules les données en direct sont affichées.' })
    await loadPresence()
  }

  // Présence : données personnelles, chargées seulement en session opérateur
  async function loadPresence() {
    if (!getToken()) return
    try {
      const events = await request('/api/v1/presence?limit=100')
      if (Array.isArray(events)) events.reverse().forEach((e) => accept({ type: 'presence', ...e }))
    } catch {
      /* session refusée : expire() a déjà été appelé */
    }
  }

  function accept(msg, live = false) {
    if (!validMessage(msg)) {
      rejected += 1
      if (rejected <= 5) console.warn('Message ignoré (format inattendu)', msg?.type)
      return
    }
    emit(live && msg.type === 'alert' ? { ...msg, live: true } : msg)
  }

  const authenticate = () => {
    const token = getToken()
    if (token && ws?.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'auth', token }))
  }

  function connect() {
    ws = new WebSocket(wsUrl)
    ws.onopen = () => {
      emit({ type: 'status', online: true })
      authenticate()
    }
    ws.onmessage = (event) => {
      let msg
      try {
        msg = JSON.parse(event.data)
      } catch {
        return accept(null)
      }
      accept(msg, true)
    }
    ws.onclose = () => {
      emit({ type: 'status', online: false })
      if (!closed) retry = setTimeout(connect, 2000) // reconnexion automatique
    }
  }

  const unwatch = onAuthChange((logged) => {
    if (logged) {
      authenticate()
      loadPresence()
    } else ws?.close() // déconnexion : nouvelle connexion anonyme (plus de données personnelles)
  })

  loadHistory()
  connect()

  return {
    label: 'Serveur FORTEX',
    subscribe(cb) {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    // Les actions renvoient une promesse : l'interface affiche l'échec (OWASP A10)
    sendCommand: (cmd) => request('/api/v1/commands', { method: 'POST', body: cmd }),
    inject: (kind) => request(`/api/v1/test/${encodeURIComponent(kind)}`, { method: 'POST' }),
    ack: (id) => request(`/api/v1/alerts/${encodeURIComponent(id)}/ack`, { method: 'POST' }),
    close() {
      closed = true
      unwatch()
      clearTimeout(retry)
      ws?.close()
    },
  }
}
