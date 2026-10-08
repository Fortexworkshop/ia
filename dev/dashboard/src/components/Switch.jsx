// Interrupteur d'actionneur : role="switch" + état écrit (« Activé » / « Coupé »).
export default function Switch({ label, checked, onChange, disabled = false, detailOn = 'Activé', detailOff = 'Coupé' }) {
  return (
    <button type="button" role="switch" aria-checked={checked} className="switch" disabled={disabled} onClick={() => onChange(!checked)}>
      <span className="label">
        <b>{label}</b>
        <span>{checked ? detailOn : detailOff}</span>
      </span>
      <span className="track" aria-hidden="true" />
    </button>
  )
}
