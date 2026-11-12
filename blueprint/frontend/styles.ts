// Gemeinsame Klassen der Blueprint-Bausteine. Flächen und Ränder nur über die Farbstufen des Kerns
// (mit Rückfallwert für ältere Kerne), Akzent #69d7ff wie im übrigen Cockpit.
export const RAND = "border-[rgb(var(--hh-s-rand,42_54_75))]"

export const FIELD =
  `w-full rounded-lg border ${RAND} bg-[rgb(var(--hh-s-box,21_28_43))] px-2.5 py-1.5 text-sm text-[#e8eef8] ` +
  "placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]"

export const SELECT = `${FIELD} cursor-pointer py-1 text-xs`

const BUTTON_BASE =
  "inline-flex shrink-0 items-center justify-center gap-1.5 rounded-md border px-2.5 py-1 text-xs font-semibold " +
  "transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/40 " +
  "disabled:cursor-not-allowed disabled:opacity-50"

export const BUTTON =
  `${BUTTON_BASE} ${RAND} text-[#c8d2df] hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))] ` +
  "hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"

export const BUTTON_ON = `${BUTTON_BASE} border-[#69d7ff]/50 bg-[#69d7ff]/10 text-[#c8f2ff] hover:bg-[#69d7ff]/20`

export const BUTTON_PRIMARY =
  `${BUTTON_BASE} border-[#69d7ff]/50 bg-[#69d7ff]/15 text-[#c8f2ff] hover:border-[#69d7ff] hover:bg-[#69d7ff]/25`

export const ERROR_BOX = "rounded-md border border-rose-400/40 bg-rose-400/10 px-2.5 py-1.5 text-xs text-rose-100"

export const SIDE_PANEL = `w-64 shrink-0 border-l ${RAND} bg-[rgb(var(--hh-s-tief,13_20_32)/0.4)]`
