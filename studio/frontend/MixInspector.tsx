import { useTranslation } from "react-i18next"
import { ClipMixForm } from "./ClipMixForm"
import type { TimelineClip } from "./timelineApi"

/** Rechts im Reiter „Ton“: Lautstärke und Blenden des gewählten Tonclips, sonst ein Hinweis. */
export function MixInspector({ clip, onChange }: { clip: TimelineClip | null; onChange: (v: { gain_db?: number; fade_in?: number; fade_out?: number }) => void }) {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto p-3 text-xs" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("properties")}</h2>
      {clip?.kind === "audio" ? <>
        <p className="break-words font-bold text-[#e8eef8]">{clip.label || t("untitled")}</p>
        <ClipMixForm clip={clip} onChange={onChange} />
      </> : <p className="leading-relaxed text-[#9aa7bc]">{t("mix_pick_clip")}</p>}
    </section>
  )
}
