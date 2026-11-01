/** Gemeinsame Klassen (Farben nur über Cockpit-Farbstufen des Kerns). */
export const BTN = "rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1.5 text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] disabled:opacity-40"
export const BTN_MAIN = "rounded bg-emerald-600 px-3 py-1.5 text-sm text-white hover:bg-emerald-500 disabled:opacity-40"
export const INPUT = "w-full rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-sm text-[#e8eef8]"
export const BOX = "rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-4 space-y-3"
export const MUTED = "text-sm text-[#c8d2df]"
export const H2 = "text-base font-semibold text-[#e8eef8]"
export const LIGHT: Record<string, string> = {
  ok: "bg-emerald-400", warn: "bg-amber-400", bad: "bg-rose-500", unknown: "bg-[rgb(var(--hh-s-rand,42_54_75))]",
}
export const PATH_TEXT: Record<string, string> = {
  cable: "text-emerald-300", mobile: "text-amber-300", none: "text-rose-300", unknown: "text-[#c8d2df]",
}
/** Diagrammfarben (recharts braucht feste Werte). */
export const CHART = { rtt: "#38bdf8", loss: "#fb7185", grid: "rgb(42 54 75)", axis: "#c8d2df" }
/** Ab wie vielen ms eine Antwort als „hakt“ gilt (je Abschnitt). */
export const WARN_MS = { home: 20, fritz: 20, internet: 60 }
