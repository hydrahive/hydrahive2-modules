import { Sparkles } from "lucide-react"
import { useTranslation } from "react-i18next"

/** Reiter „Erzeugen“, rechts, solange kein Shot gewählt ist. */
export function GenerateHint() {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("generate")}</h2>
      <p className="mt-3 flex gap-2 rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 text-xs leading-relaxed text-[#9aa7bc]" data-gen-hint>
        <Sparkles size={14} className="mt-0.5 shrink-0 text-[#69d7ff]" /> {t("gen_pick_shot")}
      </p>
    </section>
  )
}
