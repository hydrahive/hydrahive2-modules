import { useTranslation } from "react-i18next"
import { useDialog } from "@/shared/dialog/useDialog"
import { ModalPortal } from "@/shared/ModalPortal"
import { BTN, BTN_DANGER } from "./ui"

/** Eigener Bestätigungs-Dialog (kein Browser-Popup), z. B. „Playlist löschen?“. */
export function ConfirmDialog({ title, text, busy, onConfirm, onCancel }: { title: string; text: string; busy: boolean; onConfirm: () => void; onCancel: () => void }) {
  const { t } = useTranslation("radiostream")
  const dlg = useDialog({ onEscape: onCancel })
  return (
    <ModalPortal>
      <div {...dlg.props} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
        <div className="w-full max-w-md space-y-3 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] p-5">
          <h2 id={dlg.titelId} className="text-base font-semibold text-[#e8eef8]">{title}</h2>
          <p className="text-sm text-[#c8d2df] break-words">{text}</p>
          <div className="flex justify-end gap-2">
            <button type="button" className={BTN} onClick={onCancel}>{t("playlist.cancel")}</button>
            <button type="button" className={BTN_DANGER} disabled={busy} onClick={onConfirm}>{t("playlist.confirm")}</button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}
