import Icon from './Icon.jsx'
import { openLogin } from './LoginDialog.jsx'

// Indique qu'une action ou une donnée est réservée à l'opérateur, avec le moyen de se connecter.
export default function OperatorOnly({ what }) {
  return (
    <p className="operator-only">
      <Icon name="shield" />
      <span>
        Connexion opérateur requise pour {what}.{' '}
        <button type="button" className="btn small" onClick={openLogin}>
          Se connecter
        </button>
      </span>
    </p>
  )
}
