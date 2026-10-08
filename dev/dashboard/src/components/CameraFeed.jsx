// Flux vidéo de la vision (MJPEG). Distingue les situations au lieu d'un « injoignable » unique :
// pas de flux configuré, vision arrêtée, vision plantée, flux qui démarre, flux réellement injoignable.
import { useEffect, useRef, useState } from 'react'

const CAMERA_URL = import.meta.env.VITE_CAMERA_URL
const RETRY_MS = 3000 // YOLO met plusieurs secondes à charger : le flux n'est pas prêt tout de suite
const GIVE_UP_MS = 20000 // au-delà, ce n'est plus un démarrage : on le dit (en continuant d'essayer)
const STATUS_MS = 3000
const FROZEN_MS = 8000 // horodatage /status inchangé depuis 8 s : l'image affichée est figée
// Le navigateur ne signale ni les images d'un flux MJPEG ni sa coupure : on suit /status de la
// vision, dont l'horodatage change à chaque image traitée. On compare deux réponses successives
// (et non l'heure du poste) : insensible à un décalage d'horloge entre poste et serveur.
const STATUS_URL = (() => {
  try {
    return CAMERA_URL ? new URL('/status', CAMERA_URL).href : null
  } catch {
    return null
  }
})()

const withAttempt = (url, n) => `${url}${url.includes('?') ? '&' : '?'}essai=${n}`

/**
 * vision : état renvoyé par GET /api/v1/vision ({ running, crashed, exit_code }), ou null s'il est
 * inconnu (pas de serveur : on tente simplement d'afficher le flux).
 */
export default function CameraFeed({ vision }) {
  const running = vision ? vision.running : true
  const [attempt, setAttempt] = useState(0)
  const [failingSince, setFailingSince] = useState(null)
  const [now, setNow] = useState(() => Date.now())
  const timer = useRef(null)

  // Nouveau démarrage de la vision : on repart de zéro
  useEffect(() => {
    setFailingSince(null)
    setAttempt((n) => n + 1)
  }, [running])

  useEffect(() => () => clearTimeout(timer.current), [])

  // Fraîcheur du flux : dernière fois que l'horodatage de /status a changé
  const [frozenSince, setFrozenSince] = useState(null)
  useEffect(() => {
    if (!STATUS_URL || !running) return undefined
    let last = null
    let changedAt = Date.now()
    let alive = true
    const poll = async () => {
      let stamp = null
      try {
        const response = await fetch(STATUS_URL, { cache: 'no-store' })
        stamp = response.ok ? (await response.json())?.timestamp ?? null : null
      } catch {
        stamp = null
      }
      if (!alive) return
      const t = Date.now()
      if (stamp != null && stamp !== last) {
        last = stamp
        changedAt = t
      }
      setNow(t)
      setFrozenSince(t - changedAt > FROZEN_MS ? changedAt : null)
    }
    const id = setInterval(poll, STATUS_MS)
    poll()
    return () => {
      alive = false
      clearInterval(id)
    }
  }, [running])

  // Flux figé puis reparti : on recharge l'image (la connexion MJPEG coupée ne reprend pas seule)
  const wasFrozen = useRef(false)
  useEffect(() => {
    if (wasFrozen.current && frozenSince == null) setAttempt((n) => n + 1)
    wasFrozen.current = frozenSince != null
  }, [frozenSince])

  const onError = () => {
    setFailingSince((t) => t ?? Date.now())
    setNow(Date.now())
    clearTimeout(timer.current)
    timer.current = setTimeout(() => setAttempt((n) => n + 1), RETRY_MS)
  }
  const onLoad = () => setFailingSince(null)

  let message = null
  if (!CAMERA_URL) message = 'Aucun flux configuré : renseigner VITE_CAMERA_URL (voir .env.example).'
  else if (vision?.pending) message = 'Interrogation de la vision…'
  else if (!running)
    message = vision?.crashed
      ? `La vision s'est arrêtée d'elle-même (code ${vision.exit_code}). Détail dans data/vision.log sur le PC serveur.`
      : 'Vision arrêtée. Démarrer la vision pour reprendre la caméra.'
  else if (frozenSince != null && failingSince == null)
    message = `Image figée : aucune nouvelle image depuis ${Math.round((now - frozenSince) / 1000)} s. La vision ou la liaison est interrompue.`
  else if (failingSince != null)
    message =
      now - failingSince < GIVE_UP_MS
        ? 'Démarrage du flux vidéo…'
        : 'Flux injoignable alors que la vision tourne : vérifier le port du flux et le pare-feu du PC serveur. Nouvelle tentative toutes les 3 s.'

  return (
    <div className="feed">
      {CAMERA_URL && running && (
        <img
          key={attempt}
          src={withAttempt(CAMERA_URL, attempt)}
          width="640"
          height="480"
          alt="Flux vidéo de la caméra de surveillance, annoté par l'IA de vision"
          onError={onError}
          onLoad={onLoad}
          style={{ visibility: failingSince == null && frozenSince == null ? 'visible' : 'hidden' }}
        />
      )}
      {message && (
        <p className="placeholder" role="status">
          {message}
        </p>
      )}
      {!message && (
        <span className="overlay" aria-hidden="true">
          <span className="rec">En direct</span>
        </span>
      )}
    </div>
  )
}
