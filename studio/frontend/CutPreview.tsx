import { Pause, Play, SkipBack, SkipForward, Sparkles, StepBack, StepForward } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import { nextMediaClip } from "./cutLogic"
import { fileOf } from "./planLogic"
import { timecode } from "./timeline"
import type { TimelineClip } from "./timelineApi"

interface Props {
  clips: TimelineClip[]
  base: string
  fps: number
  time: number
  total: number
  playing: boolean
  current: TimelineClip | null
  onSeek: (t: number) => void
  onPlay: () => void
  bindVideo: (el: HTMLVideoElement | null) => void
  /** Ton der Tonspuren (unsichtbar, folgt der Film-Uhr). */
  sound?: React.ReactNode
  /** Über das Bild gelegt (Untertitel, 6a) – nur im Browser, nie im Bild. */
  overlay?: React.ReactNode
}

const frame = "relative flex aspect-video max-h-full w-full items-center justify-center overflow-hidden rounded-[4px] border border-[rgb(var(--hh-s-rand,34_48_72))] bg-black"

/** Vorschau im Reiter „Schneiden“: spielt den ganzen Film über alle Clips (Video, Standbild, Platzhalter, Lücke). */
export function CutPreview({ clips, base, fps, time, total, playing, current: c, onSeek, onPlay, bindVideo, sound, overlay }: Props) {
  const { t } = useTranslation("studio")
  const next = nextMediaClip(clips, time)
  const btn = "rounded-[4px] p-1.5 text-[#c3ccdd] hover:bg-[rgb(var(--hh-s-hebung,17_24_39))] hover:text-white disabled:opacity-30"
  return (
    <section className="flex h-full min-h-0 flex-col items-center justify-center gap-2 p-3" data-studio-panel="preview">
      <div className="flex min-h-0 w-full flex-1 items-center justify-center">
        <div className={frame} data-cut-preview={c ? c.kind : "gap"}>
          {c?.kind === "video" && (
            <video key={c.id} ref={bindVideo} src={fileUrl(fileOf(base, c.media_rel))} className="h-full w-full object-contain"
              preload="auto" playsInline data-cut-video={c.id} />
          )}
          {c?.kind === "image" && <img src={fileUrl(fileOf(base, c.media_rel))} alt={c.label} className="h-full w-full object-contain" data-cut-image={c.id} />}
          {c?.kind === "placeholder" && (
            <div className={`flex max-w-[80%] flex-col items-center gap-2 text-center ${c.missing ? "text-[#ff6b8a]" : "text-[#ffb86b]"}`} data-cut-card={c.id}>
              <Sparkles size={28} />
              <span className="text-sm font-bold">{c.label}</span>
              <span className="text-xs opacity-80">{c.missing ? t("cut_missing") : t("cut_placeholder_card")}</span>
            </div>
          )}
          {/* nächster Videoclip lädt schon im Hintergrund, damit der Wechsel nicht ruckelt */}
          {sound}
          {overlay}
          {next && next.id !== c?.id && <video key={`pre-${next.id}`} src={fileUrl(fileOf(base, next.media_rel))} preload="auto" muted className="hidden" data-cut-preload={next.id} />}
        </div>
      </div>
      {total > 0 && (
        <input type="range" min={0} max={total} step={1 / fps} value={time} aria-label={t("position")} data-studio-scrub
          onChange={(e) => onSeek(Number(e.target.value))} className="w-full accent-[#ff6b8a]" />
      )}
      <div className="flex w-full items-center gap-1">
        <button type="button" className={btn} disabled={!total} title={t("goto_start")} onClick={() => onSeek(0)}><SkipBack size={14} /></button>
        <button type="button" className={btn} disabled={!total} title={t("frame_back")} onClick={() => onSeek(time - 1 / fps)}><StepBack size={14} /></button>
        <button type="button" className={`${btn} bg-[#1c2940]`} disabled={!total} title={t("play")} data-studio-action="play" onClick={onPlay}>
          {playing ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button type="button" className={btn} disabled={!total} title={t("frame_forward")} onClick={() => onSeek(time + 1 / fps)}><StepForward size={14} /></button>
        <button type="button" className={btn} disabled={!total} title={t("goto_end")} onClick={() => onSeek(total)}><SkipForward size={14} /></button>
        <span className="ml-2 font-mono text-xs text-[#e8eef8]" data-studio-timecode>{timecode(time, fps)}</span>
        <span className="font-mono text-xs text-[#9aa7bc]">/ {timecode(total, fps)}</span>
        {c && <span className="ml-auto truncate text-[11px] text-[#9aa7bc]" data-cut-current>{c.label}</span>}
      </div>
    </section>
  )
}
