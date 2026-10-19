import { Coins, HardDrive } from "lucide-react"
import { useTranslation } from "react-i18next"
import { isLocalModel } from "./localModel"

/** Kleines Zeichen an Knöpfen, die beim Anbieter Geld kosten (C3) – mit Modell im Hinweis. Keine erfundenen Preise.
 *  Bei lokalen Modellen stattdessen „lokal“ (kostet nichts). */
export function Costs({ model }: { model?: string }) {
  const { t } = useTranslation("studio")
  if (isLocalModel(model)) {
    return (
      <span className="inline-flex items-center gap-0.5 rounded-full bg-[#3ddc97]/15 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-[#3ddc97]"
        title={t("costs_local_hint", { model })} data-local>
        <HardDrive size={9} /> {t("costs_local_badge")}
      </span>
    )
  }
  const hint = model ? t("costs_hint", { model }) : t("costs_hint_default")
  return (
    <span className="inline-flex items-center gap-0.5 rounded-full bg-[#ffb86b]/15 px-1.5 py-px text-[9px] font-bold uppercase tracking-wide text-[#ffb86b]"
      title={hint} data-costs>
      <Coins size={9} /> {t("costs_badge")}
    </span>
  )
}
