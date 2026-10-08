// Vocabulaire métier partagé par toutes les pages (libellés, priorités, état du site).

export const STALE_AFTER_MS = 10_000 // au-delà, les valeurs affichées ne sont plus « en direct »
const PAGE_START = Date.now() // avant la première mesure : « connexion », pas « liaison perdue »

export const SENSORS = [
  { key: 'temp', label: 'Température', unit: '°C', digits: 1, kinds: ['temperature', 'anomalie'] },
  { key: 'hum', label: 'Humidité', unit: '%', digits: 0, kinds: ['humidity'] },
  { key: 'gas', label: 'Gaz et fumées', unit: 'ppm', digits: 0, kinds: ['gas'] },
  { key: 'pir', label: 'Mouvement', unit: '', digits: 0, kinds: ['presence', 'intrusion'], binary: true },
]

export const LEVELS = {
  critical: { label: 'Critique', icon: 'critical', rank: 2 },
  warning: { label: 'Avertissement', icon: 'warning', rank: 1 },
}
export const levelOf = (alert) => LEVELS[alert.level] ?? LEVELS.warning

export const KIND_LABELS = {
  temperature: 'Température critique',
  gas: 'Gaz ou fumées',
  presence: 'Mouvement détecté',
  intrusion: 'Intrusion',
  anomalie: 'Dérive anormale (prédictif)',
  humidity: 'Humidité anormale',
}
export const kindLabel = (kind) => KIND_LABELS[kind] ?? (kind ? kind[0].toUpperCase() + kind.slice(1) : 'Alarme')

// Origine d'une alarme : distingue clairement l'IA, le garde-fou à seuil et les exercices.
export const SOURCES = {
  anomaly: 'IA · maintenance prédictive',
  vision: 'IA · vision',
  'garde-fou': 'Garde-fou (seuil critique)',
  test: 'Exercice',
  simulateur: 'Simulateur',
}
export const sourceLabel = (source) => SOURCES[source] ?? (source || 'Inconnue')
// Étiquette « exercice » : seulement quand l'origine ne le dit pas déjà (simulateur)
export const isExercise = (alert) => alert.source === 'simulateur'

export const time = (ts) => new Date(ts).toLocaleTimeString('fr-FR')
export const dateTime = (ts) =>
  new Date(ts).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })

export const ago = (ms) => {
  if (ms == null) return 'jamais'
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `il y a ${s} s`
  const m = Math.round(s / 60)
  return m < 60 ? `il y a ${m} min` : `il y a ${Math.round(m / 60)} h`
}

// Les alarmes non acquittées, de la plus grave à la plus récente.
export const activeAlarms = (alerts) =>
  alerts.filter((a) => !a.acknowledged).sort((a, b) => levelOf(b).rank - levelOf(a).rank || b.ts - a.ts)

// Défauts de la chaîne de surveillance : sans eux, « aucune alarme » ne prouve rien.
export function chainIssues(chain) {
  if (!chain) return []
  const issues = []
  if (!chain.health) issues.push('serveur de supervision injoignable')
  else {
    if (chain.health.mqtt_connected === false) issues.push('liaison MQTT avec le boîtier coupée')
    if (chain.health.database_ok === false) issues.push('base de données indisponible (historique non enregistré)')
  }
  if (chain.vision?.available && chain.vision.running === false)
    issues.push(chain.vision.crashed ? 'vision arrêtée sur une erreur : aucune détection d’intrusion' : 'surveillance vidéo arrêtée : aucune détection d’intrusion')
  return issues
}

// État global du site : répond en un coup d'œil à « tout va bien ? ».
// Il n'affirme jamais plus que ce que le système sait (pas de « tout est normal » si une brique est arrêtée).
export function siteState({ alerts, online, lastReadingAt, now, chain }) {
  const active = activeAlarms(alerts)
  const critical = active.filter((a) => a.level === 'critical').length
  const warning = active.length - critical
  const stale = !online || lastReadingAt == null || now - lastReadingAt > STALE_AFTER_MS
  const issues = chainIssues(chain)
  const base = { critical, warning, stale, issues }
  if (critical)
    return { ...base, id: 'critical', icon: 'critical', title: 'Alarme', detail: count(critical, 'alarme critique', 'alarmes critiques') + (warning ? `, ${count(warning, 'avertissement', 'avertissements')}` : '') + ' à traiter' }
  if (stale && lastReadingAt == null && now - PAGE_START < STALE_AFTER_MS)
    return { ...base, id: 'nominal', icon: 'unlink', title: 'Connexion en cours', detail: 'En attente des premières mesures du boîtier.' }
  if (stale)
    return { ...base, id: 'stale', icon: 'unlink', title: 'Liaison perdue', detail: online ? `Dernière mesure ${ago(lastReadingAt == null ? null : now - lastReadingAt)} : les valeurs ne sont plus en direct.` : 'Le serveur de supervision ne répond pas. Reconnexion automatique en cours.' }
  if (warning || issues.length)
    return { ...base, id: 'warning', icon: 'warning', title: 'Vigilance', detail: [warning && count(warning, 'avertissement', 'avertissements') + ' à examiner', ...issues].filter(Boolean).join(' · ').replace(/^./, (c) => c.toUpperCase()) }
  return {
    ...base,
    id: 'nominal',
    icon: 'shield',
    title: 'Aucune alarme',
    // n'affirme que ce qui est vérifié : l'IA prédictive ne remonte pas son état (voir la chaîne de surveillance)
    detail: chain ? 'Mesures reçues en direct. Serveur, liaison avec le boîtier et vision actifs.' : 'Mesures simulées reçues en direct (simulateur local).',
  }
}

const count = (n, one, many) => `${n} ${n > 1 ? many : one}`

// Présence : dernier pointage du jour de chaque personne (évacuation : qui est sur site ?)
export const POINTAGES = { entree: 'Entrée', pause: 'Pause', reprise: 'Reprise', sortie: 'Sortie' }
export const ON_SITE = { entree: 'Sur site', reprise: 'Sur site', pause: 'En pause', sortie: 'Parti' }
export const isToday = (ts) => new Date(ts).toDateString() === new Date().toDateString()
export function lastPointages(presence) {
  const seen = new Map()
  // presence est trié du plus récent au plus ancien : le premier vu est le dernier pointage
  for (const e of presence) if (e.kind in POINTAGES && e.person && isToday(e.ts) && !seen.has(e.person)) seen.set(e.person, e)
  return [...seen.values()]
}
