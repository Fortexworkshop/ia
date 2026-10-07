// Page d'accès à la partie caméra. Le flux vient du script de vision exécuté sur le PC serveur ;
// son URL (ex. flux MJPEG) est fournie via VITE_CAMERA_URL.
const CAMERA_URL = import.meta.env.VITE_CAMERA_URL

export default function Camera() {
  return (
    <section>
      <h2>Caméra</h2>
      {CAMERA_URL ? (
        <img className="feed" src={CAMERA_URL} alt="Flux de la webcam" />
      ) : (
        <div className="feed empty">
          Aucun flux configuré. Renseigner VITE_CAMERA_URL (voir .env.example).
        </div>
      )}
    </section>
  )
}
