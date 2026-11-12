import { CheckSquare } from "lucide-react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { useTasks } from "../useTasks"
import type { Task } from "../types"

const PRIORITY_DOT: Record<Task["priority"], string> = {
  high:   "bg-rose-400 shadow-[0_0_4px_rgba(251,113,133,0.6)]",
  medium: "bg-yellow-300",
  low:    "bg-[rgb(var(--hh-s-rand-hover,70_97_127))]",
}

interface Props {
  onPrompt: (text: string) => void
}

export function TaskBuddyBox({ onPrompt }: Props) {
  const { t } = useTranslation("tasks")
  const { tasks, complete } = useTasks({ status: "open", pollMs: 8000 })
  const inProgress = tasks.filter((task) => task.status === "in_progress")
  const open = tasks.filter((task) => task.status === "open")
  const visible = [...inProgress, ...open].slice(0, 6)

  return (
    <CollapsibleBox
      boxId="buddy-tasks"
      icon={<CheckSquare size={14} className="text-yellow-300" />}
      title={t("title")}
      color="250 204 21"
      defaultCollapsed={false}
      className="w-60"
      headerRight={
        <span className="text-[10px] text-[#9aa7bc]">
          {tasks.length > 0 ? t("buddy_count", { n: tasks.length }) : t("buddy_none")}
        </span>
      }
    >
      <div className="p-2 space-y-1">
        {visible.length === 0 ? (
          <p className="text-[11px] text-[#9aa7bc] px-1 py-0.5">{t("buddy_empty")}</p>
        ) : (
          visible.map((task) => (
            <div key={task.id} className="relative flex items-start gap-1.5 group">
              <button
                onClick={() => complete(task.id)}
                className="mt-0.5 flex-shrink-0 w-3.5 h-3.5 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] hover:border-yellow-400/50 hover:bg-yellow-400/10 transition-colors"
                title={t("mark_done")}
              />
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1">
                  <div className={`flex-shrink-0 w-1.5 h-1.5 rounded-full ${PRIORITY_DOT[task.priority]}`} />
                  <span
                    className="text-[11px] text-[#c8d2df] truncate cursor-pointer hover:text-yellow-200 transition-colors"
                    onClick={() => onPrompt(t("prompt_status", { title: task.title }))}
                  >
                    {task.title}
                  </span>
                </div>
                {task.status === "in_progress" && (
                  <span className="text-[9px] text-amber-400 ml-3">{t("buddy_in_progress")}</span>
                )}
              </div>

              {/* Hover-Tooltip mit Beschreibung */}
              {task.description && (
                <div className="
                  pointer-events-none absolute left-0 bottom-full mb-1.5 z-50 w-52
                  opacity-0 group-hover:opacity-100 transition-opacity duration-150
                  bg-[rgb(var(--hh-s-box,21_28_43))] border border-yellow-400/20 rounded-lg px-2.5 py-2
                  shadow-[0_0_12px_rgba(234,179,8,0.15)]
                ">
                  <p className="text-[10px] text-yellow-200/80 font-medium mb-0.5 truncate">{task.title}</p>
                  <p className="text-[10px] text-[#c8d2df] leading-relaxed line-clamp-4">{task.description}</p>
                </div>
              )}
            </div>
          ))
        )}
        {tasks.length > 6 && (
          <p className="text-[10px] text-[#9aa7bc] px-1 pt-1">
            {t("buddy_more", { n: tasks.length - 6 })} →{" "}
            <button
              onClick={() => onPrompt(t("prompt_all"))}
              className="text-yellow-400 hover:text-yellow-300 underline"
            >
              {t("buddy_show_all")}
            </button>
          </p>
        )}
        <button
          onClick={() => onPrompt(t("prompt_overview"))}
          className="w-full text-left text-xs px-2 py-1.5 mt-1 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] hover:border-yellow-400/20 hover:bg-yellow-400/[3%] text-[#c8d2df] hover:text-yellow-300 transition-all"
        >
          ✦ {t("buddy_discuss")}
        </button>
      </div>
    </CollapsibleBox>
  )
}
