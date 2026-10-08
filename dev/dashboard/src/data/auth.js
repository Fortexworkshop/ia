// Jeton operateur (VITE_DASHBOARD_TOKEN) : actions du superviseur. Ce n'est PAS le jeton de l'IA.
const token = import.meta.env.VITE_DASHBOARD_TOKEN
export const authHeaders = token ? { Authorization: `Bearer ${token}` } : {}
