// Reiter „KI“: Aktion wählen → Vorschlag als Änderung (rot/grün) → Annehmen/Ablehnen/Nochmal.
// Regel (Spec §3 W3, §7): Ohne „Annehmen“ ändert sich am Buch nichts; vor dem Annehmen Schnappschuss.
import { useEffect, useState, type MutableRefObject } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { Check, RotateCcw, Sparkles, X } from "lucide-react"
import { newId, type Scene } from "../model"
import { draftSuggestion, wordDiff, type SuggestAction, type Suggestion } from "../suggest"
import type { useBook } from "../useBook"

const ACTIONS: SuggestAction[] = ["rewrite", "expand", "shorten", "continue"]

interface Props { state: ReturnType<typeof useBook>; scene: Scene; editorRef: MutableRefObject<Editor | null> }

export function AiPanel({ state, scene, editorRef }: Props) {
  const { t } = useTranslation("storyteller")
  const [variant, setVariant] = useState(0)
  const mine = state.suggestions.filter((s) => s.sceneId === scene.id)
  const open = mine.find((s) => s.state === "open")
  const [stale, setStale] = useState(false)

  // Passt die Stelle im Editor noch zum Vorschlag? Bei jeder Änderung neu prüfen (außerhalb des Renderns).
  useEffect(() => {
    const ed = editorRef.current
    if (!open || !ed) { setStale(false); return }
    const check = () => setStale(isStale(ed, open))
    check()
    ed.on("update", check)
    return () => { ed.off("update", check) }
  }, [open, editorRef])

  const request = (action: SuggestAction, again = false) => {
    const ed = editorRef.current
    if (!ed) return
    let { from, to } = ed.state.selection
    if (action !== "continue" && from === to) {  // keine Markierung → aktueller Absatz
      const $f = ed.state.selection.$from
      from = $f.start(); to = $f.end()
    }
    if (action === "continue") from = to
    const original = action === "continue" ? "" : ed.state.doc.textBetween(from, to, "\n")
    const v = again ? variant + 1 : 0
    setVariant(v)
    state.addSuggestion({
      id: newId("ai"), sceneId: scene.id, action, original, from, to,
      proposal: draftSuggestion(action, original, v), createdAt: new Date().toISOString(), state: "open",
    })
  }

  const accept = (s: Suggestion) => {
    const ed = editorRef.current
    if (!ed || isStale(ed, s)) return
    state.snapshot(scene.id)
    const text = s.action === "continue" ? ` ${s.proposal}` : s.proposal
    ed.chain().focus().insertContentAt({ from: s.from, to: s.to }, text).run()
    state.resolveSuggestion(s.id, "accepted")
  }

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") { e.preventDefault(); accept(open) }
      else if (e.key === "Escape") { e.preventDefault(); state.resolveSuggestion(open.id, "rejected") }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  })

  return (
    <div className="space-y-4">
      <p className="text-xs text-zinc-400">{t("ai_intro")}</p>
      <div className="grid grid-cols-2 gap-2">
        {ACTIONS.map((a) => (
          <button key={a} onClick={() => request(a)}
            className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-white/10 px-2 py-2 text-sm text-zinc-200 hover:border-violet-400/50 hover:bg-violet-500/10">
            <Sparkles className="h-3.5 w-3.5 text-violet-300" />{t(`ai_${a}`)}
          </button>
        ))}
      </div>
      <p className="rounded border border-amber-400/20 bg-amber-400/5 px-2 py-1 text-[11px] text-amber-200/80">{t("ai_placeholder_note")}</p>

      {open && (
        <section className="space-y-2 rounded-xl border border-violet-400/30 bg-violet-500/5 p-3">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-300">{t("ai_proposal")} · {t(`ai_${open.action}`)}</h3>
          <div className="max-h-72 overflow-y-auto font-serif text-sm leading-relaxed text-zinc-200">
            {wordDiff(open.original, open.proposal).map((p, i) => (
              <span key={i} className={p.kind === "del" ? "bg-red-500/15 text-red-300 line-through" : p.kind === "add" ? "bg-emerald-500/15 text-emerald-200" : ""}>{p.text}</span>
            ))}
          </div>
          {stale && <p className="text-xs text-amber-300">{t("ai_stale")}</p>}
          <div className="flex flex-wrap gap-2 pt-1">
            <button onClick={() => accept(open)} disabled={stale}
              className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40">
              <Check className="h-4 w-4" />{t("ai_accept")}
            </button>
            <button onClick={() => state.resolveSuggestion(open.id, "rejected")}
              className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5">
              <X className="h-4 w-4" />{t("ai_reject")}
            </button>
            <button onClick={() => request(open.action, true)}
              className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-violet-300 hover:bg-violet-500/10">
              <RotateCcw className="h-4 w-4" />{t("ai_again")}
            </button>
          </div>
        </section>
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
      <p className="text-[11px] text-zinc-600">{t("ai_model")}</p>
    </div>
  )
}

/** Ist die markierte Stelle noch dieselbe wie beim Vorschlag? Sonst nicht blind ersetzen. */
function isStale(ed: Editor | null, s: Suggestion): boolean {
  if (!ed) return true
  const size = ed.state.doc.content.size
  if (s.to > size || s.from > size) return true
  return s.action !== "continue" && ed.state.doc.textBetween(s.from, s.to, "\n") !== s.original
}
