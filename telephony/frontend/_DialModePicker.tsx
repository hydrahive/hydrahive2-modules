import { Bot, Megaphone } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { DialMode } from "./types"

/** Zwei große Karten „Ansage vorlesen“ / „Assistent führt das Gespräch“ (Till 25.10.: Auswahl war zu unauffällig). */
export function DialModePicker({ mode, onChange }: { mode: DialMode; onChange: (m: DialMode) => void }) {
  const { t } = useTranslation("voip")
  const card = (m: DialMode, Icon: typeof Bot) => {
    const on = mode === m
    return (
      <button key={m} type="button" role="radio" aria-checked={on} data-voip-dial-mode={m} onClick={() => onChange(m)}
        className={`flex flex-1 items-start gap-3 rounded-xl border p-4 text-left transition-colors ${on
          ? "border-indigo-400 bg-indigo-500/15 ring-1 ring-indigo-400/60" : "border-zinc-700 bg-zinc-950/40 hover:border-zinc-500"}`}>
        <span className={`mt-0.5 rounded-lg p-2 ${on ? "bg-indigo-500/25 text-indigo-200" : "bg-zinc-800 text-zinc-400"}`}><Icon size={18} /></span>
        <span>
          <span className={`block text-sm font-semibold ${on ? "text-indigo-100" : "text-zinc-200"}`}>{t(`dial.mode_${m}`)}</span>
          <span className="mt-0.5 block text-xs text-zinc-400">{t(`dial.mode_${m}_help`)}</span>
        </span>
      </button>
    )
  }
  return (
    <div role="radiogroup" aria-label={t("dial.mode_label")} className="flex flex-col gap-3 sm:flex-row">
      {card("greeting", Megaphone)}{card("assistant", Bot)}
    </div>
  )
}
