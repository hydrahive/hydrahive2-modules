import { useTranslation } from "react-i18next"
import { ASPECTS, aspectKey, outputSize, QUALITIES, type Aspect, type Preset, type Quality } from "./deliverLogic"

interface Props {
  preset: Preset
  /** Format des Drehbuchs (für „Wie im Drehbuch“ und die Ergebnisgröße) */
  screenplay: string
  disabled?: boolean
  onChange?: (p: Preset) => void
}

const field = "rounded-[4px] border border-[#2a364b] bg-[#0b111b] px-2 py-1 text-[#e8eef8] focus:border-[#69d7ff] focus:outline-none disabled:opacity-50"

/** Vorlage für die Ausgabe (7b): Format + Qualität, darunter die Ergebnisgröße. */
export function DeliverPreset({ preset, screenplay, disabled = false, onChange }: Props) {
  const { t } = useTranslation("studio")
  const [w, h] = outputSize(preset.aspect, preset.quality, screenplay)
  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-3">
        <label className="flex flex-col gap-1">
          <span className="text-[11px] font-bold text-[#8d9ab0]">{t("deliver_aspect_label")}</span>
          <select value={preset.aspect} disabled={disabled} data-deliver-aspect className={field}
            onChange={(e) => onChange?.({ ...preset, aspect: e.target.value as Aspect })}>
            {ASPECTS.map((a) => <option key={a} value={a}>{a === "screenplay" ? t("deliver_aspect.screenplay", { aspect: screenplay }) : t(aspectKey(a))}</option>)}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-[11px] font-bold text-[#8d9ab0]">{t("deliver_quality_label")}</span>
          <select value={preset.quality} disabled={disabled} data-deliver-quality className={field}
            onChange={(e) => onChange?.({ ...preset, quality: e.target.value as Quality })}>
            {QUALITIES.map((q) => <option key={q} value={q}>{t(`deliver_quality.${q}`)}</option>)}
          </select>
        </label>
      </div>
      <p className="text-[#8d9ab0]" data-deliver-result>{t("deliver_result", { width: w, height: h })}</p>
    </div>
  )
}
