/** Kleiner Ein/Aus-Schalter (barrierefrei: role="switch", aria-checked). */
export function Switch({ checked, onChange, label, disabled }: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
  disabled?: boolean
}) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled}
      onClick={() => onChange(!checked)} data-voip-switch={checked ? "on" : "off"}
      className={`relative h-6 w-11 shrink-0 rounded-full transition-colors disabled:opacity-50 ${
        checked ? "bg-[#163248]" : "bg-[rgb(var(--hh-s-hebung,27_37_54))]"}`}>
      <span className={`absolute top-0.5 h-5 w-5 rounded-full bg-white transition-transform ${
        checked ? "translate-x-5" : "translate-x-0.5"}`} />
    </button>
  )
}
