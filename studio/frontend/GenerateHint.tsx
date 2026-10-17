import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"

/** Reiter „Erzeugen“, rechts, solange kein Shot gewählt ist. */
export function GenerateHint() {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("generate")}</h2>
      <p className="mt-3 flex gap-2 rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 text-xs leading-relaxed text-[#8d9ab0]" data-gen-hint>
        <Sparkles size={14} className="mt-0.5 shrink-0 text-[#69d7ff]" /> {t("gen_pick_shot")}
      </p>
    </section>
  )
}
