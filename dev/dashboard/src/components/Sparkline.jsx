import { memo } from 'react'

// Courbe de tendance. Décorative pour les technologies d'assistance : la tuile donne en texte
// la valeur, la tendance, le minimum et le maximum (RGAA 1.3 / 1.9, alternative textuelle).
const W = 240
const H = 56

function Sparkline({ values, min, max, step = false }) {
  if (values.length < 2) return <svg className="spark" viewBox={`0 0 ${W} ${H}`} aria-hidden="true" />
  const lo = min ?? Math.min(...values)
  const hi = max ?? Math.max(...values)
  const span = hi - lo || 1
  const x = (i) => (i / (values.length - 1)) * W
  const y = (v) => H - 3 - ((v - lo) / span) * (H - 6)
  let d = `M${x(0)},${y(values[0])}`
  for (let i = 1; i < values.length; i++) {
    d += step ? `H${x(i)}V${y(values[i])}` : `L${x(i)},${y(values[i])}`
  }
  return (
    <svg className="spark" viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" aria-hidden="true" focusable="false">
      <path className="line" d={d} />
      <circle className="now" cx={x(values.length - 1)} cy={y(values.at(-1))} r="3" />
    </svg>
  )
}

export default memo(Sparkline)
