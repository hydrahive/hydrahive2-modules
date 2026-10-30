import { Check, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Draft } from "./draftApi"
import { draftCounts } from "./draftLogic"

interface Props {
  draft: Draft
  append: boolean
  truncated: number
  busy: boolean
  canDecompose: boolean
  decompose: boolean
  onDecompose: (v: boolean) => void
  onApply: () => void
  onDiscard: () => void
}

/** Vorschau eines Entwurfs: was entsteht, bevor etwas gespeichert wird. „Übernehmen“ oder „Verwerfen“. */
export function DraftPreview({ draft, append, truncated, busy, canDecompose, decompose, onDecompose, onApply, onDiscard }: Props) {
  const { t } = useTranslation("studio")
  const names = Object.fromEntries(draft.elements.map((e) => [e.key, e.name]))
  return (
    <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-draft-preview>
      <h3 className="text-sm font-black text-[#e8eef8]">{t("draft_title")}</h3>
      <div>
        <p className="text-sm font-bold text-[#e8eef8]">{draft.head.title || t("untitled")}</p>
        {draft.head.logline && <p className="text-[#9aa7bc]">{draft.head.logline}</p>}
      </div>
      <p>{t("draft_counts", draftCounts(draft))}</p>
      {!!draft.elements.length && (
        <p className="text-[#9aa7bc]">{t("draft_elements")}: {draft.elements.map((e) => e.name).join(", ")}</p>
      )}
      <ol className="max-h-[34vh] space-y-2 overflow-y-auto rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2" data-draft-scenes>
        {draft.scenes.map((s, i) => (
          <li key={i} className="space-y-0.5">
            <p className="font-bold text-[#e8eef8]">{i + 1}. {s.title || t("untitled")}</p>
            {s.description && <p className="line-clamp-2 text-[#9aa7bc]">{s.description}</p>}
            {!!s.element_keys.length && <p className="text-[10px] text-[#9aa7bc]">{s.element_keys.map((k) => names[k]).filter(Boolean).join(", ")}</p>}
            {!!s.shots.length && (
              <ul className="list-disc pl-4 text-[11px] text-[#9aa7bc]">
                {s.shots.map((sh, j) => <li key={j} className="truncate">{sh.prompt} <span className="text-[#9aa7bc]">({sh.duration} s)</span></li>)}
              </ul>
            )}
          </li>
        ))}
      </ol>
      {truncated > 0 && <p className="text-[#ffb86b]">{t("draft_truncated", { count: truncated })}</p>}
      <p className="rounded-[4px] border border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2.5 py-2 leading-relaxed text-[#9aa7bc]" data-draft-mode={append ? "append" : "new"}>
        {append ? t("draft_append") : t("draft_new")}
      </p>
      {canDecompose && (
        <label className="flex items-start gap-2">
          <input type="checkbox" checked={decompose} onChange={(e) => onDecompose(e.target.checked)} disabled={busy} className="mt-0.5" />
          <span>{t("draft_decompose")}</span>
        </label>
      )}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onDiscard} disabled={busy} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("draft_discard")}</button>
        <button type="button" onClick={onApply} disabled={busy} data-draft-apply
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />} {t("draft_apply")}
        </button>
      </div>
    </div>
  )
}
