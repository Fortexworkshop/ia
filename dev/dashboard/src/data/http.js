// Client HTTP commun : toute erreur remonte à l'interface (OWASP A10), jamais seulement en console.
import { authHeaders, expire } from './auth.js'

export const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

export class HttpError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

const MESSAGES = {
  401: 'Action réservée à l’opérateur : connectez-vous avec le code opérateur.',
  403: 'Action refusée.',
  404: 'Élément introuvable sur le serveur.',
  413: 'Données trop volumineuses.',
  422: 'Données refusées par le serveur (format invalide).',
  503: 'Service indisponible sur le serveur.',
}

export async function request(path, { method = 'GET', body } = {}) {
  let response
  try {
    response = await fetch(base + path, {
      method,
      cache: 'no-store',
      headers: { ...authHeaders(), ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}) },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new HttpError(0, 'Serveur injoignable : vérifiez la liaison avec le PC serveur.')
  }
  if (response.status === 401) expire()
  if (!response.ok) {
    const detail = await response.json().then((b) => b?.detail).catch(() => null)
    // le détail du serveur n'est affiché que s'il est du texte simple (pas de structure interne)
    throw new HttpError(response.status, MESSAGES[response.status] ?? (typeof detail === 'string' ? detail : `Erreur ${response.status}`))
  }
  return response.json().catch(() => null)
}
