import { useTranslation } from "react-i18next"
import { useDialog } from "@/shared/dialog/useDialog"
import { ModalPortal } from "@/shared/ModalPortal"
import { BTN, BTN_DANGER } from "./ui"

/** „Zurücksetzen“: eigener Dialog (kein Browser-Popup). */
export function ResetDialog({ busy, onConfirm, onCancel }: { busy: boolean; onConfirm: () => void; onCancel: () => void }) {
  const { t } = useTranslation("hydralabor")
  const dlg = useDialog({ onEscape: onCancel })
  return (
    <ModalPortal>
      <div {...dlg.props} className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
        <div className="w-full max-w-md space-y-3 rounded-lg border border-white/10 bg-zinc-900 p-5">
          <h2 id={dlg.titelId} className="text-base font-semibold text-zinc-100">{t("reset.title")}</h2>
          <p className="text-sm text-zinc-300">{t("reset.text")}</p>
          <div className="flex justify-end gap-2">
            <button type="button" className={BTN} onClick={onCancel}>{t("reset.cancel")}</button>
            <button type="button" className={BTN_DANGER} disabled={busy} onClick={onConfirm}>{t("reset.confirm")}</button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}
