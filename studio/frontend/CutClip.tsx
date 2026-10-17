import { Film, Image as ImageIcon, Sparkles } from "lucide-react"
import { fileUrl } from "@/shared/files"
import { CLIP_MIME, pct } from "./cutDnd"
import { clipLength } from "./cutLogic"
import { fileOf } from "./planLogic"
import { toFraction, type Viewport } from "./timeline"
import type { TimelineClip } from "./timelineApi"


interface Props {
  clip: TimelineClip
  base: string
  view: Viewport
  active: boolean
  editable: boolean
  onSelect: (id: string) => void
  /** Rand greifen: Startpunkt in Bildschirm-Pixeln, die Spur misst daraus die Verschiebung. */
  onTrimStart?: (id: string, edge: "start" | "end", clientX: number) => void
}

/** Ein Clip auf der Spur V1: anklicken, ziehen (umsortieren), an den Rändern kürzen. */
export function CutClip({ clip, base, view, active, editable, onSelect, onTrimStart }: Props) {
  const left = toFraction(clip.start, view)
  const width = clipLength(clip) / view.span
  if (left + width < 0 || left > 1) return null
  const ph = clip.kind === "placeholder"
  const img = clip.kind === "image" ? fileOf(base, clip.media_rel) : ""
  const grip = (edge: "start" | "end") => editable && onTrimStart && (
    <span role="separator" aria-orientation="vertical" data-cut-trim={`${clip.id}:${edge}`}
      onPointerDown={(e) => { e.stopPropagation(); e.preventDefault(); onTrimStart(clip.id, edge, e.clientX) }}
      className={`absolute inset-y-0 z-10 w-1.5 cursor-ew-resize ${edge === "start" ? "left-0" : "right-0"} ${active ? "bg-[#69d7ff]" : "hover:bg-[#69d7ff]/70"}`} />
  )
  return (
    <div data-cut-clip={clip.id} data-placeholder={ph ? "1" : undefined} draggable={editable} role="button" tabIndex={0} title={clip.label}
      onClick={() => onSelect(clip.id)} onKeyDown={(e) => { if (e.key === "Enter") onSelect(clip.id) }}
      onDragStart={(e) => { e.dataTransfer.setData(CLIP_MIME, clip.id); e.dataTransfer.effectAllowed = "move"; onSelect(clip.id) }}
      className={`absolute inset-y-1.5 flex cursor-grab items-center gap-1 overflow-hidden rounded-[3px] px-2 text-left text-[10px] text-white active:cursor-grabbing
        ${ph ? `border border-dashed ${clip.missing ? "border-[#ff6b8a] bg-[#ff6b8a]/10 text-[#ff6b8a]" : "border-[#ffb86b] bg-[#ffb86b]/10 text-[#ffb86b]"}`
        : clip.kind === "image" ? "bg-[#3d5a80]" : "bg-[#2f6aa8]"} ${active ? "ring-2 ring-[#69d7ff]" : ""}`}
      style={{ left: pct(left), width: pct(width) }}>
      {img && <img src={fileUrl(img)} alt="" loading="lazy" draggable={false} className="pointer-events-none absolute inset-0 h-full w-full object-cover opacity-35" />}
      {grip("start")}
      <span className="pointer-events-none relative flex min-w-0 items-center gap-1">
        {ph ? <Sparkles size={10} className="shrink-0" /> : clip.kind === "image" ? <ImageIcon size={10} className="shrink-0" /> : <Film size={10} className="shrink-0" />}
        <span className="truncate">{clip.label}</span>
      </span>
      {grip("end")}
    </div>
  )
}
