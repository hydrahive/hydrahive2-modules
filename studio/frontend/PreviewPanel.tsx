import { Pause, Play, SkipBack, SkipForward, StepBack, StepForward } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { MediaView } from "./MediaView"
import { timecode } from "./timeline"

interface Props {
  item: LibraryItem | null
  bind: (el: HTMLMediaElement | null) => void
  time: number
  duration: number
  playing: boolean
  onPlay: () => void
  onSeek: (t: number) => void
}

/** Pegelanzeige links/rechts (Andeutung: bewegt sich beim Abspielen; echte Pegel kommen mit dem Ton, Etappe 5). */
function Meter({ playing }: { playing: boolean }) {
  const { t } = useTranslation("studio")
  return (
    <div className="flex h-full max-h-64 shrink-0 gap-0.5 self-center" title={t("meter")} data-studio-meter>
      {[0.72, 0.64].map((lvl, i) => (
        <div key={i} className="relative w-1.5 overflow-hidden rounded-full bg-[rgb(var(--hh-s-innen,17_24_39))]">
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#5fd38d] via-[#d8d35f] to-[#ff6b8a] transition-all duration-150"
            style={{ height: playing ? `${lvl * 100}%` : "0%" }} />
        </div>
      ))}
    </div>
  )
}

/** Vorschau: echtes Medium aus der Bibliothek, Transportleiste, Zeitcode, Bildformat, Vorschau-Kopie-Hinweis. */
export function PreviewPanel({ item, bind, time, duration, playing, onPlay, onSeek }: Props) {
  const { t } = useTranslation("studio")
  const playable = item?.kind === "video" || item?.kind === "music" || item?.kind === "audio"
  const btn = "rounded-[4px] p-1.5 text-[#c3ccdd] hover:bg-[rgb(var(--hh-s-hebung,17_24_39))] hover:text-white disabled:opacity-30"
  return (
    <section className="flex h-full min-h-0 flex-col items-center justify-center gap-2 p-3" data-studio-panel="preview">
      <div className="relative flex min-h-0 w-full flex-1 items-center justify-center gap-2">
        <MediaView item={item} bind={bind} />
        <Meter playing={playing} />
      </div>
      {playable && duration > 0 && (
        <input type="range" min={0} max={duration} step={0.04} value={time} aria-label={t("position")} data-studio-scrub
          onChange={(e) => onSeek(Number(e.target.value))} className="w-full accent-[#ff6b8a]" />
      )}
      <div className="flex w-full items-center gap-1">
        <button type="button" className={btn} disabled={!playable} title={t("goto_start")} onClick={() => onSeek(0)}><SkipBack size={14} /></button>
        <button type="button" className={btn} disabled={!playable} title={t("frame_back")} onClick={() => onSeek(time - 1 / 25)}><StepBack size={14} /></button>
        <button type="button" className={`${btn} bg-[#1c2940]`} disabled={!playable} title={t("play")} data-studio-action="play" onClick={onPlay}>
          {playing ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button type="button" className={btn} disabled={!playable} title={t("frame_forward")} onClick={() => onSeek(time + 1 / 25)}><StepForward size={14} /></button>
        <button type="button" className={btn} disabled={!playable} title={t("goto_end")} onClick={() => onSeek(duration)}><SkipForward size={14} /></button>
        <span className="ml-2 font-mono text-xs text-[#e8eef8]" data-studio-timecode>{timecode(time)}</span>
        <span className="font-mono text-xs text-[#9aa7bc]">/ {timecode(duration)}</span>
        <span className="ml-auto flex items-center gap-2 text-[11px] text-[#9aa7bc]">
          <select className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-1.5 py-0.5" aria-label={t("format")}>
            <option>16:9</option><option>9:16</option><option>1:1</option>
          </select>
          <span className="flex items-center gap-1" title={t("proxy_hint")}><span className="h-1.5 w-1.5 rounded-full bg-[#5fd38d]" /> {t("proxy")}</span>
        </span>
      </div>
    </section>
  )
}
