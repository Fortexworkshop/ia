// Source de données simulée (mode hors-ligne, sans backend) : même contrat que api.js.
// Contrat commun : { subscribe(cb) -> unsubscribe, sendCommand(cmd), inject(kind), ack(id), close() }.
// Les alarmes simulées viennent d'un simple seuil : ce n'est PAS l'IA (qui tourne côté serveur).

const rand = (n) => (Math.random() - 0.5) * n

export function createSimulator({ intervalMs = 2000 } = {}) {
  const listeners = new Set()
  const emit = (msg) => listeners.forEach((cb) => cb(msg))
  const state = { temp: 24, hum: 45, gas: 120, pir: 0 }
  const boosts = new Map() // scénarios en cours (cumulables) : kind -> fin
  const active = new Set() // alarmes en cours : une seule alarme par front montant
  let t = 0
  let nextId = 1

  const raise = (on, kind, value, unit, level, message) => {
    if (on && !active.has(kind)) {
      active.add(kind)
      emit({ type: 'alert', live: true, id: `sim-${nextId++}`, ts: Date.now(), device_id: 'SIM-01', source: 'simulateur', kind, value: +value.toFixed(1), unit, level, message })
    } else if (!on) active.delete(kind)
  }

  const tick = (ts = Date.now(), silent = false) => {
    t += 1
    for (const [kind, until] of boosts) if (until <= t) boosts.delete(kind)
    const on = (kind) => boosts.has(kind)
    state.temp += (on('heat') ? 2.4 : (24 - state.temp) * 0.15) + rand(0.3)
    state.hum = 45 + Math.sin(t / 30) * 4 + rand(1)
    state.gas += (on('gas') ? 90 : (120 - state.gas) * 0.2) + rand(6)
    state.pir = on('intrusion') ? 1 : 0
    emit({ type: 'reading', ts, temp: state.temp, hum: state.hum, gas: state.gas, pir: state.pir })
    if (silent) return
    raise(state.temp > 40, 'temperature', state.temp, '°C', 'critical', 'Surchauffe simulée')
    raise(state.gas > 600, 'gas', state.gas, 'ppm', 'critical', 'Fuite de gaz simulée')
    raise(state.pir === 1, 'presence', 1, '', 'warning', 'Mouvement simulé')
  }

  const id = setInterval(() => tick(), intervalMs)
  // Après l'abonnement : un historique court pour que les courbes ne démarrent pas vides
  queueMicrotask(() => {
    emit({ type: 'status', online: true })
    const start = Date.now() - 30 * intervalMs
    for (let i = 0; i < 30; i++) tick(start + i * intervalMs, true)
  })

  return {
    label: 'Simulateur local (sans serveur)',
    simulated: true,
    subscribe(cb) {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    sendCommand(cmd) {
      emit({ type: 'command-ack', ts: Date.now(), cmd, delivered: true })
      return Promise.resolve()
    },
    inject(kind) {
      boosts.set(kind, t + 10)
      return Promise.resolve()
    },
    ack: () => Promise.resolve(),
    close() {
      clearInterval(id)
    },
  }
}
