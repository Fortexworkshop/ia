// Connexion opérateur. WCAG 2.2 — 3.3.8 Authentification accessible : aucun test cognitif,
// collage autorisé, compatible gestionnaire de mots de passe (autocomplete), code affichable.
import { useEffect, useRef, useState } from 'react'
import Icon from './Icon.jsx'
import { useLive } from '../state/live.jsx'

const EVENT = 'fortex:login'
export const openLogin = () => window.dispatchEvent(new Event(EVENT))

export default function LoginDialog() {
  const { actions } = useLive()
  const dialog = useRef(null)
  const input = useRef(null)
  const opener = useRef(null)
  const [code, setCode] = useState('')
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const open = () => {
      opener.current = document.activeElement
      setError('')
      setCode('')
      dialog.current?.showModal()
      input.current?.focus()
    }
    window.addEventListener(EVENT, open)
    return () => window.removeEventListener(EVENT, open)
  }, [])

  const close = () => {
    dialog.current?.close()
  }

  const submit = async (e) => {
    e.preventDefault()
    if (!code.trim()) {
      setError('Saisissez le code opérateur.')
      input.current?.focus()
      return
    }
    setBusy(true)
    try {
      await actions.login(code.trim())
      close()
    } catch (err) {
      setError(err.message)
      input.current?.focus()
    } finally {
      setBusy(false)
    }
  }

  return (
    <dialog
      ref={dialog}
      className="catalog login"
      aria-labelledby="login-title"
      onClose={() => {
        setCode('') // le code ne reste pas en mémoire dans le formulaire
        opener.current?.focus?.()
      }}
    >
      <form onSubmit={submit} noValidate>
        <div className="catalog-head">
          <h2 id="login-title">Connexion opérateur</h2>
          <button type="button" className="btn small quiet" onClick={close}>
            Fermer
          </button>
        </div>
        <div className="login-body">
          <p className="muted small">
            Le code opérateur autorise les actions (acquitter, commander, gérer les personnes) et l'accès aux données
            personnelles. Il est conservé jusqu'à la fermeture de cet onglet.
          </p>
          {/* identifiant implicite : permet aux gestionnaires de mots de passe de retrouver le code */}
          <input type="text" name="username" autoComplete="username" value="operateur" readOnly hidden />
          <div className="field">
            <label htmlFor="login-code">Code opérateur</label>
            <div className="input-row">
              <input
                id="login-code"
                ref={input}
                name="password"
                type={show ? 'text' : 'password'}
                autoComplete="current-password"
                spellCheck="false"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                aria-invalid={error ? 'true' : undefined}
                aria-describedby={error ? 'login-error login-help' : 'login-help'}
              />
              <button type="button" className="btn" aria-pressed={show} onClick={() => setShow(!show)}>
                {show ? 'Masquer' : 'Afficher'}
              </button>
            </div>
            <p id="login-help" className="help">
              Fourni par l'administrateur du site (valeur DASHBOARD_TOKEN du serveur). Le collage est autorisé.
            </p>
            {error && (
              <p id="login-error" className="error" role="alert">
                <Icon name="critical" width="16" height="16" style={{ display: 'inline', verticalAlign: '-3px' }} /> {error}
              </p>
            )}
          </div>
          <div className="btn-row">
            <button type="submit" className="btn primary" disabled={busy}>
              {busy ? 'Vérification…' : 'Se connecter'}
            </button>
          </div>
        </div>
      </form>
    </dialog>
  )
}
