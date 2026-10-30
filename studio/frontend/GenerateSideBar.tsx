import { ImagePlus } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Plan } from "./planApi"

interface Props {
  plan: Plan | null
  free: boolean
  busy: boolean
  onFree: () => void
}

/** Reiter „Erzeugen“, links über der Shot-Liste: „Einzelbild (ohne Szene)“ (B3). Shots legt man im Storyboard an (C4). */
export function GenerateSideBar({ free, onFree }: Props) {
  const { t } = useTranslation("studio")
  return (
    <div className="space-y-1 border-b border-[rgb(var(--hh-s-rand,42_54_75))] p-2" data-gen-sidebar>
      <button type="button" onClick={onFree} aria-pressed={free} data-gen-free
        className={`flex w-full items-center justify-center gap-1 rounded-[4px] border px-2 py-1 text-[11px] font-bold ${free ? "border-[#69d7ff] bg-[#1c2940] text-[#69d7ff]" : "border-[rgb(var(--hh-s-rand,42_54_75))] text-[#69d7ff] hover:border-[#69d7ff] hover:bg-[#1c2940]"}`}>
        <ImagePlus size={12} /> {t("gen_free")}
      </button>
      <p className="text-[10px] leading-relaxed text-[#9aa7bc]">{t("gen_free_hint")}</p>
    </div>
  )
}
