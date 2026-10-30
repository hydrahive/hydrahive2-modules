import { AlertTriangle, ArrowRight, ListPlus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ClipMixForm } from "./ClipMixForm"
import { clipLength } from "./cutLogic"
import type { LibraryItem } from "./api"
import { MediaActions } from "./MediaActions"
import type { TimelineClip } from "./timelineApi"

const round = (n: number) => Math.round(n * 100) / 100

/** Eigenschaften eines Clips der Zeitleiste; Platzhalter springen zum Shot ins „Planen“. */
export function CutInspector({ clip, onPlan, media = null, onAppend, mix, onUnbind, onDeleteMedia, onCreateElement }: {
  clip: TimelineClip | null
  onPlan: (c: TimelineClip) => void
  /** Tonclip (5b): Lautstärke und Blenden einstellen. */
  mix?: (v: { gain_db?: number; fade_in?: number; fade_out?: number }) => void
  /** An einen Shot gebundene Sprache (5c) lösen. */
  onUnbind?: () => void
  /** Gewähltes Medium der Bibliothek (4b): an die Zeitleiste anhängen. */
  media?: (Pick<LibraryItem, "kind" | "name"> & Partial<LibraryItem>) | null
  onAppend?: () => void
  /** C1: gewähltes Medium löschen (Rückfrage) */
  onDeleteMedia?: (item: LibraryItem) => void
  /** C2: Bild als Vorlage für neue Figur/neuen Ort */
  onCreateElement?: (item: LibraryItem, kind: "character" | "place") => void
}) {
  const { t } = useTranslation("studio")
  if (!clip && media) return <MediaAppend media={media} onAppend={onAppend} onDelete={onDeleteMedia} onCreate={onCreateElement} />
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("properties")}</h2>
      {!clip ? <p className="mt-3 text-xs text-[#9aa7bc]">{t("nothing_selected")}</p> : (
        <div className="mt-3 space-y-3 text-xs" data-cut-info={clip.id}>
          <p className="break-words font-bold text-[#e8eef8]">{clip.label || t("untitled")}</p>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[#9aa7bc]">
            <dt>{t("info.kind")}</dt><dd className="text-right text-[#e8eef8]">{t(`cut_kind.${clip.kind}`)}</dd>
            <dt>{t("start")}</dt><dd className="text-right text-[#e8eef8]" data-cut-start={round(clip.start)}>{round(clip.start)} s</dd>
            <dt>{t("length")}</dt><dd className="text-right text-[#e8eef8]" data-cut-len={round(clipLength(clip))}>{round(clipLength(clip))} s</dd>
            {(clip.kind === "video" || clip.kind === "audio") && <><dt>{t(clip.kind === "audio" ? "cut_from_sound" : "cut_from_source")}</dt>
              <dd className="text-right text-[#e8eef8]">{round(clip.in)} s</dd></>}
          </dl>
          {clip.missing && (
            <p className="flex gap-1.5 rounded-[4px] border border-[#ff6b8a]/40 bg-[#ff6b8a]/10 px-2.5 py-2 leading-relaxed text-[#ff6b8a]">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" /> {t(clip.kind === "audio" ? "cut_audio_missing_hint" : "cut_missing")}
            </p>
          )}
          {clip.kind === "audio" && clip.shot_id && (
            <div className="space-y-1.5 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2.5 text-[#9aa7bc]" data-cut-bound>
              <p className="leading-relaxed">{t("cut_voice_bound")}</p>
              {onUnbind && <button type="button" onClick={onUnbind} data-cut-unbind
                className="rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] px-2 py-0.5 font-bold text-[#69d7ff] hover:bg-[#1c2940]">{t("cut_voice_unbind")}</button>}
            </div>
          )}
          {clip.kind === "audio" && mix && <ClipMixForm clip={clip} onChange={mix} />}
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

function MediaAppend({ media, onAppend, onDelete, onCreate }: { media: Pick<LibraryItem, "kind" | "name"> & Partial<LibraryItem>; onAppend?: () => void
  onDelete?: (item: LibraryItem) => void; onCreate?: (item: LibraryItem, kind: "character" | "place") => void }) {
  const { t } = useTranslation("studio")
  const ok = media.kind === "image" || media.kind === "video"
  const sound = media.kind === "music" || media.kind === "audio"
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#9aa7bc]">{t("properties")}</h2>
      <p className="mt-3 break-words text-xs font-bold text-[#e8eef8]">{media.name}</p>
      {ok || sound ? (
        <>
          <button type="button" onClick={onAppend} data-cut-append
            className="mt-3 flex w-full items-center justify-center gap-1.5 rounded-[4px] bg-[#69d7ff] py-1.5 text-xs font-black text-[#08111c]">
            <ListPlus size={13} /> {t(sound ? (media.kind === "music" ? "cut_append_music" : "cut_append_voice") : "cut_append")}
          </button>
          <p className="mt-2 text-[10px] leading-relaxed text-[#9aa7bc]">{t(sound ? "cut_append_sound_hint" : "cut_append_hint")}</p>
        </>
      ) : <p className="mt-3 rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 text-[11px] leading-relaxed text-[#9aa7bc]">{t("cut_not_on_timeline")}</p>}
      {onDelete && media.rel && <MediaActions item={media as LibraryItem} onDelete={() => onDelete(media as LibraryItem)}
        onCreateElement={onCreate && ((k) => onCreate(media as LibraryItem, k))} />}
    </section>
  )
}
