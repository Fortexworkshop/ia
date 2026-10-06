export default function Sparkline({ values, color, min, max, label }) {
  const w = 240
  const h = 56
  const viewBox = `0 0 ${w} ${h}`
  if (values.length < 2) return <svg className="spark" viewBox={viewBox} role="img" aria-label={label} />
  const lo = min ?? Math.min(...values)
  const hi = max ?? Math.max(...values)
  const span = hi - lo || 1
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - lo) / span) * (h - 4) - 2}`)
    .join(' ')
  return (
    <svg className="spark" viewBox={viewBox} preserveAspectRatio="none" role="img" aria-label={label}>
      <polyline points={pts} fill="none" style={{ stroke: color }} strokeWidth="2" />
    </svg>
  )
}
