import { memo } from 'react'
import Icon from './Icon.jsx'
import Sparkline from './Sparkline.jsx'
import { kindLabel } from '../state/model.js'

const fmt = (v, digits) => v.toLocaleString('fr-FR', { minimumFractionDigits: digits, maximumFractionDigits: digits })

// Tendance : moyenne des 5 dernières mesures contre les 5 précédentes, comparée au bruit du capteur
// (écart-type de la fenêtre). Exprimée en mots : la flèche seule ne suffit pas (RGAA 3.1).
const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length
function trend(values, digits) {
  if (values.length < 10) return null
  const delta = mean(values.slice(-5)) - mean(values.slice(-10, -5))
  const m = mean(values)
  const sd = Math.sqrt(mean(values.map((v) => (v - m) ** 2)))
  if (Math.abs(delta) <= Math.max(10 ** -digits, sd)) return { word: 'stable', arrow: '→' }
  return delta > 0 ? { word: 'en hausse', arrow: '↗' } : { word: 'en baisse', arrow: '↘' }
}

function SensorTile({ sensor, values, alarm, stale, minutes }) {
  const last = values.at(-1)
  const has = last != null
  const level = alarm ? alarm.level : null
  const cls = ['tile', level, stale ? 'stale' : ''].filter(Boolean).join(' ')
  const t = sensor.binary ? null : trend(values, sensor.digits)
  const lo = has && !sensor.binary ? Math.min(...values) : null
  const hi = has && !sensor.binary ? Math.max(...values) : null
  const headingId = `tile-${sensor.key}`

  const valueText = !has ? '–' : sensor.binary ? (last ? 'Détecté' : 'Aucun') : fmt(last, sensor.digits)

  return (
    <article className={cls} aria-labelledby={headingId}>
      <h2 id={headingId}>{sensor.label}</h2>
      <p className="reading">
        <span className={sensor.binary ? 'value text' : 'value'}>{valueText}</span>
        {has && sensor.unit && <span className="unit">{sensor.unit}</span>}
      </p>
      <p className="state">
        {alarm ? (
          <>
            <Icon name={level === 'critical' ? 'critical' : 'warning'} />
            {level === 'critical' ? 'Alarme' : 'Avertissement'} : {kindLabel(alarm.kind)}
          </>
        ) : stale ? (
          'Valeur non actualisée'
        ) : has ? (
          'Dans le profil habituel'
        ) : (
          'En attente de mesure'
        )}
      </p>
      <Sparkline values={values} min={sensor.binary ? 0 : undefined} max={sensor.binary ? 1 : undefined} step={sensor.binary} />
      <p className="facts">
        {sensor.binary ? (
          <span>{values.filter(Boolean).length ? `${values.filter(Boolean).length} détection(s)` : 'Aucune détection'} sur {minutes} min</span>
        ) : has ? (
          <>
            <span>
              {t ? (
                <>
                  <span aria-hidden="true">{t.arrow} </span>
                  {t.word[0].toUpperCase() + t.word.slice(1)}
                </>
              ) : (
                'Tendance en calcul'
              )}
            </span>
            <span>
              {minutes} min : {fmt(lo, sensor.digits)} à {fmt(hi, sensor.digits)}
              {sensor.unit && ` ${sensor.unit}`}
            </span>
          </>
        ) : null}
      </p>
    </article>
  )
}

export default memo(SensorTile)
