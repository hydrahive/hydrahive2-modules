import { useState, type CSSProperties } from "react"
import { CheckSquare, Plus } from "lucide-react"
import { useTranslation } from "react-i18next"
import { useTasks } from "../useTasks"
import type { TaskStatus, TaskPriority } from "../types"
import { NewTaskForm } from "./NewTaskForm"
import { TaskRow } from "./TaskRow"

const FILTERS: Array<TaskStatus | "all"> = ["all", "open", "in_progress", "done", "cancelled"]

export function TaskPanel() {
  const { t } = useTranslation("tasks")
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
          {FILTERS.map((value) => (
            <button
              key={value}
              onClick={() => setFilter(value)}
              className={`px-2 py-0.5 rounded text-[10px] whitespace-nowrap transition-colors
                ${filter === value
                  ? "bg-[#69d7ff]/20 text-[#69d7ff]"
                  : "text-[#9aa7bc] hover:text-[#c8d2df]"
                }`}
            >
              {value === "all" ? t("filter_all") : t(`status_${value}`)}
            </button>
          ))}
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="flex-shrink-0 text-[#9aa7bc] hover:text-[#69d7ff] transition-colors"
          title={t("create")}
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
          <p className="text-[11px] text-[#9aa7bc] px-3 py-2">{t("loading")}</p>
        )}
        {error !== null && (
          <p className="text-[11px] text-rose-500 px-3 py-2">{error || t("load_error")}</p>
        )}
        {!loading && tasks.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full gap-2 py-8">
            <CheckSquare size={24} className="text-[#46617f]" />
            <p className="text-[11px] text-[#9aa7bc]">{t("empty")}</p>
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
