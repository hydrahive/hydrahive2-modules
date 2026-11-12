// Gemeinsame Klassen der Ideen-Bausteine. Flächen und Ränder nur über die Farbstufen des Kerns
// (mit Rückfallwert für ältere Kerne), Akzent #69d7ff wie im übrigen Cockpit.
import type { IdeaStatus } from "../types"

export const FIELD =
  "w-full rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))] " +
  "px-3 py-2 text-sm text-[#e8eef8] placeholder:text-[#9aa7bc] transition-colors " +
  "focus:border-[#69d7ff]/70 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/30"

export const SELECT = `${FIELD} cursor-pointer py-1.5 text-xs`

export const LABEL = "mb-1 block text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9aa7bc]"

export const BUTTON =
  "inline-flex items-center justify-center gap-1.5 rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] " +
  "bg-[rgb(var(--hh-s-innen,36_48_71))] px-3 py-1.5 text-xs font-semibold text-[#c8d2df] transition-colors " +
  "hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))] hover:bg-[rgb(var(--hh-s-hebung,43_56_82))] " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/40 disabled:cursor-not-allowed disabled:opacity-50"

export const BUTTON_PRIMARY =
  "inline-flex items-center justify-center gap-1.5 rounded-[6px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 " +
  "px-3 py-1.5 text-xs font-semibold text-[#c8f2ff] transition-colors hover:border-[#69d7ff] hover:bg-[#69d7ff]/25 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/40 disabled:cursor-not-allowed disabled:opacity-50"

export const BUTTON_DANGER =
  "inline-flex items-center justify-center gap-1.5 rounded-[6px] border border-rose-400/40 bg-rose-400/10 " +
  "px-3 py-1.5 text-xs font-semibold text-rose-100 transition-colors hover:border-rose-300/70 hover:bg-rose-400/20 " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-300/40 disabled:cursor-not-allowed disabled:opacity-50"

export const PANEL = "rounded-[8px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-box,23_32_48))]"

export const ERROR_BOX = "rounded-[6px] border border-rose-400/40 bg-rose-400/10 px-3 py-2 text-xs text-rose-100"

/** Marke je Status: Neu fällt auf, Erledigtes und Verworfenes tritt zurück. */
export const STATUS_BADGE: Record<IdeaStatus, string> = {
  new: "border-[#69d7ff]/40 bg-[#69d7ff]/10 text-[#9fe6ff]",
  review: "border-amber-400/35 bg-amber-400/10 text-amber-200",
  planned: "border-sky-400/35 bg-sky-400/10 text-sky-200",
  parked: "border-[rgb(var(--hh-s-rand-hover,70_97_127)/0.6)] bg-[rgb(var(--hh-s-rand-hover,70_97_127)/0.12)] text-[#c8d2df]",
  done: "border-emerald-400/35 bg-emerald-400/10 text-emerald-200",
  dropped: "border-[rgb(var(--hh-s-rand,52_66_92))] bg-transparent text-[#9aa7bc] line-through",
}

export const BADGE = "inline-flex shrink-0 items-center rounded-[4px] border px-1.5 py-0.5 text-[10px] font-semibold leading-none"
