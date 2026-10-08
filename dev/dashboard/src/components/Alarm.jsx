import { memo } from 'react'
import Icon from './Icon.jsx'
import { isExercise, kindLabel, levelOf, sourceLabel, time } from '../state/model.js'

// Une alarme : niveau écrit en toutes lettres + icône + couleur (jamais la couleur seule, RGAA 3.1).
function Alarm({ alert, onAck }) {
  const level = levelOf(alert)
  const title = kindLabel(alert.kind)
  return (
    <li className={`alarm ${alert.acknowledged ? 'acked' : alert.level}`}>
      <Icon name={level.icon} />
      <p className="title">
        <span className="level">{level.label}</span> · {title}
        {alert.unit && alert.value !== '' && alert.value != null && (
          <span className="muted">
            {' '}
            ({alert.value}
            {alert.unit})
          </span>
        )}
      </p>
      <p className="meta">
        <time dateTime={new Date(alert.ts).toISOString()}>{time(alert.ts)}</time> · {sourceLabel(alert.source)}
        {isExercise(alert) && <> <span className="tag exercise">exercice</span></>}
        {alert.message && <> · {alert.message}</>}
      </p>
      <div className="act">
        {alert.acknowledged ? (
          <span className="tag">
            <Icon name="check" width="14" height="14" /> Acquittée
          </span>
        ) : onAck ? (
          <button type="button" className="btn small" onClick={() => onAck(alert)}>
            Acquitter<span className="sr-only"> : {title}, {time(alert.ts)}</span>
          </button>
        ) : (
          <span className="tag">À traiter</span>
        )}
      </div>
    </li>
  )
}

export default memo(Alarm)
