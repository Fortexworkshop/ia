// Échec d'une action (commande, acquittement…) : toujours montré à l'opérateur (OWASP A10).
import Icon from './Icon.jsx'
import { useLive } from '../state/live.jsx'

export default function Feedback() {
  const { error, actions } = useLive()
  return (
    <div className="feedback" role="alert">
      {error && (
        <p className="notice error">
          <Icon name="critical" />
          <span>{error.text}</span>
          <button type="button" className="btn small" onClick={actions.dismissError}>
            Fermer<span className="sr-only"> le message d'erreur</span>
          </button>
        </p>
      )}
    </div>
  )
}
