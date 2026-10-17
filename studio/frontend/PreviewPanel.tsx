import { Pause, Play, SkipBack, SkipForward, StepBack, StepForward } from "lucide-react"
import { useTranslation } from "react-i18next"
import { DEMO_DURATION } from "./demoData"
import { timecode } from "./timeline"

interface Props {
  time: number
  playing: boolean
  onPlay: () => void
  onSeek: (t: number) => void
}

/** Pegelanzeige links/rechts (Attrappe: bewegt sich nur beim Abspielen). */
function Meter({ playing }: { playing: boolean }) {
  const { t } = useTranslation("studio")
  return (
    <div className="flex h-full max-h-64 shrink-0 gap-0.5 self-center" title={t("meter")} data-studio-meter>
      {[0.72, 0.64].map((lvl, i) => (
        <div key={i} className="relative w-1.5 overflow-hidden rounded-full bg-[#111827]">
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-[#5fd38d] via-[#d8d35f] to-[#ff6b8a] transition-all duration-150"
            style={{ height: playing ? `${lvl * 100}%` : "0%" }} />
        </div>
      ))}
    </div>
  )
}

/** Vorschau: Bild, Transportleiste, Zeitcode, Format und Proxy-Schalter (Attrappe: farbige Fläche statt Video). */
export function PreviewPanel({ time, playing, onPlay, onSeek }: Props) {
  const { t } = useTranslation("studio")
  const hue = 190 + Math.round((time / DEMO_DURATION) * 120)
  const btn = "rounded-[4px] p-1.5 text-[#c3ccdd] hover:bg-[#111827] hover:text-white"
  return (
    <section className="flex h-full min-h-0 flex-col items-center justify-center gap-2 p-3" data-studio-panel="preview">
      <div className="relative flex min-h-0 w-full flex-1 items-center justify-center gap-2">
        <div className="aspect-video max-h-full w-full max-w-full rounded-[4px] border border-[#223048]"
          style={{ background: `radial-gradient(circle at 30% 40%, hsl(${hue} 50% 38%), hsl(${hue + 40} 45% 10%))` }}>
          <div className="flex h-full items-end justify-center pb-[8%]">
            {time > 6.5 && time < 10 && <span className="rounded bg-black/50 px-2 py-0.5 text-sm text-white">Wo bist du gewesen?</span>}
          </div>
        </div>
        <Meter playing={playing} />
      </div>
      <div className="flex w-full items-center gap-1">
        <button type="button" className={btn} title={t("goto_start")} onClick={() => onSeek(0)}><SkipBack size={14} /></button>
        <button type="button" className={btn} title={t("frame_back")} onClick={() => onSeek(time - 1 / 25)}><StepBack size={14} /></button>
        <button type="button" className={`${btn} bg-[#1c2940]`} title={t("play")} data-studio-action="play" onClick={onPlay}>
          {playing ? <Pause size={15} /> : <Play size={15} />}
        </button>
        <button type="button" className={btn} title={t("frame_forward")} onClick={() => onSeek(time + 1 / 25)}><StepForward size={14} /></button>
        <button type="button" className={btn} title={t("goto_end")} onClick={() => onSeek(DEMO_DURATION)}><SkipForward size={14} /></button>
        <span className="ml-2 font-mono text-xs text-[#e8eef8]" data-studio-timecode>{timecode(time)}</span>
        <span className="font-mono text-xs text-[#68758a]">/ {timecode(DEMO_DURATION)}</span>
        <span className="ml-auto flex items-center gap-2 text-[11px] text-[#8d9ab0]">
          <select className="rounded-[4px] border border-[#2a364b] bg-[#111827] px-1.5 py-0.5" aria-label={t("format")}>
            <option>16:9</option><option>9:16</option><option>1:1</option>
          </select>
          <span className="flex items-center gap-1" title={t("proxy_hint")}><span className="h-1.5 w-1.5 rounded-full bg-[#5fd38d]" /> {t("proxy")}</span>
        </span>
      </div>
    </section>
  )
}
