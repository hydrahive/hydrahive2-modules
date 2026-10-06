// Reiter „KI“: Modell, Aktion wählen → Vorschlag vom Server als Änderung (rot/grün) → Annehmen/
// Ablehnen/Nochmal. Regel (Spec 1b §4): Der Server ändert nichts; erst „Annehmen“ setzt den Text ein,
// vorher wird ein Schnappschuss angelegt.
import { useEffect, useState, type MutableRefObject } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { Loader2, Sparkles } from "lucide-react"
import { storyApi, StoryApiError } from "../api"
import { newId, type Scene } from "../model"
import type { SuggestAction, Suggestion } from "../suggest"
import { isStale } from "../staleCheck"
import type { BookState } from "../useBook"
import { ModelChooser } from "./ModelChooser"
import { ProposalCard } from "./ProposalCard"

const ACTIONS: SuggestAction[] = ["rewrite", "expand", "shorten", "continue"]
const CONTEXT_CHARS = 300  // „Weiterschreiben“: so viel Text vor dem Cursor zeigt dem Server die Stelle

interface Props { state: BookState; scene: Scene; editorRef: MutableRefObject<Editor | null> }

export function AiPanel({ state, scene, editorRef }: Props) {
  const { t } = useTranslation("storyteller")
  const [busy, setBusy] = useState<SuggestAction | null>(null)
  const [error, setError] = useState("")
  const mine = state.suggestions.filter((s) => s.sceneId === scene.id)
  const open = mine.find((s) => s.state === "open")
  const { book } = state

  const request = async (action: SuggestAction) => {
    const ed = editorRef.current
    if (!ed || busy) return
    let { from, to } = ed.state.selection
    const $f = ed.state.selection.$from
    if (action !== "continue" && from === to) { from = $f.start(); to = $f.end() }  // keine Markierung → Absatz
    if (action === "continue") from = to
    const original = action === "continue" ? "" : ed.state.doc.textBetween(from, to, "\n")
    if (action !== "continue" && !original.trim()) { setError(t("ai_err_selection_required")); return }
    // Weiterschreiben: Text vor dem Cursor mitschicken, damit der Server die Stelle findet.
    const anchor = action === "continue" ? ed.state.doc.textBetween($f.start(), to, "\n").slice(-CONTEXT_CHARS) : original
    setBusy(action)
    setError("")
    try {
      await state.flush()  // Server braucht den aktuellen Text als Zusammenhang
      const r = await storyApi.suggest(state.projectId, book.id, { scene_id: scene.id, action, selection: anchor, ...(book.model ? { model: book.model } : {}) })
      state.addSuggestion({
        id: newId(), sceneId: scene.id, action, original, from, to, model: r.model,
        proposal: r.proposal, createdAt: new Date().toISOString(), state: "open",
      })
    } catch (e) {
      setError(aiError(e, t))
    } finally { setBusy(null) }
  }

  const accept = async (s: Suggestion) => {
    const ed = editorRef.current
    if (!ed || isStale(ed, s)) return
    if (!(await state.snapshot(scene.id))) { setError(t("ai_err_snapshot")); return }
    if (isStale(ed, s)) return
    const text = s.action === "continue" ? ` ${s.proposal}` : s.proposal
    ed.chain().focus().insertContentAt({ from: s.from, to: s.to }, text).run()
    state.resolveSuggestion(s.id, "accepted")
  }

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); void accept(open) }
      else if (e.key === "Escape") { e.preventDefault(); state.resolveSuggestion(open.id, "rejected") }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  return (
    <div className="space-y-4">
      <ModelChooser value={book.model} onChange={(model) => state.change((b) => ({ ...b, model }))} />
      <p className="text-xs text-zinc-400">{t("ai_intro")}</p>
      <div className="grid grid-cols-2 gap-2">
        {ACTIONS.map((a) => (
          <button key={a} onClick={() => { void request(a) }} disabled={!!busy}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 px-2 py-2 text-sm text-zinc-200 hover:border-violet-400/50 hover:bg-violet-500/10 disabled:opacity-50">
            {busy === a ? <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-300" /> : <Sparkles className="h-3.5 w-3.5 text-violet-300" />}
            {t(`ai_${a}`)}
          </button>
        ))}
      </div>
      {busy && <p className="text-xs text-zinc-400" aria-live="polite">{t("ai_working")}</p>}
      {error && <p className="st-ai-error rounded border border-red-400/30 bg-red-500/10 px-2 py-1.5 text-xs text-red-200" role="alert">{error}</p>}

      {open && (
        <ProposalCard suggestion={open} editorRef={editorRef} busy={!!busy}
          onAccept={() => { void accept(open) }} onReject={() => state.resolveSuggestion(open.id, "rejected")}
          onAgain={() => { void request(open.action) }} />
      )}

      <section>
        <h3 className="mb-1 text-xs font-semibold text-zinc-400">{t("ai_history")}</h3>
        {mine.filter((s) => s.state !== "open").length === 0 ? <p className="text-xs text-zinc-600">{t("ai_history_none")}</p> : (
          <ul className="space-y-1 text-xs text-zinc-500">
            {mine.filter((s) => s.state !== "open").slice(0, 10).map((s) => (
              <li key={s.id} className="truncate">
                <span className={s.state === "accepted" ? "text-emerald-400" : "text-zinc-500"}>{t(`ai_state_${s.state}`)}</span>
                {" · "}{t(`ai_${s.action}`)}: {s.proposal}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function aiError(e: unknown, t: (k: string, o?: Record<string, unknown>) => string): string {
  if (!(e instanceof StoryApiError)) return t("ai_err_llm_failed", { message: String(e) })
  const known = ["ai_busy", "rate_limited", "llm_empty", "selection_required", "not_authenticated", "project_read_only"]
  if (known.includes(e.code)) return t(`ai_err_${e.code}`)
  return t("ai_err_llm_failed", { message: e.message || e.code })
}
