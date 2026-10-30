import { useTranslation } from "react-i18next"
import { dbText, GAIN_MAX, GAIN_MIN } from "./mixLogic"
import type { TimelineClip } from "./timelineApi"

/** Eigenschaften eines Tonclips (5b): Lautstärke, Einblenden, Ausblenden. */
export function ClipMixForm({ clip, onChange }: { clip: TimelineClip; onChange: (v: { gain_db?: number; fade_in?: number; fade_out?: number }) => void }) {
  const { t } = useTranslation("studio")
  const len = clip.out - clip.in
  const db = clip.gain_db ?? 0
  const num = "w-16 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[#0b111b] px-1.5 py-0.5 text-right text-[#e8eef8]"
  const fade = (key: "fade_in" | "fade_out", label: string) => (
    <label className="flex items-center justify-between gap-2">
      <span>{label}</span>
      <span className="flex items-center gap-1">
        <input type="number" min={0} max={Math.round(len * 100) / 100} step={0.1} value={clip[key] ?? 0} aria-label={label}
          onChange={(e) => onChange({ [key]: Number(e.target.value) || 0 })} className={num} data-clip-fade={key} /> s
      </span>
    </label>
  )
  return (
    <div className="space-y-2 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2.5 text-[#9aa7bc]" data-clip-mix={clip.id}>
      <label className="block">
        <span className="flex justify-between"><span>{t("mix_clip_volume")}</span><span className="font-mono text-[#e8eef8]">{dbText(db)}</span></span>
        <input type="range" min={GAIN_MIN} max={GAIN_MAX} step={0.5} value={db} aria-label={t("mix_clip_volume")} className="mt-1 w-full accent-[#69d7ff]"
          onChange={(e) => onChange({ gain_db: Number(e.target.value) })} onDoubleClick={() => onChange({ gain_db: 0 })} data-clip-gain />
      </label>
      {fade("fade_in", t("mix_fade_in"))}
      {fade("fade_out", t("mix_fade_out"))}
    </div>
  )
}
