import { Captions } from "lucide-react"
import { useTranslation } from "react-i18next"
import { pct } from "./cutDnd"
import type { Cue } from "./subtitleLogic"
import { toFraction, type Viewport } from "./timeline"

interface Props { cues: Cue[]; view: Viewport; time: number; selected: string | null; onSelect: (id: string) => void; onSeek: (t: number) => void }

/** Zeile „Untertitel“ unter den Tonspuren (Spec 6a): ein Kästchen je Eintrag; Klick wählt und springt hin. */
export function SubtitleTrack({ cues, view, time, selected, onSelect, onSeek }: Props) {
  const { t } = useTranslation("studio")
  const visible = cues.filter((c) => c.end > view.start && c.start < view.start + view.span)
  return (
    <div className="flex h-9 border-b border-[#1e2738]" data-sub-track>
      <div className="flex w-24 shrink-0 items-center gap-1.5 border-r border-[#1e2738] px-2 text-[10px] font-bold text-[#8d9ab0]">
        <Captions size={12} /> {t("sub_track")}
      </div>
      <div className="relative min-w-0 flex-1 overflow-hidden">
        {visible.map((c) => {
          const left = Math.max(0, toFraction(c.start, view)), right = Math.min(1, toFraction(c.end, view))
          return (
            <button key={c.id} type="button" aria-pressed={c.id === selected} title={c.text} data-sub-box={c.id}
              style={{ left: pct(left), width: pct(right - left) }} onClick={() => { onSelect(c.id); onSeek(c.start) }}
              className={`absolute inset-y-1 truncate rounded-[3px] border px-1 text-left text-[10px] leading-6 ${c.id === selected
                ? "border-[#69d7ff] bg-[#69d7ff]/25 text-white" : "border-[#46617f] bg-[#1c2940] text-[#c3ccdd] hover:border-[#69d7ff]"}`}>
              {c.text.replace(/\n/g, " ")}
            </button>
          )
        })}
        {time >= view.start && time <= view.start + view.span && (
          <span className="pointer-events-none absolute inset-y-0 w-px bg-[#ff6b8a]" style={{ left: pct(toFraction(time, view)) }} data-sub-playhead />
        )}
      </div>
    </div>
  )
}
