// Linke Spalte: Gliederung (Teil → Kapitel → Szene) mit Ziehen, Alt+↑/↓, Umbenennen; darunter Steckbriefe.
import { useRef, useState, type DragEvent } from "react"
import { useTranslation } from "react-i18next"
import { ChevronDown, ChevronRight, FilePlus2, FolderPlus } from "lucide-react"
import { addChapter, addScene, moveScene, nudgeScene, renameNode, type Book } from "../model"
import { EntityList } from "./EntityList"

interface Props {
  book: Book
  sceneId: string
  entityId: string | null
  onOpenScene: (id: string) => void
  onOpenEntity: (id: string) => void
  change: (fn: (b: Book) => Book) => void
}

export function Navigator({ book, sceneId, entityId, onOpenScene, onOpenEntity, change }: Props) {
  const { t } = useTranslation("storyteller")
  const [closed, setClosed] = useState<Record<string, boolean>>({})
  const [editing, setEditing] = useState<string | null>(null)
  // Gezogene Szene: im Ref sofort verfügbar (dragover kommt vor dem nächsten Render),
  // im State nur für die Darstellung (halbtransparent).
  const dragRef = useRef<string | null>(null)
  const [drag, setDrag] = useState<string | null>(null)
  const [over, setOver] = useState<string | null>(null)
  const startDrag = (e: DragEvent, id: string) => {
    dragRef.current = id
    e.dataTransfer.effectAllowed = "move"
    e.dataTransfer.setData("text/plain", id)  // Firefox startet das Ziehen nur mit Daten
    setDrag(id)
  }
  const endDrag = () => { dragRef.current = null; setDrag(null); setOver(null) }
  const dropOn = (chapterId: string, beforeSceneId?: string) => {
    const id = dragRef.current
    if (id) change((b) => moveScene(b, id, chapterId, beforeSceneId))
    endDrag()
  }

  const rename = (id: string, title: string) => { change((b) => renameNode(b, id, title)); setEditing(null) }
  const Title = ({ id, title, cls }: { id: string; title: string; cls: string }) => editing === id ? (
    <input autoFocus defaultValue={title} className="w-full rounded bg-zinc-950 px-1 text-sm text-zinc-100"
      onBlur={(e) => rename(id, e.target.value)}
      onKeyDown={(e) => { if (e.key === "Enter") rename(id, e.currentTarget.value); if (e.key === "Escape") setEditing(null) }} />
  ) : <span className={cls} onDoubleClick={() => setEditing(id)} title={t("rename")}>{title}</span>

  return (
    <div className="space-y-4 p-2 text-sm">
      <div>
        <div className="flex items-center justify-between px-1 pb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
          {t("structure")}
        </div>
        {book.parts.map((p) => (
          <div key={p.id}>
            {book.parts.length > 1 && <Title id={p.id} title={p.title} cls="block px-1 py-1 text-xs font-semibold text-zinc-400" />}
            {p.chapters.map((c) => (
              <div key={c.id} className="mb-1"
                onDragOver={(e) => { if (dragRef.current) { e.preventDefault(); e.dataTransfer.dropEffect = "move"; setOver(`c:${c.id}`) } }}
                onDrop={(e) => { e.preventDefault(); dropOn(c.id) }}>
                <div className={`group flex items-center gap-1 rounded px-1 py-1 ${over === `c:${c.id}` ? "bg-violet-500/10" : ""}`}>
                  <button onClick={() => setClosed((x) => ({ ...x, [c.id]: !x[c.id] }))} className="text-zinc-500 hover:text-zinc-200" aria-label={c.title}>
                    {closed[c.id] ? <ChevronRight className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                  </button>
                  <Title id={c.id} title={c.title} cls="flex-1 truncate font-semibold text-zinc-200" />
                  <button onClick={() => { const r = addScene(book, c.id); change(() => r.book); onOpenScene(r.id) }}
                    title={t("add_scene")} className="text-zinc-600 opacity-0 hover:text-zinc-200 group-hover:opacity-100">
                    <FilePlus2 className="h-3.5 w-3.5" />
                  </button>
                </div>
                {!closed[c.id] && c.scenes.map((s) => (
                  <div key={s.id} draggable
                    onDragStart={(e) => startDrag(e, s.id)} onDragEnd={endDrag}
                    onDragOver={(e) => {
                      if (dragRef.current && dragRef.current !== s.id) { e.preventDefault(); e.stopPropagation(); e.dataTransfer.dropEffect = "move"; setOver(`s:${s.id}`) }
                    }}
                    onDrop={(e) => { e.preventDefault(); e.stopPropagation(); dropOn(c.id, s.id) }}
                    className={`ml-4 border-t-2 ${over === `s:${s.id}` ? "border-violet-400" : "border-transparent"}`}>
                    <button onClick={() => onOpenScene(s.id)} aria-current={s.id === sceneId}
                      onKeyDown={(e) => {
                        if (e.altKey && (e.key === "ArrowUp" || e.key === "ArrowDown")) { e.preventDefault(); change((b) => nudgeScene(b, s.id, e.key === "ArrowUp" ? -1 : 1)) }
                        if (e.key === "F2") { e.preventDefault(); setEditing(s.id) }
                      }}
                      className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${s.id === sceneId ? "bg-violet-500/20 text-violet-100" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"} ${drag === s.id ? "opacity-40" : ""}`}>
                      <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${dot(s.status)}`} />
                      <Title id={s.id} title={s.title} cls="truncate" />
                    </button>
                  </div>
                ))}
              </div>
            ))}
            <button onClick={() => { const r = addChapter(book, p.id); change(() => r.book); onOpenScene(r.sceneId) }}
              className="ml-1 mt-1 flex items-center gap-1.5 rounded px-1 py-1 text-xs text-zinc-500 hover:bg-white/5 hover:text-zinc-200">
              <FolderPlus className="h-3.5 w-3.5" />{t("add_chapter")}
            </button>
          </div>
        ))}
        <p className="px-1 pt-1 text-[11px] text-zinc-600">{t("drag_hint")} F2 · Alt+↑/↓</p>
      </div>
      <EntityList book={book} activeId={entityId} onOpen={onOpenEntity} change={change} />
    </div>
  )
}

function dot(status: string): string {
  return { idea: "bg-zinc-600", draft: "bg-amber-400", revised: "bg-sky-400", done: "bg-emerald-400" }[status] ?? "bg-zinc-600"
}
