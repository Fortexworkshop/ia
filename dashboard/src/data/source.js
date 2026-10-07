import { createSimulator } from './simulator.js'
import { createApiSource } from './api.js'

// VITE_API_URL défini = backend FORTEX réel (REST + WebSocket), sinon simulateur local.
export function createSource() {
  const url = import.meta.env.VITE_API_URL
  return url ? createApiSource(url) : createSimulator()
}
