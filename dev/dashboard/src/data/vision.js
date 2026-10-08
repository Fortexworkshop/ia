import { authHeaders } from './auth.js'
// Pilotage de la vision : la webcam est un peripherique exclusif, l'arreter la libere.
// null = pas de backend configure : la page affiche seulement le flux.
const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

async function request(path, method = 'GET') {
  const response = await fetch(base + path, { method, cache: 'no-store', headers: authHeaders })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Erreur ${response.status}`)
  }
  return response.json()
}

export const visionApi = base
  ? {
      status: () => request('/api/v1/vision'),
      start: () => request('/api/v1/vision/start', 'POST'),
      stop: () => request('/api/v1/vision/stop', 'POST'),
    }
  : null
