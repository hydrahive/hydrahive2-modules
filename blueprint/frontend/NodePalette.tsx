import { moduleIcon } from "@/shared/module-icon"
import { PALETTE } from "./palette-data"

/** Linke Leiste: Bausteine per Drag aufs Canvas ziehen. */
export function NodePalette() {
  const onDragStart = (e: React.DragEvent, subtype: string) => {
    e.dataTransfer.setData("application/blueprint-node", JSON.stringify({ subtype }))
    e.dataTransfer.effectAllowed = "move"
  }

  return (
    <div className="w-44 shrink-0 overflow-y-auto border-r border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.4)] p-3">
      {PALETTE.map((group) => (
        <div key={group.kind} className="mb-4">
          <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-[#9aa7bc]">
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
                      ? "border-[rgb(var(--hh-s-rand,42_54_75)/0.6)] bg-[rgb(var(--hh-s-innen,17_24_39)/0.5)] text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54)/0.6)]"
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
