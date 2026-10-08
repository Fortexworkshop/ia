// Vocabulaire métier partagé par toutes les pages (libellés, priorités, état du site).

export const STALE_AFTER_MS = 10_000 // au-delà, les valeurs affichées ne sont plus « en direct »

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

// État global du site : répond en un coup d'œil à « tout va bien ? ».
export function siteState({ alerts, online, lastReadingAt, now }) {
  const active = activeAlarms(alerts)
  const critical = active.filter((a) => a.level === 'critical').length
  const warning = active.length - critical
  const stale = !online || lastReadingAt == null || now - lastReadingAt > STALE_AFTER_MS
  if (critical)
    return { id: 'critical', icon: 'critical', title: 'Alarme', detail: count(critical, 'alarme critique', 'alarmes critiques') + (warning ? `, ${count(warning, 'avertissement', 'avertissements')}` : '') + ' à traiter', critical, warning, stale }
  if (stale)
    return { id: 'stale', icon: 'unlink', title: 'Liaison perdue', detail: online ? `Dernière mesure ${ago(lastReadingAt == null ? null : now - lastReadingAt)} : les valeurs ne sont plus en direct.` : 'Le serveur de supervision ne répond pas. Reconnexion automatique en cours.', critical, warning, stale }
  if (warning)
    return { id: 'warning', icon: 'warning', title: 'Vigilance', detail: count(warning, 'avertissement', 'avertissements') + ' à examiner', critical, warning, stale }
  return { id: 'nominal', icon: 'shield', title: 'Fonctionnement nominal', detail: 'Toutes les mesures sont dans leur profil habituel. Aucune alarme en cours.', critical, warning, stale }
}

const count = (n, one, many) => `${n} ${n > 1 ? many : one}`
