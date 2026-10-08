// Session opérateur (OWASP A01 / A07).
// Le code opérateur n'est jamais compilé dans le JavaScript (une variable VITE_* est lisible par
// quiconque ouvre la page) : l'opérateur le saisit, il est gardé pour la durée de l'onglet
// (sessionStorage, effacé à la fermeture) et envoyé en en-tête Authorization.
const KEY = 'fortex.operator'
const listeners = new Set()

export function getToken() {
  try {
    return sessionStorage.getItem(KEY) || ''
  } catch {
    return ''
  }
}

function setToken(token) {
  try {
    if (token) sessionStorage.setItem(KEY, token)
    else sessionStorage.removeItem(KEY)
  } catch {
    /* stockage indisponible : la session ne survit pas au rechargement */
  }
  listeners.forEach((cb) => cb(Boolean(token)))
}

export const authHeaders = () => {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export const onAuthChange = (cb) => {
  listeners.add(cb)
  return () => listeners.delete(cb)
}

// Vérifie le code sur une route réservée à l'opérateur avant de l'enregistrer.
export async function login(base, code) {
  const response = await fetch(`${base}/api/v1/people`, { headers: { Authorization: `Bearer ${code}` }, cache: 'no-store' })
  if (response.status === 401) throw new Error('Code opérateur incorrect.')
  if (!response.ok) throw new Error(`Serveur indisponible (erreur ${response.status}).`)
  setToken(code)
}

export const logout = () => setToken('')

// Une session expire si le serveur refuse le code (code changé côté serveur, par exemple)
export const expire = () => getToken() && setToken('')
