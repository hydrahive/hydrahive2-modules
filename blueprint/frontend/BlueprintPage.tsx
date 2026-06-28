import "@xyflow/react/dist/style.css"
import { useEffect, useState } from "react"
import { blueprintApi } from "./api"
import { BoardSidebar } from "./BoardSidebar"
import { BoardEditor } from "./BoardEditor"
import type { BoardMeta } from "./types"

export function BlueprintPage() {
  const [boards, setBoards] = useState<BoardMeta[]>([])
  const [activeId, setActiveId] = useState<number | null>(null)

  const reload = () =>
    blueprintApi.list().then((bs) => {
      setBoards(bs)
      // Falls aktives Board weg ist, erstes wählen.
      setActiveId((cur) => (cur && bs.some((b) => b.id === cur) ? cur : bs[0]?.id ?? null))
    }).catch(() => {})

  useEffect(() => { reload() }, [])

  const handleCreate = (name: string) => {
    blueprintApi.create(name).then((b) => {
      setBoards((bs) => [b, ...bs])
      setActiveId(b.id)
    }).catch(() => {})
  }

  const handleDelete = (id: number) => {
    if (!confirm("Dieses Board wirklich löschen?")) return
    blueprintApi.remove(id).then(() => {
      setBoards((bs) => bs.filter((b) => b.id !== id))
      setActiveId((cur) => (cur === id ? null : cur))
    }).catch(() => {})
  }

  const active = boards.find((b) => b.id === activeId)

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      <BoardSidebar
        boards={boards}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreate}
        onDelete={handleDelete}
      />
      {active ? (
        <BoardEditor boardId={active.id} boardName={active.name} />
      ) : (
        <div className="flex flex-1 items-center justify-center">
          <p className="text-sm text-zinc-600">
            Board links wählen oder „+" für ein neues.
          </p>
        </div>
      )}
    </div>
  )
}
