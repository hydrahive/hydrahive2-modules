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
          ? "border-[#69d7ff] bg-[#69d7ff]/15 ring-1 ring-[#69d7ff]/60" : "border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.4)] hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))]"}`}>
        <span className={`mt-0.5 rounded-lg p-2 ${on ? "bg-[#69d7ff]/25 text-[#69d7ff]" : "bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df]"}`}><Icon size={18} /></span>
        <span>
          <span className={`block text-sm font-semibold ${on ? "text-[#c8f2ff]" : "text-[#e8eef8]"}`}>{t(`dial.mode_${m}`)}</span>
          <span className="mt-0.5 block text-xs text-[#c8d2df]">{t(`dial.mode_${m}_help`)}</span>
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
