import { useState } from "react"
import { Plus, Trash2, PenTool } from "lucide-react"
import type { BoardMeta } from "./types"

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
    <div className="flex w-52 shrink-0 flex-col border-r border-white/8 bg-zinc-950/60">
      <div className="flex items-center gap-2 border-b border-white/8 px-3 py-3">
        <PenTool size={16} className="text-zinc-400" />
        <span className="text-sm font-semibold text-zinc-200">Boards</span>
        <button
          onClick={() => setAdding((v) => !v)}
          className="ml-auto rounded-lg bg-zinc-800 p-1.5 text-zinc-300 hover:bg-zinc-700"
          title="Neues Board"
        >
          <Plus size={14} />
        </button>
      </div>

      {adding && (
        <div className="border-b border-white/8 p-2">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="Board-Name…"
            autoFocus
            className="w-full rounded-lg border border-white/10 bg-zinc-900 px-2.5 py-1.5 text-sm text-zinc-100 placeholder-zinc-600 focus:outline-none focus:ring-1 focus:ring-white/20"
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2">
        {boards.length === 0 ? (
          <p className="px-2 py-3 text-xs text-zinc-600">Noch keine Boards — oben „+" klicken.</p>
        ) : (
          <ul className="space-y-1">
            {boards.map((b) => (
              <li key={b.id}>
                <div
                  className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                    activeId === b.id
                      ? "bg-sky-500/15 text-sky-200"
                      : "text-zinc-300 hover:bg-white/5"
                  }`}
                >
                  <button onClick={() => onSelect(b.id)} className="flex-1 truncate text-left">
                    {b.name}
                  </button>
                  <button
                    onClick={() => onDelete(b.id)}
                    className="text-zinc-600 opacity-0 transition-opacity hover:text-red-400 group-hover:opacity-100"
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
