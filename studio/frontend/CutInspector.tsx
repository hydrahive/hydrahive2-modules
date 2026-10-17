import { AlertTriangle, ArrowRight, ListPlus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { clipLength } from "./cutLogic"
import type { TimelineClip } from "./timelineApi"

const round = (n: number) => Math.round(n * 100) / 100

/** Eigenschaften eines Clips der Zeitleiste; Platzhalter springen zum Shot ins „Planen“. */
export function CutInspector({ clip, onPlan, media = null, onAppend }: {
  clip: TimelineClip | null
  onPlan: (c: TimelineClip) => void
  /** Gewähltes Medium der Bibliothek (4b): an die Zeitleiste anhängen. */
  media?: { kind: string; name: string } | null
  onAppend?: () => void
}) {
  const { t } = useTranslation("studio")
  if (!clip && media) return <MediaAppend media={media} onAppend={onAppend} />
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("properties")}</h2>
      {!clip ? <p className="mt-3 text-xs text-[#68758a]">{t("nothing_selected")}</p> : (
        <div className="mt-3 space-y-3 text-xs" data-cut-info={clip.id}>
          <p className="break-words font-bold text-[#e8eef8]">{clip.label || t("untitled")}</p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[#8d9ab0]">
            <dt>{t("info.kind")}</dt><dd className="text-right text-[#e8eef8]">{t(`cut_kind.${clip.kind}`)}</dd>
            <dt>{t("start")}</dt><dd className="text-right text-[#e8eef8]" data-cut-start={round(clip.start)}>{round(clip.start)} s</dd>
            <dt>{t("length")}</dt><dd className="text-right text-[#e8eef8]" data-cut-len={round(clipLength(clip))}>{round(clipLength(clip))} s</dd>
            {clip.kind === "video" && <><dt>{t("cut_from_source")}</dt><dd className="text-right text-[#e8eef8]">{round(clip.in)} s</dd></>}
          </dl>
          {clip.missing && (
            <p className="flex gap-1.5 rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2.5 py-2 leading-relaxed text-[#ff6b8a]">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {t("cut_missing")}
            </p>
          )}
          {clip.kind === "placeholder" && clip.shot_id && (
            <button type="button" onClick={() => onPlan(clip)} data-cut-to-plan
              className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-[#ffb86b]/60 bg-[#ffb86b]/10 py-1.5 font-bold text-[#ffb86b] hover:bg-[#ffb86b]/20">
              {t("cut_to_plan")} <ArrowRight size={13} />
            </button>
          )}
        </div>
      )}
    </section>
  )
}

function MediaAppend({ media, onAppend }: { media: { kind: string; name: string }; onAppend?: () => void }) {
  const { t } = useTranslation("studio")
  const ok = media.kind === "image" || media.kind === "video"
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("properties")}</h2>
      <p className="mt-3 break-words text-xs font-bold text-[#e8eef8]">{media.name}</p>
      {ok ? (
        <>
          <button type="button" onClick={onAppend} data-cut-append
            className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 text-xs font-black text-[#08111c]">
            <ListPlus size={13} /> {t("cut_append")}
          </button>
          <p className="mt-2 text-[10px] leading-relaxed text-[#68758a]">{t("cut_append_hint")}</p>
        </>
      ) : <p className="mt-3 rounded-[4px] border border-[#46617f] bg-[#111827] px-2.5 py-2 text-[11px] leading-relaxed text-[#8d9ab0]">{t("cut_no_audio_yet")}</p>}
    </section>
  )
}
