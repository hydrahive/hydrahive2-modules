import { Bot, CheckSquare, MessageSquare, PenTool } from "lucide-react"
import { countByStatus, filterIdeas, groupByProject, openCount, relativeTime } from "../ideaView"
import type { T } from "../texts.de"
import { STATUSES, type IdeaListItem, type ProjectFilter, type ProjectRef, type StatusFilter } from "../types"
import { BADGE, BUTTON, LABEL, SELECT, STATUS_BADGE } from "./styles"

interface Props {
  ideas: IdeaListItem[]
  projects: ProjectRef[]
  project: ProjectFilter
  status: StatusFilter
  activeId: string | null
  loading: boolean
  locale: string
  t: T
  onProject: (project: ProjectFilter) => void
  onStatus: (status: StatusFilter) => void
  onSelect: (id: string) => void
}

const CHIP = "inline-flex items-center gap-1.5 rounded-[6px] border px-2 py-1 text-[11px] font-semibold transition-colors " +
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/40"
const CHIP_ON = "border-[#69d7ff]/60 bg-[#69d7ff]/15 text-[#c8f2ff]"
const CHIP_OFF = "border-[rgb(var(--hh-s-rand,52_66_92))] bg-transparent text-[#9aa7bc] hover:border-[rgb(var(--hh-s-rand-hover,70_97_127))] hover:text-[#c8d2df]"

function Row({ idea, active, locale, t, onSelect }: {
  idea: IdeaListItem; active: boolean; locale: string; t: T; onSelect: (id: string) => void
}) {
  return (
    <button type="button" onClick={() => onSelect(idea.id)} aria-current={active ? "true" : undefined}
      className={`block w-full rounded-[6px] border px-3 py-2.5 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#69d7ff]/40 ${
        active ? "border-[#69d7ff]/55 bg-[#69d7ff]/10" : "border-transparent hover:border-[rgb(var(--hh-s-rand,52_66_92))] hover:bg-[rgb(var(--hh-s-innen,36_48_71))]"}`}>
      <span className="flex items-start justify-between gap-2">
        <span className="min-w-0 break-words text-[13px] font-semibold leading-snug text-[#e8eef8]">{idea.title}</span>
        <span className={`${BADGE} ${STATUS_BADGE[idea.status]}`}>{t(`status_${idea.status}`)}</span>
      </span>
      {idea.body_preview && <span className="mt-1 line-clamp-2 block text-[12px] leading-snug text-[#9aa7bc]">{idea.body_preview}</span>}
      <span className="mt-1.5 flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[11px] text-[#9aa7bc]">
        {idea.origin === "agent" && <span className="inline-flex items-center gap-1 text-[#9fe6ff]"><Bot size={11} aria-hidden />{t("origin_agent")}</span>}
        {idea.note_count > 0 && (
          <span className="inline-flex items-center gap-1" title={t("notes_count", { n: idea.note_count })}>
            <MessageSquare size={11} aria-hidden /><span className="sr-only">{t("notes_count", { n: idea.note_count })}</span>
            <span aria-hidden>{idea.note_count}</span>
          </span>
        )}
        {idea.task_id && <span title={t("linked_task")}><CheckSquare size={11} aria-label={t("linked_task")} /></span>}
        {idea.board_id !== null && <span title={t("linked_board")}><PenTool size={11} aria-label={t("linked_board")} /></span>}
        <span className="ml-auto shrink-0">{relativeTime(idea.updated_at, locale)}</span>
      </span>
    </button>
  )
}

/** Liste mit Projekt- und Statusfilter. Bei „Alle Projekte“ nach Projekt gruppiert. */
export function IdeaList({ ideas, projects, project, status, activeId, loading, locale, t, onProject, onStatus, onSelect }: Props) {
  const counts = countByStatus(ideas, project)
  const total = STATUSES.reduce((sum, key) => sum + counts[key], 0)
  const visible = filterIdeas(ideas, project, status)
  const nameOf = (id: string | null) =>
    id === null ? t("no_project") : projects.find((item) => item.id === id)?.name ?? t("unknown_project")
  const groups = project === "all"
    ? groupByProject(visible, projects)
    : [{ projectId: null, name: null, known: true, ideas: visible }]
  const chips: Array<[StatusFilter, string, number]> = [
    ["open", t("filter_open"), openCount(counts)], ["all", t("filter_all"), total],
    ...STATUSES.map((key): [StatusFilter, string, number] => [key, t(`status_${key}`), counts[key]]),
  ]

  return (
    <section className="flex min-h-0 flex-col gap-3">
      <div>
        <label htmlFor="idea-filter-project" className={LABEL}>{t("filter_project_label")}</label>
        <select id="idea-filter-project" value={project} onChange={(event) => onProject(event.target.value)} className={SELECT}>
          <option value="all">{t("all_projects")}</option>
          <option value="none">{t("no_project")}</option>
          {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {chips.map(([key, label, count]) => (
          <button key={key} type="button" onClick={() => onStatus(key)} aria-pressed={status === key}
            className={`${CHIP} ${status === key ? CHIP_ON : CHIP_OFF} ${count === 0 && status !== key ? "opacity-60" : ""}`}>
            {label}<span className="tabular-nums text-[10px] opacity-80">{count}</span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="space-y-2">{[1, 2, 3].map((n) => <div key={n} className="h-16 animate-pulse rounded-[6px] bg-[rgb(var(--hh-s-innen,36_48_71))]" />)}</div>
      ) : ideas.length === 0 ? (
        <div className="rounded-[8px] border border-dashed border-[rgb(var(--hh-s-rand,52_66_92))] px-4 py-8 text-center">
          <p className="text-sm font-semibold text-[#e8eef8]">{t("empty_title")}</p>
          <p className="mx-auto mt-1.5 max-w-xs text-xs leading-relaxed text-[#9aa7bc]">{t("empty_hint")}</p>
        </div>
      ) : visible.length === 0 ? (
        <div className="rounded-[8px] border border-dashed border-[rgb(var(--hh-s-rand,52_66_92))] px-4 py-6 text-center">
          <p className="text-xs text-[#9aa7bc]">{t("empty_filtered")}</p>
          <button type="button" onClick={() => { onProject("all"); onStatus("all") }} className={`${BUTTON} mt-3`}>{t("empty_filtered_action")}</button>
        </div>
      ) : (
        <div className="min-h-0 space-y-3 overflow-y-auto pr-1">
          {groups.map((group) => (
            <div key={group.projectId ?? "none"}>
              {project === "all" && (
                <h3 className="mb-1 flex items-center justify-between px-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-[#9aa7bc]">
                  <span className="truncate">{nameOf(group.projectId)}</span><span className="tabular-nums">{group.ideas.length}</span>
                </h3>
              )}
              <ul className="space-y-1">
                {group.ideas.map((idea) => (
                  <li key={idea.id}>
                    <Row idea={idea} active={idea.id === activeId} locale={locale} t={t} onSelect={onSelect} />
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
