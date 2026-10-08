import { authHeaders } from './auth.js'
// Source réelle : backend FORTEX (REST + WebSocket), même contrat que le simulateur.
// Messages reçus : { type: 'reading' | 'alert' | 'command-ack' | 'status', ... }

export function createApiSource(baseUrl) {
  const base = baseUrl.replace(/\/$/, '')
  const wsUrl = base.replace(/^http/, 'ws') + '/ws'
  const listeners = new Set()
  const emit = (msg) => listeners.forEach((cb) => cb(msg))
  let ws = null
  let closed = false
  let retry = null

  const post = (path, body) =>
    fetch(base + path, {
      method: 'POST',
      headers: { ...authHeaders, ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    }).catch((err) => console.warn('Backend injoignable', err))

  // Historique au chargement : dernières mesures, alertes et presences enregistrees en base.
  async function loadHistory() {
    try {
      const [readings, alerts, presence] = await Promise.all([
        fetch(`${base}/api/v1/readings?limit=60`).then((r) => r.json()),
        fetch(`${base}/api/v1/alerts?limit=30`).then((r) => r.json()),
        fetch(`${base}/api/v1/presence?limit=50`).then((r) => r.json()),
      ])
      readings.forEach(emit)
      alerts.reverse().forEach(emit) // la page ajoute en tête : du plus ancien au plus récent
      presence.reverse().forEach((event) => emit({ type: 'presence', ...event }))
    } catch (err) {
      console.warn('Historique indisponible', err)
    }
  }

  function connect() {
    ws = new WebSocket(wsUrl)
    ws.onopen = () => emit({ type: 'status', online: true })
    ws.onmessage = (event) => emit(JSON.parse(event.data))
    ws.onclose = () => {
      emit({ type: 'status', online: false })
      if (!closed) retry = setTimeout(connect, 2000) // reconnexion automatique
    }
  }

  loadHistory()
  connect()

  return {
    label: 'Backend connecté',
    subscribe(cb) {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    sendCommand(cmd) {
      post('/api/v1/commands', cmd)
    },
    inject(kind) {
      post(`/api/v1/test/${kind}`)
    },
    close() {
      closed = true
      clearTimeout(retry)
      ws?.close()
    },
  }
}
