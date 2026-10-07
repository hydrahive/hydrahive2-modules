// Reiter „KI“: oben die Modus-Auswahl (Spec ghostwriter.md §2). Noch nicht gebaute Modi stünden mit
// „kommt bald“ da (seit G4 sind alle gebaut). Die Buchart wählt vor: Roman/Geschichte mit leerer Szene → Szene schreiben,
// Sach-/Lernbuch → Interview, sonst Bearbeiten.
import { useState, type MutableRefObject } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { isFiction } from "../bookFactory"
import type { Scene } from "../model"
import type { BookState } from "../useBook"
import { ChatMode } from "./ChatMode"
import { EditMode } from "./EditMode"
import { GhostChapterMode } from "./GhostChapterMode"
import { GhostSceneMode } from "./GhostSceneMode"
import { InterviewMode } from "./InterviewMode"

export type AiMode = "edit" | "scene" | "chapter" | "interview" | "chat"
const MODES: { id: AiMode; ready: boolean }[] = [
  { id: "edit", ready: true }, { id: "scene", ready: true }, { id: "chapter", ready: true },
  { id: "interview", ready: true }, { id: "chat", ready: true },
]

interface Props {
  state: BookState
  scene: Scene
  editorRef: MutableRefObject<Editor | null>
  /** Zum Reiter „Szene“ springen (z. B. um die Zusammenfassung einzutragen). */
  onGoScene: () => void
  onOpenScene: (id: string) => void
}

export function AiPanel({ state, scene, editorRef, onGoScene, onOpenScene }: Props) {
  const { t } = useTranslation("storyteller")
  const [mode, setMode] = useState<AiMode>(() => (!isFiction(state.book.kind) ? "interview" : !scene.text.trim() ? "scene" : "edit"))
  return (
    <div className="space-y-4">
      {!state.canWrite && <p className="st-read-only rounded border border-sky-400/30 bg-sky-400/5 px-2 py-1.5 text-xs text-sky-200">{t("ai_read_only")}</p>}
      <div role="radiogroup" aria-label={t("ai_mode")} className="st-ai-modes flex flex-wrap gap-1">
        {MODES.map((m) => (
          <button key={m.id} role="radio" aria-checked={mode === m.id} disabled={!m.ready}
            title={m.ready ? t(`ai_mode_${m.id}_hint`) : t("soon")} onClick={() => setMode(m.id)}
            className={`rounded-full border px-2.5 py-1 text-xs ${mode === m.id
              ? "border-violet-400 bg-violet-500/20 text-violet-100"
              : m.ready ? "border-white/10 text-zinc-300 hover:bg-white/5" : "cursor-not-allowed border-white/5 text-zinc-600"}`}>
            {t(`ai_mode_${m.id}`)}{!m.ready && <span className="ml-1 text-[10px]">· {t("soon")}</span>}
          </button>
        ))}
      </div>
      {mode === "edit" && <EditMode state={state} scene={scene} editorRef={editorRef} />}
      {mode === "scene" && <GhostSceneMode key={scene.id} state={state} scene={scene} onGoScene={onGoScene} />}
      {mode === "chapter" && <GhostChapterMode key={scene.id} state={state} scene={scene} onOpenScene={onOpenScene} />}
      {mode === "interview" && <InterviewMode key={scene.id} state={state} scene={scene} onOpenScene={onOpenScene} />}
      {mode === "chat" && <ChatMode key={scene.id} state={state} scene={scene} onGoOutline={() => setMode("chapter")} />}
    </div>
  )
}
