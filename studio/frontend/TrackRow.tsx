import { Eye, Sparkles, Volume2 } from "lucide-react"
import type { DemoTrack, TrackKind } from "./demoData"
import { toFraction, type Viewport } from "./timeline"

const COLOR: Record<TrackKind, string> = {
  text: "bg-[#7c5cff]/70", video: "bg-[#2f6aa8]", voice: "bg-[#c2477a]", music: "bg-[#6a4fb3]", subtitle: "bg-[#3d7a6a]",
}

interface Props {
  track: DemoTrack
  view: Viewport
  big: boolean
  selected: string | null
  onSelect: (clipId: string) => void
}

/** Eine Spur: Kopf (Name, sichtbar/hörbar) + Clips im Ausschnitt. Platzhalter sind gestrichelt. */
export function TrackRow({ track, view, big, selected, onSelect }: Props) {
  const audio = track.kind === "voice" || track.kind === "music"
  return (
    <div className={`flex border-b border-[#1e2738] ${big ? "h-12" : "h-6 opacity-60"}`} data-studio-track={track.kind}>
      <div className="flex w-24 shrink-0 items-center gap-1 border-r border-[#1e2738] bg-[#0d1420] px-2 text-[10px] text-[#8d9ab0]">
        <span className="min-w-0 flex-1 truncate font-bold">{track.label}</span>
        {big && (audio ? <Volume2 size={11} /> : <Eye size={11} />)}
      </div>
      <div className="relative min-w-0 flex-1 overflow-hidden">
        {track.clips.map((c) => {
          const left = toFraction(c.start, view)
          const width = c.length / view.span
          if (left + width < 0 || left > 1) return null
          const active = c.id === selected
          return (
            <button key={c.id} type="button" data-studio-clip={c.id} data-placeholder={c.placeholder ? "1" : undefined}
              onClick={() => onSelect(c.id)}
              className={`absolute inset-y-1 flex items-center gap-1 overflow-hidden rounded-[3px] px-1.5 text-left text-[10px] text-white
                ${c.placeholder ? "border border-dashed border-[#ffb86b] bg-[#ffb86b]/10 text-[#ffb86b]" : COLOR[track.kind]}
                ${active ? "ring-2 ring-[#69d7ff]" : ""}`}
              style={{ left: `${left * 100}%`, width: `${width * 100}%` }}>
              {c.placeholder && <Sparkles size={10} className="shrink-0" />}
              <span className="truncate">{c.label}</span>
              {audio && big && <Wave />}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** Angedeutete Wellenform (Attrappe). */
function Wave() {
  return (
    <svg className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 w-full opacity-40" preserveAspectRatio="none" viewBox="0 0 100 10">
      <path d="M0 5 Q 5 0 10 5 T 20 5 T 30 5 T 40 5 T 50 5 T 60 5 T 70 5 T 80 5 T 90 5 T 100 5" fill="none" stroke="white" strokeWidth="1" />
    </svg>
  )
}
