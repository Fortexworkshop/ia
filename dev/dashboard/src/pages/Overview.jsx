import SiteState from '../components/SiteState.jsx'
import WidgetGrid from '../dashboard/WidgetGrid.jsx'

// Vue d'ensemble : bandeau d'état fixe (sûreté : jamais masquable), puis tableau de bord personnalisable.
export default function Overview() {
  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>Vue d'ensemble</h1>
          <p className="lede">Site SENTINEL-X-01 · micro-centrale AetherCorp</p>
        </div>
      </div>
      <SiteState />
      <WidgetGrid />
    </div>
  )
}
