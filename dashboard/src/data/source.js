import { createSimulator } from './simulator.js'

// Choix de la source. Tant que le backend n'est pas décidé, le simulateur est utilisé.
// Quand VITE_API_URL sera défini, brancher ici un client WebSocket/REST qui respecte le même contrat.
export function createSource() {
  if (import.meta.env.VITE_API_URL) {
    console.warn('VITE_API_URL défini mais aucun client backend implémenté : simulateur utilisé.')
  }
  return createSimulator()
}
