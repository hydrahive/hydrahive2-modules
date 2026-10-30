import { BookOpen, Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { DraftBook } from "./draftApi"
import { chosenScenes } from "./draftLogic"
import { fieldCls, Label } from "./formParts"

interface Props {
  books: DraftBook[] | null
  bookId: string
  chapters: string[]
  busy: boolean
  error: string | null
  onBook: (id: string) => void
  onToggle: (chapterId: string) => void
  onRun: () => void
  onClose: () => void
}

/** „Aus dem Storyteller“: Buch wählen, Kapitel ankreuzen. Das Buch selbst bleibt unverändert. */
export function BookPick({ books, bookId, chapters, busy, error, onBook, onToggle, onRun, onClose }: Props) {
  const { t } = useTranslation("studio")
  const book = books?.find((b) => b.id === bookId) ?? null
  const count = chosenScenes(book, chapters)
  return (
    <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-book-pick>
      <h3 className="text-sm font-black text-[#e8eef8]">{t("book_title")}</h3>
      <p className="leading-relaxed text-[#9aa7bc]">{t("book_text")}</p>
      {!books ? <p className="flex items-center gap-1.5 text-[#9aa7bc]"><Loader2 size={12} className="animate-spin" /> {t("loading")}</p>
        : !books.length ? <p>{t("book_none")}</p> : (
          <>
            <label className="block">
              <Label>{t("book_label")}</Label>
              <select value={bookId} onChange={(e) => onBook(e.target.value)} disabled={busy} aria-label={t("book_label")} className={fieldCls}>
                {books.map((b) => <option key={b.id} value={b.id}>{b.title || t("untitled")}</option>)}
              </select>
            </label>
            {book && (
              <fieldset className="max-h-[32vh] space-y-1 overflow-y-auto rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] p-2">
                <legend className="px-1"><Label>{t("book_chapters")}</Label></legend>
                {book.chapters.map((c) => (
                  <label key={c.id} className="flex items-center gap-2">
                    <input type="checkbox" checked={chapters.includes(c.id)} onChange={() => onToggle(c.id)} disabled={busy} />
                    <span className="truncate text-[#e8eef8]">{c.title || t("untitled")}</span>
                    <span className="ml-auto shrink-0 text-[10px] text-[#9aa7bc]">{t("scene_count", { count: c.scenes })}</span>
                  </label>
                ))}
              </fieldset>
            )}
            <p className="text-[#9aa7bc]">{t("book_scenes", { count })}</p>
          </>
        )}
      {error && <p className="text-[#ff6b8a]" data-book-error>{error}</p>}
      <div className="flex justify-end gap-2">
        <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
        {!!books?.length && (
          <button type="button" onClick={onRun} disabled={busy || !count} data-book-run
            className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy ? <Loader2 size={13} className="animate-spin" /> : <BookOpen size={13} />} {t("book_run")}
          </button>
        )}
      </div>
    </div>
  )
}
