// Caméra : flux annoté par l'IA de vision (MJPEG servi par sentinel_vision.py sur le PC serveur).
// La webcam est un périphérique exclusif : arrêter la vision la libère pour un autre usage.
import { useCallback, useEffect, useState } from 'react'
import Icon from '../components/Icon.jsx'
import { visionApi } from '../data/vision.js'

const CAMERA_URL = import.meta.env.VITE_CAMERA_URL
const POLL_MS = 3000

export default function Camera() {
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [broken, setBroken] = useState(false)

  const refresh = useCallback(async () => {
    if (!visionApi) return
    try {
      setStatus(await visionApi.status())
      setError('')
    } catch (err) {
      setError(err.message)
    }
  }, [])

  useEffect(() => {
    refresh()
    const timer = setInterval(refresh, POLL_MS)
    return () => clearInterval(timer)
  }, [refresh])

  const toggle = async () => {
    setBusy(true)
    setError('')
    try {
      setStatus(await (status?.running ? visionApi.stop() : visionApi.start()))
      setBroken(false)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const running = visionApi ? status?.running : true
  const showFeed = CAMERA_URL && running && !broken

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Caméra</h1>
          <p className="lede">
            Détection de personnes en temps réel. Cadre vert : personne autorisée. Cadre rouge : intrus (alarme après 20 s
            sans reconnaissance).
          </p>
        </div>
        {visionApi && (
          <div className="btn-row">
            <span className={`tag ${running ? 'ok' : ''}`} role="status">
              {busy ? 'Changement en cours…' : running ? 'Vision active' : 'Vision arrêtée, caméra libre'}
            </span>
            <button type="button" className={`btn ${running ? '' : 'primary'}`} onClick={toggle} disabled={busy || status == null}>
              {running ? 'Arrêter la vision' : 'Démarrer la vision'}
            </button>
          </div>
        )}
      </div>

      {error && (
        <p className="notice error" role="status">
          <Icon name="critical" /> <span>{error}</span>
        </p>
      )}

      {/* Cadre de taille fixe (4:3) : le flux n'entraîne aucun décalage de mise en page (CLS) */}
      <div className="feed">
        {showFeed ? (
          <>
            <img
              src={CAMERA_URL}
              width="640"
              height="480"
              alt="Flux vidéo de la caméra de surveillance, annoté par l'IA de vision"
              onError={() => setBroken(true)}
            />
            <span className="overlay">
              <span className="rec">En direct</span>
            </span>
          </>
        ) : (
          <p className="placeholder">
            {!CAMERA_URL
              ? 'Aucun flux configuré : renseigner VITE_CAMERA_URL (voir .env.example).'
              : broken
                ? 'Flux injoignable. Vérifier que la vision tourne sur le PC serveur.'
                : 'Vision arrêtée. Démarrer la vision pour reprendre la caméra.'}
          </p>
        )}
      </div>

      <p className="muted small">
        Les images sont traitées sur le PC serveur du site et ne sont pas enregistrées. Seuls les événements (détection,
        pointage, alarme) sont conservés dans le journal.
      </p>
    </div>
  )
}
