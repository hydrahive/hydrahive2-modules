import { moduleIcon } from "@/shared/module-icon"
import { PALETTE } from "./palette-data"

/** Linke Leiste: Bausteine per Drag aufs Canvas ziehen. */
export function NodePalette() {
  const onDragStart = (e: React.DragEvent, subtype: string) => {
    e.dataTransfer.setData("application/blueprint-node", JSON.stringify({ subtype }))
    e.dataTransfer.effectAllowed = "move"
  }

  return (
    <div className="w-44 shrink-0 overflow-y-auto border-r border-white/8 bg-zinc-950/40 p-3">
      {PALETTE.map((group) => (
        <div key={group.kind} className="mb-4">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-500">
            {group.label}
          </p>
          <div className="space-y-1.5">
            {group.items.map((it) => {
              const Icon = moduleIcon(it.icon)
              return (
                <div
                  key={it.subtype}
                  draggable
                  onDragStart={(e) => onDragStart(e, it.subtype)}
                  className={`flex cursor-grab items-center gap-2 rounded-lg border px-2.5 py-1.5 text-xs transition-colors active:cursor-grabbing ${
                    group.kind === "layout"
                      ? "border-zinc-700/60 bg-zinc-800/50 text-zinc-300 hover:bg-zinc-700/60"
                      : "border-sky-800/40 bg-sky-950/30 text-sky-200 hover:bg-sky-900/40"
                  }`}
                >
                  <Icon size={13} className="shrink-0" />
                  <span className="truncate">{it.label}</span>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
