// Page d'accès à la partie caméra. Le flux vient du script de vision exécuté sur le PC serveur ;
// son URL (ex. flux MJPEG) est fournie via VITE_CAMERA_URL.
// La webcam est un périphérique exclusif : le bouton arrête la vision (donc libère la caméra)
// ou la relance sans avoir à couper le backend.
import { useCallback, useEffect, useState } from 'react'
import { visionApi } from '../data/vision.js'

const CAMERA_URL = import.meta.env.VITE_CAMERA_URL
const POLL_MS = 3000

export default function Camera() {
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

  const running = status?.running

  return (
    <section>
      <h2>Caméra</h2>

      {visionApi && (
        <div className="row">
          <button type="button" className={running ? '' : 'on'} onClick={toggle} disabled={busy}>
            {running ? 'Arrêter la vision (libère la caméra)' : 'Démarrer la vision'}
          </button>
          <p role="status" className={running ? 'badge ok' : 'badge'}>
            {busy ? 'En cours…' : running ? `Vision active (port ${status.port})` : 'Vision arrêtée : caméra libre'}
          </p>
        </div>
      )}

      {error && <p className="badge critical" role="status">{error}</p>}

      {CAMERA_URL && running !== false ? (
        <img className="feed" src={CAMERA_URL} alt="Flux de la webcam" />
      ) : (
        <div className="feed empty">
          {CAMERA_URL
            ? 'Flux arrêté. Démarrer la vision pour reprendre la caméra.'
            : 'Aucun flux configuré. Renseigner VITE_CAMERA_URL (voir .env.example).'}
        </div>
      )}
    </section>
  )
}
