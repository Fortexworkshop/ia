// Caméra : flux annoté par l'IA de vision (MJPEG servi par sentinel_vision.py sur le PC serveur).
// La webcam est un périphérique exclusif : arrêter la vision la libère pour un autre usage.
import { useCallback, useEffect, useState } from 'react'
import CameraFeed from '../components/CameraFeed.jsx'
import Icon from '../components/Icon.jsx'
import OperatorOnly from '../components/OperatorOnly.jsx'
import { visionApi } from '../data/vision.js'
import { useLive } from '../state/live.jsx'

const POLL_MS = 3000

export default function Camera() {
  const { operator } = useLive()
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

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
    // Arrêter la vision supprime la détection d'intrusion : confirmation explicite (OWASP A06)
    if (status?.running && !window.confirm('Arrêter la vision ? La détection d’intrusion sera désactivée tant qu’elle n’est pas redémarrée.')) return
    setBusy(true)
    setError('')
    try {
      setStatus(await (status?.running ? visionApi.stop() : visionApi.start()))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const running = visionApi ? status?.running : true

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
            <span className={`tag ${running ? 'ok' : status?.crashed ? 'warning' : ''}`} role="status">
              {busy ? 'Changement en cours…' : running ? 'Vision active' : status?.crashed ? 'Vision arrêtée sur une erreur' : 'Vision arrêtée, caméra libre'}
            </span>
            <button type="button" className={`btn ${running ? '' : 'primary'}`} onClick={toggle} disabled={!operator || busy || status == null}>
              {running ? 'Arrêter la vision' : 'Démarrer la vision'}
            </button>
          </div>
        )}
      </div>

      {visionApi && !operator && <OperatorOnly what="démarrer ou arrêter la vision" />}

      {error && (
        <p className="notice error" role="status">
          <Icon name="critical" /> <span>{error}</span>
        </p>
      )}

      {/* Cadre de taille fixe (4:3) : le flux n'entraîne aucun décalage de mise en page (CLS) */}
      <CameraFeed vision={visionApi ? (status ?? { running: false, pending: true }) : null} />

      <p className="muted small">
        Les images sont traitées sur le PC serveur du site et ne sont pas enregistrées. Seuls les événements (détection,
        pointage, alarme) sont conservés dans le journal.
      </p>
    </div>
  )
}
