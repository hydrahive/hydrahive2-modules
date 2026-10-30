import { useState, type CSSProperties } from "react"
import { CheckSquare, Plus, Trash2 } from "lucide-react"
import { useTasks } from "../useTasks"
import type { Task, TaskStatus, TaskPriority } from "../types"
import { TaskHistory } from "./TaskHistory"

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

const FILTER_OPTIONS: Array<{ value: TaskStatus | "all"; label: string }> = [
  { value: "all",        label: "Alle" },
  { value: "open",       label: "Offen" },
  { value: "in_progress",label: "In Arbeit" },
  { value: "done",       label: "Erledigt" },
  { value: "cancelled",  label: "Abgebrochen" },
]

interface NewTaskFormProps {
  onSave: (title: string, priority: TaskPriority) => Promise<void>
  onCancel: () => void
}

function NewTaskForm({ onSave, onCancel }: NewTaskFormProps) {
  const [title, setTitle] = useState("")
  const [priority, setPriority] = useState<TaskPriority>("medium")
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!title.trim()) return
    setSaving(true)
    try {
      await onSave(title.trim(), priority)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="p-2 border-b border-[rgb(var(--hh-s-rand,42_54_75))] space-y-1.5">
      <input
        autoFocus
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Aufgabentitel…"
        className="w-full bg-[rgb(var(--hh-s-innen,17_24_39)/0.6)] border border-[rgb(var(--hh-s-rand,42_54_75))] rounded px-2 py-1 text-xs text-[#e8eef8] placeholder:text-[#9aa7bc] focus:outline-none focus:border-[#69d7ff]/50"
      />
      <div className="flex items-center gap-1.5">
        <select
          value={priority}
          onChange={(e) => setPriority(e.target.value as TaskPriority)}
          className="bg-[rgb(var(--hh-s-innen,17_24_39)/0.6)] border border-[rgb(var(--hh-s-rand,42_54_75))] rounded px-1.5 py-1 text-[11px] text-[#c8d2df] focus:outline-none"
        >
          <option value="high">! Hoch</option>
          <option value="medium">~ Mittel</option>
          <option value="low">↓ Niedrig</option>
        </select>
        <div className="flex-1" />
        <button type="button" onClick={onCancel} className="text-[11px] text-[#9aa7bc] hover:text-[#c8d2df] px-2 py-1">
          Abbrechen
        </button>
        <button
          type="submit"
          disabled={saving || !title.trim()}
          className="text-[11px] bg-[#69d7ff]/80 hover:bg-[#69d7ff]/80 disabled:opacity-40 text-white px-2.5 py-1 rounded transition-colors"
        >
          {saving ? "…" : "Hinzufügen"}
        </button>
      </div>
    </form>
  )
}

interface TaskRowProps {
  task: Task
  onStatusChange: (id: string, status: TaskStatus) => void
  onDelete: (id: string) => void
}

function TaskRow({ task, onStatusChange, onDelete }: TaskRowProps) {
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

export function TaskPanel() {
  const [filter, setFilter] = useState<TaskStatus | "all">("all")
  const [showForm, setShowForm] = useState(false)

  const { tasks, loading, error, createTask, updateTask, deleteTask } = useTasks({
    status: filter === "all" ? undefined : filter,
    pollMs: 5000,
  })

  async function handleCreate(title: string, priority: TaskPriority) {
    await createTask({ title, priority })
    setShowForm(false)
  }

  async function handleStatusChange(id: string, status: TaskStatus) {
    await updateTask(id, { status })
  }

  return (
    <div className="flex flex-col h-full" style={{ "--c": "138,92,246" } as CSSProperties}>
      <div className="flex items-center gap-1.5 px-2.5 py-1.5 border-b border-[rgb(var(--hh-s-rand,42_54_75))]">
        <CheckSquare size={12} className="text-[#69d7ff] flex-shrink-0" />
        <div className="flex gap-0.5 flex-1 overflow-x-auto">
          {FILTER_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-2 py-0.5 rounded text-[10px] whitespace-nowrap transition-colors
                ${filter === value
                  ? "bg-[#69d7ff]/20 text-[#69d7ff]"
                  : "text-[#9aa7bc] hover:text-[#c8d2df]"
                }`}
            >
              {label}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex-shrink-0 text-[#9aa7bc] hover:text-[#69d7ff] transition-colors"
          title="Neuen Task anlegen"
        >
          <Plus size={13} />
        </button>
      </div>

      {showForm && (
        <NewTaskForm
          onSave={handleCreate}
          onCancel={() => setShowForm(false)}
        />
      )}

      <div className="flex-1 min-h-0 overflow-y-auto py-1">
        {loading && tasks.length === 0 && (
          <p className="text-[11px] text-[#9aa7bc] px-3 py-2">Laden…</p>
        )}
        {error && (
          <p className="text-[11px] text-rose-500 px-3 py-2">{error}</p>
        )}
        {!loading && tasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-2 py-8">
            <CheckSquare size={24} className="text-[#46617f]" />
            <p className="text-[11px] text-[#9aa7bc]">Keine Aufgaben</p>
          </div>
        )}
        {tasks.map((task) => (
          <TaskRow
            key={task.id}
            task={task}
            onStatusChange={handleStatusChange}
            onDelete={deleteTask}
          />
        ))}
      </div>
    </div>
  )
}
