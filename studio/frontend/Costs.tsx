import { Coins } from "lucide-react"
import { useTranslation } from "react-i18next"

/** Kleines Zeichen an Knöpfen, die beim Anbieter Geld kosten (C3) – mit Modell im Hinweis. Keine erfundenen Preise. */
export function Costs({ model }: { model?: string }) {
  const { t } = useTranslation("studio")
  const hint = model ? t("costs_hint", { model }) : t("costs_hint_default")
  return (
    <span className="inline-flex items-center gap-0.5 rounded-full bg-[#ffb86b]/15 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-[#ffb86b]"
      title={hint} data-costs>
      <Coins size={9} /> {t("costs_badge")}
    </span>
  )
}
