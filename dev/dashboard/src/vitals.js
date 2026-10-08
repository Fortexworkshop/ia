// Mesure des Core Web Vitals sur le terrain (LCP, CLS, INP), sans dépendance externe.
// Résultat dans window.__vitals ; affiché dans la console en développement ou avec ?vitals dans l'URL.
// Seuils « bons » de Google : LCP <= 2,5 s, CLS <= 0,1, INP <= 200 ms.

const vitals = { lcp: null, cls: 0, inp: null }
window.__vitals = vitals

function observe(type, callback, options = {}) {
  try {
    if (!PerformanceObserver.supportedEntryTypes?.includes(type)) return
    new PerformanceObserver((list) => list.getEntries().forEach(callback)).observe({ type, buffered: true, ...options })
  } catch {
    /* navigateur sans cette API : on ignore */
  }
}

// LCP : dernier candidat avant la première interaction
observe('largest-contentful-paint', (entry) => {
  vitals.lcp = Math.round(entry.startTime)
})

// CLS : somme maximale des décalages par fenêtre de session (1 s d'écart, 5 s max)
let session = 0
let sessionStart = 0
let previous = 0
observe('layout-shift', (entry) => {
  if (entry.hadRecentInput) return
  if (entry.startTime - previous > 1000 || entry.startTime - sessionStart > 5000) {
    session = 0
    sessionStart = entry.startTime
  }
  previous = entry.startTime
  session += entry.value
  vitals.cls = Math.max(vitals.cls, Math.round(session * 1000) / 1000)
})

// INP (approximation) : plus longue interaction observée
observe(
  'event',
  (entry) => {
    if (!entry.interactionId) return
    vitals.inp = Math.max(vitals.inp ?? 0, Math.round(entry.duration))
  },
  { durationThreshold: 16 },
)

if (import.meta.env.DEV || new URLSearchParams(window.location.search).has('vitals')) {
  addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') console.table(vitals)
  })
  setTimeout(() => console.info('[Core Web Vitals]', JSON.stringify(vitals)), 5000)
}
