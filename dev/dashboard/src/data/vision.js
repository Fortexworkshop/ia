// Pilotage de la vision : la webcam est un périphérique exclusif, l'arrêter la libère.
// null = pas de serveur configuré : la page affiche seulement le flux.
import { base, request } from './http.js'

export const visionApi = base
  ? {
      status: () => request('/api/v1/vision'),
      start: () => request('/api/v1/vision/start', { method: 'POST' }),
      stop: () => request('/api/v1/vision/stop', { method: 'POST' }),
    }
  : null
