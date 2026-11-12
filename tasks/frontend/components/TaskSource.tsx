import { Lightbulb } from "lucide-react"
import { Link } from "react-router-dom"
import type { Task } from "../types"

/** Rückverweis auf das, woraus der Task entstanden ist (Task ef94594a).
 *  Bisher gibt es nur Ideen aus dem Modul scratchpad; andere Arten zeigen nichts. */
export function TaskSource({ task }: { task: Pick<Task, "source_kind" | "source_id"> }) {
  if (task.source_kind !== "idea" || !task.source_id) return null
  return (
    <Link
      to={`/scratchpad?idea=${encodeURIComponent(task.source_id)}`}
      title="Zur Idee, aus der dieser Task entstanden ist"
      className="ml-5 mt-0.5 inline-flex items-center gap-1 text-[10px] text-[#9aa7bc] hover:text-[#69d7ff]"
    >
      <Lightbulb size={10} aria-hidden /> Aus Idee
    </Link>
  )
}
