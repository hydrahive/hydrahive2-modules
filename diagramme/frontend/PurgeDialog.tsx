import { useEffect } from "react"
import { useTranslation } from "react-i18next"
import { Loader2, Trash2 } from "lucide-react"

interface Props { title: string; busy: boolean; onConfirm: () => void; onClose: () => void }

/** Endgültig löschen – eigener Dialog statt Rückfrage-Popup des Browsers. */
export function PurgeDialog({ title, busy, onConfirm, onClose }: Props) {
  const { t } = useTranslation("diagramme")
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])
  return (
    <div role="dialog" aria-modal="true" aria-label={t("purge")}
      className="fixed inset-0 z-[70] grid place-items-start justify-center bg-black/60 pt-[15vh]"
      onPointerDown={(e) => { if (e.target === e.currentTarget) onClose() }}>
      <div className="w-[min(520px,92vw)] space-y-4 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-5 shadow-2xl">
        <p className="text-sm text-[#e8eef8]">{t("purge_question", { title })}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded px-3 py-1.5 text-sm text-[#c8d2df] hover:text-[#e8eef8]">
            {t("cancel")}
          </button>
          <button type="button" onClick={onConfirm} disabled={busy} data-purge-confirm
            className="flex items-center gap-1.5 rounded bg-rose-500 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />} {t("purge_confirm")}
          </button>
        </div>
      </div>
    </div>
  )
}
