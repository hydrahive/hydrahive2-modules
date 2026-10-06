// Arbeitsplatz: Kopfleiste · Navigator | Editor | Kontext · Statusleiste (Spec §4).
import { useCallback, useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { ArrowLeft, FolderOpen, Maximize2, Minimize2, PanelLeft, PanelRight } from "lucide-react"
import { lastPlace } from "../lastPlace"
import { allScenes, findScene, type Book } from "../model"
import type { Versions } from "../serverBook"
import { useBook } from "../useBook"
import { ConflictDialog } from "./ConflictDialog"
import { ContextPanel, type ContextTab } from "./ContextPanel"
import { Navigator } from "./Navigator"
import { SceneEditor } from "./SceneEditor"
import { StatusBar } from "./StatusBar"

const LAYOUT_KEY = "storyteller.layout"
interface Layout { left: boolean; right: boolean }
const readLayout = (): Layout => {
  try { return { left: true, right: true, ...JSON.parse(localStorage.getItem(LAYOUT_KEY) ?? "{}") } } catch { return { left: true, right: true } }
}

interface Props {
  projectId: string; projectName: string; initial: Book; versions: Versions; initialSceneId?: string; onClose: () => void
}

export function Workspace({ projectId, projectName, initial, versions, initialSceneId, onClose }: Props) {
  const { t } = useTranslation("storyteller")
  const state = useBook(projectId, initial, versions)
  const { book } = state
  const first = allScenes(book)[0]?.scene.id ?? ""
  const [wanted, setSceneId] = useState(initialSceneId ?? first)
  // Gewünschte Szene weg (gelöscht, Konflikt neu geladen)? Dann die erste zeigen.
  const sceneId = findScene(book, wanted) ? wanted : first
  const [layout, setLayout] = useState<Layout>(readLayout)
  const [focus, setFocus] = useState(false)
  const [tab, setTab] = useState<ContextTab>("scene")
  const [entityId, setEntityId] = useState<string | null>(null)
  const editorRef = useRef<Editor | null>(null)
  const current = findScene(book, sceneId)

  useEffect(() => { localStorage.setItem(LAYOUT_KEY, JSON.stringify(layout)) }, [layout])
  useEffect(() => { if (sceneId) lastPlace.set(projectId, book.id, sceneId) }, [projectId, book.id, sceneId])

  const { flush } = state
  const openScene = useCallback((id: string) => { void flush(); setSceneId(id) }, [flush])
  const close = useCallback(async () => { await flush(); onClose() }, [flush, onClose])
  const openEntity = useCallback((id: string) => { setEntityId(id); setTab("entity"); setLayout((l) => ({ ...l, right: true })) }, [])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.ctrlKey || e.metaKey
      if (mod && e.shiftKey && e.key.toLowerCase() === "f") { e.preventDefault(); setFocus((f) => !f) }
      else if (mod && !e.shiftKey && e.key.toLowerCase() === "b") { e.preventDefault(); setLayout((l) => ({ ...l, left: !l.left })) }
      else if (mod && !e.shiftKey && e.key.toLowerCase() === "j") { e.preventDefault(); setLayout((l) => ({ ...l, right: !l.right })) }
      else if (e.key === "Escape" && focus) setFocus(false)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [focus])

  const showLeft = layout.left && !focus
  const showRight = layout.right && !focus
  const iconBtn = "rounded-md p-1.5 text-zinc-400 hover:bg-white/10 hover:text-zinc-100"

  return (
    <div className="flex h-[calc(100dvh-9rem)] min-h-[520px] flex-col overflow-hidden rounded-xl border border-white/10 bg-[#0d1119]">
      {!focus && (
        <header className="flex shrink-0 items-center gap-2 border-b border-white/10 px-3 py-2">
          <button onClick={() => { void close() }} className={`${iconBtn} flex items-center gap-1 text-sm`}>
            <ArrowLeft className="h-4 w-4" />{t("back_books")}
          </button>
          <span className="st-project-badge inline-flex max-w-[12rem] shrink-0 items-center gap-1 truncate rounded-md border border-sky-400/30 bg-sky-400/10 px-2 py-0.5 text-xs text-sky-200"
            title={t("project_badge_title", { name: projectName })}>
            <FolderOpen className="h-3.5 w-3.5 shrink-0" /><span className="truncate">{projectName}</span>
          </span>
          <input value={book.title} aria-label={t("nb_title")}
            onChange={(e) => state.change((b) => ({ ...b, title: e.target.value }))}
            className="min-w-0 flex-1 truncate rounded-md bg-transparent px-2 py-1 text-base font-semibold text-zinc-100 hover:bg-white/5 focus:bg-white/5 focus:outline-none" />
          <nav className="hidden items-center rounded-lg border border-white/10 p-0.5 text-sm md:flex" aria-label="Ansicht">
            <span className="rounded-md bg-violet-500/20 px-3 py-1 text-violet-100">{t("view_write")}</span>
            {(["view_plan", "view_ask"] as const).map((k) => (
              <span key={k} title={t("soon")} className="cursor-not-allowed px-3 py-1 text-zinc-600">{t(k)}</span>
            ))}
          </nav>
          <button onClick={() => setLayout((l) => ({ ...l, left: !l.left }))} title={t("toggle_left")} className={iconBtn}><PanelLeft className="h-4 w-4" /></button>
          <button onClick={() => setLayout((l) => ({ ...l, right: !l.right }))} title={t("toggle_right")} className={iconBtn}><PanelRight className="h-4 w-4" /></button>
          <button onClick={() => setFocus(true)} title={t("focus")} className={iconBtn}><Maximize2 className="h-4 w-4" /></button>
        </header>
      )}
      <div className="flex min-h-0 flex-1">
        {showLeft && (
          <aside className="st-nav w-64 shrink-0 overflow-y-auto border-r border-white/10">
            <Navigator state={state} sceneId={sceneId} entityId={tab === "entity" ? entityId : null}
              onOpenScene={openScene} onOpenEntity={openEntity} />
          </aside>
        )}
        <main className="relative min-w-0 flex-1 overflow-y-auto">
          {focus && (
            <button onClick={() => setFocus(false)} title={t("focus")} className={`${iconBtn} fixed right-4 top-4 z-10`}>
              <Minimize2 className="h-4 w-4" />
            </button>
          )}
          {current && (
            <SceneEditor key={current.scene.id} book={book} found={current} focus={focus} textRev={state.textRev}
              onText={(text) => state.setScene(current.scene.id, { text })}
              onEditor={(e) => { editorRef.current = e }}
              onOpenScene={openScene} />
          )}
        </main>
        {showRight && current && (
          <aside className="st-context w-80 shrink-0 overflow-y-auto border-l border-white/10">
            <ContextPanel tab={tab} setTab={setTab} state={state} scene={current.scene}
              entityId={entityId} setEntityId={setEntityId} editorRef={editorRef} onSceneRemoved={(next) => setSceneId(next || first)} />
          </aside>
        )}
      </div>
      {!focus && <StatusBar book={book} found={current} saveState={state.saveState} saveError={state.saveError} onRetry={() => { void flush() }} />}
      {state.conflict && <ConflictDialog conflict={state.conflict} onResolve={state.resolveConflict} />}
    </div>
  )
}
