import { CheckSquare } from "lucide-react"
import type { T, TextKey } from "../texts.de"
import type { IdeaTaskRef } from "../types"
import { BADGE, BUTTON } from "./styles"

interface Props {
  task: IdeaTaskRef | null
  /** Ist das Tasks-Modul installiert? Ohne Modul gibt es keinen Knopf. */
  installed: boolean
  busy: boolean
  t: T
  onCreate: () => void
}

const STATUS_KEYS: Record<string, TextKey> = {
  open: "task_status_open", in_progress: "task_status_in_progress", done: "task_status_done", cancelled: "task_status_cancelled",
}

/** Der aus der Idee entstandene Task: Titel, Status, Kurz-ID. Ohne Task der Knopf „Task anlegen“. */
export function IdeaTask({ task, installed, busy, t, onCreate }: Props) {
  if (!task && !installed) return null
  const linked = task !== null && !task.missing
  const statusKey = task?.status ? STATUS_KEYS[task.status] : undefined

  return (
    <section aria-labelledby="idea-task-title" className="space-y-2">
      <h3 id="idea-task-title" className="text-sm font-bold text-[#e8eef8]">{t("task_title")}</h3>
      {linked ? (
        <div className="flex flex-wrap items-center gap-2 rounded-[6px] border border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))] px-3 py-2">
          <CheckSquare size={14} aria-hidden className="shrink-0 text-[#69d7ff]" />
          <span className="min-w-0 flex-1 break-words text-[13px] font-semibold text-[#e8eef8]">{task.title}</span>
          <span className={`${BADGE} border-[rgb(var(--hh-s-rand-hover,70_97_127))] text-[#c8d2df]`}>{statusKey ? t(statusKey) : task.status}</span>
          <span className="font-mono text-[11px] text-[#9aa7bc]">{task.short_id}</span>
        </div>
      ) : (
        <>
          {task?.missing && <p className="text-xs text-[#9aa7bc]">{t("task_missing")}</p>}
          {installed && (
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" onClick={onCreate} disabled={busy} className={BUTTON}>
                <CheckSquare size={13} aria-hidden />{t("task_create")}
              </button>
              <p className="min-w-0 flex-1 text-[11px] text-[#9aa7bc]">{t("task_hint")}</p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
