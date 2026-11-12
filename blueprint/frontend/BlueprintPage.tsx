import "@xyflow/react/dist/style.css"
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { useSearchParams } from "react-router-dom"
import { projectsApi } from "@/features/projects/api"
import { blueprintApi } from "./api"
import { BoardSidebar } from "./BoardSidebar"
import { BoardEditor } from "./BoardEditor"
import { errorText, linkedBoard, mergeBoard, pickBoard, projectShowing } from "./boardView"
import { BUTTON, ERROR_BOX } from "./styles"
import type { T } from "./texts.de"
import type { Board, BoardListItem, ProjectFilter, ProjectRef } from "./types"

/** Seite „Blueprint“ unter /blueprint. /blueprint?board=<id> öffnet ein Board direkt; die Adresse folgt der Auswahl. */
export function BlueprintPage() {
  const { t: translate, i18n } = useTranslation("blueprint")
  const t: T = useCallback((key, vars) => String(translate(key, vars)), [translate])
  const [boards, setBoards] = useState<BoardListItem[] | null>(null)
  const [projects, setProjects] = useState<ProjectRef[]>([])
  const [project, setProject] = useState<ProjectFilter>("all")
  const [loadFailed, setLoadFailed] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)
  const [params, setParams] = useSearchParams()
  const wanted = linkedBoard(params.get("board"))
  const known = useRef<Set<number> | null>(null)

  const reload = useCallback(async () => {
    try {
      const list = await blueprintApi.list()
      known.current = new Set(list.map((board) => board.id))
      setBoards(list)
      setLoadFailed(false)
    } catch {
      setLoadFailed(true)
    }
  }, [])

  // Beim Öffnen laden, und erneut, wenn ein Verweis auf ein Board zeigt, das die Liste noch nicht kennt
  // (zum Beispiel ein Board, das der Agent gerade angelegt hat).
  useEffect(() => {
    if (known.current === null || (wanted !== null && !known.current.has(wanted))) void reload()
  }, [wanted, reload])

  useEffect(() => {
    // Ohne Projektliste bleibt die Seite benutzbar: Boards ohne Projekt gehen immer.
    projectsApi.list()
      .then((list) => setProjects(list.map((item) => ({ id: item.id, name: item.name }))))
      .catch(() => setProjects([]))
    const refresh = () => { if (document.visibilityState === "visible") void reload() }
    document.addEventListener("visibilitychange", refresh)
    return () => document.removeEventListener("visibilitychange", refresh)
  }, [reload])

  const open = useCallback((id: number | null) => {
    setParams((current) => {
      const next = new URLSearchParams(current)
      if (id === null) next.delete("board")
      else next.set("board", String(id))
      return next
    }, { replace: true })
  }, [setParams])

  const activeId = boards ? pickBoard(boards, wanted) : null
  const active = boards?.find((board) => board.id === activeId)
  // Wechselt das offene Board (Klick, Verweis, Löschen), öffnet sich der Projektfilter so weit, dass es in der Liste steht.
  const [shownFor, setShownFor] = useState<number | null>(null)
  if (active && shownFor !== active.id) {
    setShownFor(active.id)
    setProject(projectShowing(active, project))
  }

  const onBoard = useCallback((board: Board) => {
    setBoards((list) => (list ? mergeBoard(list, board) : list))
  }, [])

  async function act(run: () => Promise<void>) {
    setActionError(null)
    try {
      await run()
    } catch (problem) {
      setActionError(errorText(problem, t))
    }
  }

  const handleCreate = (name: string) => act(async () => {
    // Ein neues Board gehört zu dem Projekt, dessen Boards gerade gezeigt werden.
    const inProject = project === "all" || project === "none" ? null : project
    const board = await blueprintApi.create(name, inProject)
    known.current?.add(board.id)
    setBoards((list) => [{ ...board, has_proposal: false }, ...(list ?? [])])
    open(board.id)
  })

  const handleDelete = (id: number) => {
    if (!confirm(t("delete_confirm"))) return
    void act(async () => {
      await blueprintApi.remove(id)
      known.current?.delete(id)
      setBoards((list) => (list ?? []).filter((board) => board.id !== id))
      if (wanted === id) open(null)
    })
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      <BoardSidebar boards={boards ?? []} projects={projects} project={project} activeId={activeId} t={t}
        onProject={setProject} onSelect={open} onCreate={(name) => void handleCreate(name)} onDelete={handleDelete} />
      <div className="flex min-w-0 flex-1 flex-col">
        {loadFailed && (
          <div role="alert" className={`${ERROR_BOX} m-2 flex flex-wrap items-center gap-3`}>
            <span>{t("boards_load_error")}</span>
            <button type="button" onClick={() => void reload()} className={BUTTON}>{t("retry")}</button>
          </div>
        )}
        {actionError && <p role="alert" className={`${ERROR_BOX} m-2`}>{actionError}</p>}
        {boards !== null && wanted !== null && wanted !== activeId && (
          <p role="status" className={`${ERROR_BOX} m-2`}>{t("link_missing")}</p>
        )}
        {active ? (
          <BoardEditor boardId={active.id} boardName={active.name} projects={projects} locale={i18n.language} t={t}
            onBoard={onBoard} />
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <p className="text-sm text-[#9aa7bc]">
              {boards === null && !loadFailed ? t("status_loading") : t("pick_board")}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
