// Source de données simulée : remplace l'ESP8266 pour la démo (option B, PC serveur local).
// Contrat commun à toute source : { subscribe(cb) -> unsubscribe, sendCommand(cmd), inject(kind) }.
// Format d'un message : { type: 'reading' | 'alert' | 'command-ack', ... }.
// Le schéma réel de POST /api/v1/alerts reste à fixer avec l'équipe backend : celui-ci est provisoire.

const rand = (n) => (Math.random() - 0.5) * n

export function createSimulator({ intervalMs = 1000 } = {}) {
  const listeners = new Set()
  let t = 0
  const state = { temp: 24, hum: 45, gas: 120, pir: 0, boost: null }
  const emit = (msg) => listeners.forEach((cb) => cb(msg))

  const tick = () => {
    t += 1
    if (state.boost?.until <= t) state.boost = null
    const b = state.boost
    state.temp += (b?.kind === 'heat' ? 1.8 : (24 - state.temp) * 0.1) + rand(0.3)
    state.hum = 45 + Math.sin(t / 30) * 4 + rand(1)
    state.gas += (b?.kind === 'gas' ? 60 : (120 - state.gas) * 0.15) + rand(6)
    state.pir = b?.kind === 'intrusion' ? 1 : 0

    const ts = Date.now()
    emit({ type: 'reading', ts, temp: state.temp, hum: state.hum, gas: state.gas, pir: state.pir })

    const alerts = [
      [state.temp > 40, 'temperature', state.temp, '°C', 'critical'],
      [state.gas > 400, 'gas', state.gas, 'ppm', 'critical'],
      [state.pir === 1, 'presence', 1, '', 'warning'],
    ]
    for (const [on, kind, value, unit, level] of alerts) {
      if (on) emit({ type: 'alert', ts, device_id: 'sim-01', kind, value: +value.toFixed(1), unit, level })
    }
  }

  const id = setInterval(tick, intervalMs)

  return {
    subscribe(cb) {
      listeners.add(cb)
      return () => listeners.delete(cb)
    },
    sendCommand(cmd) {
      emit({ type: 'command-ack', ts: Date.now(), cmd })
    },
    inject(kind) {
      state.boost = { kind, until: t + 8 }
    },
    close() {
      clearInterval(id)
    },
  }
}
