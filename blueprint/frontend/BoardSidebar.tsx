import { useState } from "react"
import { Plus, Trash2, PenTool } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import type { BoardMeta } from "./types"
import leerBild from "./assets/leer.webp"

interface Props {
  boards: BoardMeta[]
  activeId: number | null
  onSelect: (id: number) => void
  onCreate: (name: string) => void
  onDelete: (id: number) => void
}

/** Ganz links: Liste aller Boards + Neu-anlegen. */
export function BoardSidebar({ boards, activeId, onSelect, onCreate, onDelete }: Props) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")

  const submit = () => {
    const n = name.trim()
    if (!n) return
    onCreate(n)
    setName("")
    setAdding(false)
  }

  return (
    <div className="flex w-52 shrink-0 flex-col border-r border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.6)]">
      <div className="flex items-center gap-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-3">
        <PenTool size={16} className="text-[#c8d2df]" />
        <span className="text-sm font-semibold text-[#e8eef8]">Boards</span>
        <HelpButton topic="blueprint" />
        <button
          onClick={() => setAdding((v) => !v)}
          className="ml-auto rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39))] p-1.5 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
          title="Neues Board"
        >
          <Plus size={14} />
        </button>
      </div>

      {adding && (
        <div className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] p-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Board-Name…"
            autoFocus
            className="w-full rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-2.5 py-1.5 text-sm text-[#e8eef8] placeholder-[#9aa7bc] focus:outline-none focus:ring-1 focus:ring-[rgb(var(--hh-s-rand-hover,70_97_127))]"
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2">
        {boards.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center"><img src={leerBild} alt="" loading="lazy" draggable={false} className="mx-auto h-20 w-20 select-none object-contain" /><p className="text-xs text-[#9aa7bc]">Noch keine Boards — oben „+" klicken.</p></div>
        ) : (
          <ul className="space-y-1">
            {boards.map((b) => (
              <li key={b.id}>
                <div
                  className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                    activeId === b.id
                      ? "bg-sky-500/15 text-sky-200"
                      : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
                  }`}
                >
                  <button onClick={() => onSelect(b.id)} className="flex-1 truncate text-left">
                    {b.name}
                  </button>
                  <button
                    onClick={() => onDelete(b.id)}
                    className="text-[#9aa7bc] opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
                    title="Board löschen"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
