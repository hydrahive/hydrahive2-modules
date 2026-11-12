import { Trash2 } from "lucide-react"
import type { Task, TaskStatus, TaskPriority } from "../types"
import { TaskHistory } from "./TaskHistory"
import { TaskSource } from "./TaskSource"

const STATUS_LABEL: Record<TaskStatus, string> = {
  open:        "Offen",
  in_progress: "In Arbeit",
  done:        "Erledigt",
  cancelled:   "Abgebrochen",
}

const STATUS_COLOR: Record<TaskStatus, string> = {
  open:        "text-[#c8d2df]",
  in_progress: "text-amber-400",
  done:        "text-emerald-400",
  cancelled:   "text-[#9aa7bc]",
}

const PRIORITY_BADGE: Record<TaskPriority, string> = {
  high:   "text-rose-400 bg-rose-500/10",
  medium: "text-[#c8d2df] bg-[rgb(var(--hh-s-rand-hover,70_97_127)/0.1)]",
  low:    "text-[#9aa7bc] bg-[rgb(var(--hh-s-hebung,27_37_54)/0.1)]",
}

const PRIORITY_LABEL: Record<TaskPriority, string> = {
  high: "!", medium: "~", low: "↓",
}

interface TaskRowProps {
  task: Task
  onStatusChange: (id: string, status: TaskStatus) => void
  onDelete: (id: string) => void
}

export function TaskRow({ task, onStatusChange, onDelete }: TaskRowProps) {
  const isDone = task.status === "done" || task.status === "cancelled"

  return (
    <div className={`flex items-start gap-2 px-2 py-1.5 group hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] rounded transition-colors ${isDone ? "opacity-50" : ""}`}>
      <button
        onClick={() => onStatusChange(task.id, isDone ? "open" : "done")}
        className={`flex-shrink-0 mt-0.5 w-3.5 h-3.5 rounded border transition-colors
          ${isDone
            ? "bg-emerald-500/20 border-emerald-500/40"
            : "border-[rgb(var(--hh-s-rand,42_54_75))] hover:border-[#69d7ff]/50 hover:bg-[#69d7ff]/10"
          }`}
        title={isDone ? "Wieder öffnen" : "Als erledigt markieren"}
      >
        {isDone && <span className="flex items-center justify-center w-full h-full text-[8px] text-emerald-400">✓</span>}
      </button>

      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center px-1 rounded text-[9px] font-mono ${PRIORITY_BADGE[task.priority]}`}>
            {PRIORITY_LABEL[task.priority]}
          </span>
          <span className={`text-[11px] truncate ${isDone ? "line-through text-[#9aa7bc]" : "text-[#c8d2df]"}`}>
            {task.title}
          </span>
        </div>
        {task.description && (
          <p className="text-[10px] text-[#9aa7bc] mt-0.5 truncate ml-5">{task.description}</p>
        )}
        <TaskHistory taskId={task.id} count={task.history_count ?? 0} />
        <TaskSource task={task} />
      </div>

      <div className="flex items-center gap-1 flex-shrink-0">
        <div className="opacity-0 group-hover:opacity-100 transition-opacity">
          <select
            value={task.status}
            onChange={(e) => onStatusChange(task.id, e.target.value as TaskStatus)}
            onClick={(e) => e.stopPropagation()}
            className={`bg-transparent border-0 text-[10px] focus:outline-none cursor-pointer ${STATUS_COLOR[task.status]}`}
          >
            {(Object.entries(STATUS_LABEL) as [TaskStatus, string][]).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => onDelete(task.id)}
          className="text-[#9aa7bc] hover:text-rose-400 transition-colors"
          title="Task löschen"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  )
}
