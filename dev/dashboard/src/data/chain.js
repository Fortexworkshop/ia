// État de la chaîne de surveillance : sans elle, « aucune alarme » ne veut rien dire
// (une IA arrêtée ne lève aucune alarme). Interrogé toutes les 5 s par LiveProvider.
import { base, request } from './http.js'

export async function fetchChain() {
  const [health, vision, devices] = await Promise.allSettled([
    request('/health'),
    request('/api/v1/vision'),
    request('/api/v1/devices'),
  ])
  const value = (p) => (p.status === 'fulfilled' ? p.value : null)
  return { at: Date.now(), health: value(health), vision: value(vision), devices: Array.isArray(value(devices)) ? value(devices) : [] }
}

export const chainAvailable = Boolean(base)
