// Liste blanche des individus : API du backend FORTEX quand VITE_API_URL est défini,
// sinon jeu de données simulé (mode hors-ligne, lecture seule).
// Contrat d'un individu : { name, role, notes, face, created_at, updated_at }
// `face` = une empreinte faciale existe dans data/faces.npz (partagé avec la vision).

import { authHeaders } from './auth.js'

const base = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')

// Données simulées en attendant le backend. Noms et présence = données personnelles (RGPD).
export const simulatedPeople = [
  { name: 'Alice Martin', role: 'Superviseure', notes: '', face: false, created_at: '', updated_at: '' },
  { name: 'Karim Benali', role: 'Technicien', notes: '', face: false, created_at: '', updated_at: '' },
]

async function request(path, options) {
  // no-store : la liste doit refléter immédiatement un ajout ou une suppression.
  const response = await fetch(base + path, {
    cache: 'no-store',
    ...options,
    headers: { ...authHeaders, ...options?.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.detail || `Erreur ${response.status}`)
  }
  return response.json()
}

// null = pas de backend configuré : la page passe en lecture seule (données simulées).
export const peopleApi = base
  ? {
      list: () => request('/api/v1/people'),
      save: (person) =>
        request('/api/v1/people', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(person),
        }),
      remove: (name) => request(`/api/v1/people/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    }
  : null
