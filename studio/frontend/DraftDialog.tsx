import { useTranslation } from "react-i18next"
import { BookPick } from "./BookPick"
import { DraftPreview } from "./DraftPreview"
import { IdeaForm } from "./IdeaForm"
import { Backdrop } from "./StudioDialogs"
import type { DraftState } from "./useDraft"

/** Ein Dialog für beide Wege (B2): Idee bzw. Buch wählen, dann die Vorschau des Entwurfs. */
export function DraftDialog({ d, append }: { d: DraftState; append: boolean }) {
  const { t } = useTranslation("studio")
  const s = d.step
  if (!s) return null
  const label = s.kind === "idea" ? t("idea_title") : s.kind === "book" ? t("book_title") : t("draft_title")
  return (
    <Backdrop onClose={d.close} label={label}>
      {s.kind === "idea" ? (
        <IdeaForm idea={d.idea} length={d.length} style={d.style} busy={d.busy} error={d.error}
          onIdea={d.setIdea} onLength={d.setLength} onStyle={d.setStyle} onRun={d.runIdea} onClose={d.close} />
      ) : s.kind === "book" ? (
        <BookPick books={s.books} bookId={d.bookId} chapters={d.chapters} busy={d.busy} error={d.error}
          onBook={d.selectBook} onToggle={d.toggleChapter} onRun={d.runBook} onClose={d.close} />
      ) : (
        <>
          <DraftPreview draft={s.draft} append={append} truncated={s.truncated} busy={d.busy}
            canDecompose={s.fromBook} decompose={d.decompose} onDecompose={d.setDecompose} onApply={d.apply} onDiscard={d.close} />
          {d.error && <p className="px-4 pb-3 text-xs text-[#ff6b8a]" data-draft-error>{d.error}</p>}
        </>
      )}
    </Backdrop>
  )
}
