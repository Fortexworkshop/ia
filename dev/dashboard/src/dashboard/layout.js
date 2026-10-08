// Disposition personnalisable de la vue d'ensemble : liste ordonnée d'éléments (widgets).
// Mémorisée dans le navigateur du poste (localStorage) : chaque poste garde sa disposition.
// Un widget : { id, type, size: 's'|'m'|'l', title?: string, config: {} }

// v2 : chaîne de surveillance ajoutée, mode exercice retiré de la vue par défaut
const KEY = 'fortex.layout.v2'

export const SIZES = {
  s: { label: 'Petit', cols: 3 },
  m: { label: 'Moyen', cols: 6 },
  l: { label: 'Pleine largeur', cols: 12 },
}

const uid = () => (crypto.randomUUID ? crypto.randomUUID() : `w-${Date.now()}-${Math.random().toString(36).slice(2)}`)

export const make = (type, size, config = {}, title = '') => ({ id: uid(), type, size, title, config })

export const defaultLayout = () => [
  make('chain', 'm'),
  make('alarms', 'm', { limit: 6 }),
  make('sensor', 's', { sensor: 'temp' }),
  make('sensor', 's', { sensor: 'hum' }),
  make('sensor', 's', { sensor: 'gas' }),
  make('sensor', 's', { sensor: 'pir' }),
  make('actuators', 'm'),
]

// Réglages relus depuis le navigateur : n'importe qui peut les modifier, on les borne (OWASP A08)
const SENSOR_KEYS = ['temp', 'hum', 'gas', 'pir']
function sanitize(w) {
  const config = {}
  const c = w.config && typeof w.config === 'object' ? w.config : {}
  if (SENSOR_KEYS.includes(c.sensor)) config.sensor = c.sensor
  if (Number.isInteger(c.limit)) config.limit = Math.max(1, Math.min(30, c.limit))
  if (typeof c.text === 'string') config.text = c.text.slice(0, 1000)
  if (w.type === 'sensor' && !config.sensor) config.sensor = 'temp'
  return { id: w.id.slice(0, 64), type: w.type, size: w.size, title: typeof w.title === 'string' ? w.title.slice(0, 60) : '', config }
}

export function loadLayout(known) {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY))
    if (Array.isArray(saved)) {
      // On ignore tout élément d'un type inconnu ou mal formé (ancienne version, édition manuelle)
      const valid = saved.filter((w) => w && typeof w.id === 'string' && known.includes(w.type) && Object.hasOwn(SIZES, w.size))
      if (valid.length || saved.length === 0) return valid.map(sanitize)
    }
  } catch {
    /* stockage indisponible ou illisible : disposition par défaut */
  }
  return defaultLayout()
}

export function saveLayout(layout) {
  try {
    localStorage.setItem(KEY, JSON.stringify(layout))
  } catch {
    /* stockage indisponible : la disposition vaut pour cette session */
  }
}

// Opérations pures sur la disposition
export const ops = {
  add: (layout, widget, index = layout.length) => [...layout.slice(0, index), widget, ...layout.slice(index)],
  remove: (layout, id) => layout.filter((w) => w.id !== id),
  update: (layout, id, patch) => layout.map((w) => (w.id === id ? { ...w, ...patch, config: { ...w.config, ...patch.config } } : w)),
  move: (layout, id, to) => {
    const from = layout.findIndex((w) => w.id === id)
    if (from < 0) return layout
    const target = Math.max(0, Math.min(layout.length - 1, to))
    if (target === from) return layout
    const next = layout.slice()
    const [w] = next.splice(from, 1)
    next.splice(target, 0, w)
    return next
  },
}
