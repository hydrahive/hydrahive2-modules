// Mitte: Brotkrume, Szene im Prosa-Editor (eine Szene) oder Leseansicht „ganzes Kapitel“.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { BookOpenText, PencilLine } from "lucide-react"
import { ProseEditor } from "@/shared/prose/ProseEditor"
import ReactMarkdown from "react-markdown"
import { isFiction } from "../bookFactory"
import type { Book, Chapter, Scene, ScenePath } from "../model"

interface Props {
  book: Book
  found: { path: ScenePath; scene: Scene; chapter: Chapter }
  focus: boolean
  /** Erhöht sich, wenn der Text von außen ersetzt wurde → Editor neu laden. */
  textRev: number
  onText: (markdown: string) => void
  onEditor: (e: Editor) => void
  onOpenScene: (id: string) => void
}

export function SceneEditor({ book, found, focus, textRev, onText, onEditor, onOpenScene }: Props) {
  const { t } = useTranslation("storyteller")
  const [reading, setReading] = useState(false)
  const { scene, chapter } = found
  const fiction = isFiction(book.kind)

  return (
    <div className={`mx-auto w-full max-w-[42rem] px-6 ${focus ? "py-16" : "py-8"}`}>
      {!focus && (
        <div className="mb-6 flex items-center justify-between gap-3 text-xs text-zinc-500">
          <span className="truncate">{chapter.title} › <span className="text-zinc-300">{scene.title}</span></span>
          <button onClick={() => setReading((r) => !r)} className="inline-flex shrink-0 items-center gap-1 rounded px-2 py-1 hover:bg-white/5 hover:text-zinc-200">
            {reading ? <><PencilLine className="h-3.5 w-3.5" />{t("back_to_scene")}</> : <><BookOpenText className="h-3.5 w-3.5" />{t("read_chapter")}</>}
          </button>
        </div>
      )}
      {reading ? (
        <article className="space-y-8">
          <h2 className="font-serif text-2xl text-zinc-100">{chapter.title}</h2>
          {chapter.scenes.map((s, i) => (
            <section key={s.id} onClick={() => { setReading(false); onOpenScene(s.id) }}
              className={`cursor-pointer rounded-lg p-2 font-serif text-[1.05rem] leading-relaxed hover:bg-white/[0.03] ${s.id === scene.id ? "ring-1 ring-violet-400/30" : ""}`}>
              {i > 0 && <div className="mb-6 text-center text-zinc-600">* * *</div>}
              <div className="prose prose-invert max-w-none font-serif"><ReactMarkdown>{s.text || "…"}</ReactMarkdown></div>
            </section>
          ))}
        </article>
      ) : (
        <ProseEditor
          value={scene.text}
          docKey={`${scene.id}#${textRev}`}
          onChange={onText}
          onReady={onEditor}
          language={book.language}
          placeholder={t("placeholder")}
          className={`storyteller-editor font-serif text-[1.08rem] leading-[1.8] ${fiction ? "" : "storyteller-nonfiction"}`}
        />
      )}
    </div>
  )
}
