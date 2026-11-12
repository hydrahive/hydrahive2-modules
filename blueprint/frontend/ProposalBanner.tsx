import { Sparkles } from "lucide-react"
import type { ProposalDiff } from "./boardGraph"
import { formatStamp } from "./boardView"
import { BUTTON, BUTTON_ON, BUTTON_PRIMARY } from "./styles"
import type { T } from "./texts.de"

interface Props {
  note: string | null
  at: string | null
  /** Vergleich mit der eigenen Fassung. null: Der Vorschlag ist nicht lesbar. */
  diff: ProposalDiff | null
  preview: boolean
  busy: boolean
  error: string | null
  locale: string
  t: T
  onPreview: () => void
  onAccept: () => void
  onDiscard: () => void
}

const SHOWN = 6

function names(list: string[], t: T): string {
  const shown = list.slice(0, SHOWN).join(", ")
  return list.length > SHOWN ? `${shown} ${t("list_more", { n: list.length - SHOWN })}` : shown
}

/** Band über der Zeichenfläche: Der Agent hat einen Vorschlag neben die Fassung des Nutzers gelegt. */
export function ProposalBanner({ note, at, diff, preview, busy, error, locale, t, onPreview, onAccept, onDiscard }: Props) {
  const same = diff !== null && diff.added.length === 0 && diff.removed.length === 0
  return (
    <section aria-label={t("proposal_title")} className="border-b border-[#69d7ff]/30 bg-[#69d7ff]/[0.07] px-4 py-2.5">
      <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
        <div className="min-w-0 flex-1 space-y-1 text-xs text-[#c8d2df]">
          <p className="flex flex-wrap items-center gap-2">
            <Sparkles size={13} className="shrink-0 text-[#69d7ff]" aria-hidden />
            <span className="font-semibold text-[#e8eef8]">{t("proposal_title")}</span>
            {at && <span className="text-[#9aa7bc]">{formatStamp(at, locale)}</span>}
            {diff && (
              <span className="text-[#9aa7bc]">
                {t("count_nodes", { n: diff.nodes })} · {t("count_edges", { n: diff.edges })}
              </span>
            )}
          </p>
          {note && <p className="break-words text-sm text-[#e8eef8]">{note}</p>}
          {diff === null && <p className="text-amber-200">{t("proposal_unreadable")}</p>}
          {same && <p>{t("proposal_same")}</p>}
          {diff !== null && diff.added.length > 0 && (
            <p className="break-words">
              <span className="font-semibold text-emerald-200">{t("proposal_added", { n: diff.added.length })}</span>
              {" "}{names(diff.added, t)}
            </p>
          )}
          {diff !== null && diff.removed.length > 0 && (
            <p className="break-words">
              <span className="font-semibold text-rose-200">{t("proposal_removed", { n: diff.removed.length })}</span>
              {" "}{names(diff.removed, t)}
            </p>
          )}
          {diff !== null && (
            <p className="text-[#9aa7bc]">{t(preview ? "proposal_preview_hint" : "proposal_accept_hint")}</p>
          )}
          {error && <p role="alert" className="text-rose-200">{error}</p>}
        </div>
        <div className="flex shrink-0 flex-wrap items-center gap-2">
          {diff !== null && (
            <button type="button" onClick={onPreview} disabled={busy} aria-pressed={preview}
              className={preview ? BUTTON_ON : BUTTON}>{t(preview ? "proposal_preview_off" : "proposal_preview")}</button>
          )}
          {diff !== null && (
            <button type="button" onClick={onAccept} disabled={busy} className={BUTTON_PRIMARY}>
              {t("proposal_accept")}
            </button>
          )}
          <button type="button" onClick={onDiscard} disabled={busy} className={BUTTON}>{t("proposal_discard")}</button>
        </div>
      </div>
    </section>
  )
}
