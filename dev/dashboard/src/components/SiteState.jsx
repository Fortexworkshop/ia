import Icon from './Icon.jsx'
import { siteState } from '../state/model.js'
import { useLive, useNow } from '../state/live.jsx'

// Bandeau d'état du site : la première chose lue, en une seconde (« tout va bien ? »).
// Il contient aussi l'action la plus urgente : couper l'alarme sonore, acquitter.
export default function SiteState() {
  const live = useLive()
  const now = useNow()
  const state = siteState({ ...live, now })
  const sounding = live.outputs.buzzer || live.outputs.led

  return (
    <section className={`site-state ${state.id}`} aria-labelledby="site-state-title">
      <Icon name={state.icon} />
      <div>
        <h2 id="site-state-title" className="state-title">
          {state.title}
        </h2>
        <p className="state-detail">{state.detail}</p>
        {/* Seul le changement d'état est annoncé (pas le détail qui varie chaque seconde) */}
        <p className="sr-only" role="status">
          État du site : {state.title}
        </p>
      </div>
      <div className="actions">
        {sounding && (
          <button
            type="button"
            className="btn danger"
            onClick={() => {
              live.actions.command('buzzer', false)
              live.actions.command('led', false)
            }}
          >
            <Icon name="mute" /> Couper buzzer et voyant
          </button>
        )}
        {(state.critical > 0 || state.warning > 0) && (
          <a className="btn" href="#/alarmes">
            Voir les alarmes
          </a>
        )}
      </div>
    </section>
  )
}
