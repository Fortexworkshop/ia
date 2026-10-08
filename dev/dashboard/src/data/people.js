// Liste blanche des individus : API du serveur FORTEX quand VITE_API_URL est défini,
// sinon jeu de données d'exemple (mode hors-ligne, lecture seule).
// Contrat d'un individu : { name, notes, face, created_at, updated_at }
// `face` = une empreinte faciale existe dans data/faces.npz (partagé avec la vision).
// Données personnelles : lecture et écriture réservées à l'opérateur (OWASP A01).
import { base, request } from './http.js'

export const simulatedPeople = [
  { name: 'Alice Martin', notes: '', face: false, created_at: '', updated_at: '' },
  { name: 'Karim Benali', notes: '', face: false, created_at: '', updated_at: '' },
]

// null = pas de serveur configuré : la page passe en lecture seule (données d'exemple).
export const peopleApi = base
  ? {
      list: () => request('/api/v1/people'),
      save: (person) => request('/api/v1/people', { method: 'POST', body: person }),
      remove: (name) => request(`/api/v1/people/${encodeURIComponent(name)}`, { method: 'DELETE' }),
    }
  : null
