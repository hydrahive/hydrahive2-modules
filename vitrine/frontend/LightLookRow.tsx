import { useTranslation } from "react-i18next"
import { Eye } from "lucide-react"
import { LIGHT_EFFECTS, lightColor, toPicker, type LightEffect } from "./light"

const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-xs text-[#e8eef8]"

export interface LookValue { effect: LightEffect; color: string; speed?: number; brightness?: number | null }

/** Eine Zeile der Licht-Karte: Effekt, Farbe, (Tempo, eigene Helligkeit) und Vorschau-Knopf. */
export function LightLookRow({ title, value, onChange, onPreview, withSpeed = false, withBrightness = false, bad = false, children }: {
  title: string; value: LookValue; onChange: (v: LookValue) => void; onPreview?: () => void
  withSpeed?: boolean; withBrightness?: boolean; bad?: boolean; children?: React.ReactNode
}) {
  const { t } = useTranslation("vitrine")
  const moving = value.effect === "breathing" || value.effect === "flashing"
  return (
    <div className={`flex flex-wrap items-center gap-2 rounded-[4px] border px-2 py-1.5 ${bad ? "border-rose-400/60" : "border-[rgb(var(--hh-s-rand,28_38_56))]"}`}>
      <span className="h-4 w-4 shrink-0 rounded-full border border-[rgb(var(--hh-s-rand-hover,70_97_127))]" style={{ background: value.effect === "off" ? "#000" : toPicker(value.color) }} />
      <span className="w-32 shrink-0 text-xs font-semibold text-[#c8d2df]">{title}</span>
      <select aria-label={t("light_effect")} className={field} value={value.effect} onChange={(e) => onChange({ ...value, effect: e.target.value as LightEffect })}>
        {LIGHT_EFFECTS.map((x) => <option key={x} value={x}>{t(`light_effect_${x}`)}</option>)}
      </select>
      <input type="color" aria-label={t("light_color")} disabled={value.effect === "off"} value={toPicker(value.color)}
        onChange={(e) => onChange({ ...value, color: lightColor(e.target.value) ?? value.color })} className="h-7 w-10 cursor-pointer rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-transparent disabled:opacity-30" />
      {withSpeed && moving && (
        <label className="flex items-center gap-1 text-[11px] text-[#9aa7bc]">{t("light_speed")}
          <input type="range" min={0} max={100} value={value.speed ?? 50} onChange={(e) => onChange({ ...value, speed: Number(e.target.value) })} />
        </label>
      )}
      {withBrightness && (
        <label className="flex items-center gap-1 text-[11px] text-[#9aa7bc]">{t("light_own_brightness")}
          <input type="number" min={0} max={100} placeholder={t("light_brightness_default")} className={`${field} w-16`}
            value={value.brightness ?? ""} onChange={(e) => onChange({ ...value, brightness: e.target.value === "" ? null : Math.max(0, Math.min(100, Math.round(Number(e.target.value)))) })} />
        </label>
      )}
      {children}
      {onPreview && (
        <button type="button" onClick={onPreview} className="ml-auto flex items-center gap-1 rounded-[4px] border border-amber-300/40 bg-amber-300/10 px-2 py-0.5 text-[11px] font-bold text-amber-200">
          <Eye size={12} />{t("light_preview")}
        </button>
      )}
    </div>
  )
}
