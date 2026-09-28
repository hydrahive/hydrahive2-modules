import { useState } from "react"
import { useTranslation } from "react-i18next"
import { DELETION_CONFIRM_WORD } from "../deletionApi"

interface Props {
  busy: boolean
  onConfirm: (word: string) => void
  onCancel: () => void
}

/** Bestätigung per Eintippen des Lösch-Worts. Ein Klick allein reicht nicht. */
export function DeleteConfirmDialog({ busy, onConfirm, onCancel }: Props) {
  const { t } = useTranslation("akte")
  const [word, setWord] = useState("")
  const ok = word === DELETION_CONFIRM_WORD

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md rounded-2xl border border-rose-500/30 bg-zinc-950 p-5 space-y-4">
        <h3 className="text-base font-semibold text-rose-300">{t("deletion.confirm_title")}</h3>
        <p className="text-sm text-zinc-300">{t("deletion.confirm_text", { word: DELETION_CONFIRM_WORD })}</p>
        <input
          autoFocus
          value={word}
          disabled={busy}
          onChange={(e) => setWord(e.target.value)}
          placeholder={t("deletion.confirm_placeholder", { word: DELETION_CONFIRM_WORD })}
          className="w-full rounded-lg border border-white/10 bg-zinc-900 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-rose-500/50"
        />
        <div className="flex justify-end gap-2">
          <button onClick={onCancel} disabled={busy}
            className="px-3 py-1.5 rounded-lg text-sm text-zinc-400 hover:text-zinc-200 disabled:opacity-40">
            {t("deletion.cancel")}
          </button>
          <button onClick={() => onConfirm(word)} disabled={!ok || busy}
            className="px-3 py-1.5 rounded-lg text-sm bg-rose-600 text-white hover:bg-rose-500 disabled:opacity-40">
            {t("deletion.confirm_button")}
          </button>
        </div>
      </div>
    </div>
  )
}
