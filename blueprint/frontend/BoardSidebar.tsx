import { useState } from "react"
import { Plus, Trash2, PenTool, Sparkles } from "lucide-react"
import { HelpButton } from "@/i18n/HelpButton"
import { filterBoards, projectName } from "./boardView"
import { BUTTON, FIELD, RAND, SELECT } from "./styles"
import type { T } from "./texts.de"
import type { BoardListItem, ProjectFilter, ProjectRef } from "./types"
import leerBild from "./assets/leer.webp"

interface Props {
  boards: BoardListItem[]
  projects: ProjectRef[]
  project: ProjectFilter
  activeId: number | null
  t: T
  onProject: (project: ProjectFilter) => void
  onSelect: (id: number) => void
  onCreate: (name: string) => void
  onDelete: (id: number) => void
}

/** Ganz links: Liste der Boards, Projektfilter und Neu-anlegen. */
export function BoardSidebar({ boards, projects, project, activeId, t, onProject, onSelect, onCreate, onDelete }: Props) {
  const [adding, setAdding] = useState(false)
  const [name, setName] = useState("")
  const shown = filterBoards(boards, project)

  const submit = () => {
    const n = name.trim()
    if (!n) return
    onCreate(n)
    setName("")
    setAdding(false)
  }

  return (
    <div className={`flex w-52 shrink-0 flex-col border-r ${RAND} bg-[rgb(var(--hh-s-tief,13_20_32)/0.6)]`}>
      <div className={`flex items-center gap-2 border-b ${RAND} px-3 py-3`}>
        <PenTool size={16} className="text-[#c8d2df]" />
        <span className="text-sm font-semibold text-[#e8eef8]">{t("boards")}</span>
        <HelpButton topic="blueprint" />
        <button
          onClick={() => setAdding((v) => !v)}
          className="ml-auto rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39))] p-1.5 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
          title={t("board_new")}
          aria-label={t("board_new")}
        >
          <Plus size={14} />
        </button>
      </div>

      {projects.length > 0 && (
        <div className={`border-b ${RAND} p-2`}>
          <select value={project} onChange={(e) => onProject(e.target.value)}
            aria-label={t("project_filter_label")} title={t("project_filter_label")} className={SELECT}>
            <option value="all">{t("all_projects")}</option>
            <option value="none">{t("no_project")}</option>
            {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select>
        </div>
      )}

      {adding && (
        <div className={`border-b ${RAND} p-2`}>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder={t("board_name_placeholder")}
            maxLength={120}
            autoFocus
            className={FIELD}
          />
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-2">
        {boards.length === 0 ? (
          <div className="flex flex-col items-center gap-2 py-4 text-center">
            <img src={leerBild} alt="" loading="lazy" draggable={false}
              className="mx-auto h-20 w-20 select-none object-contain" />
            <p className="text-xs text-[#9aa7bc]">{t("boards_empty")}</p>
          </div>
        ) : shown.length === 0 ? (
          <div className="space-y-2 py-4 text-center text-xs text-[#9aa7bc]">
            <p>{t("boards_empty_filtered")}</p>
            <button type="button" onClick={() => onProject("all")} className={BUTTON}>{t("boards_show_all")}</button>
          </div>
        ) : (
          <ul className="space-y-1">
            {shown.map((b) => (
              <li key={b.id}>
                <div
                  className={`group flex items-center gap-2 rounded-lg px-2.5 py-2 text-sm transition-colors ${
                    activeId === b.id
                      ? "bg-sky-500/15 text-sky-200"
                      : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
                  }`}
                >
                  <button onClick={() => onSelect(b.id)} className="flex min-w-0 flex-1 flex-col text-left">
                    <span className="truncate">{b.name}</span>
                    {project === "all" && b.project_id !== null && (
                      <span className="truncate text-[10px] text-[#9aa7bc]">{projectName(b.project_id, projects, t)}</span>
                    )}
                  </button>
                  {b.has_proposal && (
                    <span title={t("has_proposal")} className="shrink-0 text-[#69d7ff]">
                      <Sparkles size={13} aria-hidden /><span className="sr-only">{t("has_proposal")}</span>
                    </span>
                  )}
                  <button
                    onClick={() => onDelete(b.id)}
                    className={"shrink-0 text-[#9aa7bc] opacity-0 transition-opacity hover:text-red-400 " +
                      "focus-visible:opacity-100 group-hover:opacity-100"}
                    title={t("board_delete")}
                    aria-label={t("board_delete")}
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
