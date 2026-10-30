// Rechte Spalte mit Reitern. Spätere Reiter (Buch fragen, Lektor, Quellen) kommen hier dazu (Spec §4).
import type { MutableRefObject } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import type { Scene } from "../model"
import type { BookState } from "../useBook"
import { AiPanel } from "./AiPanel"
import { EntityPanel } from "./EntityPanel"
import { ScenePanel } from "./ScenePanel"
import { TeamPanel } from "./TeamPanel"

export type ContextTab = "scene" | "entity" | "ai" | "team" | "notes"
const TABS: ContextTab[] = ["scene", "entity", "ai", "team", "notes"]

interface Props {
  tab: ContextTab
  setTab: (t: ContextTab) => void
  state: BookState
  scene: Scene
  entityId: string | null
  setEntityId: (id: string | null) => void
  editorRef: MutableRefObject<Editor | null>
  onSceneRemoved: (nextSceneId: string) => void
  onOpenScene: (id: string) => void
  /** G4e: Chat-Fenster im Storyteller öffnen. */
  onOpenChat?: () => void
}

export function ContextPanel({ tab, setTab, state, scene, entityId, setEntityId, editorRef, onSceneRemoved, onOpenScene, onOpenChat }: Props) {
  const { t } = useTranslation("storyteller")
  const open = (id: string) => { setEntityId(id); setTab("entity") }
  return (
    <div className="flex h-full flex-col">
      <div role="tablist" className="flex shrink-0 border-b border-[rgb(var(--hh-s-rand,42_54_75))] text-sm">
        {TABS.map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`flex-1 px-2 py-2 ${tab === k ? "border-b-2 border-[#69d7ff] text-[#e8eef8]" : "text-[#9aa7bc] hover:text-[#c8d2df]"}`}>
            {t(`tab_${k}`)}
          </button>
        ))}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        {tab === "scene" && <ScenePanel state={state} scene={scene} onOpenEntity={open} onRemoved={onSceneRemoved} />}
        {tab === "entity" && <EntityPanel state={state} entityId={entityId} onDeleted={() => setEntityId(null)} onOpen={open} />}
        {tab === "ai" && <AiPanel state={state} scene={scene} editorRef={editorRef} onGoScene={() => setTab("scene")} onOpenScene={onOpenScene} onOpenChat={onOpenChat} />}
        {tab === "team" && <TeamPanel state={state} sceneId={scene.id} onOpenScene={onOpenScene} />}
        {tab === "notes" && (
          <textarea value={state.book.notes} placeholder={t("notes_ph")}
            onChange={(e) => state.change((b) => ({ ...b, notes: e.target.value }))}
            className="h-full min-h-[300px] w-full resize-none rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-3 text-sm text-[#e8eef8] placeholder:text-[#9aa7bc]" />
        )}
      </div>
    </div>
  )
}
