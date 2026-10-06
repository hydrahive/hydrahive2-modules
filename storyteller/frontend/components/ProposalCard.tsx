// Ein offener KI-Vorschlag: Vergleich rot/grün, Hinweis wenn die Stelle sich geändert hat,
// Annehmen / Ablehnen / Nochmal.
import { useEffect, useState, type MutableRefObject } from "react"
import { useTranslation } from "react-i18next"
import type { Editor } from "@tiptap/react"
import { Check, RotateCcw, X } from "lucide-react"
import { wordDiff, type Suggestion } from "../suggest"
import { isStale } from "../staleCheck"

interface Props {
  suggestion: Suggestion
  editorRef: MutableRefObject<Editor | null>
  busy: boolean
  onAccept: () => void
  onReject: () => void
  onAgain: () => void
}

export function ProposalCard({ suggestion: s, editorRef, busy, onAccept, onReject, onAgain }: Props) {
  const { t } = useTranslation("storyteller")
  const [stale, setStale] = useState(false)

  // Passt die Stelle im Editor noch zum Vorschlag? Bei jeder Änderung neu prüfen (außerhalb des Renderns).
  useEffect(() => {
    const ed = editorRef.current
    if (!ed) { setStale(true); return }
    const check = () => setStale(isStale(ed, s))
    check()
    ed.on("update", check)
    return () => { ed.off("update", check) }
  }, [s, editorRef])

  return (
    <section className="st-proposal space-y-2 rounded-xl border border-violet-400/30 bg-violet-500/5 p-3">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-violet-300">{t("ai_proposal")} · {t(`ai_${s.action}`)}</h3>
      <div className="max-h-72 overflow-y-auto whitespace-pre-wrap font-serif text-sm leading-relaxed text-zinc-200">
        {wordDiff(s.original, s.proposal).map((p, i) => (
          <span key={i} className={p.kind === "del" ? "bg-red-500/15 text-red-300 line-through" : p.kind === "add" ? "bg-emerald-500/15 text-emerald-200" : ""}>{p.text}</span>
        ))}
      </div>
      {s.model && <p className="font-mono text-[10px] text-zinc-500">{s.model}</p>}
      {stale && <p className="text-xs text-amber-300">{t("ai_stale")}</p>}
      <div className="flex flex-wrap gap-2 pt-1">
        <button onClick={onAccept} disabled={stale || busy}
          className="inline-flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40">
          <Check className="h-4 w-4" />{t("ai_accept")}
        </button>
        <button onClick={onReject}
          className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/5">
          <X className="h-4 w-4" />{t("ai_reject")}
        </button>
        <button onClick={onAgain} disabled={busy}
          className="inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-violet-300 hover:bg-violet-500/10 disabled:opacity-40">
          <RotateCcw className="h-4 w-4" />{t("ai_again")}
        </button>
      </div>
    </section>
  )
}
