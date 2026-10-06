// Individus détectés : données simulées en attendant le backend.
// `photoUrl` null = avatar à initiales. Contrat visé : { id, name, photoUrl, lastSeen }.
// Ce sont des données personnelles (image + nom) : durée de conservation et accès à cadrer (RGPD).
export const PEOPLE = [
  { id: 'p1', name: 'Alice Martin', photoUrl: null, lastSeen: Date.now() - 4 * 60e3 },
  { id: 'p2', name: 'Karim Benali', photoUrl: null, lastSeen: Date.now() - 32 * 60e3 },
  { id: 'p3', name: 'Inconnu 01', photoUrl: null, lastSeen: Date.now() - 2 * 60e3 },
]
