import { useState, type Ref } from "react"
import { useTranslation } from "react-i18next"
import { useDialog } from "@/shared/dialog/useDialog"
import { ModalPortal } from "@/shared/ModalPortal"
import { canRemove } from "./logic"
import { BTN, BTN_DANGER, INPUT } from "./ui"

interface ViewProps {
  word: string; busy: boolean; onWord: (w: string) => void; onConfirm: () => void; onCancel: () => void; titleId: string
  dialogRef?: Ref<HTMLDivElement>
}

export function RemoveDialogView({ word, busy, onWord, onConfirm, onCancel, titleId, dialogRef }: ViewProps) {
  const { t } = useTranslation("hydralabor")
  return (
    <div ref={dialogRef} role="dialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
      <div className="w-full max-w-md space-y-3 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] p-5">
        <h2 id={titleId} className="text-base font-semibold text-[#e8eef8]">{t("remove.title")}</h2>
        <p className="text-sm text-[#c8d2df]">{t("remove.text")}</p>
        <label className="block space-y-1 text-sm text-[#c8d2df]">
          <span>{t("remove.type")}</span>
          <input className={INPUT} value={word} autoComplete="off" onChange={(e) => onWord(e.target.value)} />
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" className={BTN} onClick={onCancel}>{t("remove.cancel")}</button>
          <button type="button" className={BTN_DANGER} disabled={busy || !canRemove(word)} onClick={onConfirm}>{t("remove.confirm")}</button>
        </div>
      </div>
    </div>
  )
}

/** „Labor entfernen“: eigener Dialog, Bestätigung mit dem Wort LABOR (kein Browser-Popup). */
export function RemoveDialog({ busy, onConfirm, onCancel }: { busy: boolean; onConfirm: () => void; onCancel: () => void }) {
  const [word, setWord] = useState("")
  const dlg = useDialog({ onEscape: onCancel })
  return (
    <ModalPortal>
      <RemoveDialogView word={word} busy={busy} onWord={setWord} onConfirm={onConfirm} onCancel={onCancel}
        titleId={dlg.titelId} dialogRef={dlg.ref} />
    </ModalPortal>
  )
}
