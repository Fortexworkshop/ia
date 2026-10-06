export default function Sparkline({ values, color, min, max }) {
  const w = 240
  const h = 56
  if (values.length < 2) return <svg className="spark" viewBox={`0 0 ${w} ${h}`} />
  const lo = min ?? Math.min(...values)
  const hi = max ?? Math.max(...values)
  const span = hi - lo || 1
  const pts = values
    .map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - lo) / span) * (h - 4) - 2}`)
    .join(' ')
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="2" />
    </svg>
  )
}
