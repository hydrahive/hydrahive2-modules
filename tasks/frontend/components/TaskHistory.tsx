import { useState } from "react"
import { History } from "lucide-react"
import { tasksApi } from "../api"
import type { TaskVersion } from "../types"

/** Aufklappbarer Verlauf früherer Fassungen eines Tasks (Task df2f2eb2).
 *  Lädt erst beim Aufklappen; bei 0 Fassungen wird nichts angezeigt. */
export function TaskHistory({ taskId, count }: { taskId: string; count: number }) {
  const [open, setOpen] = useState(false)
  const [versions, setVersions] = useState<TaskVersion[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  if (count <= 0) return null

  async function toggle() {
    const next = !open
    setOpen(next)
    if (next && versions === null) {
      try {
        setVersions(await tasksApi.history(taskId))
      } catch (e) {
        setError(e instanceof Error ? e.message : "Verlauf nicht ladbar")
      }
    }
  }

  return (
    <div className="ml-5 mt-0.5">
      <button onClick={() => void toggle()} className="inline-flex items-center gap-1 text-[10px] text-zinc-500 hover:text-zinc-300">
        <History size={10} /> Verlauf ({count})
      </button>
      {open && (
        <div className="mt-1 space-y-1.5 border-l border-white/[8%] pl-2">
          {error && <p className="text-[10px] text-rose-400">{error}</p>}
          {versions === null && !error && <p className="text-[10px] text-zinc-600">lädt…</p>}
          {versions?.map((v, i) => (
            <div key={`${v.changed_at}-${i}`} className="text-[10px]">
              <div className="text-zinc-500">
                {v.changed_at.replace("T", " ").slice(0, 16)}
                {v.source === "restored" ? " · aus Chat-Verlauf wiederhergestellt" : ""}
              </div>
              {v.title && <div className="text-zinc-400">{v.title}</div>}
              <p className="whitespace-pre-wrap text-zinc-600">{v.description}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
