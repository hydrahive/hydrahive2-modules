import type { Light as L } from "./caseFormat"

const COLORS: Record<L, string> = { red: "bg-rose-500", yellow: "bg-amber-400", green: "bg-emerald-500", none: "bg-[#3a465b]" }
const TITLES: Record<L, string> = {
  red: "Frist vorbei oder in höchstens 3 Tagen",
  yellow: "Frist in höchstens 14 Tagen",
  green: "Frist später",
  none: "keine offene Frist",
}

/** Ampel-Punkt für Fristen. */
export function Light({ value }: { value: L }) {
  return <span title={TITLES[value]} aria-label={TITLES[value]} className={`inline-block h-2.5 w-2.5 shrink-0 rounded-full ${COLORS[value]}`} />
}
